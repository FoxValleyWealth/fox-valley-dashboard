# 🧭 Fox Valley Intelligence Engine — Enterprise Command Deck (v7.3R-4.2 | Manual Cash Override Extended Final Build – Nov 12 2025)
# Streamlit full deployment — production-ready build (manual cash entry + portfolio + Zacks + tactical + stops + performance)
# Author: #1 for CaptPicard

import os, io, math
from datetime import datetime
from typing import List, Tuple
import numpy as np
import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────
# PAGE CONFIG & STYLE
# ────────────────────────────────────────────────────────────────
st.set_page_config(
  page_title="Fox Valley Intelligence Engine — Command Deck v7.3R-4.2",
  page_icon="🧭",
  layout="wide",
)

st.markdown(
  """<style>
  div.block-container{padding-top:1.5rem}
  .section-card{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:1rem 1.5rem;margin-bottom:1rem}
  .data-ok{color:#22c55e;font-weight:600}.data-warn{color:#f59e0b;font-weight:600}.data-err{color:#ef4444;font-weight:700}
  </style>""",
  unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────
# CONSTANTS / PATHS
# ────────────────────────────────────────────────────────────────
DATA_DIR="data"
PORTFOLIO_FILE=os.path.join(DATA_DIR,"Portfolio_Positions_Nov-12-2025.csv")
ZACKS_G1_FILE=os.path.join(DATA_DIR,"zacks_custom_screen_2025-11-12 Growth 1.csv")
ZACKS_G2_FILE=os.path.join(DATA_DIR,"zacks_custom_screen_2025-11-12 Growth 2.csv")
ZACKS_DD_FILE=os.path.join(DATA_DIR,"zacks_custom_screen_2025-11-12 Defensive Dividends.csv")

# ────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(path:str)->Tuple[pd.DataFrame,List[str]]:
  msgs=[]
  if not os.path.exists(path):
    return pd.DataFrame(),[f"Missing file: {path}"]
  try:
    df=pd.read_csv(path,low_memory=False)
  except Exception as e:
    return pd.DataFrame(),[f"Failed to read {path}: {e}"]
  df.columns=[str(c).strip() for c in df.columns]
  def scrub(s):
    if pd.isna(s):return np.nan
    t=str(s).replace("$","").replace(",","").replace("%","").strip()
    neg=t.startswith("(") and t.endswith(")")
    t=t.replace("(","").replace(")","")
    try:v=float(t)
    except: return np.nan
    return -v if neg else v
  for c in ["Shares","Current Price","Current Value","Cost Basis","Average Cost","Day Gain","Gain/Loss %"]:
    if c in df.columns: df[c]=df[c].apply(scrub)
  if "Cost Basis" not in df.columns and "Average Cost" in df.columns:
    df["Cost Basis"]=df["Average Cost"]
  if "Current Value" not in df.columns and {"Shares","Current Price"}.issubset(df.columns):
    df["Current Value"]=df["Shares"]*df["Current Price"]
  return df,msgs

def money(x): return "—" if pd.isna(x) else f"${x:,.2f}"

def zacks_merge(g1,g2,dd):
  frames=[]
  for df,name in [(g1,"Growth 1"),(g2,"Growth 2"),(dd,"Defensive Dividends")]:
    if not df.empty:
      d=df.copy();d["Source"]=name;frames.append(d)
  return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()

# ────────────────────────────────────────────────────────────────
# SIDEBAR — MANUAL CASH & TRAILING SETTINGS
# ────────────────────────────────────────────────────────────────
st.sidebar.title("🧭 Command Deck — v7.3R-4.2")
st.sidebar.caption("Manual Cash Override Enabled | Nov 12 2025")
manual_cash=st.sidebar.number_input(
  "💰 Cash Available to Trade ($)",
  min_value=0.0,step=100.0,value=0.0,format="%.2f",
  help="Enter your current cash available to trade from Fidelity Balances tab. This overrides auto-detected SPAXX."
)
def_trail=st.sidebar.slider("Default Trailing Stop %",1,50,12)

# ────────────────────────────────────────────────────────────────
# LOAD DATA
# ────────────────────────────────────────────────────────────────
portfolio_df,pm=load_csv(PORTFOLIO_FILE)
g1_df,gm1=load_csv(ZACKS_G1_FILE)
g2_df,gm2=load_csv(ZACKS_G2_FILE)
dd_df,gm3=load_csv(ZACKS_DD_FILE)

# ────────────────────────────────────────────────────────────────
# PORTFOLIO OVERVIEW
# ────────────────────────────────────────────────────────────────
st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck")
st.caption("v7.3R-4.2 | Manual Cash Override Active | Diagnostics + Top-8 Analyzer Online")

st.markdown("---")
st.subheader("📊 Portfolio Overview")

val_col=next((c for c in ["Current Value","Market Value","Value"] if c in portfolio_df.columns),None)
est_total=float(pd.to_numeric(portfolio_df[val_col],errors='coerce').sum()) if val_col else 0.0
cash_val=manual_cash

c1,c2,c3,c4=st.columns(4)
with c1: st.metric("Estimated Total Value",money(est_total))
with c2: st.metric("Cash Available to Trade",money(cash_val))
with c3:
  dg=pd.to_numeric(portfolio_df.get("Day Gain",pd.Series(dtype=float)),errors='coerce')
  st.metric("Day Gain (sum)",money(dg.sum()) if not dg.empty else "—")
with c4:
  gl=pd.to_numeric(portfolio_df.get("Gain/Loss %",pd.Series(dtype=float)),errors='coerce')
  st.metric("Avg Gain/Loss %",f"{gl.mean():.2f}%" if not gl.empty else "—")

if manual_cash>0:
  st.success(f"Manual cash override active: {money(manual_cash)}")
else:
  st.warning("Manual cash is 0 — update sidebar for accurate available funds.")

if not portfolio_df.empty:
  st.dataframe(portfolio_df,use_container_width=True)
else:
  st.error("Portfolio file missing or empty.")

# ────────────────────────────────────────────────────────────────
# ZACKS UNIFIED ANALYZER + TOP-8
# ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔎 Zacks Unified Analyzer – Top Candidates")
all_z=zacks_merge(g1_df,g2_df,dd_df)
if not all_z.empty:
  if "Zacks Rank" in all_z.columns:
    all_z["Zacks Rank"]=pd.to_numeric(all_z["Zacks Rank"],errors='coerce')
  sort_cols=[c for c in ["Zacks Rank","PEG","PE"] if c in all_z.columns]
  if sort_cols:
    all_z=all_z.sort_values(by=sort_cols,ascending=True)
  top_n=st.slider("Top-N Candidates",4,20,8)
  st.dataframe(all_z.head(top_n),use_container_width=True)
  tickers=", ".join(sorted(set(all_z.head(top_n)["Ticker"].astype(str))))
  st.code(tickers,language="text")
else:
  st.warning("No Zacks data available.")

# ────────────────────────────────────────────────────────────────
# TACTICAL CONTROLS
# ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎯 Tactical Controls — Buy / Sell / Hold / Trim")
ca,cb,cc,cd=st.columns(4)
with ca:
  b_t=st.text_input("Buy Ticker")
  b_s=st.number_input("Buy Shares",min_value=0,step=1)
  st.button("Queue BUY",use_container_width=True)
with cb:
  s_t=st.text_input("Sell Ticker")
  s_s=st.number_input("Sell Shares",min_value=0,step=1)
  st.button("Queue SELL",use_container_width=True)
with cc:
  h_n=st.text_area("Hold Note")
  st.button("Log HOLD",use_container_width=True)
with cd:
  t_t=st.text_input("Trim Ticker")
  t_p=st.slider("Trim %",1,50,10)
  st.button("Queue TRIM",use_container_width=True)

st.caption("Interface only — no brokerage connectivity.")

# ────────────────────────────────────────────────────────────────
# TRAILING STOP MONITOR
# ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🛡️ Trailing Stop Monitor")
if not portfolio_df.empty and {"Ticker","Current Price"}.issubset(portfolio_df.columns):
  tdf=portfolio_df[[c for c in ["Ticker","Name","Current Price","Current Value"] if c in portfolio_df.columns]].copy()
  tdf["Trailing %"] = def_trail
  tdf["Stop Price"]=(1-tdf["Trailing %"] / 100)*tdf["Current Price"]
  st.dataframe(tdf,use_container_width=True)
  buf=io.StringIO();tdf.to_csv(buf,index=False)
  st.download_button("Download Trailing Stops CSV",buf.getvalue(),"trailing_stops_v73R42.csv")
else:
  st.info("Portfolio missing Ticker/Price for stops.")

# ────────────────────────────────────────────────────────────────
# PERFORMANCE SUMMARY
# ────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 Performance Summary")
cols=[c for c in ["Ticker","Name","Shares","Cost Basis","Current Price","Current Value","Gain/Loss %","Day Gain"] if c in portfolio_df.columns]
if cols:
  pf=portfolio_df[cols].copy()
  if {"Shares","Cost Basis","Current Price"}.issubset(pf.columns):
    pf["Gain $"]=(pf["Current Price"]-pf["Cost Basis"])*pf["Shares"]
  st.dataframe(pf,use_container_width=True)
else:
  st.info("Add basis and price columns for summary.")

# ────────────────────────────────────────────────────────────────
# FOOTER / DIAGNOSTICS
# ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"✅ Build v7.3R-4.2 | Manual Cash Override Active: {money(manual_cash)} | Files auto-loaded from /data | {datetime.now():%Y-%m-%d %H:%M:%S}")
