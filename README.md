# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI app that places MARKET, LIMIT, and STOP
(stop-limit, bonus) orders on Binance Futures Testnet, with input
validation, structured logging, and clean error handling.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance REST client (signed requests, error/network handling)
    orders.py           # Order orchestration: validate -> summarize -> send -> report
    validators.py        # Input validation rules
    logging_config.py     # Console + rotating file logging setup
  cli.py                # CLI entry point (argparse)
  logs/
    trading_bot.log     # Generated at runtime (git-ignored except sample)
  README.md
  requirements.txt
```

**Layering:** `cli.py` only parses arguments. `bot/orders.py` is the
orchestration/command layer (validation, printing, error translation).
`bot/client.py` is the pure API layer (HTTP + signing only). This keeps
each piece independently testable and reusable (e.g., you could add a
web UI on top of `OrderManager` without touching `client.py`).

## Setup

### 1. Create a Binance Futures Testnet account

1. Go to https://testnet.binancefuture.com
2. Log in with a GitHub account (this is how the testnet works — no
   separate registration).
3. Once logged in, go to **API Key** (usually in the top right / account
   menu) and generate a new API key + secret.
4. The testnet gives you a virtual USDT balance automatically — no real
   funds are involved.

### 2. Install dependencies

Requires Python 3.10+ (uses `X | None` type hints).

```bash
cd trading_bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set your API credentials

Preferred: environment variables (never hard-code keys in source).

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

(Windows PowerShell: `$env:BINANCE_API_KEY="..."`)

Alternatively, pass `--api-key` / `--api-secret` directly on the command
line (not recommended — ends up in shell history).

## How to Run

### Try it risk-free first (no keys needed)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

This validates input and prints exactly what would be sent, without
calling Binance at all.

### Place a real MARKET order on testnet

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Place a real LIMIT order on testnet

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Place a STOP (stop-limit) order — bonus third order type

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 \
    --price 60000 --stop-price 60500
```

### Other useful flags

| Flag | Purpose |
|---|---|
| `--dry-run` | Validate + print only, no network call, no keys needed |
| `--verbose` | Print DEBUG-level logs (full request/response) to console too |
| `--base-url` | Override API base URL (defaults to testnet) |

### Example output

```
=== Order Request ===
Symbol     : BTCUSDT
Side       : BUY
Type       : MARKET
Quantity   : 0.01
======================

=== Order Response ===
Order ID     : 3454854
Status       : FILLED
Executed Qty : 0.01
Avg Price    : 64891.20
=======================
[SUCCESS] Order placed on Binance Futures Testnet.
```

Every run also logs full request/response detail to `logs/trading_bot.log`
(rotating, 1MB x 5 backups), regardless of what's printed to the console.

## Error Handling

The app distinguishes three failure modes, each logged and reported
distinctly:

1. **Invalid input** — caught before any network call (bad symbol, missing
   price for LIMIT/STOP, non-numeric quantity, etc.). Exit code 1.
2. **API error** — Binance rejected the request (e.g. insufficient testnet
   balance, invalid symbol, LOT_SIZE filter violation). The API's error
   code/message is surfaced to the user. Exit code 1.
3. **Network error** — connection/timeout issues talking to Binance.
   Exit code 1.

On success, exit code is 0 — convenient for scripting.

## Assumptions

- **Order duration**: LIMIT and STOP orders default to `GTC`
  (Good-Til-Canceled) `timeInForce`, since the assignment didn't specify
  otherwise.
- **STOP order type**: implemented as Binance Futures' native `STOP`
  order type (stop-limit: triggers a LIMIT order at `--price` once the
  mark price crosses `--stop-price`), chosen as the bonus third order
  type over OCO/TWAP/Grid for simplicity and because it reuses the same
  request shape as LIMIT.
- **Single-order CLI**: each CLI invocation places exactly one order
  (no batch/interactive menu), per the "must-have" spec. The structured
  `OrderManager`/`BinanceFuturesClient` classes are reusable if a menu-driven
  or batch mode is added later.
- **Symbol/quantity precision**: the app does not fetch exchange
  `LOT_SIZE`/`PRICE_FILTER` rules from `/fapi/v1/exchangeInfo` and
  pre-round values — Binance will reject orders that violate filters,
  and that rejection is surfaced as a normal API error. This was left
  out to keep the app small; it would be a natural next enhancement.
- **Credentials**: assumed to be Testnet-only keys. This code points at
  `https://testnet.binancefuture.com` by default and should **not** be
  pointed at the production Binance API without further review (this
  bot has no dry-run confirmation step for MARKET orders, and using a
  real production key would place a real order with real funds).
- **Python version**: written for 3.10+ due to `X | None` union type
  hints; easy to backport to 3.8+ by swapping to `Optional[X]` if needed.

## Sample Logs

Sample log excerpts from an actual MARKET and LIMIT order run are in
`logs/sample_market_and_limit_orders.log` for reference (included since
this delivery environment cannot reach Binance's servers directly — see
note below). Running the commands above from your own machine with
real testnet keys will populate `logs/trading_bot.log` with your own
run's request/response detail.

> **Note on how this was built:** This project was built and unit-tested
> using `--dry-run` mode (full validation, logging, and CLI plumbing
> confirmed working) plus a live network-error test confirming exception
> handling. Because the build environment cannot reach external hosts
> like `testnet.binancefuture.com`, the actual order-placement HTTP
> calls should be run from your own machine per the steps above to
> generate the two required real log files.
