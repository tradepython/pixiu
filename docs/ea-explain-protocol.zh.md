# Pixiu EA Explain 协议设计

本文档定义 Pixiu 的 EA Explain 机制，用于让 EA 在实盘、回测、调试和图表分析中持续输出可查询、可追溯、可审计的策略状态与决策说明。

EA Explain 不是普通文本日志，也不是 `SaveData` 状态缓存。它是一套结构化协议，目标是让事后可以回答：

- EA 当时看到了什么市场状态。
- EA 为什么开仓、平仓、修改订单、持有或什么都不做。
- EA 当前等待什么条件。
- 风控、评分、价格过滤是否生效。
- 某张订单从开仓到平仓的完整决策链路。
- 为什么某段时间交易很少或完全没有交易。

## 1. 设计目标

### 1.1 一步到位目标

EA Explain 应使用：

```text
EA 策略
  -> EAExplainLogger 通用 EA 库
  -> Pixiu Explain API
  -> Pixiu tester / runner
  -> Pixiu chart report / replay export / 本地文件输出
```

正式方案不使用 `SaveData` 作为决策日志的长期存储，也不把大量解释信息写入 order tags。

### 1.2 核心要求

- 共用：不同 EA 使用同一套接口。
- 简单：EA 只调用少量高层接口，不直接管理输出文件或外部传输。
- 结构化：动作、原因、订单、评分、风险状态都必须有机器可查询字段。
- 可追溯：每个关键动作和关键不动作都能回放当时原因。
- 可管理：Pixiu 输出的数据可以被本地文件、图表、runner 或第三方系统查询、过滤和聚合。
- 低压力：支持批量、节流、去重和 runner 结束时统一 flush。
- 实盘回测一致：tester 和 runner 使用同一套协议。

## 2. 分层职责

### 2.1 EA 策略层

EA 策略负责产生业务解释：

- 当前市场状态。
- 当前持仓状态。
- 开仓评分和持仓评分。
- 开仓/平仓/持有/不动作原因。
- 下一步等待条件。
- 相关订单、group、cycle 信息。

EA 不负责：

- 输出文件结构。
- 外部传输。
- 重试队列。
- 输出文件管理。
- 运行上下文补充。

### 2.2 EAExplainLogger 通用库

通用库封装 EA 侧接口，并负责本地缓冲、去重、节流和 flush。

Pixiu 协议级入口仍应保持现有 EA API 风格，即由 Pixiu 注入全局函数。`EAExplainLogger` 是 EA 侧 helper，用于减少策略代码重复，不是底层协议入口。

推荐 helper 接口：

```python
explain.update_status(data)
explain.record_decision(action, reason_code, data=None, **kwargs)
explain.record_order_event(order_uid, event, reason_code, data=None, **kwargs)
explain.record_score(order_uid=None, score_type='holding', data=None, **kwargs)
explain.record_risk(action, reason_code, data=None, **kwargs)
explain.update_order_state(order_uid, data=None, **kwargs)
explain.flush()
```

EA 可以直接调用 Pixiu 底层 Explain API，也可以优先通过该库统一处理。正式协议以 `PX_*` 函数为准，helper 只负责把常用业务写法转换成标准 `status/event` 数据。

`explain.update_order_state(...)` 不是独立底层 API，它应转换为一条 `event_type = order_state_update` 的 explain event，或者在其他订单相关 event 中携带 `order_state` 字段。`explain.flush()` 也不是独立底层 API，它只负责把 helper 本地缓冲的数据通过 `PX_UpdateEAExplainStatus` 和 `PX_AppendEAExplainEvent` 提交给 Pixiu。

### 2.3 Pixiu Explain API

Pixiu 提供协议级 API：

```python
PX_UpdateEAExplainStatus(data)
PX_AppendEAExplainEvent(data)
```

API 语义：

- `PX_UpdateEAExplainStatus(data)`: 更新当前 EA 最新解释状态。Pixiu 可以按 `sid + symbol + run_id` 保留最新状态，并对重复状态做签名去重。
- `PX_AppendEAExplainEvent(data)`: 追加一条或多条解释事件。`data` 可以是单个 event object，也可以是 event object 数组。适合开仓、平仓、不动作、风控阻止、评分更新等决策流水。

两个 API 的入参格式是固定的，但采用“EA 宽松输入，Pixiu 严格归一化”的方式：

- EA 只能传 JSON object / JSON object list，不传普通字符串、数字或任意 Python 对象。
- EA 可以省略 `schema`、`type`、`time`、`time_ts`、runner、tester、symbol 等运行上下文字段，由 Pixiu 统一补充。
- EA 传入的业务字段必须稳定命名，不应在不同 EA 中随意改变同一字段含义。
- Pixiu 必须把入参归一化为协议字段，再写入 tester、chart、runner transport 或本地导出。
- Pixiu 生成的运行上下文字段优先级高于 EA 入参。EA 即使传入 `run_id`、`sid`、`symbol` 等字段，也不应覆盖 Pixiu 自己生成的值，除非对应运行模式明确允许。

`PX_UpdateEAExplainStatus(data)` 的 `data` 必须是 object。推荐字段：

```json
{
  "status": "running",
  "phase": "holding",
  "summary": "Holding 5 orders, waiting for the next signal.",
  "inventory": {},
  "risk": {},
  "market": {},
  "decision_summary": {},
  "data": {}
}
```

Pixiu 归一化后必须包含：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "status",
  "status": "running",
  "phase": "holding",
  "summary": "Holding 5 orders, waiting for the next signal.",
  "inventory": {},
  "risk": {},
  "market": {},
  "decision_summary": {},
  "data": {},
  "symbol": "EURUSD",
  "run_mode": "tester",
  "run_id": "...",
  "time": "2026-08-01 10:00:00",
  "time_ts": 1785559200
}
```

`PX_AppendEAExplainEvent(data)` 的 `data` 可以是单个 object，也可以是 object 数组。传入单个 object 时按单条 event 处理；传入数组时按批量 event 处理。每个 event object 的 `event_type` 是必填字段。`reason_code` 对决策、风控、订单维护类事件应必填；对 `heartbeat`、`warning`、`error` 可以为空，但建议填写。

推荐字段：

```json
{
  "event_type": "decision_open",
  "action": "open_buy",
  "reason_code": "score_confirmed",
  "level": "info",
  "summary": "BUY score confirmed and open conditions passed.",
  "decision_id": "EURUSD-20260801-100000-001",
  "group_id": "1778466240",
  "cycle_id": "71",
  "order_uid": "123",
  "root_uid": "123",
  "price": 1.1,
  "volume": 0.08,
  "data": {},
  "order_state": {}
}
```

Pixiu 归一化后必须包含：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "event",
  "event_type": "decision_open",
  "level": "info",
  "summary": "BUY score confirmed and open conditions passed.",
  "symbol": "EURUSD",
  "run_mode": "tester",
  "run_id": "...",
  "time": "2026-08-01 10:00:00",
  "time_ts": 1785559200
}
```

批量写入时直接把 event object 数组传给 `PX_AppendEAExplainEvent(data)`。第一版不使用 wrapper object，也不提供单独的批量 API：

```python
PX_AppendEAExplainEvent([
    {"event_type": "score_update", "summary": "Open score refreshed.", "data": {"score": 72}},
    {"event_type": "decision_no_action", "reason_code": "spread_blocked", "summary": "Spread too high."}
])
```

推荐校验规则：

- `PX_UpdateEAExplainStatus(data)`: `data` 不是 object 时拒绝。
- `PX_AppendEAExplainEvent(data)`: `data` 既不是 object 也不是数组时拒绝。
- `PX_AppendEAExplainEvent(data)`: 单个 object 缺少 `event_type` 时拒绝。
- `PX_AppendEAExplainEvent(data)`: 数组内无效 item 应记录 warning 并跳过，不影响其他有效 item。
- `data`、`inventory`、`risk`、`market`、`decision_summary`、`order_state` 必须是 object。
- `level` 默认 `info`，建议值为 `debug`、`info`、`warning`、`error`。
- 单事件归一化后不得超过 16KB，单批最多 200 条。

为了保持协议级 API 足够小，第一版不提供单独的 `PX_UpdateEAExplainOrderState` 和 `PX_FlushEAExplain`：

- 订单最新解释状态通过 `PX_AppendEAExplainEvent(s)` 中的 `order_state` 字段或 `event_type = order_state_update` 派生。
- flush 由 runner/tester 在一次 EA 执行结束时自动完成；EA helper 的 `explain.flush()` 只调用现有两个底层 API，不额外要求 Pixiu 注入 flush 函数。

Pixiu 负责自动补充运行上下文：

- `run_mode`: `tester` / `runner` / `live`
- `run_id`
- `test_id`
- `sid`
- `symbol`
- `ea_name`
- `ea_version`
- `time`
- `time_ts`

Pixiu 不解释策略逻辑，只做协议、上下文、缓冲、限流和传输。

EA 不应依赖这些 API 的返回值决定是否交易。Explain 写入失败不得影响交易主流程；Pixiu 可以返回 `True/False` 或错误摘要用于调试，但策略逻辑必须把 Explain 当作旁路观测能力。

### 2.4 Explain 内容边界

EA 可以通过 Explain 输出轻量状态和关键事件，用于后续查询、展示、回测分析和图表标注。

适合写入 Explain：

- 当前运行阶段、状态摘要和下一步等待条件。
- 低频评分、阈值、方向、风控状态等指标摘要。
- 开仓、平仓、修改订单、风控阻止、订单接管等关键事件。
- warning、error 等需要被报告或图表看到的结构化异常事件。

不适合写入 Explain：

- 高频 tick 数据。
- 大数组价格序列或完整指标序列。
- 大型调试 dump。
- 长文本普通日志。
- EA 私有缓存。
- 需要长期保存的大对象。

这些内容应继续使用价格日志、EA 日志、EA Data、tester report 或专门的数据存储。

## 3. 协议版本

所有 Explain 数据必须包含 schema 版本。

```json
{
  "schema": "pixiu-ea-explain-v1"
}
```

版本规则：

- `pixiu-ea-explain-v1` 是第一版稳定协议。
- 新增可选字段应保持兼容。
- 字段含义变化或结构性不兼容必须升级版本。

## 4. 数据模型

EA Explain 分为三类数据：

```text
status: 当前最新状态
event: 决策和动作流水
order_state: 订单级解释状态
```

### 4.1 Status

Status 保存 EA 当前最新状态。每个 `sid + symbol` 建议只有一条最新记录。

示例：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "status",
  "status": "running",
  "phase": "holding",
  "summary": "Holding 5 orders, waiting for the next signal or trailing trigger.",
  "inventory": {
    "buy_count": 3,
    "sell_count": 2,
    "buy_lot": 0.18,
    "sell_lot": 0.12,
    "floating_net": -42.5,
    "oldest_order_hours": 96.0
  },
  "risk": {
    "equity_drawdown_pct": -4.2,
    "open_disabled": false,
    "force_action_active": false
  },
  "market": {
    "range_state": "downtrend",
    "position_percent": 22.4,
    "ema_direction": "down",
    "atr_pips": 48.2
  },
  "decision_summary": {
    "last_action": "hold",
    "last_reason_code": "condition_blocked",
    "next_plan": "wait_for_next_signal",
    "next_check_after_seconds": 3600
  }
}
```

### 4.2 Event

Event 是 append-only 决策流水。任何关键动作、关键不动作、风险变化、评分变化都应记录为 event。

示例：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "event",
  "event_type": "decision_no_action",
  "action": "no_open",
  "reason_code": "condition_blocked",
  "level": "info",
  "summary": "Signal was not strong enough to open a new order.",
  "decision_id": "EURUSD-20260801-153000-001",
  "group_id": "1778466240",
  "cycle_id": "71",
  "order_uid": null,
  "data": {
    "side": "SELL",
    "score": 68,
    "threshold": 75,
    "next_plan": "wait_for_next_signal"
  }
}
```

### 4.3 Order State

Order State 保存订单级生命周期解释，方便按订单查询。

Order State 是可覆盖的最新状态，不是 EA 直接写入的独立流水。订单生命周期中的每一次关键动作仍应写入 `event`，Order State 由 Pixiu 根据 explain event 物化出来，只保存该订单当前最有用的解释摘要和最近决策引用。

示例：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "order_state",
  "order_uid": "123",
  "root_uid": "123",
  "symbol": "EURUSD",
  "open_decision_id": "EURUSD-20260801-100000-001",
  "last_decision_id": "EURUSD-20260801-153000-001",
  "last_score": 36.0,
  "last_action": "hold",
  "open_reason_code": "score_confirmed",
  "close_reason_code": null,
  "data": {
    "open": {
      "time": "2026-08-01 10:00:00",
      "side": "BUY",
      "lot": 0.08,
      "price": 1.1000,
      "score": 72
    },
    "latest": {
      "holding_hours": 5.5,
      "floating_net": 4.2,
      "target_profit": 32.0
    }
  }
}
```

EA 可以通过两种方式触发 Order State 更新。

方式一，在普通订单事件中携带 `order_state`：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "event",
  "event_type": "decision_open",
  "action": "open_buy",
  "reason_code": "score_confirmed",
  "order_uid": "123",
  "summary": "BUY score confirmed and open conditions passed.",
  "order_state": {
    "root_uid": "123",
    "open_decision_id": "EURUSD-20260801-100000-001",
    "last_decision_id": "EURUSD-20260801-100000-001",
    "last_action": "open_buy",
    "open_reason_code": "score_confirmed"
  }
}
```

方式二，写一条纯订单状态更新事件：

```json
{
  "schema": "pixiu-ea-explain-v1",
  "type": "event",
  "event_type": "order_state_update",
  "order_uid": "123",
  "summary": "Order holding score refreshed.",
  "order_state": {
    "last_score": 36.0,
    "last_action": "hold",
    "last_decision_id": "EURUSD-20260801-153000-001"
  }
}
```

Pixiu 物化 Order State 时应自动补充：

- `schema`
- `type = order_state`
- `order_uid`
- `symbol`
- `run_mode`
- `run_id`
- `time`
- `time_ts`

如果 `order_state` 中已包含这些字段，Pixiu 可以保留 EA 显式传入的业务字段，但不得允许 EA 覆盖 Pixiu 生成的运行上下文字段，例如 `run_id`、`sid`、`symbol`。

## 5. 事件类型

`event_type` 使用统一枚举。

基础事件：

```text
status_update
decision_open
decision_close
decision_modify
decision_hold
decision_no_action
score_update
order_state_update
```

风控事件：

```text
risk_check
risk_block
risk_force_action
risk_recovered
```

订单维护事件：

```text
partial_close_action
order_sync
order_adoption
```

系统事件：

```text
heartbeat
warning
error
```

## 6. 动作与原因码

### 6.1 action

`action` 表示 EA 准备做或已经做的动作。

建议枚举：

```text
open_buy
open_sell
close_order
partial_close
modify_sl
modify_tp
enter_trailing
hold
no_open
no_action
maintain_order
force_close
force_hedge
adopt_order
```

### 6.2 reason_code

`reason_code` 必须结构化，不能只写自然语言。

通用建议值：

```text
score_passed
score_low
direction_aligned
direction_adverse
condition_passed
condition_blocked
target_reachable
target_unreachable
price_confirmation_waiting
price_confirmation_passed
price_confirmation_timeout
profit_target_reached
trailing_triggered
equity_drawdown_blocked
equity_force_action_triggered
margin_risk
spread_too_wide
market_closed
order_adopted
order_incompatible
```

自然语言说明放入 `summary`，机器查询使用 `reason_code`。不同 EA 可以定义自己的 `reason_code`，建议使用稳定、可读、可过滤的 snake_case 命名，不要把长文本说明塞进 `reason_code`。

## 7. Pixiu Runner 行为

Pixiu Runner 应：

1. 在 EA 执行环境中注入 Explain API。
2. 自动补充上下文。
3. 本地缓冲 status、event 和 order_state。
4. 同一次 EA 执行结束时批量 flush。
5. 写入本地文件、实时图表或调用方自定义 transport。
6. 写入失败时记录 runner 错误并保留可观测状态，不应静默丢失。
7. 限制单次 flush 最大事件数和最大 payload 大小。
8. 对明显重复 status 和低价值 no_action 做签名去重。
9. 高优先级交易操作不得等待 Explain 写入完成。

推荐内部抽象：

```python
class ExplainTransport:
    def flush_status(self, status):
        ...

    def flush_events(self, events):
        ...

    def flush_order_states(self, order_states):
        ...
```

不同运行模式使用不同 transport：

- tester: 写入内存、JSON/JSONL 文件和 chart replay。
- live chart: 写入内存，并通过 SSE/websocket 推送给浏览器。
- runner: 写入本地文件或调用方提供的 transport。

推荐限制：

```text
status 最小写入间隔: 5 分钟
no_action 最小写入间隔: 60 分钟
单事件 payload 上限: 16KB
单次批量事件数上限: 200
单次 flush payload 上限: 1MB
```

## 8. Pixiu Tester 行为

Tester 必须实现同一套 Explain API。

回测输出建议：

```text
explain_status.json
explain_events.jsonl
explain_orders.json
```

Tester 不需要暴露独立 flush API。当开启 chart/report 输出时，测试结束统一生成文件。需要实时图表时，tester 可以在内部按 tick 或批量周期推送 explain 增量，但不应每次写磁盘。

Chart report 应支持把 explain events 显示到图表：

- `decision_open`: 开仓解释 marker。
- `decision_close`: 平仓解释 marker。
- `decision_no_action`: 可选时间轴事件。
- `risk_block`: 风控阻止 marker。
- `score_update`: 可选分数曲线或 tooltip。

实盘和回测必须使用相同字段，避免测试里能解释、线上不能解释。

## 9. 写入策略

### 9.1 推荐写入事件

以下情况建议写 event：

- 开仓。
- 平仓。
- 部分平仓。
- 修改 SL/TP。
- 进入 trailing。
- 风控禁止开仓。
- 风控强制处理。
- 订单迁移/adoption。
- 错误或异常。

### 9.2 节流事件

以下情况需要节流：

- 什么都不做。
- 状态没有变化。
- 持仓评分微小变化。
- 市场状态无变化。

节流方式：

- 内容签名一致则不写。
- 同一原因码连续出现只增加计数或按周期写摘要。
- 状态变化时立即写。

### 9.3 no_action 摘要

连续不动作时，不应每 tick 写 event。

建议数据：

```json
{
  "event_type": "decision_no_action",
  "action": "no_action",
  "reason_code": "condition_blocked",
  "summary": "No action for 47 checks; waiting for configured conditions.",
  "data": {
    "same_reason_since": "2026-08-01 10:00:00",
    "same_reason_count": 47,
    "next_plan": "wait_for_next_signal"
  }
}
```

## 10. Order Tags 关系

Order tags 只保存短引用，不保存完整解释。

建议 tags：

```json
{
  "diag_ref": "order_explain_123",
  "open_decision_id": "EURUSD-20260801-100000-001",
  "last_decision_id": "EURUSD-20260801-153000-001"
}
```

完整评分、市场状态、候选动作、阻止原因都写入 Explain event 或本地 explain 输出文件。

## 11. 与 Chart Protocol 的关系

EA Explain 可作为 Pixiu Chart Protocol 的事件源。

映射建议：

```text
explain event -> chart.events
decision_open / decision_close -> chart.orders tooltip 扩展
risk_block -> chart.objects 或 chart.events
score_update -> chart.series 或 event tooltip
```

图表 viewer 不需要理解策略，只展示结构化事件和 tooltip。

第一版 chart 集成应优先保证数据进入协议，不强制要求所有事件都有复杂视觉表现：

- 所有 explain event 应进入 `chart.events`。
- `decision_open` / `decision_close` 可以补充到订单 tooltip，不应重复生成虚假订单。
- `risk_block` 可以先显示为时间轴事件，后续再升级为图表对象。
- `score_update` 可以先作为 tooltip/event 数据，后续再升级为独立指标曲线。
- `order_state` 不直接画在图上，只用于订单面板、tooltip 和按订单查询。

## 12. 查询示例

### 12.1 为什么最近 7 天没有开仓

查询：

```text
event_type = decision_no_action
action = no_open
time >= now - 7 days
```

聚合：

```text
group by reason_code
count(*)
min(event_time)
max(event_time)
```

### 12.2 某张订单为什么亏损

查询：

```text
order_uid = ...
or root_uid = ...
order by event_time
```

看：

- 开仓评分。
- 开仓确认。
- 持仓评分变化。
- 是否出现过低成本退出窗口。
- 最终平仓原因。

### 12.3 为什么某类风控持续阻止交易

查询：

```text
event_type in (risk_check, risk_block)
reason_code = ...
order by event_time
```

## 13. 安全与可靠性

- payload 必须限制大小。
- Pixiu 生成的运行上下文字段不应被 EA 入参覆盖。
- 写入失败不能影响交易主流程，但必须产生可观测错误。
- 高优先级交易命令不能被 explain flush 阻塞。
- Explain flush 应有超时和批量上限。

## 14. 最小实现清单

第一版完整实现应包含：

1. Pixiu Explain API 注入：`PX_UpdateEAExplainStatus`、`PX_AppendEAExplainEvent`。
2. Pixiu 内部 Explain buffer/store：标准化、上下文补充、JSON 安全转换、payload 限制、批量、去重。
3. Tester 支持同一套 API，并从 explain event 物化 order_state，输出 `explain_status.json`、`explain_events.jsonl`、`explain_orders.json`。
4. Chart Protocol 支持把 explain event 写入 `chart.events`，并在订单 tooltip 中显示关键 explain 摘要。
5. Live chart transport 支持低成本实时增量推送，不强制每次 flush 写磁盘。
6. Runner 批量 flush 到本地输出或调用方自定义 transport，失败不阻塞交易主流程。
7. EAExplainLogger 通用库，封装高层 `record_decision`、`record_risk`、`record_score`、`update_order_state`。
8. Explain 输出文件生命周期跟随 tester report 或调用方运行目录管理。

## 15. Pixiu 内部建议落地顺序

为了降低一次性改动风险，建议按以下顺序开发：

1. 新增 Explain 核心模块，只处理 schema、标准化、上下文、缓冲和 JSON 安全转换，不依赖 tester 或 runner。
2. 在 `APIStub`、`TesterAPI_V1` 和 API 注入层加入两个 `PX_*Explain*` 函数。
3. 在 `EATesterContext` 中加入 `explain_status`、`explain_events`、`explain_order_states`。
4. 在 `EATester` 中实现 tester 版本 Explain API，并加入单元测试。
5. 在 Chart Adapter 中把 `explain_events` 映射到 `chart.events`。
6. 在 HTML viewer 中增加 Explain 事件展示和订单 tooltip 摘要。
7. 接入 live chart transport，只推送增量。
8. 接入 runner 本地输出和可插拔 transport。

## 16. 结论

EA Explain 的长期正确形态是：

```text
不用 SaveData 做正式日志仓库。
不用 order tags 保存大解释数据。
Pixiu 提供原生 Explain API。
EA 使用 EAExplainLogger 通用库。
Tester、Runner、Chart 统一读取 Explain 数据。
Tester 和 Runner 使用同一协议。
```

这样可以让 EA 的每一次开仓、平仓、持有、不动作和风控判断都能被追溯，同时保持策略代码接口简单、Pixiu 输出格式稳定、实时图表和回测报告行为一致。
