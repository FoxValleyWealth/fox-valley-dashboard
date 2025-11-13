# ================================================================
# Fox Valley Intelligence Engine — Command Deck v7.4R-C (Unified Build)
# FULL & FINAL STABILITY RELEASE — ENTIRE FILE
# File: fox_valley_dashboard.py
# ================================================================

import os
import io
import math
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import zipfile
import csv

# ================================================================
# PAGE CONFIGURATION
# ================================================================
st.set_page_config(
    page_title="Fox Valley Intelligence Engine — Command Deck v7.4R-C",
    page_icon="🧭",
    layout="wide",
)

st.markdown("""
<style>
div.block-container{padding-top:1.5rem}
.section-card{background:rgba(255,255,255,.02); border:1px solid rgba(255,255,255,.08);
              border-radius:16px; padding:1rem 1.5rem; margin-bottom:1rem}
.data-ok{color:#22c55e;font-weight:600}
.data-warn{color:#f59e0b;font-weight:600}
.data-err{color:#ef4444;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ================================================================
# DATA PATHS + AUTO-DETECT SYSTEM
# ================================================================
DATA_PATH = "data"
PORTFOLIO_FILE = None
ZACKS_G1_FILE = None
ZACKS_G2_FILE = None
ZACKS_DD_FILE = None

def auto_detect_files():
    global PORTFOLIO_FILE, ZACKS_G1_FILE, ZACKS_G2_FILE, ZACKS_DD_FILE
    if not os.path.exists(DATA_PATH):
        return
    files = os.listdir(DATA_PATH)
    pfiles = [f for f in files if f.lower().startswith("portfolio_positions_")]
    if pfiles:
        PORTFOLIO_FILE = os.path.join(DATA_PATH, sorted(pfiles)[-1])
    def find(prefix):
        cands = [f for f in files if f.lower().startswith(prefix.lower())]
        return os.path.join(DATA_PATH, sorted(cands)[-1]) if cands else None
    ZACKS_G1_FILE = find("zacks_custom_screen_2025-11-13 growth 1")
    ZACKS_G2_FILE = find("zacks_custom_screen_2025-11-13 growth 2")
    ZACKS_DD_FILE = find("zacks_custom_screen_2025-11-13 defensive dividends")

auto_detect_files()

# ================================================================
# HELPERS
# ================================================================
def money(x):
    if pd.isna(x): return "—"
    return f"${x:,.2f}"

def clean_numeric(s):
    if pd.isna(s): return np.nan
    t = str(s).replace("$"," ").replace(","," ").replace("%"," ").strip()
    if t.startswith("(") and t.endswith(")"):
        try: return -float(t.replace("(","").replace(")",""))
        except: return np.nan
    try: return float(t)
    except: return np.nan

# ================================================================
# CSV LOADER
# ================================================================
@st.cache_data(show_spinner=False)
def load_csv(path: str):
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
# NORMALIZATION
# ================================================================
def normalize_column_names(df):
    if df.empty: return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename_map = {}
    if "Symbol" in df.columns and "Ticker" not in df.columns:
        rename_map["Symbol"] = "Ticker"
    for alt in ["Security Description","Name"]:
        if alt in df.columns and "Description" not in df.columns:
            rename_map[alt] = "Description"
    for c in df.columns:
        if c.lower() in ["zacks","rank","zacksrank"]:
            rename_map[c] = "Zacks Rank"
    df.rename(columns=rename_map, inplace=True)
    return df

def enforce_ticker_column(df):
    if df.empty: return df
    df = df.copy()
    if "Ticker" in df.columns:
        return df
    if "Symbol" in df.columns:
        df.rename(columns={"Symbol":"Ticker"}, inplace=True)
        return df
    if "Description" in df.columns:
        df["Ticker"] = df["Description"].astype(str).str.split().str[0]
        return df
    df["Ticker"] = [f"UNK{i+1}" for i in range(len(df))]
    return df

def apply_naming_standards(df):
    df = normalize_column_names(df)
    df = enforce_ticker_column(df)
    return df

# ================================================================
# LOAD ALL DATASETS
# ================================================================
portfolio_df, pmsg = load_csv(PORTFOLIO_FILE)
portfolio_df = apply_naming_standards(portfolio_df)
g1_df, _ = load_csv(ZACKS_G1_FILE); g1_df = apply_naming_standards(g1_df)
g2_df, _ = load_csv(ZACKS_G2_FILE); g2_df = apply_naming_standards(g2_df)
dd_df, _ = load_csv(ZACKS_DD_FILE); dd_df = apply_naming_standards(dd_df)

all_z = (
    pd.concat([
        g1_df.assign(Source="Growth 1") if not g1_df.empty else None,
        g2_df.assign(Source="Growth 2") if not g2_df.empty else None,
        dd_df.assign(Source="Defensive Dividends") if not dd_df.empty else None,
    ], ignore_index=True).dropna(how="all", axis=1)
    if any([not g1_df.empty, not g2_df.empty, not dd_df.empty])
    else pd.DataFrame()
)

# ================================================================
# HEADER
# ================================================================
st.title("🧭 Fox Valley Intelligence Engine — Enterprise Command Deck (v7.4R-C)")
st.caption("Portfolio • Zacks • Tactical • Allocation • Evolution • Sector Intelligence")

# ================================================================
# PORTFOLIO OVERVIEW
# ================================================================
st.header("📊 Portfolio Overview — v7.4R-C")
c1,c2,c3,c4 = st.columns(4)

val_col = next((c for c in ["Current Value","Market Value","Value"] if c in portfolio_df.columns), None)
est_total = float(pd.to_numeric(portfolio_df[val_col], errors="coerce").sum()) if val_col else 0.0

with c1: st.metric("Estimated Total Value", money(est_total))

manual_cash = st.sidebar.number_input(
    "💰 Cash Available to Trade ($)", min_value=0.0, step=100.0, value=0.0)
with c2: st.metric("Cash Available to Trade", money(manual_cash))

with c3:
    dg = pd.to_numeric(portfolio_df.get("Day Gain", pd.Series(dtype=float)), errors="coerce")
    st.metric("Day Gain (sum)", money(dg.sum()) if not dg.empty else "—")

with c4:
    gl = pd.to_numeric(portfolio_df.get("Gain/Loss %", pd.Series(dtype=float)), errors="coerce")
    st.metric("Avg Gain/Loss %", f"{gl.mean():.2f}%" if not gl.empty else "—")

if manual_cash == 0:
    st.warning("Manual cash is 0 — update sidebar for accuracy.")
else:
    st.success(f"Manual cash override active: {money(manual_cash)}")

st.dataframe(portfolio_df, use_container_width=True)

# ================================================================
# ZACKS TOP CANDIDATES
# ================================================================
st.header("🔎 Zacks Unified Analyzer — Top Candidates")

if not all_z.empty:
    if "Zacks Rank" in all_z.columns:
        all_z["Zacks Rank"] = pd.to_numeric(all_z["Zacks Rank"], errors="coerce")
    sort_cols = [c for c in ["Zacks Rank","PEG","PE"] if c in all_z.columns]
    if sort_cols:
        all_z = all_z.sort_values(by=sort_cols, ascending=True)
    top_n = st.slider("Top-N Candidates", 4, 30, 8)
    st.dataframe(all_z.head(top_n), use_container_width=True)
    tickers = ", ".join(sorted(set(all_z.head(top_n)["Ticker"].astype(str))))
    st.code(tickers, language="text")
else:
    st.warning("No Zacks data available.")

# ================================================================
# ZACKS EVOLUTION ENGINE
# ================================================================
st.header("📈 Zacks Evolution Engine — v7.4R-C")

if not g2_df.empty and not g1_df.empty:
    old = g1_df["Ticker"].astype(str).str.upper().tolist()
    new = g2_df["Ticker"].astype(str).str.upper().tolist()
    added = sorted([t for t in new if t not in old])
    dropped = sorted([t for t in old if t not in new])
    st.subheader("🟢 New"); st.write(added if added else "[]")
    st.subheader("🔻 Dropped"); st.write(dropped if dropped else "[]")
else:
    st.info("Not enough Zacks files for evolution comparison.")

# ================================================================
# ALLOCATION ENGINE
# ================================================================
ALLOCATION_MAP = {
    "AMZN":"Growth","COMM":"Growth","RDDT":"Growth","NBIX":"Growth","GRND":"Growth",
    "ALL":"Defensive","HSBC":"Defensive","PRK":"Defensive","NEM":"Defensive","NVT":"Defensive","ARMN":"Defensive",
    "AU":"Core","IBKR":"Core","CNQ":"Core","TPC":"Core","NTB":"Core",
    "LCII":"Core","CUBI":"Core","CALX":"Core","KAR":"Core","DINO":"Core","CBOE":"Core",
}

def apply_allocation_category(df):
    if df.empty: return df
    df = df.copy()
    df["Category"] = df["Ticker"].apply(lambda x: ALLOCATION_MAP.get(str(x).upper(),"Unassigned"))
    return df

def calculate_allocation(df):
    if df.empty or "Current Value" not in df.columns:
        return df, {}
    df = df.copy()
    total = df["Current Value"].sum()
    if total <= 0: return df, {}
    df["Allocation %"] = (df["Current Value"] / total) * 100
    cat_weights = (df.groupby("Category")["Current Value"].sum() / total * 100).to_dict()
    return df, cat_weights

def allocation_panel():
    st.header("📊 Allocation System — v7.4R-C")
    if portfolio_df.empty:
        st.warning("Portfolio not loaded — cannot compute allocation.")
        return
    df = apply_allocation_category(portfolio_df)
    df, cat_weights = calculate_allocation(df)
    cols_to_show = ["Ticker","Description","Current Value","Category","Allocation %"]
    cols_to_show = [c for c in cols_to_show if c in df.columns]
    st.dataframe(df[cols_to_show], use_container_width=True)
    st.subheader("📡 Category Exposure (%)")
    if cat_weights:
        for cat,pct in cat_weights.items():
            st.write(f"**{cat}: {pct:.2f}%**")
    else:
        st.info("No category data available.")

allocation_panel()

# ================================================================
# SECTOR EXPOSURE ENGINE
# ================================================================
def sector_exposure_panel():
    st.header("🏛 Sector Exposure Map — v7.4R-C")
    if portfolio_df.empty:
        st.info("Portfolio not loaded — cannot calculate sectors.")
        return
    if "Sector" not in portfolio_df.columns:
        st.info("No sector column detected — skipping sector breakdown.")
        return
    df = portfolio_df.copy()
    if "Current Value" not in df.columns:
        st.info("Missing Current Value — cannot compute sector distribution.")
        return
    total = df["Current Value"].sum()
    if total <= 0:
        st.info("Invalid total value — cannot compute sector distribution.")
        return
    sector_weights = (df.groupby("Sector")["Current Value"].sum() / total * 100).to_dict()
    st.subheader("📡 Sector Allocation (%)")
    for sec,pct in sector_weights.items():
        st.write(f"**{sec}: {pct:.2f}%**")

sector_exposure_panel()

# ================================================================
# EXPORT ENGINE
# ================================================================
def export_bundle():
    st.header("📤 Export Unified Data Bundle (.zip)")
    if st.button("Generate Export Bundle", use_container_width=True):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            if PORTFOLIO_FILE:
                z.write(PORTFOLIO_FILE, arcname=os.path.basename(PORTFOLIO_FILE))
            if ZACKS_G1_FILE:
                z.write(ZACKS_G1_FILE, arcname=os.path.basename(ZACKS_G1_FILE))
            if ZACKS_G2_FILE:
                z.write(ZACKS_G2_FILE, arcname=os.path.basename(ZACKS_G2_FILE))
            if ZACKS_DD_FILE:
                z.write(ZACKS_DD_FILE, arcname=os.path.basename(ZACKS_DD_FILE))
        st.download_button("Download Unified Export Bundle",
            buffer.getvalue(),"FoxValley_ExportBundle.zip","application/zip")

export_bundle()

# ================================================================
# TACTICAL OPERATIONS CENTER — v7.4R-C
# ================================================================

# Initialize tactical log
if "tactical_log" not in st.session_state:
    st.session_state.tactical_log = []

# ---------------------------------------------------------------
# Tactical Action Logger
# ---------------------------------------------------------------
def log_tactical_action(action, ticker, qty=None, pct=None, notes=""):
    st.session_state.tactical_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "ticker": ticker,
        "qty": qty,
        "pct": pct,
        "notes": notes
    })

# ---------------------------------------------------------------
# Tactical Intel Engine
# ---------------------------------------------------------------
def generate_intel(action, ticker, qty=None, pct=None):
    ideas = []

    # Position check
    pos = portfolio_df[portfolio_df["Ticker"].astype(str).str.upper() == str(ticker).upper()]
    if not pos.empty:
        ideas.append("Existing position detected.")
    else:
        ideas.append("NEW entry — no current holdings.")

    # Zacks confirmation
    zf = all_z[all_z["Ticker"].astype(str).str.upper() == str(ticker).upper()]
    if not zf.empty:
        zr = pd.to_numeric(zf.get("Zacks Rank", pd.Series([None])).iloc[0], errors="coerce")
        if not pd.isna(zr):
            ideas.append(f"Zacks Rank {zr} alignment.")
        else:
            ideas.append("In Zacks list (rank not specified).")
    else:
        ideas.append("Not found in Zacks screens.")

    if action == "BUY":
        ideas.append("BUY request — confirm allocation + trend alignment.")
    elif action == "SELL":
        ideas.append("SELL request — evaluate reason for exit.")
    elif action == "TRIM":
        ideas.append(f"TRIM request — {pct}% reduction.")
    elif action == "HOLD":
        ideas.append("Position on HOLD — no immediate change.")

    return ideas

# ---------------------------------------------------------------
# Tactical Console UI
# ---------------------------------------------------------------
def tactical_console():
    st.header("🎯 Tactical Operations Center — v7.4R-C")

    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        action = st.selectbox("Action", ["BUY", "SELL", "HOLD", "TRIM"])
        ticker = st.text_input("Ticker")

    with col2:
        qty = st.number_input("Shares", min_value=0, step=1)
        pct = st.slider("Trim %", 1, 50, 10)

    with col3:
        notes = st.text_area("Execution Notes")
        if st.button("Log Action", use_container_width=True):
            intel = generate_intel(action, ticker, qty, pct if action == "TRIM" else None)
            st.subheader("🧠 Tactical Insights")
            for idea in intel:
                st.markdown(f"- {idea}")

            log_tactical_action(action, ticker,
                                qty if qty > 0 else None,
                                pct if action == "TRIM" else None,
                                notes)

            st.success(f"{action} logged for {ticker}")

    st.markdown("---")
    display_tactical_log()

# ---------------------------------------------------------------
# Display Tactical Log
# ---------------------------------------------------------------
def display_tactical_log():
    st.subheader("📘 Tactical Log — Session Actions")
    if not st.session_state.tactical_log:
        st.info("No tactical actions recorded.")
        return

    for entry in st.session_state.tactical_log:
        st.markdown(f"**[{entry['timestamp']}]** — `{entry['action']}` **{entry['ticker']}**")
        if entry.get("qty"):
            st.write(f"Shares: {entry['qty']}")
        if entry.get("pct"):
            st.write(f"Trim %: {entry['pct']}%")
        if entry.get("notes"):
            st.write(f"Notes: {entry['notes']}")
        st.markdown("---")

# Render Tactical Console
tactical_console()

# ================================================================
# SYSTEM DIAGNOSTICS — v7.4R-C
# ================================================================
st.header("🩺 System Diagnostics — v7.4R-C")

diag = []

# Portfolio file check
diag.append(("Portfolio File", PORTFOLIO_FILE, os.path.exists(PORTFOLIO_FILE) if PORTFOLIO_FILE else False))
diag.append(("Zacks G1 File", ZACKS_G1_FILE, os.path.exists(ZACKS_G1_FILE) if ZACKS_G1_FILE else False))
diag.append(("Zacks G2 File", ZACKS_G2_FILE, os.path.exists(ZACKS_G2_FILE) if ZACKS_G2_FILE else False))
diag.append(("Zacks DD File", ZACKS_DD_FILE, os.path.exists(ZACKS_DD_FILE) if ZACKS_DD_FILE else False))

for label, path, status in diag:
    if status:
        st.markdown(f"**{label}:** <span class='data-ok'>OK</span> — {path}", unsafe_allow_html=True)
    else:
        st.markdown(f"**{label}:** <span class='data-err'>Missing</span>", unsafe_allow_html=True)

# ================================================================
# END OF FULL UNIFIED FILE — v7.4R-C
# ================================================================
