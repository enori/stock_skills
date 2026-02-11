#!/usr/bin/env python3
"""Entry point for the screen-stocks skill."""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from src.data import yahoo_client
from src.core.screener import ValueScreener, SharpeScreener
from src.output.formatter import format_markdown, format_sharpe_markdown
from src.markets.japan import JapanMarket
from src.markets.us import USMarket
from src.markets.asean import ASEANMarket


MARKETS = {
    "japan": JapanMarket,
    "us": USMarket,
    "asean": ASEANMarket,
}


def main():
    parser = argparse.ArgumentParser(description="割安株スクリーニング")
    parser.add_argument("--market", default="japan", choices=["japan", "us", "asean", "all"])
    parser.add_argument("--preset", default="value",
                        choices=["value", "high-dividend", "growth-value", "deep-value", "quality", "sharpe-ratio"])
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    client = yahoo_client

    if args.market == "all":
        markets_to_run = list(MARKETS.items())
    else:
        markets_to_run = [(args.market, MARKETS[args.market])]

    for market_name, market_cls in markets_to_run:
        market = market_cls()

        if args.preset == "sharpe-ratio":
            screener = SharpeScreener(client, market)
            results = screener.screen(top_n=args.top)
            print(f"\n## {market.name} - シャープレシオ最適化 スクリーニング結果\n")
            print(format_sharpe_markdown(results))
        else:
            screener = ValueScreener(client, market)
            results = screener.screen(preset=args.preset, top_n=args.top)
            print(f"\n## {market.name} - {args.preset} スクリーニング結果\n")
            print(format_markdown(results))
        print()


if __name__ == "__main__":
    main()
