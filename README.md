# 🧭 Fox Valley Intelligence Engine — Final Tactical Assembly (v7.3R)

## 📌 Overview
The Fox Valley Intelligence Engine is a Python-based tactical decision system for portfolio analysis, equity screening, risk alerts, stop-loss signaling, and exportable tactical briefs for executive review.

This build is **fully Streamlit-free**. It operates as a **pure Python CLI tactical console**, with full compatibility for future expansion into Flask, desktop UI, or API-driven platforms.

---

## 🚀 Operational Features (Final Assembly)

| Module | Function |
|--------|----------|
| Portfolio Loader | Reads the most recent Portfolio CSV from `/data` |
| Zacks Crossmatching | Matches portfolio tickers to Growth1, Growth2, Defensive Dividend screens |
| Tactical Scoring Engine | Generates Buy, Strong Buy, Hold, Trim, Sell tactical signals |
| Performance Analysis | Computes Gain/Loss % using Cost Basis and Current Price |
| Stop Logic Engine | Issues Stop Loss Trigger or Trim → Secure Profits |
| Report Generator | Auto-exports full tactical intelligence file (CSV + PDF) |

---

## 📂 Project Folder Structure

