"""Unit tests for the cleaning rules. They use a tiny hand-made DataFrame, so no database is needed."""
import pandas as pd

from retail_pipeline import load, transform


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "Invoice":     [489434, "C489449", 489435, 489436, 489434],
        "StockCode":   [85048, "22087", "POST", 21232, 85048],
        "Description": ["LIGHT", None, "POSTAGE", None, "LIGHT"],
        "Quantity":    [12, -12, 1, 6, 12],
        "InvoiceDate": ["2009-12-01 07:45"] * 5,
        "Price":       [6.95, 2.95, 18.0, 0.0, 6.95],
        "Customer ID": [13085.0, 16321.0, None, 13085.0, 13085.0],
        "Country":     ["United Kingdom"] * 5,
    })


def test_exact_duplicates_are_removed():
    assert len(transform.remove_duplicates(sample())) == 4


def test_mixed_types_become_strings():
    df = transform.fix_types(sample())
    assert df["Invoice"].map(type).eq(str).all()
    assert df["StockCode"].map(type).eq(str).all()


def test_cancelled_orders_are_flagged_not_deleted():
    df = transform.add_flags(transform.fix_types(sample()))
    assert df["IsCancelled"].tolist() == [False, True, False, False, False]
    assert len(df) == 5


def test_valid_sale_excludes_cancelled_nonproduct_and_zero_price():
    df = transform.add_flags(transform.fix_types(sample()))
    # row 2 cancelled, row 3 postage (non-product), row 4 zero price
    assert df["IsValidSale"].tolist() == [True, False, False, False, True]


def test_missing_descriptions_are_filled():
    df = transform.fill_descriptions(transform.fix_types(sample()))
    assert df["Description"].isnull().sum() == 0
    assert (df["Description"] == "Unknown Product").sum() == 2


def test_description_recovered_from_same_stockcode():
    df = pd.DataFrame({"StockCode": ["A1", "A1"], "Description": ["MUG", None]})
    assert transform.fill_descriptions(df)["Description"].tolist() == ["MUG", "MUG"]


def test_total_price():
    df = transform.add_total_price(sample())
    assert df.loc[0, "TotalPrice"] == 12 * 6.95


def test_full_transform_runs_end_to_end():
    df = transform.transform(sample())
    assert {"IsCancelled", "IsNonProduct", "IsValidSale", "TotalPrice"} <= set(df.columns)
    assert len(df) == 4


def test_dim_customer_has_one_row_per_customer():
    dim = load.build_dim_customer(transform.transform(sample()))
    assert dim["CustomerID"].is_unique
    assert set(dim["CustomerID"]) == {13085, 16321}


def test_dim_date_key_format():
    dim = load.build_dim_date(transform.transform(sample()))
    assert dim["DateKey"].tolist() == [20091201]
