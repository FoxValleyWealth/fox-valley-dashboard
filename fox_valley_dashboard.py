
# ============================================
# FOX VALLEY TACTICAL DASHBOARD v3 – Nov 2025
# Zacks Tactical Integration Edition (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="Fox Valley Tactical Dashboard v3",
                   layout="wide",
                   initial_sidebar_state="expanded")

# --- DARK MODE STYLE ---
st.markdown("""
    <style>
        body {background-color:#0e1117;color:#FAFAFA;}
        [data-testid="stHeader"] {background-color:#0e1117;}
        [data-testid="stSidebar"] {background-color:#111318;}
        table {color:#FAFAFA;}
        .rank1 {background-color:#004d00 !important;} /* 🟩 */
        .rank2 {background-color:#665c00 !important;} /* 🟨 */
        .rank3 {background-color:#663300 !important;} /* 🟧 */
    </style>
""", unsafe_allow_html=True)

# ---------- LOAD PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    return df

portfolio = load_portfolio()
total_value = portfolio["Value"].astype(float).sum()

# ---------- DASHBOARD HEADER ----------
st.title("🧭 Fox Valley Tactical Dashboard v3")
col1, col2 = st.columns(2)
col1.metric("Total Account Value", f"${total_value:,.2f}")
cash_row = portfolio[portfolio["Ticker"].str.contains("SPAXX", na=False)]
cash_value = cash_row["Value"].astype(float).sum()
col2.metric("Cash – SPAXX (Money Market)", f"${cash_value:,.2f}")

st.markdown("---")

# ---------- SIDEBAR ZACKS UPLOADS ----------
# ---------- LOAD ZACKS SCREENS FROM /data ----------
st.sidebar.header("📈 Zacks Screens – Auto-Loaded from Repository")

g1_path = "data/zacks_custom_screen_2025-11-02_Growth1.csv"
g2_path = "data/zacks_custom_screen_2025-11-02_Growth2.csv"
dd_path = "data/zacks_custom_screen_2025-11-02_DefensiveDividend.csv"

try:
    g1 = pd.read_csv(g1_path)
    g2 = pd.read_csv(g2_path)
    dd = pd.read_csv(dd_path)
    st.sidebar.success("✅ Zacks files loaded automatically")
except Exception as e:
    st.sidebar.error(f"⚠️ Could not load Zacks screens: {e}")
    g1 = g2 = dd = pd.DataFrame()

# ---------- UTILITIES ----------
def read_zacks(file):
    df = pd.read_csv(file)
    cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if cols:
        df.rename(columns={cols[0]:"Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols: df.rename(columns={rank_cols[0]:"Zacks Rank"}, inplace=True)
    return df[["Ticker","Zacks Rank"]] if "Ticker" in df.columns else pd.DataFrame()

def highlight_rank(rank):
    try:
        r = int(rank)
        if r==1: return "rank1"
        elif r==2: return "rank2"
        else: return "rank3"
    except: return ""

def cross_match(zdf, pf):
    if zdf.empty: return pd.DataFrame()
    merged = zdf.merge(pf[["Ticker"]], on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both":"✔ Held","left_only":"🟢 Candidate"})
    merged.drop(columns="_merge", inplace=True)
    return merged

# ---------- MAIN TABS ----------
tabs = st.tabs(["💼 Portfolio Overview","📊 Growth 1","📊 Growth 2","💰 Defensive Dividend"])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)

    fig1 = px.pie(portfolio, values="Value", names="Ticker",
                  title="Portfolio Allocation", hole=0.3)
    st.plotly_chart(fig1, use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    if g1_file:
        g1 = read_zacks(g1_file)
        g1 = cross_match(g1, portfolio)
        st.dataframe(g1.style.applymap(lambda x: "color:#FFF;", subset=["Ticker"])
                          .apply(lambda s: [highlight_rank(v) for v in s], subset=["Zacks Rank"]),
                     use_container_width=True)
    else:
        st.info("Upload Growth 1 CSV in sidebar to view results.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    if g2_file:
        g2 = read_zacks(g2_file)
        g2 = cross_match(g2, portfolio)
        st.dataframe(g2.style.applymap(lambda x: "color:#FFF;", subset=["Ticker"])
                          .apply(lambda s: [highlight_rank(v) for v in s], subset=["Zacks Rank"]),
                     use_container_width=True)
    else:
        st.info("Upload Growth 2 CSV in sidebar to view results.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    if dd_file:
        dd = read_zacks(dd_file)
        dd = cross_match(dd, portfolio)
        st.dataframe(dd.style.applymap(lambda x: "color:#FFF;", subset=["Ticker"])
                          .apply(lambda s: [highlight_rank(v) for v in s], subset=["Zacks Rank"]),
                     use_container_width=True)
    else:
        st.info("Upload Defensive Dividend CSV in sidebar to view results.")

st.markdown("---")
st.caption("Automation hook ready for Sunday 07:00 CST tactical summary.")

