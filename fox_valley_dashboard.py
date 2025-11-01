# ===============================
# 🧭 FOX VALLEY DASHBOARD v11.02.2025
# Self-Correcting Portfolio Console
# ===============================

import pandas as pd
import streamlit as st
import plotly.express as px
import re

st.set_page_config(page_title="Fox Valley Dashboard", layout="wide")

PORTFOLIO_FILE = "data/portfolio_data.csv"
TOTAL_PORTFOLIO_VALUE = 162167.42
CASH_AVAILABLE = 27694.93

# -------------------------------
# LOAD DATA SAFELY
# -------------------------------
@st.cache_data
def load_portfolio():
    df = pd.read_csv(PORTFOLIO_FILE)
    # Normalize headers: strip spaces, lower-case, remove punctuation
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"[^0-9A-Za-z%]+", "", regex=True)
        .str.replace("%", "Percent")
    )

    # Smart column renaming
    rename_map = {}
    for col in df.columns:
        c = col.lower()
        if "ticker" in c: rename_map[col] = "Ticker"
        elif "company" in c or "description" in c: rename_map[col] = "Company"
        elif "share" in c or "qty" in c or "quantity" in c: rename_map[col] = "Shares"
        elif "lastprice" in c or "price" in c: rename_map[col] = "LastPrice"
        elif "value" in c and "gain" not in c: rename_map[col] = "Value"
        elif "gainloss" in c and ("$" in c or "dollar" in c): rename_map[col] = "GainLoss$"
        elif "gainloss" in c and ("percent" in c or "%" in c): rename_map[col] = "GainLoss%"
        elif "cost" in c: rename_map[col] = "CostBasis"
        elif "account" in c: rename_map[col] = "Account"

    df.rename(columns=rename_map, inplace=True)

    # Fill missing expected columns
    for expected in ["Ticker","Company","Shares","LastPrice","Value","GainLoss$","GainLoss%","CostBasis","Account"]:
        if expected not in df.columns:
            df[expected] = None

    # Clean numeric columns
    for c in ["Value","GainLoss$","CostBasis","Shares","LastPrice"]:
        try:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
        except Exception:
            pass

    df["GainLoss%"] = df["GainLoss%"].astype(str).fillna("0")
    return df

portfolio = load_portfolio()

# -------------------------------
# METRICS HEADER
# -------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Total Account Value", f"${TOTAL_PORTFOLIO_VALUE:,.2f}")
c2.metric("Cash Available", f"${CASH_AVAILABLE:,.2f}")
c3.metric("Holdings", len(portfolio))

st.markdown("---")

# -------------------------------
# SIDEBAR FILTERS
# -------------------------------
st.sidebar.header("Filters & Controls")
accounts = st.sidebar.multiselect(
    "Select Accounts",
    options=sorted(portfolio["Account"].dropna().unique()),
    default=sorted(portfolio["Account"].dropna().unique())
)
gain_filter = st.sidebar.slider("Gain/Loss % Range", -50, 50, (-50, 50))
min_value = st.sidebar.number_input("Min Position Value ($)", 0, 100000, 0)

df = portfolio.copy()
df = df[df["Account"].isin(accounts)]

def parse_percent(val):
    try:
        val = str(val)
        return float(re.findall(r"-?\d+\.?\d*", val)[0])
    except:
        return 0.0

df["GainNum"] = df["GainLoss%"].apply(parse_percent)
df = df[(df["GainNum"] >= gain_filter[0]) & (df["GainNum"] <= gain_filter[1])]
df = df[df["Value"].fillna(0) >= min_value]

# -------------------------------
# MAIN TABLE
# -------------------------------
st.subheader("Portfolio Overview")
st.dataframe(df, use_container_width=True)

# -------------------------------
# VISUALS
# -------------------------------
tab1, tab2 = st.tabs(["📊 Allocation Chart", "📈 Gain/Loss Bar Chart"])

with tab1:
    alloc = df.groupby("Ticker", dropna=True)["Value"].sum().reset_index()
    fig = px.pie(alloc, values="Value", names="Ticker", title="Portfolio Allocation by Holding")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = px.bar(df, x="Ticker", y="GainNum", color="GainNum", text="GainLoss%",
                  title="Gain/Loss % by Holding", color_continuous_scale="RdYlGn")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("Zacks Screens: Growth 1 | Growth 2 | Defensive Dividend — 10/31/2025 Uploads Synced")
st.caption("Automation Schedule: Sunday–Friday Tactical Execution • Next Run: Sunday 11/02/2025")
