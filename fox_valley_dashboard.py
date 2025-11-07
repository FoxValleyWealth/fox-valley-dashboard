# ==========================================================
# 🧭 Fox Valley Intelligence Engine v7.0R-Enterprise Restoration Core
# Stable Command Deck — November 07 2025
# ==========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import io, re, datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.0R – Enterprise Restoration Core",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- STYLES ----------
st.markdown("""
<style>
body {background-color:#0e1117;color:#fafafa;}
[data-testid="stSidebar"] {background-color:#111318;}
.rank1 {background-color:#004d00!important;}
.rank2 {background-color:#665c00!important;}
.rank3 {background-color:#663300!important;}
</style>
""", unsafe_allow_html=True)

# ---------- PORTFOLIO LOADER ----------
def load_portfolio():
    files = sorted(Path("data").glob("Portfolio_Positions_*.csv"), key=lambda f: f.stat().st_mtime)
    if not files:
        st.error("⚠️ No portfolio files found in /data.")
        return pd.DataFrame(), 0.0, 0.0

    latest = files[-1]
    raw = latest.read_text(errors="ignore")
    lines = raw.splitlines()
    header_idx = next((i for i,l in enumerate(lines) if "Symbol" in l or "Ticker" in l), 0)
    csv_stream = io.StringIO("\n".join(lines[header_idx:]))
    df = pd.read_csv(csv_stream)

    # remove disclaimer/empty rows
    df = df[df["Symbol"].notna()]

    # clean $ and commas
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].replace(r"[\$,]", "", regex=True)
            try:
                df[c] = pd.to_numeric(df[c])
            except Exception:
                pass

    # detect value column
    val_cols = [c for c in df.columns if "Value" in c or "Total" in c]
    total_value = df[val_cols[0]].sum() if val_cols else 0.0
    cash_mask = df["Symbol"].astype(str).str.contains("CASH|MMKT|MONEY|USD", case=False, na=False)
    cash_value = df.loc[cash_mask, val_cols[0]].sum() if val_cols else 0.0

    st.sidebar.info(f"📁 Active Portfolio File: {latest.name}")
    return df, float(total_value), float(cash_value)

portfolio, total_value, cash_value = load_portfolio()

# ---------- ZACKS LOAD ----------
def get_latest(pattern):
    files = list(Path("data").glob(pattern))
    return str(sorted(files, key=lambda f: f.stat().st_mtime)[-1]) if files else None

def safe_read(path):
    if not path: return pd.DataFrame()
    try: return pd.read_csv(path)
    except Exception: return pd.DataFrame()

G1_PATH = get_latest("zacks_custom_screen_*Growth 1*.csv")
G2_PATH = get_latest("zacks_custom_screen_*Growth 2*.csv")
DD_PATH = get_latest("zacks_custom_screen_*Defensive*.csv")

g1, g2, dd = safe_read(G1_PATH), safe_read(G2_PATH), safe_read(DD_PATH)
if not g1.empty or not g2.empty or not dd.empty:
    st.sidebar.success("✅ Zacks Screens Loaded Successfully")
else:
    st.sidebar.warning("⚠️ No Zacks CSV files found in /data.")

# ---------- NORMALIZATION ----------
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
    if zdf.empty or pf.empty: return pd.DataFrame()
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    pf_t = pf["Symbol"].astype(str)
    m = zdf.merge(pf_t, left_on="Ticker", right_on="Symbol", how="left", indicator=True)
    m["Held?"] = m["_merge"].map({"both":"✔ Held","left_only":"🟢 Candidate"})
    return m.drop(columns=["_merge"])

g1, g2, dd = normalize(g1), normalize(g2), normalize(dd)

# ---------- INTELLIGENCE CORE ----------
def build_intel(pf, g1, g2, dd, cash_val, total_val):
    combined = pd.concat([g1,g2,dd], ignore_index=True).drop_duplicates(subset=["Ticker"], ignore_index=True)
    held = set(pf["Symbol"].astype(str)) if not pf.empty else set()
    rank1 = combined[combined["Zacks Rank"].astype(str)=="1"] if "Zacks Rank" in combined else pd.DataFrame()
    new1 = rank1[~rank1["Ticker"].isin(held)]
    held1 = rank1[rank1["Ticker"].isin(held)]
    cash_pct = (cash_val/total_val*100) if total_val else 0
    msg = [
        "Fox Valley Daily Tactical Overlay",
        f"• Portfolio Value: ${total_val:,.2f}",
        f"• Cash Available: ${cash_val:,.2f} ({cash_pct:.2f}%)",
        f"• Total #1 Symbols: {len(rank1)}",
        f"• New #1 Candidates: {len(new1)}",
        f"• Held #1 Positions: {len(held1)}"
    ]
    return {"narrative":"\n".join(msg),"new":new1,"held":held1}

intel = build_intel(portfolio,g1,g2,dd,cash_value,total_value)

# ---------- INTERFACE ----------
tabs = st.tabs([
    "💼 Portfolio Overview","📊 Growth 1","📊 Growth 2",
    "💰 Defensive Dividend","⚙️ Tactical Decision Matrix",
    "🧩 Weekly Tactical Summary","📖 Daily Intelligence Brief"
])

with tabs[0]:
    st.metric("Total Account Value", f"${total_value:,.2f}")
    st.metric("Cash Available to Trade", f"${cash_value:,.2f}")
    st.dataframe(portfolio,use_container_width=True)
    if not portfolio.empty:
        valcol = [c for c in portfolio.columns if "Value" in c or "Total" in c]
        if valcol:
            fig = px.pie(portfolio, values=valcol[0], names="Symbol", title="Portfolio Allocation", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

def display_rank(df):
    if df.empty: st.info("No data."); return
    subset = ["Zacks Rank"] if "Zacks Rank" in df.columns else []
    st.dataframe(df.style.map(
        lambda v: "background-color:#004d00" if str(v)=="1"
        else "background-color:#665c00" if str(v)=="2"
        else "background-color:#663300" if str(v)=="3" else "",
        subset=subset
    ), use_container_width=True)

with tabs[1]: st.subheader("Zacks Growth 1 Cross-Match"); display_rank(cross_match(g1,portfolio))
with tabs[2]: st.subheader("Zacks Growth 2 Cross-Match"); display_rank(cross_match(g2,portfolio))
with tabs[3]: st.subheader("Zacks Defensive Dividend Cross-Match"); display_rank(cross_match(dd,portfolio))

with tabs[4]:
    st.subheader("⚙️ Tactical Decision Matrix – Buy / Hold / Trim")
    st.markdown("""
    | Signal | Meaning |
    |:--|:--|
    |🟢 Buy|Zacks Rank #1 new candidates not held|
    |⚪ Hold|Existing positions that remain #1|
    |🟠 Trim|Existing positions that lost #1|
    """)

with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.text(intel["narrative"])

with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.caption(f"Generated {datetime.datetime.now():%A, %B %d, %Y – %I:%M %p CST}")
    st.markdown("### 🟢 New #1 Candidates")
    display_rank(intel["new"])
    st.markdown("### ✔ Held #1 Positions")
    display_rank(intel["held"])
