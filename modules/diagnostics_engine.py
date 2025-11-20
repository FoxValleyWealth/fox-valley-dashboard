# ============================================================
# 🛠 Fox Valley Intelligence Engine — Diagnostics Engine Module
# v7.3R-5.4 | Event Logging, Status Messaging, Runtime Reporting
# ============================================================

import streamlit as st
from datetime import datetime

# Internal event store
_event_log = []


# ------------------------------------------------------------
# Log Event — Called programmatically (tactical, analytics, etc.)
# ------------------------------------------------------------
def log_event(event_type, details="", severity="INFO"):
    """
    Records events such as Buy/Sell attempts, screen load status, system notes.
    :param event_type: Short label like 'BUY', 'SELL', 'SYSTEM', 'ZACKS'
    :param details: Human-readable details to display in logs
    :param severity: INFO, WARNING, ERROR
    """
    event_entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Type": event_type.upper(),
        "Details": details,
        "Severity": severity.upper(),
    }
    _event_log.append(event_entry)


# ------------------------------------------------------------
# Render Diagnostics Panel (UI) — Called from Fox Valley Dashboard
# ------------------------------------------------------------
def render_diagnostics(manual_cash, portfolio_filename, zacks_files):
    st.markdown("## ⚙️ Diagnostics Console")

    # Cash source check
    if manual_cash > 0:
        st.info("Manual cash override active — using sidebar override value.")
    else:
        st.info("Using cash reported from portfolio file.")

    # Portfolio source
    if portfolio_filename:
        st.caption(f"Active Portfolio File: **{portfolio_filename}**")
    else:
        st.warning("No portfolio file detected.")

    # Zacks status check
    if not zacks_files:
        st.warning("⚠ No Zacks screen files found in /data directory.")
    else:
        any_file = list(zacks_files.values())[0][1]
        st.caption(f"Zacks screens loaded from: **{any_file}**")


# ------------------------------------------------------------
# Render Event Log (UI) — Bottom section display
# ------------------------------------------------------------
def render_event_log(portfolio_df, portfolio_filename, scored_candidates, available_cash):
    st.markdown("## 📘 Portfolio & Zacks Summary")

    # Portfolio summary
    if portfolio_filename:
        st.write(f"**Portfolio File:** `{portfolio_filename}`")
        st.write(f"**Positions Loaded:** {len(portfolio_df)} ")
    else:
        st.warning("No portfolio file detected.")

    # Zacks summary
    if scored_candidates is not None and not scored_candidates.empty:
        st.write(f"**Zacks Candidates Available:** {len(scored_candidates)}")
    else:
        st.warning("No Zacks candidates loaded.")

    # Cash validation
    if available_cash < 0:
        st.error("Cash value is negative — check portfolio file formatting.")

    # Event history display
    st.markdown("### 📋 System Event Log")
    if _event_log:
        st.dataframe(_event_log, use_container_width=True)
    else:
        st.caption("📝 No system events recorded yet.")


# ------------------------------------------------------------
# Utility — Clear Event Log
# ------------------------------------------------------------
def clear_event_log():
    global _event_log
    _event_log = []

