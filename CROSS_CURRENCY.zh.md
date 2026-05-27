# 交叉货币对支持设计

本文档记录 Pixiu tester 后续支持交叉货币对和动态换汇率的开发方案。

这个功能主要用于交易品种的盈亏币种或保证金币种与账户币种不一致的情况，例如：

- 使用 `USD` 账户交易 `EURGBP`
- 使用 `JPY` 账户交易 `GBPUSD`
- 使用 `JPY` 账户交易 `EURGBP`

## 目标

- 支持交叉货币对订单盈亏换算到账户币种。
- 支持 `currency_margin` 与账户币种不一致时的保证金换算。
- 支持从 symbol tick 数据中读取动态换汇率。
- 在回测开始前自动准备所需换汇 symbol。
- 回测 tick 循环中不联网下载，保证结果可复现。

## 实现状态

已在 `0.178.0` 中实现：

- 通过 `currency_conversion_settings.mode = "dynamic"` 启用动态换汇。
- 支持 `direct_then_usd` 换汇路径策略。
- 优先使用直接换汇 symbol，直接换汇不可用时再使用 USD 中转。
- 使用当前测试 tick 时间之前或等于当前时间的最近一条换汇 tick。
- 订单盈亏从 `currency_profit` 换算到账户币种。
- 保证金从 `currency_margin` 换算到账户币种。
- 面向 EA 的 `CalcProfit`、`OrderCalcProfit`、`CalcMargin`、`OrderCalcMargin`、`TickValue`、`PipValue` API。
- `PXTester` 增加按 symbol 缓存 tick 数据的能力，便于在回测 tick loop 前加载推导出的换汇 symbol。

后续计划：

- 增加更多 `download_policy` 选项，目前第一版按 `before_test` 设计。
- 增加更多缺失汇率处理策略，目前缺少路径或 tick 时会明确失败。
- 增加 `price_mode: "mid"`，用于更简单的分析型测试。
- 扩展多 symbol 订单处理能力；当前 tester 的主 tick loop 仍以主测试 symbol 为核心。

## 非目标

- 不在回测运行过程中临时下载换汇数据。
- 找不到有效换汇路径时，不使用错误或过期汇率静默继续。
- 不要求用户在所有测试里手工列出全部换汇 symbol，Pixiu 能推导的应该自动推导。

## 配置格式

可以在全局配置或单个 test 配置里加入 `currency_conversion_settings`。

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

字段说明：

- `mode`: `static` 或 `dynamic`。动态模式使用换汇 symbol 的 tick 数据。
- `auto_download`: 为 `true` 时，Pixiu 在测试开始前自动准备缺失的换汇 symbol。
- `download_policy`: 第一版只建议支持 `before_test`。
- `path_policy`: 第一版只建议支持 `direct_then_usd`。
- `missing_rate`: 第一版建议支持 `error` 和 `download_then_error`。
- `time_alignment`: 第一版建议支持 `latest_before_or_at_tick`。
- `price_mode`: 第一版建议支持 `bid_ask`，后续可以增加 `mid`。
- `fallback_enabled`: 为 `true` 时，如果动态行情不可用，可以使用配置里的静态 fallback 汇率。

## 换汇来源配置

`currency_conversions` 可以显式指定某个换汇路径使用哪个 symbol。

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

如果没有配置 `currency_conversions`，Pixiu 应该根据 `symbols`、账户币种和换汇路径策略自动推导。

## 换汇路径策略

第一版建议实现 `direct_then_usd`。

对于一次 `FROM -> TO` 的换汇：

1. 如果 `FROM == TO`，不需要换汇。
2. 优先尝试直接货币对：`FROMTO`。
3. 再尝试反向货币对：`TOFROM`。
4. 如果两边都不是 `USD`，尝试通过 USD 中转：
   - `FROM -> USD`
   - `USD -> TO`
5. 如果仍然找不到完整路径，在测试开始前明确报错。

示例：

```text
GBP -> JPY:
  优先使用 GBPJPY。
  如果 GBPJPY 不可用，使用 GBPUSD + USDJPY。

GBP -> USD:
  优先使用 GBPUSD。
  如果 GBPUSD 不可用，使用 USDGBP。

CHF -> AUD:
  优先使用 CHFAUD。
  如果 CHFAUD 不可用，使用 CHFUSD + USDAUD。
```

## 自动下载行为

自动下载应该发生在回测准备阶段，而不是 tick 循环中。

```text
1. 读取测试 symbol 和账户币种。
2. 读取 symbol 元数据：
   - currency_base
   - currency_profit
   - currency_margin
3. 推导需要的换汇：
   - currency_profit -> account currency
   - currency_margin -> account currency
4. 使用 direct_then_usd 解析换汇路径。
5. 检查每个换汇 symbol 是否已有本地 tick 数据。
6. 如果 auto_download 为 true，下载缺失的换汇 symbol。
7. 校验所有换汇路径都有可用数据。
8. 开始正式回测。
```

回测执行阶段不应该再触发网络下载，这样可以保证测试结果稳定可复现。

## 盈亏计算

订单盈亏应该先按品种的 `currency_profit` 计算，再换算到账户币种。

```text
raw_profit = (close_price - open_price) * volume * trade_contract_size * direction
account_profit = convert_currency(raw_profit, currency_profit, account_currency)
```

其中：

```text
direction = 1 表示 buy 订单
direction = -1 表示 sell 订单
```

示例：

```text
账户币种: USD
交易品种: EURGBP
currency_profit: GBP
订单: BUY 1 lot
开仓价: 0.8500
平仓价: 0.8510
合约大小: 100000

raw_profit = (0.8510 - 0.8500) * 100000 = 100 GBP
GBPUSD = 1.2500
account_profit = 125 USD
```

## 保证金计算

保证金应该先按 `currency_margin` 计算，再换算到账户币种。

第一版建议在保留现有 symbol 行为的基础上泛化：

```text
margin_in_margin_currency = calculate_symbol_margin(symbol, open_price, volume)
account_margin = convert_currency(margin_in_margin_currency, currency_margin, account_currency)
```

已有的 `USDCHF` 等测试必须保持不变。

## Bid/Ask 使用规则

第一版建议使用偏保守的 bid/ask 换算。

```text
正向货币对 FROMTO:
  FROM -> TO 使用 bid。
  TO -> FROM 使用 1 / ask。

反向货币对 TOFROM:
  FROM -> TO 使用 1 / ask。
  TO -> FROM 使用 bid。
```

保证金换算也建议使用偏保守的一侧。后续如果需要更简单的分析测试，可以增加 `price_mode: "mid"`。

## 时间对齐

动态换汇率应该使用当前测试 tick 时间之前或等于当前时间的最近一条换汇 tick。

```json
{
  "time_alignment": "latest_before_or_at_tick"
}
```

如果当前时间找不到可用换汇 tick：

- 如果 `fallback_enabled` 为 `true` 且配置了 fallback 汇率，则使用 fallback。
- 否则按 `missing_rate` 策略处理。

## 缺失汇率策略

第一版建议支持：

- `error`: 找不到换汇率时直接报错。
- `download_then_error`: 准备阶段先尝试下载，下载后仍不可用则报错。

默认建议：

```text
auto_download = true  时，默认 missing_rate = download_then_error
auto_download = false 时，默认 missing_rate = error
```

## 实现建议

建议增加内部 helper：

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

建议接入点：

- 在 `EATester.execute_` 进入 tick loop 前准备换汇 symbol 数据。
- 订单盈亏计算改成使用 `convert_currency`。
- 开仓保证金检查改成使用 `convert_currency`。
- scenario 注入的已有订单在重算 equity、margin 时也使用同一套换汇逻辑。

## 测试计划

建议补充这些回归测试：

- `EURGBP` + `USD` 账户，使用直接 `GBPUSD` 换算盈亏。
- `EURGBP` + `JPY` 账户，优先使用直接 `GBPJPY`。
- `EURGBP` + `JPY` 账户，在没有 `GBPJPY` 时使用 `GBPUSD + USDJPY`。
- 只有反向 symbol 时可以正确倒数换算。
- 缺少换汇数据时给出清晰错误。
- 现有 `USDCHF` 行为保持不变。
