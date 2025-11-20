# ============================================================
# 🛡 FOX VALLEY INTELLIGENCE ENGINE — TACTICAL ENGINE MODULE
# v7.3R-6.0 — Tactical Intelligence Engine
# Scoring, Tags, Momentum Flags, Position Actions
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ------------------------------------------------------------
# Tactical Scoring Model
# ------------------------------------------------------------
def compute_tactical_score(row):
    score = 0

    # Base Scoring (Composite Score influence)
    score += min(row.get("CompositeScore", 0), 50)

    # Price Momentum Influence
    score += min(row.get("PriceChange5d", 0), 20)

    # Rank Stability (bonus if rank stays =1)
    if str(row.get("Zacks Rank", "")).strip() == "1":
        score += 15  # Strongest signal

    # Position Risk Adjustment
    volatility = row.get("Volatility30d", 20)
    risk_penalty = min(volatility, 20) * 0.5
    score -= risk_penalty

    return max(0, min(score, 100))


# ------------------------------------------------------------
# Tactical Decision Tagging
# ------------------------------------------------------------
def tactical_tag(score):
    if score >= 85:
        return "🚀 Target Buy"
    elif score >= 70:
        return "📈 Accumulate"
    elif score >= 55:
        return "⚖ Hold"
    elif score >= 40:
        return "✂ Trim"
    else:
        return "⛔ Sell Candidate"


# ------------------------------------------------------------
# Tactical Engine — Apply Scoring & Tagging
# ------------------------------------------------------------
def apply_tactical_analysis(df):
    if df is None or df.empty:
        return df

    df["TacticalScore"] = df.apply(compute_tactical_score, axis=1)
    df["TacticalTag"] = df["TacticalScore"].apply(tactical_tag)
    df["LastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df


# ------------------------------------------------------------
# Tactical Operations Panel — UI Rendering
# ------------------------------------------------------------
def process_and_render_tactical(buy_ticker, buy_shares, sell_ticker, sell_shares):
    st.markdown("## 🎯 Tactical Operations Panel")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🟢 Buy Order")
        st.write(f"**Ticker:** {buy_ticker or '—'}")
        st.write(f"**Shares:** {buy_shares or 0}")

    with col2:
        st.markdown("### 🔴 Sell Order")
        st.write(f"**Ticker:** {sell_ticker or '—'}")
        st.write(f"**Shares:** {sell_shares or 0}")

    with col3:
        st.markdown("### 📡 Order Status")
        if (buy_ticker and buy_shares > 0) or (sell_ticker and sell_shares > 0):
            st.success("Order received — Execution pending integration.")
        else:
            st.info("No orders placed.")
