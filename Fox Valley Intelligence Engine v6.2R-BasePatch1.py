# ---------- PORTFOLIO LOAD + NORMALIZATION ----------
import pandas as pd
import streamlit as st

# 1️⃣ Load portfolio safely
try:
    portfolio = pd.read_csv("data/portfolio_data.csv")
except Exception as e:
    st.error(f"❌ Unable to load portfolio_data.csv: {e}")
    st.stop()

# 2️⃣ Clean column names (strip spaces)
portfolio.columns = [c.strip() for c in portfolio.columns]

# 3️⃣ Rename Fidelity column headers to match what the app expects
portfolio.rename(columns={
    "Symbol": "Ticker",
    "Quantity": "Shares",
    "Last Price": "MarketPrice",
    "Cost Basis Total": "CostBasis",
    "Current Value": "MarketValue",
    "Total Gain/Loss Dollar": "GainLoss$",
    "Total Gain/Loss Percent": "GainLoss%"
}, inplace=True)

# 4️⃣ Normalize tickers
if "Ticker" in portfolio.columns:
    portfolio["Ticker"] = portfolio["Ticker"].astype(str).str.strip().str.upper()
    # Remove special characters like **, .PK, etc.
    portfolio["Ticker"] = portfolio["Ticker"].str.replace(r"[^A-Z]", "", regex=True)
else:
    st.warning("⚠️ 'Ticker' column not found in portfolio_data.csv")

# 5️⃣ Clean numeric fields (strip $, commas, %, +, etc.)
money_cols = ["MarketPrice", "CostBasis", "MarketValue", "GainLoss$", "GainLoss%"]
for col in money_cols:
    if col in portfolio.columns:
        portfolio[col] = (
            portfolio[col]
            .astype(str)
            .str.replace('[\$,()%+]', '', regex=True)
            .str.strip()
        )
        portfolio[col] = pd.to_numeric(portfolio[col], errors="coerce")

# 6️⃣ Ensure Shares is numeric
if "Shares" in portfolio.columns:
    portfolio["Shares"] = pd.to_numeric(portfolio["Shares"], errors="coerce")

# 7️⃣ If MarketValue missing but Shares & MarketPrice exist, compute it
if "MarketValue" not in portfolio.columns and all(
    c in portfolio.columns for c in ["Shares", "MarketPrice"]
):
    portfolio["MarketValue"] = portfolio["Shares"] * portfolio["MarketPrice"]
