# ============================================================
# 🧭 Fox Valley Intelligence Engine — Dashboard Engine Module
# v7.3R-5.4 | Trailing Stops, Portfolio Display, UI Table Routing
# ============================================================

import pandas as pd

# ============================================================
# 1️⃣ Trailing Stop Attachment Engine
# ============================================================
def attach_trailing_stops(df, default_pct):
    """
    Adds a default trailing stop percentage to each portfolio holding.
    If 'Ticker' column missing, return unchanged.
    """
    if df is None or df.empty or "Ticker" not in df.columns:
        return df
    out = df.copy()
    out["Trailing Stop %"] = default_pct
    return out


# ============================================================
# 2️⃣ Generic DataFrame Routing to UI Bridge
# ============================================================
def prepare_display_dataframes(portfolio_df, zacks_files_dict):
    """
    Returns a dictionary of structured dataframes in a format
    ready to send to `show_dataframe()` in UI Bridge.
    """
    display_dict = {}

    # Portfolio Positions
    if portfolio_df is not None and not portfolio_df.empty:
        display_dict["Portfolio Positions"] = portfolio_df

    # Raw Zacks Screens
    if isinstance(zacks_files_dict, dict):
        for label, item in zacks_files_dict.items():
            if item:
                df_z, fn_z = item
                display_dict[f"{label} Screen"] = df_z

    return display_dict
