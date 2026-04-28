# Scenario JSON 配置说明

`scenario` 是每个测试项下的一个可选配置块。

测试配置文件使用 `pyjson5` 解析，所以既支持标准 JSON，也支持 JSON5 风格的注释和尾随逗号。

## 配置位置

将 `scenario` 放在 `tests.<test_name>` 下面：

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

## 整体结构

```json
{
  "scenario": {
    "initial_state": {
      "account_overrides": {},
      "orders": []
    },
    "events": []
  }
}
```

## `initial_state`

`initial_state` 会在 tick 数据加载完成之后、主回测循环开始之前应用。

### `initial_state.account_overrides`

用于覆盖当前测试账户中的字段。

示例：

```json
{
  "account_overrides": {
    "balance": 8000,
    "equity": 8000,
    "free_margin": 8000
  }
}
```

支持的字段取决于 tester 当前使用的账户结构，常见字段包括：

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

用于在测试开始前注入已存在订单。

示例：

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

订单字段说明：

- `ticket`：可选，自定义 ticket 编号；不传则由 tester 自动生成
- `kind`：`market` 或 `pending`
- `side`：支持以下值
  - `buy`
  - `sell`
  - `buy_limit`
  - `sell_limit`
  - `buy_stop`
  - `sell_stop`
- `cmd`：可选；如果传了，则优先使用 `cmd`，覆盖 `kind + side`
- `symbol`：可选；默认使用当前测试的 symbol
- `volume`：必填
- `open_price`：市场单可选，建议所有注入订单都显式填写
- `stop_loss`
- `take_profit`
- `comment`
- `magic_number`
- `open_time`：可选；支持 timestamp 或 ISO datetime 字符串
- `commission`
- `tags`
- `from_uid`
- `to_uid`
- `status`：可选；市场单默认是 `opened`，需要时也可以显式传 `pending`
- `count_in_report`：可选；`initial_state` 的订单默认是 `false`
- `write_log`：可选；默认是 `false`

## `events`

`events` 表示回测运行过程中的事件动作。

示例：

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

通用事件字段：

- `id`：可选；不传时自动生成 `scenario_event_<index>`
- `phase`：可选；默认是 `pre_tick`
- `action`：必填
- `params`：可选；动作参数
- `once`：可选
- `at`：在指定时间点执行
- `from`：时间区间开始
- `to`：时间区间结束
- `at_tick`：在指定 tick 序号执行
- `from_tick`：tick 区间开始
- `to_tick`：tick 区间结束

时间字段支持 ISO datetime 字符串，例如：

```json
"2021-03-16T10:05:00Z"
```

当前行为：

- 时间字符串按 UTC 的无时区时间处理
- 如果输入里带了 `Z` 或 `+08:00` 这类时区后缀，当前实现会忽略这个偏移量本身
- 这样可以保证 `scenario.at/from/to` 和 tester 内部 tick 时间的处理方式一致

### 事件匹配规则

一个事件可以通过以下任意一种方式触发：

- 精确时间：`at`
- 时间区间：`from` + `to`
- 精确 tick：`at_tick`
- tick 区间：`from_tick` + `to_tick`

### `phase`

当前支持的 phase：

- `pre_tick`
- `post_order_processing`
- `post_tick`

含义：

- `pre_tick`：当前 tick 的 `Ask/Bid/Close` 等价格被读取前执行
- `post_order_processing`：内部订单处理之后执行
- `post_tick`：当前 tick 的策略脚本执行之后执行

### `once`

默认行为：

- `mutate_tick`：默认 `once = false`
- `override_spread`：默认 `once = false`
- 其它动作：默认 `once = true`

如果 `once = false`，只要当前时间或 tick 仍然命中它的触发范围，事件就会持续重复生效。

## 当前支持的 action

### 1. `mutate_tick`

用于修改当前 tick 的市场数据。

示例：

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

`params` 支持的字段：

- 短字段名：
  - `o`
  - `h`
  - `l`
  - `c`
  - `a`
  - `b`
  - `v`
- 可读字段名：
  - `open`
  - `high`
  - `low`
  - `close`
  - `ask`
  - `bid`
  - `volume`
- `delta`：在当前值基础上做增量偏移

带 `delta` 的示例：

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

### 2. `override_spread`

用于临时覆盖当前 tick 的 `spread_point`。

示例：

```json
{
  "action": "override_spread",
  "params": {
    "spread_point": 80
  }
}
```

`params` 支持：

- `spread_point`
- `value`：`spread_point` 的别名

当前行为：

- 更新 tester context 中的 `spread_point`
- 当前 tick 的 `ask` 会按 `bid + spread` 重新计算

### 3. `place_order`

用于在测试过程中动态下单。

示例：

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

`params` 支持的字段与 `initial_state.orders` 相同。

`place_order` 的默认行为：

- `count_in_report`：默认 `true`
- `write_log`：默认 `true`
- `open_time`：默认使用当前 tick 时间

### 4. `close_order`

用于关闭已有订单。

示例：

```json
{
  "action": "close_order",
  "params": {
    "ticket": 7011,
    "comment": "scenario close"
  }
}
```

`params` 支持：

- `order_uid`
- `ticket`
- `volume`
- `price`
- `comment`
- `tags`

使用 `order_uid` 或 `ticket` 任意一种都可以定位订单。

### 5. `cancel_order`

用于取消已有挂单。

示例：

```json
{
  "action": "cancel_order",
  "params": {
    "ticket": 7021,
    "comment": "scenario cancel"
  }
}
```

`params` 支持：

- `order_uid`
- `ticket`
- `comment`
- `tags`

使用 `order_uid` 或 `ticket` 任意一种都可以定位订单。

## 完整示例

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

## 注意事项

- `scenario` 目前用于 `EATester` / `PXTester` 的测试运行。
- `place_order`、`close_order`、`cancel_order` 当前会优先按 `order_uid` 查找订单，找不到时再按 `ticket` 查找。
- `mutate_tick` 和 `override_spread` 只会修改内存中的当前 tick，不会改原始 csv 文件。
- `initial_state.orders` 会在主 tick 循环开始前完成注入。
- 对于起始就存在的持仓，通常建议设置 `count_in_report = false`，避免被统计成策略主动开仓。
- 如果不希望 scenario 污染日志，可以使用 `write_log = false`。

## 相关文件

- 示例配置：[samples/scenario_sample.json](/Users/digiyouth/local_files/codes/oeoehui_pixiu/samples/scenario_sample.json)
- 核心实现：[pixiu/tester/scenario.py](/Users/digiyouth/local_files/codes/oeoehui_pixiu/pixiu/tester/scenario.py)
- 英文版文档：[SCENARIO.md](/Users/digiyouth/local_files/codes/oeoehui_pixiu/SCENARIO.md)
