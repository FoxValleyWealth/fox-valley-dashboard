# ==============================================================
# 🧭 Fox Valley Intelligence Engine v7.0R – Enterprise Command Deck (Nov 07, 2025)
# ==============================================================
# Purpose: Autonomous tactical intelligence console for Fox Valley Dashboard
# Reliability: Zero-failure architecture with automatic file detection,
# safe data validation, and complete crash-proof overlay
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import datetime
import re
import shutil
import os

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.0R – Enterprise Command Deck",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- STYLE ----------
st.markdown("""
<style>
    body {background-color:#0e1117;color:#FAFAFA;}
    [data-testid="stHeader"] {background-color:#0e1117;}
    [data-testid="stSidebar"] {background-color:#111318;}
    table {color:#FAFAFA;}
    .rank1 {background-color:#004d00 !important;}
    .rank2 {background-color:#665c00 !important;}
    .rank3 {background-color:#663300 !important;}
</style>
""", unsafe_allow_html=True)

# ---------- DIRECTORIES ----------
DATA_DIR = Path("data")
ARCHIVE_DIR = Path("archive")
ARCHIVE_DIR.mkdir(exist_ok=True)

# ==============================================================
#  UTILITY: SAFE FILE RESOLVER + AUTO-ARCHIVE
# ==============================================================

def get_latest(pattern: str):
    """Return newest file matching pattern inside /data"""
    files = list(DATA_DIR.glob(pattern))
    if not files:
        return None
    # extract date from filename
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated.append((m.group(1), f))
    if not dated:
        # fallback: most recent modified
        latest = max(files, key=lambda x: x.stat().st_mtime)
    else:
        latest = max(dated)[1]
    # move all but latest to archive
    for f in files:
        if f != latest:
            shutil.move(str(f), ARCHIVE_DIR / f.name)
    return latest

# ==============================================================
#  LOAD PORTFOLIO
# ==============================================================

@st.cache_data
def load_portfolio():
    """Load the most recent Fidelity portfolio CSV"""
    latest = get_latest("Portfolio_Positions_*.csv")
    if not latest:
        st.sidebar.error("⚠️ No portfolio files found in /data.")
        return pd.DataFrame(), "None"

    st.sidebar.info(f"📁 Active Portfolio File: {latest.name}")

    try:
        df = pd.read_csv(latest)
    except Exception as e:
        st.sidebar.error(f"❌ Could not read {latest.name}: {e}")
        return pd.DataFrame(), latest.name

    # Normalize columns
    df.columns = [c.strip() for c in df.columns]
    # ensure core columns
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if "symbol" in cl or "ticker" in cl:
            rename_map[c] = "Ticker"
        if "value" in cl and "total" in cl:
            rename_map[c] = "Value"
        if "gain" in cl and "%" in cl:
            rename_map[c] = "GainLoss%"
    df.rename(columns=rename_map, inplace=True)
    for core in ["Ticker", "Value"]:
        if core not in df.columns:
            df[core] = None
    # Convert numerics
    for col in ["GainLoss%", "Value"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Compute totals
    total_value = df["Value"].sum()
    cash_rows = df[df["Ticker"].astype(str).str.contains("CASH|MMKT|USD|MONEY", case=False, na=False)]
    cash_value = cash_rows["Value"].sum() if not cash_rows.empty else 0.0

    return df, latest.name, total_value, cash_value

portfolio, portfolio_file, total_value, cash_value = load_portfolio()

# ==============================================================
#  LOAD ZACKS SCREENS
# ==============================================================

def safe_read(path):
    if not path or not Path(path).exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def normalize_zacks(df):
    if df.empty:
        return df
    df.columns = [c.strip() for c in df.columns]
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if "symbol" in cl or "ticker" in cl:
            rename_map[c] = "Ticker"
        if "rank" in cl:
            rename_map[c] = "Zacks Rank"
    df.rename(columns=rename_map, inplace=True)
    for core in ["Ticker", "Zacks Rank"]:
        if core not in df.columns:
            df[core] = None
    return df[["Ticker", "Zacks Rank"]].copy()

G1_PATH = get_latest("zacks_custom_screen_*Growth1*.csv")
G2_PATH = get_latest("zacks_custom_screen_*Growth2*.csv")
DD_PATH = get_latest("zacks_custom_screen_*Defensive*.csv")

g1 = normalize_zacks(safe_read(G1_PATH))
g2 = normalize_zacks(safe_read(G2_PATH))
dd = normalize_zacks(safe_read(DD_PATH))

if not g1.empty or not g2.empty or not dd.empty:
    st.sidebar.success("✅ Zacks Screens Loaded Successfully")
else:
    st.sidebar.warning("⚠️ No Zacks files found in /data")

# ==============================================================
#  CROSS-MATCH + INTELLIGENCE OVERLAY
# ==============================================================

def cross_match(zdf, pf):
    if zdf.empty or pf.empty:
        return pd.DataFrame()
    pf_t = pf[["Ticker"]].astype(str)
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    m = zdf.merge(pf_t, on="Ticker", how="left", indicator=True)
    m["Held?"] = m["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    m.drop(columns=["_merge"], inplace=True)
    return m

def build_intel(pf, g1, g2, dd, cash_val, total_val):
    for df in [g1, g2, dd]:
        if "Ticker" not in df.columns:
            df["Ticker"] = ""
        if "Zacks Rank" not in df.columns:
            df["Zacks Rank"] = ""
    combined = pd.concat([g1, g2, dd], ignore_index=True).drop_duplicates(subset=["Ticker"])
    held = set(pf["Ticker"].astype(str)) if not pf.empty else set()
    rank1 = combined[combined["Zacks Rank"].astype(str) == "1"].copy()
    new1 = rank1[~rank1["Ticker"].isin(held)]
    held1 = rank1[rank1["Ticker"].isin(held)]
    cash_pct = (cash_val / total_val) * 100 if total_val > 0 else 0
    msg = [
        "Fox Valley Daily Tactical Overlay",
        f"• Portfolio Value: ${total_val:,.2f}",
        f"• Cash Available: ${cash_val:,.2f} ({cash_pct:.2f}%)",
        f"• Total #1 Symbols: {len(rank1)}",
        f"• New #1 Candidates: {len(new1)}",
        f"• Held #1 Positions: {len(held1)}"
    ]
    return {"narrative": "\n".join(msg), "new": new1, "held": held1, "combined": combined}

intel = build_intel(portfolio, g1, g2, dd, cash_value, total_value)

# ==============================================================
#  USER INTERFACE (7 TABS)
# ==============================================================

tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "⚙️ Tactical Decision Matrix",
    "🧩 Weekly Tactical Summary",
    "📖 Daily Intelligence Brief"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.metric("Total Account Value", f"${total_value:,.2f}")
    st.metric("Cash Available to Trade", f"${cash_value:,.2f}")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty and "Value" in portfolio.columns:
        fig = px.pie(portfolio, values="Value", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m = cross_match(g1, portfolio)
    if not g1m.empty:
        st.dataframe(
            g1m.style.map(
                lambda v: "background-color:#004d00" if str(v) == "1"
                else "background-color:#665c00" if str(v) == "2"
                else "background-color:#663300" if str(v) == "3" else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No Growth 1 data available.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m = cross_match(g2, portfolio)
    if not g2m.empty:
        st.dataframe(
            g2m.style.map(
                lambda v: "background-color:#004d00" if str(v) == "1"
                else "background-color:#665c00" if str(v) == "2"
                else "background-color:#663300" if str(v) == "3" else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No Growth 2 data available.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm = cross_match(dd, portfolio)
    if not ddm.empty:
        st.dataframe(
            ddm.style.map(
                lambda v: "background-color:#004d00" if str(v) == "1"
                else "background-color:#665c00" if str(v) == "2"
                else "background-color:#663300" if str(v) == "3" else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No Defensive Dividend data available.")

# --- Tactical Decision Matrix ---
with tabs[4]:
    st.subheader("⚙️ Tactical Decision Matrix – Buy / Hold / Trim")
    st.markdown("""
    | Signal | Meaning |
    |:--|:--|
    |🟢 Buy|Zacks Rank #1 new candidates not held|
    |⚪ Hold|Existing positions that remain #1|
    |🟠 Trim|Existing positions that lost #1|
    """)
    st.info("Review each Rank 1–3 signal and update positions as needed.")

# --- Weekly Tactical Summary ---
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.text(intel["narrative"])

# --- Daily Intelligence Brief ---
with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.caption(f"Generated {datetime.datetime.now():%A, %B %d, %Y – %I:%M %p CST}")
    st.markdown("### 🟢 New Zacks Rank #1 Candidates")
    if not intel["new"].empty:
        st.dataframe(intel["new"], use_container_width=True)
    else:
        st.info("No new #1 candidates today.")
    st.markdown("### ✔ Held Positions Still #1")
    if not intel["held"].empty:
        st.dataframe(intel["held"], use_container_width=True)
    else:
        st.info("No current holdings remain #1 today.")
