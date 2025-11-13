# ================================================================
# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck v7.4R
# Unified Production Build — Nov 2025
# Portfolio • Zacks • Tactical • Allocation • Evolution • Sector • Export
# Author: #1 for CaptPicard
# ================================================================

import os
import io
import csv
import math
import zipfile
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime

# ================================================================
# PAGE CONFIG / GLOBAL STYLE
# ================================================================
st.set_page_config(
    page_title="Fox Valley Intelligence Engine — Command Deck v7.4R",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    div.block-container{padding-top:1.3rem;}
    .section-card{
        background:rgba(255,255,255,.03);
        border:1px solid rgba(255,255,255,.07);
        border-radius:18px;
        padding:1rem 1.5rem;
        margin-bottom:1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================================================================
# CORE HELPERS
# ================================================================
DATA_PATH = "data"

def money(x):
    if pd.isna(x): return "—"
    return f"${x:,.2f}"

def clean_numeric(s):
    if pd.isna(s): return np.nan
    t = str(s).replace("$","").replace(",","").replace("%","").strip()
    if t.startswith("(") and t.endswith(")"):
        try: return -float(t.replace("(","").replace(")",""))
        except: return np.nan
    try: return float(t)
    except: return np.nan

# ================================================================
# AUTO-DETECTION ENGINE (Portfolio + Zacks)
# ================================================================
PORTFOLIO_FILE = None
ZACKS_G1_FILE = None
ZACKS_G2_FILE = None
ZACKS_DD_FILE = None

def auto_detect_files():
    global PORTFOLIO_FILE, ZACKS_G1_FILE, ZACKS_G2_FILE, ZACKS_DD_FILE
    files = os.listdir(DATA_PATH)

    # Portfolio
    pf = [f for f in files if f.lower().startswith("portfolio_positions_") and f.endswith(".csv")]
    if pf: PORTFOLIO_FILE = os.path.join(DATA_PATH, sorted(pf)[-1])

    def find(prefix):
        cands = [f for f in files if f.lower().startswith(prefix.lower())]
        return os.path.join(DATA_PATH, sorted(cands)[-1]) if cands else None

    ZACKS_G1_FILE = find("zacks_custom_screen_2025-") if files else None
    ZACKS_G2_FILE = find("zacks_custom_screen_2025-") if files else None
    ZACKS_DD_FILE = find("zacks_custom_screen_2025-") if files else None

auto_detect_files()

# ================================================================
# CSV LOADER
# ================================================================
@st.cache_data(show_spinner=False)
def load_csv(path):
    if not path or not os.path.exists(path):
        return pd.DataFrame(), [f"Missing file: {path}"]
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        return pd.DataFrame(), [f"Failed to read {path}: {e}"]

    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        if any(k in c.lower() for k in ["value","price","gain","loss","basis","shares","cost"]):
            df[c] = df[c].apply(clean_numeric)

    if "Current Value" not in df.columns and {"Shares","Current Price"}.issubset(df.columns):
        df["Current Value"] = df["Shares"] * df["Current Price"]

    return df, []
# ================================================================
# v7.4R-1 HOTFIX — Ticker Auto-Detection & Normalization Patch
# ================================================================
def normalize_ticker_column(df):
    if df.empty:
        return df
    df = df.copy()

    # 1 — If 'Ticker' already exists
    if "Ticker" in df.columns:
        return df

    # 2 — Fidelity often uses 'Symbol'
    if "Symbol" in df.columns:
        df.rename(columns={"Symbol": "Ticker"}, inplace=True)
        return df

    # 3 — Extract ticker from Description (first token)
    if "Description" in df.columns:
        df["Ticker"] = df["Description"].astype(str).str.split().str[0]
        return df

    # 4 — Fallback placeholder tickers
    df["Ticker"] = [f"UNK{i+1}" for i in range(len(df))]
    return df

# ================================================================
# LOAD ALL DATA
# ================================================================
portfolio_df, pmsg = load_csv(PORTFOLIO_FILE) if PORTFOLIO_FILE else (pd.DataFrame(), ["Portfolio file not found."])
portfolio_df = normalize_ticker_column(portfolio_df)
# v7.4R-1 HOTFIX — Ticker Auto-Detection & Normalization Patch
# ================================================================
def normalize_ticker_column(df):
    if df.empty:
        return df
    df = df.copy()

    # 1 — If 'Ticker' already exists
    if "Ticker" in df.columns:
        return df

    # 2 — Fidelity often uses 'Symbol'
    if "Symbol" in df.columns:
        df.rename(columns={"Symbol": "Ticker"}, inplace=True)
        return df

    # 3 — Extract ticker from Description (first token)
    if "Description" in df.columns:
        df["Ticker"] = df["Description"].astype(str).str.split().str[0]
        return df

    # 4 — Fallback placeholder tickers
    df["Ticker"] = [f"UNK{i+1}" for i in range(len(df))]
    return df

g1_df, _ = load_csv(ZACKS_G1_FILE) if ZACKS_G1_FILE else (pd.DataFrame(), [])
g2_df, _ = load_csv(ZACKS_G2_FILE) if ZACKS_G2_FILE else (pd.DataFrame(), [])
dd_df, _ = load_csv(ZACKS_DD_FILE) if ZACKS_DD_FILE else (pd.DataFrame(), [])

all_z = pd.concat(
    [
        g1_df.assign(Source="Growth 1") if not g1_df.empty else None,
        g2_df.assign(Source="Growth 2") if not g2_df.empty else None,
        dd_df.assign(Source="Defensive Dividends") if not dd_df.empty else None,
    ],
    ignore_index=True
).dropna(how="all", axis=1) if any([not g1_df.empty, not g2_df.empty, not dd_df.empty]) else pd.DataFrame()

# ================================================================
# SIDEBAR — Cash / Trailing
# ================================================================
st.sidebar.title("🧭 Command Deck — v7.4R")
st.sidebar.caption("Enterprise Intelligence Engine")

manual_cash = st.sidebar.number_input(
    "💰 Cash Available to Trade ($)",
    min_value=0.0,
    step=100.0,
    value=0.0,
    format="%.2f",
)

def_trail = st.sidebar.slider("Default Trailing Stop %", 1, 50, 12)

# ================================================================
# MAIN TITLE
# ================================================================
st.title("🧭 Fox Valley Intelligence Engine — Enterprise Command Deck")
st.caption("v7.4R | Portfolio + Zacks + Tactical + Allocation + Evolution + Sector Intelligence")
st.markdown("---")

# ================================================================
# PORTFOLIO OVERVIEW
# ================================================================
st.subheader("📊 Portfolio Overview")

val_col = next((c for c in ["Current Value", "Market Value", "Value"] if c in portfolio_df.columns), None)
total_value = float(portfolio_df[val_col].sum()) if val_col else 0.0

day_gain = pd.to_numeric(portfolio_df.get("Day Gain", pd.Series(dtype=float)), errors='coerce').sum()
gl = pd.to_numeric(portfolio_df.get("Gain/Loss %", pd.Series(dtype=float)), errors='coerce')
avg_gain = gl.mean() if not gl.empty else np.nan

c1, c2, c3, c4 = st.columns(4)
c1.metric("Estimated Total Value", money(total_value + manual_cash))
c2.metric("Cash Available to Trade", money(manual_cash))
c3.metric("Day Gain (sum)", money(day_gain))
c4.metric("Avg Gain/Loss %", f"{avg_gain:.2f}%" if not pd.isna(avg_gain) else "—")

if manual_cash == 0:
    st.warning("Manual cash override is 0 — update sidebar for accuracy.")
else:
    st.success(f"Manual cash override active: {money(manual_cash)}")

st.dataframe(portfolio_df, use_container_width=True)
st.markdown("---")

# ================================================================
# ZACKS UNIFIED ANALYZER
# ================================================================
st.subheader("🔎 Zacks Unified Analyzer — Top Candidates")

if not all_z.empty:
    if "Zacks Rank" in all_z.columns:
        all_z["Zacks Rank"] = pd.to_numeric(all_z["Zacks Rank"], errors='coerce')

    sort_cols = [c for c in ["Zacks Rank","PEG","PE"] if c in all_z.columns]
    if sort_cols:
        all_z = all_z.sort_values(by=sort_cols, ascending=True)

    top_n = st.slider("Top-N Candidates", 4, 30, 8)
    st.dataframe(all_z.head(top_n), use_container_width=True)

    tickers = ", ".join(sorted(all_z.head(top_n)["Ticker"].astype(str)))
    st.code(tickers)
else:
    st.warning("No Zacks data available.")

st.markdown("---")

# ================================================================
# TACTICAL ENGINE
# ================================================================
if "tactical_log" not in st.session_state:
    st.session_state.tactical_log = []

def log_tactical_action(action, ticker, qty=None, pct=None, notes=""):
    st.session_state.tactical_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "ticker": ticker,
        "quantity": qty,
        "percent": pct,
        "notes": notes,
    })

def display_tactical_log():
    st.subheader("📘 Tactical Log")
    if not st.session_state.tactical_log:
        st.info("No tactical actions recorded.")
        return
    for e in st.session_state.tactical_log:
        st.markdown(f"**[{e['timestamp']}]** — `{e['action']}` **{e['ticker']}**")
        if e['quantity']: st.write(f"Shares: {e['quantity']}")
        if e['percent']: st.write(f"Trim %: {e['percent']}%")
        if e['notes']: st.write(f"Notes: {e['notes']}")
        st.markdown("---")

st.header("🎯 Tactical Operations Center — v7.4R")

col1, col2, col3 = st.columns([2,2,3])
with col1:
    action = st.selectbox("Action", ["BUY","SELL","HOLD","TRIM"])
    ticker = st.text_input("Ticker")
with col2:
    qty = st.number_input("Shares", min_value=0)
    trim_pct = st.slider("Trim %", 1, 50, 10)
with col3:
    notes = st.text_area("Execution Notes")
    if st.button("Log Action", use_container_width=True):
        log_tactical_action(action, ticker, qty if qty>0 else None, trim_pct if action=="TRIM" else None, notes)
        st.success(f"Logged {action} for {ticker}")

display_tactical_log()
st.markdown("---")

# ================================================================
# ALLOCATION ENGINE
# ================================================================
ALLOCATION_MAP = {
    "NVDA": "Growth", "AMZN": "Growth", "COMM": "Growth", "RDDT": "Growth", "NBIX": "Growth",
    "NEM": "Defensive", "ALL": "Defensive", "HSBC": "Defensive", "PRK": "Defensive", "NVT": "Defensive",
    "AU": "Core", "IBKR": "Core", "CNQ": "Core", "TPC": "Core", "NTB": "Core",
    "LCII": "Core", "CUBI": "Core", "CALX": "Core", "KAR": "Core",
}

def apply_allocation(df):
    if df.empty: return df
    df = df.copy()
    df["Category"] = df["Ticker"].apply(lambda x: ALLOCATION_MAP.get(str(x).upper(),"Unassigned"))
    return df

def calculate_allocation(df):
    if df.empty or "Current Value" not in df.columns:
        return df, {}
    total = df["Current Value"].sum()
    if total <= 0: return df, {}
    df["Allocation %"] = df["Current Value"] / total * 100
    cat = (df.groupby("Category")["Current Value"].sum() / total * 100).to_dict()
    return df, cat

st.header("📊 Allocation System — v7.4R")

alloc_df = apply_allocation(portfolio_df)
alloc_df, alloc_weights = calculate_allocation(alloc_df)

st.dataframe(
    alloc_df[[c for c in ["Ticker","Description","Current Value","Category","Allocation %"] if c in alloc_df.columns]],
    use_container_width=True
)

st.subheader("📡 Category Exposure (%)")
if alloc_weights:
    for cat, pct in alloc_weights.items():
        st.write(f"**{cat}: {pct:.2f}%**")
else:
    st.info("No category data available.")

st.markdown("---")

# ================================================================
# PERFORMANCE HEATMAP
# ================================================================
st.header("🔥 Performance Heatmap — v7.4R")

def make_heatmap(df):
    if df.empty or "Gain/Loss %" not in df.columns:
        st.info("Insufficient data for heatmap.")
        return
    df = df.copy()
    df["Gain/Loss %"] = pd.to_numeric(df["Gain/Loss %"], errors='coerce')
    df = df[df["Gain/Loss %"].notna()]
    if df.empty:
        st.warning("No numerical gain/loss data available.")
        return
    chart = alt.Chart(df).mark_rect().encode(
        x=alt.X("Ticker:N"),
        y=alt.Y("Category:N"),
        color=alt.Color("Gain/Loss %:Q", scale=alt.Scale(scheme="redyellowgreen")),
        tooltip=["Ticker","Category","Gain/Loss %","Current Value"]
    )
    st.altair_chart(chart, use_container_width=True)

make_heatmap(alloc_df)
st.markdown("---")

# ================================================================
# ZACKS EVOLUTION ENGINE
# ================================================================
st.header("📈 Zacks Evolution Engine — v7.4R")

def load_all_zfiles():
    return sorted([f for f in os.listdir(DATA_PATH) if f.lower().startswith("zacks_custom_screen_")])

def compare_two(latest, prev):
    try:
        ldf = pd.read_csv(os.path.join(DATA_PATH, latest))
        pdf = pd.read_csv(os.path.join(DATA_PATH, prev))
    except:
        return [], []
    lset = set(ldf["Ticker"].astype(str))
    pset = set(pdf["Ticker"].astype(str))
    return sorted(lset - pset), sorted(pset - lset)

zfiles = load_all_zfiles()

if len(zfiles) < 2:
    st.info("Not enough Zacks files for comparison.")
else:
    latest = zfiles[-1]
    prev = zfiles[-2]
    st.write(f"Comparing `{latest}` vs `{prev}`")
    new, dropped = compare_two(latest, prev)
    st.subheader("🟢 New")
    st.write(new if new else "None")
    st.subheader("🔻 Dropped")
    st.write(dropped if dropped else "None")

st.markdown("---")

# ================================================================
# SECTOR EXPOSURE MAP v1.0
# ================================================================
st.header("🏛 Sector Exposure Map — v7.4R")

SECTOR_MAP = {
    "NVDA": "Technology", "AMZN": "Consumer Discretionary", "COMM": "Communication",
    "RDDT": "Communication", "NBIX": "Healthcare", "NEM": "Materials", "ALL": "Financials",
    "HSBC": "Financials", "PRK": "Financials", "NVT": "Industrials", "AU": "Materials",
    "IBKR": "Financials", "CNQ": "Energy", "TPC": "Industrials", "NTB": "Financials",
    "LCII": "Consumer Discretionary", "CUBI": "Financials", "CALX": "Technology",
    "KAR": "Consumer Discretionary",
}

def apply_sector(df):
    if df.empty: return df
    df = df.copy()
    df["Sector"] = df["Ticker"].apply(lambda x: SECTOR_MAP.get(str(x).upper(),"Unassigned"))
    return df

sec_df = apply_sector(portfolio_df)

if "Current Value" in sec_df.columns and sec_df["Current Value"].sum() > 0:
    st.subheader("📡 Sector Allocation (%)")
    s = (sec_df.groupby("Sector")["Current Value"].sum() / sec_df["Current Value"].sum() * 100).sort_values(ascending=False)
    for sec, p in s.items():
        st.write(f"**{sec}: {p:.2f}%**")

chart = alt.Chart(sec_df).mark_bar().encode(
    x=alt.X("Sector:N"),
    y=alt.Y("Current Value:Q"),
    tooltip=["Sector","Current Value","Ticker"]
)
st.altair_chart(chart, use_container_width=True)

heat = alt.Chart(sec_df).mark_rect().encode(
    x=alt.X("Ticker:N"),
    y=alt.Y("Sector:N"),
    color=alt.Color("Current Value:Q", scale=alt.Scale(scheme="blues")),
    tooltip=["Ticker","Sector","Current Value"]
)
st.altair_chart(heat, use_container_width=True)

st.markdown("---")

# ================================================================
# EXPORT ENGINE
# ================================================================
st.header("📤 Export Unified Data Bundle (.zip)")

def export_bundle():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if PORTFOLIO_FILE: z.write(PORTFOLIO_FILE, os.path.basename(PORTFOLIO_FILE))
        for f in [ZACKS_G1_FILE, ZACKS_G2_FILE, ZACKS_DD_FILE]:
            if f: z.write(f, os.path.basename(f))

        tbuf = io.StringIO()
        w = csv.writer(tbuf)
        w.writerow(["timestamp","action","ticker","quantity","percent","notes"])
        for e in st.session_state.tactical_log:
            w.writerow([e["timestamp"],e["action"],e["ticker"],e["quantity"],e["percent"],e["notes"]])
        z.writestr("tactical_log.csv", tbuf.getvalue())

    return buf.getvalue()

st.download_button("Download Bundle", export_bundle(), "fvie_export_v74R.zip")

# ================================================================
# FOOTER
# ================================================================
st.markdown("---")
st.caption(f"🧭 Command Deck v7.4R — Build Time: {datetime.now():%Y-%m-%d %H:%M:%S} | Enterprise Integration Complete")
