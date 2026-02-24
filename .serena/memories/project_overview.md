# Project Overview: stock_skills

## Purpose
割安株スクリーニングシステム。Yahoo Finance API（yfinance）を使って日本株・米国株・ASEAN株・香港株・韓国株・台湾株等60地域から割安銘柄をスクリーニングする。Claude Code Skills として動作し、自然言語で話しかけるだけで適切な機能が実行される。

## Design Philosophy
「自然言語ファースト」設計。ユーザーはスラッシュコマンドやパラメータを覚える必要はなく、日本語で意図を伝えるだけで適切なスキルが自動選択・実行される。

## Tech Stack
- **Language**: Python 3.10+
- **Dependencies**: yfinance, pyyaml, numpy, pandas, pytest
- **Optional Services**: Claude API (ANTHROPIC_API_KEY), Neo4j (knowledge graph), TEI (vector embeddings)
- **Environment Variables**:
  - `ANTHROPIC_API_KEY` — Claude API (Web検索)
  - `NEO4J_MODE` — off/summary/full (default: full if connected)
  - `TEI_URL` — TEI endpoint (default: http://localhost:8081)
  - `CONTEXT_FRESH_HOURS` / `CONTEXT_RECENT_HOURS` — Context freshness thresholds

## Architecture (3-Layer)
```
Skills (.claude/skills/*/SKILL.md → scripts/*.py)
  ├─ screen-stocks, stock-report, market-research, watchlist
  ├─ stress-test, investment-note, graph-query, stock-portfolio
  │
Core (src/core/)
  ├─ screening/ — screener, indicators, filters, query_builder, alpha, technicals
  ├─ portfolio/ — portfolio_manager, portfolio_simulation, rebalancer, simulator, backtest, concentration
  ├─ risk/ — correlation, shock_sensitivity, scenario_analysis, recommender
  ├─ research/ — researcher
  ├─ models.py, common.py, ticker_utils.py, health_check.py, return_estimate.py, value_trap.py
  │
Data (src/data/)
  ├─ yahoo_client.py — yfinance wrapper with 24h JSON cache
  ├─ claude_client.py — Claude API Web Search
  ├─ graph_store.py — Neo4j CRUD (dual-write: JSON=master, Neo4j=view)
  ├─ graph_query.py, graph_nl_query.py — Graph query engine
  ├─ history_store.py — Skill execution history (JSON + Neo4j)
  ├─ auto_context.py — Automatic context injection (vector + symbol-based)
  ├─ embedding_client.py — TEI REST API client (384-dim vectors)
  ├─ note_manager.py, screen_annotator.py, summary_builder.py
  │
Markets (src/markets/) — base.py (ABC), japan.py, us.py, asean.py
Output (src/output/) — formatter.py, portfolio_formatter.py, research_formatter.py, stress_formatter.py
```

## 8 Skills
1. **screen-stocks** — 割安株スクリーニング (10 presets × 60 regions)
2. **stock-report** — 個別銘柄レポート (valuation, shareholder return)
3. **market-research** — 深掘りリサーチ (stock/industry/market/business)
4. **watchlist** — ウォッチリスト管理
5. **stress-test** — ポートフォリオ・ストレステスト
6. **stock-portfolio** — ポートフォリオ管理 (snapshot/buy/sell/analyze/health/forecast/rebalance/simulate/what-if/backtest/list)
7. **investment-note** — 投資メモ管理
8. **graph-query** — 知識グラフ自然言語クエリ
