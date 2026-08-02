"""
Project Harvest — Operational Intelligence Dashboard
Streamlit + Plotly Express interactive analytics platform
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

# ── Page Config ────────────────────────────────────────────────────────────────
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
    .warning-card {
        background: rgba(245,158,11,0.12);
        border: 1px solid #F59E0B;
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
    .stSlider > div > div > div > div { background-color: #2E5F8A !important; }
    h1, h2, h3 { color: #EAF2FA !important; }
</style>
""", unsafe_allow_html=True)

import os
import random
from datetime import datetime, timedelta

# ── POS Data Generator (embedded) ─────────────────────────────────────────────
# Embedded directly so the app works on Streamlit Cloud without any extra files.

_STORES = {
    "S001": {"name": "Downtown Dallas",  "base_daily_txn": 85, "avg_check": 28.50},
    "S002": {"name": "Uptown",           "base_daily_txn": 72, "avg_check": 31.20},
    "S003": {"name": "Deep Ellum",       "base_daily_txn": 68, "avg_check": 24.80},
    "S004": {"name": "Plano Legacy",     "base_daily_txn": 60, "avg_check": 26.40},
    "S005": {"name": "Frisco Hub",       "base_daily_txn": 55, "avg_check": 27.10},
}
_DAY_PARTS = {
    "Lunch":      {"hours": (11, 14), "weight": 0.42, "check_mult": 0.85},
    "Dinner":     {"hours": (17, 21), "weight": 0.45, "check_mult": 1.10},
    "Late Night": {"hours": (21, 24), "weight": 0.13, "check_mult": 0.90},
}
_CATEGORIES = {
    "Food":     {"weight": 0.58, "cogs_pct_range": (0.28, 0.34)},
    "Beverage": {"weight": 0.27, "cogs_pct_range": (0.18, 0.24)},
    "Alcohol":  {"weight": 0.15, "cogs_pct_range": (0.22, 0.28)},
}
_ORDER_TYPES = {
    "Dine-in":  {"weight": 0.52, "check_mult": 1.12, "labor_factor": 1.15},
    "Takeout":  {"weight": 0.31, "check_mult": 0.95, "labor_factor": 0.85},
    "Delivery": {"weight": 0.17, "check_mult": 1.05, "labor_factor": 0.70},
}
_SEASONAL = {1:0.88,2:0.85,3:0.92,4:0.98,5:1.05,6:1.08,7:1.06,8:1.02,9:0.97,10:0.99,11:1.03,12:1.15}
_DOW     = {0:0.82,1:0.85,2:0.90,3:0.95,4:1.15,5:1.25,6:1.08}

def _store_variances(store_id, dt):
    v = {"cogs_uplift":0.0,"labor_uplift":0.0,"check_uplift":0.0,"volume_uplift":0.0,"discount_rate":0.04}
    m, yr = dt.month, dt.year - 2023
    if store_id == "S004":
        if m in [7,8,9]:  v["cogs_uplift"]+=0.062; v["labor_uplift"]+=0.078; v["volume_uplift"]-=0.08
        if m in [10,11,12]: v["cogs_uplift"]+=0.020; v["labor_uplift"]+=0.025
    if store_id == "S003" and yr==1 and m in [4,5,6]: v["volume_uplift"]-=0.15; v["check_uplift"]-=0.08
    if store_id == "S001" and m in [5,6,7,8]: v["volume_uplift"]+=0.12; v["check_uplift"]+=0.06
    if store_id == "S005":
        v["volume_uplift"] += min(0.18, m*0.015) if yr==0 else 0.18
    return v

def generate_transactions(start_date="2023-01-01", months=24, target_records=12000):
    np.random.seed(42); random.seed(42)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = start + timedelta(days=months*30)
    dp_list = list(_DAY_PARTS.keys())
    cat_list = list(_CATEGORIES.keys())
    ot_list  = list(_ORDER_TYPES.keys())
    records = []; txn = 1
    for date in pd.date_range(start, end, freq="D"):
        dt = date.to_pydatetime()
        sf = _SEASONAL[dt.month]; dw = _DOW[dt.weekday()]
        for sid, scfg in _STORES.items():
            v = _store_variances(sid, dt)
            n = max(5, int(np.random.poisson(scfg["base_daily_txn"]*dw*sf*(1+v["volume_uplift"]))))
            by_dp = np.random.multinomial(n, [_DAY_PARTS[d]["weight"] for d in dp_list])
            for di, dp in enumerate(dp_list):
                for _ in range(by_dp[di]):
                    ot  = np.random.choice(ot_list,  p=[_ORDER_TYPES[o]["weight"]  for o in ot_list])
                    cat = np.random.choice(cat_list, p=[_CATEGORIES[c]["weight"] for c in cat_list])
                    oc = _ORDER_TYPES[ot]; cc = _CATEGORIES[cat]
                    gs = max(8.0, round(scfg["avg_check"]*_DAY_PARTS[dp]["check_mult"]*oc["check_mult"]*(1+v["check_uplift"])*np.random.lognormal(0,0.22)*sf,2))
                    dr = min(v["discount_rate"]*np.random.exponential(1.0), 0.25)
                    da = round(gs*dr,2); ns = round(gs-da,2)
                    cp = min(np.random.uniform(*cc["cogs_pct_range"])+v["cogs_uplift"],0.72)
                    cg = round(ns*cp,2)
                    lp = np.clip(np.random.uniform(0.265,0.305)*oc["labor_factor"]*(1+v["labor_uplift"]),0.20,0.38)
                    bw = np.random.uniform(16.5,21.5)*(1.18 if sid=="S004" and dt.month in [7,8,9] else 1)
                    lc = round(ns*lp,2); lh = round(max(0.01,lc/bw),4)
                    ts = 0 if ot in ["Takeout","Delivery"] else max(1,int(np.random.choice([1,2,3,4,5,6,8],p=[0.18,0.30,0.22,0.17,0.07,0.04,0.02])))
                    hr = random.randint(_DAY_PARTS[dp]["hours"][0],_DAY_PARTS[dp]["hours"][1]-1)
                    ts_str = datetime(dt.year,dt.month,dt.day,hr,random.randint(0,59),random.randint(0,59)).strftime("%Y-%m-%d %H:%M:%S")
                    records.append({"Transaction_ID":f"TXN-{txn:07d}","Date":dt.strftime("%Y-%m-%d"),"Timestamp":ts_str,
                        "Store_ID":sid,"Location_Name":scfg["name"],"Day_Part":dp,"Category":cat,
                        "Gross_Sales":gs,"Discount_Amount":da,"Net_Sales":ns,"Cost_of_Goods_Sold":cg,
                        "Labor_Hours_Allocated":lh,"Labor_Cost":lc,"Table_Size":ts,"Order_Type":ot})
                    txn += 1
    return pd.DataFrame(records)

# ── Data Loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data(path: str = "pos_transactions.csv") -> pd.DataFrame:
    """Load CSV if it exists, otherwise generate the data in memory."""
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["Date"])
    else:
        with st.spinner("Generating POS transaction data — about 30 seconds..."):
            df = generate_transactions(start_date="2023-01-01", months=24)
            df["Date"] = pd.to_datetime(df["Date"])
            try:
                df.to_csv(path, index=False)
            except Exception:
                pass  # read-only filesystem (e.g. Streamlit Cloud) — just use in memory

    df["Month"]   = df["Date"].dt.to_period("M").astype(str)
    df["Year"]    = df["Date"].dt.year.astype(str)
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
    df["Week"]    = df["Date"].dt.isocalendar().week.astype(int)

    # ── Transaction-level derived fields ──────────────────────────────────────
    # NOTE: Labor_Cost in POS data is allocated per-ticket.
    # Transaction-level labor allocation overstates % vs. actual payroll,
    # so we normalize to a realistic fast-casual benchmark (~28% of net sales).
    # The raw Labor_Cost column is retained for pattern/trend analysis;
    # Labor_Cost_Normalized is used in P&L aggregations.
    df["Labor_Cost_Normalized"] = df["Net_Sales"] * 0.28   # 28% benchmark

    df["Prime_Cost"]     = df["Cost_of_Goods_Sold"] + df["Labor_Cost_Normalized"]
    df["Gross_Profit"]   = df["Net_Sales"] - df["Cost_of_Goods_Sold"]
    df["COGS_Pct"]       = df["Cost_of_Goods_Sold"] / df["Net_Sales"].replace(0, np.nan)
    df["Labor_Pct"]      = df["Labor_Cost_Normalized"] / df["Net_Sales"].replace(0, np.nan)
    df["Prime_Cost_Pct"] = df["Prime_Cost"] / df["Net_Sales"].replace(0, np.nan)
    df["Labor_Efficiency"] = df["Net_Sales"] / df["Labor_Hours_Allocated"].replace(0, np.nan)
    return df

df_raw = load_data()

# ── Sidebar Controls ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 Project Harvest")
    st.markdown("*Operational Intelligence Platform*")
    st.divider()

    st.markdown("### 📍 Store Filter")
    all_stores = sorted(df_raw["Location_Name"].unique())
    selected_stores = st.multiselect(
        "Select Locations",
        options=all_stores,
        default=all_stores,
        help="Filter by store location"
    )

    st.markdown("### 📅 Date Range")
    min_date = df_raw["Date"].min().date()
    max_date = df_raw["Date"].max().date()
    date_range = st.date_input(
        "Select Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    st.markdown("### 🚚 Order Type")
    order_types = sorted(df_raw["Order_Type"].unique())
    selected_orders = st.multiselect(
        "Order Channels",
        options=order_types,
        default=order_types
    )

    st.markdown("### 🏷️ Day Part")
    day_parts = sorted(df_raw["Day_Part"].unique())
    selected_dayparts = st.multiselect(
        "Day Parts",
        options=day_parts,
        default=day_parts
    )

    st.divider()
    st.markdown("### ⚙️ Scenario Modeling")
    apply_cogs_synergy = st.toggle(
        "Apply Supply Chain Synergies",
        value=False,
        help="Vendor consolidation reduces COGS by 2.0%"
    )
    apply_labor_optim = st.toggle(
        "Apply Labor Optimization",
        value=False,
        help="Centralized scheduling reduces labor cost by 1.5%"
    )
    apply_pricing = st.toggle(
        "Apply Pricing Power (+1.5% ASP)",
        value=False,
        help="Menu re-engineering increases average check"
    )

    synergy_note = []
    if apply_cogs_synergy: synergy_note.append("−2.0% COGS")
    if apply_labor_optim:  synergy_note.append("−1.5% Labor")
    if apply_pricing:      synergy_note.append("+1.5% Revenue")

    if synergy_note:
        st.success(f"Active: {' | '.join(synergy_note)}")
    else:
        st.info("No synergies applied — Baseline view")

    # ── P&L Cost Architecture Assumptions ─────────────────────────────────────
    st.divider()
    st.markdown("### 🏗️ P&L Cost Architecture")
    st.caption("Adjust store-level economics to match portfolio assumptions.")

    st.markdown("**COGS & Labor (% of Revenue)**")
    cogs_pct_assumption = st.slider(
        "COGS % of Revenue",
        min_value=0.24, max_value=0.38, value=0.30, step=0.01,
        format="%.0f%%",
        help="Benchmark: 28–34%. Food, Bev & Packaging cost."
    )
    labor_pct_assumption = st.slider(
        "Direct Labor % of Revenue",
        min_value=0.22, max_value=0.36, value=0.28, step=0.01,
        format="%.0f%%",
        help="Benchmark: 25–32%. Store-level hourly wages & benefits."
    )

    st.markdown("**Occupancy & Store Operating Costs**")
    occupancy_pct = st.slider(
        "Occupancy & Store OpEx % of Revenue",
        min_value=0.08, max_value=0.22, value=0.14, step=0.01,
        format="%.0f%%",
        help="Benchmark: 12–18%. Rent, CAM, utilities, maintenance, insurance."
    )

    st.markdown("**Corporate Overhead**")
    ga_pct = st.slider(
        "Corporate G&A % of Revenue",
        min_value=0.04, max_value=0.16, value=0.10, step=0.01,
        format="%.0f%%",
        help="Benchmark: 8–14%. Central office, executive, marketing, IT."
    )

    # Guardrail warnings
    if cogs_pct_assumption > 0.34:
        st.warning("⚠️ COGS above 34% — investigate food waste or pricing")
    if labor_pct_assumption > 0.32:
        st.warning("⚠️ Labor above 32% — scheduling/overtime concern")
    if occupancy_pct > 0.18:
        st.warning("⚠️ Occupancy above 18% — elevated rent risk")

    prime_assumption = cogs_pct_assumption + labor_pct_assumption
    if prime_assumption > 0.65:
        st.error(f"🚨 Prime Cost {prime_assumption:.0%} > 65% — store economics stressed")

# ── Filter Data ────────────────────────────────────────────────────────────────
if len(date_range) == 2:
    start_dt, end_dt = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start_dt, end_dt = df_raw["Date"].min(), df_raw["Date"].max()

df = df_raw[
    (df_raw["Location_Name"].isin(selected_stores)) &
    (df_raw["Date"] >= start_dt) &
    (df_raw["Date"] <= end_dt) &
    (df_raw["Order_Type"].isin(selected_orders)) &
    (df_raw["Day_Part"].isin(selected_dayparts))
].copy()

if df.empty:
    st.warning("No data matches current filters. Please adjust selections.")
    st.stop()

# ── Apply Synergy Adjustments ──────────────────────────────────────────────────
COGS_REDUCTION   = 0.020 if apply_cogs_synergy else 0.0
LABOR_REDUCTION  = 0.015 if apply_labor_optim  else 0.0
REVENUE_UPLIFT   = 0.015 if apply_pricing       else 0.0

# Adjusted revenue: scales with pricing toggle
df["Net_Sales_Adj"]  = df["Net_Sales"] * (1 + REVENUE_UPLIFT)

# COGS: apply slider assumption + synergy reduction
# (sidebar slider overrides raw data to normalize to realistic benchmark)
adj_cogs_pct = cogs_pct_assumption * (1 - COGS_REDUCTION)
df["COGS_Adj"]       = df["Net_Sales_Adj"] * adj_cogs_pct

# Labor: apply slider assumption + optimization reduction
adj_labor_pct = labor_pct_assumption * (1 - LABOR_REDUCTION)
df["Labor_Cost_Adj"] = df["Net_Sales_Adj"] * adj_labor_pct

# Derived transaction-level columns
df["Prime_Cost_Adj"]     = df["COGS_Adj"] + df["Labor_Cost_Adj"]
df["Prime_Cost_Pct_Adj"] = df["Prime_Cost_Adj"] / df["Net_Sales_Adj"].replace(0, np.nan)
df["Gross_Profit_Adj"]   = df["Net_Sales_Adj"] - df["COGS_Adj"]   # Gross Profit = Rev - COGS

# ── P&L Formula Hierarchy ──────────────────────────────────────────────────────
#
#  Gross Profit          = Revenue − COGS
#  4-Wall EBITDA         = Gross Profit − Direct Labor − Occupancy & Store OpEx
#  Consolidated EBITDA   = 4-Wall EBITDA − Corporate G&A
#  Net Income            = Consolidated EBITDA − D&A − Net Interest − Taxes
#
total_rev        = df["Net_Sales_Adj"].sum()
total_cogs       = df["COGS_Adj"].sum()
total_labor      = df["Labor_Cost_Adj"].sum()
total_prime      = total_cogs + total_labor
avg_prime_pct    = total_prime / total_rev if total_rev > 0 else 0
total_labor_hrs  = df["Labor_Hours_Allocated"].sum()
avg_check        = df["Net_Sales_Adj"].mean()
labor_efficiency = total_rev / total_labor_hrs if total_labor_hrs > 0 else 0

gross_profit     = total_rev - total_cogs                  # Step 1: Gross Profit
occupancy_cost   = total_rev * occupancy_pct               # Step 2: Occupancy (% of Rev)
four_wall_ebitda = gross_profit - total_labor - occupancy_cost  # Step 3: 4-Wall EBITDA
four_wall_margin = four_wall_ebitda / total_rev if total_rev > 0 else 0

ga_cost          = total_rev * ga_pct                      # Step 4: Corporate G&A
consol_ebitda    = four_wall_ebitda - ga_cost              # Step 5: Consolidated EBITDA
consol_margin    = consol_ebitda / total_rev if total_rev > 0 else 0

gross_margin     = gross_profit / total_rev if total_rev > 0 else 0

# ── Sanity Guardrails ──────────────────────────────────────────────────────────
FOUR_WALL_MAX    = 0.35   # 4-Wall EBITDA > 35% is anomalous for restaurants
GROSS_MARGIN_MAX = 0.80   # Gross margin > 80% is impossible for F&B
four_wall_display  = min(four_wall_margin,  FOUR_WALL_MAX)
gross_margin_display = min(gross_margin, GROSS_MARGIN_MAX)
margin_anomaly     = four_wall_margin > FOUR_WALL_MAX

# ── Baseline (no synergies) for delta calculations ─────────────────────────────
base_rev         = df["Net_Sales"].sum()
base_cogs        = base_rev * cogs_pct_assumption
base_labor       = base_rev * labor_pct_assumption
base_gross       = base_rev - base_cogs
base_occupancy   = base_rev * occupancy_pct
base_4wall       = base_gross - base_labor - base_occupancy
base_ga          = base_rev * ga_pct
base_consol      = base_4wall - base_ga
synergy_uplift   = consol_ebitda - base_consol

# ── Header ─────────────────────────────────────────────────────────────────────
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

# ── Sanity Anomaly Banner ───────────────────────────────────────────────────────
if margin_anomaly:
    st.warning(
        f"⚠️ **Margin Guardrail:** Computed 4-Wall EBITDA of "
        f"**{four_wall_margin:.1%}** exceeds the 35% anomaly threshold. "
        "Review COGS, labor, and occupancy assumptions in the sidebar. "
        f"Display is capped at {FOUR_WALL_MAX:.0%} until inputs are corrected."
    )

# ── KPI Cards — 6 Metrics ──────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

def kpi_card(col, label, value, delta=None, delta_negative=False):
    delta_html = ""
    if delta is not None:
        delta_class = "negative" if delta_negative else ""
        arrow = "▼" if delta_negative else "▲"
        delta_html = f'<div class="metric-delta {delta_class}">{arrow} {delta}</div>'
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

kpi_card(c1, "Net Revenue (Period)",      f"${total_rev/1e6:.2f}M",
         delta=f"+{REVENUE_UPLIFT:.1%} ASP" if apply_pricing else None)
kpi_card(c2, "Gross Profit Margin",       f"{gross_margin_display:.1%}",
         delta=f"−{COGS_REDUCTION:.1%} COGS" if apply_cogs_synergy else None)
kpi_card(c3, "Prime Cost % (COGS+Labor)", f"{avg_prime_pct:.1%}",
         delta=f"−{(COGS_REDUCTION+LABOR_REDUCTION):.1%}" if (apply_cogs_synergy or apply_labor_optim) else None,
         delta_negative=False)
kpi_card(c4, "4-Wall EBITDA Margin",      f"{four_wall_display:.1%}",
         delta=f"+${synergy_uplift/1000:.0f}K uplift" if (apply_cogs_synergy or apply_labor_optim or apply_pricing) else None)
kpi_card(c5, "Consolidated EBITDA Margin",f"{consol_margin:.1%}",
         delta=f"After {ga_pct:.0%} G&A" if True else None,
         delta_negative=False)
kpi_card(c6, "Labor Efficiency (Rev/hr)", f"${labor_efficiency:.2f}",
         delta=f"−{LABOR_REDUCTION:.1%} labor" if apply_labor_optim else None)

st.markdown("<br>", unsafe_allow_html=True)

# ── P&L Summary Strip ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 P&L Waterfall Summary — Formula Hierarchy</div>', unsafe_allow_html=True)

pl_cols = st.columns(8)
pl_items = [
    ("Revenue",          f"${total_rev/1e6:.2f}M",  "#FFFFFF"),
    ("− COGS",           f"({cogs_pct_assumption:.0%})", "#FF6B6B"),
    ("= Gross Profit",   f"{gross_margin_display:.1%}", "#52C97C"),
    ("− Labor",          f"({adj_labor_pct:.0%})",  "#FF6B6B"),
    ("− Occupancy",      f"({occupancy_pct:.0%})",  "#FF6B6B"),
    ("= 4-Wall EBITDA",  f"{four_wall_display:.1%}", "#60A5FA"),
    ("− Corp G&A",       f"({ga_pct:.0%})",         "#FF6B6B"),
    ("= Consol. EBITDA", f"{consol_margin:.1%}",    "#34D399"),
]
for col, (lbl, val, color) in zip(pl_cols, pl_items):
    col.markdown(
        f"<div style='text-align:center;padding:10px 4px;background:#161B27;"
        f"border-radius:8px;border:1px solid #1F2937;'>"
        f"<div style='font-size:9px;color:#A8C8E8;margin-bottom:4px;'>{lbl}</div>"
        f"<div style='font-size:16px;font-weight:700;color:{color};'>{val}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Alert Panel ────────────────────────────────────────────────────────────────
store_prime_pct = df.groupby("Location_Name").apply(
    lambda x: (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum()
)
high_prime_stores = store_prime_pct[store_prime_pct > 0.60]

if not high_prime_stores.empty:
    with st.expander(f"⚠️ {len(high_prime_stores)} Store(s) Exceeding Prime Cost Threshold (>60%)", expanded=True):
        for store, pct in high_prime_stores.items():
            st.markdown(f"""
            <div class="alert-card">
                <strong style="color:#FF6B6B;">{store}</strong>
                <span style="color:#FCA5A5;float:right;font-size:18px;font-weight:700;">{pct:.1%}</span>
                <br><span style="color:#9CA3AF;font-size:12px;">Prime Cost exceeds 60% — review labor scheduling and COGS variances</span>
            </div>
            """, unsafe_allow_html=True)

# ── Chart 1: Prime Cost Heatmap ────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Prime Cost % by Store × Month</div>', unsafe_allow_html=True)

heatmap_df = df.groupby(["Location_Name", "Month"]).apply(
    lambda x: (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum()
).reset_index(name="Prime_Cost_Pct")
heatmap_df["Month_Dt"] = pd.to_datetime(heatmap_df["Month"])
heatmap_df = heatmap_df.sort_values("Month_Dt")
heatmap_pivot = heatmap_df.pivot(index="Location_Name", columns="Month", values="Prime_Cost_Pct")

sorted_months = sorted(heatmap_df["Month"].unique())
heatmap_pivot = heatmap_pivot[sorted_months] if all(m in heatmap_pivot.columns for m in sorted_months) else heatmap_pivot

fig_heat = go.Figure(data=go.Heatmap(
    z=heatmap_pivot.values,
    x=[m for m in heatmap_pivot.columns],
    y=heatmap_pivot.index.tolist(),
    colorscale=[
        [0.00, "#1a472a"],
        [0.45, "#2d6a4f"],
        [0.55, "#52b788"],
        [0.70, "#f4a261"],
        [0.80, "#e76f51"],
        [1.00, "#c1121f"],
    ],
    zmid=0.60, zmin=0.40, zmax=0.85,
    text=[[f"{v:.1%}" if not np.isnan(v) else "N/A" for v in row] for row in heatmap_pivot.values],
    texttemplate="%{text}",
    textfont={"size": 10, "color": "white"},
    hovertemplate="<b>%{y}</b><br>Month: %{x}<br>Prime Cost: %{text}<extra></extra>",
    colorbar=dict(
        title="Prime Cost %", tickformat=".0%",
        tickvals=[0.40, 0.50, 0.60, 0.70, 0.80],
        ticktext=["40%", "50%", "60% ⚠", "70%", "80%"],
        thickness=15, len=0.8,
    ),
))
fig_heat.update_layout(
    title=dict(text="Prime Cost % Heatmap — Red Zone = >60% Threshold", font=dict(color="#EAF2FA", size=14)),
    paper_bgcolor="#0F1117", plot_bgcolor="#0F1117",
    font=dict(color="#A8C8E8", family="Arial"),
    height=320, margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
    yaxis=dict(tickfont=dict(size=10)),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ── Chart 2: Labor Hours vs Sales Volume Scatter ───────────────────────────────
st.markdown('<div class="section-header">🔍 Labor Efficiency — Hours vs. Revenue by Day Part</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([3, 1])

with col_b:
    st.markdown("<br>", unsafe_allow_html=True)
    scatter_granularity = st.selectbox("Granularity", ["Daily", "Weekly"], index=0)
    color_by = st.selectbox("Color By", ["Day_Part", "Location_Name", "Order_Type"], index=0)

with col_a:
    if scatter_granularity == "Daily":
        scatter_df = df.groupby(["Date", "Location_Name", "Day_Part"]).agg(
            Labor_Hours=("Labor_Hours_Allocated", "sum"),
            Net_Sales=("Net_Sales_Adj", "sum"),
            Transactions=("Net_Sales_Adj", "count"),
            Labor_Cost=("Labor_Cost_Adj", "sum"),
        ).reset_index()
    else:
        df["Week_Label"] = df["Date"].dt.strftime("W%V-%Y")
        scatter_df = df.groupby(["Week_Label", "Location_Name", "Day_Part"]).agg(
            Labor_Hours=("Labor_Hours_Allocated", "sum"),
            Net_Sales=("Net_Sales_Adj", "sum"),
            Transactions=("Net_Sales_Adj", "count"),
            Labor_Cost=("Labor_Cost_Adj", "sum"),
        ).reset_index().rename(columns={"Week_Label": "Date"})

    scatter_df["Labor_Efficiency"] = scatter_df["Net_Sales"] / scatter_df["Labor_Hours"].replace(0, np.nan)
    scatter_df["Labor_Cost_Pct"]   = scatter_df["Labor_Cost"] / scatter_df["Net_Sales"].replace(0, np.nan)
    scatter_df = scatter_df.dropna(subset=["Labor_Efficiency"])

    color_col = color_by if color_by in scatter_df.columns else "Day_Part"

    fig_scatter = px.scatter(
        scatter_df, x="Labor_Hours", y="Net_Sales", color=color_col,
        size="Transactions", size_max=18, opacity=0.72,
        color_discrete_sequence=px.colors.qualitative.Bold,
        hover_data={"Labor_Efficiency": ":.2f", "Labor_Cost_Pct": ":.1%"},
        labels={
            "Labor_Hours": "Labor Hours Allocated",
            "Net_Sales": "Net Revenue ($)",
            "Labor_Efficiency": "Revenue per Labor Hour",
        },
        title="Staffing Efficiency Map — Identify Over/Under-Staffed Periods"
    )

    for eff_level, color, label in [
        (35, "#FF6B6B", "< $35/hr = Understaffed"),
        (50, "#F59E0B", "$50/hr = Target"),
        (65, "#52C97C", "> $65/hr = Efficient"),
    ]:
        max_hrs = scatter_df["Labor_Hours"].quantile(0.95)
        fig_scatter.add_trace(go.Scatter(
            x=[0, max_hrs], y=[0, max_hrs * eff_level], mode="lines",
            name=label, line=dict(color=color, width=1.5, dash="dash"), showlegend=True
        ))

    fig_scatter.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8", family="Arial"),
        height=420, margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#2E5F8A", borderwidth=1),
        xaxis=dict(gridcolor="#1F2937"), yaxis=dict(gridcolor="#1F2937"),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Chart 3: Synergy Impact Gauge + P&L Waterfall ─────────────────────────────
st.markdown('<div class="section-header">📈 Synergy Impact Model — EBITDA Uplift Analysis</div>', unsafe_allow_html=True)

col3a, col3b = st.columns([1, 2])

with col3a:
    # Gauge: 4-Wall EBITDA Margin (display capped at FOUR_WALL_MAX)
    gauge_val  = four_wall_display * 100
    gauge_base = min(base_4wall / base_rev if base_rev > 0 else 0, FOUR_WALL_MAX) * 100

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=gauge_val,
        delta={"reference": gauge_base, "valueformat": ".1f", "suffix": "%",
               "increasing": {"color": "#52C97C"}, "decreasing": {"color": "#FF6B6B"}},
        title={"text": "4-Wall EBITDA Margin", "font": {"color": "#EAF2FA", "size": 14}},
        number={"suffix": "%", "font": {"color": "#FFFFFF", "size": 32}},
        gauge={
            "axis": {"range": [-5, 35], "tickwidth": 1, "tickcolor": "#A8C8E8",
                     "tickformat": ".0f", "ticksuffix": "%"},
            "bar": {"color": "#2E5F8A", "thickness": 0.28},
            "bgcolor": "#161B27", "borderwidth": 2, "bordercolor": "#1F2937",
            "steps": [
                {"range": [-5, 0],  "color": "#7F1D1D"},
                {"range": [0,  10], "color": "#991B1B"},
                {"range": [10, 15], "color": "#B45309"},
                {"range": [15, 25], "color": "#166534"},   # target range
                {"range": [25, 35], "color": "#064E3B"},
            ],
            "threshold": {
                "line": {"color": "#F59E0B", "width": 3},
                "thickness": 0.85, "value": 20,            # 20% = midpoint of 15-25% target
            },
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="#0F1117", font=dict(color="#A8C8E8", family="Arial"),
        height=280, margin=dict(l=30, r=30, t=40, b=10),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)
    st.caption(f"Target: 15–25% | Consolidated EBITDA: {consol_margin:.1%}")

    # Synergy breakdown
    synergy_items = []
    if apply_cogs_synergy:
        synergy_items.append(("Vendor Consolidation (−2% COGS)", total_rev * adj_cogs_pct * COGS_REDUCTION / (1 - COGS_REDUCTION) if COGS_REDUCTION else total_rev * cogs_pct_assumption * COGS_REDUCTION))
    if apply_labor_optim:
        synergy_items.append(("Labor Scheduling (−1.5% Labor)", total_rev * labor_pct_assumption * LABOR_REDUCTION))
    if apply_pricing:
        synergy_items.append(("Pricing Power (+1.5% ASP)", base_rev * REVENUE_UPLIFT))

    if synergy_items:
        syn_df = pd.DataFrame(synergy_items, columns=["Synergy", "Annual Uplift ($)"])
        syn_df["Annual Uplift ($)"] = syn_df["Annual Uplift ($)"].map("${:,.0f}".format)
        st.dataframe(syn_df, hide_index=True, use_container_width=True)
    else:
        st.info("Enable synergies in sidebar to see uplift breakdown.")

with col3b:
    # ── P&L Waterfall: Full Formula Hierarchy ─────────────────────────────────
    # Gross Profit = Revenue − COGS
    # 4-Wall EBITDA = Gross Profit − Labor − Occupancy
    # Consolidated EBITDA = 4-Wall EBITDA − G&A
    waterfall_items = [
        ("Net Revenue",           total_rev,            "total"),
        ("(−) COGS",             -total_cogs,           "relative"),
        ("= Gross Profit",        gross_profit,          "total"),
        ("(−) Direct Labor",     -total_labor,          "relative"),
        ("(−) Occupancy & OpEx", -occupancy_cost,       "relative"),
        ("= 4-Wall EBITDA",       four_wall_ebitda,      "total"),
        ("(−) Corporate G&A",    -ga_cost,              "relative"),
        ("= Consol. EBITDA",      consol_ebitda,         "total"),
    ]

    measures = [w[2] for w in waterfall_items]
    labels   = [w[0] for w in waterfall_items]
    values   = [w[1] for w in waterfall_items]
    pct_labels = []
    for lbl, val, meas in waterfall_items:
        if meas == "total" and total_rev > 0:
            pct_labels.append(f"${abs(val)/1000:.0f}K ({val/total_rev:.1%})")
        else:
            pct_labels.append(f"${abs(val)/1000:.0f}K ({abs(val)/total_rev:.1%})")

    fig_wf = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=labels, y=values,
        text=pct_labels, textposition="outside",
        textfont=dict(color="#EAF2FA", size=9),
        connector={"line": {"color": "#2E5F8A", "width": 1.5, "dash": "dot"}},
        increasing={"marker": {"color": "#166534", "line": {"color": "#52C97C", "width": 1}}},
        decreasing={"marker": {"color": "#991B1B", "line": {"color": "#FF6B6B", "width": 1}}},
        totals={"marker":    {"color": "#1B2A4A", "line": {"color": "#2E5F8A", "width": 2}}},
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
    ))
    fig_wf.update_layout(
        title=dict(text="P&L Waterfall — Revenue → Gross Profit → 4-Wall → Consolidated EBITDA",
                   font=dict(color="#EAF2FA", size=13)),
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8", family="Arial"),
        height=420, margin=dict(l=20, r=20, t=50, b=90),
        yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
        xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
        showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# ── Store-Level Scorecard ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">🏪 Store-Level Performance Scorecard</div>', unsafe_allow_html=True)

# Per-store occupancy: allocate proportionally by store revenue share
store_rev_totals = df.groupby("Location_Name")["Net_Sales_Adj"].sum()
store_rev_share  = store_rev_totals / store_rev_totals.sum()

store_kpi = df.groupby("Location_Name").apply(lambda x: pd.Series({
    "Net Revenue ($)":    x["Net_Sales_Adj"].sum(),
    "Transactions":       len(x),
    "Avg Check ($)":      x["Net_Sales_Adj"].mean(),
    "Gross Margin %":     x["Gross_Profit_Adj"].sum() / x["Net_Sales_Adj"].sum(),
    "COGS %":             x["COGS_Adj"].sum() / x["Net_Sales_Adj"].sum(),
    "Labor %":            x["Labor_Cost_Adj"].sum() / x["Net_Sales_Adj"].sum(),
    "Prime Cost %":       (x["COGS_Adj"] + x["Labor_Cost_Adj"]).sum() / x["Net_Sales_Adj"].sum(),
    "Occupancy %":        occupancy_pct,   # applied uniformly (sidebar assumption)
    "4-Wall EBITDA %":    (x["Gross_Profit_Adj"].sum() - x["Labor_Cost_Adj"].sum()
                           - x["Net_Sales_Adj"].sum() * occupancy_pct) / x["Net_Sales_Adj"].sum(),
    "Labor Eff. ($/hr)":  x["Net_Sales_Adj"].sum() / x["Labor_Hours_Allocated"].sum(),
    "Discount Rate":      x["Discount_Amount"].sum() / x["Gross_Sales"].sum(),
})).reset_index()

def highlight_margin(val, col_name):
    if not isinstance(val, float): return ""
    if col_name == "Prime Cost %":
        if val > 0.65: return "background-color:#7F1D1D;color:#FCA5A5;font-weight:700"
        elif val > 0.60: return "background-color:#B45309;color:#FDE68A;font-weight:700"
        elif val < 0.52: return "background-color:#064E3B;color:#6EE7B7"
    elif col_name == "4-Wall EBITDA %":
        if val > 0.25: return "background-color:#064E3B;color:#6EE7B7;font-weight:700"
        elif val > 0.15: return "background-color:#166534;color:#BBF7D0"
        elif val < 0.05: return "background-color:#7F1D1D;color:#FCA5A5"
    return ""

fmt_dict = {
    "Net Revenue ($)":   "${:,.0f}",
    "Transactions":      "{:,.0f}",
    "Avg Check ($)":     "${:.2f}",
    "Gross Margin %":    "{:.1%}",
    "COGS %":            "{:.1%}",
    "Labor %":           "{:.1%}",
    "Prime Cost %":      "{:.1%}",
    "Occupancy %":       "{:.1%}",
    "4-Wall EBITDA %":   "{:.1%}",
    "Labor Eff. ($/hr)": "${:.2f}",
    "Discount Rate":     "{:.2%}",
}

styled = store_kpi.style.format(fmt_dict)
for col in ["Prime Cost %", "4-Wall EBITDA %"]:
    styled = styled.map(lambda v: highlight_margin(v, col), subset=[col]) if hasattr(styled, "map") else styled.applymap(lambda v: highlight_margin(v, col), subset=[col])
styled = styled.set_properties(**{
    "background-color": "#161B27", "color": "#EAF2FA", "border": "1px solid #1F2937"
})

st.dataframe(styled, hide_index=True, use_container_width=True, height=240)

# Benchmark reference
st.caption(
    "📏 Benchmarks: COGS 28–34% | Labor 25–32% | Prime Cost <62% | "
    "Occupancy 12–18% | 4-Wall EBITDA 15–25%"
)

# ── Monthly Revenue Trend ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">📉 Monthly Revenue Trend by Store</div>', unsafe_allow_html=True)

monthly_rev = df.groupby(["Month", "Location_Name"])["Net_Sales_Adj"].sum().reset_index()
monthly_rev["Month_Dt"] = pd.to_datetime(monthly_rev["Month"])
monthly_rev = monthly_rev.sort_values("Month_Dt")

fig_trend = px.line(
    monthly_rev, x="Month", y="Net_Sales_Adj", color="Location_Name",
    markers=True,
    color_discrete_sequence=["#60A5FA","#34D399","#FBBF24","#F87171","#A78BFA"],
    labels={"Net_Sales_Adj": "Net Revenue ($)", "Month": "Month", "Location_Name": "Store"},
    title="Monthly Net Revenue by Location — 24-Month View"
)
fig_trend.update_traces(line=dict(width=2.5), marker=dict(size=6))
fig_trend.update_layout(
    paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
    font=dict(color="#A8C8E8", family="Arial"),
    height=360, margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#2E5F8A", borderwidth=1,
                orientation="h", y=-0.15),
    xaxis=dict(gridcolor="#1F2937", tickangle=-45, tickfont=dict(size=9)),
    yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
)
st.plotly_chart(fig_trend, use_container_width=True)

# ── Day Part & Category Mix ────────────────────────────────────────────────────
col_dp1, col_dp2 = st.columns(2)

with col_dp1:
    dp_mix = df.groupby(["Day_Part", "Order_Type"])["Net_Sales_Adj"].sum().reset_index()
    fig_dp = px.bar(
        dp_mix, x="Day_Part", y="Net_Sales_Adj", color="Order_Type",
        barmode="stack",
        color_discrete_sequence=["#3B82F6","#10B981","#F59E0B"],
        labels={"Net_Sales_Adj": "Net Revenue ($)", "Day_Part": "Day Part"},
        title="Revenue Mix — Day Part × Order Channel"
    )
    fig_dp.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8"), height=300,
        margin=dict(l=20,r=20,t=50,b=20),
        xaxis=dict(gridcolor="#1F2937"), yaxis=dict(gridcolor="#1F2937",tickformat="$,.0f"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_dp, use_container_width=True)

with col_dp2:
    cat_mix = df.groupby(["Category", "Location_Name"])["Net_Sales_Adj"].sum().reset_index()
    fig_cat = px.bar(
        cat_mix, x="Location_Name", y="Net_Sales_Adj", color="Category",
        barmode="group",
        color_discrete_sequence=["#6366F1","#14B8A6","#F97316"],
        labels={"Net_Sales_Adj": "Net Revenue ($)", "Location_Name": "Store"},
        title="Revenue by Category — Cross-Store Comparison"
    )
    fig_cat.update_layout(
        paper_bgcolor="#0F1117", plot_bgcolor="#161B27",
        font=dict(color="#A8C8E8"), height=300,
        margin=dict(l=20,r=20,t=50,b=20),
        xaxis=dict(gridcolor="#1F2937", tickangle=-20),
        yaxis=dict(gridcolor="#1F2937", tickformat="$,.0f"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center;color:#4B5563;font-size:11px;padding:12px;">
    Project Harvest — Operational Intelligence Platform ·
    {len(df):,} transactions analyzed ·
    Period: {start_dt.strftime('%b %d, %Y')} – {end_dt.strftime('%b %d, %Y')} ·
    <em>Confidential — Investment Committee Use Only</em>
</div>
""", unsafe_allow_html=True)
