# Pixiu 图表与回放数据协议设计

本文档定义 Pixiu 的统一图表协议，用于本地回测报告、服务端 Web UI、实时调试和未来图表生态扩展。

协议目标是让 Pixiu 后端只负责生成结构化数据，前端 viewer 负责渲染。这样同一套数据可以同时支持：

- 本地静态 `report.html`
- 服务端 Web UI
- WebSocket 实时调试
- 回测 replay
- EA 图层、订单标记、scenario 事件和账户曲线

## 1. 设计参考

### 1.1 TradingView 风格能力

Pixiu viewer 应支持以下基础体验：

- K 线主图。
- 多 pane，例如价格、成交量、权益、保证金、指标。
- 十字光标、缩放、拖动、时间轴联动。
- 指标线、水平线、区域、marker。
- 订单和交易信号标记。
- 历史 replay 和逐步播放。

### 1.2 MT4/MT5 风格能力

Pixiu 也应覆盖 MT4/MT5 中 EA 调试常用对象：

- 买卖订单箭头。
- 开仓价、平仓价、止损、止盈线。
- 文本标签。
- 垂直线、水平线、趋势线、矩形区域。
- EA 输出的指标 buffer。
- 账户 balance、equity、margin、free_margin。
- 交易日志和错误日志。

## 2. 总体架构

```text
Pixiu tester / runner
  -> ChartDataCollector
  -> replay package / chart delta stream
  -> Pixiu Chart Viewer
  -> browser render
```

统一使用同一套协议：

```text
静态模式:
  viewer.loadReplay(replay.json)

服务端模式:
  viewer.loadReplay(await fetch("/api/backtests/{id}/replay"))

实时模式:
  websocket.onmessage = delta => viewer.appendData(delta)
```

## 3. 协议版本

每个 replay package 必须包含协议版本。

```json
{
  "version": "pixiu-chart-v1",
  "mode": "replay"
}
```

版本规则：

- `pixiu-chart-v1` 是第一版稳定协议。
- 小字段扩展应保持向后兼容。
- 不兼容修改必须升级到 `pixiu-chart-v2`。

## 4. 顶层结构

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

字段说明：

- `metadata`: 回测、EA、账户和环境元数据。
- `symbols`: symbol 合约和显示属性。
- `panes`: 图表分区定义。
- `frames`: K 线或 tick/bar 主数据。
- `indicators`: 指标定义、参数和可选的预计算结果。
- `series`: 指标线、EA plot、账户曲线等序列。
- `orders`: 订单事件。
- `positions`: 持仓区间或开平仓连线。
- `account`: 账户权益、余额、保证金等时间序列。
- `events`: scenario、风险、系统事件。
- `objects`: 图形对象，例如线段、区域、文本。
- `assets`: 自定义图标、图片等 viewer 资源。
- `logs`: 时间轴日志。
- `reports`: 回测报告摘要。

## 5. metadata

```json
{
  "metadata": {
    "test_uid": "test-001",
    "test_name": "testEURUSD_grid",
    "run_id": "20260618-001",
    "mode": "tester",
    "pixiu_version": "0.178.0",
    "script_name": "ExampleStrategy",
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

要求：

- 时间统一使用 Unix timestamp 秒。
- 展示层可以按用户时区格式化。
- 回测复现相关信息应放入 `metadata`，例如配置 hash、数据版本、EA 版本。

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

为未来股票、期货、加密扩展预留：

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

`panes` 定义图表布局。

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

规则：

- `id` 是 series/object/event 绑定 pane 的主键。
- `type=price` 的 pane 默认显示 K 线、订单、价格对象。
- `type=account` 默认显示账户相关序列。
- 前端可以按 `height` 比例布局。

## 8. frames

`frames` 是主价格数据，支持 bar 和 tick 两种粒度。

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

要求：

- 回放 viewer 第一版可以只渲染 bar。
- tick 可用于高精度 replay 或 EA 调试。
- 大数据量时建议后端先聚合成 bar，再将 tick 作为可选详情。

## 9. account

账户曲线单独存储，不塞进每根 K 线。

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

viewer 可自动生成默认 series：

- `balance`
- `equity`
- `margin`
- `free_margin`
- `profit`

## 10. series

`series` 用于指标、EA plot、账户线和自定义曲线。

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

支持类型：

- `line`
- `histogram`
- `area`
- `baseline`
- `scatter`
- `bar`

建议 EA API 对应：

```python
PlotSeries("ma_fast", value, chart="price", color="#f59e0b")
```

### 10.1 indicators

`indicators` 用于描述指标本身，`series` 用于承载指标最终画出来的数据。这样可以同时支持：

- Pixiu tester 后端预计算指标。
- EA 自己输出指标线。
- viewer 根据 `frames` 在前端计算轻量指标。
- 将来通过插件扩展用户自定义指标。

第一版建议优先支持“预计算指标”：Pixiu 或 EA 生成指标数据，viewer 只负责渲染，不在浏览器里执行用户代码。

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

多输出指标，例如 MACD，可以让一个 `indicator` 绑定多个 `series`：

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

`engine` 建议值：

- `pixiu_builtin`: Pixiu 内置指标，例如 MA、EMA、RSI、MACD、ATR。
- `ea`: EA 主动输出的指标数据。
- `viewer_builtin`: viewer 可安全本地计算的内置指标。
- `external`: 由外部服务或插件预计算后写入。

安全规则：

- v1 不建议在 replay JSON 中携带可执行脚本。
- 用户自定义指标第一阶段应以“预计算结果 + 元数据”的方式进入协议。
- 如果将来支持用户指标脚本，应放到单独插件沙箱中运行，并只把结果写回 `series`。

## 11. orders

订单以事件流记录，不重复塞进每一帧。

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
        "group": "sample_group",
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

支持事件：

- `OPEN`
- `CLOSE`
- `PARTIAL_CLOSE`
- `MODIFY`
- `PENDING_CREATE`
- `PENDING_CANCEL`
- `PENDING_TRIGGER`
- `REJECT`
- `ERROR`

viewer 默认行为：

- `OPEN BUY`: 向上箭头。
- `OPEN SELL`: 向下箭头。
- `CLOSE profit >= 0`: 绿色方块。
- `CLOSE profit < 0`: 红色方块。
- `MODIFY`: 圆点。
- SL/TP 可显示为虚线或对象。

## 12. positions

`positions` 用于表达一个完整持仓生命周期，方便画开平仓连线和区间。

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

第一版可以不强制生成 `positions`，由 viewer 根据 `orders` 聚合。但如果后端能生成，前端体验更稳定。

## 13. events

`events` 表示非订单事件，包括 scenario、风险、系统、数据和 EA 运行态。

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

支持类型：

- `scenario`
- `risk`
- `system`
- `data`
- `ea_state`
- `notification`
- `conversion`

支持等级：

- `debug`
- `info`
- `warning`
- `error`
- `critical`

## 14. objects

`objects` 对应 TradingView drawing 和 MT4/MT5 chart objects。

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

`marker` 用于交易信号、EA 提醒、用户自定义图标和特殊事件标记。简单图标可以使用内置 `shape`，复杂图标应先在 `assets.icons` 中声明，再通过 `icon_id` 引用。

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

内置 `shape` 建议支持：

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

`assets.icons` 支持来源：

- `builtin`: viewer 内置图标名。
- `svg`: 经过清洗的 SVG data URI。
- `png`: PNG data URI。
- `url`: 静态资源相对路径，适合服务端或 replay package。

安全规则：

- 默认不加载远程网络图片，只允许 replay package 内相对路径或 data URI。
- SVG 必须由 viewer 清洗，禁止脚本、外链、事件属性。
- 图标尺寸应有上限，例如 64x64，避免 replay 文件异常膨胀。
- 图标只负责显示，不承载交易逻辑。

支持对象类型：

- `horizontal_line`
- `vertical_line`
- `trend_line`
- `rectangle`
- `text`
- `marker`
- `range`
- `polyline`

建议 EA API 对应：

```python
PlotLine("grid-level-5", price=level)
PlotText("stage-note", price=Ask(), text="stage 5")
PlotBand("risk-zone", low=low, high=high)
PlotMarker("stage-6", price=Ask(), shape="icon", icon="grid-fire", text="stage 6")
```

## 15. logs

日志应该带时间，方便与图表同步。

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

建议来源：

- `ea`
- `tester`
- `runner`
- `scenario`
- `risk`
- `system`

## 16. reports

回测摘要可以放在 `reports`，方便 viewer 展示侧栏。

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

## 17. 实时 delta 协议

实时模式不发送完整 replay，而是发送增量。

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

规则：

- `seq` 单调递增。
- 前端发现缺失 seq，可以请求全量 replay 或从指定 seq 补数据。
- 每个 delta 应尽量小。
- 高频 tick 不应逐 tick 推送 UI，建议批量 flush。

建议批量策略：

```text
graph_sample_interval: 每 N 个 tick 采样一帧。
graph_flush_interval_ms: 每 N 毫秒发送一次增量。
max_delta_items: 单次增量最大项目数。
```

## 18. 静态 replay package

本地回测输出建议：

```text
pixiu-chart/
  index.html
  replay.json
  assets/
    pixiu-chart-viewer.js
    pixiu-chart-viewer.css
```

或者单文件模式：

```text
report.html
```

单文件模式可把 replay 数据内嵌到 HTML，但大数据量时应使用外部 `replay.json`。

### 18.1 当前浏览器报告实现

第一阶段 Pixiu 提供一个零前端构建、零外部 CDN 的静态 HTML viewer。

特点：

- HTML 内嵌 `pixiu-chart-v1` replay JSON。
- 使用浏览器原生 SVG 渲染价格 K 线、EA series、订单标记和账户曲线。
- 不依赖 Dash、Plotly.js、lightweight-charts 或网络资源。
- 可本地双击打开，也可以由服务端直接返回 HTML。
- 后续可以在不改 replay 协议的情况下替换为 lightweight-charts viewer。

Python API：

```python
replay = tester.build_chart_replay(graph_data=graph_data)
html = tester.build_chart_report_html(graph_data=graph_data, title="EURUSD Replay")
tester.save_chart_report_html("reports/eurusd.html", graph_data=graph_data)
```

直接使用 renderer：

```python
from pixiu.tester import render_chart_replay_html, write_chart_replay_html

html = render_chart_replay_html(replay, title="EURUSD Replay")
write_chart_replay_html(replay, "reports/eurusd.html")
```

CLI：

```bash
pixiu test -c pixiu.json -n testEURUSD -s EA.py --chart-report reports
```

如果只有一个 test，也可以直接输出单个 HTML 文件：

```bash
pixiu test -c pixiu.json -n testEURUSD -s EA.py --chart-report reports/eurusd.html
```

多 test 输出目录时，文件名格式为：

```text
{tag}-{test_name}.html
```

## 19. 与现有 Pixiu 图表能力的映射

当前 Pixiu 已有：

- `AddChart(name, chart=...)`
- `Plot(series)`
- `context.charts_data`
- `order_logs`
- `account_logs`
- `PXTester.graph_data`
- `EATesterGraphServer`

建议映射：

```text
AddChart:
  写入 panes / series 配置。

Plot:
  兼容旧 API，转换为 series 或 object。

order_logs:
  转换为 orders。

account_logs:
  转换为 account。

scenario actions:
  转换为 events。

print_logs:
  转换为 logs。

graph_data["ticks"]:
  迁移为 frames + account。
```

### 19.1 旧 `script_settings.charts` 兼容策略

当前 Pixiu 已经允许 EA 在 `PX_InitScriptSettings()` 或 `AddChart()` 中声明 chart 设置，例如：

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

等价的 `script_settings` 结构为：

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

这个结构应继续保留，并作为新协议的兼容输入。它的定位是“图表布局和 series 元数据声明”，不是完整 replay 数据。

旧结构到新协议的建议映射：

```text
script_settings.charts.{chart_name}
  -> panes[] 中的一个 pane

script_settings.charts.{chart_name}.series[]
  -> series[] 中的 series metadata

series[].name
  -> series.id / series.name

series[].color
  -> series.color

Plot(series)
  -> 给对应 series 追加 data 点

PXTester.graph_data["ticks"]
  -> frames + account + orders
```

例如旧配置：

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

可以转换为：

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

### 19.2 兼容 adapter 建议

第一阶段不建议直接删除旧 API，而是新增一个 adapter，把旧数据统一转换为 `pixiu-chart-v1`。

建议组件：

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

转换规则：

- `script_settings.charts` 只负责生成 `panes` 和空的 `series` 声明。
- `context.charts_data` 负责填充 EA 主动输出的 `series.data`。
- `PXTester.graph_data["ticks"]` 拆成 `frames`、`account` 和 `orders`。
- `order_logs` 如果比 tick 内订单更完整，应优先作为 `orders` 来源。
- `account_logs` 如果比 tick 内账户数据更完整，应优先作为 `account` 来源。
- `print_logs` 转换为 `logs`，并保留 `source="ea"`。
- scenario 运行记录转换为 `events`。

兼容原则：

- `AddChart()` 和 `Plot()` 保持可用。
- 新 API `PlotSeries()`、`PlotMarker()`、`PlotLine()` 等可以先内部复用 adapter。
- 新 viewer 只消费 `pixiu-chart-v1`，不直接理解旧 `charts_data`。
- 旧 Dash/Plotly 图表服务可以保留一段时间，但应逐步改为消费 adapter 输出。

### 19.3 需要注意的旧结构限制

旧 `script_settings.charts` 能表达的内容较少：

- 没有统一的时间字段定义。
- 没有 `frames`、`account`、`orders`、`events` 的拆分。
- 没有 `objects`，因此不能表达水平线、垂直线、文本、区域和自定义 marker。
- 没有 `assets.icons`，因此不能表达用户自定义图标资源。
- 没有 `indicators`，只能把指标结果当成普通 series。
- `Plot(series)` 目前没有强制要求绑定 chart name、series id 和时间，转换时可能需要按当前 tick 时间补齐。

因此旧结构可以作为兼容入口，但不应继续扩展成完整图表协议。新的能力应优先进入 `pixiu-chart-v1`。

## 20. 建议新增 EA 图表 API

保留旧 API：

```python
Plot(series)
AddChart(name, chart={})
```

新增推荐 API：

```python
PlotSeries(name, value, chart="price", symbol=None, color=None, style=None)
PlotMarker(name, price=None, time=None, chart="price", symbol=None, shape="circle", text=None, color=None)
PlotLine(name, price=None, time_from=None, time_to=None, chart="price", symbol=None, color=None, style=None)
PlotText(name, text, price=None, time=None, chart="price", symbol=None, color=None)
PlotBand(name, low, high, time_from=None, time_to=None, chart="price", symbol=None, color=None)
DefineIcon(name, source, icon_type="svg", width=None, height=None)
PlotIcon(name, icon, price=None, time=None, chart="price", symbol=None, text=None, style=None)
```

第一版可以只实现：

- `PlotSeries`
- `PlotMarker`
- `PlotLine`
- `PlotText`
- `DefineIcon`

## 21. 性能原则

1. 不收集“图片帧”，只收集结构化数据。
2. 高频价格数据采样或聚合。
3. 订单、日志、scenario、EA plot 用事件流。
4. 实时推送使用 delta，不全量发送。
5. 前端 viewer 使用增量更新。
6. 大数据 replay 支持分段加载。
7. 后端不依赖浏览器或 GUI 环境。

## 22. 兼容策略

### 22.1 与 TradingView lightweight-charts

可直接映射：

```text
frames -> candlestickSeries.setData/update
series line -> lineSeries.setData/update
indicators -> one or more line/histogram series
orders/events marker -> series markers
account -> 独立 pane line series
```

部分对象如 rectangle、trend line 需要前端自定义 overlay。

### 22.2 与 MT4/MT5 图形对象

可直接映射：

```text
OBJ_HLINE -> horizontal_line
OBJ_VLINE -> vertical_line
OBJ_TREND -> trend_line
OBJ_RECTANGLE -> rectangle
OBJ_TEXT / OBJ_LABEL -> text
订单箭头 -> orders marker
```

## 23. 第一版落地范围

建议第一版只做：

1. `frames`
2. `account`
3. `orders`
4. `events`
5. `logs`
6. `series` 的 `line`
7. `indicators` 的预计算指标描述
8. `objects` 的 `horizontal_line`、`vertical_line`、`text`、`marker`
9. `assets.icons` 的 `builtin` 和安全 SVG data URI
10. 静态 `replay.json`
11. 浏览器 viewer 加载 `replay.json`

暂不做：

- 完整 drawing editor。
- 在线保存用户画线。
- tick 级超大数据流。
- 多用户协同。
- TradingView Pine Script 兼容。

## 24. 示例完整 replay

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
