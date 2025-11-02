# ============================================
# FOX VALLEY TACTICAL DASHBOARD v3 – Nov 2025
# Zacks Tactical Integration Edition (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Fox Valley Tactical Dashboard v3",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# ---------- LOAD ZACKS SCREENS ----------
G1_PATH = "data/zacks_custom_screen_2025-11-02_Growth1.csv"
G2_PATH = "data/zacks_custom_screen_2025-11-02_Growth2.csv"
DD_PATH = "data/zacks_custom_screen_2025-11-02_DefensiveDividend.csv"

def safe_read(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Zacks files loaded automatically from /data")
else:
    st.sidebar.error("⚠️ No Zacks files found in /data. Add them in GitHub → /data.")

# ---------- UTILITIES ----------
def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if ticker_cols:
        df = df.rename(columns={ticker_cols[0]: "Ticker"})
    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols:
            df = df.rename(columns={rank_cols[0]: "Zacks Rank"})
    keep = []
    if "Ticker" in df.columns:
        keep.append("Ticker")
    if "Zacks Rank" in df.columns:
        keep.append("Zacks Rank")
    df = df[keep].copy()
    return df

def cross_match(zacks_df: pd.DataFrame, portfolio_df: pd.DataFrame) -> pd.DataFrame:
    if zacks_df.empty:
        return zacks_df
    pf = portfolio_df[["Ticker"]].copy()
    pf["Ticker"] = pf["Ticker"].astype(str)
    zacks_df["Ticker"] = zacks_df["Ticker"].astype(str)
    merged = zacks_df.merge(pf, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

# ---------- NORMALIZE ZACKS ----------
g1 = normalize_zacks(g1_raw)
g2 = normalize_zacks(g2_raw)
dd = normalize_zacks(dd_raw)

# ---------- MAIN TABS ----------
tabs = st.tabs(["💼 Portfolio Overview", "📊 Growth 1", "📊 Growth 2", "💰 Defensive Dividend"])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)

    if not portfolio.empty:
        fig1 = px.pie(portfolio, values="Value", names="Ticker",
                      title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No portfolio data found in /data/portfolio_data.csv")

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    if not g1.empty:
        g1_matched = cross_match(g1, portfolio)
        st.dataframe(
            g1_matched.style.map(
                lambda val: "background-color: #004d00" if str(val) == "1"
                else "background-color: #665c00" if str(val) == "2"
                else "background-color: #663300" if str(val) == "3"
                else ""
            , subset=["Zacks Rank"]),
            use_container_width=True
        )
    else:
        st.info("Zacks Growth 1 screen not found or empty in /data.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    if not g2.empty:
        g2_matched = cross_match(g2, portfolio)
        st.dataframe(
            g2_matched.style.map(
                lambda val: "background-color: #004d00" if str(val) == "1"
                else "background-color: #665c00" if str(val) == "2"
                else "background-color: #663300" if str(val) == "3"
                else ""
            , subset=["Zacks Rank"]),
            use_container_width=True
        )
    else:
        st.info("Zacks Growth 2 screen not found or empty in /data.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    if not dd.empty:
        dd_matched = cross_match(dd, portfolio)
        st.dataframe(
            dd_matched.style.map(
                lambda val: "background-color: #004d00" if str(val) == "1"
                else "background-color: #665c00" if str(val) == "2"
                else "background-color: #663300" if str(val) == "3"
                else ""
            , subset=["Zacks Rank"]),
            use_container_width=True
        )
    else:
        st.info("Zacks Defensive Dividend screen not found or empty in /data.")

st.markdown("---")
st.caption("Automation hook ready for Sunday 07:00 CST tactical summary.")
