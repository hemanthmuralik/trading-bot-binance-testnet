"""
Order orchestration layer: sits between the CLI and the API client.

Responsible for:
- validating input (via validators.py)
- printing a clear request summary before sending
- calling the client
- printing a clear response summary / success-failure message
- translating exceptions into a consistent OrderResult
"""

import logging
from dataclasses import dataclass, field

from bot.client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from bot.validators import ValidationError, validate_order_params

logger = logging.getLogger("trading_bot.orders")


@dataclass
class OrderResult:
    success: bool
    message: str
    raw_response: dict = field(default_factory=dict)


class OrderManager:
    """High-level order placement, used by the CLI layer."""

    def __init__(self, client: BinanceFuturesClient | None, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run
        if not dry_run and client is None:
            raise ValueError("A BinanceFuturesClient is required when dry_run=False.")

    def place_order(
        self, symbol, side, order_type, quantity, price=None, stop_price=None
    ) -> OrderResult:
        # 1. Validate input
        try:
            params = validate_order_params(
                symbol=symbol, side=side, order_type=order_type,
                quantity=quantity, price=price, stop_price=stop_price,
            )
        except ValidationError as exc:
            logger.warning("Validation failed: %s", exc)
            print(f"\n[FAILED] Invalid input: {exc}\n")
            return OrderResult(success=False, message=str(exc))

        # 2. Print request summary
        self._print_request_summary(params)

        # 3. Dry-run short-circuit (no network call)
        if self.dry_run:
            fake_response = {
                "orderId": "DRY-RUN",
                "status": "SIMULATED",
                "executedQty": "0",
                "avgPrice": "0",
                "symbol": params["symbol"],
                "side": params["side"],
                "type": params["order_type"],
            }
            logger.info("DRY RUN - no request sent. Simulated params=%s", params)
            self._print_response_summary(fake_response, success=True, dry_run=True)
            return OrderResult(success=True, message="Dry run - no order sent.", raw_response=fake_response)

        # 4. Call the API, handling errors distinctly
        try:
            response = self.client.place_order(
                symbol=params["symbol"],
                side=params["side"],
                order_type=params["order_type"],
                quantity=params["quantity"],
                price=params["price"],
                stop_price=params["stop_price"],
            )
        except BinanceAPIError as exc:
            logger.error("Order failed (API error): %s", exc)
            print(f"\n[FAILED] Binance API rejected the order: {exc}\n")
            return OrderResult(success=False, message=str(exc), raw_response=exc.payload)
        except BinanceNetworkError as exc:
            logger.error("Order failed (network error): %s", exc)
            print(f"\n[FAILED] Network error while placing order: {exc}\n")
            return OrderResult(success=False, message=str(exc))
        except Exception as exc:  # noqa: BLE001 - final safety net, always logged
            logger.exception("Unexpected error placing order")
            print(f"\n[FAILED] Unexpected error: {exc}\n")
            return OrderResult(success=False, message=str(exc))

        # 5. Success
        logger.info("Order placed successfully: %s", response)
        self._print_response_summary(response, success=True)
        return OrderResult(success=True, message="Order placed successfully.", raw_response=response)

    # -- presentation helpers ---------------------------------------------

    @staticmethod
    def _print_request_summary(params: dict) -> None:
        print("\n=== Order Request ===")
        print(f"Symbol     : {params['symbol']}")
        print(f"Side       : {params['side']}")
        print(f"Type       : {params['order_type']}")
        print(f"Quantity   : {params['quantity']}")
        if params["price"] is not None:
            print(f"Price      : {params['price']}")
        if params["stop_price"] is not None:
            print(f"Stop Price : {params['stop_price']}")
        print("======================")

    @staticmethod
    def _print_response_summary(response: dict, success: bool, dry_run: bool = False) -> None:
        print("\n=== Order Response ===")
        print(f"Order ID     : {response.get('orderId', 'N/A')}")
        print(f"Status       : {response.get('status', 'N/A')}")
        print(f"Executed Qty : {response.get('executedQty', 'N/A')}")
        avg_price = response.get("avgPrice")
        if avg_price is not None:
            print(f"Avg Price    : {avg_price}")
        print("=======================")
        if dry_run:
            print("[DRY RUN] No real order was sent to Binance.\n")
        elif success:
            print("[SUCCESS] Order placed on Binance Futures Testnet.\n")
        else:
            print("[FAILED] Order was not placed.\n")
