# 🌾 Project Harvest — Operational Intelligence Dashboard

> **An institutional-grade private equity analytics project bridging store-level operational data with M&A deal modeling for a fast casual restaurant platform rollup.**

---

## Live Dashboard

[project-harvest-gz9bxcmgxuy7xby4sp9cuq](https://project-harvest-gz9bxcmgxuy7xby4sp9cuq.streamlit.app/)

---

## Project Overview

Project Harvest is a two-part private equity analytical deliverable built to demonstrate the full analytical stack expected of a PE operations analyst — from raw transaction-level data through investment committee-ready financial modeling.

**Part 1** is an interactive Streamlit dashboard that ingests 50,000+ daily POS transactions across five restaurant locations and 24 months, computes operational KPIs, and surfaces portfolio-level insights with dynamic scenario modeling.

**Part 2** is an institutional-grade Excel deal model covering the full platform rollup — initial platform acquisition, three bolt-on add-ons, a 3-tier synergy schedule, integrated 3-statement model with debt waterfall, and a returns analysis with 2-way sensitivity matrix.

---

## Dashboard Features

### Executive KPI Header
Five dynamic cards updating in real time based on sidebar filters and scenario toggles:
- Net Revenue (period)
- Prime Cost %
- 4-Wall EBITDA Margin
- Average Check Size
- Labor Efficiency (Revenue per Labor Hour)

### Interactive Controls
- **Store filter** — select any combination of the five locations
- **Date range slider** — zoom into any period within the 24-month window
- **Order type filter** — Dine-in, Takeout, Delivery
- **Day part filter** — Lunch, Dinner, Late Night
- **Scenario toggles** — three independent synergy levers:
  - Supply Chain Synergies (−2% COGS via vendor consolidation)
  - Labor Optimization (−1.5% labor via centralized scheduling)
  - Pricing Power (+1.5% average check via menu re-engineering)

### Visual Sections
- **Prime Cost Heatmap** — store × month grid with red zone highlighting above the 60% threshold
- **Labor Efficiency Scatter** — labor hours vs. revenue by day part with staffing benchmark lines at $35, $50, and $65 per hour
- **EBITDA Waterfall** — revenue to 4-wall EBITDA P&L build
- **EBITDA Margin Gauge** — live gauge with delta vs. baseline
- **Store Scorecard** — cross-store KPI table with conditional formatting (red above 60% prime cost, green below 52%)
- **Monthly Revenue Trend** — 24-month line chart by location
- **Day Part & Category Mix** — stacked and grouped bar charts
- **S004 Plano Legacy Deep Dive** — dual-axis chart isolating the Q3 operational variance with month-by-month labor and COGS spike

### Operational Variances Injected
The synthetic dataset includes realistic operational variances designed to surface meaningful analytical findings:

| Store | Variance |
|-------|----------|
| S004 Plano Legacy | High labor overtime + food waste in Q3 (Jul–Sep) — prime cost spikes to ~71% |
| S003 Deep Ellum | Alcohol license suspension Apr–Jun Year 2 — 15% volume decline |
| S001 Downtown Dallas | Catering contract boost Q2–Q3 — 12% volume uplift |
| S005 Frisco Hub | Growth store ramp — progressive volume increase through Year 1 |

---

## Excel Deal Model — ProjectHarvest_DealModel.xlsx

Five tabs covering the full M&A and financial modeling workflow.

### Tab 1: Deal Assumptions
Centralized input sheet with yellow-filled analyst inputs. All downstream tabs reference this sheet — change any assumption and the entire model updates.

- Platform Co: $15M LTM Revenue, $3M LTM EBITDA, 8.0x entry multiple
- Add-On Targets: 3 bolt-ons at $2M revenue each, 4.5x entry multiple
- Capital structure: 4.0x senior leverage, 8.5% interest rate, 5% mandatory amortization
- 3-tier synergy schedule with 24-month ramp curve

### Tab 2: AJE Schedule & Comparative Balance Sheet
Nine labeled acquisition journal entries (AJE #1 through AJE #9) covering platform entry, add-on acquisitions, transaction fees, three synergy tiers, implementation costs, debt issuance, and equity contribution.

Comparative Balance Sheet across four adjustment columns:
- **Column C** — Pre-Acquisition
- **Column D** — Platform Acquisition Adjustment
- **Column E** — Add-On Adjustment
- **Column G** — Post-Acquisition Pro Forma

### Tab 3: 3-Statement Integrated Model
Full five-year income statement, debt schedule, and cash flow statement (indirect method).

- Revenue grows from combined entity base at formula-driven rate
- Synergy benefit line pulls directly from AJE schedule at 24-month ramp percentages
- FCF sweep wired to mandatory debt paydown — 100% excess cash applied to term loan
- Interest expense linked from average debt balance in debt schedule
- Tax provision, D&A, CapEx, and NWC change all formula-driven

### Tab 4: Exit & Returns Waterfall
Three scenario columns — Base Case, Upside, Downside — with independent EBITDA growth rate and exit multiple assumptions.

- Exit TEV, net debt deduction, sell-side fees, gross equity proceeds
- MOIC (gross and net), IRR (gross and net), DPI, leverage at entry and exit
- Base case: 9.0x exit multiple, 6.5% organic EBITDA growth

### Tab 5: 2-Way Sensitivity Matrix
Two 9×9 matrices covering Exit Multiple (7.0x–11.0x) vs. EBITDA Growth Rate (2%–10%):
- **Matrix A** — Gross MOIC
- **Matrix B** — Gross IRR

Color coded: green above 3.0x MOIC / 25% IRR, yellow 2.0x–3.0x / 15%–25%, red below threshold. Base case cell highlighted in orange.

---

## Repository Structure

```
project-harvest/
├── app.py              # Streamlit dashboard — self-contained, no CSV required
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

The dashboard auto-generates all transaction data on first load. No external data files or API keys required.

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| Dashboard framework | Streamlit |
| Visualization | Plotly (Express + Graph Objects) |
| Data manipulation | Pandas, NumPy |
| Financial model | Excel (openpyxl) |
| Hosting | Streamlit Community Cloud |
| Version control | GitHub |

---

## Running Locally

```bash
# Install dependencies
pip install pandas numpy streamlit plotly

# Launch the dashboard
streamlit run app.py
```

The app opens at `http://localhost:8501`. Data generates automatically on first load (~20 seconds) and is cached for the session.

---

## Deal Model Assumptions Summary

| Parameter | Value |
|-----------|-------|
| Platform LTM Revenue | $15,000,000 |
| Platform LTM EBITDA | $3,000,000 |
| Platform Entry Multiple | 8.0x |
| Add-On Revenue (each) | $2,000,000 |
| Add-On Entry Multiple | 4.5x |
| Number of Add-Ons | 3 |
| Multiple Arbitrage Gain | Immediate equity value from 4.5x → 8.0x re-rating |
| Senior Leverage | 4.0x EBITDA |
| Interest Rate | 8.5% |
| Mandatory Amortization | 5% annually |
| FCF Sweep | 100% excess cash |
| Exit Multiple (Base) | 9.0x |
| Hold Period | 5 years |
| Synergy Run-Rate | ~$550K annually (Tier 1 + 2 + 3) |

---

## About

Built as an independent financial modeling project demonstrating analytical capabilities across operational data engineering, interactive dashboard development, and institutional-grade private equity deal modeling in the restaurant and food & beverage sector.

*Confidential — all financial figures are illustrative and for analytical demonstration purposes only.*
