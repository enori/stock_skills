# Code Style and Conventions

## Language
- Python 3.10+
- UTF-8 encoding

## Naming
- **Functions/variables**: snake_case (e.g., `get_stock_info`, `_safe_get`)
- **Classes**: PascalCase (e.g., `ValueScreener`, `Position`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `CACHE_DIR`, `CACHE_TTL_HOURS`)
- **Private helpers**: prefixed with underscore (e.g., `_normalize_ratio`, `_cache_path`)

## Type Hints
- Used on function signatures: `def get_stock_info(symbol: str) -> Optional[dict]:`
- Dataclass fields with types: `symbol: str`, `shares: int`, `cost_price: float`

## Docstrings
- NumPy-style docstrings on dataclasses (Attributes section)
- Brief triple-quoted docstrings on functions describing purpose and return value
- Japanese comments in some places (natural for this project's domain)

## Data Classes
- `@dataclass` from dataclasses module
- Include `to_dict()` and `from_dict()` class methods for serialization
- Located in `src/core/models.py`

## Module Patterns
- **yahoo_client**: Module-level functions (not a class). Import as `from src.data import yahoo_client`
- **Screeners**: Class-based with `__init__` and `screen` methods
- **`HAS_MODULE` pattern**: Scripts use `try/except ImportError` for graceful degradation
- **Data access**: Always through `src/data/yahoo_client.py` (never call yfinance directly)
- **Dual-write**: JSON/CSV = master, Neo4j = view

## Import Style
- Direct path imports: `from src.core.screening.screener import AlphaScreener`
- Scripts add project root to sys.path: `sys.path.insert(0, ...)`

## Configuration
- YAML config files in `config/` (screening_presets.yaml, exchanges.yaml, markets.yaml)
- Environment variables for optional services (ANTHROPIC_API_KEY, NEO4J_MODE, TEI_URL)

## Error Handling
- Graceful degradation when optional services unavailable
- `_safe_get()` pattern for dict access with None fallback
- `_sanitize_anomalies()` for data quality
- `_normalize_ratio()` for dividend yield normalization (>1 → divide by 100)
