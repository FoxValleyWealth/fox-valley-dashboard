# =========================================================
# FOX VALLEY INTELLIGENCE ENGINE v6.3 – Nov 2025
# Dark Command Build – Post-Trade Integration
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.3 – Dark Command Build",
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
        .footer {color:#888;font-size:0.8em;text-align:center;margin-top:40px;}
        button {border-radius:10px !important;}
    </style>
""", unsafe_allow_html=True)

FOOTER_HTML = (
    "<div class='footer'>Fox Valley Intelligence Engine v6.3 – Dark Command Build © 2025</div>"
)

# =========================================================
# 1️⃣  PORTFOLIO BASELINE – POST-TRADE UPDATE
# =========================================================
@st.cache_data
def load_portfolio() -> pd.DataFrame:
    df = pd.read_csv("data/portfolio_data.csv")
    if "GainLoss%" in df.columns:
        df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

pf = load_portfolio().copy()

# remove exited tickers
for sold in ["MRMD","KE","IPG"]:
    pf = pf[pf["Ticker"] != sold]

# ensure PRK + NTB holdings exist
def ensure_position(df,ticker,shares,price):
    val = shares*price
    if ticker not in df["Ticker"].astype(str).tolist():
        add = {"Ticker":ticker,"Shares":shares,"Price":price,"Value":val,"GainLoss%":0}
        for c in df.columns:
            if c not in add:
                add[c]=None
        df = pd.concat([df,pd.DataFrame([add])],ignore_index=True)
    return df

pf = ensure_position(pf,"PRK",34,151.00)
pf = ensure_position(pf,"NTB",110,46.55)

# compute totals
total_value = 163_663.96
cash_value  = 37_650.30
cash_pct    = (cash_value/total_value)*100

# =========================================================
# 2️⃣  LOAD ZACKS FILES (LATEST + PRIOR)
# =========================================================
def _sorted(pattern):
    files=list(Path("data").glob(pattern))
    pat=re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated=[]
    for f in files:
        m=pat.search(f.name)
        if m: dated.append((m.group(1),f))
    dated.sort()
    return [p for _,p in dated]

def latest_prev(patterns):
    allp=[]
    for pat in patterns: allp+=_sorted(pat)
    allp=sorted(set(allp))
    if not allp: return None,None
    return str(allp[-1]),(str(allp[-2]) if len(allp)>1 else None)

G1_CUR,G1_PREV=latest_prev(["*Growth 1*.csv","*Growth1*.csv"])
G2_CUR,G2_PREV=latest_prev(["*Growth 2*.csv","*Growth2*.csv"])
DD_CUR,DD_PREV=latest_prev(["*Defensive*.csv","*Dividend*.csv"])

def safe_read(path):
    if not path: return pd.DataFrame()
    try: return pd.read_csv(path)
    except: return pd.DataFrame()

g1_cur,g2_cur,dd_cur=safe_read(G1_CUR),safe_read(G2_CUR),safe_read(DD_CUR)
g1_prev,g2_prev,dd_prev=safe_read(G1_PREV),safe_read(G2_PREV),safe_read(DD_PREV)

if any(not d.empty for d in [g1_cur,g2_cur,dd_cur]):
    st.sidebar.success("✅ Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks screens found in /data")

# =========================================================
# 3️⃣  NORMALIZE ZACKS DATA
# =========================================================
def normalize(df,group):
    if df.empty: return pd.DataFrame(columns=["Ticker","Zacks Rank","Group"])
    df=df.copy()
    tick=[c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tick: df.rename(columns={tick[0]:"Ticker"},inplace=True)
    if "Zacks Rank" not in df.columns:
        r=[c for c in df.columns if "rank" in c.lower()]
        if r: df.rename(columns={r[0]:"Zacks Rank"},inplace=True)
    keep=[c for c in ["Ticker","Zacks Rank"] if c in df.columns]
    df=df[keep].copy()
    df["Group"]=group
    return df

g1_cur,g2_cur,dd_cur=[normalize(d,g) for d,g in 
                      [(g1_cur,"Growth 1"),(g2_cur,"Growth 2"),(dd_cur,"Defensive Dividend")]]
g1_prev,g2_prev,dd_prev=[normalize(d,g) for d,g in 
                      [(g1_prev,"Growth 1"),(g2_prev,"Growth 2"),(dd_prev,"Defensive Dividend")]]

combined_cur=pd.concat([g1_cur,g2_cur,dd_cur],ignore_index=True).drop_duplicates("Ticker")
combined_prev=pd.concat([g1_prev,g2_prev,dd_prev],ignore_index=True).drop_duplicates("Ticker")

for d in [combined_cur,combined_prev]:
    if "Zacks Rank" in d.columns:
        d["Zacks Rank"]=pd.to_numeric(d["Zacks Rank"],errors="coerce")

# =========================================================
# 4️⃣  DECISION MATRIX + EXECUTION LOGIC
# =========================================================
def cross_match(z,port):
    if z.empty: return z
    pt=set(port["Ticker"].astype(str))
    z=z.copy(); z["Held?"]=z["Ticker"].apply(lambda t:"✔ Held" if t in pt else "🟢 Candidate")
    return z

def build_matrix(pf,comb,total,cash):
    if comb.empty: return pd.DataFrame()
    dm=cross_match(comb,pf)
    def stop(g):
        return "10%" if "Growth 1" in g else ("10%" if "Growth 2" in g else "12%")
    dm["Suggested Stop %"]=dm["Group"].apply(stop)
    def action(r):
        try:
            r=int(r)
            return "🟢 BUY" if r==1 else ("⚪ HOLD" if r==2 else "🟠 TRIM")
        except: return ""
    dm["Action"]=dm["Zacks Rank"].apply(action)
    r1=dm[dm["Zacks Rank"]==1]; n=len(r1)
    deploy=total*0.85
    per=min(0.15,(deploy/total/n if n else 0))
    dm["Suggested Allocation %"]=dm["Ticker"].apply(lambda t:per*100 if t in r1["Ticker"].values else 0)
    dm["Estimated Buy Amount"]=dm["Suggested Allocation %"].apply(
        lambda p:f"${(p/100)*total:,.2f}" if p else "")
    return dm

decision=build_matrix(pf,combined_cur,total_value,cash_value)

# =========================================================
# 5️⃣  RANK DELTAS
# =========================================================
def rank_deltas(cur,prev):
    if cur.empty or prev.empty: return pd.DataFrame(),pd.DataFrame()
    m=cur.merge(prev[["Ticker","Zacks Rank"]].rename(columns={"Zacks Rank":"Prev"}),on="Ticker",how="outer")
    new=m[(m["Zacks Rank"]==1)&(m["Prev"]!=1)]
    drop=m[(m["Prev"]==1)&(m["Zacks Rank"]!=1)]
    return new,drop
new1,drop1=rank_deltas(combined_cur,combined_prev)

# =========================================================
# 6️⃣  INTELLIGENCE BRIEF + EXECUTION PLAN
# =========================================================
def brief(dm,total,cash,cashpct):
    if dm.empty:
        return f"Value ${total:,.2f}\nCash ${cash:,.2f} ({cashpct:.1f}%)\nNo active signals."
    b=dm[dm["Action"].str.contains("BUY",na=False)]
    lines=[f"Portfolio ${total:,.2f}",f"Cash ${cash:,.2f} ({cashpct:.1f}%)",
           f"BUY {len(b)} | CASH floor 15%"]
    if cashpct<5: lines.append("⚠️ Cash tight")
    elif cashpct>25: lines.append("🟡 Cash high – add #1s")
    else: lines.append("🟢 Cash optimal")
    if not b.empty:
        lines.append("Focus : "+", ".join(b["Ticker"]))
    if not new1.empty: lines.append(f"↑ New #1 entries: {len(new1)}")
    if not drop1.empty: lines.append(f"↓ Dropped #1 since prior: {len(drop1)}")
    return "\n".join(lines)

brief_txt=brief(decision,total_value,cash_value,cash_pct)

def exec_plan(dm,total):
    b=dm[dm["Action"]=="🟢 BUY"].copy()
    if b.empty: return b
    order={"Growth 1":1,"Growth 2":2,"Defensive Dividend":3}
    b["Order"]=b["Group"].map(order).fillna(9)
    b.sort_values(["Order","Ticker"],inplace=True)
    b["AllocPct"]=b["Suggested Allocation %"].astype(float)
    b["Alloc$"]=(b["AllocPct"]/100)*total
    b["Alloc$Str"]=b["Alloc$"].apply(lambda x:f"${x:,.2f}")
    b["Seq"]=range(1,len(b)+1)
    return b[["Seq","Ticker","Group","Zacks Rank","Suggested Stop %","AllocPct","Alloc$Str"]]

exec_df=exec_plan(decision,total_value)

# =========================================================
# 7️⃣  STREAMLIT TABS
# =========================================================
tabs=st.tabs([
 "💼 Portfolio Overview","📊 Growth 1","📊 Growth 2","💰 Defensive Dividend",
 "📈 Decision Matrix","🧩 Tactical Summary","📖 Daily Intelligence Brief"
])

# --- Portfolio
with tabs[0]:
    st.subheader("Qualified Plan Holdings – Post-Trade Update")
    st.dataframe(pf,use_container_width=True)
    if not pf.empty and "Value" in pf:
        fig=px.pie(pf,values="Value",names="Ticker",hole=0.3,
                   title="Portfolio Allocation")
        st.plotly_chart(fig,use_container_width=True)
    st.markdown(FOOTER_HTML,unsafe_allow_html=True)

# --- Zacks Tabs
for tab,df,label in [(tabs[1],g1_cur,"Growth 1"),
                     (tabs[2],g2_cur,"Growth 2"),
                     (tabs[3],dd_cur,"Defensive Dividend")]:
    with tab:
        st.subheader(f"Zacks {label} Cross-Match")
        if not df.empty:
            cm=cross_match(df,pf)
            st.dataframe(cm,use_container_width=True)
        else:
            st.info(f"No {label} data found.")
        st.markdown(FOOTER_HTML,unsafe_allow_html=True)

# --- Decision Matrix
with tabs[4]:
    st.subheader("📈 Tactical Decision Matrix")
    if not decision.empty:
        st.dataframe(decision,use_container_width=True)
        st.caption("15% max per #1, 15% cash floor.")
    else: st.info("No signals.")
    st.markdown(FOOTER_HTML,unsafe_allow_html=True)

# --- Tactical Summary
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.write(f"Value ${total_value:,.2f}  Cash ${cash_value:,.2f}")
    if not new1.empty:
        st.markdown("↑ New #1 Entries"); st.dataframe(new1,use_container_width=True)
    if not drop1.empty:
        st.markdown("↓ Dropped #1"); st.dataframe(drop1,use_container_width=True)
    st.markdown(FOOTER_HTML,unsafe_allow_html=True)

# --- Daily Intelligence Brief
with tabs[6]:
    st.subheader("📖 Daily Intelligence Brief – Command Overview")
    st.caption(datetime.datetime.now().strftime("%A %B %d %Y – %I:%M %p CST"))
    st.markdown(f"```text\n{brief_txt}\n```")
    st.markdown("### 🚀 Execution Protocol")
    if not exec_df.empty:
        st.dataframe(exec_df,use_container_width=True)
        total_alloc=exec_df["AllocPct"].sum()
        tot_amt=exec_df["Alloc$"].sum()
        st.markdown(f"**Total Allocation → {total_alloc:.1f}% (~${tot_amt:,.0f})**")
    else: st.info("No BUY signals today.")
    st.markdown(FOOTER_HTML,unsafe_allow_html=True)

# --- Optional Auto-Summary Writer
def write_summary():
    now=datetime.datetime.now()
    f=f"data/tactical_summary_{now:%Y-%m-%d}.md"
    try:
        with open(f,"w",encoding="utf-8") as o:
            o.write("# Fox Valley Tactical Summary\n\n")
            o.write(brief_txt)
    except: pass

t=datetime.datetime.now()
if t.hour==6 and 45<=t.minute<55: write_summary()
