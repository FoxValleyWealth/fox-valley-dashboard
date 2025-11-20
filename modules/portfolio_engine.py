# ============================================================
# 🧭 Fox Valley Intelligence Engine — Portfolio Engine Module
# v7.3R-5.3 | Core Portfolio Loader + Synthetic Gain Calculator
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
    """
    Returns: (DataFrame, filename)
    Loads the most recent CSV file matching pattern in 'directory'.
    """
    try:
        if not os.path.isdir(directory):
            return None, None

        files = [f for f in os.listdir(directory) if pattern in f and f.endswith(".csv")]
        if not files:
            return None, None

        latest = sorted(
            files,
            key=lambda x: os.path.getmtime(os.path.join(directory, x)),
            reverse=True,
        )[0]
        df = pd.read_csv(os.path.join(directory, latest))
        return df, latest
    except Exception:
        return None, None


def load_portfolio():
    """
    Loads the latest Portfolio_Positions file from /data.
    """
    df, filename = load_latest_file(PORTFOLIO_FILE_PATTERN, directory=DATA_DIR)
    if df is None:
        return None, None

    # Clean numeric fields and normalize symbol column
    df = (
        df.replace(r"\((.*?)\)", r"-\1", regex=True)
        .replace(r"[\$,]", "", regex=True)
    )
    df = df.apply(lambda col: pd.to_numeric(col, errors="ignore"))

    if "Symbol" in df.columns:
        df = df.rename(columns={"Symbol": "Ticker"})

    return df, filename


# ============================================================
# SYNTHETIC GAIN ENGINE (Weighted Gain/Loss Calculation)
# ============================================================
def compute_synthetic_gain(df):
    """
    Fallback calculation when Gain/Loss % is missing.
    Derived using: (CurrentValue - CostBasis) / CostBasis * 100
    """
    try:
        if "Current Value" in df.columns and "Cost Basis" in df.columns:
            cv = pd.to_numeric(df["Current Value"], errors="coerce").fillna(0)
            cb = pd.to_numeric(df["Cost Basis"], errors="coerce").replace(0, np.nan)
            synthetic = ((cv - cb) / cb) * 100
            return synthetic.fillna(0)
        else:
            return pd.Series(0, index=df.index, dtype=float)
    except Exception:
        return pd.Series(0, index=df.index, dtype=float)


def compute_portfolio_metrics(df):
    """
    Computes the following:
    - Total Value
    - Cash Value
    - Value-Weighted Avg Gain/Loss % using Smart Gain Mode
    """
    if df is None or df.empty:
        return 0.0, 0.0, None

    try:
        current_value_series = pd.to_numeric(
            df.get("Current Value", pd.Series(dtype=float)), errors="coerce"
        ).fillna(0)
        total_value = current_value_series.sum()

        gain_candidates = [
            "Gain/Loss %", "Total Gain/Loss Percent", "Today's Gain/Loss Percent",
            "GainLossPct", "% Gain/Loss", "%Chg"
        ]
        detected_gain_col = next((col for col in gain_candidates if col in df.columns), None)

        if detected_gain_col:
            numeric_gain = pd.to_numeric(df[detected_gain_col], errors="coerce").fillna(0)
        else:
            numeric_gain = compute_synthetic_gain(df)

        avg_gain = (
            (numeric_gain * current_value_series).sum() / total_value
            if total_value > 0
            else None
        )

        cash_value = 0.0
        if "Ticker" in df.columns:
            cash_rows = df[df["Ticker"].astype(str).str.lower().eq("cash")]
            if not cash_rows.empty:
                cash_value = pd.to_numeric(
                    cash_rows["Current Value"], errors="coerce"
                ).fillna(0).sum()

        return float(total_value), float(cash_value), avg_gain

    except Exception:
        return 0.0, 0.0, None


# ============================================================
# HISTORY ARCHIVE LOADING (archive_Portfolio_Positions_*)
# ============================================================
def load_archive_portfolio_history():
    """
    Returns dataframe of historical total portfolio values
    from /archive folder.
    """
    history_rows = []

    if not os.path.isdir(ARCHIVE_DIR):
        return pd.DataFrame()

    for f in os.listdir(ARCHIVE_DIR):
        if not f.startswith("archive_Portfolio_Positions_") or not f.endswith(".csv"):
            continue

        try:
            date_part = f.replace("archive_Portfolio_Positions_", "").replace(".csv", "")
            try:
                dt = datetime.strptime(date_part, "%b-%d-%Y")
            except:
                dt = None

            full_path = os.path.join(ARCHIVE_DIR, f)
            df = pd.read_csv(full_path)

            df = df.replace(r"\((.*?)\)", r"-\1", regex=True).replace(r"[\$,]", "", regex=True)
            df = df.apply(lambda col: pd.to_numeric(col, errors="ignore"))

            if "Symbol" in df.columns:
                df = df.rename(columns={"Symbol": "Ticker"})

            total_value, _, _ = compute_portfolio_metrics(df)

            history_rows.append({
                "Label": date_part,
                "Date": dt if dt is not None else date_part,
                "Total Value": total_value
            })

        except Exception:
            continue

    hist_df = pd.DataFrame(history_rows)
    if not hist_df.empty and pd.api.types.is_datetime64_any_dtype(hist_df["Date"]):
        hist_df = hist_df.sort_values("Date")

    return hist_df

