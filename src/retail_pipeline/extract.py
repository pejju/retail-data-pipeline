"""Extract step: read the raw source file."""
import pandas as pd

from . import config


def extract_raw(path=None, sheet=None) -> pd.DataFrame:
    """Read the raw Online Retail II data (Excel sheet, or a CSV export of it)."""
    path = path or config.RAW_FILE
    sheet = sheet or config.RAW_SHEET
    if str(path).lower().endswith(".csv"):
        return pd.read_csv(path, dtype={"Invoice": str, "StockCode": str})
    return pd.read_excel(path, sheet_name=sheet)
