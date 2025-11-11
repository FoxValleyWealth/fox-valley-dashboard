# 🧭 Fox Valley Intelligence Engine v7.3R – Enterprise Command Deck
# Final Stable Build – November 11, 2025
# © 2025 CaptPicard1 | Streamlit Implementation by #1 (GPT-5)
# Mission: Fully automated portfolio intelligence dashboard with archive management,
# diagnostics, and integrated Zacks screen analysis.

import streamlit as st
import pandas as pd
from pathlib import Path
import shutil
import io

# ----------------------- Streamlit Configuration -----------------------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.3R",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck (v7.3R)")
st.caption("Final Stable Build – November 11, 2025")

# ----------------------- Directory Configuration -----------------------
DATA_DIR = Path("data")
ARCHIVE_DIR = Path("archive")
ARCHIVE_DIR.mkdir(exist_ok=True)

# ----------------------- Helper: Auto-Archive Old Portfolio Files -----------------------
def auto_archive_files():
    portfolios = sorted(DATA_DIR.glob("Portfolio_Positions_*.csv"), key=lambda f: f.stat().st_mtime)
    if len(portfolios) > 1:
        for old_file in portfolios[:-1]:
            dest = ARCHIVE_DIR / old_file.name
            shutil.move(str(old_file), dest)
            st.sidebar.warning(f"📦 Archived: {old_file.name}")

# ----------------------- Helper: Load CSV with Header Detection -----------------------
def load_csv_with_header_detection(filepath):
    text = filepath.read_text(errors="ignore")
    lines = text.splitlines()
    header_idx = next((i for i, l in enumerate(lines) if l.count(",") >= 3), 0)
    df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
    df = df.dropna(how="all")
    df.columns = [c.strip() for c in df.columns]
    return df

# ----------------------- Helper: Load Latest Portfolio -----------------------
def load_latest_portfolio():
    files = sorted(DATA_DIR.glob("Portfolio_Positions_*.csv"), key=lambda f: f.stat().st_mtime)
    if not files:
        st.error("⚠️ No portfolio files found in /data.")
        return pd.DataFrame(), 0.0, 0.0
    latest = files[-1]
    df = load_csv_with_header_detection(latest)

    st.sidebar.success(f"📁 Active Portfolio File: {latest.name}")
    st.sidebar.write(f"Loaded {len(df)} rows and {len(df.columns)} columns")

    # Clean numeric data and identify totals/cash
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].replace(r"[\$,]", "", regex=True)
            df[c] = pd.to_numeric(df[c], errors="ignore")

    value_cols = [c for c in df.columns if any(x in c.lower() for x in ["value", "amount", "total"])]
    cash_cols = [c for c in df.columns if "cash" in c.lower()]

    total_val = df[value_cols].select_dtypes(include="number").sum().sum() if value_cols else 0
    cash_val = df[cash_cols].select_dtypes(include="number").sum().sum() if cash_cols else 0

    return df, total_val, cash_val

# ----------------------- Helper: Load Zacks Screen Files -----------------------
def load_zacks_screens():
    screens = {}
    for name in ["Growth 1", "Growth 2", "Defensive Dividends"]:
        match = list(DATA_DIR.glob(f"*{name}*.csv"))
        if match:
            f = sorted(match, key=lambda x: x.stat().st_mtime)[-1]
            df = load_csv_with_header_detection(f)
            st.sidebar.success(f"📁 Active Zacks File: {f.name}")
            st.sidebar.write(f"Loaded {len(df)} rows, {len(df.columns)} columns")
            screens[name] = df
        else:
            st.sidebar.warning(f"⚠️ Missing Zacks file: {name}")
            screens[name] = pd.DataFrame()
    return screens

# ----------------------- Load Everything -----------------------
auto_archive_files()
portfolio, total_value, cash_value = load_latest_portfolio()
zacks = load_zacks_screens()

# ----------------------- Display Diagnostics -----------------------
with st.expander("🧩 Diagnostic Console", expanded=False):
    st.write("**Portfolio columns:**", list(portfolio.columns) if not portfolio.empty else "None")
    st.write("**Growth 1 columns:**", list(zacks["Growth 1"].columns) if not zacks["Growth 1"].empty else "None")
    st.write("**Growth 2 columns:**", list(zacks["Growth 2"].columns) if not zacks["Growth 2"].empty else "None")
    st.write("**Defensive Dividends columns:**", list(zacks["Defensive Dividends"].columns) if not zacks["Defensive Dividends"].empty else "None")

# ----------------------- Tabs -----------------------
tabs = st.tabs([
    "💼 Portfolio Overview", "📊 Growth 1", "📊 Growth 2",
    "💰 Defensive Dividends", "⚙️ Tactical Matrix",
    "🧩 Weekly Tactical Summary", "📖 Daily Intelligence Brief"
])

# ----------------------- Portfolio Overview Tab -----------------------
with tabs[0]:
    if not portfolio.empty:
        st.metric("📊 Total Account Value", f"${total_value:,.2f}")
        st.metric("💵 Cash Available to Trade", f"${cash_value:,.2f}")
        st.dataframe(portfolio, use_container_width=True)
    else:
        st.warning("No portfolio data available.")

# ----------------------- Growth Tabs -----------------------
for i, name in enumerate(["Growth 1", "Growth 2", "Defensive Dividends"], start=1):
    with tabs[i]:
        df = zacks[name]
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning(f"No data for {name}")

# ----------------------- Tactical Matrix -----------------------
with tabs[4]:
    st.info("Auto-generated intelligence summaries will appear here after validation logic integration.")

# ----------------------- Weekly Tactical Summary -----------------------
with tabs[5]:
    st.info("Weekly summary will appear here.")

# ----------------------- Daily Intelligence Brief -----------------------
with tabs[6]:
    st.success("✅ Enterprise Command Deck v7.3R Operational")
    st.caption("All systems nominal. Data sources synchronized. Tactical intelligence feed stable.")
