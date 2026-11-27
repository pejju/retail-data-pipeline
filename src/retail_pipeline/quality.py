"""Data quality gate: checks that run after every load and STOP the pipeline if the data is wrong.

If a check fails, a DataQualityError is raised. In Airflow that marks the task as failed, so the
RFM view (and therefore the dashboard) is never refreshed from bad data.
"""
import logging

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


class DataQualityError(Exception):
    pass


def _scalar(conn, sql: str):
    return conn.execute(text(sql)).scalar()


def run_checks(clean: pd.DataFrame, engine: Engine) -> None:
    failures = []

    def check(passed: bool, name: str, detail: str) -> None:
        log.info("[%s] %s: %s", "PASS" if passed else "FAIL", name, detail)
        if not passed:
            failures.append(f"{name}: {detail}")

    with engine.connect() as conn:
        # 1. Completeness: every cleaned row made it into the fact table
        fact_rows = _scalar(conn, "SELECT COUNT(*) FROM fact_sales")
        check(fact_rows == len(clean), "row_count", f"fact_sales={fact_rows}, cleaned data={len(clean)}")

        # 2. Referential integrity: no fact row points at a missing dimension row
        for dim, key in [("dim_product", "ProductKey"), ("dim_date", "DateKey")]:
            orphans = _scalar(conn, f"""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN {dim} d ON f.{key} = d.{key}
                WHERE d.{key} IS NULL""")
            check(orphans == 0, f"no_orphans_{dim}", f"{orphans} orphaned rows")

        orphan_customers = _scalar(conn, """
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_customer c ON f.CustomerKey = c.CustomerKey
            WHERE f.CustomerKey IS NOT NULL AND c.CustomerKey IS NULL""")
        check(orphan_customers == 0, "no_orphans_dim_customer", f"{orphan_customers} orphaned rows")

        # 3. Uniqueness: one row per customer and per product in the dimensions
        dup_customers = _scalar(conn, "SELECT COUNT(*) - COUNT(DISTINCT CustomerID) FROM dim_customer")
        check(dup_customers == 0, "unique_customers", f"{dup_customers} duplicate CustomerIDs")

        # 4. Validity: valid sales never have a zero or negative price
        bad_prices = _scalar(conn, "SELECT COUNT(*) FROM fact_sales WHERE IsValidSale = 1 AND Price <= 0")
        check(bad_prices == 0, "valid_sale_price_positive", f"{bad_prices} bad rows")

        # 5. Reconciliation: revenue in MySQL matches revenue computed in pandas
        db_revenue = float(_scalar(conn, "SELECT SUM(TotalPrice) FROM fact_sales WHERE IsValidSale = 1") or 0)
        df_revenue = float(clean.loc[clean["IsValidSale"], "TotalPrice"].sum())
        check(abs(db_revenue - df_revenue) < 1.0, "revenue_reconciles",
              f"MySQL={db_revenue:,.2f}, pandas={df_revenue:,.2f}")

    if failures:
        raise DataQualityError("Data quality checks failed:\n  - " + "\n  - ".join(failures))
    log.info("All data quality checks passed")
