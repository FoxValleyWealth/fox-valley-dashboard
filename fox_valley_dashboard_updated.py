# ============================================
# FOX VALLEY TACTICAL DASHBOARD v4.3 – Nov 2025
# Full Automation • Daily Intelligence • Debug Preview
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Tactical Dashboard v4.3",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- DARK MODE ----------
st.markdown("""
<style>
body{background-color:#0e1117;color:#FAFAFA;}
[data-testid="stHeader"]{background-color:#0e1117;}
[data-testid="stSidebar"]{background-color:#111318;}
table{color:#FAFAFA;}
.rank1{background-color:#004d00!important;}
.rank2{background-color:#665c00!important;}
.rank3{background-color:#663300!important;}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["Ticker"] = df["Ticker"].astype(str)
    return df

portfolio = load_portfolio()
total_value = portfolio["Value"].sum()
cash_row = portfolio[portfolio["Ticker"].str.contains("SPAXX", na=False)]
cash_value = cash_row["Value"].sum()

# ---------- AUTO-DETECT ZACKS FILES ----------
DATE_RX = re.compile(r"(\d{4}-\d{2}-\d{2})")

def _find_latest(patterns):
    found = []
    for pat in patterns:
        for p in Path("data").glob(pat):
            m = DATE_RX.search(p.name)
            if m: found.append((m.group(1), p))
    if not found: return None
    found.sort(key=lambda t: t[0])
    return str(found[-1][1])

G1_PATH = _find_latest(["zacks_custom_screen_*growth*1*.csv", "zacks_custom_screen_*Growth*1*.csv"])
G2_PATH = _find_latest(["zacks_custom_screen_*growth*2*.csv", "zacks_custom_screen_*Growth*2*.csv"])
DD_PATH = _find_latest(["zacks_custom_screen_*defensive*dividend*.csv", "zacks_custom_screen_*Defensive*Dividend*.csv"])

def safe_read(path):
    try:
        return pd.read_csv(path) if path else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

g1_raw, g2_raw, dd_raw = map(safe_read, [G1_PATH, G2_PATH, DD_PATH])

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No Zacks CSVs found in /data")

# ---------- NORMALIZATION + CROSSMATCH ----------
def normalize(df):
    if df.empty: return df
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    ticker = next((c for c in df.columns if "ticker" in c or "symbol" in c), None)
    rank = next((c for c in df.columns if "rank" in c), None)
    out = pd.DataFrame()
    if ticker: out["Ticker"] = df[ticker].astype(str)
    if rank: out["Zacks Rank"] = pd.to_numeric(df[rank], errors="coerce")
    return out

def cross_match(zdf, pf):
    if zdf.empty: return pd.DataFrame(columns=["Ticker","Zacks Rank","Held?"])
    pf_tk = pf[["Ticker"]].astype(str)
    merged = zdf.merge(pf_tk, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both":"✔ Held","left_only":"🟢 Candidate"})
    return merged.drop(columns="_merge")

g1, g2, dd = map(normalize, [g1_raw, g2_raw, dd_raw])

# ---------- INTELLIGENCE ENGINE ----------
def intel_report(portfolio, g1, g2, dd):
    combined = pd.concat([g1, g2, dd], ignore_index=True).drop_duplicates(subset=["Ticker"])
    combined["Zacks Rank"] = pd.to_numeric(combined["Zacks Rank"], errors="coerce")
    held = set(portfolio["Ticker"])
    rank1 = combined[combined["Zacks Rank"] == 1]
    new1 = rank1[~rank1["Ticker"].isin(held)]
    held1 = rank1[rank1["Ticker"].isin(held)]
    cash_pct = (cash_value / total_value)*100 if total_value else 0
    text = [
        f"Portfolio Value: ${total_value:,.2f}",
        f"Cash (SPAXX): ${cash_value:,.2f} ({cash_pct:.1f}%)",
        f"Detected Rank #1s: {len(rank1)}  New: {len(new1)}  Held: {len(held1)}"
    ]
    if cash_pct<5: text.append("⚠️ Low cash — limited buy flexibility.")
    elif cash_pct>25: text.append("🟡 High cash — review deployment.")
    else: text.append("🟢 Cash balanced for tactical moves.")
    return {"combined":combined,"new1":new1,"held1":held1,"text":"\n".join(text),"cash_pct":cash_pct}

intel = intel_report(portfolio,g1,g2,dd)

# ---------- MAIN TABS ----------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "🧩 Tactical Summary",
    "📖 Daily Intelligence Brief",
    "🧾 Debug Preview"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty:
        st.plotly_chart(px.pie(portfolio, values="Value", names="Ticker",
                               title="Portfolio Allocation", hole=0.3),
                        use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m = cross_match(g1,portfolio)
    st.dataframe(g1m,use_container_width=True) if not g1m.empty else st.info("No data found.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m = cross_match(g2,portfolio)
    st.dataframe(g2m,use_container_width=True) if not g2m.empty else st.info("No data found.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm = cross_match(dd,portfolio)
    st.dataframe(ddm,use_container_width=True) if not ddm.empty else st.info("No data found.")

# --- Tactical Summary ---
with tabs[4]:
    st.subheader("🧩 Weekly Tactical Summary")
    portfolio["GainLoss%"]=pd.to_numeric(portfolio["GainLoss%"],errors="coerce")
    st.metric("Total Value",f"${total_value:,.2f}")
    st.metric("Avg Gain/Loss %",f"{portfolio['GainLoss%'].mean():.2f}%")
    st.markdown("**Top 3 Gainers**")
    st.dataframe(portfolio.nlargest(3,"GainLoss%")[["Ticker","GainLoss%"]])
    st.markdown("**Top 3 Decliners**")
    st.dataframe(portfolio.nsmallest(3,"GainLoss%")[["Ticker","GainLoss%"]])

# --- Daily Intelligence Brief ---
with tabs[5]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.code(intel["text"])
    st.markdown("### 🟢 New Rank #1 Candidates (not held)")
    st.dataframe(intel["new1"]) if not intel["new1"].empty else st.info("No new Rank #1 stocks today.")
    st.markdown("### ✔ Held Positions Still Rank #1")
    st.dataframe(intel["held1"]) if not intel["held1"].empty else st.info("None remain Rank #1 today.")
    st.markdown("### 📋 Full Combined Zacks Universe")
    st.dataframe(intel["combined"]) if not intel["combined"].empty else st.info("Upload Zacks files to populate.")

# --- Debug Preview ---
with tabs[6]:
    st.subheader("🧾 Debug Preview – File Detection & Validation")
    base = Path("data")
    files = sorted([str(p) for p in base.glob("zacks_custom_screen_*.csv")])
    st.markdown("**All CSV files in /data:**")
    st.code("\n".join(files) if files else "No files found.")
    st.markdown(f"**Growth 1 →** {G1_PATH or 'Not detected'}")
    st.markdown(f"**Growth 2 →** {G2_PATH or 'Not detected'}")
    st.markdown(f"**Defensive Dividend →** {DD_PATH or 'Not detected'}")

    for label,df in [("Growth 1",g1_raw),("Growth 2",g2_raw),("Defensive Dividend",dd_raw)]:
        st.markdown(f"### {label} – Preview")
        if df.empty: st.warning("Empty or unreadable file.")
        else: st.dataframe(df.head(10))

    for label,df in [("Growth 1",g1),("Growth 2",g2),("Defensive Dividend",dd)]:
        st.markdown(f"**{label} Rank #1 count:** {(df['Zacks Rank']==1).sum() if 'Zacks Rank' in df else 0}**")

# --- Auto-Generate Weekly Markdown Summary (Sundays 07:00 CST) ---
def write_summary():
    now=datetime.datetime.now()
    fname=f"data/tactical_summary_{now:%Y-%m-%d}.md"
    with open(fname,"w",encoding="utf-8") as f:
        f.write(f"# Fox Valley Tactical Summary – {now:%B %d, %Y}\n\n")
        f.write(intel["text"])
    st.success(f"Summary exported → {fname}")

now=datetime.datetime.now()
if now.weekday()==6 and now.hour==7:
    write_summary()
