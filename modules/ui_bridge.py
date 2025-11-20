# ============================================================
# 🧭 Fox Valley Intelligence Engine — UI Bridge Module
# v7.3R-5.3 | Integration Layer for Streamlit Command Deck UI
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------
# SAFE DATAFRAME DISPLAY
# ------------------------------------------------------------
def show_dataframe(df, title=None, highlight_func=None):
    """
    Safely displays a styled dataframe with optional highlight logic.
    """
    if df is None or df.empty:
        st.warning("No data available for display.")
        return

    if title:
        st.markdown(f"### {title}")

    if highlight_func:
        st.dataframe(df.style.apply(highlight_func, axis=1))
    else:
        st.dataframe(df)


# ------------------------------------------------------------
# METRIC CARD RENDERER
# ------------------------------------------------------------
def render_metric_cards(total_value, available_cash, avg_gain):
    """
    Renders the 3 primary metric cards on the Command Deck.
    """
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### **Estimated Total Value**")
        st.markdown(f"## ${total_value:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### **Cash Available to Trade**")
        st.markdown(f"## ${available_cash:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### **Avg Gain/Loss %**")
        if avg_gain is not None:
            st.markdown(f"## {avg_gain:.2f}%")
        else:
            st.markdown("## —")
        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# DIAGNOSTIC LOG DISPLAY
# ------------------------------------------------------------
def render_diagnostics(portfolio_file, zacks_file, manual_cash_active):
    st.markdown("## ⚙️ Diagnostics Console")

    if manual_cash_active:
        st.info("Manual cash override active — using sidebar override value.")
    else:
        st.info("Using cash reported from portfolio file.")

    if portfolio_file:
        st.caption(f"**Active Portfolio File:** {portfolio_file}")
    else:
        st.warning("Portfolio file not found.")

    if zacks_file:
        st.caption(f"**Zacks screens loaded from:** {zacks_file}")
    else:
        st.warning("No Zacks file detected.")

# ------------------------------------------------------------
# TACTICAL CONTROL DISPLAY
# ------------------------------------------------------------
def render_tactical_panel(buy_ticker, buy_shares, sell_ticker, sell_shares):
    st.markdown("## 🎯 Tactical Operations Panel")

    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown("### Buy Order")
        st.write(f"**Ticker:** {buy_ticker or '—'}")
        st.write(f"**Shares:** {buy_shares or 0}")

    with colB:
        st.markdown("### Sell Order")
        st.write(f"**Ticker:** {sell_ticker or '—'}")
        st.write(f"**Shares:** {sell_shares or 0}")

    with colC:
        st.markdown("### Order Status")
        st.info("Order execution module placeholder — integration pending.")


# ------------------------------------------------------------
# EVENT LOGGING (Shared from engines)
# ------------------------------------------------------------
def render_event_log(event_log):
    if not event_log:
        return

    st.markdown("## 📋 Event Log")
    for event in event_log:
        st.markdown(
            f"""
            <div style="background:#f7f7f7;padding:10px;border-radius:8px;
                 border:1px solid #ddd;margin-top:5px;">
                <b>{event['timestamp']}</b> — <b>{event['type']}</b><br>
                {event['details']}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# FOOTER SIGNATURE
# ------------------------------------------------------------
def render_footer(version_text="v7.3R-5.3 — All Systems Online"):
    st.markdown("---")
    st.markdown(
        f"""
        <div style="text-align:center; color:gray; padding-top:10px;">
            🧭 Fox Valley Intelligence Engine — Command Deck<br>
            {version_text}<br>
            Real-Time + Synthetic Gain Engine Active | Historical & Tactical Systems Online
        </div>
        """,
        unsafe_allow_html=True,
    )

