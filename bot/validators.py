"""
Input validation for order parameters.

Kept independent of the CLI/network layers so the same rules can be
unit-tested or reused (e.g. if a UI is added later).
"""

import re

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}  # STOP = bonus stop-limit type
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when user-supplied order parameters are invalid."""


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected uppercase alphanumeric, e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT, or STOP).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, required: bool) -> float | None:
    if price is None or price == "":
        if required:
            raise ValidationError("Price is required for LIMIT/STOP orders.")
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError("Price must be greater than 0.")
    return price


def validate_stop_price(stop_price, required: bool) -> float | None:
    if stop_price is None or stop_price == "":
        if required:
            raise ValidationError("Stop price is required for STOP orders.")
        return None
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if stop_price <= 0:
        raise ValidationError("Stop price must be greater than 0.")
    return stop_price


def validate_order_params(symbol, side, order_type, quantity, price=None, stop_price=None) -> dict:
    """Validate a full set of order parameters and return the normalized dict."""
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    quantity = validate_quantity(quantity)
    price = validate_price(price, required=(order_type in {"LIMIT", "STOP"}))
    stop_price = validate_stop_price(stop_price, required=(order_type == "STOP"))

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
    }
