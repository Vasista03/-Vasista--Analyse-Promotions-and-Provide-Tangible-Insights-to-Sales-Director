from __future__ import annotations
import os
import pandas as pd
import streamlit as st
from typing import Dict, Optional
import numpy as np

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))

CSV_ALIASES = {
    "campaign_data": "dim_campaigns.csv",
    "product_data": "dim_products.csv",
    "stores_data": "dim_stores.csv",
    "event_data": "fact_events.csv",
    "clean_revenue": "clean_revenue.csv",
    "city_sales": "city_sales.csv",
    "clean_all": "clean_all.csv",
}

EXPECTED_SCHEMAS: Dict[str, list[str]] = {
    "campaign_data": ["campaign_id", "campaign_name", "start_date", "end_date"],
    "product_data": ["product_code", "product_name", "category"],
    "stores_data": ["store_id", "city"],
    "event_data": [
        "event_id",
        "store_id",
        "campaign_id",
        "product_code",
        "base_price",
        "promo_type",
        "quantity_sold(before_promo)",
        "quantity_sold(after_promo)",
    ],
    "clean_revenue": [
        "event_id",
        "store_id",
        "campaign_id",
        "product_code",
        "base_price",
        "promo_type",
        "quantity_sold (before_promo)",
        "quantity_sold (after_promo)",
        "city",
        "total_quantity_sold",
        "product_name",
        "promo_discount",
        "revenue_before_promo",
        "revenue_after_promo",
    ],
    "city_sales": [
        "city",
        "location",
        "total_quantity_sold",
        "lat",
        "lng",
        "quantity_before_promo",
        "quantity_after_promo",
    ],
    "clean_all": [
        "event_id",
        "store_id",
        "campaign_id",
        "product_code",
        "base_price",
        "promo_type",
        "quantity_sold (before_promo)",
        "quantity_sold (after_promo)",
        "city",
        "total_quantity_sold",
        "product_name",
        "promo_discount",
        "revenue_before_promo",
        "revenue_after_promo",
        "category",
        "ir%",
        "inc_units",
        "isu_percent",
        "inc_revenue",
        "ir_percent_calc",
        "rev_per_discount_unit",
        "rev_per_discount_amount",
        "isu%",
        "promo_category",
        "incremental_revenue",
        "margin_efficiency",
        "incremental_margin%",
        "before_rev",
        "before_qty",
        "after_qty",
        "ir_row",
    ],
}


@st.cache_data(show_spinner=False)
def load_csv(alias: str, dtype: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Load CSV by alias from DATA_DIR with caching and light validation."""
    if alias not in CSV_ALIASES:
        raise KeyError(f"Unknown dataset alias: {alias}")
    filename = CSV_ALIASES[alias]
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        st.warning(f"Missing data file: {filename} under {DATA_DIR}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=dtype  )
    except Exception as exc:
        st.error(f"Failed reading {filename}: {exc}")
        return pd.DataFrame()

    # Parse date columns if present
    for col in ("start_date", "end_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Normalize column names to strip whitespace variants
    df.columns = [c.strip() for c in df.columns]

    # Attempt to harmonize common alternative column names
    rename_map = {
        "quantity_sold(before_promo)": "quantity_sold (before_promo)",
        "quantity_sold(after_promo)": "quantity_sold (after_promo)",
        "Incremental Revenue": "incremental_revenue",
        "IR%": "ir%",
        "ISU%": "isu%",
        "incremental_margin %": "incremental_margin%",
    }
    columns_lower = {c.lower(): c for c in df.columns}
    for k, v in list(rename_map.items()):
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)

    return df


def get_all_datasets() -> Dict[str, pd.DataFrame]:
    return {alias: load_csv(alias) for alias in CSV_ALIASES}


def apply_global_filters(df: pd.DataFrame, state: dict) -> pd.DataFrame:
    """
    Apply global Streamlit filters (campaign, category, product, promo_type, city)
    to a given dataframe.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to filter.
    state : dict
        st.session_state containing selected filter values.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe.
    """

    if df is None or df.empty:
        return df

    # Map of dataframe column -> corresponding session_state key
    filter_map = {
        "campaign_id": "campaigns",
        "category": "categories",
        "product_code": "products",
        "promo_type": "promo_types",
        "city": "cities",
    }

    filters = []
    for col, key in filter_map.items():
        # Use .get() to avoid KeyError if missing in session_state
        selected_values = state.get(key, [])
        if col in df.columns and selected_values:
            filters.append(df[col].isin(selected_values))

    # Combine all filters safely
    if filters:
        df = df[np.logical_and.reduce(filters)]

    return df

    # Date range filter using campaign dates when available
    start = state.get("date_start")
    end = state.get("date_end")
    if (
        start is not None
        and end is not None
        and {"start_date", "end_date"}.issubset(df.columns)
    ):
        filters.append((df["start_date"] <= end) & (df["end_date"] >= start))

    if not filters:
        return df

    mask = filters[0]
    for f in filters[1:]:
        mask &= f
    return df[mask]
