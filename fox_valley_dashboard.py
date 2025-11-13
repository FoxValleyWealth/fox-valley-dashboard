# ================================================================
# 🧭 Fox Valley Intelligence Engine – Enterprise Command Deck
# Version: v7.3R-4.5 "Fidelity Autopilot Edition"
# Full-file replacement for fox_valley_dashboard.py
# Auto-detects latest files + fully auto-maps ALL Fidelity formats
# Author: #1 for CaptPicard
# ================================================================

import os
import io
import math
import time
import zipfile
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# ----------------------------------------------------------------
# PAGE CONFIG & VISUAL FRAMEWORK
# ----------------------------------------------------------------
st.set_page_config(
    page_title="Fox Valley Command Deck v7.3R-4.5 — Fidelity Autopilot",
    page_icon="🧭",
    layout="wide"
)

st.markdown(
    """
    <style>
        div.block-container {
            padding-top: 1.5rem;
            max-width: 1750px;
        }
        .section-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }
        .metric-good { color: #22c55e; font-weight: 600; }
        .metric-warn { color: #f59e0b; font-weight: 600; }
        .metric-bad { color: #ef4444; font-weight: 700; }
        th, td {
            font-size: 0.95rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------------------
# CONSTANTS & DATA PATH
# ----------------------------------------------------------------
DATA_PATH = "data"

# ----------------------------------------------------------------
# FIDELITY AUTO-MAPPING ENGINE (NEW FOR v7.3R-4.5)
# ----------------------------------------------------------------
# This module makes the Command Deck compatible with:
#  - Older Fidelity CSVs
#  - Newer Fidelity CSVs (Nov 2025+)
#  - Future Fidelity format updates
# by translating whatever Fidelity exports → Command Deck internal schema.
# ----------------------------------------------------------------

FIDELITY_COLUMN_MAP = {
    # Ticker / Symbol
    "Symbol": "Ticker",
    "Ticker": "Ticker",

    # Shares / Quantity
    "Quantity": "Shares",
    "Shares": "Shares",

    # Last Price / Current Price
    "Last Price": "Current Price",
    "Price": "Current Price",
    "Current Price": "Current Price",

    # Value
    "Current Value": "Current Value",
    "Market Value": "Current Value",
    "Value": "Current Value",

    # Day Gain
    "Today's Gain/Loss Dollar": "Day Gain",
    "Day Gain": "Day Gain",

    # % Gain Today
    "Today's Gain/Loss Percent": "Day Gain %",

    # Total Gain %
    "Total Gain/Loss Percent": "Gain/Loss %",
    "Gain/Loss %": "Gain/Loss %",

    # Total Gain $
    "Total Gain/Loss Dollar": "Gain/Loss $",

    # Cost Basis
    "Cost Basis Total": "Cost Basis",
    "Cost Basis": "Cost Basis",

    # Average Cost
    "Average Cost Basis": "Average Cost",
    "Average Cost": "Average Cost",
}


def fidelity_auto_map(df: pd.DataFrame) -> pd.DataFrame:
    """
    Automatically renames Fidelity columns to Command Deck internal names.
    Returns a DataFrame with consistent, predictable column names.
    """

    col_map = {}
    for col in df.columns:
        clean = col.strip()
        if clean in FIDELITY_COLUMN_MAP:
            col_map[col] = FIDELITY_COLUMN_MAP[clean]

    df = df.rename(columns=col_map)

    # Convert money-like values to floats
    def scrub(x):
        if pd.isna(x):
            return np.nan
        if isinstance(x, (int, float)):
            return x
        s = str(x).replace("$", "").replace(",", "").replace("%", "").strip()
        neg = s.startswith("(") and s.endswith(")")
        s = s.replace("(", "").replace(")", "")
        try:
            v = float(s)
            return -v if neg else v
        except:
            return np.nan

    numeric_cols = [
        "Shares", "Current Price", "Current Value", "Gain/Loss %",
        "Gain/Loss $", "Day Gain", "Cost Basis", "Average Cost"
    ]

    for c in numeric_cols:
        if c in df.columns:
            df[c] = df[c].apply(scrub)

    # If Shares and Current Price exist, compute Value
    if "Shares" in df.columns and "Current Price" in df.columns:
        df["Current Value"] = df["Shares"] * df["Current Price"]

    # Ensure Ticker exists
    if "Ticker" not in df.columns:
        # Try Symbol if needed
        if "Symbol" in df.columns:
            df["Ticker"] = df["Symbol"].astype(str)
        else:
            df["Ticker"] = "UNKNOWN"

    return df


# ----------------------------------------------------------------
# FILE DISCOVERY ENGINE (AUTO-DETECT LATEST FILE)
# ----------------------------------------------------------------
def get_latest_file(keyword: str):
    """
    Find the latest CSV in /data that matches the keyword.
    Ignores archive_ files completely.
    """
    files = [
        f for f in os.listdir(DATA_PATH)
        if keyword.lower() in f.lower()
        and f.endswith(".csv")
        and not f.lower().startswith("archive_")
    ]
    if not files:
        return None
    latest = max(files, key=lambda f:
                 os.path.getmtime(os.path.join(DATA_PATH, f)))
    return os.path.join(DATA_PATH, latest), latest


# ----------------------------------------------------------------
# UNIFIED CSV LOADER (NOW AUTO-MAPS FIDELITY)
# ----------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv_auto(keyword: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Loads the most recent file matching keyword.
    Also applies Fidelity column remapping.
    """

    messages = []
    path_info = get_latest_file(keyword)

    if not path_info:
        return pd.DataFrame(), [f"No file found for keyword '{keyword}'"]

    path, filename = path_info

    try:
        df = pd.read_csv(path, low_memory=False)
        messages.append(f"Loaded latest: {filename}")
    except Exception as e:
        return pd.DataFrame(), [f"Failed to load {filename}: {e}"]

    # Apply Fidelity → Command Deck mapping
    df = fidelity_auto_map(df)

    return df, messages
# ================================================================
# SECTION B — Data Load Engine / Sidebar / Portfolio Overview
# ================================================================

# ----------------------------------------------------------------
# LOAD ALL DATASETS (auto-detected & auto-mapped)
# ----------------------------------------------------------------
portfolio_df, pf_msg = load_csv_auto("Portfolio_Positions")
g1_df, g1_msg = load_csv_auto("Growth 1")
g2_df, g2_msg = load_csv_auto("Growth 2")
dd_df, dd_msg = load_csv_auto("Defensive")

# ----------------------------------------------------------------
# SIDEBAR — MANUAL CASH & TRAILING STOP CONTROL
# ----------------------------------------------------------------
st.sidebar.title("🧭 Command Deck v7.3R-4.5 — Fidelity Autopilot")
st.sidebar.caption(f"Build Initialized | {datetime.now():%b %d %Y}")

manual_cash = st.sidebar.number_input(
    "💰 Manual Cash Override ($)",
    min_value=0.0, step=100.0, value=0.0, format="%.2f",
    help="Enter current Fidelity cash balance to override auto-detect."
)
default_stop = st.sidebar.slider("Default Trailing Stop %", 1, 50, 10)

st.sidebar.markdown("---")
st.sidebar.write("### Diagnostics")
for msg in pf_msg + g1_msg + g2_msg + dd_msg:
    st.sidebar.text(msg)

# ----------------------------------------------------------------
# MAIN HEADER
# ----------------------------------------------------------------
st.title("🧭 Fox Valley Intelligence Engine — Enterprise Command Deck")
st.caption("v7.3R-4.5 Fidelity Autopilot Edition | Portfolio + Zacks + Trend Engine Online")
st.markdown("---")

# ----------------------------------------------------------------
# PORTFOLIO OVERVIEW / SUMMARY METRICS
# ----------------------------------------------------------------
st.subheader("📊 Portfolio Overview")

if not portfolio_df.empty:
    # detect value column
    val_col = next((c for c in ["Current Value","Market Value","Value"] if c in portfolio_df.columns), None)
    total_val = float(portfolio_df[val_col].sum()) if val_col else 0.0
    cash_val = manual_cash

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated Total Value", f"${total_val:,.2f}")
    c2.metric("Cash Available to Trade", f"${cash_val:,.2f}")

    day_gain = pd.to_numeric(portfolio_df.get("Day Gain", pd.Series(dtype=float)), errors='coerce')
    c3.metric("Day Gain (sum)", f"${day_gain.sum():,.2f}" if not day_gain.empty else "—")

    gl = pd.to_numeric(portfolio_df.get("Gain/Loss %", pd.Series(dtype=float)), errors='coerce')
    c4.metric("Avg Gain/Loss %", f"{gl.mean():.2f}%" if not gl.empty else "—")

    st.success(f"Portfolio Loaded Successfully — {len(portfolio_df)} Positions Detected")
    st.dataframe(portfolio_df, use_container_width=True)
else:
    st.error("Portfolio file missing or empty — upload Portfolio_Positions_*.csv to /data.")
# ================================================================
# SECTION C — Zacks Analyzer / Trend Comparator / Trailing Stops / Tactical Console
# ================================================================

# ----------------------------------------------------------------
# ZACKS UNIFIED ANALYZER
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("🔎 Zacks Unified Analyzer — Top Candidates")

def unify_zacks(g1, g2, dd):
    frames=[]
    for df,name in [(g1,"Growth 1"),(g2,"Growth 2"),(dd,"Defensive Dividend")]:
        if not df.empty:
            d=df.copy()
            d["Source"]=name
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

unified = unify_zacks(g1_df, g2_df, dd_df)

if not unified.empty:
    if "Zacks Rank" in unified.columns:
        unified["Zacks Rank"] = pd.to_numeric(unified["Zacks Rank"], errors='coerce')

    sort_cols = [c for c in ["Zacks Rank","PEG","PE"] if c in unified.columns]
    if sort_cols:
        unified = unified.sort_values(by=sort_cols, ascending=True)

    top_n = st.slider("Top-N Candidates", 4, 30, 15)
    st.dataframe(unified.head(top_n), use_container_width=True)

    tickers = ", ".join(sorted(set(unified.head(top_n)["Ticker"].astype(str))))
    st.code(tickers, language="text")
else:
    st.warning("No Zacks files found in /data")

# ----------------------------------------------------------------
# ZACKS TREND COMPARATOR (Last 5 Uploads)
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Zacks Trend Comparator — Last 5 Uploads")

def zacks_trend(category: str):
    files = sorted(
        [
            f for f in os.listdir(DATA_PATH)
            if category.lower() in f.lower()
            and f.endswith(".csv")
            and not f.lower().startswith("archive_")
        ],
        key=lambda x: os.path.getmtime(os.path.join(DATA_PATH, x)),
        reverse=True
    )[:5]

    if len(files) < 2:
        return None

    latest = pd.read_csv(os.path.join(DATA_PATH, files[0]))
    prev = pd.read_csv(os.path.join(DATA_PATH, files[1]))

    if "Ticker" not in latest.columns:
        latest = fidelity_auto_map(latest)
    if "Ticker" not in prev.columns:
        prev = fidelity_auto_map(prev)

    return {
        "latest": files[0],
        "previous": files[1],
        "new": list(set(latest["Ticker"]) - set(prev["Ticker"])),
        "dropped": list(set(prev["Ticker"]) - set(latest["Ticker"]))
    }

for cat in ["Growth 1","Growth 2","Defensive"]:
    tr = zacks_trend(cat)
    if tr:
        st.markdown(f"**{cat} — {tr['latest']} vs {tr['previous']}**")
        st.write("🟢 New:", tr["new"][:10])
        st.write("🔻 Dropped:", tr["dropped"][:10])
    else:
        st.info(f"{cat}: Not enough files for trend comparison.")

# ----------------------------------------------------------------
# TRAILING STOP MONITOR
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("🛡️ Trailing Stop Monitor")

if not portfolio_df.empty and {"Ticker","Current Price"}.issubset(portfolio_df.columns):
    tdf = portfolio_df[["Ticker","Current Price","Current Value"]].copy()
    tdf["Trailing %"] = default_stop
    tdf["Stop Price"] = tdf["Current Price"] * (1 - tdf["Trailing %"] / 100)

    st.dataframe(tdf, use_container_width=True)
    csv_buf = io.StringIO()
    tdf.to_csv(csv_buf, index=False)
    st.download_button(
        "⬇️ Download Trailing Stops CSV",
        csv_buf.getvalue(),
        "trailing_stops_v73R45.csv",
        mime="text/csv"
    )
else:
    st.info("Portfolio missing Ticker or Current Price columns — cannot calculate trailing stops.")

# ----------------------------------------------------------------
# TACTICAL CONSOLE — BUY / SELL / HOLD / TRIM
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("🎯 Tactical Console — Buy / Sell / Hold / Trim")

ca, cb, cc, cd = st.columns(4)

with ca:
    buy_ticker = st.text_input("Buy Ticker")
    buy_shares = st.number_input("Buy Shares", min_value=0, step=1)
    st.button("Queue BUY", use_container_width=True)

with cb:
    sell_ticker = st.text_input("Sell Ticker")
    sell_shares = st.number_input("Sell Shares", min_value=0, step=1)
    st.button("Queue SELL", use_container_width=True)

with cc:
    hold_note = st.text_area("Hold Note")
    st.button("Log HOLD", use_container_width=True)

with cd:
    trim_ticker = st.text_input("Trim Ticker")
    trim_percent = st.slider("Trim %", 1, 50, 10)
    st.button("Queue TRIM", use_container_width=True)

st.caption("Interface only — no brokerage connectivity.")
# ================================================================
# SECTION D — Performance Summary / Export Hub / Diagnostics Footer
# ================================================================

# ----------------------------------------------------------------
# PERFORMANCE SUMMARY
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Performance Summary")

if not portfolio_df.empty:
    # Select key columns safely
    cols = [c for c in [
        "Ticker","Description","Shares","Cost Basis","Average Cost",
        "Current Price","Current Value","Gain/Loss $","Gain/Loss %","Day Gain"
    ] if c in portfolio_df.columns]

    if cols:
        pf = portfolio_df[cols].copy()

        # Calculate missing gain columns if needed
        if {"Shares","Cost Basis","Current Price"}.issubset(pf.columns):
            pf["Gain $"] = (pf["Current Price"] - pf["Average Cost"]) * pf["Shares"]
            pf["Gain/Loss %"] = (
                (pf["Current Price"] - pf["Average Cost"]) / pf["Average Cost"]
            ) * 100

        st.dataframe(pf, use_container_width=True)
    else:
        st.info("Required columns missing for performance summary.")
else:
    st.warning("Portfolio not loaded — performance summary unavailable.")

# ----------------------------------------------------------------
# EXPORT HUB — Unified ZIP Bundle
# ----------------------------------------------------------------
st.markdown("---")
st.subheader("📤 Export Unified Data Bundle (.zip)")

def create_data_bundle():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in os.listdir(DATA_PATH):
            if f.endswith(".csv") and not f.lower().startswith("archive_"):
                zf.write(os.path.join(DATA_PATH, f), arcname=f)
    buf.seek(0)
    return buf

if st.button("Generate Data Bundle"):
    z = create_data_bundle()
    st.download_button(
        "⬇️ Download Data_Bundle.zip",
        data=z,
        file_name=f"FoxValley_Data_{datetime.now():%Y%m%d}.zip",
        mime="application/zip"
    )
    st.success("Bundle ready for download.")

# ----------------------------------------------------------------
# SYSTEM FOOTER / DIAGNOSTICS
# ----------------------------------------------------------------
st.markdown("---")
st.caption(f"""
🧭 Fox Valley Command Deck v7.3R-4.5 — Fidelity Autopilot Edition  
Build Time: {datetime.now():%Y-%m-%d %H:%M:%S}  
© CaptPicard + #1 — Fox Valley Intelligence Engine
""")
