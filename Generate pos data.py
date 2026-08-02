"""
Project Harvest — POS Transaction Data Generator
Generates 10,000+ daily ticket-level records across 5 store locations, 24 months.
Injects realistic operational variances including Store #4 high labor / food waste in Q3.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

# ── Store Configuration ────────────────────────────────────────────────────────
STORES = {
    "S001": {"name": "Downtown Dallas",  "base_daily_txn": 85, "avg_check": 28.50, "tier": "flagship"},
    "S002": {"name": "Uptown",           "base_daily_txn": 72, "avg_check": 31.20, "tier": "premium"},
    "S003": {"name": "Deep Ellum",       "base_daily_txn": 68, "avg_check": 24.80, "tier": "standard"},
    "S004": {"name": "Plano Legacy",     "base_daily_txn": 60, "avg_check": 26.40, "tier": "standard"},
    "S005": {"name": "Frisco Hub",       "base_daily_txn": 55, "avg_check": 27.10, "tier": "growth"},
}

# ── Day Part Configuration ─────────────────────────────────────────────────────
DAY_PARTS = {
    "Lunch":      {"hours": (11, 14), "weight": 0.42, "check_mult": 0.85},
    "Dinner":     {"hours": (17, 21), "weight": 0.45, "check_mult": 1.10},
    "Late Night": {"hours": (21, 24), "weight": 0.13, "check_mult": 0.90},
}

CATEGORIES = {
    "Food":     {"weight": 0.58, "cogs_pct_range": (0.28, 0.34)},
    "Beverage": {"weight": 0.27, "cogs_pct_range": (0.18, 0.24)},
    "Alcohol":  {"weight": 0.15, "cogs_pct_range": (0.22, 0.28)},
}

ORDER_TYPES = {
    "Dine-in":  {"weight": 0.52, "check_mult": 1.12, "labor_factor": 1.15},
    "Takeout":  {"weight": 0.31, "check_mult": 0.95, "labor_factor": 0.85},
    "Delivery": {"weight": 0.17, "check_mult": 1.05, "labor_factor": 0.70},
}

# ── Seasonal Factors (monthly) ─────────────────────────────────────────────────
MONTHLY_SEASONAL = {
    1:  0.88,  2: 0.85,  3: 0.92,  4: 0.98,
    5:  1.05,  6: 1.08,  7: 1.06,  8: 1.02,
    9:  0.97, 10: 0.99, 11: 1.03, 12: 1.15,
}

DAY_OF_WEEK_FACTOR = {
    0: 0.82,  # Monday
    1: 0.85,  # Tuesday
    2: 0.90,  # Wednesday
    3: 0.95,  # Thursday
    4: 1.15,  # Friday
    5: 1.25,  # Saturday
    6: 1.08,  # Sunday
}

def get_store_variances(store_id: str, date: datetime) -> dict:
    """
    Inject realistic operational variances per store.
    Store S004: High labor overtime and food waste in Q3 (Jul-Sep).
    Store S003: Declining performance in Year 2 (alcohol license issue).
    Store S001: Premium performance driven by catering contracts.
    """
    month = date.month
    year_offset = (date.year - 2023)  # 0 for 2023, 1 for 2024

    variances = {
        "cogs_uplift":   0.0,
        "labor_uplift":  0.0,
        "check_uplift":  0.0,
        "volume_uplift": 0.0,
        "discount_rate": 0.04,
    }

    if store_id == "S004":
        # Q3 food waste crisis + overtime labor
        if month in [7, 8, 9]:
            variances["cogs_uplift"]   += 0.062   # +6.2% COGS from food waste
            variances["labor_uplift"]  += 0.078   # +7.8% labor (overtime)
            variances["volume_uplift"] -= 0.08    # -8% volume (poor mgmt)
        # Gradual recovery Q4
        if month in [10, 11, 12]:
            variances["cogs_uplift"]   += 0.020
            variances["labor_uplift"]  += 0.025

    if store_id == "S003":
        # Alcohol license suspension April-June Year 2
        if year_offset == 1 and month in [4, 5, 6]:
            variances["volume_uplift"] -= 0.15
            variances["check_uplift"]  -= 0.08    # lost high-check alcohol orders

    if store_id == "S001":
        # Catering contract boost (B2B volume) Q2 + Q3
        if month in [5, 6, 7, 8]:
            variances["volume_uplift"] += 0.12
            variances["check_uplift"]  += 0.06

    if store_id == "S005":
        # Growth store — ramping up through Year 1, plateau in Year 2
        if year_offset == 0:
            ramp = min(0.18, month * 0.015)
            variances["volume_uplift"] += ramp
        else:
            variances["volume_uplift"] += 0.18

    return variances


def generate_timestamp(date: datetime, day_part: str) -> str:
    hours_range = DAY_PARTS[day_part]["hours"]
    hour = random.randint(hours_range[0], hours_range[1] - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(date.year, date.month, date.day, hour, minute, second).strftime("%Y-%m-%d %H:%M:%S")


def generate_transactions(start_date: str = "2023-01-01",
                          months: int = 24,
                          target_records: int = 12000) -> pd.DataFrame:
    """Main generator function."""
    print(f"Generating ~{target_records:,} POS transactions across {months} months...")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = start + timedelta(days=months * 30)

    all_dates   = pd.date_range(start, end, freq='D')
    store_ids   = list(STORES.keys())
    day_part_list   = list(DAY_PARTS.keys())
    category_list   = list(CATEGORIES.keys())
    order_type_list = list(ORDER_TYPES.keys())

    records = []
    txn_counter = 1

    for date in all_dates:
        dt = date.to_pydatetime()
        dow_factor  = DAY_OF_WEEK_FACTOR[dt.weekday()]
        seas_factor = MONTHLY_SEASONAL[dt.month]

        for store_id in store_ids:
            store_cfg = STORES[store_id]
            variances = get_store_variances(store_id, dt)

            # Determine number of transactions today
            base_txn = store_cfg["base_daily_txn"]
            vol_factor = 1.0 + variances["volume_uplift"]
            n_txn = max(5, int(np.random.poisson(base_txn * dow_factor * seas_factor * vol_factor)))

            # Distribute across day parts
            dp_weights = [DAY_PARTS[dp]["weight"] for dp in day_part_list]
            txn_by_dp = np.random.multinomial(n_txn, dp_weights)

            for dp_idx, dp_name in enumerate(day_part_list):
                for _ in range(txn_by_dp[dp_idx]):
                    # Order type
                    ot_weights = [ORDER_TYPES[ot]["weight"] for ot in order_type_list]
                    order_type = np.random.choice(order_type_list, p=ot_weights)
                    ot_cfg = ORDER_TYPES[order_type]

                    # Category
                    cat_weights = [CATEGORIES[c]["weight"] for c in category_list]
                    category = np.random.choice(category_list, p=cat_weights)
                    cat_cfg = CATEGORIES[category]

                    # Gross sales
                    base_check = store_cfg["avg_check"]
                    dp_mult    = DAY_PARTS[dp_name]["check_mult"]
                    ot_mult    = ot_cfg["check_mult"]
                    chk_uplift = 1.0 + variances["check_uplift"]
                    check_noise = np.random.lognormal(0, 0.22)

                    gross_sales = round(
                        base_check * dp_mult * ot_mult * chk_uplift * check_noise * seas_factor,
                        2
                    )
                    gross_sales = max(8.0, gross_sales)

                    # Discount
                    disc_rate = variances["discount_rate"] * np.random.exponential(1.0)
                    disc_rate = min(disc_rate, 0.25)
                    discount_amt = round(gross_sales * disc_rate, 2)
                    net_sales    = round(gross_sales - discount_amt, 2)

                    # COGS
                    cogs_pct = np.random.uniform(*cat_cfg["cogs_pct_range"])
                    cogs_pct += variances["cogs_uplift"]
                    cogs_pct  = min(cogs_pct, 0.72)
                    cogs      = round(net_sales * cogs_pct, 2)

                    # Labor (allocated at transaction level)
                    base_labor_hrs = net_sales / np.random.uniform(38, 58)
                    base_labor_hrs *= ot_cfg["labor_factor"]
                    base_labor_hrs *= (1.0 + variances["labor_uplift"])
                    base_labor_hrs  = max(0.01, base_labor_hrs)
                    labor_hrs = round(base_labor_hrs, 4)

                    # Wage rate ($16-$22/hr + overtime premium for S004 Q3)
                    base_wage = np.random.uniform(16.5, 21.5)
                    if store_id == "S004" and dt.month in [7, 8, 9]:
                        base_wage *= 1.18  # overtime premium
                    labor_cost = round(labor_hrs * base_wage, 2)

                    # Table size
                    table_size = max(1, int(np.random.choice(
                        [1, 2, 3, 4, 5, 6, 8],
                        p=[0.18, 0.30, 0.22, 0.17, 0.07, 0.04, 0.02]
                    )))
                    if order_type in ["Takeout", "Delivery"]:
                        table_size = 0

                    records.append({
                        "Transaction_ID":        f"TXN-{txn_counter:07d}",
                        "Date":                  dt.strftime("%Y-%m-%d"),
                        "Timestamp":             generate_timestamp(dt, dp_name),
                        "Store_ID":              store_id,
                        "Location_Name":         store_cfg["name"],
                        "Day_Part":              dp_name,
                        "Category":              category,
                        "Gross_Sales":           gross_sales,
                        "Discount_Amount":       discount_amt,
                        "Net_Sales":             net_sales,
                        "Cost_of_Goods_Sold":    cogs,
                        "Labor_Hours_Allocated": labor_hrs,
                        "Labor_Cost":            labor_cost,
                        "Table_Size":            table_size,
                        "Order_Type":            order_type,
                    })
                    txn_counter += 1

    df = pd.DataFrame(records)
    print(f"Generated {len(df):,} transactions.")
    return df


if __name__ == "__main__":
    df = generate_transactions(start_date="2023-01-01", months=24)

    # Derived fields
    df["Date"]  = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Year"]  = df["Date"].dt.year
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)

    # Prime Cost (COGS + Labor) / Net Sales at transaction level
    df["Prime_Cost"]    = df["Cost_of_Goods_Sold"] + df["Labor_Cost"]
    df["Prime_Cost_Pct"]= df["Prime_Cost"] / df["Net_Sales"].replace(0, np.nan)
    df["COGS_Pct"]      = df["Cost_of_Goods_Sold"] / df["Net_Sales"].replace(0, np.nan)
    df["Labor_Pct"]     = df["Labor_Cost"] / df["Net_Sales"].replace(0, np.nan)

    out = "pos_transactions.csv"
    df.to_csv(out, index=False)
    print(f"Saved to {out} ({os.path.getsize(out)/1024:.1f} KB)")

    # Summary stats
    print("\n── Summary ──────────────────────────────────────────")
    print(f"Date range:      {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"Total records:   {len(df):,}")
    print(f"Total Net Sales: ${df['Net_Sales'].sum():,.0f}")
    print(f"Avg Check Size:  ${df['Net_Sales'].mean():.2f}")
    print(f"Avg Prime Cost:  {df['Prime_Cost_Pct'].mean():.1%}")
    print(f"\nBy Store:")
    store_summary = df.groupby("Location_Name").agg(
        Transactions=("Net_Sales","count"),
        Net_Sales=("Net_Sales","sum"),
        Avg_Prime_Cost=("Prime_Cost_Pct","mean")
    ).round(4)
    print(store_summary.to_string())
