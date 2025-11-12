# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck (v7.3R-4 | Final Stable Build – Nov 12, 2025)
# Streamlit app — single-file deployment (no hot-fixes). Designed for /data CSV inputs.
# Author: #1 for CaptPicard

import os
import io
import math
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fox Valley Intelligence Engine — Command Deck v7.3R-4",
    page_icon="🧭",
    layout="wide",
)

# Dark Command Deck accents (note: global Streamlit dark theme is preferred via .streamlit/config.toml)
# Keep CSS minimal to avoid conflicts.
st.markdown(
    """
    <style>
      .metric-small .stMetric {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 12px;
      }
      .data-ok {color:#22c55e;font-weight:600}
      .data-warn {color:#f59e0b;font-weight:600}
      .data-err {color:#ef4444;font-weight:700}
      .section-card {background: rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);padding: 12px 16px;border-radius: 16px}
      .subtle {opacity:.85}
      div.block-container{padding-top:1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS (Default file paths — auto-load at launch)
# ──────────────────────────────────────────────────────────────────────────────
DATA_DIR = "data"  # NOTE: Streamlit Cloud mounts repo root; use relative path
PORTFOLIO_FILE = os.path.join(DATA_DIR, "Portfolio_Positions_Nov-12-2025.csv")
ZACKS_G1_FILE = os.path.join(DATA_DIR, "zacks_custom_screen_2025-11-12 Growth 1.csv")
ZACKS_G2_FILE = os.path.join(DATA_DIR, "zacks_custom_screen_2025-11-12 Growth 2.csv")
ZACKS_DD_FILE = os.path.join(DATA_DIR, "zacks_custom_screen_2025-11-12 Defensive Dividends.csv")

EXPECTED_PORT_COLS = {
    "Ticker", "Shares", "Current Price", "Current Value", "Cost Basis",
    "Sector", "Name", "Type", "Zacks Rank", "Day Change %", "Gain/Loss %",
}

# ──────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(path: str) -> Tuple[pd.DataFrame, List[str]]:
    """Robust CSV loader with numeric coercion and column cleanup.
    Returns df, messages[] (warnings/info).
    """
    msgs = []
    if not os.path.exists(path):
        return pd.DataFrame(), [f"Missing file: {path}"]
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        return pd.DataFrame(), [f"Failed to read {path}: {e}"]

    # Strip columns and normalize common headers
    df.columns = [str(c).strip() for c in df.columns]

    # Coerce numerics for common fields
    for col in [
        "Shares", "Current Price", "Current Value", "Cost Basis",
        "Day Change %", "Gain/Loss %", "Zacks Rank",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Some exports use different naming; add best-effort harmonization
    if "Price" in df.columns and "Current Price" not in df.columns:
        df["Current Price"] = pd.to_numeric(df["Price"], errors="coerce")
    if "Value" in df.columns and "Current Value" not in df.columns:
        df["Current Value"] = pd.to_numeric(df["Value"], errors="coerce")

    # Compute Current Value if missing
    if "Current Value" not in df.columns and {"Shares", "Current Price"}.issubset(df.columns):
        df["Current Value"] = df["Shares"] * df["Current Price"]
        msgs.append("Computed 'Current Value' = Shares × Current Price")

    return df, msgs


def human_money(x: float) -> str:
    if pd.isna(x):
        return "—"
    return f"${x:,.2f}"


def infer_cash(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    cash = 0.0
    # Heuristics: rows that represent cash or money market
    cash_aliases = {"CASH", "SPAXX", "FDRXX", "Money Market", "Cash"}
    ticker_col = "Ticker" if "Ticker" in df.columns else None
    type_col = "Type" if "Type" in df.columns else None

    if ticker_col:
        cash_rows = df[df[ticker_col].astype(str).str.upper().isin(cash_aliases)]
        if "Current Value" in df.columns:
            cash += cash_rows.get("Current Value", pd.Series(dtype=float)).sum()
    if type_col:
        mm_rows = df[df[type_col].astype(str).str.contains("cash|money", case=False, na=False)]
        if "Current Value" in df.columns:
            cash += mm_rows.get("Current Value", pd.Series(dtype=float)).sum()

    # Deduplicate if overlaps (simple min to avoid double count)
    return float(cash)


def zacks_merge(g1: pd.DataFrame, g2: pd.DataFrame, dd: pd.DataFrame) -> pd.DataFrame:
    def prep(df: pd.DataFrame, source: str) -> pd.DataFrame:
        if df.empty:
            return df
        out = df.copy()
        out.columns = [str(c).strip() for c in out.columns]
        # Standardize common headers
        rename_map = {
            "Symbol": "Ticker",
            "Company": "Name",
            "Rank": "Zacks Rank",
            "ZacksRank": "Zacks Rank",
        }
        out = out.rename(columns={k:v for k,v in rename_map.items() if k in out.columns})
        if "Zacks Rank" in out.columns:
            out["Zacks Rank"] = pd.to_numeric(out["Zacks Rank"], errors="coerce")
        out["Source"] = source
        return out

    g1p = prep(g1, "Growth 1")
    g2p = prep(g2, "Growth 2")
    ddp = prep(dd, "Defensive Dividends")

    frames = [df for df in [g1p, g2p, ddp] if not df.empty]
    if not frames:
        return pd.DataFrame()
    # Keep a tidy union of vital columns
    keep = [
        "Ticker", "Name", "Sector", "Industry", "Zacks Rank", "PE", "PEG",
        "Dividend Yield", "Price", "Price Target", "Source"
    ]
    union_cols = sorted({c for f in frames for c in f.columns} | set(keep))
    merged = pd.concat([f.reindex(columns=union_cols) for f in frames], ignore_index=True)
    # Deduplicate by Ticker+Source to preserve which screen suggested it
    merged = merged.drop_duplicates(subset=[c for c in ["Ticker", "Source"] if c in merged.columns])
    return merged


def mk_metric(label: str, value: str, help_text: str = ""):
    col = st.container()
    with col:
        st.metric(label, value, help=help_text)


# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Controls & File Status
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.title("🧭 Command Deck — v7.3R-4")
st.sidebar.caption("Final Stable Build — November 12, 2025")

st.sidebar.subheader("Data Sources")
st.sidebar.write("Using auto-load defaults. Upload to override during a session.")

with st.sidebar.expander("Portfolio CSV", expanded=True):
    st.code(PORTFOLIO_FILE, language="text")
    uploaded_port = st.file_uploader("Override portfolio CSV", type=["csv"], key="port")

with st.sidebar.expander("Zacks CSVs", expanded=True):
    st.code(ZACKS_G1_FILE, language="text")
    up_g1 = st.file_uploader("Override Growth 1 CSV", type=["csv"], key="g1")
    st.code(ZACKS_G2_FILE, language="text")
    up_g2 = st.file_uploader("Override Growth 2 CSV", type=["csv"], key="g2")
    st.code(ZACKS_DD_FILE, language="text")
    up_dd = st.file_uploader("Override Defensive Dividends CSV", type=["csv"], key="dd")

st.sidebar.subheader("Trailing Stop Defaults")
def_trail = st.sidebar.slider("Default trailing stop %", 1, 50, 12, help="Used when per‑stock setting is absent")

# ──────────────────────────────────────────────────────────────────────────────
# LOAD DATA (Auto + optional overrides)
# ──────────────────────────────────────────────────────────────────────────────
# Portfolio
if uploaded_port is not None:
    try:
        portfolio_df = pd.read_csv(uploaded_port)
        port_msgs = ["Loaded from upload override."]
    except Exception as e:
        portfolio_df = pd.DataFrame()
        port_msgs = [f"Failed uploaded portfolio: {e}"]
else:
    portfolio_df, port_msgs = load_csv(PORTFOLIO_FILE)

# Zacks screens
if up_g1 is not None:
    try:
        g1_df = pd.read_csv(up_g1)
        g1_msgs = ["Growth 1 (upload override)"]
    except Exception as e:
        g1_df, g1_msgs = pd.DataFrame(), [f"Failed Growth 1 upload: {e}"]
else:
    g1_df, g1_msgs = load_csv(ZACKS_G1_FILE)

if up_g2 is not None:
    try:
        g2_df = pd.read_csv(up_g2)
        g2_msgs = ["Growth 2 (upload override)"]
    except Exception as e:
        g2_df, g2_msgs = pd.DataFrame(), [f"Failed Growth 2 upload: {e}"]
else:
    g2_df, g2_msgs = load_csv(ZACKS_G2_FILE)

if up_dd is not None:
    try:
        dd_df = pd.read_csv(up_dd)
        dd_msgs = ["Defensive Dividends (upload override)"]
    except Exception as e:
        dd_df, dd_msgs = pd.DataFrame(), [f"Failed Defensive Dividends upload: {e}"]
else:
    dd_df, dd_msgs = load_csv(ZACKS_DD_FILE)

# ──────────────────────────────────────────────────────────────────────────────
# HEADER — Build banner + data validations
# ──────────────────────────────────────────────────────────────────────────────
st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck")
st.caption("v7.3R-4 | Final Stable Build — November 12, 2025 | Diagnostics + Top‑8 Analyzer Active")

# Portfolio status
port_stat = f"Loaded {len(portfolio_df):,} rows and {len(portfolio_df.columns):,} columns" if not portfolio_df.empty else "No rows"
value_col_used = "Current Value" if "Current Value" in portfolio_df.columns else ("Value" if "Value" in portfolio_df.columns else "(none)")

status_cols = st.columns(4)
with status_cols[0]:
    st.markdown("**📁 Active Portfolio File:** ")
    st.code(PORTFOLIO_FILE, language="text")
    st.markdown(f"<span class='subtle'>Loaded status:</span> {port_stat}", unsafe_allow_html=True)
with status_cols[1]:
    st.markdown("**📁 Active Zacks Growth 1 File:**")
    st.code(ZACKS_G1_FILE, language="text")
    st.markdown(f"<span class='subtle'>Rows:</span> {len(g1_df):,}", unsafe_allow_html=True)
with status_cols[2]:
    st.markdown("**📁 Active Zacks Growth 2 File:**")
    st.code(ZACKS_G2_FILE, language="text")
    st.markdown(f"<span class='subtle'>Rows:</span> {len(g2_df):,}", unsafe_allow_html=True)
with status_cols[3]:
    st.markdown("**📁 Active Zacks Defensive Dividends File:**")
    st.code(ZACKS_DD_FILE, language="text")
    st.markdown(f"<span class='subtle'>Rows:</span> {len(dd_df):,}", unsafe_allow_html=True)

if port_msgs:
    for m in port_msgs:
        st.info(m)
for m in g1_msgs + g2_msgs + dd_msgs:
    st.info(m)

# ──────────────────────────────────────────────────────────────────────────────
# PORTFOLIO OVERVIEW
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.subheader("📊 Portfolio Overview")

est_total = float(pd.to_numeric(portfolio_df.get("Current Value", pd.Series(dtype=float)), errors='coerce').sum()) if not portfolio_df.empty else 0.0
est_cash = infer_cash(portfolio_df)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Estimated Total Value", human_money(est_total))
with m2:
    st.metric("Estimated Cash Value", human_money(est_cash))
with m3:
    day_gain = float(pd.to_numeric(portfolio_df.get("Day Gain", pd.Series(dtype=float)), errors='coerce').sum()) if "Day Gain" in portfolio_df.columns else float('nan')
    st.metric("Day Gain (sum)", human_money(day_gain) if not math.isnan(day_gain) else "—")
with m4:
    gl_pct = pd.to_numeric(portfolio_df.get("Gain/Loss %", pd.Series(dtype=float)), errors='coerce')
    st.metric("Avg Gain/Loss %", f"{gl_pct.mean():.2f}%" if not gl_pct.empty else "—")

if not portfolio_df.empty:
    with st.expander("Show portfolio table"):
        st.dataframe(portfolio_df, use_container_width=True)
else:
    st.warning("Portfolio file not loaded or contains no rows.")

# ──────────────────────────────────────────────────────────────────────────────
# ZACKS — Unified Analyzer + Top‑8
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.subheader("🔎 Zacks Screens — Unified Analyzer")

zacks_all = zacks_merge(g1_df, g2_df, dd_df)

if zacks_all.empty:
    st.warning("No Zacks data available. Check the three CSV inputs.")
else:
    # TOP‑8 selection logic: rank by Zacks Rank (asc) then by PEG (asc) when present, else PE (asc)
    sort_cols = []
    if "Zacks Rank" in zacks_all.columns:
        sort_cols.append(("Zacks Rank", True))
    if "PEG" in zacks_all.columns:
        sort_cols.append(("PEG", True))
    elif "PE" in zacks_all.columns:
        sort_cols.append(("PE", True))

    if sort_cols:
        by = [c for c, _ in sort_cols]
        asc = [a for _, a in sort_cols]
        zacks_sorted = zacks_all.sort_values(by=by, ascending=asc, na_position='last')
    else:
        zacks_sorted = zacks_all.copy()

    top_n = st.slider("Top‑N candidates", 4, 20, 8)
    top8 = zacks_sorted.head(top_n)

    st.dataframe(top8, use_container_width=True)

    # Click‑to‑copy tickers
    tickers = ", ".join(sorted(set(str(t) for t in top8.get("Ticker", []))))
    st.code(tickers or "", language="text")

# ──────────────────────────────────────────────────────────────────────────────
# TACTICAL — Buy / Sell / Hold / Trim Controls (UI only)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.subheader("🎯 Tactical Controls — Buy / Sell / Hold / Trim")

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    buy_ticker = st.text_input("Buy — Ticker", placeholder="e.g., NVDA")
    buy_shares = st.number_input("Shares", min_value=0, value=0, step=1)
    st.button("Queue BUY", use_container_width=True)
with col_b:
    sell_ticker = st.text_input("Sell — Ticker", placeholder="e.g., NVDA")
    sell_shares = st.number_input("Shares ", min_value=0, value=0, step=1, key="sell")
    st.button("Queue SELL", use_container_width=True)
with col_c:
    hold_note = st.text_area("Hold — Note", placeholder="Reason / timeframe")
    st.button("Log HOLD", use_container_width=True)
with col_d:
    trim_ticker = st.text_input("Trim — Ticker", placeholder="e.g., NVDA")
    trim_pct = st.slider("Trim %", 1, 50, 10)
    st.button("Queue TRIM", use_container_width=True)

st.caption("These controls log intentions/UI only. No brokerage connectivity is performed.")

# ──────────────────────────────────────────────────────────────────────────────
# TRAILING STOP MONITOR
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.subheader("🛡️ Trailing Stop Monitor")

trail_df = pd.DataFrame()
if not portfolio_df.empty and {"Ticker", "Current Price"}.issubset(portfolio_df.columns):
    trail_df = portfolio_df[[c for c in ["Ticker", "Name", "Current Price", "Current Value"] if c in portfolio_df.columns]].copy()
    # If a per‑stock trailing % column exists, respect it; else use default
    if "Trailing %" in portfolio_df.columns:
        trail_df["Trailing %"] = pd.to_numeric(portfolio_df["Trailing %"], errors="coerce").fillna(def_trail)
    else:
        trail_df["Trailing %"] = def_trail
    trail_df["Stop Price"] = (1 - trail_df["Trailing %"]/100.0) * pd.to_numeric(trail_df["Current Price"], errors="coerce")
    st.dataframe(trail_df, use_container_width=True)

    # Export helper
    csv_buf = io.StringIO()
    trail_df.to_csv(csv_buf, index=False)
    st.download_button("Download Trailing Stops CSV", data=csv_buf.getvalue(), file_name="trailing_stops_v73R4.csv", mime="text/csv")
else:
    st.info("Add 'Ticker' and 'Current Price' to portfolio CSV to activate trailing stops.")

# ──────────────────────────────────────────────────────────────────────────────
# PERFORMANCE SUMMARY (basic)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.subheader("📈 Performance Summary (Basic)")

perf_cols = [c for c in ["Ticker", "Name", "Shares", "Cost Basis", "Current Price", "Current Value", "Gain/Loss %", "Day Change %"] if c in portfolio_df.columns]
if perf_cols:
    perf_df = portfolio_df[perf_cols].copy()
    # compute Gain $ if possible
    if {"Shares", "Cost Basis", "Current Price"}.issubset(perf_df.columns):
        perf_df["Gain $"] = (perf_df["Current Price"] - perf_df["Cost Basis"]) * perf_df["Shares"]
    st.dataframe(perf_df, use_container_width=True)
else:
    st.info("Provide Cost Basis / Shares / Current Price to enable performance computations.")

# ──────────────────────────────────────────────────────────────────────────────
# FOOTER / DIAGNOSTICS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("\n---\n")
st.caption(
    "✅ Build: v7.3R‑4 Final Stable | Files auto‑loaded from /data | Override via sidebar uploaders during a session."
)
