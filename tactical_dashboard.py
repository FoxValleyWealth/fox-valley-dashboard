import streamlit as st
import pandas as pd

from modules.portfolio_engine import load_portfolio_data, load_cash_position, calculate_summary, prepare_portfolio_export
from modules.zacks_unified_analyzer import merge_zacks_screens, extract_rank1_candidates, prepare_zacks_export
from modules.trailing_stop_manager.py import apply_trailing_stop
from modules.tactical_controls import process_tactical_action

st.set_page_config(
    page_title="Fox Valley Tactical Command Deck",
    layout="wide"
)

st.title("🧭 Fox Valley Tactical Command Deck — v7.7R — Stable Build")

# ---------------------------------------------------------------------
# FILE UPLOAD SECTION
# ---------------------------------------------------------------------
st.sidebar.header("📂 Upload Portfolio and Zacks Files")

portfolio_file = st.sidebar.file_uploader("Upload Portfolio CSV", type=["csv"])
growth1_file = st.sidebar.file_uploader("Upload Growth 1 CSV", type=["csv"])
growth2_file = st.sidebar.file_uploader("Upload Growth 2 CSV", type=["csv"])
dividend_file = st.sidebar.file_uploader("Upload Defensive Dividends CSV", type=["csv"])

manual_cash = st.sidebar.number_input("Manual Cash Override ($)", min_value=0.0, step=100.0)

# ---------------------------------------------------------------------
# LOAD AND PREPARE DATA
# ---------------------------------------------------------------------
if portfolio_file:
    portfolio_df = load_portfolio_data(portfolio_file)
    cash_value = load_cash_position(manual_cash)
    summary = calculate_summary(portfolio_df, cash_value)

    st.subheader("📊 Portfolio Overview")
    st.metric("💰 Total Portfolio Value", f"${summary['total_value']:,}")
    st.metric("🏦 Cash Available", f"${summary['cash']:,}")
    st.metric("📈 Total Gain/Loss", f"${summary['gain_loss_total']:,}")
    st.metric("📊 Avg Gain/Loss %", f"{summary['avg_gain_loss_pct']}%")

    st.write("### Current Holdings")
    st.dataframe(portfolio_df)

    # Trailing Stops
    portfolio_df = apply_trailing_stop(portfolio_df, trailing_stop_pct=5)
    st.write("### Trailing Stop Protection")
    st.dataframe(portfolio_df)

# ---------------------------------------------------------------------
# ZACKS UNIFIED CANDIDATE PROCESSING
# ---------------------------------------------------------------------
if growth1_file or growth2_file or dividend_file:
    files_dict = {
        "Growth1": growth1_file,
        "Growth2": growth2_file,
        "Dividend": dividend_file
    }
    zacks_df = merge_zacks_screens(files_dict)

    st.subheader("🎯 Unified Zacks Candidates")
    st.dataframe(zacks_df)

    rank1_df = extract_rank1_candidates(zacks_df)
    st.write("🔥 **Zacks Rank 1 Candidates — Highest Tactical Priority**")
    st.dataframe(rank1_df)

# ---------------------------------------------------------------------
# TACTICAL ACTION EXECUTABLE (NO BROKERAGE)
# ---------------------------------------------------------------------
st.subheader("🛠 Tactical Action")
action = st.selectbox("Select Action", ["BUY", "SELL", "TRIM", "HOLD"])
ticker = st.text_input("Ticker (e.g. NVDA)")
shares = st.number_input("Shares", min_value=1, step=1)

if st.button("Execute"):
    result = process_tactical_action(action, ticker, shares)
    st.success(result)

# ---------------------------------------------------------------------
# SYSTEM STATUS FOOTER
# ---------------------------------------------------------------------
st.markdown("---")
st.caption("🧭 Fox Valley Intelligence Engine — Stable Tactical Core v7.7R")
