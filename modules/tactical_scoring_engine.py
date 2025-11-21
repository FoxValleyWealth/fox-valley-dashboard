import pandas as pd

# ===========================
# Tactical Scoring Engine
# ===========================

def calculate_unrealized_gain(row):
    """Calculate unrealized gain/loss % based on cost basis."""
    if "Cost Basis" in row and row["Cost Basis"] > 0:
        return ((row["Current Price"] - row["Cost Basis"]) / row["Cost Basis"]) * 100
    return None

def zacks_signal(rank):
    """Maps Zacks Rank to tactical action signals."""
    mapping = {
        1: "Strong Buy",
        2: "Buy",
        3: "Hold",
        4: "Trim",
        5: "Sell"
    }
    return mapping.get(rank, "No Rating")

def apply_tactical_rules(df):
    """Applies tactical scoring decisions to the crossmatched portfolio."""
    df["Gain/Loss %"] = df.apply(calculate_unrealized_gain, axis=1)
    df["Action"] = df["Zacks Rank"].apply(zacks_signal)

    # Tactical refinement based on performance
    df.loc[(df["Action"] == "Hold") & (df["Gain/Loss %"] > 20), "Action"] = "Trim"
    df.loc[(df["Action"] == "Sell") & (df["Gain/Loss %"] > 30), "Action"] = "Sell - Take Profits"
    df.loc[(df["Action"] == "Buy") & (df["Gain/Loss %"] < -10), "Action"] = "Buy More (Dip Buy)"

    return df
