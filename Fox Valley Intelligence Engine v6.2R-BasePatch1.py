# ---------- PORTFOLIO LOAD + NORMALIZATION & VALIDATION ----------
import pandas as pd
import streamlit as st

# 1️⃣ Load portfolio safely
try:
    portfolio = pd.read_csv("data/portfolio_data.csv")
except Exception as e:
    st.error(f"❌ Unable to load portfolio_data.csv: {e}")
    st.stop()

# 2️⃣ Rename Fidelity column headers to match what the app expects
portfolio.rename(columns={
    "Quantity": "Shares",
    "Last Price": "MarketPrice",
    "Cost Basis Total": "CostBasis",
    "Current Value": "MarketValue",
    "Total Gain/Loss Dollar": "GainLoss$",
    "Total Gain/Loss Percent": "GainLoss%"
}, inplace=True)

# 3️⃣ Normalize tickers
if "Ticker" in portfolio.columns:
    portfolio["Ticker"] = portfolio["Ticker"].astype(str).str.strip().str.upper()
    portfolio["Ticker"] = portfolio["Ticker"].str.replace(r"[^A-Z]", "", regex=True)
else:
    st.warning("⚠️ Missing 'Ticker' column in portfolio_data.csv")

# 4️⃣ Compute gain/loss only if required columns exist
if all(col in portfolio.columns for col in ["CostBasis", "MarketPrice", "Shares"]):
    portfolio["Shares"] = pd.to_numeric(portfolio["Shares"], errors="coerce")
    portfolio["MarketValue"] = portfolio["Shares"] * portfolio["MarketPrice"]
    portfolio["GainLoss$"] = (portfolio["MarketPrice"] - portfolio["CostBasis"]) * portfolio["Shares"]
    portfolio["GainLoss%"] = ((portfolio["MarketPrice"] / portfolio["CostBasis"]) - 1) * 100
else:
    st.warning("⚠️ Missing one of: CostBasis, MarketPrice, or Shares columns.")
