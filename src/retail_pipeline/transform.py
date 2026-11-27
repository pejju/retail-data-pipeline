"""Transform step: the cleaning rules worked out in notebooks/01_data_loading_inspection.ipynb.

Every rule is a small function that takes a DataFrame and returns a new one, so each rule can be
unit-tested on its own (see tests/test_transform.py).
"""
import pandas as pd

from . import config


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows that are identical in every column (6,865 in the source: export glitches)."""
    return df.drop_duplicates(keep="first")


def fix_types(df: pd.DataFrame) -> pd.DataFrame:
    """Invoice and StockCode arrive as a mix of int and str; force str so .str methods work."""
    df = df.copy()
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag (not delete) cancellations and non-product rows, and build the IsValidSale flag."""
    df = df.copy()
    df["IsCancelled"] = df["Invoice"].str.startswith("C")
    df["IsNonProduct"] = df["StockCode"].isin(config.NON_PRODUCT_CODES)
    df["IsValidSale"] = ~df["IsCancelled"] & ~df["IsNonProduct"] & (df["Price"] > 0)
    return df


def fill_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    """Recover missing descriptions from other rows with the same StockCode; else 'Unknown Product'."""
    df = df.copy()
    desc_map = df.dropna(subset=["Description"]).groupby("StockCode")["Description"].first()
    df["Description"] = df["Description"].fillna(df["StockCode"].map(desc_map))
    df["Description"] = df["Description"].fillna("Unknown Product")
    return df


def add_total_price(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["TotalPrice"] = df["Quantity"] * df["Price"]
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Run every cleaning rule in order."""
    df = remove_duplicates(df)
    df = fix_types(df)
    df = add_flags(df)
    df = fill_descriptions(df)
    df = add_total_price(df)
    return df


def save_processed(df: pd.DataFrame) -> None:
    """Write the cleaned data, plus the customer-only subset (rows with a Customer ID)."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.CLEAN_FILE, index=False)
    df[df["Customer ID"].notnull()].to_csv(config.CUSTOMERS_FILE, index=False)


def read_processed(path=None) -> pd.DataFrame:
    """Read the cleaned CSV back with the right types (used when steps run as separate tasks)."""
    df = pd.read_csv(path or config.CLEAN_FILE, dtype={"Invoice": str, "StockCode": str})
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df
