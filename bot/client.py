"""
Thin wrapper around the Binance Futures (USDT-M) Testnet REST API.

Implemented with plain `requests` + HMAC-SHA256 signing rather than the
python-binance library, so the request/response cycle is fully visible
and easy to log/debug. Every request and response (or error) is logged.

Docs: https://binance-docs.github.io/apidocs/testnet/en/
"""

import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")


class BinanceAPIError(Exception):
    """Raised when Binance returns an error response (non-2xx or {code, msg})."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class BinanceNetworkError(Exception):
    """Raised when a request fails due to a network/connection issue."""


class BinanceFuturesClient:
    """
    Minimal signed REST client for Binance Futures Testnet (USDT-M).

    Only implements what this bot needs: placing orders and a basic
    connectivity/account check. Extend as needed.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://testnet.binancefuture.com",
        recv_window: int = 5000,
        timeout: int = 10,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key and API secret are required.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # -- internal helpers ---------------------------------------------------

    def _sign(self, params: dict) -> dict:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(self, method: str, endpoint: str, params: dict | None = None, signed: bool = True) -> dict:
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        if signed:
            params = self._sign(params)

        # Log the outgoing request (redacting the signature/secret)
        safe_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST %s %s params=%s", method, url, safe_params)

        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("NETWORK ERROR %s %s -> %s", method, url, exc)
            raise BinanceNetworkError(f"Network error calling {endpoint}: {exc}") from exc

        logger.debug("RESPONSE %s %s status=%s body=%s", method, url, response.status_code, response.text)

        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code != 200:
            msg = data.get("msg", "Unknown error") if isinstance(data, dict) else str(data)
            code = data.get("code") if isinstance(data, dict) else None
            logger.error("API ERROR %s %s -> status=%s code=%s msg=%s", method, url, response.status_code, code, msg)
            raise BinanceAPIError(
                f"Binance API error ({response.status_code}, code={code}): {msg}",
                status_code=response.status_code,
                payload=data,
            )

        return data

    # -- public API -----------------------------------------------------

    def ping(self) -> dict:
        """Basic connectivity test (unsigned)."""
        return self._request("GET", "/fapi/v1/ping", signed=False)

    def get_account(self) -> dict:
        """Fetch account info (balances, positions) - useful for sanity checks."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place an order on Binance Futures Testnet.

        order_type: MARKET | LIMIT | STOP (stop-limit)
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP" if order_type == "STOP" else order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP":
            # Stop-Limit: triggers a LIMIT order once stopPrice is reached
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force

        logger.info(
            "Placing %s %s order: symbol=%s qty=%s price=%s stopPrice=%s",
            side, order_type, symbol, quantity, price, stop_price,
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)
