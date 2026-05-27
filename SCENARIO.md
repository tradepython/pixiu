# Scenario JSON Configuration

`scenario` is an optional block under each test item in the test config file.

The config parser uses `pyjson5`, so standard JSON works, and JSON5-style comments/trailing commas also work.

## Location

Put `scenario` under `tests.<test_name>`:

```json
{
  "tests": {
    "scenario_demo": {
      "symbol": "USDCHF",
      "account": "default",
      "tick_data": "./usdchf_m1_20210315-0415.csv",
      "scenario": {
      }
    }
  }
}
```

## Structure

```json
{
  "scenario": {
    "initial_state": {
      "account_overrides": {},
      "orders": [],
      "data": []
    },
    "events": []
  }
}
```

## `initial_state`

`initial_state` is applied after tick data is loaded and before the backtest loop starts.

### `initial_state.account_overrides`

Overrides values in the current test account.

Example:

```json
{
  "account_overrides": {
    "balance": 8000,
    "equity": 8000,
    "free_margin": 8000
  }
}
```

Supported fields depend on the account structure already used by the tester, such as:

- `balance`
- `equity`
- `margin`
- `free_margin`
- `credit`
- `profit`
- `margin_level`
- `leverage`
- `currency`
- `limit_orders`
- `margin_so_call`
- `margin_so_so`
- `commission`

### `initial_state.orders`

Injects existing orders before the test starts.

Example:

```json
{
  "orders": [
    {
      "ticket": 7001,
      "kind": "market",
      "side": "buy",
      "volume": 0.2,
      "open_price": 0.9234,
      "stop_loss": 0.922,
      "take_profit": 0.926,
      "comment": "seed long",
      "count_in_report": false,
      "write_log": false
    },
    {
      "ticket": 7002,
      "kind": "pending",
      "side": "sell_stop",
      "volume": 0.1,
      "open_price": 0.921,
      "stop_loss": 0.9225,
      "take_profit": 0.918
    }
  ]
}
```

Order fields:

- `ticket`: optional, custom ticket id. If omitted, tester generates one.
- `kind`: `market` or `pending`
- `side`: supported values:
  - `buy`
  - `sell`
  - `buy_limit`
  - `sell_limit`
  - `buy_stop`
  - `sell_stop`
- `cmd`: optional. If provided, it overrides `kind` + `side`.
- `symbol`: optional. Default is current test symbol.
- `volume`: required
- `open_price`: optional for market orders, recommended for all injected orders
- `stop_loss`
- `take_profit`
- `comment`
- `magic_number`
- `open_time`: optional. Supports timestamp or ISO datetime string.
- `commission`
- `tags`
- `from_uid`
- `to_uid`
- `status`: optional. For market orders default is `opened`; use `pending` if needed.
- `count_in_report`: optional, default `false` for `initial_state` orders
- `write_log`: optional, default `false`

### `initial_state.data`

Seeds tester persistent runtime data before the main tick loop starts.

This is useful when an EA needs existing runtime state, such as a GridFire `open_info_<SYMBOL>` record, in addition to existing orders.

Example:

```json
{
  "data": [
    {
      "scope": "ACCOUNT_EA",
      "name": "open_info_EURUSD",
      "data": {
        "symbol": "EURUSD",
        "status": "running",
        "stage": 5,
        "orders": ["7001", "7002", "7003", "7004"]
      }
    }
  ]
}
```

Supported fields:

- `scope`: optional. Supports `EA`, `EA_VERSION`, `ACCOUNT`, `EA_SETTINGS`, `ACCOUNT_EA`. Default is `EA`.
- `name`: required.
- `data`: JSON-serializable data.
- `format`: optional. Currently only `json` is supported.

`initial_state.data` also supports an object form:

```json
{
  "data": {
    "ACCOUNT_EA": {
      "open_info_EURUSD": {
        "symbol": "EURUSD",
        "status": "running"
      }
    }
  }
}
```

Aliases:

- `persistent_data`
- `runtime_data`

## `events`

`events` are runtime actions executed during the backtest loop.

Example:

```json
{
  "events": [
    {
      "id": "flash_crash",
      "phase": "pre_tick",
      "at": "2021-03-16T10:05:00Z",
      "action": "mutate_tick",
      "params": {
        "low": 0.91,
        "high": 0.924,
        "close": 0.912,
        "bid": 0.91195,
        "ask": 0.9125
      }
    }
  ]
}
```

Common event fields:

- `id`: optional. If omitted, auto-generated as `scenario_event_<index>`.
- `phase`: optional. Default is `pre_tick`.
- `action`: required.
- `params`: optional action parameters.
- `once`: optional.
- `at`: execute at exact time.
- `from`: start time for a time range event.
- `to`: end time for a time range event.
- `at_tick`: execute at exact tick index.
- `from_tick`: start tick index for a tick range event.
- `to_tick`: end tick index for a tick range event.

Time fields support ISO datetime strings, for example:

```json
"2021-03-16T10:05:00Z"
```

Current behavior:

- time strings are treated as UTC without timezone conversion
- if the input includes a timezone suffix such as `Z` or `+08:00`, the offset part is ignored
- this keeps `scenario.at/from/to` aligned with tester tick time handling

### Event matching rules

An event can be triggered by either:

- exact time: `at`
- time range: `from` + `to`
- exact tick: `at_tick`
- tick range: `from_tick` + `to_tick`

### `phase`

Supported phases:

- `pre_tick`
- `post_order_processing`
- `post_tick`

Meaning:

- `pre_tick`: execute before `Ask/Bid/Close` are read for that tick
- `post_order_processing`: execute after internal order processing
- `post_tick`: execute after strategy code is executed for that tick

### `once`

Default behavior:

- `mutate_tick`: default `once = false`
- `price_path`: default `once = false`
- `override_spread`: default `once = false`
- other actions: default `once = true`

If `once` is `false`, the event will keep applying while its time/tick range still matches.

## Supported actions

### 1. `mutate_tick`

Changes market data on the current tick.

Example:

```json
{
  "action": "mutate_tick",
  "params": {
    "open": 0.913,
    "high": 0.924,
    "low": 0.91,
    "close": 0.912,
    "bid": 0.91195,
    "ask": 0.9125,
    "volume": 999
  }
}
```

Supported fields in `params`:

- short names:
  - `o`
  - `h`
  - `l`
  - `c`
  - `a`
  - `b`
  - `v`
- readable names:
  - `open`
  - `high`
  - `low`
  - `close`
  - `ask`
  - `bid`
  - `volume`
- `delta`: adds offsets to current values

Example with `delta`:

```json
{
  "action": "mutate_tick",
  "params": {
    "delta": {
      "close": -0.005,
      "bid": -0.005,
      "ask": -0.005
    }
  }
}
```

### 2. `price_path`

Generates a continuous price path over a tick/time range. This is useful for quickly building extreme market conditions such as one-way crashes, rallies, gaps, and pullbacks.

Example:

```json
{
  "id": "extreme_downtrend",
  "phase": "pre_tick",
  "from_tick": 10,
  "to_tick": 40,
  "action": "price_path",
  "params": {
    "start_bid": 1.1800,
    "step": -0.0010,
    "spread_point": 20
  }
}
```

Common `params`:

- `start_bid` / `start` / `price`: starting bid
- `end_bid` / `end`: ending bid; when set, Pixiu linearly interpolates over the matched range
- `step`: bid price step per tick
- `step_points`: point step per tick, converted by symbol point
- `spread_point` / `spread_points`: generated spread
- `open` / `high` / `low` / `close` / `ask` / `volume`: optional field overrides
- `high_offset` / `low_offset`: automatic high/low offsets when high/low are not provided

### 3. `override_spread`

Temporarily overrides `spread_point` for the current tick.

Example:

```json
{
  "action": "override_spread",
  "params": {
    "spread_point": 80
  }
}
```

Supported `params`:

- `spread_point`
- `value` (alias of `spread_point`)

Current behavior:

- `spread_point` is updated in tester context
- current tick `ask` is recalculated from `bid + spread`

### 4. `place_order`

Places an order during the test.

Example:

```json
{
  "action": "place_order",
  "phase": "post_order_processing",
  "at_tick": 50,
  "params": {
    "ticket": 7011,
    "kind": "market",
    "side": "sell",
    "volume": 0.1,
    "comment": "scenario hedge",
    "count_in_report": false,
    "write_log": true
  }
}
```

Supported `params` are the same as `initial_state.orders`.

Default behavior for `place_order`:

- `count_in_report`: default `true`
- `write_log`: default `true`
- `open_time`: current tick time

### 5. `close_order`

Closes an existing order.

Example:

```json
{
  "action": "close_order",
  "params": {
    "ticket": 7011,
    "comment": "scenario close"
  }
}
```

Supported `params`:

- `order_uid`
- `ticket`
- `volume`
- `price`
- `comment`
- `tags`

Use either `order_uid` or `ticket` to identify the order.

### 6. `cancel_order`

Cancels an existing pending order.

Example:

```json
{
  "action": "cancel_order",
  "params": {
    "ticket": 7021,
    "comment": "scenario cancel"
  }
}
```

Supported `params`:

- `order_uid`
- `ticket`
- `comment`
- `tags`

Use either `order_uid` or `ticket` to identify the order.

### 7. `save_data`

Writes runtime data during the test.

Example:

```json
{
  "action": "save_data",
  "phase": "pre_tick",
  "at_tick": 20,
  "params": {
    "scope": "ACCOUNT_EA",
    "name": "open_info_EURUSD",
    "data": {
      "symbol": "EURUSD",
      "status": "running",
      "stage": 6
    }
  }
}
```

Supported `params`:

- `scope`
- `name`
- `data`
- `format`

## Script Settings Overrides

Test config `script_settings` are merged on top of EA defaults from `PX_InitScriptSettings()` and `AddParam()`.

This allows test config values such as `grid_pips`, `orders_queue_timeout_seconds`, and `risk_min_spread_multiplier` to override EA defaults while keeping the original parameter metadata.

Example:

```json
{
  "tests": {
    "extreme_case": {
      "script_settings": {
        "params": {
          "grid_pips": 8,
          "orders_queue_timeout_seconds": 3,
          "risk_min_spread_multiplier": 1.25
        }
      }
    }
  }
}
```

You can also override a parameter using the full parameter payload:

```json
{
  "script_settings": {
    "params": {
      "grid_pips": {
        "value": 8
      }
    }
  }
}
```

## Full example

```json
{
  "tests": {
    "scenario_demo": {
      "symbol": "USDCHF",
      "account": "default",
      "tick_data": "./usdchf_m1_20210315-0415.csv",
      "scenario": {
        "initial_state": {
          "account_overrides": {
            "balance": 8000,
            "equity": 8000,
            "free_margin": 8000
          },
          "orders": [
            {
              "ticket": 7001,
              "kind": "market",
              "side": "buy",
              "volume": 0.2,
              "open_price": 0.9234,
              "stop_loss": 0.922,
              "take_profit": 0.926,
              "comment": "seed long",
              "count_in_report": false
            },
            {
              "ticket": 7002,
              "kind": "pending",
              "side": "sell_stop",
              "volume": 0.1,
              "open_price": 0.921,
              "stop_loss": 0.9225,
              "take_profit": 0.918
            }
          ]
        },
        "events": [
          {
            "id": "flash_crash",
            "phase": "pre_tick",
            "at": "2021-03-16T10:05:00Z",
            "action": "mutate_tick",
            "params": {
              "low": 0.91,
              "high": 0.924,
              "close": 0.912,
              "bid": 0.91195
            }
          },
          {
            "id": "wide_spread",
            "phase": "pre_tick",
            "from": "2021-03-16T10:05:00Z",
            "to": "2021-03-16T10:10:00Z",
            "action": "override_spread",
            "once": false,
            "params": {
              "spread_point": 80
            }
          },
          {
            "id": "manual_hedge",
            "phase": "post_order_processing",
            "at_tick": 50,
            "action": "place_order",
            "params": {
              "ticket": 7011,
              "kind": "market",
              "side": "sell",
              "volume": 0.1,
              "comment": "scenario hedge",
              "count_in_report": false
            }
          },
          {
            "id": "cancel_seed_pending",
            "phase": "pre_tick",
            "at_tick": 70,
            "action": "cancel_order",
            "params": {
              "ticket": 7002,
              "comment": "scenario cancel"
            }
          }
        ]
      }
    }
  }
}
```

## Notes

- `scenario` is supported by `EATester` / `PXTester` test runs.
- For `place_order`, `close_order`, and `cancel_order`, the current implementation resolves orders by `order_uid` first, then by `ticket`.
- `mutate_tick` and `override_spread` modify the current tick in memory only.
- `initial_state.orders` are injected before the main tick loop starts.
- `count_in_report = false` is useful for seeded orders that should not be treated as strategy-created trades.
- `write_log = false` is useful when you want to keep the scenario quiet in logs.

## Files

- Example config: [samples/scenario_sample.json](/Users/digiyouth/local_files/codes/oeoehui_pixiu/samples/scenario_sample.json)
- Core implementation: [pixiu/tester/scenario.py](/Users/digiyouth/local_files/codes/oeoehui_pixiu/pixiu/tester/scenario.py)
