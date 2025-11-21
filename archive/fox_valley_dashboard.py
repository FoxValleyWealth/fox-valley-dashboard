# ============================================================
# 🧭 FOX VALLEY INTELLIGENCE ENGINE — COMMAND DECK
# v7.3R-5.5 — Modular Engines + Intelligence Brief Online
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np

# ------------------------------------------------------------
# Engine Module Imports
# ------------------------------------------------------------
from modules.portfolio_engine import (
    load_portfolio,
    compute_portfolio_metrics,
    load_archive_portfolio_history,
)

from modules.zacks_engine import (
    load_zacks_files_auto,
    merge_zacks_screens,
    score_zacks_candidates,
    get_top_n,
    highlight_rank_1,
)

from modules.dashboard_engine import attach_trailing_stops
from modules.analytics_engine import render_analytics_clusters
from modules.tactical_engine import process_and_render_tactical

from modules.ui_bridge import (
    render_metric_cards,
    render_diagnostics,
    render_tactical_panel,   # kept for future UI hooks
    render_event_log,
    show_dataframe,
    render_zacks_intel_brief,
    render_footer,
)

# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Fox Valley Intelligence Engine – Command Deck",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# SIDEBAR — CONTROL PANEL
# ============================================================
with st.sidebar:
    st.markdown("## 🧭 Command Deck Controls")

    manual_cash = st.number_input(
        "Enter Cash Available to Trade ($)",
        min_value=0.0,
        value=0.0,
        step=50.0,
        key="manual_cash_override",
    )

    st.markdown("---")
    default_trailing_stop = st.number_input(
        "Default Trailing Stop (%)",
        min_value=0.0,
        max_value=50.0,
        value=1.0,
        step=0.5,
        key="default_trailing_stop",
    )

    st.markdown("---")
    top_n = st.number_input(
        "Top-N Zacks Candidates",
        min_value=1,
        max_value=50,
        value=8,
        step=1,
        key="top_n_candidates",
    )

    st.markdown("---")
    st.markdown("### 🎯 Tactical Controls")
    buy_ticker = st.text_input("Buy Ticker")
    buy_shares = st.number_input("Buy Shares", min_value=0, step=1)

    sell_ticker = st.text_input("Sell Ticker")
    sell_shares = st.number_input("Sell Shares", min_value=0, step=1)

# ============================================================
# DATA INGESTION
# ============================================================
portfolio_df, portfolio_filename = load_portfolio()
zacks_files = load_zacks_files_auto()

# Portfolio metrics
total_value, cash_value, avg_gain = compute_portfolio_metrics(portfolio_df)
available_cash = manual_cash if manual_cash > 0 else cash_value

# Zacks processing
zacks_unified = merge_zacks_screens(zacks_files)
scored_candidates = score_zacks_candidates(zacks_unified)
top_n_df = get_top_n(scored_candidates, top_n)

# ============================================================
# PAGE HEADER
# ============================================================
st.markdown(
    """
# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck  
**v7.3R-5.5** | Modular Engines + Zacks Intelligence Brief Online  
"""
)

# ============================================================
# METRIC CARDS (UI BRIDGE)
# ============================================================
render_metric_cards(total_value, available_cash, avg_gain)

# ============================================================
# DIAGNOSTICS PANEL
# ============================================================
render_diagnostics(manual_cash, portfolio_filename, zacks_files)

# ============================================================
# 🧠 ZACKS INTELLIGENCE BRIEF
# ============================================================
render_zacks_intel_brief(scored_candidates)

# ============================================================
# 🔎 ZACKS UNIFIED ANALYZER — TOP CANDIDATES
# ============================================================
st.markdown("## 🔎 Zacks Unified Analyzer — Top Candidates")

if not top_n_df.empty:
    st.dataframe(top_n_df.style.apply(highlight_rank_1, axis=1), use_container_width=True)
else:
    st.warning("No Zacks candidates available for Top-N view.")

# ============================================================
# 📂 ZACKS TACTICAL SCREENS (RAW DATA)
# ============================================================
show_dataframe(zacks_files)

# ============================================================
# 📊 PORTFOLIO POSITIONS (WITH TRAILING STOPS)
# ============================================================
portfolio_with_stops = attach_trailing_stops(portfolio_df, default_trailing_stop)
show_dataframe({"Portfolio Positions": portfolio_with_stops})

# ============================================================
# 🎯 TACTICAL OPERATIONS PANEL
# ============================================================
process_and_render_tactical(buy_ticker, buy_shares, sell_ticker, sell_shares)

# ============================================================
# 📘 PORTFOLIO & ZACKS SUMMARY
# ============================================================
render_event_log(portfolio_df, portfolio_filename, scored_candidates, available_cash)

# ============================================================
# 🔥 ANALYTICS CLUSTERS (NEUTRAL ZONE)
# ============================================================
render_analytics_clusters(portfolio_df, scored_candidates)

# ============================================================
# 🕒 ARCHIVE OVERVIEW HISTORY
# ============================================================
history_df = load_archive_portfolio_history()
if history_df is not None and not history_df.empty:
    st.markdown("## 🕒 Historical Portfolio Value (Archive Engine)")
    st.dataframe(history_df, use_container_width=True)
else:
    st.caption("No archive files detected for history tracking.")

# ============================================================
# END OF FILE — Unified Modular Build
# ============================================================
render_footer()
