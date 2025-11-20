# ============================================================
# 🧭 Fox Valley Intelligence Engine — Dashboard Integration Module
# v7.3R-5.3 | Unified Data Interface (Portfolio + Zacks + Metrics)
# ============================================================

import pandas as pd
from typing import Tuple, Dict

from .portfolio_engine import (
    load_portfolio,
    compute_portfolio_metrics,
    attach_trailing_stops,
)

from .zacks_engine import (
    load_zacks_files_auto,
    merge_zacks_screens,
    score_zacks_candidates,
    get_top_n,
)

# ============================================================
# UNIFIED INGESTION PIPELINE
# ============================================================
def load_all_data(data_dir="data") -> Tuple[pd.DataFrame, str, pd.DataFrame, Dict]:
    """
    Loads:
    - Portfolio file and filename
    - Latest Zacks files as dictionary
    - Unified scored Zacks DataFrame
    Returns:
        (portfolio_df, portfolio_filename, scored_candidates_df, zacks_files_dict)
    """
    # 1️⃣ Load portfolio
    portfolio_df, portfolio_filename = load_portfolio()

    # 2️⃣ Load Zacks files
    zacks_files_dict = load_zacks_files_auto(data_dir)
    zacks_unified = merge_zacks_screens(zacks_files_dict)
    scored_candidates = score_zacks_candidates(zacks_unified)

    return portfolio_df, portfolio_filename, scored_candidates, zacks_files_dict


# ============================================================
# DASHBOARD METRICS FOR DISPLAY
# ============================================================
def compute_dashboard_metrics(portfolio_df, manual_cash_override=0.0):
    """
    Dashboard-level routing of portfolio metrics.
    Safely handles overrides and empty frames.
    """
    total_value, cash_value, avg_gain = compute_portfolio_metrics(portfolio_df)

    # Respect manual override if entered
    available_cash = (
        manual_cash_override if manual_cash_override > 0 else cash_value
    )

    return {
        "total_value": float(total_value),
        "cash_value": float(available_cash),
        "avg_gain": None if avg_gain is None else float(avg_gain),
    }


# ============================================================
# TOP-N CANDIDATES EXTRACTOR
# ============================================================
def get_dashboard_top_n(scored_candidates_df, n):
    """Returns top-n candidates safely."""
    return get_top_n(scored_candidates_df, n)


# ============================================================
# PORTFOLIO TABLE WITH TRAILING STOPS
# ============================================================
def build_portfolio_table_with_stops(portfolio_df, default_stop_pct):
    """
    Attaches default trailing stop values to the portfolio table.
    """
    return attach_trailing_stops(portfolio_df, default_stop_pct)


# ============================================================
# ZACKS SCREEN INSPECTOR (for expander sections)
# ============================================================
def get_zacks_screen_data(zacks_files_dict):
    """
    Prepares a dictionary for dashboard consumption:
    { ScreenType: (dataframe, filename) }
    """
    return zacks_files_dict


# ============================================================
# SAFE WRAPPER FOR MAIN DASHBOARD ACCESS
# ============================================================
class DashboardData:
    """
    Central data wrapper used in fox_valley_dashboard.py
    """

    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.portfolio_df = None
        self.portfolio_filename = None
        self.scored_candidates = None
        self.zacks_files = {}

    def load(self):
        (
            self.portfolio_df,
            self.portfolio_filename,
            self.scored_candidates,
            self.zacks_files,
        ) = load_all_data(self.data_dir)

    def get_metrics(self, manual_cash):
        return compute_dashboard_metrics(
            self.portfolio_df,
            manual_cash_override=manual_cash,
        )

    def get_top_n(self, n):
        return get_dashboard_top_n(self.scored_candidates, n)

    def get_portfolio_table(self, default_trailing_stop):
        return build_portfolio_table_with_stops(
            self.portfolio_df,
            default_trailing_stop,
        )

    def get_zacks_raw(self):
        return get_zacks_screen_data(self.zacks_files)

