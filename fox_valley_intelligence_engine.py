import os
import pandas as pd
from tabulate import tabulate
from datetime import datetime

# Tactical scoring engine import
try:
    from modules.tactical_scoring_engine import apply_tactical_rules
except ImportError:
    print("⚠ Missing tactical_scoring_engine module in /modules. Please add it.")
    exit()


# ===== PATH SETTINGS =====
DATA_PATH = "data"


# ===== FILE LOADERS =====
def load_most_recent_file(keyword):
    """Returns the most recent CSV file in /data matching a keyword."""
    files = [f for f in os.listdir(DATA_PATH) if keyword.lower() in f.lower() and f.endswith(".csv")]
    if not files:
        return None
    latest_file = sorted(files)[-1]
    return os.path.join(DATA_PATH, latest_file)


def load_portfolio():
    """Loads the latest portfolio CSV file."""
    path = load_most_recent_file("Portfolio")
    if path:
        print(f"\n🗂 Loading Portfolio File: {os.path.basename(path)}")
        return pd.read_csv(path)
    print("⚠ No portfolio file found.")
    return None


def load_zacks_files():
    """Loads Zacks Growth1, Growth2, and Defensive Dividend screens."""
    categories = ["Growth1", "Growth 1", "Growth2", "Growth 2", "Defensive"]
    loaded = {}
    for cat in categories:
        path = load_most_recent_file(cat)
        if path:
            print(f"📥 Loaded Zacks File: {os.path.basename(path)}")
            loaded[cat] = pd.read_csv(path)
    if not loaded:
        print("\n⚠ No Zacks files found.")
    return loaded


# ===== ANALYSIS — Portfolio Summary =====
def show_portfolio_summary(df):
    """Displays key portfolio metrics."""
    if df is None or df.empty:
        print("⚠ No portfolio data to analyze.")
        return

    df["Value"] = df["Shares"] * df["Current Price"]
    total_value = df["Value"].sum()

    print("\n📊 Portfolio Summary")
    print(tabulate(df[["Ticker", "Shares", "Current Price", "Value"]].head(12),
                   headers='keys', tablefmt='github', floatfmt=".2f"))
    print(f"\n💰 Estimated Total Portfolio Value: ${total_value:,.2f}")


# ===== CROSSMATCH + TACTICAL SIGNALS =====
def crossmatch_with_zacks(portfolio_df, zacks_data):
    """Matches portfolio tickers with Zacks screens and applies tactical logic."""
    if portfolio_df is None or not zacks_data:
        print("\n⚠ Cannot crossmatch — missing data.")
        return

    portfolio_df["Ticker"] = portfolio_df["Ticker"].str.upper()
    all_matches = []

    for category, zacks_df in zacks_data.items():
        zacks_df["Ticker"] = zacks_df["Ticker"].str.upper()

        if "Zacks Rank" in zacks_df.columns:
            zacks_df["Zacks Rank"] = pd.to_numeric(zacks_df["Zacks Rank"], errors="coerce")

        merged = pd.merge(portfolio_df, zacks_df, on="Ticker", how="inner")
        if not merged.empty:
            merged["Screen Category"] = category
            all_matches.append(merged)

    if all_matches:
        result = pd.concat(all_matches, ignore_index=True)
        result = apply_tactical_rules(result)  # Charlie Segment scoring

        print("\n🎯 Tactical Signals — Portfolio Intelligence Report")
        print(tabulate(result[[
            "Ticker", "Shares", "Current Price", "Gain/Loss %",
            "Zacks Rank", "Action", "Screen Category"
        ]], headers='keys', tablefmt='github', floatfmt=".2f"))
    else:
        print("\n📭 No matches found between portfolio and Zacks screens.")


# ===== MAIN EXECUTION =====
def main():
    print("\n🧭 Fox Valley Intelligence Engine — Tactical Console (CLI Edition)")
    print("==================================================================\n")

    portfolio_df = load_portfolio()
    zacks_files = load_zacks_files()

    show_portfolio_summary(portfolio_df)
    crossmatch_with_zacks(portfolio_df, zacks_files)

    print("\n🚀 Engine Execution Complete — Charlie Segment Active.")
    print("Next: Stop-Loss Decision Engine + CSV/PDF Tactical Report Export (Delta Segment).")


if __name__ == "__main__":
    main()
