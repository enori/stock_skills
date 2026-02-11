"""Value stock screening engine."""

from pathlib import Path
from typing import Optional

import yaml

from src.core.filters import apply_filters
from src.core.indicators import calculate_value_score
from src.core.sharpe import compute_full_sharpe_score

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "screening_presets.yaml"


def _load_preset(preset_name: str) -> dict:
    """Load screening criteria from the presets YAML file."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    presets = config.get("presets", {})
    if preset_name not in presets:
        raise ValueError(f"Unknown preset: '{preset_name}'. Available: {list(presets.keys())}")
    return presets[preset_name].get("criteria", {})


class ValueScreener:
    """Screen stocks for value investment opportunities."""

    def __init__(self, yahoo_client, market):
        """Initialise the screener.

        Parameters
        ----------
        yahoo_client : module or object
            Must expose ``get_stock_info(symbol) -> dict | None``.
        market : Market
            Must expose ``get_default_symbols() -> list[str]``
            and ``get_thresholds() -> dict``.
        """
        self.yahoo_client = yahoo_client
        self.market = market

    def screen(
        self,
        symbols: Optional[list[str]] = None,
        criteria: Optional[dict] = None,
        preset: Optional[str] = None,
        top_n: int = 20,
    ) -> list[dict]:
        """Run the screening process and return the top results.

        Parameters
        ----------
        symbols : list[str], optional
            Ticker symbols to screen. Defaults to the market's default list.
        criteria : dict, optional
            Filter criteria (e.g. ``{'max_per': 15, 'min_roe': 0.05}``).
        preset : str, optional
            Name of a preset defined in ``config/screening_presets.yaml``.
            Ignored when *criteria* is explicitly provided.
        top_n : int
            Maximum number of results to return, sorted by value score descending.

        Returns
        -------
        list[dict]
            Each dict contains: symbol, name, price, per, pbr,
            dividend_yield, roe, value_score.
        """
        # Resolve symbols
        if symbols is None:
            symbols = self.market.get_default_symbols()

        # Resolve criteria (explicit criteria takes priority over preset)
        if criteria is None:
            if preset is not None:
                criteria = _load_preset(preset)
            else:
                criteria = {}

        thresholds = self.market.get_thresholds()

        results: list[dict] = []

        for symbol in symbols:
            data = self.yahoo_client.get_stock_info(symbol)
            if data is None:
                continue

            # Apply filter criteria
            if not apply_filters(data, criteria):
                continue

            # Calculate value score
            score = calculate_value_score(data, thresholds)

            results.append({
                "symbol": data.get("symbol", symbol),
                "name": data.get("name"),
                "price": data.get("price"),
                "per": data.get("per"),
                "pbr": data.get("pbr"),
                "dividend_yield": data.get("dividend_yield"),
                "roe": data.get("roe"),
                "value_score": score,
            })

        # Sort by value_score descending, take top N
        results.sort(key=lambda r: r["value_score"], reverse=True)
        return results[:top_n]


class SharpeScreener:
    """Screen stocks using the Sharpe Ratio optimization framework."""

    def __init__(self, yahoo_client, market):
        self.yahoo_client = yahoo_client
        self.market = market

    def screen(
        self,
        symbols: Optional[list[str]] = None,
        top_n: int = 20,
    ) -> list[dict]:
        """Run SR screening. Stocks with fewer than 3 conditions are excluded."""
        if symbols is None:
            symbols = self.market.get_default_symbols()

        thresholds = self.market.get_thresholds()
        # SR framework uses its own thresholds (KIK-330 spec)
        thresholds["hv30_max"] = 0.25
        thresholds["per_max"] = 15.0
        thresholds["pbr_max"] = 1.5
        rf = thresholds.get("rf", 0.005)

        results: list[dict] = []

        for symbol in symbols:
            detail = self.yahoo_client.get_stock_detail(symbol)
            if detail is None:
                continue

            sr_result = compute_full_sharpe_score(detail, thresholds, rf=rf)
            if sr_result is None:
                continue

            results.append({
                "symbol": detail.get("symbol", symbol),
                "name": detail.get("name"),
                "price": detail.get("price"),
                "per": detail.get("per"),
                "pbr": detail.get("pbr"),
                "dividend_yield": detail.get("dividend_yield"),
                "roe": detail.get("roe"),
                "eps_growth": detail.get("eps_growth"),
                "hv30": sr_result["hv30"],
                "expected_return": sr_result["expected_return"],
                "adjusted_sr": sr_result["adjusted_sr"],
                "conditions_passed": sr_result["conditions_passed"],
                "condition_details": sr_result["condition_details"],
                "final_score": sr_result["final_score"],
            })

        results.sort(key=lambda r: r["final_score"], reverse=True)
        return results[:top_n]
