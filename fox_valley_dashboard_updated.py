# ============================================
# FOX VALLEY TACTICAL DASHBOARD v4.2 – Nov 2025
# Daily Intelligence + Robust Zacks Loader (spaces/underscores) + Debug Preview (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Tactical Dashboard v4.2 – Daily Intelligence",
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
    # Ticker as string for safe merges
    df["Ticker"] = df["Ticker"].astype(str)
    return df

portfolio = load_portfolio()
total_value = portfolio["Value"].sum()
cash_row = portfolio[portfolio["Ticker"].str.contains("SPAXX", na=False)]
cash_value = cash_row["Value"].sum()

# ---------- ROBUST ZACKS FILE DISCOVERY ----------
# Handles both:
#   zacks_custom_screen_2025-11-03_Growth1.csv  (underscores)
#   zacks_custom_screen_2025-11-03 Growth 1.csv (spaces)
DATE_RX = re.compile(r"(\d{4}-\d{2}-\d{2})")

def list_zacks_files():
    base = Path("data")
    # accept .csv with any spaces/underscores after the date
    return list(base.glob("zacks_custom_screen_*[Gg]rowth*1*.csv")) + \
           list(base.glob("zacks_custom_screen_*[Gg]rowth*2*.csv")) + \
           list(base.glob("zacks_custom_screen_*[Dd]efensive*Dividend*.csv")) + \
           list(base.glob("zacks_custom_screen_*[Dd]efensive*Dividends*.csv"))

def _pick_latest(paths, kind_hint):
    """Pick the latest file by date for a given kind (growth1/growth2/defensive)."""
    candidates = []
    for p in paths:
        name = p.name.lower()
        if kind_hint == "g1" and ("growth1" in name or "growth 1" in name):
            m = DATE_RX.search(name)
            if m: candidates.append((m.group(1), p))
        elif kind_hint == "g2" and ("growth2" in name or "growth 2" in name):
            m = DATE_RX.search(name)
            if m: candidates.append((m.group(1), p))
        elif kind_hint == "dd" and ("defens" in name and "dividend" in name):
            m = DATE_RX.search(name)
            if m: candidates.append((m.group(1), p))
    if not candidates:
        return None
    # pick max date lexicographically (YYYY-MM-DD works)
    candidates.sort(key=lambda t: t[0])
    return str(candidates[-1][1])

def discover_latest_files():
    all_paths = list_zacks_files()
    g1 = _pick_latest(all_paths, "g1")
    g2 = _pick_latest(all_paths, "g2")
    dd = _pick_latest(all_paths, "dd")
    return g1, g2, dd, all_paths

def safe_read(path: str | None):
    if path is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        return df
    except Exception:
        return pd.DataFrame()

G1_PATH, G2_PATH, DD_PATH, ALL_FOUND = discover_latest_files()
g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

# ---------- SIDEBAR STATUS ----------
if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Latest Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data. Check filenames or headers.")

# ---------- NORMALIZE + CROSSMATCH ----------
def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    df = df.copy()

    # Normalize column names
    cols_lower = {c: c.lower() for c in df.columns}
    df.rename(columns={k: v for k, v in cols_lower.items()}, inplace=True)

    # Find ticker column
    ticker_col = None
    for key in ["ticker", "symbol", "ticker symbol", "tk"]:
        if key in df.columns:
            ticker_col = key
            break
    if ticker_col is None:
        # fallback: first column often is company/ticker; try to detect short uppercase strings
        for c in df.columns:
            if df[c].astype(str).str.match(r"^[A-Z.\-]{1,6}$").sum() > 0:
                ticker_col = c
                break

    # Find zacks rank column
    rank_col = None
    for key in ["zacks rank", "zacksrank", "rank", "zacks_rank"]:
        if key in df.columns:
            rank_col = key
            break

    out = pd.DataFrame()
    if ticker_col is not None:
        out["Ticker"] = df[ticker_col].astype(str)
    if rank_col is not None:
        # coerce to numeric if possible
        out["Zacks Rank"] = pd.to_numeric(df[rank_col], errors="coerce")
    return out

def cross_match(zdf: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    if zdf.empty:
        return pd.DataFrame(columns=["Ticker", "Zacks Rank", "Held?"])
    pf_tickers = pf[["Ticker"]].astype(str)
    zdf = zdf.copy()
    zdf["Ticker"] = zdf["Ticker"].astype(str)
    merged = zdf.merge(pf_tickers, on="Ticker", how="left", indicator=True)
    merged["Held?"] = merged["_merge"].map({"both": "✔ Held", "left_only": "🟢 Candidate"})
    merged.drop(columns=["_merge"], inplace=True)
    return merged

g1 = normalize_zacks(g1_raw)
g2 = normalize_zacks(g2_raw)
dd = normalize_zacks(dd_raw)

# ---------- INTELLIGENCE ENGINE ----------
def build_intel_overlay(portfolio_df: pd.DataFrame,
                        g1_df: pd.DataFrame,
                        g2_df: pd.DataFrame,
                        dd_df: pd.DataFrame,
                        cash_val: float,
                        total_val: float) -> dict:
    combined = pd.concat([g1_df, g2_df, dd_df], axis=0, ignore_index=True)
    if not combined.empty:
        combined["Zacks Rank"] = pd.to_numeric(combined.get("Zacks Rank"), errors="coerce")
        combined = combined.drop_duplicates(subset=["Ticker"])
    held_tickers = set(portfolio_df["Ticker"].astype(str))
    rank1 = combined[combined["Zacks Rank"] == 1] if not combined.empty else pd.DataFrame()
    new_rank1 = rank1[~rank1["Ticker"].isin(held_tickers)] if not rank1.empty else pd.DataFrame()
    held_rank1 = rank1[rank1["Ticker"].isin(held_tickers)] if not rank1.empty else pd.DataFrame()

    cash_pct = (cash_val / total_val) * 100 if total_val > 0 else 0

    # Narrative
    pieces = []
    pieces.append("Fox Valley Tactical Intelligence – Daily Overlay")
    pieces.append(f"- Portfolio value: ${total_val:,.2f}")
    pieces.append(f"- Cash on hand (SPAXX): ${cash_val:,.2f} ({cash_pct:.2f}%)")
    if not combined.empty:
        pieces.append(f"- Zacks Rank #1 symbols detected today: {0 if rank1.empty else len(rank1)}")
        pieces.append(f"- New #1s not held: {0 if new_rank1.empty else len(new_rank1)}")
        pieces.append(f"- Held still #1: {0 if held_rank1.empty else len(held_rank1)}")
    else:
        pieces.append("- No valid Zacks rows detected. Check headers or file format.")

    if cash_pct < 5:
        pieces.append("⚠️ Cash is tight — avoid overcommitting unless signal is very strong.")
    elif cash_pct > 25:
        pieces.append("🟡 Cash elevated — consider deploying into top new #1s or defensive dividends.")
    else:
        pieces.append("🟢 Cash in tactical range — standard buy/trims can be executed.")

    narrative = "\n".join(pieces)
    return {
        "narrative": narrative,
        "combined": combined,
        "new_rank1": new_rank1,
        "held_rank1": held_rank1,
        "cash_pct": cash_pct
    }

intel = build_intel_overlay(portfolio, g1, g2, dd, cash_value, total_value)

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
        fig = px.pie(portfolio, values="Value", names="Ticker",
                     title="Portfolio Allocation", hole=0.3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No portfolio data found in /data/portfolio_data.csv")

# --- Growth 1 ---
with tabs[1]:
    st.subheader("Zacks Growth 1 Cross-Match")
    if not g1.empty:
        g1m = cross_match(g1, portfolio)
        st.dataframe(
            g1m.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No valid Zacks Growth 1 data detected.")

# --- Growth 2 ---
with tabs[2]:
    st.subheader("Zacks Growth 2 Cross-Match")
    if not g2.empty:
        g2m = cross_match(g2, portfolio)
        st.dataframe(
            g2m.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No valid Zacks Growth 2 data detected.")

# --- Defensive Dividend ---
with tabs[3]:
    st.subheader("Zacks Defensive Dividend Cross-Match")
    if not dd.empty:
        ddm = cross_match(dd, portfolio)
        st.dataframe(
            ddm.style.map(
                lambda v: "background-color: #004d00" if str(v) == "1"
                else "background-color: #665c00" if str(v) == "2"
                else "background-color: #663300" if str(v) == "3"
                else "",
                subset=["Zacks Rank"]
            ),
            use_container_width=True
        )
    else:
        st.info("No valid Zacks Defensive Dividend data detected.")

# --- Tactical Summary (weekly view retained) ---
with tabs[4]:
    st.subheader("🧩 Weekly Tactical Summary – Automated Intelligence")
    portfolio["GainLoss%"] = pd.to_numeric(portfolio["GainLoss%"], errors="coerce")
    avg_gain = portfolio["GainLoss%"].mean()
    st.metric("Total Value", f"${total_value:,.2f}")
    st.metric("Avg Gain/Loss %", f"{avg_gain:.2f}%")

    st.markdown("**Top 3 Gainers**")
    st.dataframe(portfolio.nlargest(3, "GainLoss%")[["Ticker", "GainLoss%"]])
    st.markdown("**Top 3 Decliners**")
    st.dataframe(portfolio.nsmallest(3, "GainLoss%")[["Ticker", "GainLoss%"]])

    st.markdown("---")
    st.markdown("### 🧠 Tactical Intelligence Feed")
    combined = intel["combined"]
    if not combined.empty:
        held = combined.merge(portfolio[["Ticker"]], on="Ticker", how="inner")
        newc = combined[~combined["Ticker"].isin(portfolio["Ticker"])]
        st.markdown("**🟢 New Zacks Rank #1 Candidates:**")
        st.dataframe(newc, use_container_width=True)
        st.markdown("**✔ Held Positions Still Active (#1):**")
        st.dataframe(held, use_container_width=True)
    else:
        st.info("Zacks data unavailable for tactical analysis.")

    cash_pct = intel["cash_pct"]
    st.markdown("---")
    st.metric("Cash (SPAXX)", f"${cash_value:,.2f}")
    st.metric("Cash % of Account", f"{cash_pct:.2f}%")

    if cash_pct < 5:
        st.warning("⚠️ Low cash reserves — limited buy power.")
    elif cash_pct > 25:
        st.info("🟡 Elevated cash — consider redeployment.")
    else:
        st.success("🟢 Balanced liquidity for tactical flexibility.")

# --- Daily Intelligence Brief ---
with tabs[5]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.markdown("#### 🧠 AI Tactical Narrative")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    now_str = datetime.datetime.now().strftime("%A, %B %d, %Y – %I:%M %p CST")
    st.caption(f"Generated: {now_str}")

    st.markdown("### 🟢 New Zacks Rank #1 Candidates (Not Currently Held)")
    if not intel["new_rank1"].empty:
        st.dataframe(intel["new_rank1"], use_container_width=True)
    else:
        st.info("No NEW Rank #1 candidates outside current holdings today.")

    st.markdown("### ✔ Held Positions Still Zacks #1")
    if not intel["held_rank1"].empty:
        st.dataframe(intel["held_rank1"], use_container_width=True)
    else:
        st.info("None of the current holdings are Rank #1 in today’s screens.")

    st.markdown("### 📋 Full Combined Zacks View (Growth1 + Growth2 + Defensive)")
    if not intel["combined"].empty:
        st.dataframe(intel["combined"], use_container_width=True)
    else:
        st.info("Upload today’s Zacks files to populate this view.")

# --- Debug Preview ---
with tabs[6]:
    st.subheader("🧾 Debug Preview – Zacks File Detection & Contents")

    # 1) Show all files found in /data matching zacks_custom_screen_*
    st.markdown("**All matching files in `/data`:**")
    if ALL_FOUND:
        st.code("\n".join(sorted([str(p) for p in ALL_FOUND])))
    else:
        st.warning("No files found matching `zacks_custom_screen_*`. Check names and location.")

    # 2) Show which file was selected for each category
    colA, colB, colC = st.columns(3)
    colA.metric("Growth 1 path", G1_PATH if G1_PATH else "Not detected")
    colB.metric("Growth 2 path", G2_PATH if G2_PATH else "Not detected")
    colC.metric("Defensive path", DD_PATH if DD_PATH else "Not detected")

    # 3) Preview heads and schema for each raw CSV
    def preview_df(label, path, df):
        st.markdown(f"#### {label}")
        if path is None:
            st.info("No file detected.")
            return
        st.caption(f"Path: `{path}`  •  Rows: {len(df)}  •  Columns: {list(df.columns)}")
        if df.empty:
            st.warning("Loaded empty or unreadable CSV — check delimiter, headers, or file format.")
        else:
            st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")
    preview_df("Growth 1 (raw)", G1_PATH, g1_raw)
    preview_df("Growth 2 (raw)", G2_PATH, g2_raw)
    preview_df("Defensive Dividend (raw)", DD_PATH, dd_raw)

    # 4) Rank-1 counts & candidate breakdown
    def rank1_summary(label, df_norm):
        st.markdown(f"**{label} – Rank #1 Summary**")
        if df_norm.empty or "Zacks Rank" not in df_norm.columns:
            st.info("No normalized data or no 'Zacks Rank' column detected.")
            return
        dfn = df_norm.copy()
        dfn["Zacks Rank"] = pd.to_numeric(dfn["Zacks Rank"], errors="coerce")
        r1 = dfn[dfn["Zacks Rank"] == 1]
        st.write(f"- Total rows: {len(dfn)}")
        st.write(f"- Rank #1 rows: {len(r1)}")
        if not r1.empty:
            st.write("- Rank #1 tickers:")
            st.code(", ".join(sorted(r1["Ticker"].astype(str).unique())))
        else:
            st.info("No Rank #1 entries in this file.")

    st.markdown("---")
    rank1_summary("Growth 1", g1)
    rank1_summary("Growth 2", g2)
    rank1_summary("Defensive Dividend", dd)

    # 5) New #1s vs Held #1s preview
    if not intel["combined"].empty:
        st.markdown("**Combined NEW #1 vs HELD #1 breakdown**")
        if not intel["new_rank1"].empty:
            st.markdown("🟢 **New (not held)**")
            st.code(", ".join(sorted(intel["new_rank1"]["Ticker"].astype(str).unique())))
        else:
            st.info("No NEW #1s (not held).")
        if not intel["held_rank1"].empty:
            st.markdown("✔ **Held (still #1)**")
            st.code(", ".join(sorted(intel["held_rank1"]["Ticker"].astype(str).unique())))
        else:
            st.info("No HELD #1s today.")
    else:
        st.info("Combined Zacks set is empty — check headers/columns.")

# --- Automated Tactical Summary File Generation ---
def generate_tactical_summary():
    now = datetime.datetime.now()
    fname = f"data/tactical_summary_{now.strftime('%Y-%m-%d')}.md"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# Fox Valley Tactical Summary – {now:%B %d, %Y}\n")
            f.write(f"**Total Value:** ${total_value:,.2f}\n")
            f.write(f"**Cash:** ${cash_value:,.2f}\n\n")
            f.write("## Tactical Intelligence\n")
            f.write(intel["narrative"])
            f.write("\n\n## Notes\n")
            f.write("- Generated automatically by Fox Valley Tactical Dashboard v4.2\n")
        st.success(f"Tactical summary exported → {fname}")
    except Exception as e:
        st.error(f"Failed to write tactical summary: {e}")

# --- Auto-Run at 06:45 AM Daily ---
now = datetime.datetime.now()
if now.hour == 6 and 45 <= now.minute < 55:
    generate_tactical_summary()
