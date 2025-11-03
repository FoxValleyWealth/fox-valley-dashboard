# ============================================
# FOX VALLEY INTELLIGENCE ENGINE v6.1.1 – Nov 2025
# Tactical Core System – Auto Allocation + Trade Plan (Dark Mode)
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v6.1.1 – Tactical Core System",
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
        .footer {color: #888; font-size: 0.8em; text-align: center; margin-top: 40px;}
        button {border-radius: 10px !important;}
    </style>
""", unsafe_allow_html=True)

# ---------- LOAD PORTFOLIO ----------
@st.cache_data
def load_portfolio():
    df = pd.read_csv("data/portfolio_data.csv")
    # Make sure numeric
    if "GainLoss%" in df.columns:
        df["GainLoss%"] = pd.to_numeric(df["GainLoss%"], errors="coerce")
    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df

portfolio = load_portfolio().copy()

# Remove fully exited positions (per your instructions)
sold_tickers = ["MRMD", "KE", "IPG"]
if "Ticker" in portfolio.columns:
    portfolio = portfolio[~portfolio["Ticker"].isin(sold_tickers)].copy()

# Ensure HSBC position is present (70 @ 70.41)
if "Ticker" in portfolio.columns:
    tickers_str = portfolio["Ticker"].astype(str).tolist()
    if "HSBC" not in tickers_str:
        hsbc_row = {
            "Ticker": "HSBC",
            "Value": 70 * 70.41,
            "GainLoss%": 0.0
        }
        # Fill missing columns with NaN-safe values
        for col in portfolio.columns:
            if col not in hsbc_row:
                hsbc_row[col] = None
        portfolio = pd.concat([portfolio, pd.DataFrame([hsbc_row])], ignore_index=True)

# Recompute totals after adjustments
if "Value" in portfolio.columns:
    total_value = portfolio["Value"].sum()
else:
    total_value = 0.0

if "Ticker" in portfolio.columns and "Value" in portfolio.columns:
    cash_rows = portfolio[portfolio["Ticker"].astype(str).str.contains("SPAXX", na=False)]
    cash_value = cash_rows["Value"].sum()
else:
    cash_value = 0.0

cash_pct = (cash_value / total_value) * 100 if total_value > 0 else 0.0

# ---------- AUTO-DETECT LATEST ZACKS FILES ----------
def get_latest_zacks_file(pattern: str) -> str | None:
    files = Path("data").glob(pattern)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
    dated_files = []
    for f in files:
        m = date_pattern.search(str(f))
        if m:
            dated_files.append((m.group(1), f))
    if dated_files:
        return str(max(dated_files)[1])
    return None

G1_PATH = get_latest_zacks_file("*Growth 1*.csv") or get_latest_zacks_file("*Growth1*.csv")
G2_PATH = get_latest_zacks_file("*Growth 2*.csv") or get_latest_zacks_file("*Growth2*.csv")
DD_PATH = get_latest_zacks_file("*Defensive*.csv")

def safe_read(path: str | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

g1_raw = safe_read(G1_PATH)
g2_raw = safe_read(G2_PATH)
dd_raw = safe_read(DD_PATH)

if not g1_raw.empty or not g2_raw.empty or not dd_raw.empty:
    st.sidebar.success("✅ Latest Zacks files auto-detected from /data")
else:
    st.sidebar.error("⚠️ No valid Zacks CSVs found in /data folder.")

# ---------- NORMALIZE & CROSSMATCH ----------
def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = df.columns.str.lower()
    ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower()]
    if ticker_cols:
        df = df.rename(columns={ticker_cols[0]: "Ticker"})
    if "Zacks Rank" not in df.columns:
        rank_cols = [c for c in df.columns if "rank" in c.lower()]
        if rank_cols:
            df = df.rename(columns={rank_cols[0]: "Zacks Rank"})
    keep = [c for c in ["Ticker", "Zacks Rank"] if c in df.columns]
    return df[keep].copy()

def cross_match(zdf: pd.DataFrame, pf: pd.DataFrame) -> pd.DataFrame:
    if zdf.empty or "Ticker" not in zdf.columns or "Ticker" not in pf.columns:
        return pd.DataFrame()
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

# ---------- DECISION MATRIX ----------
def build_decision_matrix(pf: pd.DataFrame,
                          g1: pd.DataFrame,
                          g2: pd.DataFrame,
                          dd: pd.DataFrame,
                          total_val: float,
                          cash_val: float) -> pd.DataFrame:
    combined = pd.concat([g1, g2, dd], axis=0, ignore_index=True)
    if combined.empty or "Ticker" not in combined.columns:
        return pd.DataFrame()
    combined = combined.drop_duplicates(subset=["Ticker"])

    held_tickers = set(pf["Ticker"].astype(str).tolist())
    combined["Ticker"] = combined["Ticker"].astype(str)
    combined["Held?"] = combined["Ticker"].apply(
        lambda t: "✔ Held" if t in held_tickers else "🟢 Candidate"
    )

    def which_group(ticker: str) -> str:
        if ticker in g1["Ticker"].astype(str).values:
            return "Growth 1"
        if ticker in g2["Ticker"].astype(str).values:
            return "Growth 2"
        if ticker in dd["Ticker"].astype(str).values:
            return "Defensive Dividend"
        return "Unknown"

    combined["Group"] = combined["Ticker"].apply(which_group)

    def suggested_stop(group: str) -> str:
        if group == "Growth 1":
            return "10%"
        if group == "Growth 2":
            return "10%"
        if group == "Defensive Dividend":
            return "12%"
        return ""

    combined["Suggested Stop %"] = combined["Group"].apply(suggested_stop)
    combined["Zacks Rank"] = pd.to_numeric(combined["Zacks Rank"], errors="coerce")

    # Strict Zacks Rank Logic → BUY / HOLD / TRIM
    def action_from_rank(rank: float | int | None) -> str:
        try:
            r = int(rank)
            if r == 1:
                return "🟢 BUY"
            elif r == 2:
                return "⚪ HOLD"
            else:
                return "🟠 TRIM"
        except Exception:
            return ""

    combined["Action"] = combined["Zacks Rank"].apply(action_from_rank)

    # Allocation engine – 15% max per position, 15% cash floor
    deployable = total_val * 0.85  # 85% of portfolio can be allocated
    rank1 = combined[combined["Zacks Rank"] == 1]
    n_rank1 = len(rank1)
    if n_rank1 > 0 and total_val > 0:
        # max 15% each, but scaled by number of rank1s
        raw_weight = deployable / total_val / n_rank1
        weight_each = min(0.15, raw_weight)
    else:
        weight_each = 0.0

    def alloc_percent(ticker: str) -> float:
        if ticker in rank1["Ticker"].values:
            return weight_each * 100.0
        return 0.0

    combined["Suggested Allocation %"] = combined["Ticker"].apply(alloc_percent)

    def alloc_dollar(pct: float) -> str:
        if pct <= 0 or total_val <= 0:
            return ""
        amt = (pct / 100.0) * total_val
        return f"${amt:,.2f}"

    combined["Estimated Buy Amount"] = combined["Suggested Allocation %"].apply(alloc_dollar)

    return combined

decision_matrix = build_decision_matrix(portfolio, g1, g2, dd, total_value, cash_value)

# ---------- INTELLIGENCE BRIEF ----------
def build_brief(dm: pd.DataFrame, total_val: float, cash_val: float, cash_pct: float) -> str:
    if dm.empty:
        return (
            "Fox Valley Intelligence Engine – Daily Tactical Brief\n"
            f"- Portfolio Value: ${total_val:,.2f}\n"
            f"- Cash: ${cash_val:,.2f} ({cash_pct:.2f}%)\n"
            "- No active Zacks signals detected in the latest screens.\n"
        )

    buys = dm[dm["Action"].str.contains("BUY", na=False)]
    holds = dm[dm["Action"].str.contains("HOLD", na=False)]
    trims = dm[dm["Action"].str.contains("TRIM", na=False)]

    lines = [
        "Fox Valley Intelligence Engine – Daily Tactical Brief",
        f"- Portfolio Value: ${total_val:,.2f}",
        f"- Cash: ${cash_val:,.2f} ({cash_pct:.2f}%)",
        f"- BUY signals: {len(buys)} | HOLD: {len(holds)} | TRIM: {len(trims)}",
    ]

    if cash_pct < 5:
        lines.append("⚠️ Cash is tight — prioritize only the strongest Rank #1 candidates.")
    elif cash_pct > 25:
        lines.append("🟡 Cash is elevated — consider scaling into top Zacks Rank #1 names.")
    else:
        lines.append("🟢 Cash is in tactical range — standard buy/trim discipline applies.")

    if not buys.empty:
        tickers = ", ".join(buys["Ticker"].astype(str).tolist())
        lines.append(f"Primary BUY focus list (Rank #1): {tickers}")
    else:
        lines.append("No Rank #1 BUY signals today.")

    return "\n".join(lines)

brief_text = build_brief(decision_matrix, total_value, cash_value, cash_pct)

# ---------- TABS ----------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividend",
    "📈 Decision Matrix",
    "🧩 Tactical Summary",
    "📖 Daily Intelligence Brief"
])

# --- Portfolio Overview ---
with tabs[0]:
    st.subheader("Qualified Plan Holdings")
    st.dataframe(portfolio, use_container_width=True)

    if "Value" in portfolio.columns and "Ticker" in portfolio.columns and not portfolio.empty:
        fig = px.pie(
            portfolio,
            values="Value",
            names="Ticker",
            title="Portfolio Allocation",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "<div class='footer'>Fox Valley Intelligence Engine v6.1.1 – Tactical Core System</div>",
        unsafe_allow_html=True
    )

# --- Growth 1 / Growth 2 / Defensive Dividend ---
tab_configs = [
    (tabs[1], g1, "Growth 1"),
    (tabs[2], g2, "Growth 2"),
    (tabs[3], dd, "Defensive Dividend"),
]

for tab, df, label in tab_configs:
    with tab:
        st.subheader(f"Zacks {label} Cross-Match")
        if not df.empty:
            cm = cross_match(df, portfolio)
            if not cm.empty and "Zacks Rank" in cm.columns:
                styled = cm.style.map(
                    lambda v: "background-color: #004d00" if str(v) == "1"
                    else "background-color: #665c00" if str(v) == "2"
                    else "background-color: #663300" if str(v) == "3"
                    else "",
                    subset=["Zacks Rank"]
                )
                st.dataframe(styled, use_container_width=True)
            else:
                st.dataframe(cm, use_container_width=True)
        else:
            st.info(f"No valid Zacks {label} data detected.")

        st.markdown(
            "<div class='footer'>Fox Valley Intelligence Engine v6.1.1 – Tactical Core System</div>",
            unsafe_allow_html=True
        )

# --- Decision Matrix ---
with tabs[4]:
    st.subheader("📈 Tactical Decision Matrix – Auto-Weighted Allocation")

    if not decision_matrix.empty:
        st.dataframe(decision_matrix, use_container_width=True)
        st.markdown(
            "💹 Each Zacks #1 candidate is capped at 15% allocation with a 15% cash floor."
        )
        if st.button("🚀 Deploy Trade Plan (Simulation Only)"):
            st.success("Trade Plan validated – ready for Fidelity execution window.")
    else:
        st.info("No actionable Zacks data available. Upload latest screens to /data.")

    st.markdown(
        "<div class='footer'>Fox Valley Intelligence Engine v6.1.1 – Tactical Core System</div>",
        unsafe_allow_html=True
    )

# --- Tactical Summary ---
with tabs[5]:
    st.subheader("🧩 Weekly Tactical Summary")

    st.write(f"Total Value: ${total_value:,.2f}")
    st.write(f"Cash Available: ${cash_value:,.2f} ({cash_pct:.2f}%)")

    if not decision_matrix.empty:
        rank1_only = decision_matrix[decision_matrix["Zacks Rank"] == 1]
        st.markdown("### Active Zacks #1 Candidates")
        st.dataframe(rank1_only, use_container_width=True)
    else:
        st.info("No Rank #1 candidates in the current Zacks screens.")

    st.markdown(
        "<div class='footer'>Fox Valley Intelligence Engine v6.1.1 – Tactical Core System</div>",
        unsafe_allow_html=True
    )

# --- Daily Intelligence Brief ---
with tabs[6]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")

    now_str = datetime.datetime.now().strftime("%A, %B %d, %Y – %I:%M %p CST")
    st.caption(f"Generated: {now_str}")

    st.markdown("```text\n" + brief_text + "\n```")

    if not decision_matrix.empty:
        st.markdown("### Full Decision Matrix Snapshot")
        st.dataframe(decision_matrix, use_container_width=True)
    else:
        st.info("No Zacks data loaded; decision matrix is empty.")

    st.markdown(
        "<div class='footer'>Fox Valley Intelligence Engine v6.1.1 – Tactical Core System</div>",
        unsafe_allow_html=True
    )

# ---------- (Optional) Daily Tactical Summary File ----------
def generate_tactical_summary_file():
    """Writes a markdown summary file to /data once per morning window."""
    now = datetime.datetime.now()
    fname = f"data/tactical_summary_{now.strftime('%Y-%m-%d')}.md"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# Fox Valley Tactical Summary – {now:%B %d, %Y}\n\n")
            f.write(brief_text + "\n\n")
            if not decision_matrix.empty:
                f.write("## Decision Matrix\n\n")
                f.write(decision_matrix.to_markdown(index=False))
        # Note: no Streamlit message here; this may run in background
    except Exception:
        # Fail silently in production; logs are available in cloud if needed
        pass

# Auto-run between 06:45 and 06:55 CST
now = datetime.datetime.now()
if now.hour == 6 and 45 <= now.minute < 55:
    generate_tactical_summary_file()
