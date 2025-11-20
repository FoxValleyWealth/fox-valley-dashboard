# ============================================================
# 🧭 Fox Valley Intelligence Engine — Portfolio Engine Module
# v7.3R-5.4 | Core Portfolio Loader + Synthetic Gain Calculator
# ============================================================

import os
import pandas as pd
import numpy as np
from datetime import datetime

# -----------------------------
# GLOBAL PATH REFERENCES
# -----------------------------
DATA_DIR = "data"
ARCHIVE_DIR = "archive"
PORTFOLIO_FILE_PATTERN = "Portfolio_Positions"


# ============================================================
# CORE FILE LOADING UTILITIES
# ============================================================
def load_latest_file(pattern, directory=DATA_DIR):
    """Returns the latest CSV file matching a pattern."""
    try:
        if not os.path.isdir(directory):
            return None, None
        files = [f for f in os.listdir(directory) if pattern in f and f.endswith(".csv")]
        if not files:
            return None, None
        latest = sorted(files, key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)[0]
        return pd.read_csv(os.path.join(directory, latest)), latest
    except Exception:
        return None, None


def load_portfolio():
    """Loads and cleans the most recent portfolio file."""
    df, filename = load_latest_file(PORTFOLIO_FILE_PATTERN)
    if df is None:
        return None, None

    df = df.replace(r"\((.*?)\)", r"-\1", regex=True).replace(r"[\$,]", "", regex=True)
    df = df.apply(lambda col: pd.to_numeric(col, errors="ignore"))

    if "Symbol" in df.columns:
        df = df.rename(columns={"Symbol": "Ticker"})

    return df, filename


# ============================================================
# SYNTHETIC GAIN ENGINE (Weighted Gain/Loss Calculation)
# ============================================================
def compute_synthetic_gain(df):
    """Fallback when Gain/Loss % is missing."""
    try:
        if "Current Value" in df.columns and "Cost Basis" in df.columns:
            cv = pd.to_numeric(df["Current Value"], errors="coerce").fillna(0)
            cb = pd.to_numeric(df["Cost Basis"], errors="coerce").replace(0, np.nan)
            synthetic = ((cv - cb) / cb) * 100
            return synthetic.fillna(0)
        return pd.Series(0, index=df.index, dtype=float)
    except Exception:
        return pd.Series(0, index=df.index, dtype=float)


def compute_portfolio_metrics(df):
    """Returns Total Value, Cash Value, Weighted Avg Gain %."""
    if df is None or df.empty:
        return 0.0, 0.0, None
    try:
        current_value_series = pd.to_numeric(df.get("Current Value", pd.Series(dtype=float)), errors="coerce").fillna(0)
        total_value = current_value_series.sum()
        
        gain_candidates = ["Gain/Loss %", "Total Gain/Loss Percent", "GainLossPct", "%Chg"]
        detected_gain_col = next((col for col in gain_candidates if col in df.columns), None)
        
        numeric_gain = pd.to_numeric(df[detected_gain_col], errors="coerce").fillna(0) if detected_gain_col else compute_synthetic_gain(df)

        avg_gain = (numeric_gain * current_value_series).sum() / total_value if total_value > 0 else None

        cash_value = df[df["Ticker"].astype(str).str.lower() == "cash"]["Current Value"].sum() if "Ticker" in df.columns else 0.0

        return float(total_value), float(cash_value), avg_gain
    except Exception:
        return 0.0, 0.0, None


# ============================================================
# ARCHIVE HISTORY LOADING
# ============================================================
def load_archive_portfolio_history():
    """Builds historical value trend from archive folder."""
    history = []
    if not os.path.isdir(ARCHIVE_DIR):
        return pd.DataFrame()

    for f in os.listdir(ARCHIVE_DIR):
        if not f.startswith("archive_Portfolio_Positions_") or not f.endswith(".csv"):
            continue

        try:
            date_part = f.replace("archive_Portfolio_Positions_", "").replace(".csv", "")
            dt = None
            try:
                dt = datetime.strptime(date_part, "%b-%d-%Y")
            except:
                dt = None

            df = pd.read_csv(os.path.join(ARCHIVE_DIR, f))
            df = df.replace(r"\((.*?)\)", r"-\1", regex=True).replace(r"[\$,]", "", regex=True)
            df = df.apply(lambda col: pd.to_numeric(col, errors="ignore"))

            if "Symbol" in df.columns:
                df = df.rename(columns={"Symbol": "Ticker"})

            total_value, _, _ = compute_portfolio_metrics(df)

            history.append({"Label": date_part, "Date": dt or date_part, "Total Value": total_value})

        except Exception:
            continue

    hist_df = pd.DataFrame(history)
    if not hist_df.empty and pd.api.types.is_datetime64_any_dtype(hist_df["Date"]):
        hist_df = hist_df.sort_values("Date")

    return hist_df
