# ============================================================
# 🧭 Fox Valley Intelligence Engine — UI Bridge Module
# v7.3R-5.5 | Unified UI Rendering & Intelligence Brief
# ============================================================

import streamlit as st
import pandas as pd

# ------------------------------------------------------------
# METRIC CARDS (Top Overview)
# ------------------------------------------------------------
def render_metric_cards(total_value, available_cash, avg_gain):
    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 💰 Estimated Total Value")
        st.markdown(f"## ${total_value:,.2f}")
        st.markmarkdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 💵 Cash Available to Trade")
        st.markdown(f"## ${available_cash:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    with colC:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Avg Gain/Loss %")
        if avg_gain is not None:
            st.markdown(f"## {avg_gain:.2f}%")
        else:
            st.markdown("## —")
        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# DIAGNOSTICS CONSOLE
# ------------------------------------------------------------
def render_diagnostics(manual_cash, portfolio_filename, zacks_files):
    st.markdown("## ⚙️ Diagnostics Console")

    if manual_cash > 0:
        st.info("Manual cash override active — using sidebar override value.")
    else:
        st.info("Using cash reported from portfolio file.")

    if portfolio_filename:
        st.caption(f"Active Portfolio File: **{portfolio_filename}**")

    if not zacks_files:
        st.warning("No Zacks screen files detected in /data for the latest date.")
    else:
        st.success("Zacks screens loaded successfully.")


# ------------------------------------------------------------
# TACTICAL OPERATIONS PANEL (basic UI hook)
# ------------------------------------------------------------
def render_tactical_panel(buy_ticker, buy_shares, sell_ticker, sell_shares):
    st.markdown("## 🎯 Tactical Operations Panel")
    st.write(f"**Buy Order** — Ticker: {buy_ticker or '—'}, Shares: {buy_shares}")
    st.write(f"**Sell Order** — Ticker: {sell_ticker or '—'}, Shares: {sell_shares}")
    st.caption("Order execution module placeholder — integration pending.")


# ------------------------------------------------------------
# GENERIC DATA DISPLAY ENGINE
# Accepts:
#   • A single DataFrame
#   • A dict of { label: DataFrame }
#   • A dict of { label: (DataFrame, filename) }
# ------------------------------------------------------------
def show_dataframe(data):
    # Single DataFrame
    if isinstance(data, pd.DataFrame):
        st.dataframe(data, use_container_width=True)
        return

    # Dictionary-based
    if isinstance(data, dict):
        for label, value in data.items():
            df = None
            filename = None

            # Case: (DataFrame, filename)
            if isinstance(value, tuple) and len(value) == 2:
                df, filename = value
            # Case: plain DataFrame
            elif isinstance(value, pd.DataFrame):
                df = value
            else:
                continue  # unsupported format, skip

            if df is None:
                continue

            if filename:
                st.markdown(f"### 📄 {label} — `{filename}`")
            else:
                st.markdown(f"### 📄 {label}")

            st.dataframe(df, use_container_width=True)
        return

    st.warning("⚠ Unsupported data format for display.")


# ------------------------------------------------------------
# EVENT LOG / SUMMARY PANEL
# ------------------------------------------------------------
def render_event_log(portfolio_df, portfolio_filename, scored_candidates, available_cash):
    st.markdown("## 📘 Portfolio Summary")
    if portfolio_df is not None:
        st.write(f"Positions Loaded: {len(portfolio_df)}")
        st.write(f"Portfolio File: `{portfolio_filename}`")
    else:
        st.warning("No portfolio file detected.")

    st.markdown("## 📒 Zacks Screening Summary")
    if scored_candidates is not None and not scored_candidates.empty:
        st.write(f"Candidates Ranked: {len(scored_candidates)}")
    else:
        st.warning("No valid Zacks candidates found.")

    if available_cash < 0:
        st.error("Cash value is negative — check portfolio file formatting.")


# ------------------------------------------------------------
# 🧠 ZACKS INTELLIGENCE BRIEF
# High-level summary above the Top-N table
# ------------------------------------------------------------
def render_zacks_intel_brief(scored_candidates):
    st.markdown("## 🧠 Zacks Intelligence Brief")

    if scored_candidates is None or scored_candidates.empty:
        st.warning("No Zacks candidates loaded — intelligence brief unavailable.")
        return

    cols = scored_candidates.columns

    total_candidates = len(scored_candidates)
    unique_tickers = scored_candidates["Ticker"].nunique() if "Ticker" in cols else total_candidates

    # Best-ranked candidate (top of CompositeScore-sorted frame)
    best_ticker = "—"
    best_score = None
    best_source = "—"

    try:
        top_row = scored_candidates.iloc[0]
        if "Ticker" in cols:
            best_ticker = str(top_row.get("Ticker", "—"))
        if "CompositeScore" in cols:
            best_score = float(top_row.get("CompositeScore", 0.0))
        if "Source" in cols:
            best_source = str(top_row.get("Source", "—"))
    except Exception:
        pass

    # Source distribution
    source_counts = None
    if "Source" in cols:
        source_counts = scored_candidates["Source"].value_counts()

    # Display
    st.write(f"**Total Candidates Ranked:** {total_candidates}")
    st.write(f"**Unique Tickers:** {unique_tickers}")

    if best_score is not None:
        st.write(f"**Top Candidate:** `{best_ticker}` "
                 f"(CompositeScore: {best_score:,.2f} | Source: {best_source})")
    else:
        st.write(f"**Top Candidate:** `{best_ticker}` (score unavailable)")

    if source_counts is not None and not source_counts.empty:
        st.markdown("**Source Distribution:**")
        st.dataframe(source_counts.rename("Count").to_frame(), use_container_width=True)


# ------------------------------------------------------------
# FOOTER — Styling & System Signature
# ------------------------------------------------------------
def render_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; color:gray;">
            🧭 Fox Valley Intelligence Engine — Command Deck v7.3R-5.5<br>
            Modular Engine Architecture | Real-Time Tactical & Intelligence Systems Active
        </div>
        """,
        unsafe_allow_html=True
    )
