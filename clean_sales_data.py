"""
Clean a messy sales dataset: missing values, dates, duplicates, and category text.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean sales CSV: Price/Date nulls, date format, duplicate Transaction IDs, Category casing."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("sales_raw.csv"),
        help="Path to input CSV (default: sales_raw.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("Cleaned_Data.csv"),
        help="Path for cleaned CSV (default: Cleaned_Data.csv)",
    )
    return parser.parse_args()


def load_sales(path: Path) -> pd.DataFrame:
    if not path.is_file():
        print(f"Error: input file not found: {path.resolve()}", file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(path)


def normalize_category(series: pd.Series) -> pd.Series:
    """Strip whitespace, title-case, treat blanks as missing."""
    s = series.astype("string").str.strip().str.title()
    blank = s.isna() | (s.str.len() == 0)
    return s.mask(blank)


def clean_sales(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Return cleaned dataframe and a dict of intermediate stats for reporting.
    """
    stats: dict = {}
    required = ["Transaction ID", "Price", "Date", "Category"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        print(
            f"Error: CSV must include columns {required}. Missing: {missing_cols}",
            file=sys.stderr,
        )
        sys.exit(1)

    working = df.copy()

    # --- Price: numeric + missing handling ---
    price_before_na = working["Price"].isna().sum()
    working["Price"] = pd.to_numeric(working["Price"], errors="coerce")
    price_coerced_na = working["Price"].isna().sum()
    median_price = working["Price"].median()
    if pd.isna(median_price):
        median_price = 0.0
    filled = working["Price"].isna().sum()
    working["Price"] = working["Price"].fillna(median_price)
    stats["price_missing_initial"] = int(price_before_na)
    stats["price_invalid_or_missing_after_coerce"] = int(price_coerced_na)
    stats["price_filled_with_median"] = int(filled)
    stats["median_price_used"] = float(median_price)

    # --- Date: parse + drop unparseable / missing ---
    date_before_na = working["Date"].isna().sum()
    working["Date"] = pd.to_datetime(working["Date"], errors="coerce", dayfirst=False)
    rows_before_drop = len(working)
    working = working.dropna(subset=["Date"])
    rows_dropped_bad_date = rows_before_drop - len(working)
    working["Date"] = working["Date"].dt.strftime("%Y-%m-%d")
    stats["date_missing_initial"] = int(date_before_na)
    stats["date_unparseable_or_missing_dropped"] = int(rows_dropped_bad_date)

    # --- Duplicates on Transaction ID ---
    dup_mask = working.duplicated(subset=["Transaction ID"], keep=False)
    duplicate_id_rows_before = int(dup_mask.sum())
    unique_dup_ids = working.loc[dup_mask, "Transaction ID"].nunique()
    rows_before_dedup = len(working)
    working = working.drop_duplicates(subset=["Transaction ID"], keep="first")
    stats["rows_duplicate_transaction_ids_removed"] = rows_before_dedup - len(working)
    stats["rows_touched_by_duplicate_groups"] = duplicate_id_rows_before
    stats["transaction_ids_with_duplicates"] = int(unique_dup_ids)

    # --- Category capitalization ---
    working["Category"] = normalize_category(working["Category"]).fillna("Unknown")

    stats["final_row_count"] = len(working)
    return working, stats


def print_before_after_summary(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    stats: dict,
) -> None:
    n0, n1 = len(df_before), len(df_after)

    invalid_price_before = int(pd.to_numeric(df_before["Price"], errors="coerce").isna().sum())
    invalid_date_before = int(pd.to_datetime(df_before["Date"], errors="coerce").isna().sum())
    dup_rows_before = int(df_before.duplicated(subset=["Transaction ID"], keep=False).sum())

    invalid_price_after = int(pd.to_numeric(df_after["Price"], errors="coerce").isna().sum())
    invalid_date_after = int(pd.to_datetime(df_after["Date"], errors="coerce").isna().sum())
    dup_rows_after = int(df_after.duplicated(subset=["Transaction ID"], keep=False).sum())

    print()
    print("=" * 60)
    print(" BEFORE vs AFTER - Sales data cleaning summary")
    print("=" * 60)
    print(f"  Rows                          {n0:>8}  ->  {n1:>8}")
    print(f"  Invalid / missing Price       {invalid_price_before:>8}  ->  {invalid_price_after:>8}")
    print(f"  Invalid / missing Date        {invalid_date_before:>8}  ->  {invalid_date_after:>8}")
    print(f"  Rows in duplicate ID groups   {dup_rows_before:>8}  ->  {dup_rows_after:>8}")
    print()
    print("  Details:")
    print(f"    - Price: filled {stats['price_filled_with_median']} value(s) with median {stats['median_price_used']:.2f}")
    print(f"    - Date: dropped {stats['date_unparseable_or_missing_dropped']} row(s) with missing/unparseable dates")
    print(f"    - Dates standardized to YYYY-MM-DD")
    print(f"    - Removed {stats['rows_duplicate_transaction_ids_removed']} duplicate row(s) (kept first per Transaction ID)")
    print(f"    - Category: stripped and title-cased; empty -> 'Unknown'")
    print("=" * 60)
    print()


def main() -> None:
    args = parse_args()
    df_raw = load_sales(args.input)
    df_clean, stats = clean_sales(df_raw)
    df_clean.to_csv(args.output, index=False)
    print(f"Wrote cleaned data to: {args.output.resolve()}")
    print_before_after_summary(df_raw, df_clean, stats)


if __name__ == "__main__":
    main()
