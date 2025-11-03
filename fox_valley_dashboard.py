# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v5.3 – Nov 2025
# Zacks Tactical Rank Delta System + Tactical Alert Engine (Executive Command Edition)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime
import os

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v5.3",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- DARK MODE ----------
st.markdown("""
    <style>
        body {background-color:#0e1117;color:#FAFAFA;}
        [data-testid="stHeader"] {background-color:#0e1117;}
        [data-testid="stSidebar"] {background-color:#111318;}
        table {color:#FAFAFA;}
        .rank1 {background-color:#004d00 !important;}
        .rank2 {background-color:#665c00 !important;}
        .rank3 {background-color:#663300 !important;}
    </style>
""", unsafe_allow_html=True)

# ---------- CLEANUP SYSTEM ----------
def cleanup_old_files():
    """Remove Zacks CSVs older than 7 days; keep recent 2 for alert comparison."""
    data_path = Path("data")
    removed = []
    if not data_path.exists():
        return removed
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for f in data_path.glob("zacks_custom_screen_*.csv"):
        try:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", str(f))
            if match:
                file_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d")
                if file_date < cutoff:
                    f.unlink()
                    removed.append(f.name)
        except Exception:
            continue
    return removed

purged_files = cleanup_old_files()
last_cleanup = datetime.datetime.now().strftime("%Y-%m-%d %H:%M CST")

# ---------- LOAD PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

portfolio = load_portfolio()
total_value = portfolio["Value"].sum()
cash_value = portfolio.loc[portfolio["Ticker"].str.contains("SPAXX", na=False), "Value"].sum()

# ---------- AUTO-DETECT ZACKS FILES ----------
def get_sorted_zacks(pattern):
    """Return sorted list of (date, file) tuples newest→oldest."""
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated.append((m.group(1), f))
    return sorted(dated, reverse=True)

def safe_read(path):
    try:
        return pd.read_csv(path) if path else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ---------- DETECT TODAY + YESTERDAY FILES ----------
G1_all = get_sorted_zacks("zacks_custom_screen_*Growth1*.csv")
G2_all = get_sorted_zacks("zacks_custom_screen_*Growth2*.csv")
DD_all = get_sorted_zacks("zacks_custom_screen_*Defensive*.csv")

def pick_latest(files):
    return str(files[0][1]) if files else None

def pick_prev(files):
    return str(files[1][1]) if len(files) > 1 else None

G1, G2, DD = pick_latest(G1_all), pick_latest(G2_all), pick_latest(DD_all)
G1_prev, G2_prev, DD_prev = pick_prev(G1_all), pick_prev(G2_all), pick_prev(DD_all)

g1, g2, dd = safe_read(G1), safe_read(G2), safe_read(DD)
g1_prev, g2_prev, dd_prev = safe_read(G1_prev), safe_read(G2_prev), safe_read(DD_prev)

# ---------- NORMALIZATION ----------
def normalize(df):
    if df.empty:
        return df
    tick = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tick:
        df.rename(columns={tick[0]: "Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        ranks = [c for c in df.columns if "rank" in c.lower()]
        if ranks:
            df.rename(columns={ranks[0]: "Zacks Rank"}, inplace=True)
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

g1, g2, dd = map(normalize, [g1, g2, dd])
g1_prev, g2_prev, dd_prev = map(normalize, [g1_prev, g2_prev, dd_prev])

# ---------- INTELLIGENCE ENGINE ----------
def build_intel(pf, g1, g2, dd, cash, total):
    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True).drop_duplicates(subset=["Ticker"])
    held = set(pf["Ticker"].astype(str))
    rank1 = combined[combined["Zacks Rank"] == 1] if "Zacks Rank" in combined.columns else pd.DataFrame()
    new = rank1[~rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()
    kept = rank1[rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()
    cash_pct = (cash / total) * 100 if total > 0 else 0
    narrative = [
        f"🧭 Fox Valley Tactical Brief – {datetime.datetime.now():%B %d, %Y}",
        f"Portfolio: ${total:,.2f} | Cash: ${cash:,.2f} ({cash_pct:.2f}%)",
        f"Detected #1 tickers: {len(rank1)} | New #1s: {len(new)} | Held #1s: {len(kept)}",
    ]
    if cash_pct < 5:
        narrative.append("⚠️ Low liquidity – prioritize profit-taking or defensive holds.")
    elif cash_pct > 25:
        narrative.append("🟡 Elevated cash reserves – redeployment window open.")
    else:
        narrative.append("🟢 Cash allocation optimal for tactical execution.")
    return {"combined": combined, "new": new, "kept": kept, "narrative": "\n".join(narrative)}

intel = build_intel(portfolio, g1, g2, dd, cash_value, total_value)

# ---------- ALERT ENGINE ----------
def detect_alerts(today_df, prev_df, label):
    """Compare today vs yesterday for upgrades/downgrades/new/removals."""
    if today_df.empty or prev_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    merged = pd.merge(
        prev_df, today_df, on="Ticker", how="outer", suffixes=("_prev", "_today"), indicator=True
    )
    upgrades = merged[(merged["Zacks Rank_prev"] > merged["Zacks Rank_today"]) & (merged["_merge"] == "both")]
    downgrades = merged[(merged["Zacks Rank_prev"] < merged["Zacks Rank_today"]) & (merged["_merge"] == "both")]
    new = merged[merged["_merge"] == "right_only"]
    removed = merged[merged["_merge"] == "left_only"]
    for df in [upgrades, downgrades, new, removed]:
        df["Screen"] = label
    return upgrades, downgrades, new, removed

# Run comparisons
up1, down1, new1, rem1 = detect_alerts(g1, g1_prev, "Growth1")
up2, down2, new2, rem2 = detect_alerts(g2, g2_prev, "Growth2")
up3, down3, new3, rem3 = detect_alerts(dd, dd_prev, "Defensive")

up_all = pd.concat([up1, up2, up3], ignore_index=True)
down_all = pd.concat([down1, down2, down3], ignore_index=True)
new_all = pd.concat([new1, new2, new3], ignore_index=True)
rem_all = pd.concat([rem1, rem2, rem3], ignore_index=True)

# Log to file
alert_log_path = Path("data/alerts_log.csv")
def log_alerts():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if all(df.empty for df in [up_all, down_all, new_all, rem_all]):
        return None
    combined = pd.concat([up_all, down_all, new_all, rem_all], ignore_index=True)
    combined["Timestamp"] = now
    if alert_log_path.exists():
        old = pd.read_csv(alert_log_path)
        combined = pd.concat([old, combined], ignore_index=True)
    combined.to_csv(alert_log_path, index=False)
    return combined

alert_df = log_alerts()

# ---------- ROI TRACKER ----------
def log_roi():
    path = Path("data/roi_history.csv")
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    roi = (portfolio["GainLoss%"].mean()) if "GainLoss%" in portfolio.columns else 0
    new_row = pd.DataFrame([[now, total_value, cash_value, roi]],
                           columns=["Date", "Value", "Cash", "ROI"])
    if path.exists():
        df = pd.read_csv(path)
        df = pd.concat([df, new_row], ignore_index=True).drop_duplicates(subset=["Date"], keep="last")
    else:
        df = new_row
    df.to_csv(path, index=False)
    return df

roi_df = log_roi()

# ---------- MAIN DASHBOARD ----------
tabs = st.tabs([
    "🚨 Tactical Alert Engine",
    "📂 Data Integrity Report",
    "💼 Portfolio",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "🧩 Tactical Summary",
    "📈 ROI Tracker"
])

# --- ALERT TAB ---
with tabs[0]:
    st.subheader("🚨 Zacks Tactical Alert Engine – Day-to-Day Delta Report")
    if all(df.empty for df in [up_all, down_all, new_all, rem_all]):
        st.info("No changes detected between the last two sessions.")
    else:
        if not up_all.empty:
            st.markdown("### 🔺 Upgrades (Improved Rank)")
            st.dataframe(up_all[["Ticker", "Zacks Rank_prev", "Zacks Rank_today", "Screen"]])
        if not down_all.empty:
            st.markdown("### 🔻 Downgrades (Weakened Rank)")
            st.dataframe(down_all[["Ticker", "Zacks Rank_prev", "Zacks Rank_today", "Screen"]])
        if not new_all.empty:
            st.markdown("### 🆕 New Entrants")
            st.dataframe(new_all[["Ticker", "Zacks Rank_today", "Screen"]])
        if not rem_all.empty:
            st.markdown("### ❌ Removals (No Longer Listed)")
            st.dataframe(rem_all[["Ticker", "Zacks Rank_prev", "Screen"]])

# --- Data Integrity Report ---
with tabs[1]:
    st.subheader("📂 Data Integrity Report – Pre-Flight Validation")
    st.markdown(f"**Last Cleanup:** {last_cleanup}")
    if purged_files:
        st.markdown(f"🧹 Removed: {', '.join(purged_files)}")
    else:
        st.markdown("✅ No cleanup actions today.")

    integrity = []
    for name, path, df in [("Growth 1", G1, g1), ("Growth 2", G2, g2), ("Defensive", DD, dd)]:
        status = "✅ Loaded" if len(df) > 0 else "❌ Missing"
        integrity.append({"Screen": name, "File": Path(path).name if path else "None", "Records": len(df), "Status": status})
    st.dataframe(pd.DataFrame(integrity), use_container_width=True)

# --- Remaining Tabs (Portfolio, Growths, etc.) ---
def show_zacks(df, label):
    st.subheader(f"Zacks {label} Cross-Match")
    if df.empty:
        st.info(f"No valid {label} data found.")
        return
    merged = df.merge(portfolio[["Ticker"]], on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    st.dataframe(
        merged.style.map(
            lambda v: "background-color:#004d00" if str(v) == "1"
            else "background-color:#665c00" if str(v) == "2"
            else "background-color:#663300" if str(v) == "3"
            else "",
            subset=["Zacks Rank"]
        ), use_container_width=True
    )

with tabs[2]:
    st.subheader("💼 Portfolio Overview")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty:
        fig = px.pie(portfolio, values="Value", names="Ticker", title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

with tabs[3]: show_zacks(g1, "Growth 1")
with tabs[4]: show_zacks(g2, "Growth 2")
with tabs[5]: show_zacks(dd, "Defensive Dividend")

with tabs[6]:
    st.subheader("🧩 Tactical Summary – Executive Overview")
    st.markdown(f"```text\n{intel['narrative']}\n```")

with tabs[7]:
    st.subheader("📈 ROI vs Zacks 26% Annual Benchmark")
    if not roi_df.empty:
        fig = px.line(roi_df, x="Date", y="ROI", title="ROI History", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        current = roi_df.iloc[-1]["ROI"]
        st.metric("Current ROI", f"{current:.2f}%")
        delta = current - 26
        if current >= 26:
            st.success(f"🔥 Surpassing Zacks benchmark by {delta:.2f}%")
        else:
            st.warning(f"📉 Trailing benchmark by {abs(delta):.2f}%")
