# ============================================================
# 🧭 Fox Valley Intelligence Engine — Tactical Engine Module
# v7.3R-5.4 | Tactical UI Rendering + Order Logging
# ============================================================

import streamlit as st
from modules.diagnostics_engine import log_event


# ============================================================
# 1️⃣ CORE TACTICAL PROCESSING
# ============================================================
def process_and_render_tactical(buy_ticker, buy_shares, sell_ticker, sell_shares):
    """
    Handles tactical UI input and logs executed placeholder orders.
    """
    st.markdown("## 🎯 Tactical Operations Panel")

    col1, col2, col3 = st.columns(3)

    # Buy Order Summary
    with col1:
        st.markdown("### 🟢 Buy Order")
        st.write(f"**Ticker:** {buy_ticker or '—'}")
        st.write(f"**Shares:** {buy_shares or 0}")

    # Sell Order Summary
    with col2:
        st.markdown("### 🔴 Sell Order")
        st.write(f"**Ticker:** {sell_ticker or '—'}")
        st.write(f"**Shares:** {sell_shares or 0}")

    # Order Status
    with col3:
        st.markdown("### 📡 Order Status")
        if (buy_ticker and buy_shares > 0) or (sell_ticker and sell_shares > 0):
            st.info("Order module placeholder — brokerage integration pending.")
        else:
            st.caption("No orders placed.")

    # Event Logging
    if buy_ticker and buy_shares > 0:
        log_event("Buy Order Entered", f"Ticker: {buy_ticker}, Shares: {buy_shares}")

    if sell_ticker and sell_shares > 0:
        log_event("Sell Order Entered", f"Ticker: {sell_ticker}, Shares: {sell_shares}")


# ============================================================
# 2️⃣ TACTICAL PANEL RENDER (LEGACY SAFE MODE)
# ============================================================
def render_tactical_panel():
    """
    Deprecated caller for legacy compatibility.
    """
    st.caption("🔧 Tactical Panel is now handled by process_and_render_tactical().")
