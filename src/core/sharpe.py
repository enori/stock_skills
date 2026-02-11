"""Sharpe Ratio calculation and 5-condition framework."""

import numpy as np
from typing import Any, Optional

DEFAULT_RF = 0.005  # 0.5% Japan default


def calculate_hv(close_prices: list[float], window: int = 30) -> Optional[float]:
    """Annualized historical volatility from close prices.
    Returns None if insufficient data (need window+1 prices).
    Uses log returns, annualized with sqrt(252).
    """
    if len(close_prices) < window + 1:
        return None
    prices = np.array(close_prices[-(window + 1):], dtype=np.float64)
    if np.any(prices <= 0):
        return None
    log_returns = np.diff(np.log(prices))
    std = np.std(log_returns, ddof=1)
    return float(std * np.sqrt(252))


def calculate_upside_downside_vol(
    close_prices: list[float], window: int = 30
) -> tuple[Optional[float], Optional[float]]:
    """Separate upside and downside annualized volatility.
    Returns (upside_vol, downside_vol).
    """
    if len(close_prices) < window + 1:
        return (None, None)
    prices = np.array(close_prices[-(window + 1):], dtype=np.float64)
    if np.any(prices <= 0):
        return (None, None)
    log_returns = np.diff(np.log(prices))

    up_returns = log_returns[log_returns > 0]
    down_returns = log_returns[log_returns < 0]

    if len(up_returns) < 2:
        upside_vol = None
    else:
        upside_vol = float(np.std(up_returns, ddof=1) * np.sqrt(252))

    if len(down_returns) < 2:
        downside_vol = None
    else:
        downside_vol = float(np.std(down_returns, ddof=1) * np.sqrt(252))

    return (upside_vol, downside_vol)


def calculate_expected_return(
    eps_growth: Optional[float],
    dividend_yield: Optional[float],
    fcf_yield: Optional[float],
) -> float:
    """expected_return = eps_growth + dividend_yield + fcf_yield.
    None values treated as 0.
    """
    eg = eps_growth if eps_growth is not None else 0.0
    dy = dividend_yield if dividend_yield is not None else 0.0
    fy = fcf_yield if fcf_yield is not None else 0.0
    return eg + dy + fy


def calculate_adjusted_sr(
    expected_return: float,
    rf: float,
    hv30: float,
    hv90: Optional[float],
    upside_vol: Optional[float],
    downside_vol: Optional[float],
) -> Optional[float]:
    """adjusted_sr = sr * vol_trend * min(asymmetry, 2.0)

    sr = (expected_return - rf) / (hv30 * 0.8)
    vol_trend = hv90 / hv30 (>1 means declining vol, good)
    asymmetry = upside_vol / downside_vol (>1 means upward bias, good)

    Returns None if hv30 is None or <= 0.
    """
    if hv30 is None or hv30 <= 0:
        return None

    sr = (expected_return - rf) / (hv30 * 0.8)

    # vol_trend: default 1.0 if hv90 not available
    if hv90 is not None and hv30 > 0:
        vol_trend = hv90 / hv30
    else:
        vol_trend = 1.0

    # asymmetry: default 1.0 if either vol is unavailable
    if upside_vol is not None and downside_vol is not None and downside_vol > 0:
        asymmetry = min(upside_vol / downside_vol, 2.0)
    else:
        asymmetry = 1.0

    return float(sr * vol_trend * asymmetry)


def check_low_volatility(hv30: Optional[float], threshold: float = 0.25) -> bool:
    """Condition 1: HV30 < threshold (default 25%)."""
    if hv30 is None:
        return False
    return hv30 < threshold


def check_undervalued(
    per: Optional[float],
    pbr: Optional[float],
    per_max: float = 15.0,
    pbr_max: float = 1.5,
) -> bool:
    """Condition 2: 0 < PER < per_max AND 0 < PBR < pbr_max."""
    if per is None or pbr is None:
        return False
    return (0 < per < per_max) and (0 < pbr < pbr_max)


def check_financial_stability(
    equity_ratio: Optional[float],
    operating_cf: Optional[float],
    net_income: Optional[float],
    fcf: Optional[float],
    total_debt: Optional[float],
    ebitda: Optional[float],
) -> bool:
    """Condition 3: ALL of:
    - equity_ratio > 0.40
    - operating_cf > net_income (earnings quality)
    - fcf > 0
    - debt/ebitda < 3.0 (if ebitda > 0)
    """
    if equity_ratio is None or equity_ratio <= 0.40:
        return False
    if operating_cf is None or net_income is None or operating_cf <= net_income:
        return False
    if fcf is None or fcf <= 0:
        return False
    # debt/ebitda check: only enforced when ebitda is positive
    if ebitda is not None and ebitda > 0:
        debt = total_debt if total_debt is not None else 0.0
        if debt / ebitda >= 3.0:
            return False
    # If ebitda is None or <= 0, skip the debt/ebitda check
    # (we cannot compute a meaningful ratio)
    if ebitda is not None and ebitda <= 0:
        return False
    return True


def check_eps_growth(
    eps_growth: Optional[float],
    revenue_growth: Optional[float],
    roe: Optional[float],
) -> bool:
    """Condition 4: ALL of: eps_growth > 5%, revenue_growth > 0%, roe > 8%."""
    if eps_growth is None or eps_growth <= 0.05:
        return False
    if revenue_growth is None or revenue_growth <= 0.0:
        return False
    if roe is None or roe <= 0.08:
        return False
    return True


def count_conditions_passed(
    stock_detail: dict, thresholds: dict
) -> tuple[int, dict[str, Any]]:
    """Evaluate conditions 1-4 (condition 5 catalyst is None/out of scope).

    Returns (count_passed, {condition_name: bool_or_None}).
    """
    hv_threshold = thresholds.get("hv_threshold", 0.25)
    per_max = thresholds.get("per_max", 15.0)
    pbr_max = thresholds.get("pbr_max", 1.5)

    # Extract fields from stock_detail
    hv30 = stock_detail.get("hv30")
    per = stock_detail.get("trailingPE") or stock_detail.get("per")
    pbr = stock_detail.get("priceToBook") or stock_detail.get("pbr")

    equity_ratio = stock_detail.get("equity_ratio")
    operating_cf = stock_detail.get("operating_cashflow") or stock_detail.get("operatingCashflow")
    net_income = stock_detail.get("net_income_stmt") or stock_detail.get("netIncome") or stock_detail.get("net_income")
    fcf = stock_detail.get("fcf") or stock_detail.get("free_cashflow") or stock_detail.get("freeCashflow")
    total_debt = stock_detail.get("total_debt") or stock_detail.get("totalDebt")
    ebitda = stock_detail.get("ebitda")

    eps_growth = stock_detail.get("earningsGrowth") or stock_detail.get("eps_growth")
    revenue_growth = stock_detail.get("revenueGrowth") or stock_detail.get("revenue_growth")
    roe = stock_detail.get("returnOnEquity") or stock_detail.get("roe")

    c1 = check_low_volatility(hv30, threshold=hv_threshold)
    c2 = check_undervalued(per, pbr, per_max=per_max, pbr_max=pbr_max)
    c3 = check_financial_stability(equity_ratio, operating_cf, net_income, fcf, total_debt, ebitda)
    c4 = check_eps_growth(eps_growth, revenue_growth, roe)

    details: dict[str, Any] = {
        "low_volatility": c1,
        "undervalued": c2,
        "financial_stability": c3,
        "eps_growth": c4,
        "catalyst": None,  # condition 5 out of scope
    }

    passed = sum(1 for v in [c1, c2, c3, c4] if v)
    return (passed, details)


def calculate_condition_multiplier(passed_count: int) -> Optional[float]:
    """4+ -> 1.0, 3 -> 0.8, 2 or less -> None (excluded)."""
    if passed_count >= 4:
        return 1.0
    if passed_count == 3:
        return 0.8
    return None


def compute_full_sharpe_score(
    stock_detail: dict, thresholds: dict, rf: float = DEFAULT_RF
) -> Optional[dict]:
    """Main entry point. Computes everything for one stock.

    1. Calculate HV30, HV90, upside/downside vol from stock_detail["price_history"]
    2. Calculate expected_return from eps_growth + dividend_yield + fcf_yield
       (fcf_yield = fcf/market_cap or free_cashflow/market_cap)
    3. Calculate adjusted_sr
    4. Count conditions passed, get multiplier
    5. If multiplier is None -> return None (excluded)
    6. final_score = adjusted_sr * multiplier
    7. Cap expected_return at 1.0 (100%) to prevent outliers

    Returns dict with: expected_return, hv30, hv90, upside_vol, downside_vol,
    raw_sr, adjusted_sr, conditions_passed, condition_details, condition_multiplier,
    final_score, fcf_yield, rf
    """
    price_history = stock_detail.get("price_history", [])

    # Step 1: Volatility calculations
    hv30 = calculate_hv(price_history, window=30)
    hv90 = calculate_hv(price_history, window=90)
    upside_vol, downside_vol = calculate_upside_downside_vol(price_history, window=30)

    # Inject hv30 into stock_detail so count_conditions_passed can use it
    stock_detail_with_hv = {**stock_detail, "hv30": hv30}

    # Step 2: Expected return (use our standard field names)
    eps_growth = stock_detail.get("eps_growth") or stock_detail.get("earnings_growth")
    dividend_yield = stock_detail.get("dividend_yield")

    # fcf_yield: use provided value, or compute from fcf / market_cap
    fcf_yield = stock_detail.get("fcf_yield")
    if fcf_yield is None:
        fcf = stock_detail.get("fcf") or stock_detail.get("free_cashflow")
        market_cap = stock_detail.get("market_cap")
        if fcf is not None and market_cap is not None and market_cap > 0:
            fcf_yield = fcf / market_cap
        else:
            fcf_yield = None

    expected_return = calculate_expected_return(eps_growth, dividend_yield, fcf_yield)

    # Step 7 (early): Cap expected_return at 1.0 (100%)
    expected_return = min(expected_return, 1.0)

    # Step 3: Adjusted Sharpe Ratio
    if hv30 is None or hv30 <= 0:
        raw_sr = None
        adjusted_sr = None
    else:
        raw_sr = (expected_return - rf) / (hv30 * 0.8)
        adjusted_sr = calculate_adjusted_sr(expected_return, rf, hv30, hv90, upside_vol, downside_vol)

    # Step 4: Conditions
    conditions_passed, condition_details = count_conditions_passed(stock_detail_with_hv, thresholds)
    condition_multiplier = calculate_condition_multiplier(conditions_passed)

    # Step 5: Exclude if multiplier is None
    if condition_multiplier is None:
        return None

    # Step 6: Final score
    if adjusted_sr is not None:
        final_score = adjusted_sr * condition_multiplier
    else:
        final_score = None

    return {
        "expected_return": expected_return,
        "hv30": hv30,
        "hv90": hv90,
        "upside_vol": upside_vol,
        "downside_vol": downside_vol,
        "raw_sr": raw_sr,
        "adjusted_sr": adjusted_sr,
        "conditions_passed": conditions_passed,
        "condition_details": condition_details,
        "condition_multiplier": condition_multiplier,
        "final_score": final_score,
        "fcf_yield": fcf_yield,
        "rf": rf,
    }
