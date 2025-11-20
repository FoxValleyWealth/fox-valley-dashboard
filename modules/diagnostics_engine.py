# ============================================================
# 🧭 Fox Valley Intelligence Engine — Diagnostics Engine Module
# v7.3R-5.3 | Analytics, Visualization & Historical Intelligence
# ============================================================

import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

from .portfolio_engine import compute_portfolio_metrics
from .zacks_engine import score_zacks_candidates

# ============================================================
# 1️⃣ PORTFOLIO WEIGHT HEAT MAP
# ============================================================
def generate_weight_heatmap(portfolio_df):
    if portfolio_df is None or portfolio_df.empty:
        return None

    if "Current Value" not in portfolio_df.columns:
        return None

    df = portfolio_df.copy()
    df["Weight %"] = (
        pd.to_numeric(df["Current Value"], errors="coerce").fillna(0)
        / pd.to_numeric(df["Current Value"], errors="coerce").fillna(0).sum()
    ) * 100

    fig = px.imshow(
        [df["Weight %"]],
        labels=dict(color="Portfolio Weight %"),
        x=df.get("Ticker", pd.Series(range(len(df)))),
        y=["Weight %"],
        color_continuous_scale="Blues",
    )
    fig.update_layout(height=300, title="Portfolio Allocation Heat Map")
    return fig


# ============================================================
# 2️⃣ GAIN / LOSS HEAT MAP
# ============================================================
def generate_gain_heatmap(portfolio_df):
    if portfolio_df is None or portfolio_df.empty:
        return None

    gain_col = None
    for cand in ["Gain/Loss %", "Total Gain/Loss Percent", "Today's Gain/Loss Percent"]:
        if cand in portfolio_df.columns:
            gain_col = cand
            break

    if not gain_col:
        return None

    gain_series = pd.to_numeric(portfolio_df[gain_col], errors="coerce").fillna(0)

    fig = px.imshow(
        [gain_series],
        labels=dict(color=gain_col),
        x=portfolio_df.get("Ticker", pd.Series(range(len(gain_series)))),
        y=[gain_col],
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(height=300, title="Gain/Loss % Heat Map")
    return fig


# ============================================================
# 3️⃣ ZACKS COMPOSITE SCORE HEAT MAP
# ============================================================
def generate_composite_score_heatmap(scored_df):
    if scored_df is None or scored_df.empty:
        return None

    if "CompositeScore" not in scored_df.columns:
        return None

    comp_df = scored_df[["Ticker", "CompositeScore"]].reset_index(drop=True)

    fig = px.imshow(
        [comp_df["CompositeScore"]],
        labels=dict(color="Composite Score"),
        x=comp_df["Ticker"],
        y=["Composite Score"],
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=300, title="Zacks Composite Score Heat Map")
    return fig


# ============================================================
# 4️⃣ CORRELATION MATRIX (Portfolio Numeric Relationships)
# ============================================================
def generate_correlation_matrix(portfolio_df):
    if portfolio_df is None or portfolio_df.empty:
        return None

    numeric_cols = portfolio_df.select_dtypes(include=["float", "int"]).columns
    if len(numeric_cols) < 2:
        return None

    corr = portfolio_df[numeric_cols].corr()

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, cmap="coolwarm", annot=True, fmt=".2f", linewidths=0.5, ax=ax)
    ax.set_title("Portfolio Correlation Matrix")
    return fig


# ============================================================
# 5️⃣ HISTORICAL PORTFOLIO TREND CHART
# ============================================================
def generate_portfolio_history_chart(hist_df):
    if hist_df is None or hist_df.empty:
        return None

    try:
        fig = px.line(
            hist_df.sort_values("Date"),
            x="Date",
            y="Total Value",
            markers=True,
            title="Historical Portfolio Value Trend",
        )
        fig.update_layout(height=400)
        return fig
    except Exception:
        return None


# ============================================================
# 6️⃣ HISTORICAL ZACKS SCREEN SIZE TREND
# ============================================================
def generate_zacks_screen_history(pivot_df):
    if pivot_df is None or pivot_df.empty:
        return None

    try:
        fig = px.imshow(
            pivot_df.values,
            labels=dict(color="Tickers"),
            x=list(pivot_df.columns),
            y=list(pivot_df.index),
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=350, title="Historical Zacks Screen Size Heat Map")
        return fig
    except Exception:
        return None

