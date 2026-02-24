# Suggested Commands

## Testing
```bash
# Run all tests (~1706 tests, ~5s)
python3 -m pytest tests/ -q

# Run specific test file
python3 -m pytest tests/core/test_screener.py -q

# Run specific test
python3 -m pytest tests/core/test_screener.py::test_function_name -q
```

## Skills Execution
```bash
# Screening (EquityQuery)
python3 .claude/skills/screen-stocks/scripts/run_screen.py --region japan --preset value --top 10

# Trending (requires ANTHROPIC_API_KEY)
python3 .claude/skills/screen-stocks/scripts/run_screen.py --region japan --preset trending --top 10

# Stock report
python3 .claude/skills/stock-report/scripts/generate_report.py 7203.T

# Market research (stock/industry/market/business)
python3 .claude/skills/market-research/scripts/run_research.py stock 7203.T

# Watchlist
python3 .claude/skills/watchlist/scripts/manage_watchlist.py list

# Portfolio
python3 .claude/skills/stock-portfolio/scripts/run_portfolio.py snapshot
python3 .claude/skills/stock-portfolio/scripts/run_portfolio.py health

# Stress test
python3 .claude/skills/stress-test/scripts/run_stress_test.py --portfolio 7203.T,AAPL

# Investment note
python3 .claude/skills/investment-note/scripts/manage_note.py list

# Graph query
python3 .claude/skills/graph-query/scripts/run_query.py "7203.Tの前回レポートは？"

# Auto context injection
python3 scripts/get_context.py "<user input>"
```

## Dependencies
```bash
pip install -r requirements.txt
```

## Neo4j Schema Init
```bash
python3 scripts/init_graph.py
```

## Git
```bash
git status
git diff
git log --oneline -10
```

## System Utils (Linux)
```bash
ls, cd, grep, find, cat, head, tail
```
