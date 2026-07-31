"""
Project Harvest — Operational Intelligence Dashboard
Streamlit + Plotly interactive analytics platform
Auto-generates POS data on first load — no CSV upload required.
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
import random
import os
warnings.filterwarnings("ignore")

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project Harvest — Operations Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0F1117; }
    .stApp { background-color: #0F1117; }
    .metric-card {
        background: linear-gradient(135deg, #1B2A4A 0%, #2E5F8A 100%);
        border: 1px solid #2E5F8A;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(46,95,138,0.3);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        color: #A8C8E8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .metric-delta {
        font-size: 12px;
        color: #52C97C;
        margin-top: 6px;
    }
    .metric-delta.negative { color: #FF6B6B; }
    .alert-card {
        background: rgba(255,107,107,0.12);
        border: 1px solid #FF6B6B;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
    }
    .section-header {
        font-size: 16px;
        font-weight: 700;
        color: #EAF2FA;
        border-left: 4px solid #2E5F8A;
        padding-left: 12px;
        margin: 24px 0 16px 0;
    }
    div[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1F2937;
    }
    h1, h2, h3 { color: #EAF2FA !important; }
    .stDataFrame { background-color: #161B27; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA GENERATION — runs inline, no CSV file needed
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pos_data() -> pd.DataFrame:
    """
    Generate synthetic POS transaction data for 5 store locations over 24 months.
    Injects realistic operational variances:
      - Store S004 (Plano Legacy): high labor overtime + food waste in Q3
      - Store S003 (Deep Ellum): volume decline Apr-Jun Year 2
      - Store S001 (Downtown Dallas): catering boost Q2-Q3
      - Store S005 (Frisco Hub): growth ramp through Year 1
    """
    np.random.seed(42)
    random.seed(42)

    STORES = {
        "S001": {"name": "Downtown Dallas", "base_daily_txn": 18, "avg_check": 28.50},
        "S002": {"name": "Uptown",          "base_daily_txn": 15, "avg_check": 31.20},
        "S003": {"name": "Deep Ellum",      "base_daily_txn": 14, "avg_check": 24.80},
        "S004": {"name": "Plano Legacy",    "base_daily_txn": 12, "avg_check": 26.40},
        "S005": {"name": "Frisco Hub",      "base_daily_txn": 11, "avg_check": 27.10},
    }

    MONTHLY_SEASONAL = {
        1:0.88, 2:0.85, 3:0.92, 4:0.98,
        5:1.05, 6:1.08, 7:1.06, 8:1.02,
        9:0.97, 10:0.99, 11:1.03, 12:1.15,
    }
    DOW_FACTOR = {0:0.82, 1:0.85, 2:0.90, 3:0.95, 4:1.15, 5:1.25, 6:1.08}

    DAY_PARTS  = ["Lunch", "Dinner", "Late Night"]
    DP_WEIGHTS = [0.42, 0.45, 0.13]
    DP_CHECK   = [0.85, 1.10, 0.90]

    CATEGORIES  = ["Food", "Beverage", "Alcohol"]
    CAT_WEIGHTS = [0.58, 0.27, 0.15]
    CAT_COGS    = [(0.28, 0.34), (0.18, 0.24), (0.22, 0.28)]

    ORDER_TYPES = ["Dine-in", "Takeout", "Delivery"]
    OT_WEIGHTS  = [0.52, 0.31, 0.17]
    OT_CHECK    = [1.12, 0.95, 1.05]
    OT_LABOR    = [1.15, 0.85, 0.70]

    from datetime import datetime, timedelta
    start     = datetime(2023, 1, 1)
    all_dates = [start + timedelta(days=d) for d in range(24 * 30)]

    records = []
    txn_id  = 1

    for dt in all_dates:
        seas = MONTHLY_SEASONAL[dt.month]
        dow  = DOW_FACTOR[dt.weekday()]
        yr   = dt.year - 2023  # 0 = Year 1, 1 = Year 2

        for sid, scfg in STORES.items():
            # ── Operational variances ─────────────────────────────────────────
            s4_q3    = sid == "S004" and dt.month in [7, 8, 9]
            s3_susp  = sid == "S003" and yr == 1 and dt.month in [4, 5, 6]
            s1_cat   = sid == "S001" and dt.month in [5, 6, 7, 8]
            s5_ramp  = sid == "S005" and yr == 0

            cogs_adj  = 0.062 if s4_q3 else 0.0
            labor_adj = 0.078 if s4_q3 else 0.0
            vol_adj   = (-0.08 if s4_q3 else
                         -0.15 if s3_susp else
                          0.12 if s1_cat else
                          min(0.18, dt.month * 0.015) if s5_ramp else 0.0)
            check_adj = -0.08 if s3_susp else (0.06 if s1_cat else 0.0)

            n = max(3, int(np.random.poisson(
                scfg["base_daily_txn"] * seas * dow * (1 + vol_adj)
            )))

            dp_idx  = np.random.choice(3, size=n, p=DP_WEIGHTS)
            cat_idx = np.random.choice(3, size=n, p=CAT_WEIGHTS)
            ot_idx  = np.random.choice(3, size=n, p=OT_WEIGHTS)

            for i in range(n):
                dp  = DAY_PARTS[dp_idx[i]]
                cat = CATEGORIES[cat_idx[i]]
                ot  = ORDER_TYPES[ot_idx[i]]

                gross = max(8.0, round(
                    scfg["avg_check"]
                    * DP_CHECK[dp_idx[i]]
                    * OT_CHECK[ot_idx[i]]
                    * (1 + check_adj)
                    * seas
                    * np.random.lognormal(0, 0.22), 2
                ))
                disc  = round(gross * min(0.20, np.random.exponential(0.04)), 2)
                net   = round(gross - disc, 2)

                cogs_pct = np.random.uniform(*CAT_COGS[cat_idx[i]]) + cogs_adj
                cogs     = round(net * min(cogs_pct, 0.72), 2)

                lhr  = round(
                    net / np.random.uniform(38, 58)
                    * OT_LABOR[ot_idx[i]]
                    * (1 + labor_adj), 4
                )
                wage_rate = np.random.uniform(16.5, 21.5) * (1.18 if s4_q3 else 1.0)
                wage      = round(lhr * wage_rate, 2)

                tbl  = 0 if ot in ["Takeout", "Delivery"] else random.choice([1,2,2,3,3,4,5])
                hour = (random.randint(11, 13) if dp == "Lunch" else
                        random.randint(17, 20) if dp == "Dinner" else
                        random.randint(21, 23))

                records.append({
                    "Transaction_ID":        f"TXN-{txn_id:07d}",
                    "Date":                  dt.strftime("%Y-%m-%d"),
                    "Timestamp":             f"{dt.strftime('%Y-%m-%d')} {hour:02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
                    "Store_ID":              sid,
                    "Location_Name":         scfg["name"],
                    "Day_Part":              dp,
                    "Category":              cat,
                    "Gross_Sales":           gross,
                    "Discount_Amount":       disc,
                    "Net_Sales":             net,
                    "Cost_of_Goods_Sold":    cogs,
                    "Labor_Hours_Allocated": lhr,
                    "Labor_Cost":            wage,
                    "Table_Size":            tbl,
                    "Order_Type":            ot,
                })
                txn_id += 1

    df = pd.DataFrame(records)
    df["Date"]    = pd.to_datetime(df["Date"])
    df["Month"]   = df["Date"].dt.to_period("M").astype(str)
    df["Year"]    = df["Date"].dt.year.astype(str)
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
    df["Week"]    = df["Date"].dt.isocalendar().week.astype(int)

    df["Prime_Cost"]      = df["Cost_of_Goods_Sold"] + df["Labor_Cost"]
    df["Gross_Margin"]    = df["Net_Sales"] - df["Cost_of_Goods_Sold"]
    df["EBITDA_Proxy"]    = df["Net_Sales"] - df["Prime_Cost"]
    df["Prime_Cost_Pct"]  = df["Prime_Cost"]     / df["Net_Sales"].replace(0, np.nan)
    df["COGS_Pct"]        = df["Cost_of_Goods_Sold"] / df["Net_Sales"].replace(0, np.nan)
    df["Labor_Pct"]       = df["Labor_Cost"]     / df["Net_Sales"].replace(0, np.nan)
    df["Labor_Efficiency"]= df["Net_Sales"]      / df["Labor_Hours_Allocated"].replace(0, np.nan)

    return df


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Load POS data. Tries CSV first (faster); generates inline if not found.
    Cached for the session so it only runs once.
    """
    csv_path = "pos_transactions.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, parse_dates=["Date"])
        # Add derived columns if missing
        if "Prime_Cost" not in df.columns:
            df["Prime_Cost"]      = df["Cost_of_Goods_Sold"] + df["Labor_Cost"]
            df["Prime_Cost_Pct"]  = df["Prime_Cost"] / df["Net_Sales"].replace(0, np.nan)
            df["COGS_Pct"]        = df["Cost_of_Goods_Sold"] / df["Net_Sales"].replace(0, np.nan)
            df["Labor_Pct"]       = df["Labor_Cost"] / df["Net_Sales"].replace(0, np.nan)
            df["Labor_Efficiency"]= df["Net_Sales"] / df["Labor_Hours_Allocated"].replace(0, np.nan)
        if "Month" not in df.columns:
            df["Month"]   = df["Date"].dt.to_period("M").astype(str)
            df["Year"]    = df["Date"].dt.year.astype(str)
            df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
            df["Week"]    = df["Date"].dt.isocalendar().week.astype(int)
        return df
    else:
        return generate_pos_data()


# ── Load data with progress indicator ─────────────────────────────────────────
with st.spinner("🌾 Loading Project Harvest data — please wait about 20 seconds on first visit..."):
    df_raw = load_data()

# ── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 Project Harvest")
    st.markdown("*Operational Intelligence Platform*")
    st.divider()

    st.markdown("### 📍 Store Filter")
    all_stores     = sorted(df_raw["Location_Name"].unique())
    selected_stores = st.multiselect(
        "Select Locations",
        options=all_stores,
        default=all_stores,
    )

    st.markdown("### 📅 Date Range")
    min_date = df_raw["Date"].min().date()
    max_date = df_raw["Date"].max().date()
    date_range = st.date_input(
        "Select Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    st.markdown("### 🚚 Order Type")
    order_types     = sorted(df_raw["Order_Type"].unique())
    selected_orders = st.multiselect(
        "Order Channels",
        options=order_types,
        default=order_types,
    )

    st.markdown("### 🏷️ Day Part")
    day_parts        = sorted(df_raw["Day_Part"].unique())
    selected_dayparts = st.multiselect(
        "Day Parts",
        options=day_parts,
        default=day_parts,
    )

    st.divider()
    st.markdown("### ⚙️ Scenario Modeling")
    apply_cogs_synergy = st.toggle(
        "Supply Chain Synergies (−2% COGS)",
        value=False,
        help="Vendor consolidation reduces COGS by 2.0%",
    )
    apply_labor_optim = st.toggle(
        "Labor Optimization (−1.5% Labor)",
        value=False,
        help="Centralized scheduling reduces labor cost by 1.5%",
    )
    apply_pricing = st.toggle(
        "Pricing Power (+1.5% ASP)",
        value=False,
        help="Menu re-engineering increases average check by 1.5%",
    )

    active = []
    if apply_cogs_synergy: active.append("−2% COGS")
    if apply_labor_optim:  active.append("−1.5% Labor")
    if apply_pricing:      active.append("+1.5% ASP")
    if active:
        st.success("Active: " + " | ".join(active))
    else:
        st.info("Baseline view — no synergies applied")

    st.divider()
    st.markdown("### 🏗️ Fixed Cost Assumptions")
    monthly_rent_k = st.number_input("Monthly Rent / Store ($K)", value=22.0, step=1.0)
    monthly_ga_pct = st.slider(
        "G&A % of Revenue", min_value=0.03, max_value=0.10,
        value=0.055, step=0.005, format="%.1%%"
    )

# ── Date filter ───────────────────────────────────────────────────────────────
if len(date_range) == 2:
    start_dt = pd.Timestamp(date_range[0])
    end_dt   = pd.Timestamp(date_range[1])
else:
    start_dt = df_raw["Date"].min()
    end_dt   = df_raw["Date"].max()

df = df_raw[
    df_raw["Location_Name"].isin(selected_stores) &
    (df_raw["Date"] >= start_dt) &
    (df_raw["Date"] <= end_dt) &
    df_raw["Order_Type"].isin(selected_orders) &
    df_raw["Day_Part"].isin(selected_dayparts)
].copy()

if df.empty:
    st.warning("No data matches current filters.")
    st.stop()

# ── Apply synergy adjustments ─────────────────────────────────────────────────
COGS_RED  = 0.020 if apply_cogs_synergy else 0.0
LABOR_RED = 0.015 if apply_labor_optim  else 0.0
REV_UP    = 0.015 if apply_pricing      else 0.0

df["Net_Sales_Adj"]      = df["Net_Sales"] * (1 + REV_UP)
df["COGS_Adj"]           = df["Cost_of_Goods_Sold"] * (1 - COGS_RED)
df["Labor_Cost_Adj"]     = df["Labor_Cost"] * (1 - LABOR_RED)
df["Prime_Cost_Adj"]     = df["COGS_Adj"] + df["Labor_Cost_Adj"]
df["Prime_Cost_Pct_Adj"] = df["Prime_Cost_Adj"] / df["Net_Sales_Adj"].replace(0, np.nan)
df["EBITDA_Adj"]         = df["Net_Sales_Adj"] - df["Prime_Cost_Adj"]

# ── KPI calculations ──────────────────────────────────────────────────────────
n_months = max(1, (end_dt - start_dt).days / 30)
n_stores = len(selected_stores)

total_rev   = df["Net_Sales_Adj"].sum()
total_cogs  = df["COGS_Adj"].sum()
total_labor = df["Labor_Cost_Adj"].sum()
total_prime = total_cogs + total_labor
avg_prime   = total_prime / total_rev if total_rev else 0
total_hrs   = df["Labor_Hours_Allocated"].sum()
avg_check   = df["Net_Sales_Adj"].mean()
labor_eff   = total_rev / total_hrs if total_hrs else 0

fixed_costs  = n_stores * monthly_rent_k * 1000 * n_months
ga_cost      = total_rev * monthly_ga_pct
fw_ebitda    = total_rev - total_prime - fixed_costs - ga_cost
fw_margin    = fw_ebitda / total_rev if total_rev else 0

base_rev     = df["Net_Sales"].sum()
base_prime   = (df["Cost_of_Goods_Sold"] + df["Labor_Cost"]).sum()
base_ebitda  = base_rev - base_prime - fixed_costs - (base_rev * monthly_ga_pct)
synergy_lift = fw_ebitda - base_ebitda

# ── Header banner ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1B2A4A,#0D1B2E);
            border-radius:16px;padding:28px 36px;margin-bottom:28px;
            border:1px solid #2E5F8A;">
    <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:700;">
        🌾 Project Harvest — Operational Intelligence
    </h1>
    <p style="color:#A8C8E8;margin:8px 0 0;font-size:13px;">
        Platform Co Portfolio Analytics · Investment Committee View
    </p>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
def kpi_card(col, label, value, delta=None, neg=False):
    arrow = "▼" if neg else "▲"
    delta_html = (
        f'<div class="metric-delta {"negative" if neg else ""}">{arrow} {delta}</div>'
        if delta else ""
    )
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
kpi_card(c1, "Net Revenue (Period)",   f"${total_rev/1e6:.2f}M",
         delta=f"+{REV_UP:.1%} pricing" if apply_pricing else None)
kpi_card(c2, "Prime Cost %",           f"{avg_prime:.1%}",
         delta=f"−{(COGS_RED+LABOR_RED):.1%} synergy" if (apply_cogs_synergy or apply_labor_optim) else None)
kpi_card(c3, "4-Wall EBITDA Margin",   f"{fw_margin:.1%}",
         delta=f"+${synergy_lift/1000:.0f}K uplift" if synergy_lift > 0 else None)
kpi_card(c4, "Average Check Size",     f"${avg_check:.2f}",
         delta=f"+1.5% ASP" if apply_pricing else None)
kpi_card(c5, "Labor Efficiency ($/hr)",f"${labor_eff:.2f}",
         delta=f"−{LABOR_RED:.1%} labor cost" if apply_labor_optim else None)

st.markdown("<br>", unsafe_allow_html=True)

# ── Alert panel ───────────────────────────────────────────────────────────────
store_prime = df.groupby("Location_Name").apply(
    lambda x: (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum()
)
high_prime = store_prime[store_prime > 0.60]

if not high_prime.empty:
    with st.expander(
        f"⚠️ {len(high_prime)} Store(s) Exceeding Prime Cost Threshold (>60%)",
        expanded=True
    ):
        for store, pct in high_prime.items():
            st.markdown(f"""
            <div class="alert-card">
                <strong style="color:#FF6B6B;">{store}</strong>
                <span style="color:#FCA5A5;float:right;font-size:18px;font-weight:700;">{pct:.1%}</span>
                <br><span style="color:#9CA3AF;font-size:12px;">
                Prime Cost exceeds 60% — review labor scheduling and COGS variances
                </span>
            </div>
            """, unsafe_allow_html=True)

# ── Chart 1: Prime Cost Heatmap ───────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Prime Cost % by Store × Month</div>',
            unsafe_allow_html=True)

hm_df = (
    df.groupby(["Location_Name", "Month"])
    .apply(lambda x: (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum())
    .reset_index(name="Prime_Cost_Pct")
)
hm_df["Month_Dt"] = pd.to_datetime(hm_df["Month"])
hm_df = hm_df.sort_values("Month_Dt")
hm_pivot = hm_df.pivot(index="Location_Name", columns="Month", values="Prime_Cost_Pct")
sorted_months = sorted(hm_df["Month"].unique())
hm_pivot = hm_pivot.reindex(columns=sorted_months)

fig_heat = go.Figure(go.Heatmap(
    z=hm_pivot.values,
    x=list(hm_pivot.columns),
    y=hm_pivot.index.tolist(),
    colorscale=[
        [0.00, "#1a472a"], [0.45, "#2d6a4f"], [0.55, "#52b788"],
        [0.70, "#f4a261"], [0.80, "#e76f51"], [1.00, "#c1121f"],
    ],
    zmid=0.60, zmin=0.40, zmax=0.85,
    text=[[f"{v:.1%}" if not np.isnan(v) else "N/A" for v in row]
          for row in hm_pivot.values],
    texttemplate="%{text}",
    textfont={"size": 9, "color": "white"},
    hovertemplate="<b>%{y}</b><br>Month: %{x}<br>Prime Cost: %{text}<extra></extra>",
    colorbar=dict(
        title="Prime Cost %", tickformat=".0%",
        tickvals=[0.40, 0.50, 0.60, 0.70, 0.80],
        ticktext=["40%", "50%", "60% ⚠", "70%", "80%"],
        thickness=14, len=0.8,
    ),
))
fig_heat.update_layout(
    title=dict(text="Prime Cost Heatmap — Red Zone = >60% Threshold",
               font=dict(color="#EAF2FA", size=13)),
    paper_bgcolor="#0F1117", plot_bgcolor="#0F1117",
    font=dict(color="#A8C8E8", family="Arial"),
    height=300,
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(tickangle=-45, tickfont=dict(size=8)),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ── Chart 2: Labor Efficiency Scatter ─────────────────────────────────────────
st.markdown('<div class="section-header">🔍 Labor Efficiency — Hours vs. Revenue by Day Part</div>',
            unsafe_allow_html=True)

col_a, col_b = st.columns([3, 1])

with col_b:
    st.markdown("<br>", unsafe_allow_html=True)
    color_by = st.selectbox("Color By", ["Day_Part", "Location_Name", "Order_Type"])

with col_a:
    sc_df = (
        df.groupby(["Date", "Location_Name", "Day_Part"])
        .agg(
            Labor_Hours=("Labor_Hours_Allocated", "sum"),
            Net_Sales=("Net_Sales_Adj", "sum"),
            Transactions=("Net_Sales_Adj", "count"),
            Labor_Cost=("Labor_Cost_Adj", "sum"),
        )
        .reset_index()
    )
    sc_df["Labor_Efficiency"] = sc_df["Net_Sales"] / sc_df["Labor_Hours"].replace(0, np.nan)
    sc_df["Labor_Cost_Pct"]   = sc_df["Labor_Cost"] / sc_df["Net_Sales"].replace(0, np.nan)
    sc_df = sc_df.dropna(subset=["Labor_Efficiency"])

    fig_sc = px.scatter(
        sc_df, x="Labor_Hours", y="Net_Sales",
        color=color_by if color_by in sc_df.columns else "Day_Part",
        size="Transactions", size_max=16, opacity=0.70,
        color_discrete_sequence=px.colors.qualitative.Bold,
        hover_data={"Labor_Efficiency": ":.2f", "Labor_Cost_Pct": ":.1%"},
        labels={"Labor_Hours": "Labor Hours", "Net_Sales": "Net Revenue ($)"},
        title="Staffing Efficiency Map — Identify Over/Under-Staffed Periods",
    )
    max_hrs = sc_df["Labor_Hours"].quantile(0.95)
    for eff, color, label in [
        (35, "#FF6B6B", "< $35/hr — Understaffed"),
        (50, "#F59E0B", "$50/hr — Target"),
        (65, "#52C97C", "> $65/hr — Efficient"),
    ]:
        fig_sc.add_trace(go.Scatter(
            x=[0, max_hrs], y=[0, max_hrs * eff],
            mode="lines", name=label,
            line=dict(color=color, width=1.5, dash="dash"),
        ))
    fig_sc.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8", family="Arial"),
        height=400, margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#2E5F8A", borderwidth=1),
        xaxis=dict(gridcolor="#1F2937"),
        yaxis=dict(gridcolor="#1F2937"),
    )
    st.plotly_chart(fig_sc, use_container_width=True)

# ── Chart 3: Waterfall + Gauge ────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 Synergy Impact — EBITDA Waterfall & Margin Gauge</div>',
            unsafe_allow_html=True)

col3a, col3b = st.columns([1, 2])

with col3a:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=fw_margin * 100,
        delta={
            "reference": (base_ebitda / base_rev * 100) if base_rev else 0,
            "valueformat": ".1f",
            "suffix": "%",
            "increasing": {"color": "#52C97C"},
            "decreasing": {"color": "#FF6B6B"},
        },
        title={"text": "4-Wall EBITDA Margin", "font": {"color": "#EAF2FA", "size": 13}},
        number={"suffix": "%", "font": {"color": "#FFFFFF", "size": 30}},
        gauge={
            "axis": {"range": [-5, 35], "tickwidth": 1, "tickcolor": "#A8C8E8",
                     "tickformat": ".0f", "ticksuffix": "%"},
            "bar": {"color": "#2E5F8A", "thickness": 0.28},
            "bgcolor": "#161B27",
            "borderwidth": 2, "bordercolor": "#1F2937",
            "steps": [
                {"range": [-5, 0],  "color": "#7F1D1D"},
                {"range": [0, 10],  "color": "#991B1B"},
                {"range": [10, 18], "color": "#B45309"},
                {"range": [18, 25], "color": "#166534"},
                {"range": [25, 35], "color": "#064E3B"},
            ],
            "threshold": {
                "line": {"color": "#F59E0B", "width": 3},
                "thickness": 0.85,
                "value": 20,
            },
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="#0F1117",
        font=dict(color="#A8C8E8", family="Arial"),
        height=260,
        margin=dict(l=30, r=30, t=40, b=10),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    if active:
        rows = []
        if apply_cogs_synergy:
            rows.append(("Vendor Consolidation (−2% COGS)", total_rev * COGS_RED))
        if apply_labor_optim:
            rows.append(("Labor Scheduling (−1.5% Labor)",  total_labor * LABOR_RED))
        if apply_pricing:
            rows.append(("Pricing Power (+1.5% ASP)",       base_rev * REV_UP))
        syn_df = pd.DataFrame(rows, columns=["Synergy", "Uplift ($)"])
        syn_df["Uplift ($)"] = syn_df["Uplift ($)"].map("${:,.0f}".format)
        st.dataframe(syn_df, hide_index=True, use_container_width=True)
    else:
        st.info("Enable synergies in the sidebar to see the uplift breakdown.")

with col3b:
    wf_labels = [
        "Net Revenue", "Cost of Goods Sold", "Labor Cost",
        "After Prime Cost", "Rent & Occupancy", "G&A Expense", "4-Wall EBITDA",
    ]
    wf_measures = ["total", "relative", "relative", "total", "relative", "relative", "total"]
    wf_values   = [
        total_rev, -total_cogs, -total_labor,
        0, -fixed_costs, -ga_cost, fw_ebitda,
    ]
    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=wf_measures,
        x=wf_labels,
        y=wf_values,
        text=[f"${abs(v)/1000:.0f}K" for v in wf_values],
        textposition="outside",
        textfont=dict(color="#EAF2FA", size=9),
        connector={"line": {"color": "#2E5F8A", "width": 1.5, "dash": "dot"}},
        increasing={"marker": {"color": "#166534", "line": {"color": "#52C97C", "width": 1}}},
        decreasing={"marker": {"color": "#991B1B", "line": {"color": "#FF6B6B", "width": 1}}},
        totals={"marker":    {"color": "#1B2A4A", "line": {"color": "#2E5F8A", "width": 2}}},
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    fig_wf.update_layout(
        title=dict(text="P&L Waterfall — Revenue to 4-Wall EBITDA",
                   font=dict(color="#EAF2FA", size=13)),
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8", family="Arial"),
        height=360,
        margin=dict(l=20, r=20, t=50, b=80),
        yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
        xaxis=dict(tickangle=-25, tickfont=dict(size=9)),
        showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# ── Store Scorecard ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏪 Store-Level Performance Scorecard</div>',
            unsafe_allow_html=True)

store_kpi = (
    df.groupby("Location_Name")
    .apply(lambda x: pd.Series({
        "Net Revenue ($)":      x["Net_Sales_Adj"].sum(),
        "Transactions":         len(x),
        "Avg Check ($)":        x["Net_Sales_Adj"].mean(),
        "Prime Cost %":         (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum(),
        "COGS %":               x["COGS_Adj"].sum() / x["Net_Sales_Adj"].sum(),
        "Labor %":              x["Labor_Cost_Adj"].sum() / x["Net_Sales_Adj"].sum(),
        "Labor Eff. ($/hr)":    x["Net_Sales_Adj"].sum() / x["Labor_Hours_Allocated"].sum(),
        "Discount Rate":        x["Discount_Amount"].sum() / x["Gross_Sales"].sum(),
    }))
    .reset_index()
)

def color_prime(val):
    if not isinstance(val, float): return ""
    if val > 0.65: return "background-color:#7F1D1D;color:#FCA5A5;font-weight:700"
    if val > 0.60: return "background-color:#B45309;color:#FDE68A;font-weight:700"
    if val < 0.52: return "background-color:#064E3B;color:#6EE7B7"
    return ""

fmt = {
    "Net Revenue ($)":   "${:,.0f}",
    "Transactions":      "{:,.0f}",
    "Avg Check ($)":     "${:.2f}",
    "Prime Cost %":      "{:.1%}",
    "COGS %":            "{:.1%}",
    "Labor %":           "{:.1%}",
    "Labor Eff. ($/hr)": "${:.2f}",
    "Discount Rate":     "{:.2%}",
}

st.dataframe(
    store_kpi.style
        .format(fmt)
        .applymap(color_prime, subset=["Prime Cost %"])
        .set_properties(**{
            "background-color": "#161B27",
            "color": "#EAF2FA",
            "border": "1px solid #1F2937",
        }),
    hide_index=True,
    use_container_width=True,
    height=220,
)

# ── Monthly Revenue Trend ─────────────────────────────────────────────────────
st.markdown('<div class="section-header">📉 Monthly Revenue Trend by Store</div>',
            unsafe_allow_html=True)

monthly = (
    df.groupby(["Month", "Location_Name"])["Net_Sales_Adj"]
    .sum()
    .reset_index()
)
monthly["Month_Dt"] = pd.to_datetime(monthly["Month"])
monthly = monthly.sort_values("Month_Dt")

fig_trend = px.line(
    monthly, x="Month", y="Net_Sales_Adj", color="Location_Name",
    markers=True,
    color_discrete_sequence=["#60A5FA","#34D399","#FBBF24","#F87171","#A78BFA"],
    labels={"Net_Sales_Adj": "Net Revenue ($)", "Month": "Month",
            "Location_Name": "Store"},
    title="Monthly Net Revenue by Location — 24-Month View",
)
fig_trend.update_traces(line=dict(width=2.5), marker=dict(size=5))
fig_trend.update_layout(
    paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
    font=dict(color="#A8C8E8", family="Arial"),
    height=340,
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#2E5F8A",
                borderwidth=1, orientation="h", y=-0.20),
    xaxis=dict(gridcolor="#1F2937", tickangle=-45, tickfont=dict(size=8)),
    yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
)
st.plotly_chart(fig_trend, use_container_width=True)

# ── Day Part & Category Mix ───────────────────────────────────────────────────
col_dp, col_cat = st.columns(2)

with col_dp:
    dp_mix = (
        df.groupby(["Day_Part", "Order_Type"])["Net_Sales_Adj"]
        .sum()
        .reset_index()
    )
    fig_dp = px.bar(
        dp_mix, x="Day_Part", y="Net_Sales_Adj", color="Order_Type",
        barmode="stack",
        color_discrete_sequence=["#3B82F6","#10B981","#F59E0B"],
        labels={"Net_Sales_Adj": "Net Revenue ($)", "Day_Part": "Day Part"},
        title="Revenue Mix — Day Part × Order Channel",
    )
    fig_dp.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8"), height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(gridcolor="#1F2937"),
        yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_dp, use_container_width=True)

with col_cat:
    cat_mix = (
        df.groupby(["Category", "Location_Name"])["Net_Sales_Adj"]
        .sum()
        .reset_index()
    )
    fig_cat = px.bar(
        cat_mix, x="Location_Name", y="Net_Sales_Adj", color="Category",
        barmode="group",
        color_discrete_sequence=["#6366F1","#14B8A6","#F97316"],
        labels={"Net_Sales_Adj": "Net Revenue ($)", "Location_Name": "Store"},
        title="Revenue by Category — Cross-Store Comparison",
    )
    fig_cat.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8"), height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(gridcolor="#1F2937", tickangle=-20),
        yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ── Q3 S004 Spotlight ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🔴 Store S004 Plano Legacy — Q3 Variance Deep Dive</div>',
            unsafe_allow_html=True)

s4_df = df_raw[df_raw["Store_ID"] == "S004"].copy()
s4_monthly = (
    s4_df.groupby("Month")
    .apply(lambda x: pd.Series({
        "Prime_Cost_Pct": (x["Cost_of_Goods_Sold"] + x["Labor_Cost"]).sum() / x["Net_Sales"].sum(),
        "Labor_Pct":      x["Labor_Cost"].sum() / x["Net_Sales"].sum(),
        "COGS_Pct":       x["Cost_of_Goods_Sold"].sum() / x["Net_Sales"].sum(),
        "Net_Sales":      x["Net_Sales"].sum(),
    }))
    .reset_index()
)
s4_monthly["Month_Dt"] = pd.to_datetime(s4_monthly["Month"])
s4_monthly = s4_monthly.sort_values("Month_Dt")

fig_s4 = go.Figure()
fig_s4.add_trace(go.Bar(
    x=s4_monthly["Month"], y=s4_monthly["Net_Sales"],
    name="Net Sales ($)", marker_color="#2E5F8A", opacity=0.7,
    yaxis="y2",
))
for col, color, name in [
    ("Prime_Cost_Pct", "#FF6B6B", "Prime Cost %"),
    ("Labor_Pct",      "#F59E0B", "Labor %"),
    ("COGS_Pct",       "#60A5FA", "COGS %"),
]:
    fig_s4.add_trace(go.Scatter(
        x=s4_monthly["Month"], y=s4_monthly[col],
        name=name, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5),
    ))
fig_s4.add_hline(y=0.60, line_dash="dash", line_color="#FF6B6B",
                 annotation_text="60% Prime Cost Threshold",
                 annotation_position="top left")
fig_s4.update_layout(
    title=dict(
        text="Plano Legacy — Monthly KPIs (note Q3 labor & COGS spike from operational issues)",
        font=dict(color="#EAF2FA", size=12),
    ),
    paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
    font=dict(color="#A8C8E8", family="Arial"),
    height=360,
    margin=dict(l=20, r=60, t=60, b=60),
    legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#2E5F8A",
                borderwidth=1, orientation="h", y=-0.25),
    xaxis=dict(gridcolor="#1F2937", tickangle=-45, tickfont=dict(size=8)),
    yaxis=dict(gridcolor="#1F2937", tickformat=".0%", title="Cost %"),
    yaxis2=dict(overlaying="y", side="right", tickformat="$,.0f",
                title="Net Sales ($)", showgrid=False),
)
st.plotly_chart(fig_s4, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center;color:#4B5563;font-size:11px;padding:12px;">
    Project Harvest — Operational Intelligence Platform ·
    {len(df):,} transactions in view ·
    Period: {start_dt.strftime('%b %d, %Y')} – {end_dt.strftime('%b %d, %Y')} ·
    <em>Confidential — Investment Committee Use Only</em>
</div>
""", unsafe_allow_html=True)
