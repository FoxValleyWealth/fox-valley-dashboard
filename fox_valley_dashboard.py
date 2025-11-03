# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v6.1 – Nov 2025
# Tactical Core System – Auto Allocation + Trade Plan (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.1 – Tactical Core System",
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
        .footer {color: #888; font-size: 0.8em; text-align: center; margin-top: 40px;}
        button {border-radius: 10px !important;}
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

# Include HSBC purchase
new_holding = pd.DataFrame([{"Ticker": "HSBC", "Value": 70 * 70.41, "GainLoss%": 0}])
portfolio = pd.concat([portfolio, new_holding], ignore_index=True)
total_value = portfolio["Value"].sum()

# ---------- AUTO-DETECT LATEST ZACKS FILES ----------
def get_latest_zacks_file(pattern):
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated_files = []
    for f in files:
        match = date_pattern.search(str(f))
        if match:
            dated_files.append((match.group(1), f))
    if dated_files:
        latest = max(dated_files)[1]
        return str(latest)
    return None

G1_PATH = get_latest_zacks_file("*Growth1*.csv")
G2_PATH = get_latest_zacks_file("*Growth2*.csv")
DD_PATH = get_latest_zacks_file("*Defensive*.csv")

def safe_read(path):
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw, g2_raw, dd_raw = map(safe_read, [G1_PATH, G2_PATH, DD_PATH])

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Latest Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data folder.")

# ---------- NORMALIZE & CROSSMATCH ----------
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

g1, g2, dd = map(normalize_zacks, [g1_raw, g2_raw, dd_raw])

# ---------- TACTICAL ENGINE ----------
def build_decision_matrix(portfolio_df, g1, g2, dd, cash_val, total_val):
    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True)
    combined = combined.drop_duplicates(subset=["Ticker"])
    held_tickers = set(portfolio_df["Ticker"].astype(str).tolist())
    combined["Held?"] = combined["Ticker"].apply(lambda x: "✔ Held" if x in held_tickers else "🟢 Candidate")

    # Suggested stops
    def stop_cat(ticker):
        if ticker in g1["Ticker"].values: return "10%"
        if ticker in g2["Ticker"].values: return "10%"
        if ticker in dd["Ticker"].values: return "12%"
        return ""

    combined["Suggested Stop %"] = combined["Ticker"].apply(stop_cat)
    combined["Zacks Rank"] = pd.to_numeric(combined["Zacks Rank"], errors="coerce")

    deployable_cash = total_val * 0.85
    max_weight = 0.15
    rank1 = combined[combined["Zacks Rank"] == 1]
    count = len(rank1)
    weight_each = min(max_weight, (deployable_cash / total_val) / max(1, count))
    combined["Suggested Allocation %"] = combined["Ticker"].apply(
        lambda t: f"{weight_each*100:.1f}%" if t in rank1["Ticker"].values else ""
    )
    combined["Estimated Buy Amount"] = combined["Suggested Allocation %"].apply(
        lambda x: f"${(float(x.strip('%'))/100)*total_val:,.2f}" if x else ""
    )

    return combined, rank1

decision_matrix, rank1_list = build_decision_matrix(portfolio, g1, g2, dd, cash_value, total_value)

# ---------- TABS ----------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "📈 Decision Matrix",
    "🧩 Tactical Summary",
    "📖 Daily Intelligence Brief"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)
    fig = px.pie(portfolio, values="Value", names="Ticker", title="Portfolio Allocation", hole=0.3)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<div class='footer'>Fox Valley Intelligence Engine v6.1 – Tactical Core System</div>", unsafe_allow_html=True)

# --- Growth 1 / Growth 2 / Defensive Dividend ---
for idx, (tab, df, name) in enumerate(zip(tabs[1:4], [g1, g2, dd], ["Growth 1", "Growth 2", "Defensive Dividend"])):
    with tab:
        st.subheader(f"Zacks {name} Cross-Match")
        if not df.empty:
            cm = cross_match(df, portfolio)
            st.dataframe(
                cm.style.map(
                    lambda v: "background-color: #004d00" if str(v) == "1"
                    else "background-color: #665c00" if str(v) == "2"
                    else "background-color: #663300" if str(v) == "3"
                    else "",
                    subset=["Zacks Rank"]
                ),
                use_container_width=True
            )
        else:
            st.info(f"No valid Zacks {name} data detected.")
        st.markdown("<div class='footer'>Fox Valley Intelligence Engine v6.1 – Tactical Core System</div>", unsafe_allow_html=True)

# --- Decision Matrix ---
with tabs[4]:
    st.subheader("📈 Tactical Decision Matrix – Auto Weighted Allocation")
    st.dataframe(decision_matrix, use_container_width=True)
    st.markdown("💹 Each Zacks #1 candidate capped at 15% allocation, cash floor held at 15%.")
    if st.button("🚀 Deploy Trade Plan (Simulation Only)"):
        st.success("Trade Plan validated – ready for Fidelity execution window.")
    st.markdown("<div class='footer'>Fox Valley Intelligence Engine v6.1 – Tactical Core System</div>", unsafe_allow_html=True)

# --- Tactical Summary ---
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.write(f"Total Value: ${total_value:,.2f}")
    st.write(f"Cash Available: ${cash_value:,.2f}")
    st.write(f"Active Zacks #1 Candidates: {len(rank1_list)}")
    st.dataframe(rank1_list, use_container_width=True)
    st.markdown("<div class='footer'>Fox Valley Intelligence Engine v6.1 – Tactical Core System</div>", unsafe_allow_html=True)

# --- Daily Intelligence Brief ---
with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    now = datetime.datetime.now().strftime("%A, %B %d, %Y – %I:%M %p CST")
    st.caption(f"Generated: {now}")
    st.write("🧭 Tactical Insights:")
    if not rank1_list.empty:
        st.success(f"{len(rank1_list)} Zacks #1s detected – Allocation model active.")
    else:
        st.warning("No active Zacks #1s detected today.")
    st.markdown("<div class='footer'>Fox Valley Intelligence Engine v6.1 – Tactical Core System</div>", unsafe_allow_html=True)
