"""CSV/XLSX parser and data cleaner.

Handles:
- Date format detection and normalization
- Missing value handling
- Type coercion (quantity, price → float)
- Revenue computation (quantity × unit_price when revenue column absent)
- Duplicate row removal
- Cleaning report generation
"""

import pandas as pd
import json
from datetime import datetime


# Columns we try to find in uploads (case-insensitive fuzzy matching)
EXPECTED_COLUMNS = {
    'date': ['date', 'order_date', 'transaction_date', 'sale_date', 'invoice_date'],
    'product': ['product', 'product_name', 'item', 'item_name', 'sku'],
    'category': ['category', 'product_category', 'dept', 'department'],
    'quantity': ['quantity', 'qty', 'units', 'units_sold', 'quantity_sold'],
    'unit_price': ['unit_price', 'price', 'unit_cost', 'selling_price', 'rate'],
    'revenue': ['revenue', 'total', 'amount', 'sales', 'total_revenue', 'total_amount'],
    'region': ['region', 'location', 'city', 'state', 'area', 'territory', 'store'],
    'customer_id': ['customer_id', 'customer', 'cust_id', 'client_id', 'buyer_id'],
    'cost': ['cost', 'cogs', 'cost_of_goods', 'unit_cost', 'total_cost'],
}


def _match_columns(df_columns):
    """Map DataFrame columns to expected schema using fuzzy matching."""
    mapping = {}
    df_cols_lower = {c.lower().strip(): c for c in df_columns}

    for target, candidates in EXPECTED_COLUMNS.items():
        for candidate in candidates:
            if candidate in df_cols_lower:
                mapping[target] = df_cols_lower[candidate]
                break

    return mapping


def _parse_dates(series):
    """Attempt to parse a Series as dates with multiple format detection."""
    for fmt in [None, '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
                '%d-%m-%Y', '%m-%d-%Y', '%B %d, %Y', '%d %B %Y']:
        try:
            parsed = pd.to_datetime(series, format=fmt, dayfirst=('d' == (fmt or '')[1:2]))
            if parsed.notna().sum() > len(series) * 0.5:
                return parsed
        except (ValueError, TypeError):
            continue
    # Final fallback — let pandas infer
    return pd.to_datetime(series, errors='coerce', infer_datetime_format=True)


def parse_and_clean(filepath, industry_type='generic'):
    """Parse a CSV or XLSX file, clean it, and return (DataFrame, cleaning_report_dict).

    The returned DataFrame has normalized column names matching the SalesRecord schema.
    """
    report = {
        'original_rows': 0,
        'final_rows': 0,
        'duplicates_removed': 0,
        'nulls_filled': {},
        'columns_mapped': {},
        'columns_not_found': [],
        'revenue_computed': False,
        'date_parse_failures': 0,
        'warnings': [],
    }

    # --- Read file ---
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext in ('xlsx', 'xls'):
        df = pd.read_excel(filepath, engine='openpyxl')
    else:
        # Try common encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            df = pd.read_csv(filepath, encoding='utf-8', errors='replace')

    report['original_rows'] = len(df)

    if len(df) > 100000:
        raise ValueError("File exceeds maximum limit of 100,000 rows.")

    if df.empty:
        raise ValueError("File is empty or has no data rows.")

    # --- Column mapping ---
    col_map = _match_columns(df.columns)
    report['columns_mapped'] = {k: v for k, v in col_map.items()}

    missing_required = []
    if 'date' not in col_map:
        missing_required.append('date')
    if 'revenue' not in col_map and ('quantity' not in col_map or 'unit_price' not in col_map):
        missing_required.append('revenue (or quantity + unit_price)')

    report['columns_not_found'] = missing_required
    if missing_required:
        raise ValueError(f"Missing required columns: {', '.join(missing_required)}")

    # Rename columns to our standard schema
    rename_map = {v: k for k, v in col_map.items()}
    df = df.rename(columns=rename_map)

    # --- Date parsing ---
    if 'date' in df.columns:
        df['date'] = _parse_dates(df['date'])
        date_nulls = df['date'].isna().sum()
        if date_nulls > 0:
            if date_nulls > len(df) * 0.5:
                raise ValueError("Date column parsing failed for more than 50% of rows. Ensure dates are valid.")
            report['date_parse_failures'] = int(date_nulls)
            df = df.dropna(subset=['date'])

    # --- Numeric coercion ---
    for col in ['quantity', 'unit_price', 'revenue', 'cost']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Revenue computation ---
    if 'revenue' not in df.columns or df['revenue'].isna().all():
        if 'quantity' in df.columns and 'unit_price' in df.columns:
            df['revenue'] = df['quantity'] * df['unit_price']
            report['revenue_computed'] = True
    elif df['revenue'].isna().any():
        # Fill missing revenue where quantity & price exist
        mask = df['revenue'].isna() & df['quantity'].notna() & df['unit_price'].notna()
        df.loc[mask, 'revenue'] = df.loc[mask, 'quantity'] * df.loc[mask, 'unit_price']
        if mask.sum() > 0:
            report['revenue_computed'] = True

    # --- Null handling ---
    fill_defaults = {
        'product': 'Unknown',
        'category': 'Uncategorized',
        'region': 'Unknown',
        'customer_id': 'anonymous',
    }
    for col, default in fill_defaults.items():
        if col in df.columns:
            null_count = int(df[col].isna().sum())
            if null_count > 0:
                df[col] = df[col].fillna(default)
                report['nulls_filled'][col] = null_count

    # --- Duplicate removal ---
    before_dedup = len(df)
    df = df.drop_duplicates()
    report['duplicates_removed'] = before_dedup - len(df)

    # --- Keep only recognized columns ---
    schema_cols = list(EXPECTED_COLUMNS.keys())
    keep = [c for c in schema_cols if c in df.columns]
    df = df[keep]

    report['final_rows'] = len(df)

    return df, report
