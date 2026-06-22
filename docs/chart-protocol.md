# Pixiu Chart and Replay Data Protocol Design

This document defines Pixiu's unified chart protocol for local backtest reports, server-side Web UIs, live debugging, and future chart ecosystem extensions.

The goal is to keep the Pixiu backend responsible for producing structured data, while the frontend viewer is responsible for rendering. The same data model can then support:

- Local static `report.html`
- Server-side Web UI
- WebSocket live debugging
- Backtest replay
- EA layers, order markers, scenario events, and account curves

## 1. Design References

### 1.1 TradingView-Style Capabilities

The Pixiu viewer should support these basic interactions:

- Main candlestick chart.
- Multiple panes, such as price, volume, equity, margin, and indicators.
- Crosshair, zooming, panning, and linked time axes.
- Indicator lines, horizontal lines, zones, and markers.
- Order and trading signal markers.
- Historical replay and step-by-step playback.

### 1.2 MT4/MT5-Style Capabilities

Pixiu should also cover common EA debugging objects from MT4/MT5:

- Buy/sell order arrows.
- Open price, close price, stop-loss, and take-profit lines.
- Text labels.
- Vertical lines, horizontal lines, trend lines, and rectangular zones.
- Indicator buffers output by EAs.
- Account balance, equity, margin, and free margin.
- Trading logs and error logs.

## 2. Overall Architecture

```text
Pixiu tester / runner
  -> ChartDataCollector
  -> replay package / chart delta stream
  -> Pixiu Chart Viewer
  -> browser render
```

Use one protocol across all modes:

```text
Static mode:
  viewer.loadReplay(replay.json)

Server mode:
  viewer.loadReplay(await fetch("/api/backtests/{id}/replay"))

Live mode:
  websocket.onmessage = delta => viewer.appendData(delta)
```

## 3. Protocol Version

Every replay package must include a protocol version.

```json
{
  "version": "pixiu-chart-v1",
  "mode": "replay"
}
```

Versioning rules:

- `pixiu-chart-v1` is the first stable protocol version.
- Small field additions should remain backward compatible.
- Breaking changes must upgrade the protocol to `pixiu-chart-v2`.

## 4. Top-Level Structure

```json
{
  "version": "pixiu-chart-v1",
  "mode": "replay",
  "metadata": {},
  "symbols": {},
  "panes": [],
  "frames": [],
  "indicators": [],
  "series": [],
  "orders": [],
  "positions": [],
  "account": [],
  "events": [],
  "objects": [],
  "assets": {},
  "logs": [],
  "reports": {}
}
```

Field descriptions:

- `metadata`: Backtest, EA, account, and environment metadata.
- `symbols`: Symbol contract and display properties.
- `panes`: Chart pane definitions.
- `frames`: Main candlestick or tick/bar price data.
- `indicators`: Indicator definitions, parameters, and optional precomputed results.
- `series`: Indicator lines, EA plots, account curves, and other series.
- `orders`: Order events.
- `positions`: Position intervals or open/close connection lines.
- `account`: Account equity, balance, margin, and related time series.
- `events`: Scenario, risk, and system events.
- `objects`: Drawing objects such as lines, zones, and text.
- `assets`: Viewer resources such as custom icons or images.
- `logs`: Timeline logs.
- `reports`: Backtest report summaries.

## 5. metadata

```json
{
  "metadata": {
    "test_uid": "test-001",
    "test_name": "testEURUSD_grid",
    "run_id": "20260618-001",
    "mode": "tester",
    "pixiu_version": "0.178.0",
    "script_name": "GridFire",
    "script_version": "1.2.3",
    "account": {
      "currency": "USD",
      "balance": 10000,
      "leverage": 100
    },
    "time": {
      "timezone": "UTC",
      "start": 1710000000,
      "end": 1710086400
    }
  }
}
```

Requirements:

- Time values use Unix timestamps in seconds.
- The display layer can format times in the user's timezone.
- Reproducibility information should be stored in `metadata`, such as config hash, data version, and EA version.

## 6. symbols

```json
{
  "symbols": {
    "EURUSD": {
      "asset_class": "forex",
      "base_currency": "EUR",
      "profit_currency": "USD",
      "margin_currency": "EUR",
      "digits": 5,
      "point": 0.00001,
      "pip_size": 0.0001,
      "tick_size": 0.00001,
      "contract_size": 100000,
      "volume_unit": "lot",
      "display": {
        "price_precision": 5,
        "volume_precision": 2
      }
    }
  }
}
```

Reserved for future stock, futures, and crypto extensions:

```json
{
  "ESM6": {
    "asset_class": "futures",
    "exchange": "CME",
    "currency": "USD",
    "tick_size": 0.25,
    "tick_value": 12.5,
    "contract_size": 50,
    "volume_unit": "contract",
    "expiration": "2026-06-19"
  }
}
```

## 7. panes

`panes` defines the chart layout.

```json
{
  "panes": [
    {
      "id": "price",
      "title": "EURUSD",
      "type": "price",
      "height": 0.6,
      "symbol": "EURUSD"
    },
    {
      "id": "account",
      "title": "Account",
      "type": "account",
      "height": 0.25
    },
    {
      "id": "logs",
      "title": "Events",
      "type": "timeline",
      "height": 0.15
    }
  ]
}
```

Rules:

- `id` is the primary key used by series, objects, and events to bind to a pane.
- A `type=price` pane displays candlesticks, orders, and price objects by default.
- A `type=account` pane displays account-related series by default.
- The frontend can use `height` as a proportional layout value.

## 8. frames

`frames` contains the main price data and supports both bar and tick granularity.

### 8.1 Bar frame

```json
{
  "frames": [
    {
      "id": "bar-1",
      "type": "bar",
      "symbol": "EURUSD",
      "timeframe": "m1",
      "time": 1710000000,
      "open": 1.0801,
      "high": 1.0810,
      "low": 1.0795,
      "close": 1.0806,
      "volume": 120,
      "bid": 1.08055,
      "ask": 1.08070
    }
  ]
}
```

### 8.2 Tick frame

```json
{
  "type": "tick",
  "symbol": "EURUSD",
  "time": 1710000000.123,
  "bid": 1.08055,
  "ask": 1.08070,
  "last": 1.08060,
  "volume": 1
}
```

Requirements:

- The first replay viewer version may render only bars.
- Ticks can be used for high-precision replay or EA debugging.
- For large datasets, the backend should aggregate ticks into bars first and keep ticks as optional detail data.

## 9. account

Account curves are stored separately rather than embedded in every candlestick.

```json
{
  "account": [
    {
      "time": 1710000000,
      "balance": 10000,
      "equity": 10015.5,
      "margin": 300,
      "free_margin": 9715.5,
      "profit": 15.5,
      "margin_level": 32.38,
      "currency": "USD"
    }
  ]
}
```

The viewer can automatically create default series:

- `balance`
- `equity`
- `margin`
- `free_margin`
- `profit`

## 10. series

`series` is used for indicators, EA plots, account lines, and custom curves.

```json
{
  "series": [
    {
      "id": "ma_fast",
      "pane": "price",
      "symbol": "EURUSD",
      "type": "line",
      "name": "MA Fast",
      "color": "#f59e0b",
      "line_width": 2,
      "data": [
        {"time": 1710000000, "value": 1.0803},
        {"time": 1710000060, "value": 1.0805}
      ],
      "source": {
        "type": "ea_plot",
        "name": "ma_fast"
      }
    }
  ]
}
```

Supported types:

- `line`
- `histogram`
- `area`
- `baseline`
- `scatter`
- `bar`

Suggested EA API mapping:

```python
PlotSeries("ma_fast", value, chart="price", color="#f59e0b")
```

### 10.1 indicators

`indicators` describes the indicator itself, while `series` carries the final rendered data. This supports:

- Indicators precomputed by the Pixiu tester backend.
- Indicator lines output directly by the EA.
- Lightweight indicators calculated by the viewer from `frames`.
- Future user-defined indicators through plugins.

For v1, prefer "precomputed indicators": Pixiu or the EA generates indicator data, and the viewer only renders it. The browser should not execute user code.

```json
{
  "indicators": [
    {
      "id": "rsi_14",
      "name": "RSI(14)",
      "symbol": "EURUSD",
      "pane": "rsi",
      "engine": "pixiu_builtin",
      "formula": "rsi",
      "inputs": {
        "source": "close",
        "period": 14
      },
      "outputs": [
        {
          "name": "rsi",
          "series_id": "rsi_14_value",
          "type": "line",
          "color": "#2563eb"
        }
      ],
      "levels": [
        {"value": 70, "text": "Overbought", "color": "#ef4444"},
        {"value": 30, "text": "Oversold", "color": "#22c55e"}
      ]
    }
  ],
  "series": [
    {
      "id": "rsi_14_value",
      "pane": "rsi",
      "symbol": "EURUSD",
      "type": "line",
      "name": "RSI(14)",
      "color": "#2563eb",
      "data": [
        {"time": 1710000000, "value": 48.2},
        {"time": 1710000060, "value": 51.7}
      ],
      "source": {
        "type": "indicator",
        "indicator_id": "rsi_14",
        "output": "rsi"
      }
    }
  ]
}
```

Multi-output indicators such as MACD can bind one `indicator` to multiple `series`:

```json
{
  "id": "macd_12_26_9",
  "name": "MACD(12,26,9)",
  "symbol": "EURUSD",
  "pane": "macd",
  "engine": "pixiu_builtin",
  "formula": "macd",
  "inputs": {
    "source": "close",
    "fast": 12,
    "slow": 26,
    "signal": 9
  },
  "outputs": [
    {"name": "macd", "series_id": "macd_line", "type": "line", "color": "#2563eb"},
    {"name": "signal", "series_id": "macd_signal", "type": "line", "color": "#f97316"},
    {"name": "histogram", "series_id": "macd_histogram", "type": "histogram", "color": "#64748b"}
  ]
}
```

Suggested `engine` values:

- `pixiu_builtin`: Pixiu built-in indicators such as MA, EMA, RSI, MACD, and ATR.
- `ea`: Indicator data actively output by the EA.
- `viewer_builtin`: Built-in indicators that the viewer can calculate safely locally.
- `external`: Precomputed by an external service or plugin.

Security rules:

- v1 should not carry executable scripts inside replay JSON.
- User-defined indicators should first enter the protocol as "precomputed results + metadata".
- If user indicator scripts are supported in the future, they should run in a separate plugin sandbox and only write results back into `series`.

## 11. orders

Orders are recorded as an event stream and are not repeated in every frame.

```json
{
  "orders": [
    {
      "uid": "7001",
      "ticket": "7001",
      "symbol": "EURUSD",
      "time": 1710000000,
      "event": "OPEN",
      "side": "BUY",
      "order_type": "MARKET",
      "volume": 0.1,
      "price": 1.0807,
      "stop_loss": 1.0780,
      "take_profit": 1.0840,
      "profit": 0,
      "margin": 108.07,
      "comment": "grid stage 1",
      "magic_number": 10001,
      "tags": {
        "group": "gridfire",
        "stage": 1
      }
    },
    {
      "uid": "7001",
      "ticket": "7001",
      "symbol": "EURUSD",
      "time": 1710003600,
      "event": "CLOSE",
      "side": "BUY",
      "volume": 0.1,
      "price": 1.0830,
      "profit": 23.0,
      "comment": "take profit"
    }
  ]
}
```

Supported events:

- `OPEN`
- `CLOSE`
- `PARTIAL_CLOSE`
- `MODIFY`
- `PENDING_CREATE`
- `PENDING_CANCEL`
- `PENDING_TRIGGER`
- `REJECT`
- `ERROR`

Default viewer behavior:

- `OPEN BUY`: upward arrow.
- `OPEN SELL`: downward arrow.
- `CLOSE profit >= 0`: green square.
- `CLOSE profit < 0`: red square.
- `MODIFY`: dot.
- SL/TP can be displayed as dashed lines or objects.

## 12. positions

`positions` expresses the full lifecycle of a position, making it easier to draw open/close connection lines and intervals.

```json
{
  "positions": [
    {
      "id": "pos-7001",
      "symbol": "EURUSD",
      "side": "BUY",
      "volume": 0.1,
      "open_order_uid": "7001",
      "close_order_uid": "7001",
      "open_time": 1710000000,
      "open_price": 1.0807,
      "close_time": 1710003600,
      "close_price": 1.0830,
      "profit": 23.0,
      "profit_currency": "USD",
      "account_profit": 23.0,
      "status": "CLOSED"
    }
  ]
}
```

v1 does not have to generate `positions`. The viewer can aggregate them from `orders`. If the backend can generate them, the frontend experience will be more stable.

## 13. events

`events` represents non-order events, including scenario, risk, system, data, and EA runtime-state events.

```json
{
  "events": [
    {
      "id": "scenario-1",
      "time": 1710001200,
      "type": "scenario",
      "name": "force_drop_stage",
      "level": "info",
      "symbol": "EURUSD",
      "price": 1.0790,
      "text": "Scenario forced price drop",
      "payload": {
        "action": "mutate_tick",
        "stage": 5
      }
    },
    {
      "id": "risk-1",
      "time": 1710002400,
      "type": "risk",
      "name": "margin_warning",
      "level": "warning",
      "text": "Margin level below threshold"
    }
  ]
}
```

Supported types:

- `scenario`
- `risk`
- `system`
- `data`
- `ea_state`
- `notification`
- `conversion`

Supported levels:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

## 14. objects

`objects` maps to TradingView drawings and MT4/MT5 chart objects.

### 14.1 Horizontal line

```json
{
  "id": "grid-level-5",
  "pane": "price",
  "symbol": "EURUSD",
  "type": "horizontal_line",
  "price": 1.0785,
  "time_from": 1710000000,
  "time_to": 1710007200,
  "style": {
    "color": "#94a3b8",
    "line_width": 1,
    "line_style": "dashed"
  },
  "text": "Grid level 5"
}
```

### 14.2 Vertical line

```json
{
  "id": "news-time",
  "pane": "price",
  "type": "vertical_line",
  "time": 1710003600,
  "style": {
    "color": "#f97316",
    "line_width": 1
  },
  "text": "News"
}
```

### 14.3 Rectangle / zone

```json
{
  "id": "risk-zone",
  "pane": "price",
  "symbol": "EURUSD",
  "type": "rectangle",
  "time_from": 1710000000,
  "time_to": 1710007200,
  "price_from": 1.0760,
  "price_to": 1.0790,
  "style": {
    "fill_color": "rgba(239, 68, 68, 0.15)",
    "border_color": "#ef4444"
  },
  "text": "High risk zone"
}
```

### 14.4 Text

```json
{
  "id": "note-1",
  "pane": "price",
  "symbol": "EURUSD",
  "type": "text",
  "time": 1710003600,
  "price": 1.0810,
  "text": "Stage 6 large lot",
  "style": {
    "color": "#111827",
    "background": "#fde68a"
  }
}
```

### 14.5 Marker / custom icon

`marker` is used for trading signals, EA alerts, user-defined icons, and special event markers. Simple icons can use built-in `shape` values. More complex icons should first be declared in `assets.icons`, then referenced through `icon_id`.

```json
{
  "assets": {
    "icons": {
      "grid-fire": {
        "type": "svg",
        "source": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iLi4uIj48L3N2Zz4=",
        "width": 24,
        "height": 24
      },
      "risk-warning": {
        "type": "builtin",
        "name": "warning-triangle"
      }
    }
  },
  "objects": [
    {
      "id": "stage-6-marker",
      "pane": "price",
      "symbol": "EURUSD",
      "type": "marker",
      "time": 1710003600,
      "price": 1.0810,
      "shape": "icon",
      "icon_id": "grid-fire",
      "text": "Stage 6",
      "style": {
        "color": "#ef4444",
        "size": 18,
        "anchor": "bottom"
      }
    }
  ]
}
```

Recommended built-in `shape` values:

- `circle`
- `square`
- `triangle_up`
- `triangle_down`
- `arrow_up`
- `arrow_down`
- `diamond`
- `cross`
- `flag`
- `icon`

Supported `assets.icons` sources:

- `builtin`: Viewer built-in icon name.
- `svg`: Sanitized SVG data URI.
- `png`: PNG data URI.
- `url`: Relative static resource path, suitable for server mode or replay packages.

Security rules:

- Remote network images are not loaded by default. Only replay-package relative paths or data URIs are allowed.
- SVG must be sanitized by the viewer. Scripts, external links, and event attributes are forbidden.
- Icon dimensions should have an upper bound, such as 64x64, to prevent abnormal replay file growth.
- Icons are display-only and must not carry trading logic.

Supported object types:

- `horizontal_line`
- `vertical_line`
- `trend_line`
- `rectangle`
- `text`
- `marker`
- `range`
- `polyline`

Suggested EA API mapping:

```python
PlotLine("grid-level-5", price=level)
PlotText("stage-note", price=Ask(), text="stage 5")
PlotBand("risk-zone", low=low, high=high)
PlotMarker("stage-6", price=Ask(), shape="icon", icon="grid-fire", text="stage 6")
```

## 15. logs

Logs should carry timestamps so they can be synchronized with the chart.

```json
{
  "logs": [
    {
      "time": 1710000000,
      "level": "info",
      "source": "ea",
      "message": "Spread condition passed",
      "symbol": "EURUSD",
      "order_uid": null,
      "payload": {}
    }
  ]
}
```

Recommended sources:

- `ea`
- `tester`
- `runner`
- `scenario`
- `risk`
- `system`

## 16. reports

Backtest summaries can be stored in `reports` for display in the viewer sidebar.

```json
{
  "reports": {
    "summary": {
      "init_balance": 10000,
      "balance": 10320.5,
      "total_net_profit": 320.5,
      "max_drawdown": -120.0,
      "total_trades": 42,
      "win_rate": 0.61
    }
  }
}
```

## 17. Live Delta Protocol

Live mode does not send a full replay on every update. It sends deltas instead.

```json
{
  "version": "pixiu-chart-v1",
  "mode": "delta",
  "seq": 1024,
  "time": 1710003600,
  "append": {
    "frames": [],
    "account": [],
    "indicators": [],
    "series": [],
    "orders": [],
    "events": [],
    "objects": [],
    "logs": []
  }
}
```

Rules:

- `seq` must be monotonically increasing.
- If the frontend detects a missing `seq`, it can request a full replay or backfill from a specified `seq`.
- Each delta should be as small as possible.
- High-frequency ticks should not be pushed to the UI one-by-one. Batch flushing is recommended.

Recommended batching strategy:

```text
graph_sample_interval: sample one frame every N ticks.
graph_flush_interval_ms: send one delta every N milliseconds.
max_delta_items: maximum number of items in one delta.
```

## 18. Static Replay Package

Recommended local backtest output:

```text
pixiu-chart/
  index.html
  replay.json
  assets/
    pixiu-chart-viewer.js
    pixiu-chart-viewer.css
```

Or single-file mode:

```text
report.html
```

Single-file mode can embed replay data directly in HTML, but large datasets should use an external `replay.json`.

### 18.1 Current Browser Report Implementation

The first stage provides a static HTML viewer with no frontend build step and no external CDN.

Characteristics:

- HTML embeds the `pixiu-chart-v1` replay JSON.
- Native browser SVG renders price candlesticks, EA series, order markers, and account curves.
- No dependency on Dash, Plotly.js, lightweight-charts, or network resources.
- Can be opened locally by double-clicking, or returned directly by a server.
- The viewer can later be replaced by a lightweight-charts viewer without changing the replay protocol.

Python API:

```python
replay = tester.build_chart_replay(graph_data=graph_data)
html = tester.build_chart_report_html(graph_data=graph_data, title="EURUSD Replay")
tester.save_chart_report_html("reports/eurusd.html", graph_data=graph_data)
```

Renderer API:

```python
from pixiu.tester import render_chart_replay_html, write_chart_replay_html

html = render_chart_replay_html(replay, title="EURUSD Replay")
write_chart_replay_html(replay, "reports/eurusd.html")
```

CLI:

```bash
pixiu test -c pixiu.json -n testEURUSD -s EA.py --chart-report reports
```

For a single test, it can also output a single HTML file directly:

```bash
pixiu test -c pixiu.json -n testEURUSD -s EA.py --chart-report reports/eurusd.html
```

When multiple tests output to a directory, the filename format is:

```text
{tag}-{test_name}.html
```

## 19. Mapping Existing Pixiu Chart Capabilities

Pixiu currently has:

- `AddChart(name, chart=...)`
- `Plot(series)`
- `context.charts_data`
- `order_logs`
- `account_logs`
- `PXTester.graph_data`
- `EATesterGraphServer`

Recommended mapping:

```text
AddChart:
  Write panes / series configuration.

Plot:
  Convert the legacy API into series or objects.

order_logs:
  Convert to orders.

account_logs:
  Convert to account.

scenario actions:
  Convert to events.

print_logs:
  Convert to logs.

graph_data["ticks"]:
  Migrate to frames + account.
```

### 19.1 Legacy `script_settings.charts` Compatibility Strategy

Pixiu already allows EAs to declare chart settings in `PX_InitScriptSettings()` or `AddChart()`, for example:

```python
AddChart(
    name="price",
    chart={
        "series": [
            {"name": "top_signal", "color": "#89F3DAFF"},
            {"name": "bottom_signal", "color": "#e7dc48"}
        ]
    }
)
```

The equivalent `script_settings` structure is:

```json
{
  "charts": {
    "price": {
      "series": [
        {"name": "top_signal", "color": "#89F3DAFF"},
        {"name": "bottom_signal", "color": "#e7dc48"}
      ]
    }
  },
  "params": {}
}
```

This structure should remain supported and serve as a compatibility input for the new protocol. Its role is "chart layout and series metadata declaration", not full replay data.

Recommended mapping from the legacy structure to the new protocol:

```text
script_settings.charts.{chart_name}
  -> one pane in panes[]

script_settings.charts.{chart_name}.series[]
  -> series metadata in series[]

series[].name
  -> series.id / series.name

series[].color
  -> series.color

Plot(series)
  -> append data points to the corresponding series

PXTester.graph_data["ticks"]
  -> frames + account + orders
```

For example, this legacy config:

```json
{
  "charts": {
    "price": {
      "series": [
        {"name": "top_signal", "color": "#89F3DAFF"}
      ]
    }
  }
}
```

Can be converted to:

```json
{
  "panes": [
    {
      "id": "price",
      "title": "price",
      "type": "price",
      "height": 0.7
    }
  ],
  "series": [
    {
      "id": "top_signal",
      "pane": "price",
      "type": "line",
      "name": "top_signal",
      "color": "#89F3DAFF",
      "data": [],
      "source": {
        "type": "legacy_plot",
        "chart": "price",
        "name": "top_signal"
      }
    }
  ]
}
```

### 19.2 Compatibility Adapter Recommendation

The first stage should not delete the legacy API directly. Instead, add an adapter that converts legacy data into a unified `pixiu-chart-v1` package.

Recommended component:

```text
LegacyChartAdapter
  input:
    script_settings.charts
    context.charts_data
    PXTester.graph_data["ticks"]
    order_logs
    account_logs
    print_logs

  output:
    pixiu-chart-v1 replay package
```

Conversion rules:

- `script_settings.charts` only generates `panes` and empty `series` declarations.
- `context.charts_data` fills `series.data` emitted by the EA.
- `PXTester.graph_data["ticks"]` is split into `frames`, `account`, and `orders`.
- `order_logs` should be preferred as an `orders` source if it is more complete than orders embedded in ticks.
- `account_logs` should be preferred as an `account` source if it is more complete than account data embedded in ticks.
- `print_logs` is converted to `logs` and keeps `source="ea"`.
- Scenario runtime records are converted to `events`.

Compatibility principles:

- `AddChart()` and `Plot()` remain available.
- New APIs such as `PlotSeries()`, `PlotMarker()`, and `PlotLine()` can initially reuse the adapter internally.
- The new viewer only consumes `pixiu-chart-v1` and does not understand legacy `charts_data` directly.
- The legacy Dash/Plotly chart service may be kept temporarily, but should gradually move to consuming adapter output.

### 19.3 Legacy Structure Limitations

The legacy `script_settings.charts` structure has limited expressiveness:

- No unified time field definition.
- No separation of `frames`, `account`, `orders`, and `events`.
- No `objects`, so it cannot express horizontal lines, vertical lines, text, zones, or custom markers.
- No `assets.icons`, so it cannot express custom icon resources.
- No `indicators`; indicator results can only be treated as ordinary series.
- `Plot(series)` currently does not require an explicit chart name, series id, or time. Conversion may need to fill the current tick time.

Therefore, the legacy structure can be used as a compatibility entry point, but it should not be expanded into the full chart protocol. New capabilities should enter `pixiu-chart-v1` first.

## 20. Recommended New EA Chart APIs

Keep legacy APIs:

```python
Plot(series)
AddChart(name, chart={})
```

Add recommended APIs:

```python
PlotSeries(name, value, chart="price", symbol=None, color=None, style=None)
PlotMarker(name, price=None, time=None, chart="price", symbol=None, shape="circle", text=None, color=None)
PlotLine(name, price=None, time_from=None, time_to=None, chart="price", symbol=None, color=None, style=None)
PlotText(name, text, price=None, time=None, chart="price", symbol=None, color=None)
PlotBand(name, low, high, time_from=None, time_to=None, chart="price", symbol=None, color=None)
DefineIcon(name, source, icon_type="svg", width=None, height=None)
PlotIcon(name, icon, price=None, time=None, chart="price", symbol=None, text=None, style=None)
```

The first version can implement only:

- `PlotSeries`
- `PlotMarker`
- `PlotLine`
- `PlotText`
- `DefineIcon`

## 21. Performance Principles

1. Do not collect "image frames"; collect structured data only.
2. Sample or aggregate high-frequency price data.
3. Use event streams for orders, logs, scenarios, and EA plots.
4. Use deltas for live push instead of sending the full state.
5. The frontend viewer should use incremental updates.
6. Large replay files should support segmented loading.
7. The backend must not depend on a browser or GUI environment.

## 22. Compatibility Strategy

### 22.1 With TradingView lightweight-charts

Direct mappings:

```text
frames -> candlestickSeries.setData/update
series line -> lineSeries.setData/update
indicators -> one or more line/histogram series
orders/events marker -> series markers
account -> independent pane line series
```

Some objects, such as rectangles and trend lines, require custom frontend overlays.

### 22.2 With MT4/MT5 Chart Objects

Direct mappings:

```text
OBJ_HLINE -> horizontal_line
OBJ_VLINE -> vertical_line
OBJ_TREND -> trend_line
OBJ_RECTANGLE -> rectangle
OBJ_TEXT / OBJ_LABEL -> text
order arrows -> orders marker
```

## 23. First-Version Scope

The recommended first version includes only:

1. `frames`
2. `account`
3. `orders`
4. `events`
5. `logs`
6. `line` series
7. Precomputed indicator descriptions in `indicators`
8. `horizontal_line`, `vertical_line`, `text`, and `marker` objects
9. `builtin` and safe SVG data URI support in `assets.icons`
10. Static `replay.json`
11. Browser viewer loading `replay.json`

Not included for now:

- Full drawing editor.
- Online persistence for user drawings.
- Very large tick-level data streams.
- Multi-user collaboration.
- TradingView Pine Script compatibility.

## 24. Full Replay Example

```json
{
  "version": "pixiu-chart-v1",
  "mode": "replay",
  "metadata": {
    "test_name": "testEURUSD_grid",
    "mode": "tester",
    "pixiu_version": "0.178.0",
    "account": {
      "currency": "USD",
      "balance": 10000
    },
    "time": {
      "timezone": "UTC",
      "start": 1710000000,
      "end": 1710003600
    }
  },
  "symbols": {
    "EURUSD": {
      "asset_class": "forex",
      "digits": 5,
      "point": 0.00001,
      "pip_size": 0.0001,
      "contract_size": 100000,
      "volume_unit": "lot"
    }
  },
  "panes": [
    {"id": "price", "title": "EURUSD", "type": "price", "height": 0.7, "symbol": "EURUSD"},
    {"id": "account", "title": "Account", "type": "account", "height": 0.3}
  ],
  "frames": [
    {
      "type": "bar",
      "symbol": "EURUSD",
      "timeframe": "m1",
      "time": 1710000000,
      "open": 1.0801,
      "high": 1.0810,
      "low": 1.0795,
      "close": 1.0806,
      "volume": 120
    }
  ],
  "account": [
    {
      "time": 1710000000,
      "balance": 10000,
      "equity": 10015.5,
      "margin": 300,
      "free_margin": 9715.5,
      "profit": 15.5,
      "currency": "USD"
    }
  ],
  "orders": [
    {
      "uid": "7001",
      "symbol": "EURUSD",
      "time": 1710000000,
      "event": "OPEN",
      "side": "BUY",
      "order_type": "MARKET",
      "volume": 0.1,
      "price": 1.0807,
      "stop_loss": 1.0780,
      "take_profit": 1.0840,
      "comment": "grid stage 1"
    }
  ],
  "events": [],
  "series": [],
  "objects": [],
  "logs": [],
  "reports": {
    "summary": {
      "init_balance": 10000,
      "balance": 10015.5,
      "total_net_profit": 15.5
    }
  }
}
```
