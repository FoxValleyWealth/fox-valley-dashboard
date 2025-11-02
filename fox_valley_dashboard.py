# ============================================
# FOX VALLEY TACTICAL DASHBOARD v3 – Nov 2025
# Automated Zacks Loader + Tactical Summary (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

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
def get_latest_zacks_file(pattern):
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated_files = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated_files.append((m.group(1), f))
    if dated_files:
        latest = max(dated_files)[1]
        return str(latest)
    return None

G1_PATH = get_latest_zacks_file("zacks_custom_screen_*_Growth1.csv")
G2_PATH = get_latest_zacks_file("zacks_custom_screen_*_Growth2.csv")
DD_PATH = get_latest_zacks_file("zacks_custom_screen_*_DefensiveDividend.csv")

def safe_read(path):
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

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
        fig = px.pie(
            portfolio,
            values="Value",
            names="Ticker",
            title="Portfolio Allocation",
            hole=0.3
        )
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
            ),
            use_container_width=True
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
            ),
            use_container_width=True
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
            ),
            use_container_width=True
        )
    else:
        st.info("No valid Zacks Defensive Dividend data detected.")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("🧩 Weekly Tactical Summary – Automated Intelligence")

    st.markdown("### 📈 Portfolio Overview")
    portfolio["GainLoss%"] = pd.to_numeric(portfolio["GainLoss%"], errors="coerce")
    avg_gain = portfolio["GainLoss%"].mean()
    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("Avg Gain/Loss %", f"{avg_gain:.2f}%")

    st.markdown("**Top 3 Gainers**")
    st.dataframe(portfolio.nlargest(3, "GainLoss%")[["Ticker", "GainLoss%"]])

    st.markdown("**Top 3 Decliners**")
    st.dataframe(portfolio.nsmallest(3, "GainLoss%")[["Ticker", "GainLoss%"]])

    st.markdown("---")
    st.markdown("### 🧠 Tactical Analysis")
    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True).drop_duplicates(subset=["Ticker"])
    if not combined.empty:
        held = combined.merge(portfolio[["Ticker"]], on="Ticker", how="inner")
        new = combined[~combined["Ticker"].isin(portfolio["Ticker"])]
        st.markdown("**🟢 New Zacks Rank #1 Candidates:**")
        st.dataframe(new)
        st.markdown("**✔ Held Positions Still Active:**")
        st.dataframe(held)
    else:
        st.info("Zacks data unavailable for tactical analysis.")

    st.markdown("---")
    st.markdown("### 💰 Cash & Allocation")
    cash_pct = (cash_value / total_value) * 100 if total_value > 0 else 0
    st.metric("Cash (SPAXX)", f"${cash_value:,.2f}")
    st.metric("Cash % of Account", f"{cash_pct:.2f}%")

    if cash_pct < 5:
        st.warning("⚠️ Low cash reserves — limited buy power.")
    elif cash_pct > 25:
        st.info("🟡 Elevated cash — consider redeployment.")
    else:
        st.success("🟢 Balanced liquidity for tactical flexibility.")

    st.markdown("---")
    st.markdown("### 🎯 Tactical Plan")
    st.markdown("""
    - 🟢 **Potential Buys:** New Zacks Rank #1 candidates.
    - 🟠 **Review:** Positions that lost Zacks Rank #1.
    - ⚪ **Hold:** Active #1s with stable momentum.
    """)

# --- Automated Tactical Summary File Generation ---
def generate_tactical_summary():
    now = datetime.datetime.now()
    fname = f"data/tactical_summary_{now.strftime('%Y-%m-%d')}.md"
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
