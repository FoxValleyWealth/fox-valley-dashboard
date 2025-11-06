# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v6.2 – Restoration Build (Stable Nov 03, 2025)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime
import streamlit as st
st.cache_data.clear()

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.2 – Restoration Build",
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

# ---------- PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

portfolio = load_portfolio()
total_value = 163663.96
cash_value = 27721.60

# ---------- AUTO-DETECT ZACKS FILES ----------
def get_latest(pattern):
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated.append((m.group(1), f))
    return str(max(dated)[1]) if dated else None

G1_PATH = get_latest("zacks_custom_screen_*Growth1*.csv")
G2_PATH = get_latest("zacks_custom_screen_*Growth2*.csv")
DD_PATH = get_latest("zacks_custom_screen_*Defensive*.csv")

def safe_read(p):
    if not p: return pd.DataFrame()
    try: return pd.read_csv(p)
    except: return pd.DataFrame()

g1 = safe_read(G1_PATH)
g2 = safe_read(G2_PATH)
dd = safe_read(DD_PATH)

if not g1.empty or not g2.empty or not dd.empty:
    st.sidebar.success("✅ Latest Zacks screens auto-detected.")
else:
    st.sidebar.error("⚠️ No Zacks CSVs found in /data.")

# ---------- NORMALIZE + MATCH ----------
def normalize(df):
    if df.empty: return df
    tcols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tcols: df.rename(columns={tcols[0]: "Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        rcols = [c for c in df.columns if "rank" in c.lower()]
        if rcols: df.rename(columns={rcols[0]: "Zacks Rank"}, inplace=True)
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

def cross_match(zdf, pf):
    if zdf.empty: return pd.DataFrame()
    pf_t = pf[["Ticker"]].astype(str)
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    m = zdf.merge(pf_t, on="Ticker", how="left", indicator=True)
    m["Held?"] = m["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    m.drop(columns=["_merge"], inplace=True)
    return m

g1, g2, dd = normalize(g1), normalize(g2), normalize(dd)

# ---------- BUILD INTELLIGENCE OVERLAY ----------
def build_intel(pf, g1, g2, dd, cash_val, total_val):
    combined = pd.concat([g1, g2, dd], ignore_index=True).drop_duplicates(subset=["Ticker"])
    held = set(pf["Ticker"].astype(str))
    rank1 = combined[combined["Zacks Rank"] == 1] if "Zacks Rank" in combined else pd.DataFrame()
    new1 = rank1[~rank1["Ticker"].isin(held)]
    held1 = rank1[rank1["Ticker"].isin(held)]
    cash_pct = (cash_val / total_val) * 100 if total_val > 0 else 0

    msg = [f"Fox Valley Daily Tactical Overlay",
           f"• Portfolio Value: ${total_val:,.2f}",
           f"• Cash Available: ${cash_val:,.2f} ({cash_pct:.2f}%)",
           f"• Total #1 Symbols: {len(rank1)}",
           f"• New #1 Candidates: {len(new1)}",
           f"• Held #1 Positions: {len(held1)}"]
    return {"narrative": "\n".join(msg), "new": new1, "held": held1, "combined": combined}

intel = build_intel(portfolio, g1, g2, dd, cash_value, total_value)

# ---------- MAIN TABS ----------
tabs = st.tabs(["💼 Portfolio Overview","📊 Growth 1","📊 Growth 2","💰 Defensive Dividend",
                "⚙️ Tactical Decision Matrix","🧩 Tactical Summary","📖 Daily Intelligence Brief"])

# --- Portfolio Overview ---
with tabs[0]:
    st.metric("Total Account Value", f"${total_value:,.2f}")
    st.metric("Cash Available to Trade", f"${cash_value:,.2f}")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty:
        fig = px.pie(portfolio, values="Value", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m = cross_match(g1, portfolio)
    if not g1m.empty:
        st.dataframe(g1m.style.map(
            lambda v: "background-color:#004d00" if str(v)=="1"
            else "background-color:#665c00" if str(v)=="2"
            else "background-color:#663300" if str(v)=="3" else "",
            subset=["Zacks Rank"]), use_container_width=True)

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m = cross_match(g2, portfolio)
    if not g2m.empty:
        st.dataframe(g2m.style.map(
            lambda v: "background-color:#004d00" if str(v)=="1"
            else "background-color:#665c00" if str(v)=="2"
            else "background-color:#663300" if str(v)=="3" else "",
            subset=["Zacks Rank"]), use_container_width=True)

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm = cross_match(dd, portfolio)
    if not ddm.empty:
        st.dataframe(ddm.style.map(
            lambda v: "background-color:#004d00" if str(v)=="1"
            else "background-color:#665c00" if str(v)=="2"
            else "background-color:#663300" if str(v)=="3" else "",
            subset=["Zacks Rank"]), use_container_width=True)

# --- Tactical Decision Matrix ---
with tabs[4]:
    st.subheader("⚙️ Tactical Decision Matrix – Buy / Hold / Trim")
    st.markdown("""
    | Signal | Meaning |
    |:--|:--|
    |🟢 Buy|Zacks Rank #1 new candidates not held |
    |⚪ Hold|Existing positions that remain #1 |
    |🟠 Trim|Existing positions that lost #1 |
    """)
    st.info("Review each Rank 1–3 signal and update positions as needed.")

# --- Tactical Summary ---
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.text(intel["narrative"])

# --- Daily Intelligence Brief ---
with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.caption(f"Generated {datetime.datetime.now():%A, %B %d, %Y – %I:%M %p CST}")
    st.markdown("### 🟢 New Zacks Rank #1 Candidates")
    if not intel["new"].empty:
        st.dataframe(intel["new"], use_container_width=True)
    else:
        st.info("No new #1 candidates today.")
    st.markdown("### ✔ Held Positions Still #1")
    if not intel["held"].empty:
        st.dataframe(intel["held"], use_container_width=True)
    else:
        st.info("No current holdings remain #1 today.")
