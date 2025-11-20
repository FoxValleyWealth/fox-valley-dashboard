# ============================================================
# 🛡 FOX VALLEY INTELLIGENCE ENGINE — TACTICAL ENGINE MODULE
# v7.3R-6.1 — Tactical + Persistence Intelligence Engine
# Adds Rank Stability, Trust Factor, and Final Tactical Score
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ------------------------------------------------------------
# Tactical Scoring (Existing Core Risk/Reward Model)
# ------------------------------------------------------------
def compute_tactical_score(row):
    score = 0
    score += min(row.get("CompositeScore", 0), 50)
    score += min(row.get("PriceChange5d", 0), 20)

    if str(row.get("Zacks Rank", "")).strip() == "1":
        score += 15

    volatility = row.get("Volatility30d", 20)
    score -= min(volatility, 20) * 0.5

    return max(0, min(score, 100))


# ------------------------------------------------------------
# 📅 Rank Persistence Engine (NEW in Phase 6.1)
# ------------------------------------------------------------
def compute_persistence(row):
    days = row.get("PersistenceDays", 0)
    try:
        return int(days)
    except:
        return 0


def stability_class(days):
    if days >= 10:
        return "🛡 Durable"
    elif days >= 5:
        return "🌱 Emerging"
    else:
        return "⚠ Unstable"


def trust_factor(days, score):
    if days >= 10:
        return min(score * 1.2, 100)
    elif days >= 5:
        return min(score * 1.1, 100)
    else:
        return score


# ------------------------------------------------------------
# 🔎 Final Tactical Score with Persistence & Trust Multiplier
# ------------------------------------------------------------
def compute_final_tactical_score(row):
    base_score = compute_tactical_score(row)
    days = compute_persistence(row)
    adjusted = trust_factor(days, base_score)
    return round(adjusted, 2)


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
# Apply Tactical + Persistence Intelligence
# ------------------------------------------------------------
def apply_tactical_analysis(df):
    if df is None or df.empty:
        return df

    df["PersistenceDays"] = df.apply(compute_persistence, axis=1)
    df["StabilityClass"] = df["PersistenceDays"].apply(stability_class)

    df["TacticalScore"] = df.apply(compute_tactical_score, axis=1)
    df["FinalTacticalScore"] = df.apply(compute_final_tactical_score, axis=1)
    df["TacticalTag"] = df["FinalTacticalScore"].apply(tactical_tag)

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
