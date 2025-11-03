# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v7.1 – Nov 2025
# Dark Tactical Command • Manual Totals • Clean Portfolio
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import datetime
import re

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.1 – Tactical Command",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- DARK MODE ----------
st.markdown(
    """
    <style>
        body {background-color:#0e1117;color:#FAFAFA;}
        [data-testid="stHeader"] {background-color:#0e1117;}
        [data-testid="stSidebar"] {background-color:#111318;}
        table {color:#FAFAFA;}
        .rank1 {background-color:#004d00 !important;}
        .rank2 {background-color:#665c00 !important;}
        .rank3 {background-color:#663300 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 0) MANUAL OVERRIDES (FROM LIVE ACCOUNT)
# =========================================================
MANUAL_TOTAL_VALUE = 163_663.96   # live account value
MANUAL_CASH_VALUE  = 27_721.60   # cash available to trade

# =========================================================
# 1) LOAD + PATCH PORTFOLIO (REMOVE SOLD, ADD NEW POSITIONS)
# =========================================================

@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    # make sure these are numeric if present
    if "GainLoss%" in df.columns:
        df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

portfolio = load_portfolio()

# remove fully exited tickers
sold_tickers = ["MRMD", "KE", "IPG"]
if "Ticker" in portfolio.columns:
    portfolio["Ticker"] = portfolio["Ticker"].astype(str)
    portfolio = portfolio[~portfolio["Ticker"].isin(sold_tickers)].copy()
else:
    st.error("portfolio_data.csv must contain a 'Ticker' column.")
    st.stop()

def ensure_position(df: pd.DataFrame, ticker: str, shares: float, price: float):
    """If ticker not present, add it with basic fields."""
    if ticker in df["Ticker"].astype(str).values:
        return df

    value = shares * price
    new_row = {}
    cols = df.columns.tolist()

    for col in cols:
        cname = col.lower()
        if col == "Ticker":
            new_row[col] = ticker
        elif cname in ("shares", "quantity"):
            new_row[col] = shares
        elif cname in ("last price", "last_price", "price"):
            new_row[col] = price
        elif col == "Value":
            new_row[col] = value
        elif col in ("GainLoss%", "gainloss%", "gainlosspct"):
            new_row[col] = 0.0
        elif col.lower() == "type":
            new_row[col] = "Equity"
        else:
            new_row[col] = df[col].iloc[0] if len(df) > 0 else None

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

# Add new trades if not already in the CSV
# HSBC: 70 @ 70.41
portfolio = ensure_position(portfolio, "HSBC", 70, 70.41)
# PRK: 34 @ 151.00
portfolio = ensure_position(portfolio, "PRK", 34, 151.00)
# NTB: 110 @ 46.55
portfolio = ensure_position(portfolio, "NTB", 110, 46.55)

# Raw values from CSV (still used for pie chart, etc.)
if "Value" not in portfolio.columns:
    st.error("portfolio_data.csv must contain a 'Value' column.")
    st.stop()

raw_total_value = pd.to_numeric(portfolio["Value"], errors="coerce").sum()
cash_mask = portfolio["Ticker"].str.contains("SPAXX", case=False, na=False)
raw_cash_value = pd.to_numeric(portfolio.loc[cash_mask, "Value"], errors="coerce").sum()

# 🔒 Use manual overrides for all tactical logic and metrics
total_value = MANUAL_TOTAL_VALUE
cash_value  = MANUAL_CASH_VALUE

# =========================================================
# 2) ZACKS FILE AUTO-DETECT
# =========================================================

def find_latest_by_keywords(keywords):
    """Find latest CSV in /data containing all keywords (case-insensitive) and a date."""
    data_path = Path("data")
    if not data_path.exists():
        return None

    files = list(data_path.glob("*.csv"))
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    best = None
    best_date = None

    for f in files:
        name = f.name.lower()
        if all(k.lower() in name for k in keywords):
            m = date_pattern.search(f.name)
            if not m:
                continue
            d = m.group(1)
            try:
                dt = datetime.datetime.strptime(d, "%Y-%m-%d").date()
            except Exception:
                continue
            if (best_date is None) or (dt > best_date):
                best_date = dt
                best = f

    return str(best) if best is not None else None

def safe_read(path):
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

# Allow both underscore and space naming styles
G1_PATH = find_latest_by_keywords(["zacks", "growth", "1"])
G2_PATH = find_latest_by_keywords(["zacks", "growth", "2"])
DD_PATH = find_latest_by_keywords(["zacks", "defensive"])

g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Latest Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data folder.")

# =========================================================
# 3) NORMALIZE ZACKS + CROSSMATCH
# =========================================================

def normalize_zacks(df: pd.DataFrame, group_name: str) -> pd.DataFrame:
    if df.empty:
        return df

    cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if cols:
        df = df.rename(columns={cols[0]: "Ticker"})

    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols:
            df = df.rename(columns={rank_cols[0]: "Zacks Rank"})

    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    if not keep:
        return pd.DataFrame()

    out = df[keep].copy()
    out["Ticker"] = out["Ticker"].astype(str)
    if "Zacks Rank" in out.columns:
        out["Zacks Rank"] = pd.to_numeric(out["Zacks Rank"], errors="coerce")
    out["Group"] = group_name
    return out

def cross_match(zdf: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    if zdf.empty:
        return pd.DataFrame()
    pf_tickers = pf[["Ticker"]].astype(str)
    merged = zdf.merge(pf_tickers, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

g1 = normalize_zacks(g1_raw, "Growth 1")
g2 = normalize_zacks(g2_raw, "Growth 2")
dd = normalize_zacks(dd_raw, "Defensive Dividend")

combined_zacks = (
    pd.concat([g1, g2, dd], axis=0, ignore_index=True)
    .drop_duplicates(subset=["Ticker"], keep="first")
    if (not g1.empty or not g2.empty or not dd.empty)
    else pd.DataFrame()
)

# =========================================================
# 4) RANK DELTA (TODAY VS PRIOR DAY – BEST EFFORT)
# =========================================================

def find_prev_by_keywords_and_date(keywords, target_date: datetime.date):
    data_path = Path("data")
    if not data_path.exists():
        return None
    files = list(data_path.glob("*.csv"))
    date_str = target_date.strftime("%Y-%m-%d")
    for f in files:
        name_low = f.name.lower()
        if all(k.lower() in name_low for k in keywords) and date_str in f.name:
            return str(f)
    return None

def load_prev_today_pair(keywords):
    latest_path = find_latest_by_keywords(keywords)
    if not latest_path:
        return pd.DataFrame(), pd.DataFrame()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(latest_path).name)
    if not m:
        return safe_read(latest_path), pd.DataFrame()
    today_date = datetime.datetime.strptime(m.group(1), "%Y-%m-%d").date()
    prev_date = today_date - datetime.timedelta(days=1)
    prev_path = find_prev_by_keywords_and_date(keywords, prev_date)
    return safe_read(latest_path), safe_read(prev_path)

def prep_rank_df(df, group_name: str):
    return normalize_zacks(df, group_name)

g1_today_raw, g1_prev_raw = load_prev_today_pair(["zacks", "growth", "1"])
g2_today_raw, g2_prev_raw = load_prev_today_pair(["zacks", "growth", "2"])
dd_today_raw, dd_prev_raw = load_prev_today_pair(["zacks", "defensive"])

today_all = pd.concat(
    [prep_rank_df(g1_today_raw, "Growth 1"),
     prep_rank_df(g2_today_raw, "Growth 2"),
     prep_rank_df(dd_today_raw, "Defensive Dividend")],
    axis=0, ignore_index=True
)

prev_all = pd.concat(
    [prep_rank_df(g1_prev_raw, "Growth 1"),
     prep_rank_df(g2_prev_raw, "Growth 2"),
     prep_rank_df(dd_prev_raw, "Defensive Dividend")],
    axis=0, ignore_index=True
)

def compute_rank_deltas(today_df: pd.DataFrame, prev_df: pd.DataFrame):
    if today_df.empty or prev_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        t = today_df[["Ticker", "Zacks Rank"]].dropna().copy()
        p = prev_df[["Ticker", "Zacks Rank"]].dropna().copy()
        t["Ticker"] = t["Ticker"].astype(str)
        p["Ticker"] = p["Ticker"].astype(str)
        merged = t.merge(p, on="Ticker", how="outer", suffixes=("_Today", "_Prev"))
        new_rank1 = merged[
            (merged["Zacks Rank_Today"] == 1) & (merged["Zacks Rank_Prev"] != 1)
        ]
        dropped_rank1 = merged[
            (merged["Zacks Rank_Today"] != 1) & (merged["Zacks Rank_Prev"] == 1)
        ]
        persistent_rank1 = merged[
            (merged["Zacks Rank_Today"] == 1) & (merged["Zacks Rank_Prev"] == 1)
        ]
        return new_rank1, persistent_rank1, dropped_rank1
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

new1, persist1, drop1 = compute_rank_deltas(today_all, prev_all)

# =========================================================
# 5) ALLOCATION + INTELLIGENCE ENGINE
# =========================================================

def suggest_stop_for_group(group: str) -> str:
    if "Growth 1" in group:
        return "10%"
    if "Growth 2" in group:
        return "10%"
    if "Defensive" in group:
        return "12%"
    return "10%"

def build_allocation_for_new_rank1(combined: pd.DataFrame,
                                   portfolio_df: pd.DataFrame,
                                   total_value: float,
                                   cash_value: float) -> pd.DataFrame:
    if combined.empty:
        return pd.DataFrame()

    held = set(portfolio_df["Ticker"].astype(str))
    candidates = combined[(combined["Zacks Rank"] == 1)].copy()
    candidates = candidates[~candidates["Ticker"].isin(held)].copy()

    if candidates.empty:
        return candidates

    # Maintain 15% cash floor
    min_cash = 0.15 * total_value
    if cash_value <= min_cash:
        candidates["Suggested Stop %"] = candidates["Group"].apply(suggest_stop_for_group)
        candidates["AllocPct"] = 0.0
        candidates["EstBuy$"] = 0.0
        candidates["AI Action"] = "HOLD – Cash floor reached"
        return candidates

    deployable = cash_value - min_cash
    n = len(candidates)
    if n <= 0 or deployable <= 0:
        candidates["Suggested Stop %"] = candidates["Group"].apply(suggest_stop_for_group)
        candidates["AllocPct"] = 0.0
        candidates["EstBuy$"] = 0.0
        candidates["AI Action"] = "HOLD – No deployable cash"
        return candidates

    max_pos_value = 0.15 * total_value  # single-position cap
    per_dollars = min(deployable / n, max_pos_value)
    per_pct = per_dollars / total_value * 100 if total_value > 0 else 0.0

    candidates["Suggested Stop %"] = candidates["Group"].apply(suggest_stop_for_group)
    candidates["AllocPct"] = per_pct
    candidates["EstBuy$"] = per_dollars
    candidates["AI Action"] = "BUY – Rank #1 candidate"

    return candidates

def build_intel_overlay(portfolio_df: pd.DataFrame,
                        combined_df: pd.DataFrame,
                        new1: pd.DataFrame,
                        persist1: pd.DataFrame,
                        drop1: pd.DataFrame,
                        cash_value: float,
                        total_value: float) -> dict:
    held = set(portfolio_df["Ticker"].astype(str))
    if not combined_df.empty and "Zacks Rank" in combined_df.columns:
        rank1 = combined_df[combined_df["Zacks Rank"] == 1]
    else:
        rank1 = pd.DataFrame()

    new_unheld = rank1[~rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()
    held_rank1 = rank1[rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()

    cash_pct = (cash_value / total_value) * 100 if total_value > 0 else 0

    bias = "⚪ Neutral"
    if len(new_unheld) > len(drop1):
        bias = "🟢 Offensive Bias"
    elif len(drop1) > len(new_unheld):
        bias = "🟠 Defensive Bias"

    narrative = f"""
Fox Valley Tactical Intelligence – Daily Overlay
Portfolio: ${total_value:,.2f}
Cash: ${cash_value:,.2f} ({cash_pct:.1f}%)
Active Bias: {bias}

New Rank #1s vs yesterday: {len(new1)}
Persistent Rank #1s: {len(persist1)}
Dropped Rank #1s: {len(drop1)}

New Rank #1 Candidates NOT Held: {len(new_unheld)}
Held Positions Still Rank #1: {len(held

1)}
"""

    return {
        "narrative": narrative.strip(),
        "combined": combined_df,
        "new_unheld": new_unheld,
        "held_rank1": held_rank1,
        "new1": new1,
        "drop1": drop1,
        "bias": bias,
    }

allocation_df = build_allocation_for_new_rank1(
    combined_zacks, portfolio, total_value, cash_value
)

intel = build_intel_overlay(
    portfolio,
    combined_zacks,
    new1,
    persist1,
    drop1,
    cash_value,
    total_value,
)

# =========================================================
# 6) MAIN TABS (7 TAB LAYOUT, DARK MODE)
# =========================================================

tabs = st.tabs(
    [
        "💼 Portfolio Overview",
        "📊 Growth 1",
        "📊 Growth 2",
        "💰 Defensive Dividend",
        "⚙️ Tactical Decision Matrix",
        "🧩 Tactical Summary",
        "📖 Daily Intelligence Brief",
    ]
)

# --- TAB 0: PORTFOLIO OVERVIEW ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings (Active – MRMD/KE/IPG Removed)")
    st.dataframe(portfolio, use_container_width=True)

    col1, col2 = st.columns(2)
    col1.metric("Total Account Value", f"${total_value:,.2f}")
    col2.metric("Cash Available to Trade", f"${cash_value:,.2f}")

    if not portfolio.empty and "Value" in portfolio.columns:
        fig = px.pie(
            portfolio,
            values="Value",
            names="Ticker",
            title="Portfolio Allocation (using CSV values)",
            hole=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 1: GROWTH 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m = cross_match(g1, portfolio)
    if not g1m.empty:
        g1m["Suggested Stop %"] = g1m["Group"].apply(suggest_stop_for_group)
        st.dataframe(g1m, use_container_width=True)
    else:
        st.info("No valid Zacks Growth 1 data detected.")

# --- TAB 2: GROWTH 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m = cross_match(g2, portfolio)
    if not g2m.empty:
        g2m["Suggested Stop %"] = g2m["Group"].apply(suggest_stop_for_group)
        st.dataframe(g2m, use_container_width=True)
    else:
        st.info("No valid Zacks Growth 2 data detected.")

# --- TAB 3: DEFENSIVE DIVIDEND ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm = cross_match(dd, portfolio)
    if not ddm.empty:
        ddm["Suggested Stop %"] = ddm["Group"].apply(suggest_stop_for_group)
        st.dataframe(ddm, use_container_width=True)
    else:
        st.info("No valid Zacks Defensive Dividend data detected.")

# --- TAB 4: TACTICAL DECISION MATRIX ---
with tabs[4]:
    st.subheader("⚙️ Tactical Decision Matrix – BUY Candidates")
    if not allocation_df.empty:
        st.dataframe(allocation_df, use_container_width=True)
        if "AllocPct" in allocation_df.columns:
            total_alloc_pct = allocation_df["AllocPct"].sum()
            est_total_buy = allocation_df["EstBuy$"].sum()
            st.markdown(
                f"**Total Proposed Allocation → {total_alloc_pct:.1f}% (~${est_total_buy:,.0f})**"
            )
            st.caption("Rule: Maintain ~15% cash and ≤15% per single position.")
    else:
        st.info("No new Zacks Rank #1 candidates available for deployment under current cash rules.")

# --- TAB 5: TACTICAL SUMMARY ---
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary – Bias & Rank Overview")
    st.markdown(f"```text\n{intel['narrative']}\n```")

    st.markdown("### 🟢 New Rank #1s vs Yesterday (All Screens)")
    if not intel["new1"].empty:
        st.dataframe(intel["new1"], use_container_width=True)
    else:
        st.info("No detectable new Rank #1 vs prior day (or no prior-day files).")

    st.markdown("### 🟠 Dropped Rank #1s Since Yesterday")
    if not intel["drop1"].empty:
        st.dataframe(intel["drop1"], use_container_width=True)
    else:
        st.info("No detectable dropped Rank #1 vs prior day (or no prior-day files).")

# --- TAB 6: DAILY INTELLIGENCE BRIEF ---
with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")

    st.markdown("#### 🧠 AI Tactical Narrative")
    st.markdown(f"```text\n{intel['narrative']}\n```")

    now_str = datetime.datetime.now().strftime("%A, %B %d, %Y – %I:%M %p CST")
    st.caption(f"Generated: {now_str}")

    st.markdown("### 🟢 New Zacks Rank #1 Candidates (Not Currently Held)")
    if not intel["new_unheld"].empty:
        st.dataframe(intel["new_unheld"], use_container_width=True)
    else:
        st.info("No NEW Rank #1 candidates outside current holdings today.")

    st.markdown("### ✔ Held Positions Still Zacks Rank #1")
    if not intel["held_rank1"].empty:
        st.dataframe(intel["held_rank1"], use_container_width=True)
    else:
        st.info("None of the current holdings are Rank #1 in today’s screens.")

    st.markdown("### 📋 Full Combined Zacks View (Growth 1 + Growth 2 + Defensive)")
    if not intel["combined"].empty:
        st.dataframe(intel["combined"], use_container_width=True)
    else:
        st.info("Upload new Zacks files to populate this view.")

# =========================================================
# 7) AUTO EXPORT DAILY INTEL BRIEF (06:45–06:55 CST)
# =========================================================

def export_intel_brief():
    now = datetime.datetime.now()
    fname = f"data/intel_brief_{now.strftime('%Y-%m-%d')}.md"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(intel["narrative"])
        st.caption(f"Intel brief exported → {fname}")
    except Exception as e:
        st.error(f"Failed to export intel brief: {e}")

now = datetime.datetime.now()
if now.hour == 6 and 45 <= now.minute < 55:
    export_intel_brief()
