# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v6.5 – Nov 2025
# Dark Command Build • Rank Delta • Tactical Allocation • Clean Portfolio
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import datetime, re

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.5 – Tactical Command",
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

# 🔥 Remove fully sold tickers from active display
sold_tickers = ["MRMD", "KE", "IPG"]
portfolio = portfolio[~portfolio["Ticker"].isin(sold_tickers)].copy()

total_value = portfolio["Value"].sum()
cash_row = portfolio[portfolio["Ticker"].str.contains("SPAXX", na=False)]
cash_value = cash_row["Value"].sum()

# ---------- AUTO-DETECT LATEST ZACKS FILES ----------
def get_latest_zacks_file(pattern: str):
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

G1_PATH = get_latest_zacks_file("*Growth 1.csv") or get_latest_zacks_file("*Growth1.csv")
G2_PATH = get_latest_zacks_file("*Growth 2.csv") or get_latest_zacks_file("*Growth2.csv")
DD_PATH = get_latest_zacks_file("*Defensive Dividends.csv") or get_latest_zacks_file("*DefensiveDividend.csv")

def safe_read(path: str | None):
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

# ---------- NORMALIZE + CROSSMATCH ----------
def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    tcols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tcols: df.rename(columns={tcols[0]:"Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        rcols=[c for c in df.columns if "rank" in c.lower()]
        if rcols: df.rename(columns={rcols[0]:"Zacks Rank"}, inplace=True)
    keep=[c for c in ["Ticker","Zacks Rank"] if c in df.columns]
    return df[keep].copy()

def cross_match(zdf: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    if zdf.empty: return pd.DataFrame()
    pf_tickers = pf[["Ticker"]].astype(str)
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    merged = zdf.merge(pf_tickers, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both":"✔ Held","left_only":"🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

g1,g2,dd = map(normalize_zacks,[g1_raw,g2_raw,dd_raw])

# ---------- RANK DELTA ----------
def compare_rank_deltas(today_df, prev_df):
    if today_df.empty or prev_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    merged = today_df.merge(prev_df, on="Ticker", how="outer", suffixes=("_Today","_Prev"))
    new_rank1 = merged[(merged["Zacks Rank_Today"]==1) & (merged["Zacks Rank_Prev"]!=1)]
    dropped_rank1 = merged[(merged["Zacks Rank_Today"]!=1) & (merged["Zacks Rank_Prev"]==1)]
    persistent_rank1 = merged[(merged["Zacks Rank_Today"]==1) & (merged["Zacks Rank_Prev"]==1)]
    return new_rank1,persistent_rank1,dropped_rank1

def get_yesterday_file(today_path):
    if today_path is None: return None
    m=re.search(r"(\d{4}-\d{2}-\d{2})",today_path)
    if not m: return None
    today_date=datetime.datetime.strptime(m.group(1),"%Y-%m-%d")
    yest=(today_date-datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    candidate=str(today_path).replace(m.group(1),yest)
    return candidate if Path(candidate).exists() else None

g1_prev,g2_prev,dd_prev=map(safe_read,[get_yesterday_file(G1_PATH),get_yesterday_file(G2_PATH),get_yesterday_file(DD_PATH)])
new1,persist1,drop1=compare_rank_deltas(pd.concat([g1,g2,dd]),pd.concat([g1_prev,g2_prev,dd_prev]))

# ---------- ALLOCATION + STOP RULES ----------
def recommend_allocation(rank):
    if str(rank)=="1": return 12.0
    if str(rank)=="2": return 8.0
    if str(rank)=="3": return 5.0
    return 0.0

def suggest_stop(df_name):
    if "Growth 1" in df_name: return "10%"
    if "Growth 2" in df_name: return "10%"
    if "Defensive" in df_name: return "12%"
    return "10%"

# ---------- BUILD INTELLIGENCE ----------
def build_intel(portfolio,g1,g2,dd,new1,persist1,drop1,cash_value,total_value):
    combined=pd.concat([g1,g2,dd],axis=0,ignore_index=True).drop_duplicates(subset=["Ticker"])
    held=set(portfolio["Ticker"].astype(str))
    rank1=combined[combined["Zacks Rank"]==1]
    new_rank1=rank1[~rank1["Ticker"].isin(held)]
    held_rank1=rank1[rank1["Ticker"].isin(held)]
    cash_pct=(cash_value/total_value)*100 if total_value>0 else 0

    bias="⚪ Neutral"
    if len(new_rank1)>len(drop1): bias="🟢 Offensive Bias"
    elif len(drop1)>len(new_rank1): bias="🟠 Defensive Bias"

    narrative=f"""
🧭 Fox Valley Tactical Intelligence – Daily Overlay
Portfolio: ${total_value:,.2f}
Cash: ${cash_value:,.2f} ({cash_pct:.1f}%)
Active Bias: {bias}

New Rank #1s: {len(new1)} | Persistent: {len(persist1)} | Dropped: {len(drop1)}
New Unheld #1 Candidates: {len(new_rank1)} | Held #1s: {len(held_rank1)}
"""
    return {"narrative":narrative,"combined":combined,"new_rank1":new_rank1,
            "held_rank1":held_rank1,"new1":new1,"drop1":drop1,"bias":bias}

intel=build_intel(portfolio,g1,g2,dd,new1,persist1,drop1,cash_value,total_value)

# ---------- MAIN TABS ----------
tabs=st.tabs([
    "💼 Portfolio Overview","📊 Growth 1","📊 Growth 2","💰 Defensive Dividend",
    "🧩 Tactical Summary","📖 Daily Intelligence Brief","⚙️ Tactical Decision Matrix"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings (Active)")
    st.dataframe(portfolio,use_container_width=True)
    if not portfolio.empty:
        fig=px.pie(portfolio,values="Value",names="Ticker",title="Portfolio Allocation",hole=0.3)
        st.plotly_chart(fig,use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m=cross_match(g1,portfolio)
    if not g1m.empty:
        g1m["Suggested Stop %"]=suggest_stop("Growth 1")
        st.dataframe(g1m,use_container_width=True)
    else: st.info("No valid Growth 1 data.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m=cross_match(g2,portfolio)
    if not g2m.empty:
        g2m["Suggested Stop %"]=suggest_stop("Growth 2")
        st.dataframe(g2m,use_container_width=True)
    else: st.info("No valid Growth 2 data.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm=cross_match(dd,portfolio)
    if not ddm.empty:
        ddm["Suggested Stop %"]=suggest_stop("Defensive Dividend")
        st.dataframe(ddm,use_container_width=True)
    else: st.info("No valid Defensive Dividend data.")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.markdown(f"```text\n{intel['narrative']}\n```")

# --- Daily Intelligence Brief ---
with tabs[5]:
    st.subheader("📖 Daily Intelligence Brief – Rank Delta Analysis")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.markdown("### 🟢 New Rank #1s vs Yesterday")
    st.dataframe(intel["new1"],use_container_width=True)
    st.markdown("### 🟠 Dropped Rank #1s Since Yesterday")
    st.dataframe(intel["drop1"],use_container_width=True)

# --- Tactical Decision Matrix ---
with tabs[6]:
    st.subheader("⚙️ Tactical Decision Matrix – Allocation Guidance")
    exec_df=intel["new_rank1"].copy()
    if not exec_df.empty:
        exec_df["Suggested Stop %"]="10%"
        exec_df["AllocPct"]=exec_df["Zacks Rank"].apply(recommend_allocation)
        exec_df["Alloc$"]=exec_df["AllocPct"]*total_value/100
        st.dataframe(exec_df,use_container_width=True)
        total_alloc=exec_df["AllocPct"].sum()
        tot_amt=exec_df["Alloc$"].sum()
        st.markdown(f"**Total Allocation → {total_alloc:.1f}% (~${tot_amt:,.0f})**")
    else:
        st.info("No new #1 candidates available for tactical allocation today.")

# --- Auto Export ---
def export_intel():
    now=datetime.datetime.now()
    fname=f"data/intel_brief_{now.strftime('%Y-%m-%d')}.md"
    with open(fname,"w",encoding="utf-8") as f:
        f.write(intel["narrative"])
    st.caption(f"Intel brief exported: {fname}")

now=datetime.datetime.now()
if now.hour==6 and 45<=now.minute<55:
    export_intel()
