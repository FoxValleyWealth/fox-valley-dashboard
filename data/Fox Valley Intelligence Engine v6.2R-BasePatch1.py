# ============================================
# 🧭 Fox Valley Intelligence Engine v6.2R – Stable Build (Nov 05, 2025)
# ============================================

import os
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.2R",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- DARK MODE ----------
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

# ---------- PORTFOLIO LOAD + NORMALIZATION ----------
data_path = os.path.join(os.path.dirname(__file__), "data", "Portfolio_Positions_Nov-05-2025.csv")
st.write(f"📂 Attempting to load: {data_path}")

try:
    portfolio = pd.read_csv(data_path)
    st.success("✅ Portfolio loaded successfully!")
except Exception as e:
    st.error(f"❌ Unable to load Portfolio_Positions_Nov-05-2025.csv: {e}")
    st.stop()

# --- Clean column names ---
portfolio.columns = [c.strip() for c in portfolio.columns]

# --- Rename Fidelity headers ---
portfolio.rename(columns={
    "Symbol": "Ticker",
    "Quantity": "Shares",
    "Last Price": "MarketPrice",
    "Cost Basis Total": "CostBasis",
    "Current Value": "MarketValue",
    "Total Gain/Loss Dollar": "GainLoss$",
    "Total Gain/Loss Percent": "GainLoss%"
}, inplace=True)

# --- Normalize tickers ---
if "Ticker" in portfolio.columns:
    portfolio["Ticker"] = portfolio["Ticker"].astype(str).str.strip().str.upper()
    portfolio["Ticker"] = portfolio["Ticker"].str.replace(r"[^A-Z]", "", regex=True)
else:
    st.warning("⚠️ Missing 'Ticker' column in portfolio file.")

# --- Clean numeric fields ---
money_cols = ["MarketPrice", "CostBasis", "MarketValue", "GainLoss$", "GainLoss%"]
for col in money_cols:
    if col in portfolio.columns:
        portfolio[col] = (
            portfolio[col]
            .astype(str)
            .str.replace('[\$,()%+]', '', regex=True)
            .str.strip()
        )
        portfolio[col] = pd.to_numeric(portfolio[col], errors="coerce")

# --- Ensure Shares is numeric ---
if "Shares" in portfolio.columns:
    portfolio["Shares"] = pd.to_numeric(portfolio["Shares"], errors="coerce")

# --- Compute missing MarketValue ---
if "MarketValue" not in portfolio.columns and all(
    c in portfolio.columns for c in ["Shares", "MarketPrice"]
):
    portfolio["MarketValue"] = portfolio["Shares"] * portfolio["MarketPrice"]

# ---------- DASHBOARD ----------
tabs = st.tabs(["💼 Portfolio Overview", "📊 Growth 1", "📊 Growth 2", "💰 Defensive Dividend",
                "⚙️ Tactical Decision Matrix", "🧩 Tactical Summary", "📖 Daily Intelligence Brief"])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("💼 Current Portfolio Overview")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty and "MarketValue" in portfolio.columns and "Ticker" in portfolio.columns:
        fig = px.pie(portfolio, values="MarketValue", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

# --- Tactical Summary Placeholder ---
with tabs[5]:
    total_value = portfolio["MarketValue"].sum() if "MarketValue" in portfolio.columns else 0
    st.subheader("🧩 Tactical Summary")
    st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    st.metric("Positions Tracked", f"{len(portfolio)}")

# --- Intelligence Brief Placeholder ---
with tabs[6]:
    st.subheader("📖 Daily Intelligence Brief")
    st.caption(f"Generated {datetime.datetime.now():%A, %B %d, %Y – %I:%M %p CST}")
    st.info("No Zacks screen data loaded for this demo build.")
