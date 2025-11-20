# ============================================================
# 🧭 Fox Valley Intelligence Engine — UI Bridge Engine
# v7.3R-5.4 | Modular UI Rendering Gateway
# ============================================================

import streamlit as st


# ============================================================
# 1️⃣ METRIC CARDS (Top-Level Summary)
# ============================================================
def render_metric_cards(total_value, available_cash, avg_gain):
    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown("### 💰 Estimated Total Value")
        st.markdown(f"## ${total_value:,.2f}")

    with colB:
        st.markdown("### 💵 Cash Available to Trade")
        st.markdown(f"## ${available_cash:,.2f}")

    with colC:
        st.markdown("### 📊 Avg Gain/Loss %")
        st.markdown(f"## {avg_gain:.2f}%" if avg_gain is not None else "## —")


# ============================================================
# 2️⃣ DIAGNOSTICS HEADER
# ============================================================
def render_diagnostics(manual_cash, portfolio_filename, zacks_files):
    st.markdown("## ⚙️ Diagnostics Console")

    if manual_cash > 0:
        st.info("Manual cash override active — using sidebar override value.")
    else:
        st.info("Using cash reported from portfolio file.")

    if portfolio_filename:
        st.caption(f"Active Portfolio File: **{portfolio_filename}**")

    if not zacks_files:
        st.warning("No Zacks screen files detected for latest date.")
    else:
        st.caption("Zacks screens loaded successfully.")


# ============================================================
# 3️⃣ TACTICAL PANEL (Cargo Handled in Tactical Engine)
# ============================================================
def render_tactical_panel():
    st.caption("Tactical Engine handles direct tactical rendering.")


# ============================================================
# 4️⃣ ORDER LOG / SUMMARY PANEL
# ============================================================
def render_event_log(portfolio_df, portfolio_filename, scored_candidates, available_cash):
    st.markdown("## 📘 Portfolio & Zacks Summary")

    if portfolio_df is not None and not portfolio_df.empty:
        st.write(f"**Positions Loaded:** {len(portfolio_df)}")
        st.write(f"**Portfolio File:** `{portfolio_filename}`")
    else:
        st.warning("No portfolio file detected.")

    if available_cash < 0:
        st.error("Cash value is negative — check portfolio formatting.")

    if scored_candidates is None or scored_candidates.empty:
        st.warning("No Zacks candidates loaded — analyzer cannot compute rankings.")
    else:
        st.info("Zacks candidates successfully scored and ranked.")


# ============================================================
# 5️⃣ GENERIC DATAFRAME DISPLAY
# ============================================================
def show_dataframe(zacks_or_portfolio_dict):
    """
    Display portfolio or Zacks screens in expandable sections via dictionary input.
    Example input format:
    {
        "Portfolio Positions": <df>,
        "Growth1 Screen": <df>,
    }
    """
    if not isinstance(zacks_or_portfolio_dict, dict):
        st.warning("Invalid data source for display.")
        return

    for label, df in zacks_or_portfolio_dict.items():
        with st.expander(f"📄 {label}"):
            st.dataframe(df)


# ============================================================
# 6️⃣ FOOTER MODULE
# ============================================================
def render_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; color:gray; padding-top:10px;">
            🧭 Fox Valley Intelligence Engine — Command Deck (Modular Build v7.3R-5.4)<br>
            Real-Time + Tactical + Synthetic Engines Unified<br>
        </div>
        """,
        unsafe_allow_html=True
    )
