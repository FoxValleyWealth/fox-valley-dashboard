
import streamlit as st
import pandas as pd
import datetime
import altair as alt

st.set_page_config(page_title="Fox Valley Technical Console", layout="wide")

st.title("🦊 Fox Valley Technical Console")
st.markdown("This dashboard is your command center for tactical stock screening, portfolio review, and real-time decisions.")

# Sidebar Navigation
st.sidebar.header("🧭 Navigation")
selected_section = st.sidebar.radio("Go to:", [
    "Portfolio Overview", "Watchlist", "Zacks Screen Upload",
    "Notes", "Weekly AI Summary", "Spreadsheet Import", "Visual Charts"
])

# Dummy Portfolio Data - replace with live connection later
portfolio = pd.DataFrame({
    "Ticker": ["NVDA", "IBKR", "XPER"],
    "Shares": [295, 100, 750],
    "Cost Basis": [176.71, 63.00, 6.25],
    "Current Price": [476.00, 85.00, 6.60]
})
portfolio["Market Value"] = portfolio["Shares"] * portfolio["Current Price"]
portfolio["Unrealized Gain/Loss"] = portfolio["Market Value"] - (portfolio["Shares"] * portfolio["Cost Basis"])

# Section Logic
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

elif selected_section == "Notes":
    st.subheader("📝 Tactical Notes")
    st.text_area("Enter your thoughts here:", height=200)
    st.markdown("""
    ### 🧠 Weekly AI Summary
    - NVDA leading growth with solid gains.
    - VYX and DINO triggered tactical buys.
    - AU remains on watchlist amid gold sector softness.
    - Total portfolio value as of last close: **$161,969.06**
    """)

elif selected_section == "Spreadsheet Import":
    st.subheader("📂 Import Spreadsheet")
    excel_file = st.file_uploader("Upload Excel spreadsheet", type=["xlsx"])
    if excel_file:
        df = pd.read_excel(excel_file)
        st.dataframe(df)

elif selected_section == "Visual Charts":
    st.subheader("📈 Performance Visualization")
    base = alt.Chart(portfolio).encode(x="Ticker", y="Market Value", tooltip=["Market Value", "Unrealized Gain/Loss"])
    st.altair_chart(base.mark_bar(color="orange").properties(title="Market Value by Ticker"), use_container_width=True)
    st.altair_chart(base.mark_line(color="blue").encode(y="Unrealized Gain/Loss").properties(title="Unrealized Gain/Loss by Ticker"), use_container_width=True)

# Sidebar Timestamp
st.sidebar.markdown(f"📅 Date: {datetime.date.today().strftime('%B %d, %Y')}")
