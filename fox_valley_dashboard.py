# ===============================
# 🧭 FOX VALLEY DASHBOARD v11.01.2025
# Interactive Portfolio Command Console
# ===============================

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Fox Valley Dashboard", layout="wide")

PORTFOLIO_FILE = "data/portfolio_data.csv"
TOTAL_PORTFOLIO_VALUE = 162167.42
CASH_AVAILABLE = 27694.93

@st.cache_data
def load_portfolio():
    df = pd.read_csv(PORTFOLIO_FILE)
    df["GainLoss%"] = df["GainLoss%"].astype(str)
    return df

portfolio = load_portfolio()

col1, col2, col3 = st.columns(3)
col1.metric("Total Account Value", f"${TOTAL_PORTFOLIO_VALUE:,.2f}")
col2.metric("Cash Available", f"${CASH_AVAILABLE:,.2f}")
col3.metric("Number of Holdings", len(portfolio))

st.markdown("---")

st.sidebar.header("Filters & Controls")
accounts = st.sidebar.multiselect("Select Accounts", options=portfolio["Account"].unique(), default=portfolio["Account"].unique())
gain_filter = st.sidebar.slider("Gain/Loss % Range", -50, 50, (-50, 50))
min_value = st.sidebar.number_input("Min Position Value ($)", 0, 100000, 0)

filtered_df = portfolio.copy()
filtered_df = filtered_df[filtered_df["Account"].isin(accounts)]

def parse_percent(val):
    try:
        return float(val.replace("%", "").replace("+", "").replace("-", "")) * (-1 if "-" in val else 1)
    except:
        return 0.0

filtered_df["GainNum"] = filtered_df["GainLoss%"].apply(parse_percent)
filtered_df = filtered_df[
    (filtered_df["GainNum"] >= gain_filter[0]) &
    (filtered_df["GainNum"] <= gain_filter[1]) &
    (filtered_df["Value"] >= min_value)
]

st.subheader("Portfolio Overview")
st.dataframe(filtered_df, use_container_width=True)

tab1, tab2 = st.tabs(["📊 Allocation Chart", "📈 Gain/Loss Bar Chart"])

with tab1:
    alloc = filtered_df.groupby("Ticker")["Value"].sum().reset_index()
    fig = px.pie(alloc, values="Value", names="Ticker", title="Portfolio Allocation by Holding")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = px.bar(filtered_df, x="Ticker", y="GainNum", color="GainNum", text="GainLoss%",
                  title="Gain/Loss % by Holding", color_continuous_scale="RdYlGn")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("Zacks Screens: Growth 1 | Growth 2 | Defensive Dividend — 10/31/2025 Uploads Synced")
st.caption("Automation Schedule: Sunday–Friday Tactical Execution • Next Run: Sunday 11/02/2025")
