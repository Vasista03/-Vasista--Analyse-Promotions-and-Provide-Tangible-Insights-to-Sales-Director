
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

COLOR_MAP = {
    "revenue": "#2ecc71",
    "units": "#9b59b6",
    "margin": "#3498db",
    "ir%": "#f39c12",
}


def init_session_state():
    defaults: Dict[str, Any] = {
        "campaigns": [],
        "categories": [],
        "products": [],
        "promo_types": [],
        "cities": [],
        "kpi_focus": "Revenue",
        "compare_mode": False,
        "date_start": None,
        "date_end": None,
        "annotations": {},
        "selected_city": None,
        "top_n": 10,
        "discount_range": (0.0, 1.0),
        "price_range": (0.0, 1_000.0),
        "ir_range": (0.0, 1.0),
        "inc_rev_range": (0.0, 10_000.0),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def kpi_color(kpi: str) -> str:
    key = kpi.strip().lower()
    if key.startswith("rev"):
        return COLOR_MAP["revenue"]
    if key.startswith("mar"):
        return COLOR_MAP["margin"]
    if key.startswith("ir"):
        return COLOR_MAP["ir%"]
    return "#666"


def metric_card(label: str, value: Any, delta: Optional[Any] = None, help_text: Optional[str] = None):
    with st.container():
        st.markdown(f"<div class='kpi-card'><div class='label'>{label}</div><div class='value'>{value}</div></div>", unsafe_allow_html=True)
        if delta is not None:
            st.caption(f"Δ {delta}")
        if help_text:
            st.caption(help_text)


def dataframe_download(df: pd.DataFrame, filename: str):
    if df is None or df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Export CSV", data=csv, file_name=filename, mime="text/csv")