# ============================================
# FOX VALLEY TACTICAL DASHBOARD v4.4 – Nov 2025
# Unified Automation • Daily Intelligence • Debug Integration
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Tactical Dashboard v4.4",
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

# ---------- LOAD PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

portfolio = load_portfolio()
total_value = portfolio["Value"].sum()
cash_row = portfolio[portfolio["Ticker"].str.contains("SPAXX", na=False)]
cash_value = cash_row["Value"].sum()

# ---------- AUTO-DETECT LATEST ZACKS FILES ----------
def get_latest_zacks_file(patterns):
    files = []
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    for pattern in patterns:
        for f in Path("data").glob(pattern):
            m = date_pattern.search(str(f))
            if m:
                files.append((m.group(1), f))
    if files:
        return str(max(files)[1])
    return None

G1_PATH = get_latest_zacks_file(["*Growth1*.csv", "*Growth 1*.csv"])
G2_PATH = get_latest_zacks_file(["*Growth2*.csv", "*Growth 2*.csv"])
DD_PATH = get_latest_zacks_file(["*DefensiveDividend*.csv", "*Defensive Dividends*.csv"])

def safe_read(path):
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw, g2_raw, dd_raw = safe_read(G1_PATH), safe_read(G2_PATH), safe_read(DD_PATH)

# ---------- STATUS SIDEBAR ----------
if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Latest Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data folder.")

# ---------- NORMALIZE + MATCH ----------
def normalize_zacks(df):
    if df.empty:
        return df
    ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if ticker_cols:
        df.rename(columns={ticker_cols[0]: "Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols:
            df.rename(columns={rank_cols[0]: "Zacks Rank"}, inplace=True)
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

def cross_match(zdf, pf):
    if zdf.empty:
        return pd.DataFrame()
    pf_tickers = pf[["Ticker"]].astype(str)
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    merged = zdf.merge(pf_tickers, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

g1, g2, dd = normalize_zacks(g1_raw), normalize_zacks(g2_raw), normalize_zacks(dd_raw)

# ---------- MAIN TABS ----------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "🧩 Tactical Summary",
    "📖 Daily Intelligence Brief",
    "🧾 Debug Preview"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty:
        fig = px.pie(portfolio, values="Value", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No portfolio data found in /data/portfolio_data.csv")

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    if not g1.empty:
        g1m = cross_match(g1, portfolio)
        st.dataframe(
            g1m.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ), use_container_width=True
        )
    else:
        st.info("No valid Zacks Growth 1 data detected.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    if not g2.empty:
        g2m = cross_match(g2, portfolio)
        st.dataframe(
            g2m.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ), use_container_width=True
        )
    else:
        st.info("No valid Zacks Growth 2 data detected.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    if not dd.empty:
        ddm = cross_match(dd, portfolio)
        st.dataframe(
            ddm.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ), use_container_width=True
        )
    else:
        st.info("No valid Zacks Defensive Dividend data detected.")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("🧩 Weekly Tactical Summary – Zacks Intelligence")
    portfolio["GainLoss%"] = pd.to_numeric(portfolio["GainLoss%"], errors="coerce")
    avg_gain = portfolio["GainLoss%"].mean()
    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("Avg Gain/Loss %", f"{avg_gain:.2f}%")

    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True).drop_duplicates(subset=["Ticker"])
    held = combined.merge(portfolio[["Ticker"]], on="Ticker", how="inner")
    new = combined[~combined["Ticker"].isin(portfolio["Ticker"])]

    st.markdown("**🟢 New Zacks Rank #1 Candidates (Not Held)**")
    st.dataframe(new, hide_index=True, use_container_width=True)

    st.markdown("**✔ Held Positions Still Zacks Ranked**")
    st.dataframe(held, hide_index=True, use_container_width=True)

# --- Daily Intelligence Brief ---
with tabs[5]:
    st.subheader("📖 Daily Intelligence Brief")
    st.markdown(f"**Date:** {datetime.datetime.now():%A, %B %d, %Y}")
    if not combined.empty:
        rank1 = combined[combined["Zacks Rank"] == 1]
        held_rank1 = rank1.merge(portfolio[["Ticker"]], on="Ticker", how="inner")
        new_rank1 = rank1[~rank1["Ticker"].isin(portfolio["Ticker"])]

        st.markdown("### 🟢 Tactical Recommendations")
        st.markdown(f"- **New Rank #1 Buy Candidates:** {len(new_rank1)}")
        st.markdown(f"- **Held Rank #1 Positions:** {len(held_rank1)}")
        st.markdown(f"- **Total Portfolio Holdings:** {len(portfolio)}")

        st.markdown("---")
        if not new_rank1.empty:
            st.markdown("**New Zacks #1 Candidates:**")
            st.dataframe(new_rank1, hide_index=True, use_container_width=True)
        if not held_rank1.empty:
            st.markdown("**Held Zacks #1 Positions:**")
            st.dataframe(held_rank1, hide_index=True, use_container_width=True)
    else:
        st.info("No Zacks data available for intelligence summary.")

# --- Debug Preview ---
with tabs[6]:
    st.subheader("🧾 Debug Preview – File Detection & Diagnostics")
    st.markdown("**Detected Zacks Files:**")
    st.json({
        "Growth 1": G1_PATH,
        "Growth 2": G2_PATH,
        "Defensive Dividend": DD_PATH
    })
    st.markdown("**File Status Summary:**")
    st.write({
        "Growth 1 Rows": len(g1),
        "Growth 2 Rows": len(g2),
        "Defensive Dividend Rows": len(dd),
        "Portfolio Rows": len(portfolio)
    })
    st.markdown("**Preview: Growth 1 Sample**")
    st.dataframe(g1.head(), use_container_width=True)
    st.markdown("**Preview: Growth 2 Sample**")
    st.dataframe(g2.head(), use_container_width=True)
    st.markdown("**Preview: Defensive Dividend Sample**")
    st.dataframe(dd.head(), use_container_width=True)

# --- Automated Tactical Summary File Generation ---
def generate_tactical_summary():
    now = datetime.datetime.now()
    fname = f"data/tactical_summary_{now.strftime('%Y-%m-%d')}.md"
    cash_pct = (cash_value / total_value) * 100 if total_value > 0 else 0
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"# Fox Valley Tactical Summary – {now:%B %d, %Y}\n")
        f.write(f"**Total Value:** ${total_value:,.2f}\n")
        f.write(f"**Cash:** ${cash_value:,.2f} ({cash_pct:.2f}%)\n\n")
        f.write("## Tactical Plan\n")
        f.write("- 🟢 Buy Zacks Rank #1 candidates\n")
        f.write("- 🟠 Trim lagging positions\n")
        f.write("- ⚪ Maintain liquidity balance\n")
    st.success(f"Tactical summary exported → {fname}")

now = datetime.datetime.now()
if now.weekday() == 6 and now.hour == 7:
    generate_tactical_summary()
