# ============================================================
# 🧭 Fox Valley Intelligence Engine – Enterprise Command Deck
# Version: v7.3R-4.4 (Quantum Surge – Nov 13 2025)
# Unified Build: Auto-Detects Latest Portfolio + Zacks Files
# Author: #1 for CaptPicard
# ============================================================

import os, io, math, zipfile, time
from datetime import datetime
from typing import List, Tuple
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="🧭 Fox Valley Command Deck v7.3R-4.4 — Quantum Surge",
    page_icon="🧭",
    layout="wide"
)

st.markdown(
    """<style>
    div.block-container {padding-top: 1.5rem;}
    .section-card {background: rgba(255,255,255,.02);
                   border: 1px solid rgba(255,255,255,.08);
                   border-radius: 16px; padding: 1rem 1.5rem;
                   margin-bottom: 1rem;}
    </style>""",
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# CONSTANTS / DATA PATHS
# ------------------------------------------------------------
DATA_PATH = "data"

# Auto-detect the latest file matching keywords
def get_latest_file(keyword: str):
    files = [f for f in os.listdir(DATA_PATH) if keyword.lower() in f.lower() and f.endswith(".csv")]
    if not files:
        return None
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(DATA_PATH, f)))
    return os.path.join(DATA_PATH, latest), latest

# ------------------------------------------------------------
# DATA LOADING ENGINE (UNIFIED)
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv_auto(keyword: str):
    path_info = get_latest_file(keyword)
    if not path_info:
        return pd.DataFrame(), [f"No file found for keyword '{keyword}'"]
    path, filename = path_info
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        return pd.DataFrame(), [f"Failed to read {filename}: {e}"]

    df.columns = [str(c).strip() for c in df.columns]

    # Normalize numeric fields
    def scrub(v):
        if pd.isna(v): return np.nan
        s=str(v).replace("$","").replace(",","").replace("%","").strip()
        neg=s.startswith("(") and s.endswith(")")
        s=s.replace("(","").replace(")","")
        try: val=float(s)
        except: return np.nan
        return -val if neg else val

    for c in ["Shares","Cost Basis","Average Cost","Current Price","Current Value","Gain/Loss %","Day Gain"]:
        if c in df.columns:
            df[c]=df[c].apply(scrub)

    if "Cost Basis" not in df.columns and "Average Cost" in df.columns:
        df["Cost Basis"]=df["Average Cost"]

    if "Current Value" not in df.columns and {"Shares","Current Price"}.issubset(df.columns):
        df["Current Value"]=df["Shares"]*df["Current Price"]

    return df, [f"Loaded latest: {filename}"]

# ------------------------------------------------------------
# LOAD ALL LIVE DATA
# ------------------------------------------------------------
portfolio_df, pf_msg = load_csv_auto("Portfolio_Positions")
g1_df, g1_msg = load_csv_auto("Growth 1")
g2_df, g2_msg = load_csv_auto("Growth 2")
dd_df, dd_msg = load_csv_auto("Defensive")

# ------------------------------------------------------------
# SIDEBAR CONFIG
# ------------------------------------------------------------
st.sidebar.title("🧭 Command Deck v7.3R-4.4 — Quantum Surge")
st.sidebar.caption(f"Build Initialized | {datetime.now():%b %d %Y}")

manual_cash = st.sidebar.number_input(
    "💰 Manual Cash Override ($)",
    min_value=0.0, step=100.0, value=0.0, format="%.2f"
)

default_stop = st.sidebar.slider("Default Trailing Stop %", 1, 50, 10)

st.sidebar.markdown("---")
st.sidebar.write("### Diagnostics")
st.sidebar.write("\n".join(pf_msg + g1_msg + g2_msg + dd_msg))

# ------------------------------------------------------------
# MAIN HEADER
# ------------------------------------------------------------
st.title("🧭 Fox Valley Intelligence Engine — Enterprise Command Deck")
st.caption("v7.3R-4.4 Quantum Surge | Auto-Loading Portfolio + Zacks + Trend Engine Online")

st.markdown("---")

# ------------------------------------------------------------
# PORTFOLIO OVERVIEW
# ------------------------------------------------------------
st.subheader("📊 Portfolio Overview")

if not portfolio_df.empty:
    val_col = next((c for c in ["Current Value","Market Value","Value"] if c in portfolio_df.columns), None)
    total_val = float(portfolio_df[val_col].sum()) if val_col else 0
    cash_val = manual_cash

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Estimated Total Value", f"${total_val:,.2f}")
    c2.metric("Cash Available to Trade", f"${cash_val:,.2f}")

    day_gain = portfolio_df.get("Day Gain", pd.Series(dtype=float))
    c3.metric("Day Gain (sum)", f"${day_gain.sum():,.2f}" if not day_gain.empty else "—")

    gl = portfolio_df.get("Gain/Loss %", pd.Series(dtype=float))
    c4.metric("Avg Gain/Loss %", f"{gl.mean():.2f}%" if not gl.empty else "—")

    st.success(f"Portfolio Loaded Successfully — {len(portfolio_df)} Positions Detected")
    st.dataframe(portfolio_df, use_container_width=True)
else:
    st.error("Portfolio not found or empty — upload Portfolio_Positions_*.csv to /data")

# ------------------------------------------------------------
# ZACKS UNIFIED ANALYZER
# ------------------------------------------------------------
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
        unified["Zacks Rank"]=pd.to_numeric(unified["Zacks Rank"], errors='coerce')

    sort_cols=[c for c in ["Zacks Rank","PEG","PE"] if c in unified.columns]
    if sort_cols:
        unified=unified.sort_values(by=sort_cols, ascending=True)

    top_n = st.slider("Top-N Candidates", 4, 30, 15)
    st.dataframe(unified.head(top_n), use_container_width=True)

    tickers = ", ".join(sorted(set(unified.head(top_n)["Ticker"].astype(str))))
    st.code(tickers, language="text")
else:
    st.warning("No Zacks files found in /data")

# ------------------------------------------------------------
# TREND COMPARATOR (Last 5 Uploads)
# ------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Zacks Trend Comparator — Last 5 Uploads")

def zacks_trend(category: str):
    files = sorted(
        [f for f in os.listdir(DATA_PATH) if category.lower() in f.lower() and f.endswith(".csv")],
        key=lambda x: os.path.getmtime(os.path.join(DATA_PATH, x)),
        reverse=True
    )[:5]

    if len(files) < 2:
        return None

    latest = pd.read_csv(os.path.join(DATA_PATH, files[0]))
    prev = pd.read_csv(os.path.join(DATA_PATH, files[1]))

    return {
        "latest": files[0],
        "previous": files[1],
        "new": list(set(latest["Ticker"]) - set(prev["Ticker"])),
        "dropped": list(set(prev["Ticker"]) - set(latest["Ticker"]))
    }

for cat in ["Growth 1","Growth 2","Defensive"]:
    tr=zacks_trend(cat)
    if tr:
        st.markdown(f"**{cat} — {tr['latest']} vs {tr['previous']}**")
        st.write("🟢 New:", tr["new"][:10])
        st.write("🔻 Dropped:", tr["dropped"][:10])
    else:
        st.info(f"{cat}: Not enough files for trend comparison")

# ------------------------------------------------------------
# TRAILING STOP MATRIX
# ------------------------------------------------------------
st.markdown("---")
st.subheader("🛡️ Trailing Stop Monitor")

if not portfolio_df.empty and {"Ticker","Current Price"}.issubset(portfolio_df.columns):
    tdf = portfolio_df[["Ticker","Current Price","Current Value"]].copy()
    tdf["Trailing %"] = default_stop
    tdf["Stop Price"] = tdf["Current Price"] * (1 - tdf["Trailing %"] / 100)

    st.dataframe(tdf, use_container_width=True)
else:
    st.info("Portfolio missing Ticker or Current Price columns")

# ------------------------------------------------------------
# EXPORT HUB
# ------------------------------------------------------------
st.markdown("---")
st.subheader("📤 Export Unified Data Bundle (.zip)")

def create_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in os.listdir(DATA_PATH):
            if f.endswith(".csv"):
                zf.write(os.path.join(DATA_PATH, f), arcname=f)
    buf.seek(0)
    return buf

if st.button("Generate Data Bundle"):
    z= create_zip()
    st.download_button("⬇️ Download Data Bundle.zip", data=z,
                       file_name=f"FoxValley_Data_{datetime.now():%Y%m%d}.zip")
    st.success("Bundle ready!")

# ------------------------------------------------------------
# FOOTER / DIAGNOSTICS
# ------------------------------------------------------------
st.markdown("---")
st.caption(f"🧭 Command Deck v7.3R-4.4 — Quantum Surge | Build Time: {datetime.now():%Y-%m-%d %H:%M:%S}")
