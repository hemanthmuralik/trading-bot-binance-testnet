#!/usr/bin/env python3
"""
CLI entry point for the Simplified Binance Futures Testnet Trading Bot.

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Stop-limit order (bonus):
    python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 \\
        --price 60000 --stop-price 60500

Dry run (no real API call, no keys required):
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run

API credentials are read from the BINANCE_API_KEY / BINANCE_API_SECRET
environment variables, or can be passed explicitly with --api-key/--api-secret.
"""

import argparse
import os
import sys

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logging
from bot.orders import OrderManager

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place Market/Limit/Stop orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", default=None, help="Limit price (required for LIMIT/STOP)")
    parser.add_argument("--stop-price", default=None, help="Stop trigger price (required for STOP)")

    parser.add_argument("--api-key", default=os.environ.get("BINANCE_API_KEY"),
                         help="Binance Testnet API key (or set BINANCE_API_KEY env var)")
    parser.add_argument("--api-secret", default=os.environ.get("BINANCE_API_SECRET"),
                         help="Binance Testnet API secret (or set BINANCE_API_SECRET env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                         help=f"API base URL (default: {DEFAULT_BASE_URL})")

    parser.add_argument("--dry-run", action="store_true",
                         help="Validate and print the order without sending it to Binance")
    parser.add_argument("--verbose", action="store_true", help="Verbose console logging (DEBUG level)")

    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(verbose=args.verbose)

    if not args.dry_run and (not args.api_key or not args.api_secret):
        print(
            "[FAILED] API key/secret not provided. Set BINANCE_API_KEY / BINANCE_API_SECRET "
            "env vars, pass --api-key/--api-secret, or use --dry-run to test without credentials."
        )
        return 1

    client = None
    if not args.dry_run:
        try:
            client = BinanceFuturesClient(
                api_key=args.api_key, api_secret=args.api_secret, base_url=args.base_url
            )
        except ValueError as exc:
            logger.error("Failed to initialize client: %s", exc)
            print(f"[FAILED] {exc}")
            return 1

    manager = OrderManager(client=client, dry_run=args.dry_run)

    result = manager.place_order(
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
    )

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
