```python
import streamlit as st
import pandas as pd
from pathlib import Path
import shutil
import io

st.set_page_config(page_title="Fox Valley Intelligence Engine v7.3R", layout="wide")
st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck")

DATA_DIR = Path("data")
ARCHIVE_DIR = Path("archive")
ARCHIVE_DIR.mkdir(exist_ok=True)

# ---------- Auto-archive old Portfolio and Zacks files ----------
def auto_archive(pattern):
files = sorted(DATA_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)
if len(files) > 1:
for old in files[:-1]:
shutil.move(str(old), ARCHIVE_DIR / old.name)
st.sidebar.info(f"Archived: {old.name}")

auto_archive("Portfolio_Positions_*.csv")
for pattern in ["zacks_custom_screen_Growth 1.csv", "zacks_custom_screen_Growth 2.csv", "zacks_custom_screen_Defensive.csv"]:
auto_archive(pattern)

# ---------- UNIVERSAL CSV LOADER WITH HEADER DETECTION ----------
def load_latest(pattern):
files = sorted(DATA_DIR.glob(pattern), key=lambda f: f.stat().st_mtime)
if not files:
return pd.DataFrame(), ""
f = files[-1]
text = f.read_text(errors="ignore")
lines = text.splitlines()
header = next((i for i, l in enumerate(lines) if l.count(",") >= 3), 0)
df = pd.read_csv(io.StringIO("\n".join(lines[header:])))
df = df.dropna(how="all")
df.columns = [c.strip() for c in df.columns]
for c in df.columns:
if df[c].dtype == object:
df[c] = df[c].replace(r"[\$,]", "", regex=True)
try:
df[c] = pd.to_numeric(df[c], errors="ignore")
except:
pass
return df, f.name

# ---------- LOAD DATA ----------
portfolio, pf_file = load_latest("Portfolio_Positions_*.csv")
zacks_growth1, z1_file = load_latest("zacks_custom_screen_Growth 1.csv")
zacks_growth2, z2_file = load_latest("zacks_custom_screen_Growth 2.csv")
zacks_div, zd_file = load_latest("zacks_custom_screen_Defensive.csv")

# ---------- COLUMN/TYPE DIAGNOSTICS ----------
def find_cols(df, keys, stcontainer):
keys = [k.lower() for k in keys]
matches = [c for c in df.columns if any(k in c.lower() for k in keys)]
stcontainer.write(f"Columns: {df.columns.tolist()}")
stcontainer.write(f"Types: {df.dtypes}")
stcontainer.write(f"Candidate columns: {matches}")
return matches

# ---------- STREAMLIT TABS ----------
tab1, tab2, tab3, tab4 = st.tabs([
"Portfolio Overview", "Growth Screens", "Tactical Matrix", "Intelligence Briefs"
])

with tab1:
st.header("Portfolio Overview")
if not portfolio.empty:
value_cols = find_cols(portfolio, ["total", "value", "market", "amount"], st)
cash_cols = find_cols(portfolio, ["cash"], st)
total = portfolio[value_cols[0]].sum() if value_cols else 0.0
cash = portfolio[cash_cols[0]].sum() if cash_cols else 0.0
st.metric("Portfolio Total Value", f"${total:,.2f}")
st.metric("Cash Value", f"${cash:,.2f}")
st.dataframe(portfolio)
st.caption(f"Source: {pf_file}")
else:
st.error("Portfolio Data Not Found.")

with tab2:
st.header("Zacks Growth Screens")
if not zacks_growth1.empty:
st.subheader("Growth 1")
st.dataframe(zacks_growth1)
st.caption(f"Source: {z1_file}")
if not zacks_growth2.empty:
st.subheader("Growth 2")
st.dataframe(zacks_growth2)
st.caption(f"Source: {z2_file}")
if not zacks_div.empty:
st.subheader("Defensive Dividend")
st.dataframe(zacks_div)
st.caption(f"Source: {zd_file}")
if zacks_growth1.empty and zacks_growth2.empty and zacks_div.empty:
st.error("No Zacks Growth Data Found.")

with tab3:
st.header("Tactical Matrix: Portfolio & Zacks Cross-Match")
if not portfolio.empty and not zacks_growth1.empty:
pf_ticker_cols = find_cols(portfolio, ["symbol", "ticker"], st)
z1_ticker_cols = find_cols(zacks_growth1, ["symbol", "ticker"], st)
if pf_ticker_cols and z1_ticker_cols:
pf_ticker_col = pf_ticker_cols[0]
z1_ticker_col = z1_ticker_cols[0]
zacks_rank_cols = [c for c in zacks_growth1.columns if "zacks" in c.lower() and "rank" in c.lower()]
if zacks_rank_cols:
merged = portfolio.merge(
zacks_growth1[zacks_growth1[zacks_rank_cols[0]] == 1],
left_on=pf_ticker_col, right_on=z1_ticker_col, how="inner", suffixes=('_pf', '_zacks')
)
st.write("Holdings with Zacks Rank = 1:")
st.dataframe(merged)
else:
st.warning("No Zacks Rank column found in Growth 1 file.")
else:
st.warning("Cannot find matching ticker columns.")
else:
st.info("Need both Portfolio and Zacks Growth 1 data to cross-match holdings.")

with tab4:
st.header("Intelligence Briefs")
st.markdown("""
- Data Pipeline: Latest files auto-ingested from `/data`, old files archived in `/archive`
- Diagnostics: Column/Type logic and file sources displayed in each tab
- Tactical Matrix: Cross-matches active holdings with Zacks Rank = 1
- Expansion: Add charts, alerts, and new signals as needed
""")
```

How to use:
- Save this code in your main Python file (for example, `fox_valley_dashboard.py`).
- Your data folder must be named `data`, and the archive folder `archive` will be created automatically.
- Your CSV files should use the same naming pattern as before:
- Portfolio: `Portfolio_Positions_*.csv`
- Zacks: `zacks_custom_screen_Growth 1.csv`, `zacks_custom_screen_Growth 2.csv`, `zacks_custom_screen_Defensive.csv`
- Run your app with:
```
streamlit run fox_valley_dashboard.py
