from __future__ import annotations
import streamlit as st
import pandas as pd
from scripts.data_loader import get_all_datasets
from scripts.ui_utils import init_session_state, dataframe_download

st.set_page_config(page_title="Data Explorer", layout="wide")
init_session_state()

datasets = get_all_datasets()

st.markdown("## 🧭 Data Explorer")

alias = st.selectbox("Dataset", list(datasets.keys()))
df = datasets.get(alias, pd.DataFrame())

if df is None or df.empty:
    st.info("No data loaded for selected dataset.")
else:
    st.dataframe(df, use_container_width=True)
    dataframe_download(df, f"{alias}.csv")
st.caption("Tip: Place your CSVs under /data named as per aliases in scripts/data_loader.py")
