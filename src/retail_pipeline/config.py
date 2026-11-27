"""Central configuration: file paths and database connection, read from environment variables / .env.

Nothing secret is hard-coded here. Locally the values come from the .env file in the project root;
inside Docker / Airflow they come from the container environment.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# src/retail_pipeline/config.py -> project root is two folders up
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

RAW_FILE = PROJECT_ROOT / os.getenv("RAW_FILE", "data/raw/online_retail_II.xlsx")
RAW_SHEET = os.getenv("RAW_SHEET", "Year 2009-2010")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEAN_FILE = PROCESSED_DIR / "cleaned_online_retail.csv"
CUSTOMERS_FILE = PROCESSED_DIR / "cleaned_online_retail_customers.csv"
SQL_DIR = PROJECT_ROOT / "SQL"

# StockCodes confirmed (by their Description) to be postage, fees and adjustments, not products.
NON_PRODUCT_CODES = ["POST", "D", "M", "DOT", "ADJUST", "S", "B", "AMAZONFEE", "GIFT"]


def db_name() -> str:
    return os.getenv("DB_NAME", "retail_analytics")


def server_url() -> str:
    """SQLAlchemy URL for the MySQL server itself (no database selected)."""
    user = quote_plus(os.environ["DB_USER"])
    password = quote_plus(os.environ["DB_PASSWORD"])
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}"


def database_url() -> str:
    """SQLAlchemy URL for the MySQL warehouse, built from environment variables."""
    return f"{server_url()}/{db_name()}"
