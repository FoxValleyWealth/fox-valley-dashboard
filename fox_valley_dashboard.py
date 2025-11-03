# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v5.1 – Nov 2025
# Zacks Tactical Rank Delta System (Executive Mode + Auto Maintenance)
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
    page_title="Fox Valley Intelligence Engine v5.1",
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

# ---------- AUTO FILE MAINTENANCE ----------
def cleanup_old_files():
    """Deletes Zacks CSVs older than 7 days; retains ROI and portfolio files."""
    data_path = Path("data")
    if not data_path.exists():
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for f in data_path.glob("zacks_custom_screen_*.csv"):
        try:
            # Extract date pattern
            match = re.search(r"(\d{4}-\d{2}-\d{2})", str(f))
            if match:
                file_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d")
                if file_date < cutoff:
                    f.unlink()
                    st.sidebar.info(f"🧹 Removed old file: {f.name}")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not process {f.name}: {e}")

cleanup_old_files()

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

# ---------- AUTO-DETECT LATEST ZACKS FILES ----------
def get_latest(pattern):
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated = []
    for f in files:
        m = date_pattern.search(str(f))
        if m: dated.append((m.group(1), f))
    return str(max(dated)[1]) if dated else None

G1 = get_latest("zacks_custom_screen_*Growth1*.csv")
G2 = get_latest("zacks_custom_screen_*Growth2*.csv")
DD = get_latest("zacks_custom_screen_*Defensive*.csv")

def safe_read(p):
    try:
        return pd.read_csv(p) if p else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

g1 = safe_read(G1)
g2 = safe_read(G2)
dd = safe_read(DD)

# ---------- SIDEBAR STATUS ----------
if any(not d.empty for d in [g1, g2, dd]):
    st.sidebar.success("✅ Latest Zacks files auto-loaded from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data folder.")

# ---------- NORMALIZATION ----------
def normalize(df):
    if df.empty: return df
    tick = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tick: df.rename(columns={tick[0]: "Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        ranks = [c for c in df.columns if "rank" in c.lower()]
        if ranks: df.rename(columns={ranks[0]: "Zacks Rank"}, inplace=True)
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

g1, g2, dd = map(normalize, [g1, g2, dd])

# ---------- INTELLIGENCE ENGINE ----------
def build_intel(pf, g1, g2, dd, cash, total):
    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True).drop_duplicates(subset=["Ticker"])
    held = set(pf["Ticker"].astype(str))
    rank1 = combined[combined["Zacks Rank"] == 1] if "Zacks Rank" in combined.columns else pd.DataFrame()
    new = rank1[~rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()
    kept = rank1[rank1["Ticker"].isin(held)] if not rank1.empty else pd.DataFrame()

    cash_pct = (cash / total) * 100 if total > 0 else 0
    summary = [
        f"🧭 Fox Valley Intelligence Brief – {datetime.datetime.now():%B %d, %Y}",
        f"Total Portfolio: ${total:,.2f}",
        f"Cash Reserve: ${cash:,.2f} ({cash_pct:.2f}%)",
        f"Detected Zacks #1 tickers: {len(rank1)}",
        f"New #1 Candidates: {len(new)}",
        f"Held #1 Positions: {len(kept)}"
    ]
    if cash_pct < 5:
        summary.append("⚠️ Low liquidity – prioritize profit-taking or defensive holds.")
    elif cash_pct > 25:
        summary.append("🟡 Elevated cash reserves – redeployment window open.")
    else:
        summary.append("🟢 Cash allocation optimal for tactical execution.")

    return {"combined": combined, "new": new, "kept": kept, "narrative": "\n".join(summary)}

intel = build_intel(portfolio, g1, g2, dd, cash_value, total_value)

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
    "💼 Portfolio",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "🧩 Tactical Summary",
    "📈 ROI Tracker"
])

# --- Portfolio ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty:
        fig = px.pie(portfolio, values="Value", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

# --- Zacks Tabs ---
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

with tabs[1]: show_zacks(g1, "Growth 1")
with tabs[2]: show_zacks(g2, "Growth 2")
with tabs[3]: show_zacks(dd, "Defensive Dividend")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("🧩 Tactical Summary – Executive Overview")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.markdown("### 🟢 New Zacks Rank #1 Candidates")
    st.dataframe(intel["new"], use_container_width=True) if not intel["new"].empty else st.info("No new #1 candidates.")
    st.markdown("### ✔ Held Positions Still Rank #1")
    st.dataframe(intel["kept"], use_container_width=True) if not intel["kept"].empty else st.info("No held #1 positions today.")

# --- ROI Tracker ---
with tabs[5]:
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
    else:
        st.info("No ROI data logged yet.")

# ---------- AUTO DAILY REPORT ----------
def export_brief():
    now = datetime.datetime.now()
    fname = Path(f"data/tactical_brief_{now:%Y-%m-%d}.md")
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"# Fox Valley Daily Intelligence Brief – {now:%B %d, %Y}\n\n")
        f.write(intel["narrative"])
        f.write("\n\n## ROI Snapshot\n")
        f.write(roi_df.tail(1).to_string(index=False))
    st.caption(f"✅ Daily brief saved → {fname.name}")

now = datetime.datetime.now()
if now.hour == 6 and 45 <= now.minute < 55:
    export_brief()
