# ================================================
# 🧭 FOX VALLEY INTELLIGENCE ENGINE — COMMAND DECK
# v7.3R-4.x  |  Segment 1A Source Transmission
# ================================================

import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

# ------------------------------------------------
# STREAMLIT CONFIGURATION
# ------------------------------------------------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine – Command Deck",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------
# GLOBAL CONSTANTS
# ------------------------------------------------
DATA_DIR = "data"
PORTFOLIO_FILE_PATTERN = "Portfolio_Positions"
ZACKS_PREFIX = "zacks_custom_screen"
VALID_SCREEN_TYPES = ["Growth1", "Growth2", "DefensiveDividend"]

# ------------------------------------------------
# GLOBAL STYLES
# ------------------------------------------------
CUSTOM_CSS = """
<style>
/* Universal font */
html, body, [class*="css"]  {
    font-family: 'Segoe UI', sans-serif;
}

/* Headline styling */
h1, h2, h3 {
    font-weight: 700;
}

/* Highlight Zacks #1 rank rows */
.highlight-rank-1 {
    background-color: #ffeb3b33 !important;
}

/* Card-like containers */
.dashboard-card {
    padding: 18px;
    background-color: #f8f9fa;
    border-radius: 14px;
    border: 1px solid #ddd;
    margin-bottom: 12px;
}

/* Sidebar styling */
.sidebar-section {
    padding: 14px;
    margin-bottom: 16px;
    background: #f0f2f6;
    border-radius: 10px;
}

/* Table styling */
.dataframe tbody tr:hover {
    background-color: #e6f7ff !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------------------------------------------
# UTILITY — LOAD LATEST FILE MATCHING PATTERN
# ------------------------------------------------
def load_latest_file(pattern, directory=DATA_DIR):
    """
    Returns the most recent file in the data/ directory
    matching the supplied pattern.
    """
    try:
        files = [
            f for f in os.listdir(directory)
            if pattern in f and f.endswith(".csv")
        ]
        if not files:
            return None, None

        files_sorted = sorted(
            files,
            key=lambda x: os.path.getmtime(os.path.join(directory, x)),
            reverse=True
        )
        latest = files_sorted[0]
        full_path = os.path.join(directory, latest)

        df = pd.read_csv(full_path)
        return df, latest

    except Exception as e:
        st.error(f"[ERROR] Could not load dataset for pattern {pattern}: {e}")
        return None, None

# ------------------------------------------------
# LOAD PORTFOLIO POSITIONS
# ------------------------------------------------
def load_portfolio():
    """
    Loads the most recent portfolio CSV in the form:
    Portfolio_Positions_XXXX.csv
    """
    df, filename = load_latest_file(PORTFOLIO_FILE_PATTERN)
    if df is None:
        st.warning("No portfolio file found in /data")
        return None, None
    return df, filename

# ------------------------------------------------
# LOAD ZACKS SCREENS (G1, G2, DEF)
# ------------------------------------------------
def load_zacks_screen(screen_type):
    """
    screen_type: Growth1, Growth2, DefensiveDividend
    Returns the newest Zacks screen file of that type.
    """
    pattern = f"{ZACKS_PREFIX}_"
    df, filename = load_latest_file(pattern)

    if df is None:
        return None, None

    # Filter by type if multiple exist in filename
    if screen_type.lower() not in filename.lower():
        # If multiple files exist, pick filtered manually
        candidates = [
            f for f in os.listdir(DATA_DIR)
            if screen_type.lower() in f.lower()
            and f.endswith(".csv")
        ]
        if candidates:
            latest = sorted(
                candidates,
                key=lambda x: os.path.getmtime(os.path.join(DATA_DIR, x)),
                reverse=True
            )[0]
            df = pd.read_csv(os.path.join(DATA_DIR, latest))
            filename = latest

    return df, filename

# ------------------------------------------------
# CALCULATE PORTFOLIO METRICS
# ------------------------------------------------
def compute_portfolio_metrics(df):
    """
    Computes account value, cash, average gain, etc.
    Assumes columns:
    - 'Current Value'
    - 'Gain/Loss $'
    - 'Gain/Loss %'
    - 'Ticker'
    """
    if df is None or df.empty:
        return 0, 0, 0

    try:
        total_value = df["Current Value"].sum()
        avg_gain = df["Gain/Loss %"].mean()

        cash_row = df[df["Ticker"].str.lower() == "cash"]
        cash_value = cash_row["Current Value"].sum() if not cash_row.empty else 0

        return total_value, cash_value, avg_gain
    except:
        return 0, 0, 0

# ------------------------------------------------
# HIGHLIGHT ZACKS RANK = 1
# ------------------------------------------------
def highlight_rank_1(row):
    try:
        if "Zacks Rank" in row and str(row["Zacks Rank"]).strip() == "1":
            return ['background-color: #ffeb3b33'] * len(row)
    except:
        pass
    return [''] * len(row)
# ================================================
# SEGMENT 1B — COMMAND DECK CORE INTERFACE LAYER
# v7.3R-4.x
# ================================================

# ------------------------------------------------
# SIDEBAR — CONTROL PANEL
# ------------------------------------------------
with st.sidebar:
    st.markdown("## 🧭 Command Deck Controls")

    # Manual cash override
    st.markdown("#### Manual Cash Override ($)")
    manual_cash = st.number_input(
        "Enter Cash Available to Trade",
        min_value=0.0, value=0.0, step=100.0,
        key="manual_cash_override"
    )

    st.markdown("---")

    # Default trailing stop % for entire deck
    st.markdown("#### Default Trailing Stop %")
    default_trailing_stop = st.number_input(
        "Trailing Stop (%)",
        min_value=0.0, max_value=50.0,
        value=1.0, step=0.5,
        key="default_trailing_stop"
    )

    st.markdown("---")

    # Top-N Zacks analyzer
    st.markdown("#### Zacks Unified Analyzer")
    top_n = st.number_input(
        "Top-N Candidates",
        min_value=1, max_value=50,
        value=8, step=1,
        key="top_n_candidates"
    )

    st.markdown("---")

    # Tactical Buy/Sell/Trim interface
    st.markdown("#### 🎯 Tactical Controls")
    buy_ticker = st.text_input("Buy Ticker")
    buy_shares = st.number_input("Buy Shares", min_value=0, step=1)

    sell_ticker = st.text_input("Sell Ticker")
    sell_shares = st.number_input("Sell Shares", min_value=0, step=1)

# ------------------------------------------------
# UNIFIED ZACKS INGESTION LAYER
# ------------------------------------------------
def load_all_zacks_screens():
    """
    Returns dict with keys Growth1, Growth2, DefensiveDividend
    Each entry: (DataFrame, filename)
    """
    screens = {}
    for sctype in VALID_SCREEN_TYPES:
        df, fn = load_zacks_screen(sctype)
        screens[sctype] = {"df": df, "file": fn}
    return screens

all_screens = load_all_zacks_screens()

# ------------------------------------------------
# ZACKS — CLEAN AND MERGE
# ------------------------------------------------
def prepare_screen(df, label):
    """Normalizes columns and tags with source."""
    if df is None:
        return None
    out = df.copy()
    out.columns = [c.strip() for c in out.columns]
    out["Source"] = label
    return out

def merge_all_screens():
    """Combined Zacks (G1 + G2 + DEF) into one unified DataFrame."""
    prepared = []
    for sc in VALID_SCREEN_TYPES:
        entry = all_screens[sc]
        if entry["df"] is not None:
            prepared.append(prepare_screen(entry["df"], sc))
    if not prepared:
        return pd.DataFrame()
    return pd.concat(prepared, ignore_index=True)

zacks_unified = merge_all_screens()

# ------------------------------------------------
# SCORING ENGINE — BASELINE
# ------------------------------------------------
def score_zacks_candidates(df):
    """
    Scoring foundation for Zacks Top-N engine.
    Uses:
    - Zacks Rank
    - Price Momentum (if provided)
    - Market Cap
    - Source weighting (G1, G2, DEF)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    scored = df.copy()

    # Convert rank
    if "Zacks Rank" in scored.columns:
        scored["RankScore"] = scored["Zacks Rank"].astype(str).str.extract("(\d)").astype(float)
    else:
        scored["RankScore"] = 5.0

    # Price momentum surrogate
    if "Price Change %" in scored.columns:
        scored["Momentum"] = scored["Price Change %"].astype(float)
    else:
        scored["Momentum"] = 0

    # Market Cap handling
    if "Market Cap" in scored.columns:
        scored["SizeScore"] = scored["Market Cap"].astype(float)
    else:
        scored["SizeScore"] = 0

    # Source weighting
    def source_weight(src):
        if src == "Growth1": return 1.15
        if src == "Growth2": return 1.10
        if src == "DefensiveDividend": return 1.05
        return 1.0

    scored["SourceWeight"] = scored["Source"].apply(source_weight)

    # Composite scoring formula
    scored["CompositeScore"] = (
        (6 - scored["RankScore"]) * 5 +
        scored["Momentum"] * 0.2 +
        scored["SizeScore"] * 0.00001
    ) * scored["SourceWeight"]

    return scored.sort_values("CompositeScore", ascending=False)

scored_candidates = score_zacks_candidates(zacks_unified)

# ------------------------------------------------
# TOP-N EXTRACTOR
# ------------------------------------------------
def get_top_n(df, n):
    if df is None or df.empty:
        return pd.DataFrame()
    return df.head(n)

top_n_df = get_top_n(scored_candidates, top_n)

# ------------------------------------------------
# TABLE UTILITY
# ------------------------------------------------
def render_table(df, label=None, highlight=False):
    if df is None or df.empty:
        st.warning(f"No data found for {label}")
        return

    if highlight:
        st.dataframe(df.style.apply(highlight_rank_1, axis=1))
    else:
        st.dataframe(df)
# ================================================
# SEGMENT 1C — MAIN COMMAND DECK LAYOUT
# v7.3R-4.x
# ================================================

# ------------------------------------------------
# LOAD PORTFOLIO
# ------------------------------------------------
portfolio_df, portfolio_filename = load_portfolio()

# Calculate core metrics
total_value, cash_value, avg_gain = compute_portfolio_metrics(portfolio_df)

# Override cash if user uses manual override
available_cash = manual_cash if manual_cash > 0 else cash_value

# ------------------------------------------------
# PAGE TITLE
# ------------------------------------------------
st.markdown(f"""
# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck  
**v7.3R-4.x** | Real-Time Diagnostics Online  
""")

# ------------------------------------------------
# PORTFOLIO OVERVIEW CARDS
# ------------------------------------------------
colA, colB, colC = st.columns(3)

with colA:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### **Estimated Total Value**")
    st.markdown(f"## ${total_value:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

with colB:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### **Cash Available to Trade**")
    st.markdown(f"## ${available_cash:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

with colC:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### **Avg Gain/Loss %**")
    if avg_gain:
        st.markdown(f"## {avg_gain:.2f}%")
    else:
        st.markdown("## —")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------
# DIAGNOSTICS
# ------------------------------------------------
st.markdown("## ⚙️ Diagnostics Console")

if manual_cash > 0:
    st.info("Manual cash override active — using sidebar override value.")
else:
    st.info("Using cash reported from portfolio file.")

if portfolio_filename:
    st.caption(f"Active Portfolio File: **{portfolio_filename}**")

# ------------------------------------------------
# ZACKS UNIFIED ANALYZER
# ------------------------------------------------
st.markdown("## 🔎 Zacks Unified Analyzer — Top Candidates")
st.caption("Ranked across Growth1, Growth2, Defensive Dividend using composite scoring.")

render_table(top_n_df, label="Top-N Candidates", highlight=True)

# ------------------------------------------------
# INDIVIDUAL ZACKS SCREENS
# ------------------------------------------------
st.markdown("## 📂 Zacks Tactical Screens (Raw Data)")

for sctype in VALID_SCREEN_TYPES:
    entry = all_screens[sctype]
    df = entry["df"]
    filename = entry["file"]

    with st.expander(f"📄 {sctype} — {filename}"):
        render_table(df, label=sctype, highlight=True)

# ------------------------------------------------
# TRAILING STOP MODULE
# ------------------------------------------------
def attach_trailing_stops(df, default_pct):
    """
    Adds trailing stop % column for all rows.
    """
    if df is None or df.empty:
        return df

    out = df.copy()
    out["Trailing Stop %"] = default_pct
    return out

portfolio_with_stops = attach_trailing_stops(portfolio_df, default_trailing_stop)

# ------------------------------------------------
# PORTFOLIO TABLE
# ------------------------------------------------
st.markdown("## 📊 Portfolio Positions (with Trailing Stops)")
render_table(portfolio_with_stops, label="Portfolio")

# ------------------------------------------------
# TACTICAL BUY/SELL/HOLD PANEL
# ------------------------------------------------
st.markdown("## 🎯 Tactical Operations Panel")

colB1, colB2, colB3 = st.columns(3)

with colB1:
    st.markdown("### Buy Order")
    st.write(f"**Ticker:** {buy_ticker or '—'}")
    st.write(f"**Shares:** {buy_shares or 0}")

with colB2:
    st.markdown("### Sell Order")
    st.write(f"**Ticker:** {sell_ticker or '—'}")
    st.write(f"**Shares:** {sell_shares or 0}")

with colB3:
    st.markdown("### Order Status")
    st.info("Order execution module placeholder — integration pending.")
# ================================================
# SEGMENT 1D — LOGGING, UTILITIES, AND FUTURE HOOKS
# v7.3R-4.x
# ================================================

# ------------------------------------------------
# COMMAND DECK — EVENT LOGGING
# ------------------------------------------------
def log_event(event_type, details):
    """
    Simple in-app event logger to show notable actions.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.markdown(
        f"""
        <div style="
            background:#f7f7f7;
            padding:10px;
            border-radius:10px;
            border:1px solid #ddd;
            margin-top:8px;
        ">
            <b>{timestamp}</b> — <b>{event_type}</b><br>{details}
        </div>
        """,
        unsafe_allow_html=True
    )

# Example log triggers
if buy_ticker and buy_shares > 0:
    log_event("Buy Order Entered", f"Ticker: {buy_ticker}, Shares: {buy_shares}")

if sell_ticker and sell_shares > 0:
    log_event("Sell Order Entered", f"Ticker: {sell_ticker}, Shares: {sell_shares}")

# ------------------------------------------------
# PORTFOLIO SUMMARY PANEL
# ------------------------------------------------
st.markdown("## 📘 Portfolio Summary")

if portfolio_df is not None and not portfolio_df.empty:
    st.write(f"**Positions Loaded:** {len(portfolio_df)}")
    st.write(f"**Portfolio File:** `{portfolio_filename}`")
else:
    st.warning("No portfolio file detected.")

# ------------------------------------------------
# ZACKS SUMMARY PANEL
# ------------------------------------------------
st.markdown("## 📒 Zacks Screening Summary")

for sctype in VALID_SCREEN_TYPES:
    entry = all_screens[sctype]
    df = entry["df"]
    filename = entry["file"]
    if df is not None:
        st.write(f"**{sctype}:** {len(df)} tickers ({filename})")
    else:
        st.write(f"**{sctype}:** No file detected")

# ------------------------------------------------
# DIAGNOSTIC WARNINGS
# ------------------------------------------------
if available_cash < 0:
    st.error("Cash value is negative — check portfolio file formatting.")

if scored_candidates is None or scored_candidates.empty:
    st.warning("No Zacks screening candidates were loaded — analyzer cannot compute Top-N rankings.")

# ------------------------------------------------
# FUTURE AUTOMATION HOOKS
# ------------------------------------------------
"""
Reserved expansion section for:

- Auto-execution workflow  
- Fidelity API trading bridge  
- Weekly cycle automation  
- Daily Top-8 analyzer  
- Server-side caching engine  
- Historical signal comparison  
- Watchlist synchronization  

These hooks allow v7.3R to expand to v7.4R+ without rewriting the core.
"""
# ================================================
# SEGMENT 1E — ANALYTICS CLUSTER (HEAT MAPS)
# v7.3R-4.4
# ================================================

import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.markdown("## 🔥 Analytics Cluster — Heat Map Suite")

# ------------------------------------------------
# 1️⃣ PORTFOLIO WEIGHT HEAT MAP (Plotly)
# ------------------------------------------------
if portfolio_df is not None and not portfolio_df.empty:
    weight_df = portfolio_df.copy()
    if "Current Value" in weight_df.columns:
        weight_df["Weight %"] = weight_df["Current Value"] / weight_df["Current Value"].sum() * 100

        fig_weight = px.imshow(
            [weight_df["Weight %"]],
            labels=dict(color="Weight %"),
            x=weight_df["Ticker"],
            y=["Weight"],
            color_continuous_scale="Blues"
        )
        fig_weight.update_layout(height=300)

        with st.expander("📘 Portfolio Weight Heat Map"):
            st.plotly_chart(fig_weight, use_container_width=True)
    else:
        st.warning("Portfolio file missing 'Current Value' column — cannot build weight map.")

# ------------------------------------------------
# 2️⃣ GAIN / LOSS % HEAT MAP (Plotly)
# ------------------------------------------------
if portfolio_df is not None and not portfolio_df.empty:
    if "Gain/Loss %" in portfolio_df.columns:
        fig_gain = px.imshow(
            [portfolio_df["Gain/Loss %"]],
            labels=dict(color="Gain/Loss %"),
            x=portfolio_df["Ticker"],
            y=["Gain/Loss %"],
            color_continuous_scale="RdYlGn"
        )
        fig_gain.update_layout(height=300)

        with st.expander("📈 Gain/Loss % Heat Map"):
            st.plotly_chart(fig_gain, use_container_width=True)
    else:
        st.warning("Portfolio file missing 'Gain/Loss %' column — cannot build gain/loss map.")

# ------------------------------------------------
# 3️⃣ ZACKS COMPOSITE SCORE HEAT MAP (Plotly)
# ------------------------------------------------
if not scored_candidates.empty:
    if "CompositeScore" in scored_candidates.columns:
        comp_df = scored_candidates[["Ticker", "CompositeScore"]].reset_index(drop=True)

        fig_comp = px.imshow(
            [comp_df["CompositeScore"]],
            labels=dict(color="Composite Score"),
            x=comp_df["Ticker"],
            y=["Composite Score"],
            color_continuous_scale="Viridis"
        )
        fig_comp.update_layout(height=300)

        with st.expander("💡 Zacks Composite Score Heat Map"):
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("CompositeScore column missing — cannot render Zacks heat map.")

# ------------------------------------------------
# 4️⃣ CORRELATION MATRIX HEAT MAP (Seaborn)
# ------------------------------------------------
if portfolio_df is not None and not portfolio_df.empty:

    # build returns matrix if possible
    numeric_cols = portfolio_df.select_dtypes(include=["float", "int"]).columns

    if len(numeric_cols) > 1:
        corr = portfolio_df[numeric_cols].corr()

        with st.expander("🧩 Correlation Matrix Heat Map"):
            fig, ax = plt.subplots(figsize=(10, 7))
            sns.heatmap(
                corr,
                cmap="coolwarm",
                annot=True,
                fmt=".2f",
                linewidths=0.5,
                ax=ax
            )
            st.pyplot(fig)
    else:
        st.warning("Not enough numeric data to compute correlation heat map.")

# ------------------------------------------------
# END OF FILE
# ------------------------------------------------
