# 🧭 Fox Valley Intelligence Engine v7.3R-2 — Enterprise Command Deck
# Final Build — Nov 12, 2025
# - Auto-detect latest daily CSVs (Portfolio + Zacks G1/G2/DefDiv)
# - Correct totals: Total Account Value from "Current Value" ONLY
# - Cash detection: SPAXX / Money Market / Type=Cash / Core / Available
# - Cross-match & Tactical Matrix + Daily Brief
# - Objective Top-8 candidates (Rank #1 & Not Held first; multi-source priority)
# - Diagnostic Console at top

import streamlit as st
import pandas as pd
from pathlib import Path
import io
import datetime as dt

# ----------------------- Streamlit Config -----------------------
st.set_page_config(
    page_title="Fox Valley Intelligence Engine v7.3R-2",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🧭 Fox Valley Intelligence Engine – Enterprise Command Deck (v7.3R-2)")
st.caption("Final Build — Nov 12, 2025 | Top-8 + Correct Totals + Diagnostics")

DATA_DIR = Path("data")

# ----------------------- CSV Loader w/ Header Detection -----------------------
def load_csv(filepath: Path) -> pd.DataFrame:
    """
    Safely load a CSV that may contain disclaimer lines above the header.
    Heuristic: first line with >= 3 commas is treated as header line.
    """
    text = filepath.read_text(errors="ignore")
    lines = text.splitlines()
    hdr = next((i for i, l in enumerate(lines) if l.count(",") >= 3), 0)
    df = pd.read_csv(io.StringIO("\n".join(lines[hdr:])))
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def newest_non_archived(pattern: str) -> Path | None:
    """
    Return newest file in /data that:
      - matches pattern, AND
      - does NOT start with 'archive_'.
    """
    cands = [p for p in DATA_DIR.glob(pattern) if not p.name.startswith("archive_")]
    if not cands:
        return None
    return sorted(cands, key=lambda p: p.stat().st_mtime)[-1]

# ----------------------- Portfolio Loader & Totals -----------------------
def load_latest_portfolio():
    """
    Load newest Portfolio_Positions_*.csv (non-archived) and compute:
      - total account value (from 'Current Value' only)
      - cash value (SPAXX / Money Market / Type=Cash / Core / Available)
    """
    pfile = newest_non_archived("Portfolio_Positions_*.csv")
    if pfile is None:
        st.error("⚠️ No portfolio files found in /data.")
        return pd.DataFrame(), 0.0, 0.0, None

    df = load_csv(pfile)
    st.sidebar.success(f"📁 Active Portfolio File: {pfile.name}")
    st.sidebar.write(f"Loaded {len(df)} rows and {len(df.columns)} columns")

    # Clean numeric-like text (remove $ and ,), convert when sensible
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].str.replace(r"[\$,]", "", regex=True)
            # don't force to numeric here; we’ll coerce selectively

    # Identify "Current Value" column precisely first; fallbacks after
    value_col = None
    strict = ["Current Value"]
    looser = ["Total Account Value", "Account Value", "Total Value"]

    for tgt in strict + looser:
        vcand = next((c for c in df.columns if c.lower() == tgt.lower()), None)
        if vcand:
            value_col = vcand
            break

    if value_col is None:
        vcands = [c for c in df.columns if "value" in c.lower()]
        value_col = vcands[0] if vcands else None

    if value_col is None:
        st.error("⚠️ Could not identify a value column (e.g., 'Current Value').")
        return df, 0.0, 0.0, pfile.name

    # Compute total from that ONE column only
    total_val = pd.to_numeric(df[value_col], errors="coerce").sum()

    # Cash detection via multiple signals
    symbol_col = next((c for c in df.columns if c.lower() in ["symbol", "ticker"] or "symbol" in c.lower()), None)
    desc_col   = next((c for c in df.columns if "description" in c.lower()), None)
    type_col   = next((c for c in df.columns if c.lower() == "type"), None)

    cash_mask = pd.Series(False, index=df.index)

    if type_col is not None:
        cash_mask |= df[type_col].astype(str).str.contains("cash", case=False, na=False)
        cash_mask |= df[type_col].astype(str).str.contains("core", case=False, na=False)

    if desc_col is not None:
        cash_mask |= df[desc_col].astype(str).str.contains("money market", case=False, na=False)

    if symbol_col is not None:
        cash_mask |= df[symbol_col].astype(str).str.contains("SPAXX", case=False, na=False)

    # Also consider headers that may say "Available to Trade"
    avail_cols = [c for c in df.columns if "available" in c.lower()]
    avail_val = 0.0
    for c in avail_cols:
        avail_val += pd.to_numeric(df[c], errors="coerce").sum()

    cash_from_rows = pd.to_numeric(df.loc[cash_mask, value_col], errors="coerce").sum()
    cash_val = max(cash_from_rows, avail_val)

    # Diagnostics
    st.sidebar.write(f"🔍 Value column used: {value_col}")
    st.sidebar.write(f"🔍 Estimated total account value: ${total_val:,.2f}")
    st.sidebar.write(f"🔍 Estimated cash value: ${cash_val:,.2f}")

    return df, float(total_val), float(cash_val), pfile.name

# ----------------------- Zacks Loaders -----------------------
def load_zacks():
    """
    Load newest non-archived Zacks screens (Growth 1, Growth 2, Defensive Dividends).
    Returns dict: {label: DataFrame}
    """
    labels = {
        "Growth 1": "Growth 1",
        "Growth 2": "Growth 2",
        "Defensive Dividends": "Defensive Dividends",
    }
    out = {}
    for label, token in labels.items():
        f = newest_non_archived(f"*{token}*.csv")
        if f is None:
            st.sidebar.warning(f"⚠️ Missing Zacks file for: {label}")
            out[label] = pd.DataFrame()
            continue
        df = load_csv(f)
        st.sidebar.success(f"📁 Active Zacks File: {f.name}")
        st.sidebar.write(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        out[label] = df
    return out

def normalize_zacks(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    z = df.copy()

    # Ticker column
    tcol = next((c for c in z.columns if c.lower() == "ticker" or "ticker" in c.lower()), None)
    if tcol is None:
        return pd.DataFrame()
    z.rename(columns={tcol: "Ticker"}, inplace=True)
    z["Ticker"] = z["Ticker"].astype(str).str.strip()

    # Zacks Rank column
    if "Zacks Rank" not in z.columns:
        rc = next((c for c in z.columns if "zacks rank" in c.lower() or c.lower() == "rank"), None)
        if rc:
            z.rename(columns={rc: "Zacks Rank"}, inplace=True)
    if "Zacks Rank" in z.columns:
        z["Zacks Rank"] = pd.to_numeric(z["Zacks Rank"], errors="coerce")
    else:
        z["Zacks Rank"] = pd.NA

    # Optional: Norm price/RS if present; leave as-is otherwise
    return z[["Ticker", "Zacks Rank"]].copy()

# ----------------------- Cross-Match & Intelligence -----------------------
def classify_action(rank, held):
    if pd.isna(rank):
        return "Review"
    if rank == 1 and not held:
        return "🟢 Buy – New #1"
    if rank == 1 and held:
        return "⚪ Hold – Held #1"
    if rank == 2 and held:
        return "🟠 Review – Held #2"
    if rank == 2 and not held:
        return "Watch – Rank 2"
    if rank >= 3 and held:
        return "🔻 Caution – Held 3+"
    if rank >= 3 and not held:
        return "Avoid – Rank 3+"
    return "Review"

def cross_match(zdf: pd.DataFrame, holdings: set, source: str) -> pd.DataFrame:
    z = normalize_zacks(zdf)
    if z.empty:
        return pd.DataFrame()
    z["Held"] = z["Ticker"].isin(holdings)
    z["Source"] = source
    z["Action"] = [classify_action(r, h) for r, h in zip(z["Zacks Rank"], z["Held"])]
    return z

def build_intelligence(portfolio: pd.DataFrame, zacks: dict, total_val: float, cash_val: float):
    if portfolio.empty:
        return {
            "narrative": "No portfolio data available.",
            "matrix": pd.DataFrame(),
            "g1": pd.DataFrame(), "g2": pd.DataFrame(), "dd": pd.DataFrame(),
            "rank1_new": pd.DataFrame(), "rank1_held": pd.DataFrame(),
            "top8": pd.DataFrame(),
        }

    # Portfolio tickers
    p_symbol = next((c for c in portfolio.columns if c.lower() in ["symbol", "ticker"] or "symbol" in c.lower()), None)
    if p_symbol is None:
        return {
            "narrative": "No Symbol/Ticker column found in portfolio.",
            "matrix": pd.DataFrame(),
            "g1": pd.DataFrame(), "g2": pd.DataFrame(), "dd": pd.DataFrame(),
            "rank1_new": pd.DataFrame(), "rank1_held": pd.DataFrame(),
            "top8": pd.DataFrame(),
        }
    holdings = set(portfolio[p_symbol].astype(str))

    g1 = cross_match(zacks.get("Growth 1", pd.DataFrame()), holdings, "Growth 1")
    g2 = cross_match(zacks.get("Growth 2", pd.DataFrame()), holdings, "Growth 2")
    dd = cross_match(zacks.get("Defensive Dividends", pd.DataFrame()), holdings, "Defensive Dividends")

    frames = [f for f in [g1, g2, dd] if not f.empty]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Ticker","Zacks Rank","Held","Source","Action"])

    if not combined.empty:
        # Consolidate by ticker: min rank, held if any, list of sources
        agg = (
            combined
            .groupby("Ticker", as_index=False)
            .agg({
                "Zacks Rank": "min",
                "Held": "any",
                "Source": lambda s: ", ".join(sorted(set(s))),
            })
        )
        agg["Action"] = [classify_action(r, h) for r, h in zip(agg["Zacks Rank"], agg["Held"])]
    else:
        agg = combined.copy()

    # Rank #1 breakdown
    rank1 = agg[agg["Zacks Rank"] == 1] if not agg.empty else pd.DataFrame()
    rank1_new  = rank1[~rank1["Held"]] if not rank1.empty else pd.DataFrame()
    rank1_held = rank1[ rank1["Held"]] if not rank1.empty else pd.DataFrame()

    # Objective Top-8 selection:
    # 1) Rank 1 and Not Held (multi-source before single-source)
    def src_count(s: str) -> int:
        return len([x.strip() for x in s.split(",")]) if isinstance(s, str) and s.strip() else 0

    if not agg.empty:
        candidates = agg.copy()
        candidates["SourceCount"] = candidates["Source"].apply(src_count)

        # Primary bucket: Rank 1 & Not Held
        b1 = candidates[(candidates["Zacks Rank"] == 1) & (~candidates["Held"])]
        b1 = b1.sort_values(["SourceCount", "Ticker"], ascending=[False, True])

        # Secondary bucket: Rank 1 & Held (upgrade to Hold)
        b2 = candidates[(candidates["Zacks Rank"] == 1) & (candidates["Held"])].sort_values(["SourceCount","Ticker"], ascending=[False, True])

        # Tertiary bucket (only if needed to fill to 8): Rank 2 & Not Held
        b3 = candidates[(candidates["Zacks Rank"] == 2) & (~candidates["Held"])].sort_values(["SourceCount","Ticker"], ascending=[False, True])

        top = pd.concat([b1, b2, b3], ignore_index=True).head(8)
        top = top[["Ticker","Zacks Rank","Held","Source"]].copy()
        top["Action"] = [classify_action(r, h) for r, h in zip(top["Zacks Rank"], top["Held"])]
        top8 = top
    else:
        top8 = pd.DataFrame()

    # Narrative
    nh = portfolio[p_symbol].nunique()
    covered = agg[agg["Held"]].shape[0] if not agg.empty else 0
    r1_total = rank1.shape[0] if not rank1.empty else 0
    r1_new_ct = rank1_new.shape[0] if not rank1_new.empty else 0
    r1_held_ct = rank1_held.shape[0] if not rank1_held.empty else 0

    narrative = f"""Fox Valley Daily Tactical Overlay – {nh} holdings

• Total account value: ${total_val:,.2f}
• Cash available (SPAXX / Core): ${cash_val:,.2f}
• Holdings covered by Zacks screens: {covered}
• Total Zacks Rank #1 symbols (all screens): {r1_total}
  • New #1 candidates (not held): {r1_new_ct}
  • Existing holdings that are #1: {r1_held_ct}
"""

    return {
        "narrative": narrative,
        "matrix": agg,
        "g1": g1, "g2": g2, "dd": dd,
        "rank1_new": rank1_new,
        "rank1_held": rank1_held,
        "top8": top8,
    }

# ----------------------- Load Data -----------------------
portfolio, total_value, cash_value, pfile_name = load_latest_portfolio()
zacks = load_zacks()
intel = build_intelligence(portfolio, zacks, total_value, cash_value)

# ----------------------- Diagnostics -----------------------
with st.expander("🧩 Diagnostic Console", expanded=True):
    st.write("**Active Portfolio File:**", pfile_name or "None")
    if not portfolio.empty:
        st.write("**Portfolio columns:**", list(portfolio.columns))
        st.write("**Rows x Cols:**", f"{portfolio.shape[0]} x {portfolio.shape[1]}")
    else:
        st.warning("No portfolio loaded.")

    for key in ["Growth 1", "Growth 2", "Defensive Dividends"]:
        df = zacks.get(key, pd.DataFrame())
        st.markdown(f"**Zacks {key}:** {'Loaded' if not df.empty else 'Missing/Empty'}")
        if not df.empty:
            st.write("Columns:", list(df.columns))
            st.write("Rows x Cols:", f"{df.shape[0]} x {df.shape[1]}")

    st.markdown("**Intelligence Narrative Preview:**")
    st.text(intel["narrative"])

# ----------------------- Tabs -----------------------
tabs = st.tabs([
    "💼 Portfolio Overview",
    "📊 Growth 1",
    "📊 Growth 2",
    "💰 Defensive Dividends",
    "⚙️ Tactical Matrix",
    "⭐ Top-8 Candidates",
    "🧩 Weekly Tactical Summary",
    "📖 Daily Intelligence Brief",
])

# Portfolio
with tabs[0]:
    st.subheader("💼 Portfolio Overview")
    if not portfolio.empty:
        st.metric("📊 Total Account Value", f"${total_value:,.2f}")
        st.metric("💵 Cash Available to Trade", f"${cash_value:,.2f}")
        st.dataframe(portfolio, use_container_width=True)
    else:
        st.warning("No portfolio data available.")

# Growth 1
with tabs[1]:
    st.subheader("📊 Zacks Growth 1 — Cross-Match")
    g1 = intel.get("g1", pd.DataFrame())
    if not g1.empty:
        st.dataframe(g1, use_container_width=True)
    else:
        st.info("No Growth 1 data available.")

# Growth 2
with tabs[2]:
    st.subheader("📊 Zacks Growth 2 — Cross-Match")
    g2 = intel.get("g2", pd.DataFrame())
    if not g2.empty:
        st.dataframe(g2, use_container_width=True)
    else:
        st.info("No Growth 2 data available.")

# Defensive Dividends
with tabs[3]:
    st.subheader("💰 Zacks Defensive Dividends — Cross-Match")
    dd = intel.get("dd", pd.DataFrame())
    if not dd.empty:
        st.dataframe(dd, use_container_width=True)
    else:
        st.info("No Defensive Dividends data available.")

# Tactical Matrix
with tabs[4]:
    st.subheader("⚙️ Tactical Decision Matrix")
    matrix = intel.get("matrix", pd.DataFrame())
    if not matrix.empty:
        order = {
            "🟢 Buy – New #1": 0,
            "⚪ Hold – Held #1": 1,
            "🟠 Review – Held #2": 2,
            "Watch – Rank 2": 3,
            "🔻 Caution – Held 3+": 4,
            "Avoid – Rank 3+": 5,
            "Review": 6,
        }
        matrix = matrix.copy()
        matrix["ActionPriority"] = matrix["Action"].map(order).fillna(99)
        view = matrix.sort_values(["ActionPriority", "Ticker"]).drop(columns=["ActionPriority"])
        st.dataframe(view, use_container_width=True)
        st.caption("Sorted: Buy/Hold at top; then Review/Watch; then Caution/Avoid.")
    else:
        st.info("No tactical matrix available — check Zacks files.")

# Top-8
with tabs[5]:
    st.subheader("⭐ Top-8 Tactical Candidates (Objective)")
    top8 = intel.get("top8", pd.DataFrame())
    if not top8.empty:
        # Display Source count for transparency
        t = top8.copy()
        t["Sources"] = t["Source"]
        st.dataframe(t[["Ticker","Zacks Rank","Held","Action","Sources"]], use_container_width=True)
        st.caption("Priority: Rank #1 & Not Held first; multi-source > single-source; then Rank 2 if needed.")
    else:
        st.info("No Top-8 candidates found. Verify Zacks screens and ranks.")

# Weekly Summary
with tabs[6]:
    st.subheader("🧩 Weekly Tactical Summary")
    st.markdown("""
This summary reflects the current portfolio and latest Zacks screens:

- Portfolio total (from **Current Value** only)
- Cash reserves (SPAXX / Money Market / Core / Available)
- Count of holdings covered by Zacks
- Rank-1s (new vs held)
    """)
    st.text(intel["narrative"])

# Daily Brief
with tabs[7]:
    st.subheader("📖 Fox Valley Daily Intelligence Brief")
    st.markdown(f"```text\n{intel['narrative']}\n```")
    st.caption(f"Generated {dt.datetime.now():%A, %B %d, %Y – %I:%M %p %Z}".replace("  ", " "))

    r1_new  = intel.get("rank1_new",  pd.DataFrame())
    r1_held = intel.get("rank1_held", pd.DataFrame())

    st.markdown("### 🟢 New Zacks Rank #1 Candidates (Not Held)")
    if not r1_new.empty:
        st.dataframe(r1_new[["Ticker","Zacks Rank","Source","Action"]], use_container_width=True)
    else:
        st.info("No new Rank #1 candidates today.")

    st.markdown("### ✔ Current Holdings That Are Still Rank #1")
    if not r1_held.empty:
        st.dataframe(r1_held[["Ticker","Zacks Rank","Source","Action"]], use_container_width=True)
    else:
        st.info("No current holdings are Rank #1 today.")
