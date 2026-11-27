"""Load step: build the star schema (notebooks/03_load_warehouse.ipynb) and write it to MySQL.

The load is idempotent: tables are truncated first (full refresh), so running the pipeline twice
gives the same result as running it once.
"""
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from . import config

log = logging.getLogger(__name__)

TABLES_LOAD_ORDER = ["dim_customer", "dim_product", "dim_date", "fact_sales"]


def run_sql_file(engine: Engine, path: Path) -> None:
    """Execute every statement in a .sql file (statements separated by ';').

    CREATE DATABASE and USE statements are skipped: the engine is already connected to the database
    named in the config, so the same SQL files work for any database name.
    """
    statements = []
    for raw in Path(path).read_text(encoding="utf-8").split(";"):
        lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt and not stmt.upper().startswith(("USE ", "CREATE DATABASE")):
            statements.append(stmt)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def create_database_if_missing() -> None:
    """Create the target database (name from config) before connecting to it."""
    server = create_engine(config.server_url())
    with server.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{config.db_name()}`"))
    server.dispose()


def truncate_tables(engine: Engine) -> None:
    """Empty all warehouse tables. TRUNCATE also resets AUTO_INCREMENT, so surrogate keys are stable."""
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(TABLES_LOAD_ORDER):
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def build_dim_customer(df: pd.DataFrame) -> pd.DataFrame:
    dim = df.dropna(subset=["Customer ID"]).drop_duplicates(subset=["Customer ID"])[["Customer ID", "Country"]]
    dim = dim.rename(columns={"Customer ID": "CustomerID"})
    dim["CustomerID"] = dim["CustomerID"].astype(int)
    return dim


def build_dim_product(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=["StockCode"])[["StockCode", "Description"]]


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(pd.Series(df["InvoiceDate"].dt.normalize().unique())).sort_values()
    dim = pd.DataFrame({"FullDate": dates})
    dim["DateKey"] = dim["FullDate"].dt.strftime("%Y%m%d").astype(int)
    dim["Year"] = dim["FullDate"].dt.year
    dim["Month"] = dim["FullDate"].dt.month
    dim["MonthName"] = dim["FullDate"].dt.month_name()
    dim["Quarter"] = dim["FullDate"].dt.quarter
    dim["Weekday"] = dim["FullDate"].dt.day_name()
    dim["FullDate"] = dim["FullDate"].dt.date
    return dim[["DateKey", "FullDate", "Year", "Month", "MonthName", "Quarter", "Weekday"]]


def build_fact_sales(df: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    """Swap natural keys for the surrogate keys MySQL generated in the dimension tables."""
    customer_keys = pd.read_sql("SELECT CustomerKey, CustomerID FROM dim_customer", con=engine)
    product_keys = pd.read_sql("SELECT ProductKey, StockCode FROM dim_product", con=engine)

    fact = df.rename(columns={"Invoice": "InvoiceNo", "Customer ID": "CustomerID"})
    fact = fact.merge(customer_keys, on="CustomerID", how="left")
    fact = fact.merge(product_keys, on="StockCode", how="left")
    fact["DateKey"] = fact["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    # CustomerKey is NULL for anonymous transactions; keep it as a nullable integer
    fact["CustomerKey"] = fact["CustomerKey"].astype("Int64")
    return fact[["InvoiceNo", "CustomerKey", "ProductKey", "DateKey",
                 "Quantity", "Price", "TotalPrice", "IsCancelled", "IsValidSale"]]


def load_all(df: pd.DataFrame, engine: Engine) -> None:
    """Full refresh of the warehouse: truncate, then load dimensions before the fact table."""
    truncate_tables(engine)

    dim_customer = build_dim_customer(df)
    dim_customer.to_sql("dim_customer", con=engine, if_exists="append", index=False)
    log.info("Loaded dim_customer: %d rows", len(dim_customer))

    dim_product = build_dim_product(df)
    dim_product.to_sql("dim_product", con=engine, if_exists="append", index=False)
    log.info("Loaded dim_product: %d rows", len(dim_product))

    dim_date = build_dim_date(df)
    dim_date.to_sql("dim_date", con=engine, if_exists="append", index=False)
    log.info("Loaded dim_date: %d rows", len(dim_date))

    fact_sales = build_fact_sales(df, engine)
    fact_sales.to_sql("fact_sales", con=engine, if_exists="append", index=False,
                      chunksize=5000, method="multi")
    log.info("Loaded fact_sales: %d rows", len(fact_sales))


def create_schema(engine: Engine) -> None:
    """Create the database and the star-schema tables if they don't exist yet."""
    create_database_if_missing()
    run_sql_file(engine, config.SQL_DIR / "01_schema.sql")


def refresh_rfm_view(engine: Engine) -> None:
    run_sql_file(engine, config.SQL_DIR / "03_create_rfm_view.sql")
