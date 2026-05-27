# Cross-Currency Conversion Design

This document describes the planned Pixiu tester support for cross-currency pairs and dynamic conversion rates.

The feature is intended for tests where the trading symbol profit or margin currency differs from the account currency, for example:

- Trading `EURGBP` with a `USD` account
- Trading `GBPUSD` with a `JPY` account
- Trading `EURGBP` with a `JPY` account

## Goals

- Calculate order profit in the account currency for cross-currency symbols.
- Calculate margin in the account currency when `currency_margin` differs from the account currency.
- Support dynamic conversion rates from symbol tick data.
- Prepare required conversion symbols before the backtest starts.
- Keep backtest execution deterministic by avoiding network downloads during the tick loop.

## Implementation Status

Implemented in `0.178.0`:

- Dynamic conversion mode through `currency_conversion_settings.mode = "dynamic"`.
- `direct_then_usd` path resolution.
- Direct pair priority before USD bridge conversion.
- Latest conversion tick at or before the current test tick.
- Profit conversion from `currency_profit` to account currency.
- Margin conversion from `currency_margin` to account currency.
- EA-facing `CalcProfit`, `OrderCalcProfit`, `CalcMargin`, `OrderCalcMargin`, `TickValue`, and `PipValue`.
- Per-symbol tick data cache in `PXTester` so inferred conversion symbols can be loaded before the backtest tick loop.

Still planned:

- More download policy options beyond `before_test`.
- More missing-rate strategies beyond failing clearly when no conversion path or tick exists.
- Optional `price_mode: "mid"` for analytical tests.
- Broader multi-symbol order processing beyond the current tester's primary-symbol tick loop.

## Non-Goals

- Do not download conversion data while the backtest is already running.
- Do not silently use a wrong or stale conversion rate when no valid path exists.
- Do not require every test to manually list all conversion symbols when Pixiu can infer them.

## Configuration

Add `currency_conversion_settings` to the test or global config.

```json
{
  "currency_conversion_settings": {
    "mode": "dynamic",
    "auto_download": true,
    "download_policy": "before_test",
    "path_policy": "direct_then_usd",
    "missing_rate": "download_then_error",
    "time_alignment": "latest_before_or_at_tick",
    "price_mode": "bid_ask",
    "fallback_enabled": false
  }
}
```

Fields:

- `mode`: `static` or `dynamic`. Dynamic mode uses conversion symbol tick data.
- `auto_download`: when `true`, Pixiu prepares missing conversion symbols before the test starts.
- `download_policy`: first version should support `before_test` only.
- `path_policy`: first version should support `direct_then_usd`.
- `missing_rate`: first version should support `error` and `download_then_error`.
- `time_alignment`: first version should support `latest_before_or_at_tick`.
- `price_mode`: first version should support `bid_ask`; `mid` can be added later if needed.
- `fallback_enabled`: when `true`, Pixiu can use configured static fallback rates if dynamic data is unavailable.

## Conversion Source Configuration

`currency_conversions` can explicitly describe which symbol should be used for a conversion pair.

```json
{
  "currency_conversions": {
    "GBPUSD": {
      "source": "symbol",
      "symbol": "GBPUSD",
      "price": "bid_ask",
      "fallback": {
        "bid": 1.2500,
        "ask": 1.2502
      }
    },
    "USDJPY": {
      "source": "symbol",
      "symbol": "USDJPY",
      "price": "bid_ask"
    },
    "GBPJPY": {
      "source": "symbol",
      "symbol": "GBPJPY",
      "price": "bid_ask"
    }
  }
}
```

If `currency_conversions` is omitted, Pixiu should infer conversion symbols from `symbols`, account currency, and the conversion path policy.

## Path Policy

The first implementation should use `direct_then_usd`.

For a required conversion from `FROM` to `TO`:

1. If `FROM == TO`, no conversion is required.
2. Try direct symbol: `FROMTO`.
3. Try inverse symbol: `TOFROM`.
4. If neither currency is `USD`, try a USD bridge:
   - `FROM -> USD`
   - `USD -> TO`
5. If no complete path exists, fail clearly before the test starts.

Examples:

```text
GBP -> JPY:
  Prefer GBPJPY.
  If GBPJPY is unavailable, use GBPUSD + USDJPY.

GBP -> USD:
  Prefer GBPUSD.
  If GBPUSD is unavailable, use USDGBP.

CHF -> AUD:
  Prefer CHFAUD.
  If CHFAUD is unavailable, use CHFUSD + USDAUD.
```

## Auto Download Behavior

Auto download should run during a preparation phase before the backtest loop.

```text
1. Read test symbol and account currency.
2. Read symbol metadata:
   - currency_base
   - currency_profit
   - currency_margin
3. Infer required conversions:
   - currency_profit -> account currency
   - currency_margin -> account currency
4. Resolve conversion paths using direct_then_usd.
5. Check local tick data for every required conversion symbol.
6. Download missing conversion symbols if auto_download is true.
7. Validate that all conversion paths have usable data.
8. Start the backtest.
```

Backtest execution must not perform network downloads. This keeps test results reproducible.

## Profit Calculation

Profit should be calculated in the symbol profit currency first, then converted to the account currency.

```text
raw_profit = (close_price - open_price) * volume * trade_contract_size * direction
account_profit = convert_currency(raw_profit, currency_profit, account_currency)
```

Where:

```text
direction = 1 for buy orders
direction = -1 for sell orders
```

Example:

```text
Account currency: USD
Symbol: EURGBP
currency_profit: GBP
Order: BUY 1 lot
Open: 0.8500
Close: 0.8510
Contract size: 100000

raw_profit = (0.8510 - 0.8500) * 100000 = 100 GBP
GBPUSD = 1.2500
account_profit = 125 USD
```

## Margin Calculation

Margin should be calculated in `currency_margin` first, then converted to the account currency.

The exact notional calculation should preserve existing behavior for existing symbols, then generalize through currency conversion.

Suggested first version:

```text
margin_in_margin_currency = calculate_symbol_margin(symbol, open_price, volume)
account_margin = convert_currency(margin_in_margin_currency, currency_margin, account_currency)
```

Existing tests for pairs such as `USDCHF` must continue to pass unchanged.

## Bid/Ask Rules

For the first version, Pixiu should use conservative bid/ask conversion:

```text
Direct pair FROMTO:
  FROM -> TO uses bid.
  TO -> FROM uses 1 / ask.

Inverse pair TOFROM:
  FROM -> TO uses 1 / ask.
  TO -> FROM uses bid.
```

For margin conversion, using the conservative side is preferred. A future option can add `price_mode: "mid"` for simpler analytical tests.

## Time Alignment

Dynamic conversion rates should use the latest conversion tick at or before the current test tick time.

```json
{
  "time_alignment": "latest_before_or_at_tick"
}
```

If no conversion tick exists at or before the current test tick:

- If `fallback_enabled` is `true` and a fallback rate exists, use fallback.
- Otherwise follow `missing_rate`.

## Missing Rate Policy

Suggested first-version policies:

- `error`: fail before or during the test when no conversion rate is available.
- `download_then_error`: during preparation, try to download missing data first; if still unavailable, fail.

The default should be `download_then_error` when `auto_download` is true, otherwise `error`.

## Implementation Notes

Suggested internal helpers:

```python
def resolve_conversion_path(from_currency, to_currency):
    ...

def prepare_currency_conversion_data(test_config):
    ...

def get_conversion_rate(from_currency, to_currency, at_time, purpose):
    ...

def convert_currency(amount, from_currency, to_currency, at_time, purpose):
    ...
```

Suggested integration points:

- Prepare conversion symbols before `EATester.execute_` enters the tick loop.
- Replace profit conversion logic in order profit calculation with `convert_currency`.
- Replace margin currency assumptions in order open checks with `convert_currency`.
- Keep scenario-injected orders compatible by applying the same conversion logic when account equity and margin are recalculated.

## Test Plan

Add regression tests for:

- `EURGBP` with a `USD` account using direct `GBPUSD`.
- `EURGBP` with a `JPY` account using direct `GBPJPY`.
- `EURGBP` with a `JPY` account falling back to `GBPUSD + USDJPY`.
- Inverse conversion when only the reverse symbol exists.
- Missing conversion data produces a clear error.
- Existing `USDCHF` behavior remains unchanged.
