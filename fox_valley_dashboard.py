import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Fox Valley Technical Console", layout="wide")

st.title("🦊 Fox Valley Technical Console")
st.markdown("This dashboard is your command center for tactical stock screening, portfolio review, and real-time decisions.")

# Sidebar for user options
st.sidebar.header("🧭 Navigation")
selected_section = st.sidebar.radio("Go to:", ["Portfolio Overview", "Watchlist", "Zacks Screen Upload", "Notes"])

# Portfolio data (placeholder — replace with live data connection later)
portfolio = pd.DataFrame({
    "Ticker": ["NVDA", "IBKR", "XPER"],
    "Shares": [295, 100, 750],
    "Cost Basis": [176.71, 63.00, 6.25],
    "Current Price": [476.00, 85.00, 6.60]
})
portfolio["Market Value"] = portfolio["Shares"] * portfolio["Current Price"]
portfolio["Unrealized Gain/Loss"] = portfolio["Market Value"] - (portfolio["Shares"] * portfolio["Cost Basis"])

# Section rendering
if selected_section == "Portfolio Overview":
    st.subheader("📊 Current Holdings")
    st.dataframe(portfolio, use_container_width=True)
    st.metric("Total Market Value", f"${portfolio['Market Value'].sum():,.2f}")
    st.metric("Total Gain/Loss", f"${portfolio['Unrealized Gain/Loss'].sum():,.2f}")

elif selected_section == "Watchlist":
    st.subheader("👀 Stocks On Watch")
    st.write("AU, DINO, VYX, others...")

elif selected_section == "Zacks Screen Upload":
    st.subheader("📁 Upload Zacks Custom Screens")
    uploaded_file = st.file_uploader("Upload a Zacks CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)

elif selected_section == "Notes":
    st.subheader("📝 Tactical Notes")
    st.text_area("Enter your thoughts here:", height=200)

st.sidebar.markdown(f"📅 Date: {datetime.date.today().strftime('%B %d, %Y')}")

