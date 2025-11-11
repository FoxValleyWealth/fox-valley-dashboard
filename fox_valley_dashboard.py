# ================================================================
# 🧭 FOX VALLEY INTELLIGENCE ENGINE v7.2R-1
# Enterprise Command Deck – Path Integrity Final Build (Nov 11 2025)
# ================================================================
#  • Auto-detects /data folder in any environment (Cloud / Local)
#  • Loads newest Portfolio_Positions_*.csv + latest Zacks screens
#  • Displays portfolio metrics, growth screens, and intelligence deck
# ================================================================

import streamlit as st
import pandas as pd
from pathlib import Path
import io

# ------------------------------------------------
# 🔧 Streamlit configuration
# ------------------------------------------------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck (v7.2R-1)")
st.caption("Final Stable Build – November 11 2025")

# ------------------------------------------------
# 🧭 Resolve /data directory dynamically
# ------------------------------------------------
DATA_PATH = (Path(__file__).parent / "data").resolve()
if not DATA_PATH.exists():
    st.error(f"⚠️ Data folder not found at: {DATA_PATH}")
else:
    st.success(f"📂 Data folder detected: {DATA_PATH}")

# ------------------------------------------------
# 📂 Generic CSV loader (returns newest file)
# ------------------------------------------------
def load_latest_csv(prefix: str):
    files = sorted(DATA_PATH.glob(f"{prefix}*.csv"), key=lambda f: f.stat().st_mtime)
    if not files:
        st.warning(f"⚠️ No files found for pattern: {prefix}")
        return None
    latest = files[-1]
    st.info(f"📁 Active file: {latest.name}")
    try:
        df = pd.read_csv(latest, dtype=str)
    except Exception as e:
        st.error(f"❌ Error loading {latest.name}: {e}")
        return None
    df = df.dropna(how="all")
    st.write(f"Loaded {len(df)} rows from {latest.name}")
    return df

# ------------------------------------------------
# 🧩 Load all current datasets
# ------------------------------------------------
portfolio = load_latest_csv("Portfolio_Positions_")
g1 = load_latest_csv("zacks_custom_screen_2025-11-11 Growth 1")
g2 = load_latest_csv("zacks_custom_screen_2025-11-11 Growth 2")
dd = load_latest_csv("zacks_custom_screen_2025-11-11 Defensive Dividends")

# ------------------------------------------------
# 💰 Compute totals if portfolio detected
# ------------------------------------------------
if portfolio is not None and not portfolio.empty:
    st.subheader("💼 Portfolio Overview")

    # Clean currency fields
    for c in portfolio.columns:
        if portfolio[c].dtype == object:
            portfolio[c] = portfolio[c].replace(r"[\$,]", "", regex=True)
            try:
                portfolio[c] = pd.to_numeric(portfolio[c], errors="ignore")
            except Exception:
                pass

    # Infer likely cash and total columns
    value_cols = [c for c in portfolio.columns if any(x in c.lower()
                  for x in ["value", "amount", "total", "balance"])]
    cash_cols = [c for c in portfolio.columns if "cash" in c.lower()]

    total_value = sum(pd.to_numeric(portfolio[c], errors="coerce").sum()
                      for c in value_cols)
    cash_value = sum(pd.to_numeric(portfolio[c], errors="coerce").sum()
                     for c in cash_cols)

    st.metric("📊 Total Account Value", f"${total_value:,.2f}")
    st.metric("💵 Cash Available to Trade", f"${cash_value:,.2f}")
    st.dataframe(portfolio, use_container_width=True)

else:
    st.warning("⚠️ No portfolio data available.")

# ------------------------------------------------
# 📈 Zacks Screens
# ------------------------------------------------
def show_zacks_tab(df, title):
    if df is None or df.empty:
        st.warning(f"⚠️ No data found for {title}.")
        return
    st.subheader(title)
    st.dataframe(df, use_container_width=True)

with st.expander("📊 Growth 1"):
    show_zacks_tab(g1, "Growth 1")

with st.expander("📊 Growth 2"):
    show_zacks_tab(g2, "Growth 2")

with st.expander("💰 Defensive Dividends"):
    show_zacks_tab(dd, "Defensive Dividends")

# ------------------------------------------------
# 🧠 Tactical & Summary Sections (placeholders)
# ------------------------------------------------
st.subheader("⚙️ Tactical Decision Matrix")
st.caption("Auto-generated intelligence summaries will appear here.")
st.subheader("🧩 Weekly Tactical Summary")
st.subheader("📖 Daily Intelligence Brief")
st.success("✅ Enterprise Command Deck v7.2R-1 Operational")
