# ================================================================
# Fox Valley Intelligence Engine — Command Deck v7.4R (StabilityPatch)
# PART A — Systems Architecture, Loaders, Portfolio Overview, Zacks Engine
# Author: #1 for CaptPicard — Nov 2025
# ================================================================

import os
import io
import math
import csv
import zipfile
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# ================================================================
# PAGE CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="Fox Valley Intelligence Engine — Command Deck v7.4R",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    div.block-container {padding-top: 1.5rem;}
    .section-card {
        background: rgba(255,255,255,.02);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 16px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    .data-ok {color:#22c55e;font-weight:600}
    .data-warn {color:#f59e0b;font-weight:600}
    .data-err {color:#ef4444;font-weight:700}
    </style>
    """,
    unsafe_allow_html=True,
)

# ================================================================
# CONSTANTS & DATA PATHS
# ================================================================
DATA_PATH = "data"

PORTFOLIO_FILE = None
ZACKS_G1_FILE = None
ZACKS_G2_FILE = None
ZACKS_DD_FILE = None

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def money(x):
    if pd.isna(x):
        return "—"
    return f"${x:,.2f}"

def clean_numeric(s):
    """Cleans Fidelity numeric strings including ($1,234.56)."""
    if pd.isna(s): 
        return np.nan
    t = str(s).replace("$", "").replace(",", "").replace("%", "").strip()

    neg = (t.startswith("(") and t.endswith(")"))
    t = t.replace("(", "").replace(")", "")
    try:
        v = float(t)
        return -v if neg else v
    except:
        return np.nan

# ================================================================
# AUTO-DETECT LATEST FILES
# ================================================================
def auto_detect_files():
    """Automatically finds the newest portfolio and Zacks files."""
    global PORTFOLIO_FILE, ZACKS_G1_FILE, ZACKS_G2_FILE, ZACKS_DD_FILE

    if not os.path.exists(DATA_PATH):
        return

    files = os.listdir(DATA_PATH)

    # Detect Portfolio
    p = [f for f in files if f.lower().startswith("portfolio_positions_")]
    if p:
        PORTFOLIO_FILE = os.path.join(DATA_PATH, sorted(p)[-1])

    # Detect Zacks screens
    def detect(prefix):
        c = [f for f in files if f.lower().startswith(prefix)]
        return os.path.join(DATA_PATH, sorted(c)[-1]) if c else None

    ZACKS_G1_FILE = detect("zacks_custom_screen_2025-11-13 growth 1")
    ZACKS_G2_FILE = detect("zacks_custom_screen_2025-11-13 growth 2")
    ZACKS_DD_FILE = detect("zacks_custom_screen_2025-11-13 defensive dividends")

auto_detect_files()

# ================================================================
# CSV LOADER — STABILITY VERSION
# ================================================================
@st.cache_data(show_spinner=False)
def load_csv(path):
    """Loads a CSV and resolves all numeric Fidelity columns."""
    if not path or not os.path.exists(path):
        return pd.DataFrame(), [f"Missing file: {path}"]

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        return pd.DataFrame(), [f"Failed to read {path}: {e}"]

    df.columns = [str(c).strip() for c in df.columns]

    # clean numeric columns
    for c in df.columns:
        if any(k in c.lower() for k in ["value", "price", "gain", "loss", "basis", "shares", "cost"]):
            df[c] = df[c].apply(clean_numeric)

    # Derived columns
    if "Current Value" not in df.columns and {"Shares", "Current Price"}.issubset(df.columns):
        df["Current Value"] = df["Shares"] * df["Current Price"]

    return df, []

# ================================================================
# TICKER NORMALIZATION → KEY STABILITY FEATURE
# ================================================================
def normalize_ticker_column(df):
    """Ensures portfolio always has a correct 'Ticker' column."""
    if df.empty:
        return df

    df = df.copy()

    # CASE 1: Already correct
    if "Ticker" in df.columns:
        return df

    # CASE 2: Fidelity uses "Symbol"
    if "Symbol" in df.columns:
        df.rename(columns={"Symbol": "Ticker"}, inplace=True)
        return df

    # CASE 3: Extract from Description
    if "Description" in df.columns:
        df["Ticker"] = df["Description"].astype(str).str.split().str[0]
        return df

    # CASE 4: Fallback — prevent crash
    df["Ticker"] = [f"UNK{i+1}" for i in range(len(df))]
    return df

# ================================================================
# LOAD ALL DATA (with protection)
# ================================================================
portfolio_df, pmsg = load_csv(PORTFOLIO_FILE) if PORTFOLIO_FILE else (pd.DataFrame(), ["Portfolio file missing"])
portfolio_df = normalize_ticker_column(portfolio_df)

g1_df, _ = load_csv(ZACKS_G1_FILE) if ZACKS_G1_FILE else (pd.DataFrame(), [])
g2_df, _ = load_csv(ZACKS_G2_FILE) if ZACKS_G2_FILE else (pd.DataFrame(), [])
dd_df, _ = load_csv(ZACKS_DD_FILE) if ZACKS_DD_FILE else (pd.DataFrame(), [])

# Merge Zacks
all_z = pd.concat(
    [
        g1_df.assign(Source="Growth 1") if not g1_df.empty else None,
        g2_df.assign(Source="Growth 2") if not g2_df.empty else None,
        dd_df.assign(Source="Defensive Dividends") if not dd_df.empty else None,
    ],
    ignore_index=True
).dropna(how="all", axis=1) if any([not g1_df.empty, not g2_df.empty, not dd_df.empty]) else pd.DataFrame()

# ================================================================
# SIDEBAR — Manual Cash Entry (Daily)
# ================================================================
st.sidebar.title("🧭 Command Deck — v7.4R")
st.sidebar.caption("Enterprise Intelligence Engine")

manual_cash = st.sidebar.number_input(
    "💰 Cash Available to Trade ($)",
    min_value=0.0,
    step=100.0,
    value=0.0,
    format="%.2f"
)

def_trail = st.sidebar.slider(
    "Default Trailing Stop %",
    1, 50, 12
)

# ================================================================
# PORTFOLIO OVERVIEW DISPLAY
# ================================================================
st.title("🧭 Fox Valley Intelligence Engine — Enterprise Command Deck (v7.4R)")
st.caption("Portfolio + Zacks + Tactical + Allocation + Evolution + Sector Intelligence Online")
st.markdown("---")

st.subheader("📊 Portfolio Overview")

val_col = next((c for c in ["Current Value", "Market Value", "Value"] if c in portfolio_df.columns), None)
total_value = float(pd.to_numeric(portfolio_df[val_col], errors='coerce').sum()) if val_col else 0.0
cash_value = manual_cash

day_gain = pd.to_numeric(
    portfolio_df.get("Today's Gain/Loss Dollar", portfolio_df.get("Day Gain", pd.Series(dtype=float))),
    errors='coerce'
).sum()

gl = pd.to_numeric(
    portfolio_df.get("Total Gain/Loss Percent", portfolio_df.get("Gain/Loss %", pd.Series(dtype=float))),
    errors='coerce'
)

avg_gain = gl.mean() if not gl.empty else np.nan

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Estimated Total Value", money(total_value + cash_value))
with c2:
    st.metric("Cash Available to Trade", money(cash_value))
with c3:
    st.metric("Day Gain (sum)", money(day_gain))
with c4:
    st.metric("Avg Gain/Loss %", f"{avg_gain:.2f}%" if not pd.isna(avg_gain) else "—")

if manual_cash > 0:
    st.success(f"Manual cash override active: {money(cash_value)}")
else:
    st.warning("Manual cash is 0 — update sidebar for accuracy.")

if not portfolio_df.empty:
    st.dataframe(portfolio_df, use_container_width=True)
else:
    st.error("Portfolio file missing or empty.")

# ================================================================
# ZACKS UNIFIED ANALYZER — TOP CANDIDATES
# ================================================================
st.markdown("---")
st.subheader("🔎 Zacks Unified Analyzer — Top Candidates")

if not all_z.empty:

    if "Zacks Rank" in all_z.columns:
        all_z["Zacks Rank"] = pd.to_numeric(all_z["Zacks Rank"], errors='coerce')

    sort_cols = [c for c in ["Zacks Rank", "PEG", "PE"] if c in all_z.columns]
    if sort_cols:
        all_z = all_z.sort_values(by=sort_cols, ascending=True)

    top_n = st.slider("Top-N Candidates", 4, 30, 8)

    st.dataframe(all_z.head(top_n), use_container_width=True)

    tickers = ", ".join(sorted(set(all_z.head(top_n)["Ticker"].astype(str))))
    st.code(tickers, language="text")

else:
    st.warning("No Zacks data available.")
# ================================================================
# PART B — Tactical Engine, Allocation System, Sector Map, Evolution,
#           Export Engine, and Final Diagnostics
# ================================================================

# ================================================================
# TACTICAL ENGINE (Logging + Insights)
# ================================================================
if "tactical_log" not in st.session_state:
    st.session_state.tactical_log = []

def log_tactical_action(action_type, ticker, quantity=None, percent=None, notes=""):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action_type,
        "ticker": ticker,
        "quantity": quantity,
        "percent": percent,
        "notes": notes,
    }
    st.session_state.tactical_log.append(entry)

def display_tactical_log():
    st.subheader("📘 Tactical Log — Session Actions")
    if not st.session_state.tactical_log:
        st.info("No tactical actions recorded.")
        return

    for e in st.session_state.tactical_log:
        st.markdown(f"**[{e['timestamp']}]** — `{e['action']}` **{e['ticker']}**")
        if e.get("quantity"): 
            st.write(f"Shares: {e['quantity']}")
        if e.get("percent"): 
            st.write(f"Trim %: {e['percent']}%")
        if e.get("notes"): 
            st.write(f"Notes: {e['notes']}")
        st.markdown("---")

# Tactical Intelligence (Mission B4)
def generate_tactical_insights(action_type, ticker, quantity=None, percent=None):
    intel = []

    # Detect if position exists
    if not portfolio_df.empty:
        exists = portfolio_df[portfolio_df["Ticker"].astype(str).str.upper() == str(ticker).upper()]
        intel.append("Existing position detected." if not exists.empty else "New position.")

    # Zacks intelligence
    if not all_z.empty:
        z = all_z[all_z["Ticker"].astype(str).str.upper() == str(ticker).upper()]
        if not z.empty:
            zr = z.get("Zacks Rank", pd.Series([None])).iloc[0]
            intel.append(f"Zacks Rank {zr} identified.")
        else:
            intel.append("Ticker not present in Zacks screens.")

    # Action classification
    if action_type == "BUY": intel.append("BUY action — ensure allocation alignment.")
    if action_type == "SELL": intel.append("SELL action — evaluate risk/exit logic.")
    if action_type == "HOLD": intel.append("HOLD logged — no changes.")
    if action_type == "TRIM": intel.append(f"TRIM initiated — {percent}% profit capture or risk adjustment.")

    return intel

def display_insights(intel):
    st.markdown("### 🧠 Tactical Intelligence Insights")
    for idea in intel:
        st.markdown(f"- {idea}")
    st.markdown("---")

# Tactical Console UI
st.markdown("---")
st.header("🎯 Tactical Operations Center — v7.4R")

def tactical_console():
    c1, c2, c3 = st.columns([2,2,3])

    with c1:
        action_type = st.selectbox("Action", ["BUY","SELL","HOLD","TRIM"])
        ticker = st.text_input("Ticker")

    with c2:
        qty = st.number_input("Shares (if applicable)", min_value=0)
        tpercent = st.slider("Trim %", 1, 50, 10)

    with c3:
        notes = st.text_area("Execution Notes")
        st.write("")
        if st.button("Log Action", use_container_width=True):
            intel = generate_tactical_insights(action_type, ticker, qty, (tpercent if action_type=="TRIM" else None))
            display_insights(intel)
            log_tactical_action(
                action_type,
                ticker,
                qty if qty>0 else None,
                (tpercent if action_type=="TRIM" else None),
                notes,
            )
            st.success(f"Logged {action_type} for {ticker}")

    st.markdown("---")
    display_tactical_log()

tactical_console()


# ================================================================
# ALLOCATION SYSTEM
# ================================================================
ALLOCATION_MAP = {
    "NVDA": "Growth", "AMZN": "Growth", "COMM": "Growth", "RDDT": "Growth", "NBIX": "Growth",
    "NEM": "Defensive", "ALL": "Defensive", "HSBC": "Defensive", "PRK": "Defensive", "NVT": "Defensive", "ARMN": "Defensive", "RGLD": "Defensive",
    "AU": "Core", "IBKR": "Core", "CNQ": "Core", "TPC": "Core", "NTB": "Core",
    "LCII": "Core", "CUBI": "Core", "CALX": "Core", "KAR": "Core", "DINO": "Core", "CBOE": "Core", "GRND": "Growth",
}

def apply_allocation(df):
    if df.empty:
        return df
    df = df.copy()
    df["Category"] = df["Ticker"].apply(lambda t: ALLOCATION_MAP.get(str(t).upper(), "Unassigned"))
    return df

def compute_allocation_weights(df):
    if df.empty or "Current Value" not in df.columns:
        return {}
    total = df["Current Value"].sum()
    if total <= 0: 
        return {}
    return (df.groupby("Category")["Current Value"].sum() / total * 100).round(2).to_dict()

# Allocation UI
st.header("📊 Allocation System — v7.4R")

alloc_df = apply_allocation(portfolio_df)
cat_weights = compute_allocation_weights(alloc_df)

st.dataframe(
    alloc_df[
        [c for c in ["Ticker","Description","Current Value","Category"] if c in alloc_df.columns]
    ],
    use_container_width=True
)

st.subheader("📡 Category Exposure (%)")
if cat_weights:
    for k,v in cat_weights.items():
        st.write(f"**{k}: {v:.2f}%**")
else:
    st.info("Not enough data for allocation metrics.")

st.markdown("---")


# ================================================================
# PERFORMANCE HEATMAP — v7.4R
# ================================================================
st.header("🔥 Performance Heatmap — v7.4R")

def make_performance_heatmap(df):
    if df.empty or "Ticker" not in df.columns or "Gain/Loss %" not in df.columns:
        st.info("Insufficient data for heatmap.")
        return

    df = df.copy()
    df["Gain/Loss %"] = pd.to_numeric(df["Gain/Loss %"], errors="coerce")
    df = df[df["Gain/Loss %"].notna()]

    if df.empty:
        st.warning("No numerical gain/loss data available.")
        return

    chart = (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("Ticker:N", sort=None),
            y=alt.Y("Category:N", sort=None),
            color=alt.Color("Gain/Loss %:Q", scale=alt.Scale(scheme="redyellowgreen")),
            tooltip=["Ticker","Category","Gain/Loss %","Current Value"],
        )
        .properties(height=200)
    )

    st.altair_chart(chart, use_container_width=True)

make_performance_heatmap(alloc_df)

st.markdown("---")


# ================================================================
# ZACKS EVOLUTION ENGINE (TREND COMPARATOR)
# ================================================================
st.header("📈 Zacks Evolution Engine — v7.4R")

def all_zacks_files():
    return sorted([f for f in os.listdir(DATA_PATH) if f.lower().startswith("zacks_custom_screen_")])

def compare_versions(latest, previous):
    try:
        ldf = pd.read_csv(os.path.join(DATA_PATH, latest))
        pdf = pd.read_csv(os.path.join(DATA_PATH, previous))
    except:
        return [], []

    lset = set(ldf["Ticker"].astype(str))
    pset = set(pdf["Ticker"].astype(str))

    return sorted(lset - pset), sorted(pset - lset)

versions = all_zacks_files()

if len(versions) < 2:
    st.info("Not enough Zacks files for trend analysis.")
else:
    latest = versions[-1]
    prev = versions[-2]

    st.write(f"Comparing `{latest}` vs `{prev}`")

    new, dropped = compare_versions(latest, prev)

    st.subheader("🟢 New")
    st.write(new if new else "None")

    st.subheader("🔻 Dropped")
    st.write(dropped if dropped else "None")

st.markdown("---")


# ================================================================
# SECTOR EXPOSURE MAP — v7.4R
# ================================================================
st.header("🏛 Sector Exposure Map — v7.4R")

SECTOR_MAP = {
    "NVDA":"Technology", "AMZN":"Consumer Discretionary", "COMM":"Communication", "RDDT":"Communication", "NBIX":"Healthcare",
    "NEM":"Materials", "ALL":"Financials", "HSBC":"Financials", "PRK":"Financials", "NVT":"Industrials", 
    "AU":"Materials", "IBKR":"Financials", "CNQ":"Energy", "TPC":"Industrials", "NTB":"Financials",
    "LCII":"Consumer Discretionary", "CUBI":"Financials", "CALX":"Technology", "KAR":"Consumer Discretionary",
    "DINO":"Energy", "CBOE":"Financials", "ARMN":"Materials", "RGLD":"Materials", "GRND":"Communication",
}

def apply_sector(df):
    if df.empty:
        return df
    df = df.copy()
    df["Sector"] = df["Ticker"].apply(lambda t: SECTOR_MAP.get(str(t).upper(), "Unassigned"))
    return df

sector_df = apply_sector(portfolio_df)

if "Current Value" in sector_df.columns:
    st.subheader("📡 Sector Allocation (%)")
    total = sector_df["Current Value"].sum()
    if total > 0:
        weights = (
            sector_df.groupby("Sector")["Current Value"].sum() / total * 100
        ).round(2)
        for s,p in weights.items():
            st.write(f"**{s}: {p:.2f}%**")

# Bar Chart
chart = (
    alt.Chart(sector_df)
    .mark_bar()
    .encode(
        x="Sector:N",
        y="Current Value:Q",
        tooltip=["Sector","Current Value","Ticker"],
    )
    .properties(height=300)
)
st.altair_chart(chart, use_container_width=True)

# Heatmap
heat = (
    alt.Chart(sector_df)
    .mark_rect()
    .encode(
        x="Ticker:N",
        y="Sector:N",
        color=alt.Color("Current Value:Q", scale=alt.Scale(scheme="blues")),
        tooltip=["Ticker","Sector","Current Value"],
    )
    .properties(height=200)
)
st.altair_chart(heat, use_container_width=True)

st.markdown("---")


# ================================================================
# EXPORT BUNDLE ENGINE
# ================================================================
st.header("📤 Export Unified Data Bundle (.zip)")

def export_bundle():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:

        # Portfolio + Zacks files
        if PORTFOLIO_FILE:
            z.write(PORTFOLIO_FILE, arcname=os.path.basename(PORTFOLIO_FILE))

        for f in [ZACKS_G1_FILE, ZACKS_G2_FILE, ZACKS_DD_FILE]:
            if f:
                z.write(f, arcname=os.path.basename(f))

        # Tactical log
        tbuf = io.StringIO()
        writer = csv.writer(tbuf)
        writer.writerow(["timestamp","action","ticker","quantity","percent","notes"])
        for e in st.session_state.tactical_log:
            writer.writerow([e["timestamp"], e["action"], e["ticker"], e["quantity"], e["percent"], e["notes"]])
        z.writestr("tactical_log.csv", tbuf.getvalue())

    st.download_button("Download Bundle", buf.getvalue(), "foxvalley_export_v74R.zip")

export_bundle()

# ================================================================
# FOOTER / DIAGNOSTICS
# ================================================================
st.markdown("---")
st.caption(
    f"🧭 Command Deck v7.4R — StabilityPatch Complete | Build: {datetime.now():%Y-%m-%d %H:%M:%S}"
)
