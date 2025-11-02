# ============================================
# FOX VALLEY TACTICAL DASHBOARD v3 – Nov 2025
# Zacks Tactical Integration Edition + Automation (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from pathlib import Path

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Tactical Dashboard v3",
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
        .rank1 {background-color:#004d00 !important;} /* 🟩 */
        .rank2 {background-color:#665c00 !important;} /* 🟨 */
        .rank3 {background-color:#663300 !important;} /* 🟧 */
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

# ---------- HEADER ----------
st.title("🧭 Fox Valley Tactical Dashboard v3")
col1, col2 = st.columns(2)
col1.metric("Total Account Value", f"${total_value:,.2f}")
col2.metric("Cash – SPAXX (Money Market)", f"${cash_value:,.2f}")
st.markdown("---")

# ---------- LOAD ZACKS SCREENS ----------
G1_PATH = "data/zacks_custom_screen_2025-11-02_Growth1.csv"
G2_PATH = "data/zacks_custom_screen_2025-11-02_Growth2.csv"
DD_PATH = "data/zacks_custom_screen_2025-11-02_DefensiveDividend.csv"

def safe_read(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Zacks files loaded automatically from /data")
else:
    st.sidebar.error("⚠️ No Zacks files found in /data. Add them in GitHub → /data.")

# ---------- UTILITIES ----------
def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if ticker_cols:
        df = df.rename(columns={ticker_cols[0]: "Ticker"})
    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols:
            df = df.rename(columns={rank_cols[0]: "Zacks Rank"})
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

def cross_match(zacks_df: pd.DataFrame, portfolio_df: pd.DataFrame) -> pd.DataFrame:
    if zacks_df.empty:
        return pd.DataFrame()
    pf = portfolio_df[["Ticker"]].astype(str)
    zacks_df["Ticker"] = zacks_df["Ticker"].astype(str)
    merged = zacks_df.merge(pf, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

g1 = normalize_zacks(g1_raw)
g2 = normalize_zacks(g2_raw)
dd = normalize_zacks(dd_raw)

# ---------- MAIN TABS ----------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "🧩 Tactical Summary"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)

    if not portfolio.empty:
        fig1 = px.pie(portfolio, values="Value", names="Ticker",
                      title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No portfolio data found in /data/portfolio_data.csv")

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    if not g1.empty:
        g1_matched = cross_match(g1, portfolio)
        st.dataframe(
            g1_matched.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("Zacks Growth 1 screen not found or empty in /data.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    if not g2.empty:
        g2_matched = cross_match(g2, portfolio)
        st.dataframe(
            g2_matched.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("Zacks Growth 2 screen not found or empty in /data.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    if not dd.empty:
        dd_matched = cross_match(dd, portfolio)
        st.dataframe(
            dd_matched.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("Zacks Defensive Dividend screen not found or empty in /data.")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("Weekly Tactical Summary – Zacks Integration")

    # --- Portfolio Snapshot ---
    st.markdown("### 📈 Portfolio Performance Overview")
    try:
        portfolio["GainLoss%"] = pd.to_numeric(portfolio["GainLoss%"], errors="coerce")
        avg_gain = portfolio["GainLoss%"].mean()

        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
        st.metric("Average Gain/Loss %", f"{avg_gain:.2f}%")

        top_gainers = portfolio.nlargest(3, "GainLoss%")[["Ticker", "GainLoss%"]]
        top_losers = portfolio.nsmallest(3, "GainLoss%")[["Ticker", "GainLoss%"]]

        st.markdown("**Top 3 Gainers**")
        st.dataframe(top_gainers, hide_index=True, use_container_width=True)

        st.markdown("**Top 3 Decliners**")
        st.dataframe(top_losers, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Unable to compute performance: {e}")

    # --- Zacks Intelligence Feed ---
    st.markdown("---")
    st.markdown("### 🧩 Zacks Rank Cross-Analysis")

    def summarize_zacks_changes(zdf, pf):
        if zdf.empty:
            return pd.DataFrame()
        merged = zdf.merge(pf[["Ticker"]], on="Ticker", how="left", indicator=True)
        merged["Status"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 New Candidate"})
        merged.drop(columns="_merge", inplace=True)
        return merged

    combined_zacks = pd.concat([g1, g2, dd], axis=0, ignore_index=True).drop_duplicates(subset=["Ticker"])

    if not combined_zacks.empty:
        merged_status = summarize_zacks_changes(combined_zacks, portfolio)
        rank1_new = merged_status[(merged_status["Zacks Rank"] == 1) & (merged_status["Status"] == "🟢 New Candidate")]
        rank_drops = portfolio[~portfolio["Ticker"].isin(combined_zacks[combined_zacks["Zacks Rank"] == 1]["Ticker"])]

        st.markdown("#### 🟢 New Zacks #1 Rank Candidates (Not Held)")
        st.dataframe(rank1_new, hide_index=True, use_container_width=True)

        st.markdown("#### 🟠 Held Positions No Longer Zacks #1")
        st.dataframe(rank_drops[["Ticker", "Value"]], hide_index=True, use_container_width=True)
    else:
        st.info("Zacks data not available for analysis.")

    # --- Cash & Buy Power ---
    st.markdown("---")
    st.markdown("### 💰 Cash and Buy Power")
    cash_percent = (cash_value / total_value) * 100 if total_value > 0 else 0
    st.metric("Cash (SPAXX)", f"${cash_value:,.2f}")
    st.metric("Cash as % of Account", f"{cash_percent:.2f}%")

    if cash_percent < 5:
        st.warning("⚠️ Low cash reserves — limited buy flexibility.")
    elif cash_percent > 25:
        st.info("🟡 Cash levels elevated — review deployment options.")
    else:
        st.success("🟢 Cash allocation balanced for tactical flexibility.")

    # --- Tactical Guidance ---
    st.markdown("---")
    st.markdown("### 🎯 Tactical Action Plan")
    st.markdown("""
    - 🟢 **Potential Buys:** New Zacks Rank #1 stocks not currently held.
    - 🟠 **Review / Trim:** Held stocks that have lost Zacks Rank #1 status.
    - ⚪ **Hold / Monitor:** Current holdings still Zacks Rank #1.
    """)
    st.caption("Next tactical update scheduled for Sunday 07:00 CST.")

# ============================================
# PHASE 3 – AUTOMATED SUNDAY SUMMARY GENERATOR
# ============================================
def generate_tactical_report():
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    file_path = Path(f"data/tactical_summary_{today_str}.md")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# 🧩 Fox Valley Tactical Summary – {today_str}\n\n")
            f.write(f"**Generated:** {now.strftime('%A, %B %d, %Y %I:%M %p CST')}\n\n")
            f.write(f"**Total Value:** ${total_value:,.2f}\n")
            f.write(f"**Cash (SPAXX):** ${cash_value:,.2f}\n\n")
            f.write("## 🎯 Tactical Guidance\n")
            f.write("- 🟢 Review new Zacks #1 candidates\n")
            f.write("- 🟠 Evaluate positions losing Zacks #1\n")
            f.write("- ⚪ Maintain cash flexibility\n")
        st.success(f"✅ Tactical summary exported to {file_path.name}")
        st.caption(f"Last automated tactical report generated: {now.strftime('%Y-%m-%d %H:%M CST')}")
    except Exception as e:
        st.error(f"⚠️ Failed to write tactical summary: {e}")

# --- Weekly Auto-Refresh ---
now = datetime.datetime.now()
if now.weekday() == 6 and now.hour == 7:
    generate_tactical_report()
