from __future__ import annotations
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
from datetime import date
import plotly.graph_objects as go
from scripts.data_loader import get_all_datasets, apply_global_filters
from scripts.ui_utils import (
    init_session_state,
    metric_card,
    dataframe_download,
    kpi_color,
)

st.set_page_config(page_title="Promotion Performance Dashboard", layout="wide")

# Inject CSS
with open(os.path.join("assets", "style.css"), "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_session_state()


@st.cache_data(show_spinner=False)
def load_data():
    return get_all_datasets()


datasets = load_data()
# Unpack
campaigns = datasets.get("campaign_data", pd.DataFrame())
products = datasets.get("product_data", pd.DataFrame())
stores = datasets.get("stores_data", pd.DataFrame())
events = datasets.get("event_data", pd.DataFrame())
clean_revenue = datasets.get("clean_revenue", pd.DataFrame())
city_sales = datasets.get("city_sales", pd.DataFrame())
clean_all = datasets.get("clean_all", pd.DataFrame())


# ------- TOP-LEVEL FILTERS -------
st.markdown("## 📊 Promotion Performance Dashboard")

# Define columns
col1, col2, col3, col4, col5, col6 = st.columns(6)


# Helper to safely get unique options
def safe_unique(series):
    if series is None or series.empty:
        return []
    return sorted(series.dropna().unique().tolist())


# Initialize session_state defaults only once
default_state = {
    "campaigns": [],
    "categories": [],
    "products": [],
    "promo_types": [],
    "cities": [],
    "kpi_focus": "Revenue",
}
for key, default in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = default


# -----------------------------
# Build filters from clean_all
# -----------------------------

with col1:
    st.session_state["campaigns"] = st.multiselect(
        "🎯 Campaign",
        options=safe_unique(clean_all.get("campaign_id", pd.Series())),
        default=st.session_state["campaigns"],
        help="Select one or more campaigns to filter data.",
    )

with col2:
    st.session_state["categories"] = st.multiselect(
        "📦 Category",
        options=safe_unique(clean_all.get("category", pd.Series())),
        default=st.session_state["categories"],
        help="Filter data based on product category.",
    )

with col3:
    st.session_state["products"] = st.multiselect(
        "🛍️ Product",
        options=safe_unique(clean_all.get("product_name", pd.Series())),
        default=st.session_state["products"],
        help="Filter data by product names.",
    )

with col4:
    st.session_state["promo_types"] = st.multiselect(
        "🏷️ Promo Type",
        options=safe_unique(clean_all.get("promo_type", pd.Series())),
        default=st.session_state["promo_types"],
        help="Choose the type of promotion (e.g., Discount, Combo).",
    )

with col5:
    st.session_state["cities"] = st.multiselect(
        "🌆 City",
        options=safe_unique(clean_all.get("city", pd.Series())),
        default=st.session_state["cities"],
        help="Filter sales data by city.",
    )

with col6:
    st.session_state["kpi_focus"] = st.radio(
        "📈 KPI Focus",
        ["Revenue", "Units"],
        index=["Revenue", "Units"].index(st.session_state["kpi_focus"]),
        horizontal=True,
        help="Select the main performance metric to focus on.",
    )


# ------- SIDEBAR -------


# ------- CENTER + RIGHT PANELS -------
center, right = st.columns([2, 1])

# -------------------------------
# 1️⃣ Initialize default session_state keys
# -------------------------------
default_state = {
    "campaigns": [],
    "categories": [],
    "products": [],
    "promo_types": [],
    "cities": [],
    "kpi_focus": "Revenue",
    "discount_range": (0.0, 1.0),
    "price_range": (0.0, 1000.0),
    "inc_rev_range": (0.0, 100000.0),
    "ir_range": (0.0, 1.0),
    "show_before": True,
    "show_after": True,
    "positive_only": False,
    "normalize_store": False,
    "top_n": 10,
    "selected_city": "All",
}

for key, default in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = default
# -------------------------------------------------------------------------------------------------------------
# Apply global filters to dataframes where applicable
filtered_clean_revenue = apply_global_filters(clean_revenue, dict(st.session_state))
filtered_city_sales = apply_global_filters(city_sales, dict(st.session_state))
filtered_clean_all = apply_global_filters(clean_all, dict(st.session_state))

with right:
    st.subheader("KPI Summary")

    # City-scoped dataframe
    scope_df = filtered_clean_all
    # Apply city filter
    focus_city = st.session_state.get("selected_city")
    if focus_city and focus_city != "All" and "city" in scope_df.columns:
        scope_df = scope_df[scope_df["city"] == focus_city]

    # Apply category filter
    selected_categories = st.session_state.get("categories", [])
    if selected_categories:
        scope_df = scope_df[scope_df["category"].isin(selected_categories)]

    kpi_focus = st.session_state.get("kpi_focus", "Revenue")

    if kpi_focus == "Revenue":
        total_before = scope_df["revenue_before_promo"].sum()
        total_after = scope_df["revenue_after_promo"].sum()
        ir_percent = (
            ((total_after - total_before) / total_before * 100) if total_before else 0
        )

        metric_card("Revenue Before", f"₹{total_before:,.0f}")
        metric_card("Revenue After", f"₹{total_after:,.0f}")
        metric_card("Incremental Revenue %", f"{ir_percent:.1f}%")

    elif kpi_focus == "Units":
        total_units_before = scope_df["quantity_sold (before_promo)"].sum()
        total_units_after = scope_df["quantity_sold (after_promo)"].sum()
        isu_percent = (
            ((total_units_after - total_units_before) / total_units_before * 100)
            if total_units_before
            else 0
        )

        metric_card("Units Before", f"{total_units_before:,}")
        metric_card("Units After", f"{total_units_after:,}")
        metric_card("Incremental Sold Units %", f"{isu_percent:.1f}%")

# dont touchh
total_before = scope_df["revenue_before_promo"].sum()
total_after = scope_df["revenue_after_promo"].sum()
ir_percent = (total_after - total_before) / total_before * 100
total_units_before = scope_df["quantity_sold (before_promo)"].sum()
total_units_after = scope_df["quantity_sold (after_promo)"].sum()
isu_percent = (total_units_after - total_units_before) / total_units_before * 100

# -----------------------------------------


# Optional: Filter by selected campaigns/products
df_filtered = clean_all.copy()
if "campaigns" in st.session_state and st.session_state["campaigns"]:
    df_filtered = df_filtered[
        df_filtered["campaign_id"].isin(st.session_state["campaigns"])
    ]
if "products" in st.session_state and st.session_state["products"]:
    df_filtered = df_filtered[
        df_filtered["product_name"].isin(st.session_state["products"])
    ]


y_values = [total_before, total_after]
y_text = [f"₹{total_before:,.0f}", f"₹{total_after:,.0f}"]
y_label = "Revenue (₹)"
ir_label = "Incremental Revenue %"
ir_value = ir_percent

y_values = [total_units_before, total_units_after]
y_text = [f"{total_units_before:,}", f"{total_units_after:,}"]
y_label = "Units Sold"
ir_label = "Incremental Sold Units %"
ir_value = isu_percent

# -------------------------
# KPI focus (Revenue or Units) GRAPHGRAPHGRAPHGRAPHGRAPHGRAPHGRAPHGRAPHGRAPH
# -------------------------

fig_kpi = go.Figure()

# Determine values from KPI summary
if kpi_focus == "Revenue":
    y_values = [total_before, total_after]
    y_text = [f"₹{total_before:,.0f}", f"₹{total_after:,.0f}"]
    y_label = "Revenue (₹)"
    ir_label = "Incremental Revenue %"
    ir_value = ir_percent

elif kpi_focus == "Units":
    y_values = [total_units_before, total_units_after]
    y_text = [f"{total_units_before:,}", f"{total_units_after:,}"]
    y_label = "Units Sold"
    ir_label = "Incremental Sold Units %"
    ir_value = isu_percent


# -------------------------
# Plotly chart
# -------------------------
# Bars
fig_kpi.add_trace(
    go.Bar(
        x=["Before", "After"],
        y=y_values,
        name=y_label,
        text=y_text,
        textposition="auto",
        marker_color=["green", "orange"],
    )
)

# IR% / ISU% line
fig_kpi.add_trace(
    go.Scatter(
        x=["Before", "After"],
        y=[0, ir_value],
        name=ir_label,
        yaxis="y2",
        text=[None, f"{ir_value:.1f}%"],
        textposition="top center",
        mode="lines+markers+text",
        line=dict(color="red", width=3, dash="dash"),
    )
)

fig_kpi.update_layout(
    title=f"{kpi_focus} Before vs After Promo and {ir_label}",
    yaxis=dict(title=y_label),
    yaxis2=dict(title=ir_label, overlaying="y", side="right", showgrid=False),
    legend=dict(y=1.1, orientation="h"),
    template="plotly_white",
    width=700,
    height=450,
)

st.plotly_chart(fig_kpi, use_container_width=True)




# -------------------------------
# TREEMAP: Hierarchical Performance Breakdown
# -------------------------------
st.subheader("Treemap View")

if not filtered_clean_all.empty and set(
    ["campaign_id", "product_name", "promo_type", "incremental_margin%"]
).issubset(filtered_clean_all.columns):

    treemap_df = filtered_clean_all.copy()

    # Apply city-level filter if selected
    if focus_city and focus_city != "All" and "city" in treemap_df.columns:
        treemap_df = treemap_df[treemap_df["city"] == focus_city]

    # KPI Focus switch (Revenue / Units)
    kpi_focus = st.session_state.get("kpi_focus", "Revenue")

    if kpi_focus == "Revenue":
        value_col = "revenue_after_promo"
        title_metric = "Revenue (₹)"
    else:
        value_col = "quantity_sold (after_promo)"
        title_metric = "Units Sold"

    # Ensure no missing values
    treemap_df = treemap_df.dropna(subset=[value_col, "incremental_margin%"])

    # Build Treemap
    fig_treemap = px.treemap(
        treemap_df,
        path=["campaign_id", "product_name", "promo_type"],
        values=value_col,
        color="incremental_margin%",
        color_continuous_scale="RdYlGn",
        hover_data={
            "incremental_margin%": ":.2f",
            value_col: ":,.0f",
        },
        title=f"Treemap — {title_metric} by Campaign → Product → Promo Type",
    )

    # Clean layout
    fig_treemap.update_layout(
        margin=dict(t=60, l=0, r=0, b=0),
        height=500,
        template="plotly_white",
    )

    st.plotly_chart(fig_treemap, use_container_width=True)

else:
    st.caption(
        "Required columns missing for Treemap: 'campaign_id', 'product_name', 'promo_type', 'incremental_margin%'."
    )


st.caption(
    """
🧩 **Treemap View — Campaign, Product & Promo Insights**

This chart shows how **Revenue (₹)** is spread across **Campaigns**, **Products**, and **Promo Types**.  
Each box represents a product — the **bigger the box, the higher the revenue**.  
Colors show **profitability (Incremental Margin %)**:
- 🟩 Green = High margin  
- 🟨 Yellow = Moderate  
- 🟥 Red = Low or negative  

For example, **Product P14** under **CAMP_SAN_01** is dark green with a **92.14% margin**,  
meaning it performed very well with the **BOGOF** offer.
"""
)


# GEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO

# Prepare data for visuals using filtered data
map_df = filtered_city_sales.copy()
if not map_df.empty:
    # Decide color metric by KPI
    kpi = st.session_state.get("kpi_focus", "Revenue").lower()
    color_col = (
        "revenue_after_promo"
        if "rev" in kpi
        else (
            "total_quantity_sold"
            if "unit" in kpi
            else (
                "margin_efficiency"
                if "margin" in kpi and "margin_efficiency" in map_df.columns
                else "total_quantity_sold"
            )
        )
    )

with center:
    st.subheader("Geospatial Performance")
    # Controls for map type before rendering
    map_mode = st.radio(
        "Map Mode", ["Bubbles", "Heatmap"], horizontal=True, key="map_mode"
    )

    if map_df.empty or not set(["lat", "lng"]).issubset(map_df.columns):
        st.info("City map requires 'lat' and 'lng' columns in city_sales.")
    else:
        view_state = pdk.ViewState(
            latitude=float(map_df["lat"].mean()),
            longitude=float(map_df["lng"].mean()),
            zoom=3,
        )
        layers = []
        if map_mode == "Bubbles":
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=map_df,
                    get_position="[lng, lat]",
                    get_radius="total_quantity_sold",
                    radius_scale=0.5,
                    get_fill_color="[50, 180, 120, 160]",
                    pickable=True,
                    auto_highlight=True,
                )
            )
        else:
            layers.append(
                pdk.Layer(
                    "HeatmapLayer",
                    data=map_df,
                    get_position="[lng, lat]",
                    get_weight="total_quantity_sold",
                    radius_pixels=60,
                )
            )
        st.pydeck_chart(
            pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip={"text": "{city}\nQty: {total_quantity_sold}"},
            )
        )
