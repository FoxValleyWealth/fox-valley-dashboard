# ============================================================
# 🧭 Fox Valley Intelligence Engine v7.1R – Enterprise Command Deck (Stable, Nov 10 2025)
# ============================================================

import streamlit as st
import pandas as pd
from pathlib import Path
import re, io, datetime, shutil
import plotly.express as px

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.1R – Enterprise Command Deck",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- STYLE ----------
st.markdown("""
<style>
    body {background-color:#0e1117;color:#FAFAFA;}
    [data-testid="stSidebar"] {background-color:#111318;}
    table {color:#FAFAFA;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1️⃣ ENTERPRISE PORTFOLIO LOADER (Auto-Detect + Diagnostics)
# ============================================================

def load_portfolio():
    data_path = Path("data")
    files = sorted(data_path.glob("Portfolio_Positions_*.csv"), key=lambda f: f.stat().st_mtime)
    if not files:
        st.error("⚠️ No portfolio files found in /data.")
        return pd.DataFrame(), 0.0, 0.0, "None"
    latest = files[-1]
    st.sidebar.info(f"📁 Active Portfolio File: {latest.name}")

    # Archive old files
    archive_path = Path("archive")
    archive_path.mkdir(exist_ok=True)
    for old in files[:-1]:
        shutil.move(str(old), archive_path / old.name)

    text = latest.read_text(errors="ignore")
    lines = text.splitlines()
    header_idx = next((i for i, l in enumerate(lines) if l.count(",") >= 3), 0)
    csv_stream = io.StringIO("\n".join(lines[header_idx:]))
    df = pd.read_csv(csv_stream)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]

    # Clean all potential currency fields
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].replace(r"[\$,]", "", regex=True)
            try:
                df[c] = pd.to_numeric(df[c], errors="ignore")
            except Exception:
                pass

    # Detect total/cash/value columns dynamically
    value_candidates = [c for c in df.columns if any(x in c.lower() for x in ["total", "value", "amount", "cash"])]
    total = cash = 0.0
    for c in value_candidates:
        col_sum = pd.to_numeric(df[c], errors="coerce").sum()
        if "cash" in c.lower():
            cash += col_sum
        else:
            total += col_sum

    return df, float(total), float(cash), latest.name

portfolio, total_value, cash_value, active_file = load_portfolio()

# ============================================================
# 2️⃣ AUTO-DETECT ZACKS SCREENS
# ============================================================

def get_latest(pattern):
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated.append((m.group(1), f))
    return str(max(dated)[1]) if dated else None

def safe_read(path):
    if not path:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

G1_PATH = get_latest("zacks_custom_screen_*Growth1*.csv")
G2_PATH = get_latest("zacks_custom_screen_*Growth2*.csv")
DD_PATH = get_latest("zacks_custom_screen_*Defensive*.csv")

g1, g2, dd = safe_read(G1_PATH), safe_read(G2_PATH), safe_read(DD_PATH)

if not (g1.empty and g2.empty and dd.empty):
    st.sidebar.success("✅ Zacks Screens Loaded Successfully")
else:
    st.sidebar.error("⚠️ No Zacks CSVs found in /data.")

# ============================================================
# 3️⃣ NORMALIZE DATA
# ============================================================

def normalize(df):
    if df.empty:
        return df
    tcols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if tcols:
        df.rename(columns={tcols[0]: "Ticker"}, inplace=True)
    if "Zacks Rank" not in df.columns:
        rcols = [c for c in df.columns if "rank" in c.lower()]
        if rcols:
            df.rename(columns={rcols[0]: "Zacks Rank"}, inplace=True)
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

g1, g2, dd = normalize(g1), normalize(g2), normalize(dd)

# ============================================================
# 4️⃣ CROSS-MATCH + INTELLIGENCE
# ============================================================

def cross_match(zdf, pf):
    if zdf.empty or pf.empty or "Ticker" not in pf.columns:
        return pd.DataFrame()
    pf_tickers = pf["Ticker"].astype(str).str.upper()
    zdf["Ticker"] = zdf["Ticker"].astype(str).str.upper()
    m = zdf.copy()
    m["Held?"] = m["Ticker"].apply(lambda t: "✔ Held" if t in pf_tickers.values else "🟢 Candidate")
    return m

def build_intel(pf, g1, g2, dd, cash_val, total_val):
    # Filter out empty or invalid dataframes
    valid = []
    for df in [g1, g2, dd]:
        if not df.empty and "Ticker" in df.columns:
            df = df.reset_index(drop=True).copy()
            valid.append(df)

    # If nothing valid, return empty intelligence safely
    if not valid:
        return {"narrative": "No valid Zacks data detected.", "new": pd.DataFrame(), "held": pd.DataFrame()}

    # Safe concatenation and duplicate cleanup
    combined = pd.concat(valid, ignore_index=True)

    # Guarantee presence of 'Ticker' column
    if "Ticker" not in combined.columns:
        combined["Ticker"] = ""

    # Drop duplicates safely (without unsupported 'errors' arg)
    try:
        combined = combined.drop_duplicates(subset=["Ticker"], inplace=False)
    except Exception:
        combined = combined.loc[:, ~combined.columns.duplicated()]

    # Build tactical intelligence
    held = set(pf["Ticker"].astype(str)) if "Ticker" in pf.columns else set()
    rank_col = "Zacks Rank" if "Zacks Rank" in combined.columns else None

    if rank_col:
        rank1 = combined[combined[rank_col].astype(str) == "1"]
    else:
        rank1 = pd.DataFrame(columns=["Ticker"])

    new1 = rank1[~rank1["Ticker"].isin(held)]
    held1 = rank1[rank1["Ticker"].isin(held)]
    cash_pct = (cash_val / total_val) * 100 if total_val > 0 else 0

    msg = [
        f"Fox Valley Tactical Summary",
        f"• Portfolio Value: ${total_val:,.2f}",
        f"• Cash Available: ${cash_val:,.2f} ({cash_pct:.2f}%)",
        f"• Total #1 Symbols: {len(rank1)}",
        f"• New #1 Candidates: {len(new1)}",
        f"• Held #1 Positions: {len(held1)}"
    ]

    return {"narrative": "\n".join(msg), "new": new1, "held": held1}


intel = build_intel(portfolio, g1, g2, dd, cash_value, total_value)

# ============================================================
# 5️⃣ COMMAND DECK TABS
# ============================================================

tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "⚙️ Tactical Decision Matrix",
    "🧩 Weekly Tactical Summary",
    "📖 Daily Intelligence Brief"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.metric("Total Account Value", f"${total_value:,.2f}")
    st.metric("Cash Available to Trade", f"${cash_value:,.2f}")
    st.dataframe(portfolio, use_container_width=True)
    if not portfolio.empty and "Value" in portfolio.columns:
        fig = px.pie(portfolio, values="Value", names="Ticker", title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    g1m = cross_match(g1, portfolio)
    if not g1m.empty:
        st.dataframe(g1m, use_container_width=True)
    else:
        st.info("No data for Growth 1.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    g2m = cross_match(g2, portfolio)
    if not g2m.empty:
        st.dataframe(g2m, use_container_width=True)
    else:
        st.info("No data for Growth 2.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    ddm = cross_match(dd, portfolio)
    if not ddm.empty:
        st.dataframe(ddm, use_container_width=True)
    else:
        st.info("No data for Defensive Dividend.")

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

# --- Weekly Tactical Summary ---
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
