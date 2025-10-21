from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scripts.data_loader import get_all_datasets, apply_global_filters
from scripts.ui_utils import init_session_state
import networkx as nx

st.set_page_config(page_title="Advanced Analytics", layout="wide")
st.subheader("Parallel Categories: Campaign → Promo Type → Category")


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


filtered_clean_revenue = apply_global_filters(clean_revenue, dict(st.session_state))
filtered_city_sales = apply_global_filters(city_sales, dict(st.session_state))
filtered_clean_all = apply_global_filters(clean_all, dict(st.session_state))


# Check required columns
required_cols = ["campaign_id", "promo_type", "category", "incremental_margin%", "city"]
if (
    set(required_cols).issubset(filtered_clean_all.columns)
    and not filtered_clean_all.empty
):

    # Optional filters
    with st.expander("🔍 Advanced Filters"):
        cities = ["All"] + sorted(filtered_clean_all["city"].dropna().unique().tolist())
        selected_city = st.selectbox("🌆 Select City", cities, index=0)
        min_count = st.slider("📊 Minimum Records per Combination", 1, 100, 10, step=5)

    # Apply filters
    df_para = filtered_clean_all.copy()
    if selected_city != "All":
        df_para = df_para[df_para["city"] == selected_city]

    # Count occurrences per combination
    combo_counts = (
        df_para.groupby(["campaign_id", "promo_type", "category"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )

    # Merge count back to main data
    df_para = pd.merge(
        df_para, combo_counts, on=["campaign_id", "promo_type", "category"], how="left"
    )

    # Apply threshold
    df_para = df_para[df_para["count"] >= min_count]

    # Build Plotly Parallel Categories chart
    fig_para = px.parallel_categories(
        df_para,
        dimensions=["campaign_id", "promo_type", "category"],
        color="incremental_margin%",
        color_continuous_scale="RdYlGn",
        labels={
            "campaign_id": "Campaign",
            "promo_type": "Promo Type",
            "category": "Product Category",
            "incremental_margin%": "Incremental Margin (%)",
        },
        title="Parallel Categories — Campaign → Promo Type → Category",
    )

    # Layout tuning
    fig_para.update_layout(
        height=600,
        margin=dict(t=60, l=20, r=20, b=20),
        template="plotly_white",
    )

    st.plotly_chart(fig_para, use_container_width=True)

else:
    st.warning(
        "⚠️ Missing columns: Please ensure 'campaign_id', 'promo_type', 'category', 'incremental_margin%', and 'city' exist in clean_all."
    )

st.caption(
    """
This chart shows how **campaigns**, **promo types**, and **product categories** are linked, 
and how each performed in terms of **profit (Incremental Margin %)**.

- 🟩 **Green lines = profit**  
- 🟥 **Red lines = loss**

Each line shows one promotion’s path from **Campaign → Offer Type → Product Category**.

**Example:**  
“DIWALI” with **BOGOF** on **Home Care** made good profit (green),  
while **25% OFF** under “P_SAN_01” on **Personal Care** gave low profit (red).

This helps quickly see **which offers worked best** and **which didn’t**.
"""
)


st.subheader("Violin Plot: Incremental Margin % by Promo Type")

required_cols = {"promo_type", "incremental_margin%"}
if not required_cols.issubset(filtered_clean_all.columns):
    st.warning(f"Missing columns: {required_cols - set(filtered_clean_all.columns)}")
else:
    # Optional: Filter by selected promo types
    promo_options = filtered_clean_all["promo_type"].dropna().unique().tolist()
    selected_promos = st.multiselect(
        "Select Promo Types", options=promo_options, default=promo_options
    )

    df_plot = filtered_clean_all[filtered_clean_all["promo_type"].isin(selected_promos)]

    # Choose metric to plot: incremental_margin%
    metric = st.radio("Select Metric", ["incremental_margin%"], horizontal=True)

    # Toggle to show points (beeswarm)
    show_points = st.checkbox("Show individual points", value=True)

    fig_violin = px.violin(
        df_plot,
        x="promo_type",
        y=metric,
        box=True,  # Show boxplot inside violin
        points="all" if show_points else False,  # Show individual points
        color="promo_type",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hover_data=["campaign_id", "product_code", "city"],
        title=f"Distribution of {metric} per Promo Type",
    )

    fig_violin.update_layout(
        yaxis_title=metric,
        xaxis_title="Promo Type",
        showlegend=False,
        template="plotly_white",
        height=500,
    )

    st.plotly_chart(fig_violin, use_container_width=True)

st.caption(
    """
This chart shows how **Incremental Margin %** varies for each **Promo Type**.

- Each shape shows how profits are spread across all promotions of that type.  
- Wider parts mean more promotions with similar results.

**Example:**  
**BOGOF** offers mostly gave **high margins (profitable)**,  
while **50% OFF** and **25% OFF** often led to **low or negative margins**.

It helps see **which promo types perform better** and **which tend to lose profit**.
"""
)


st.subheader("Sankey: Campaign → Promo Type → Category → Revenue/Units")

# Ensure required columns exist
required_cols = {
    "campaign_id",
    "promo_type",
    "category",
    "revenue_after_promo",
    "total_quantity_sold",
}
if not required_cols.issubset(filtered_clean_all.columns):
    st.warning(f"Missing columns: {required_cols - set(filtered_clean_all.columns)}")
else:
    df_sankey = filtered_clean_all.copy()

    # Metric selection: Revenue or Units
    metric = st.radio("Select Metric", ["Revenue", "Units"], horizontal=True)
    value_col = "revenue_after_promo" if metric == "Revenue" else "total_quantity_sold"

    # Min threshold slider
    min_value = st.slider(
        f"Minimum {metric} to display",
        min_value=0,
        max_value=int(df_sankey[value_col].max()),
        value=0,
        step=100,
    )

    # Filter rows by threshold
    df_sankey = df_sankey[df_sankey[value_col] >= min_value]

    # Build node list
    campaigns = df_sankey["campaign_id"].unique().tolist()
    promos = df_sankey["promo_type"].unique().tolist()
    categories = df_sankey["category"].unique().tolist()
    labels = campaigns + promos + categories
    label_indices = {label: i for i, label in enumerate(labels)}

    # Build links: Campaign -> Promo Type
    df_links1 = (
        df_sankey.groupby(["campaign_id", "promo_type"])[value_col].sum().reset_index()
    )
    source1 = df_links1["campaign_id"].map(label_indices)
    target1 = df_links1["promo_type"].map(label_indices)
    value1 = df_links1[value_col]

    # Build links: Promo Type -> Category
    df_links2 = (
        df_sankey.groupby(["promo_type", "category"])[value_col].sum().reset_index()
    )
    source2 = df_links2["promo_type"].map(label_indices)
    target2 = df_links2["category"].map(label_indices)
    value2 = df_links2[value_col]

    # Combine
    sources = pd.concat([source1, source2], ignore_index=True)
    targets = pd.concat([target1, target2], ignore_index=True)
    values = pd.concat([value1, value2], ignore_index=True)

    # Sankey diagram
    fig_sankey = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color="skyblue",
            ),
            link=dict(source=sources, target=targets, value=values, color="lightgreen"),
        )
    )

    fig_sankey.update_layout(
        title_text=f"Sankey Flow: Campaign → Promo Type → Category ({metric})",
        font_size=12,
        height=600,
    )

    st.plotly_chart(fig_sankey, use_container_width=True)

st.caption(
    """
This visualization illustrates how each **Marketing Campaign** connects to different **Promotion Types**, 
and how these promotions drive revenue across **Product Categories**.

- **Campaigns** → represent the starting point of each marketing effort.  
- **Promo Types** → show the kind of offers used (e.g., BOGOF, 33% OFF, Cashback).  
- **Categories** → indicate where the revenue was generated (e.g., Grocery, Home Appliances).  

For example, **CAMP_SAN_01** primarily used **BOGOF** and **33% OFF** promotions, 
which generated high revenue from **Grocery & Staples** and **Home Appliances**.

**Tip:** The **thicker the line**, the **greater the revenue contribution** along that path.
"""
)

st.subheader("Faceted Small Multiples: Before/After KPI per Campaign")

# KPI toggle: Revenue or Units
kpi_option = st.radio("Select KPI", ["Revenue", "Units"], horizontal=True)

# Map KPI to column names
if kpi_option == "Revenue":
    before_col = "revenue_before_promo"
    after_col = "revenue_after_promo"
    y_label = "Revenue (₹)"
else:
    before_col = "quantity_sold (before_promo)"
    after_col = "quantity_sold (after_promo)"
    y_label = "Units Sold"

# Ensure columns exist
required_cols = {"campaign_id", "product_code", before_col, after_col}
missing_cols = required_cols - set(filtered_clean_all.columns)
if missing_cols:
    st.warning(f"Missing columns: {missing_cols}")
else:
    df_facet = filtered_clean_all.copy()

    # Melt KPI for Before/After
    df_melt = df_facet.melt(
        id_vars=["campaign_id", "product_code"],
        value_vars=[before_col, after_col],
        var_name="Period",
        value_name=kpi_option,
    )

    # Rename periods
    df_melt["Period"] = df_melt["Period"].map(
        {before_col: "Before", after_col: "After"}
    )

    # Faceted bar chart
    fig_facet = px.bar(
        df_melt,
        x="product_code",
        y=kpi_option,
        color="Period",
        facet_col="campaign_id",
        facet_col_wrap=3,
        barmode="group",
        height=500,
        hover_data={kpi_option: ":,.0f"},
        labels={"product_code": "Product", kpi_option: y_label},
    )

    fig_facet.update_layout(
        title=f"Before vs After {kpi_option} per Campaign",
        legend=dict(y=1.1, orientation="h"),
        margin=dict(t=80, b=50),
    )

    st.plotly_chart(fig_facet, use_container_width=True)

st.subheader("Sunburst — Hierarchical Promo Insights")

# Required columns
required_cols = {
    "campaign_id",
    "promo_type",
    "category",
    "product_code",
    "incremental_margin%",
    "revenue_after_promo",
    "total_quantity_sold",
}
missing = required_cols - set(filtered_clean_all.columns)
if missing:
    st.warning(
        f"Sunburst requires these columns in filtered_clean_all: {sorted(missing)}"
    )
else:
    df_sb = filtered_clean_all.copy()

    # Optional: city filter (matches how you scope other visuals)
    focus_city = st.session_state.get("selected_city", "All")
    if focus_city and focus_city != "All" and "city" in df_sb.columns:
        df_sb = df_sb[df_sb["city"] == focus_city]

    # KPI selection (uses session_state main KPI if present)
    kpi_focus = st.session_state.get("kpi_focus", "Revenue")
    if kpi_focus == "Revenue":
        value_col = "revenue_after_promo"
        value_label = "Revenue (₹)"
    else:
        value_col = "total_quantity_sold"
        value_label = "Units"

    # Optional control: limit to top N leaf combinations to avoid clutter
    top_n = st.number_input(
        "Limit to top N leaf combinations (0 = no limit)",
        min_value=0,
        max_value=500,
        value=0,
        step=10,
    )

    # Aggregate by hierarchy path
    path = ["campaign_id", "promo_type", "category", "product_code"]
    agg = df_sb.groupby(path, as_index=False).agg(
        **{value_col: (value_col, "sum")},
        incremental_margin_pct=("incremental_margin%", "mean"),
    )

    # Optional: prune to top-N leaf nodes by value (keeps highest contributors)
    if top_n and top_n > 0:
        top_leaves = (
            agg.groupby("product_code")[value_col].sum().nlargest(top_n).index.tolist()
        )
        agg = agg[agg["product_code"].isin(top_leaves)]

    # Build sunburst
    fig_sb = px.sunburst(
        agg,
        path=path,
        values=value_col,
        color="incremental_margin_pct",
        color_continuous_scale="RdYlGn",
        hover_data={value_col: ":,.0f", "incremental_margin_pct": ":.2f"},
        title=f"Sunburst — {value_label} by Campaign → Promo Type → Category → Product",
    )

    # Layout tuning
    fig_sb.update_traces(textinfo="label+percent entry")  # show label and percent
    fig_sb.update_layout(
        margin=dict(t=60, l=10, r=10, b=10),
        height=700,
        template="plotly_white",
        coloraxis_colorbar=dict(title="Incremental Margin %"),
    )

    # show chart with unique key
    st.plotly_chart(fig_sb, use_container_width=True, key="sunburst_chart")

st.caption(
    """

This chart shows how **Revenue (₹)** is distributed across different levels:  
**Campaign ➜ Promo Type ➜ Category ➜ Product**.

-**Center Circle (Campaign):** Represents the main marketing campaigns (e.g., CAMP_SAN_01, CAMP_DIW_01).  
-**Next Rings (Promo Types):** Show the types of promotions used — like BOGOF, 33% OFF, or Cashback.  
-**Outer Rings (Categories & Products):** Indicate which product categories and specific items contributed to the revenue.  

For example, **CAMP_SAN_01** generated the highest revenue, mainly through **BOGOF** and **33% OFF** promotions, 
driving strong sales in **Grocery & Staples** and **Home Appliances**.  

**Color Insight:**  
- **Green shades** indicate higher **Incremental Margin %**,  
- **Red shades** indicate lower or negative margin performance.  

Each layer helps identify which **campaigns and promotions** performed best and where improvements can be made.
"""
)
