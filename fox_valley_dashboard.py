# 🧭 FOX VALLEY INTELLIGENCE ENGINE — COMMAND DECK
# v7.3R-5.1 — Stable Unified Build (Avg Gain/Loss Engine Upgrade)

import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

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
ARCHIVE_DIR = "archive"
PORTFOLIO_FILE_PATTERN = "Portfolio_Positions"
ZACKS_PREFIX = "zacks_custom_screen"
VALID_SCREEN_TYPES = ["Growth1", "Growth2", "DefensiveDividend"]

# ------------------------------------------------
# GLOBAL STYLES
# ------------------------------------------------
CUSTOM_CSS = """
<style>
html, body, [class*="css"]  {
    font-family: 'Segoe UI', sans-serif;
}
h1, h2, h3 {
    font-weight: 700;
}
.highlight-rank-1 {
    background-color: #ffeb3b33 !important;
}
.dashboard-card {
    padding: 18px;
    background-color: #f8f9fa;
    border-radius: 14px;
    border: 1px solid #ddd;
    margin-bottom: 12px;
}
.sidebar-section {
    padding: 14px;
    margin-bottom: 16px;
    background: #f0f2f6;
    border-radius: 10px;
}
.dataframe tbody tr:hover {
    background-color: #e6f7ff !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ====================================================
# CORE FILE LOADERS
# ====================================================
def load_latest_file(pattern, directory=DATA_DIR):
    """
    Return (DataFrame, filename) of the newest CSV in `directory`
    whose filename contains `pattern`. If none found, (None, None).
    """
    try:
        if not os.path.isdir(directory):
            return None, None

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
        st.error(f"[ERROR] Could not load dataset for pattern '{pattern}' in '{directory}': {e}")
        return None, None


def load_portfolio():
    """
    Load the most recent Portfolio_Positions_*.csv from /data.
    """
    df, filename = load_latest_file(PORTFOLIO_FILE_PATTERN, directory=DATA_DIR)
    if df is None:
        st.warning("No portfolio file found in /data")
        return None, None
    return df, filename


def load_zacks_files_auto(directory=DATA_DIR):
    """
    Scan /data for:
        zacks_custom_screen_YYYY-MM-DD Growth 1.csv
        zacks_custom_screen_YYYY-MM-DD Growth 2.csv
        zacks_custom_screen_YYYY-MM-DD Defensive Dividends.csv

    Return dict:
        {
            "Growth1": (df, filename),
            "Growth2": (df, filename),
            "DefensiveDividend": (df, filename)
        }
    for the latest available date among those files.
    """
    import re

    if not os.path.isdir(directory):
        return {}

    files = [
        f for f in os.listdir(directory)
        if f.startswith(ZACKS_PREFIX)
        and f.endswith(".csv")
        and "archive" not in f.lower()
    ]

    if not files:
        return {}

    date_pattern = r"zacks_custom_screen_(\d{4}-\d{2}-\d{2})"
    date_map = {}

    for f in files:
        m = re.search(date_pattern, f)
        if not m:
            continue
        d = m.group(1)
        date_map.setdefault(d, []).append(f)

    if not date_map:
        return {}

    newest = sorted(date_map.keys())[-1]
    todays_files = date_map[newest]

    out = {}
    for f in todays_files:
        lower = f.lower()
        full = os.path.join(directory, f)

        if "growth 1" in lower:
            key = "Growth1"
        elif "growth 2" in lower:
            key = "Growth2"
        elif "defensive" in lower or "dividends" in lower:
            key = "DefensiveDividend"
        else:
            # If it doesn't clearly match, skip
            continue

        try:
            df = pd.read_csv(full)
            out[key] = (df, f)
        except Exception as e:
            st.error(f"[ERROR] Could not read Zacks file '{f}': {e}")

    return out

# ====================================================
# ZACKS PREP & SCORING
# ====================================================
def prepare_screen(df, label):
    if df is None:
        return None
    out = df.copy()
    out.columns = [c.strip() for c in out.columns]
    out["Source"] = label
    return out


def merge_zacks_screens(auto_dict):
    """
    Merge all auto-detected Zacks screens into a unified DataFrame.
    """
    prepared = []
    for label in VALID_SCREEN_TYPES:
        item = auto_dict.get(label)
        if not item:
            continue
        df, _fn = item
        p = prepare_screen(df, label)
        if p is not None:
            prepared.append(p)

    if not prepared:
        return pd.DataFrame()

    return pd.concat(prepared, ignore_index=True)


def score_zacks_candidates(df):
    """
    Compute CompositeScore across Growth1, Growth2, DefensiveDividend.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    scored = df.copy()

    # Zacks Rank → lower is better
    if "Zacks Rank" in scored.columns:
        scored["RankScore"] = (
            scored["Zacks Rank"].astype(str).str.extract(r"(\d)").astype(float)
        )
    else:
        scored["RankScore"] = 5.0

    # Momentum proxy
    if "Price Change %" in scored.columns:
        scored["Momentum"] = pd.to_numeric(
            scored["Price Change %"], errors="coerce"
        ).fillna(0.0)
    else:
        scored["Momentum"] = 0.0

    # Market cap proxy
    if "Market Cap" in scored.columns:
        scored["SizeScore"] = pd.to_numeric(
            scored["Market Cap"], errors="coerce"
        ).fillna(0.0)
    else:
        scored["SizeScore"] = 0.0

    def source_weight(src):
        if src == "Growth1":
            return 1.15
        if src == "Growth2":
            return 1.10
        if src == "DefensiveDividend":
            return 1.05
        return 1.0

    scored["SourceWeight"] = scored["Source"].apply(source_weight)

    scored["CompositeScore"] = (
        (6 - scored["RankScore"]) * 5
        + scored["Momentum"] * 0.2
        + scored["SizeScore"] * 0.00001
    ) * scored["SourceWeight"]

    # Sort best → worst
    scored = scored.sort_values("CompositeScore", ascending=False)
    return scored


def get_top_n(df, n):
    if df is None or df.empty:
        return pd.DataFrame()
    return df.head(n)

# ====================================================
# PORTFOLIO METRICS (LIVE + FIDELITY-SAFE)
# ====================================================
def compute_portfolio_metrics(df):
    """
    Compute:
    - Total account value
    - Cash value
    - Value-weighted Avg Gain/Loss %

    This upgraded version is compatible with multiple Fidelity-style
    gain/loss column names and is architected for downstream use by:
    - Tactical Trend Analyzer
    - Risk Posture / Intelligence Brief
    """
    if df is None or df.empty:
        return 0.0, 0.0, None

    try:
        # --- Total Portfolio Value ---
        current_value_series = pd.to_numeric(
            df.get("Current Value", pd.Series(dtype=float)), errors="coerce"
        ).fillna(0)
        total_value = current_value_series.sum()

        # --- Detect & Compute Gain/Loss % Safely ---
        gain_loss_candidates = [
            "Gain/Loss %",
            "Total Gain/Loss Percent",
            "Today's Gain/Loss Percent",
            "GainLossPct",
            "% Gain/Loss",
            "%Chg",
        ]

        detected_gain_column = None
        for col in gain_loss_candidates:
            if col in df.columns:
                detected_gain_column = col
                break

        avg_gain = None
        if detected_gain_column and total_value > 0:
            numeric_gain = pd.to_numeric(
                df[detected_gain_column], errors="coerce"
            ).fillna(0)

            # Value-weighted contribution
            weighted_contribution = numeric_gain * current_value_series
            total_weighted = weighted_contribution.sum()

            if total_value > 0:
                avg_gain = total_weighted / total_value
            else:
                avg_gain = None

        # --- Cash Value Detection (Ticker == 'cash') ---
        cash_value = 0.0
        if "Ticker" in df.columns:
            cash_rows = df[df["Ticker"].astype(str).str.lower().eq("cash")]
            if not cash_rows.empty:
                cash_value = pd.to_numeric(
                    cash_rows["Current Value"], errors="coerce"
                ).fillna(0).sum()

        return float(total_value), float(cash_value), avg_gain

    except Exception:
        return 0.0, 0.0, None

# ====================================================
# STYLE HELPERS
# ====================================================
def highlight_rank_1(row):
    try:
        if "Zacks Rank" in row and str(row["Zacks Rank"]).strip() == "1":
            return ['background-color: #ffeb3b33'] * len(row)
    except Exception:
        pass
    return [''] * len(row)


def attach_trailing_stops(df, default_pct):
    if df is None or df.empty:
        return df
    out = df.copy()
    out["Trailing Stop %"] = default_pct
    return out


def log_event(event_type, details):
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
        unsafe_allow_html=True,
    )

# ====================================================
# HISTORICAL ENGINE — /archive AWARE
# ====================================================
def load_archive_portfolio_history():
    """
    Scan /archive for archive_Portfolio_Positions_*.csv
    and build a small history table of Date vs Total Value.
    """
    history_rows = []

    if not os.path.isdir(ARCHIVE_DIR):
        return pd.DataFrame()

    for f in os.listdir(ARCHIVE_DIR):
        if not f.startswith("archive_Portfolio_Positions_"):
            continue
        if not f.endswith(".csv"):
            continue

        # Example: archive_Portfolio_Positions_Nov-10-2025.csv
        try:
            date_part = f.replace("archive_Portfolio_Positions_", "").replace(".csv", "")
            # Parse month-abbrev date like Nov-10-2025
            dt = datetime.strptime(date_part, "%b-%d-%2025".replace("2025", "%Y"))  # defensive
        except Exception:
            # If parsing fails, keep as plain string
            dt = None

        full_path = os.path.join(ARCHIVE_DIR, f)
        try:
            df = pd.read_csv(full_path)

            # Clean like live portfolio
            df_clean = (
                df.replace(r"\((.*?)\)", r"-\1", regex=True)
                  .replace(r"[\$,]", "", regex=True)
            )
            df_clean = df_clean.apply(lambda col: pd.to_numeric(col, errors="ignore"))
            if "Symbol" in df_clean.columns:
                df_clean = df_clean.rename(columns={"Symbol": "Ticker"})

            total_value, _, _ = compute_portfolio_metrics(df_clean)

            history_rows.append({
                "Label": date_part,
                "Date": dt if dt is not None else date_part,
                "Total Value": total_value
            })
        except Exception as e:
            st.warning(f"[ARCHIVE] Could not process portfolio file '{f}': {e}")

    if not history_rows:
        return pd.DataFrame()

    hist_df = pd.DataFrame(history_rows)

    # Sort by date if possible
    if "Date" in hist_df.columns and hist_df["Date"].dtype != object:
        hist_df = hist_df.sort_values("Date")
    return hist_df


def load_archive_zacks_counts():
    """
    Scan /archive for archive_zacks_custom_screen_YYYY-MM-DD <Type>.csv
    and summarize ticker counts per date and screen type.
    """
    rows = []

    if not os.path.isdir(ARCHIVE_DIR):
        return pd.DataFrame()

    for f in os.listdir(ARCHIVE_DIR):
        if not f.startswith("archive_zacks_custom_screen_"):
            continue
        if not f.endswith(".csv"):
            continue

        # Example: archive_zacks_custom_screen_2025-11-10 Growth 1.csv
        # or archive_zacks_custom_screen_2025-11-10 Defensive Dividends.csv
        base = f.replace("archive_zacks_custom_screen_", "").replace(".csv", "")
        parts = base.split(" ")
        if not parts:
            continue

        date_str = parts[0]  # 2025-11-10
        type_str = " ".join(parts[1:]).strip()

        # Map type_str to canonical source label
        lower_type = type_str.lower()
        if "growth" in lower_type and "1" in lower_type:
            source = "Growth1"
        elif "growth" in lower_type and "2" in lower_type:
            source = "Growth2"
        elif "defensive" in lower_type or "dividends" in lower_type:
            source = "DefensiveDividend"
        else:
            # Unknown type naming; skip
            continue

        full_path = os.path.join(ARCHIVE_DIR, f)
        try:
            df = pd.read_csv(full_path)
            count = len(df)
            rows.append({
                "DateStr": date_str,
                "Screen": source,
                "Tickers": count
            })
        except Exception as e:
            st.warning(f"[ARCHIVE] Could not process Zacks file '{f}': {e}")

    if not rows:
        return pd.DataFrame()

    hist = pd.DataFrame(rows)

    # Sort by date string if it parses
    try:
        hist["Date"] = pd.to_datetime(hist["DateStr"], errors="coerce")
        hist = hist.sort_values(["Date", "Screen"])
    except Exception:
        pass

    return hist

# ====================================================
# SIDEBAR — CONTROL PANEL
# ====================================================
with st.sidebar:
    st.markdown("## 🧭 Command Deck Controls")

    st.markdown("#### Manual Cash Override ($)")
    manual_cash = st.number_input(
        "Enter Cash Available to Trade",
        min_value=0.0,
        value=0.0,
        step=100.0,
        key="manual_cash_override",
    )

    st.markdown("---")

    st.markdown("#### Default Trailing Stop %")
    default_trailing_stop = st.number_input(
        "Trailing Stop (%)",
        min_value=0.0,
        max_value=50.0,
        value=1.0,
        step=0.5,
        key="default_trailing_stop",
    )

    st.markdown("---")

    st.markdown("#### Zacks Unified Analyzer")
    top_n = st.number_input(
        "Top-N Candidates",
        min_value=1,
        max_value=50,
        value=8,
        step=1,
        key="top_n_candidates",
    )

    st.markdown("---")

    st.markdown("#### 🎯 Tactical Controls")
    buy_ticker = st.text_input("Buy Ticker")
    buy_shares = st.number_input("Buy Shares", min_value=0, step=1)

    sell_ticker = st.text_input("Sell Ticker")
    sell_shares = st.number_input("Sell Shares", min_value=0, step=1)

# ====================================================
# LIVE DATA LOAD — PORTFOLIO + ZACKS (/data)
# ====================================================
portfolio_df, portfolio_filename = load_portfolio()

# Clean Fidelity export numerics + normalize symbol column
if portfolio_df is not None:
    portfolio_df = (
        portfolio_df
        .replace(r"\((.*?)\)", r"-\1", regex=True)
        .replace(r"[\$,]", "", regex=True)
    )
    portfolio_df = portfolio_df.apply(lambda col: pd.to_numeric(col, errors="ignore"))

    if "Symbol" in portfolio_df.columns:
        portfolio_df = portfolio_df.rename(columns={"Symbol": "Ticker"})

# Zacks auto-ingestion from /data
zacks_files = load_zacks_files_auto(DATA_DIR)
zacks_unified = merge_zacks_screens(zacks_files)
scored_candidates = score_zacks_candidates(zacks_unified)
top_n_df = get_top_n(scored_candidates, top_n)

# ====================================================
# CORE METRICS (LIVE)
# ====================================================
total_value, cash_value, avg_gain = compute_portfolio_metrics(portfolio_df)
available_cash = manual_cash if manual_cash > 0 else cash_value

# ====================================================
# PAGE HEADER
# ====================================================
st.markdown(
    """
# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck  
**v7.3R-5.1** | Real-Time + Historical Diagnostics Online  
"""
)

# ====================================================
# OVERVIEW METRIC CARDS
# ====================================================
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
    if avg_gain is not None:
        st.markdown(f"## {avg_gain:.2f}%")
    else:
        st.markdown("## —")
    st.markdown("</div>", unsafe_allow_html=True)

# ====================================================
# DIAGNOSTICS PANEL
# ====================================================
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
    # Show the date that file names are based on, by example
    any_file = list(zacks_files.values())[0][1]
    st.caption(f"Zacks screens loaded from: **{any_file}**")

# ====================================================
# ZACKS UNIFIED ANALYZER — TOP N
# ====================================================
st.markdown("## 🔎 Zacks Unified Analyzer — Top Candidates")
st.caption("Ranked across Growth1, Growth2, Defensive Dividend using composite scoring.")

if not top_n_df.empty:
    st.dataframe(top_n_df.style.apply(highlight_rank_1, axis=1))
else:
    st.warning("No Zacks candidates available for Top-N view.")

# ====================================================
# ZACKS RAW SCREEN TABLES
# ====================================================
st.markdown("## 📂 Zacks Tactical Screens (Raw Data)")

for sctype in VALID_SCREEN_TYPES:
    item = zacks_files.get(sctype)
    if item:
        df_z, fn_z = item
        with st.expander(f"📄 {sctype} — {fn_z}"):
            st.dataframe(df_z.style.apply(highlight_rank_1, axis=1))
    else:
        with st.expander(f"📄 {sctype} — No file detected"):
            st.write("No data for this screen.")

# ====================================================
# PORTFOLIO TABLE (WITH TRAILING STOPS)
# ====================================================
portfolio_with_stops = attach_trailing_stops(portfolio_df, default_trailing_stop)

st.markdown("## 📊 Portfolio Positions (with Trailing Stops)")
if portfolio_with_stops is not None and not portfolio_with_stops.empty:
    st.dataframe(portfolio_with_stops)
else:
    st.warning("No portfolio positions to display.")

# ====================================================
# TACTICAL OPERATIONS PANEL
# ====================================================
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

# Log events if user has entered orders
if buy_ticker and buy_shares > 0:
    log_event("Buy Order Entered", f"Ticker: {buy_ticker}, Shares: {buy_shares}")

if sell_ticker and sell_shares > 0:
    log_event("Sell Order Entered", f"Ticker: {sell_ticker}, Shares: {sell_shares}")

# ====================================================
# SUMMARY PANELS
# ====================================================
st.markdown("## 📘 Portfolio Summary")
if portfolio_df is not None and not portfolio_df.empty:
    st.write(f"**Positions Loaded:** {len(portfolio_df)}")
    st.write(f"**Portfolio File:** `{portfolio_filename}`")
else:
    st.warning("No portfolio file detected.")

st.markdown("## 📒 Zacks Screening Summary")
for sctype in VALID_SCREEN_TYPES:
    item = zacks_files.get(sctype)
    if item:
        df_s, fn_s = item
        st.write(f"**{sctype}:** {len(df_s)} tickers ({fn_s})")
    else:
        st.write(f"**{sctype}:** No file detected")

if available_cash < 0:
    st.error("Cash value is negative — check portfolio file formatting.")

if scored_candidates is None or scored_candidates.empty:
    st.warning("No Zacks candidates loaded — analyzer cannot compute rankings.")

# ====================================================
# ANALYTICS CLUSTER — HEAT MAP SUITE (LIVE)
# ====================================================
st.markdown("## 🔥 Analytics Cluster — Heat Map Suite")

# 1️⃣ Portfolio Weight Heat Map
if portfolio_df is not None and not portfolio_df.empty:
    weight_df = portfolio_df.copy()
    if "Current Value" in weight_df.columns:
        total_cv = pd.to_numeric(weight_df["Current Value"], errors="coerce").fillna(0).sum()
        if total_cv > 0:
            weight_df["Weight %"] = (
                pd.to_numeric(weight_df["Current Value"], errors="coerce").fillna(0)
                / total_cv
            ) * 100

            fig_weight = px.imshow(
                [weight_df["Weight %"]],
                labels=dict(color="Weight %"),
                x=weight_df.get("Ticker", pd.Series(range(len(weight_df)))),
                y=["Weight"],
                color_continuous_scale="Blues",
            )
            fig_weight.update_layout(height=300)

            with st.expander("📘 Portfolio Weight Heat Map"):
                st.plotly_chart(fig_weight, use_container_width=True)
        else:
            st.warning("Current Value column totals to 0 — cannot compute weights.")
    else:
        st.warning("Portfolio file missing 'Current Value' column — cannot build weight heat map.")

# 2️⃣ Gain / Loss % Heat Map
if portfolio_df is not None and not portfolio_df.empty:
    gain_col = None
    for cand in ["Gain/Loss %", "Total Gain/Loss Percent", "Today's Gain/Loss Percent"]:
        if cand in portfolio_df.columns:
            gain_col = cand
            break

    if gain_col:
        gain_series = pd.to_numeric(
            portfolio_df[gain_col], errors="coerce"
        ).fillna(0)
        fig_gain = px.imshow(
            [gain_series],
            labels=dict(color=gain_col),
            x=portfolio_df.get("Ticker", pd.Series(range(len(gain_series)))),
            y=[gain_col],
            color_continuous_scale="RdYlGn",
        )
        fig_gain.update_layout(height=300)

        with st.expander("📈 Gain/Loss % Heat Map"):
            st.plotly_chart(fig_gain, use_container_width=True)
    else:
        st.warning(
            "Portfolio file missing any recognized gain column — cannot build gain/loss map."
        )

# 3️⃣ Zacks Composite Score Heat Map
if scored_candidates is not None and not scored_candidates.empty:
    if "CompositeScore" in scored_candidates.columns:
        comp_df = scored_candidates[["Ticker", "CompositeScore"]].reset_index(drop=True)
        fig_comp = px.imshow(
            [comp_df["CompositeScore"]],
            labels=dict(color="Composite Score"),
            x=comp_df["Ticker"],
            y=["Composite Score"],
            color_continuous_scale="Viridis",
        )
        fig_comp.update_layout(height=300)

        with st.expander("💡 Zacks Composite Score Heat Map"):
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.warning("Missing CompositeScore column — cannot generate Zacks heat map.")

# 4️⃣ Correlation Matrix (numeric columns)
if portfolio_df is not None and not portfolio_df.empty:
    numeric_cols = portfolio_df.select_dtypes(include=["float", "int"]).columns
    if len(numeric_cols) > 1:
        corr = portfolio_df[numeric_cols].corr()
        with st.expander("🧩 Correlation Matrix Heat Map"):
            fig, ax = plt.subplots(figsize=(11, 9))
            sns.heatmap(
                corr,
                cmap="coolwarm",
                annot=True,
                fmt=".2f",
                linewidths=0.5,
                ax=ax,
            )
            st.pyplot(fig)
    else:
        st.warning("Not enough numeric data to compute correlation matrix.")

# ====================================================
# 📚 HISTORICAL OVERVIEW (FROM /archive)
# ====================================================
st.markdown("## 🕒 Historical Overview — Archive Engine")

# Portfolio history from /archive
try:
    hist_port = load_archive_portfolio_history()
    if hist_port is not None and not hist_port.empty:
        with st.expander("📘 Historical Portfolio Value (archive_Portfolio_Positions_*)"):
            display_df = hist_port.copy()
            # Prefer label for readability
            st.dataframe(display_df[["Label", "Total Value"]])

            # Line chart if real datetime is available
            if pd.api.types.is_datetime64_any_dtype(display_df["Date"]):
                fig_hist = px.line(
                    display_df.sort_values("Date"),
                    x="Date",
                    y="Total Value",
                    markers=True,
                    title="Historical Total Portfolio Value"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.caption("No archive portfolio files detected for historical value analysis.")
except Exception as e:
    st.warning(f"[HISTORICAL] Portfolio history engine encountered an issue: {e}")

# Zacks historical counts from /archive
try:
    hist_zacks = load_archive_zacks_counts()
    if hist_zacks is not None and not hist_zacks.empty:
        with st.expander("📒 Historical Zacks Screen Size (archive_zacks_custom_screen_*)"):
            st.dataframe(hist_zacks[["DateStr", "Screen", "Tickers"]])

            # Small pivot heat map: Date vs Screen → Ticker counts
            try:
                pivot = hist_zacks.pivot_table(
                    index="DateStr", columns="Screen", values="Tickers", fill_value=0
                )
                fig_z = px.imshow(
                    pivot.values,
                    labels=dict(color="Tickers"),
                    x=list(pivot.columns),
                    y=list(pivot.index),
                    color_continuous_scale="Blues"
                )
                fig_z.update_layout(
                    height=350,
                    xaxis_title="Screen",
                    yaxis_title="Date"
                )
                st.plotly_chart(fig_z, use_container_width=True)
            except Exception:
                # If pivot fails for any reason, just show the raw table above
                pass
    else:
        st.caption("No archive Zacks files detected for historical comparison.")
except Exception as e:
    st.warning(f"[HISTORICAL] Zacks history engine encountered an issue: {e}")

# ====================================================
# END OF FILE — v7.3R-5.1
# ====================================================
