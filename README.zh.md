<p align="center">
<img width="128" height="128" src="https://raw.githubusercontent.com/tradepython/pixiu/main/pixiu-128x128-8bit.png">
</p>


PiXiu - 貔貅
=======
貔貅是一款交易回测工具，它是仿照 MT4/MT5 的测试器开发的。
它有一套标准的API定义，使用这些API编写的回测代码，可以无需更改的在 www.TradePython.com 上运行。

安装
=======
pip install pixiu


使用方法
=======
参数:
    -c/--testconfig         测试配置文件
    -n/--testname           测试名称（测试配置文件中）
    -s/--scriptpath         脚本文件
    -o/--logpath            日志文件
    -p/--printlogtype       输出Log类型
    -m/--multiprocessing    多进程模式
    -r/--compare            比较多个标签
    -t/--tag                标签
    -l/--datafile           数据文件名

    基本用法：

    pixiu -c pixiu_sample.json -n testUSDCHF_TP -s pixiu_sample.py
    pixiu -c pixiu_sample.json -n testUSDCHF_TP -s pixiu_sample.py
    pixiu -c pixiu_sample.json -n testUSDCHF -s pixiu_sample2.py -o log.txt

    比较多个策略：

    pixiu -c pixiu.json -n testAUDUSD_A testGBPUSD_A testNZDUSD_A testEURUSD_A testUSDCHF_A testUSDJPY_A testUSDCAD_A -s ../strategies/strategy_v1.py -p report -t strategy-v1 -l strategy_compare.json
    pixiu -c pixiu.json -n testAUDUSD_A testGBPUSD_A testNZDUSD_A testEURUSD_A testUSDCHF_A testUSDJPY_A testUSDCAD_A -s ../strategies/strategy_v2.py -p report -t strategy-v2 -l strategy_compare.json
    pixiu -c pixiu.json -n testAUDUSD_A testGBPUSD_A testNZDUSD_A testEURUSD_A testUSDCHF_A testUSDJPY_A testUSDCAD_A -s ../strategies/strategy_v3.py -p report -t strategy-v3 -l strategy_compare.json

    pixiu -c pixiu.json -n testAUDUSD_A testGBPUSD_A testNZDUSD_A testEURUSD_A testUSDCHF_A testUSDJPY_A testUSDCAD_A -t strategy-v1 -r strategy-v2 strategy-v3 -l strategy_compare.json

    Output:
    +----+--------------------------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+--------------------+
    |    |                                      | testAUDUSD_A | testGBPUSD_A | testNZDUSD_A | testEURUSD_A | testUSDCHF_A | testUSDJPY_A | testUSDCAD_A | Total/Avg          |
    +----+--------------------------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+--------------------+
    | 1  | Init Balance(2.10.0)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
    | 1  | Init Balance(2.10.1)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
    | 1  | Init Balance(2.10.2)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
    ...
    | 7  | Balance(2.10.0)                      | 4988.31             | 5064.61             | 5041.77             | 5071.6              | 4994.96             | 4996.97             | 4996.94             | 35155.16 / 5022.17 |
    | 7  | Balance(2.10.1)                      | 5003.42 ↑           | 5061.26 ↓           | 5000.58 ↓           | 4965.65 ↓           | 5009.12 ↑           | 5033.44 ↑           | 4931.17 ↓           | 35004.64 / 5000.66 |
    | 7  | Balance(2.10.2)                      | 4981.59 ↓           | 5076.74 ↑           | 5000.58 ↓           | 4985.02 ↓           | 5023.02 ↑           | 5029.35 ↑           | 4965.34 ↓           | 35061.64 / 5008.81 |
    | 8  | Total Net Profit(2.10.0)             | -11.69              | 64.61               | 41.77               | 71.6                | -5.05               | -3.02               | -3.05               | 155.17 / 22.17     |
    | 8  | Total Net Profit(2.10.1)             | 3.42 ↑              | 61.26 ↓             | 0.58 ↓              | -34.35 ↓            | 9.14 ↑              | 33.44 ↑             | -68.84 ↓            | 4.65 / 0.66        |
    | 8  | Total Net Profit(2.10.2)             | -18.41 ↓            | 76.74 ↑             | 0.58 ↓              | -14.98 ↓            | 23.04 ↑             | 29.35 ↑             | -34.68 ↓            | 61.64 / 8.81       |
    | 9  | Total Net Profit Rate(2.10.0)        | -0.23 %             | 1.29 %              | 0.84 %              | 1.43 %              | -0.1 %              | -0.06 %             | -0.06 %             | 3.11 % / 0.44 %    |
    | 9  | Total Net Profit Rate(2.10.1)        | 0.07 % ↑            | 1.23 % ↓            | 0.01 % ↓            | -0.69 % ↓           | 0.18 % ↑            | 0.67 % ↑            | -1.38 % ↓           | 0.09 % / 0.01 %    |
    | 9  | Total Net Profit Rate(2.10.2)        | -0.37 % ↓           | 1.53 % ↑            | 0.01 % ↓            | -0.3 % ↓            | 0.46 % ↑            | 0.59 % ↑            | -0.69 % ↓           | 1.23 % / 0.18 %    |
    ...

    pixiu -c pixiu.json -n testUSDCAD_A -t strategy-v1 -r strategy-v2 strategy-v3 -l strategy_compare.json
    Output:
    +----+--------------------------------------+---------------------+-------------------+
    |    |                                      | testUSDCAD_A | Total/Avg         |
    +----+--------------------------------------+---------------------+-------------------+
    | 1  | Init Balance(2.10.0)                 | 5000.0              | 5000.0 / 5000.0   |
    | 1  | Init Balance(2.10.1)                 | 5000.0              | 5000.0 / 5000.0   |
    | 1  | Init Balance(2.10.2)                 | 5000.0              | 5000.0 / 5000.0   |
    ...
    | 7  | Balance(2.10.0)                      | 4996.94             | 4996.94 / 4996.94 |
    | 7  | Balance(2.10.1)                      | 4931.17 ↓           | 4931.17 / 4931.17 |
    | 7  | Balance(2.10.2)                      | 4965.34 ↓           | 4965.34 / 4965.34 |
    | 8  | Total Net Profit(2.10.0)             | -3.05               | -3.05 / -3.05     |
    | 8  | Total Net Profit(2.10.1)             | -68.84 ↓            | -68.84 / -68.84   |
    | 8  | Total Net Profit(2.10.2)             | -34.68 ↓            | -34.68 / -34.68   |
    | 9  | Total Net Profit Rate(2.10.0)        | -0.06 %             | -0.06 % / -0.06 % |
    | 9  | Total Net Profit Rate(2.10.1)        | -1.38 % ↓           | -1.38 % / -1.38 % |
    | 9  | Total Net Profit Rate(2.10.2)        | -0.69 % ↓           | -0.69 % / -0.69 % |
    ...


测试配置文件格式
=======
json 格式:
例子：
```json
{
 "accounts": {
    "default": {
      "balance": 10000.0,
      "equity": 10000.0,
      "margin": 0,
      "free_margin": 10000.0,
      "credit": 0.0,
      "profit": 0.0,
      "margin_level": 0,
      "leverage": 100,
      "currency": "USD",
      "free_margin_mode": 0,
      "stop_out_level": 0,
      "stop_out_mode": 0,
      "company": "TradePython.com",
      "name": "PXTester",
      "number": "000",
      "server": "PXTester",
      "trade_mode": 0,
      "limit_orders": 500,
      "margin_so_mode": 0,
      "trade_allowed": true,
      "trade_expert": 1,
      "margin_so_call": 0.0,
      "margin_so_so": 0.0,
      "commission": 0.0
    }
  },
  "symbols": {
    "USDCHF": {
      "symbol": "USDCHF",
      "spread": 2,
      "digits": 5,
      "stop_level": 0,
      "volume_min": 0.01,
      "trade_contract_size": 100000,
      "point": 0.00001,
      "currency_profit": "CHF",
      "currency_base": "USD",
      "currency_margin": "USD"
    }
  },
  "tests": {
    "testUSDCHF": {
      "symbol": "USDCHF",
      "tick_data": "usdchf_m1_20210315-0415.csv",
      "start_time": "2021-03-15",
      "end_time": "2021-04-16",
      "max_tick": 100,
      "balance": 10000,
      "leverage": 100,
      "currency": "USD",
      "account": "default",
      "spread_point": 15
    },
    "testUSDCHF_TP": {
      "symbol": "USDCHF",
      "tick_data": {
         "channel": "tradepython.com",
         "api_token": "YOUR-API-TOKEN",
         "source": "12345678@PixiuServer01",
         "format": "json",
         "period": 30,
         "timeframe": "m1"
      },
      "max_tick": 100,
      "balance": 10000,
      "leverage": 100,
      "currency": "USD",
      "account": "default",
      "spread_point": 15
    },
    "testUSDCHF_TP2": {
      "symbol": "USDCHF",
      "tick_data": {
         "channel": "tradepython.com",
         "api_token": "YOUR-API-TOKEN",
         "source": {"type": "public", "name": "sample-public-feed"},
         "format": "json",
         "period": 30,
         "start_time": "2021-03-15",
         "end_time": "2021-04-16",
         "timeframe": "m1"
      },
      "start_time": "2021-03-15",
      "end_time": "2021-04-16",
      "max_tick": 100,
      "balance": 10000,
      "leverage": 100,
      "currency": "USD",
      "account": "default",
      "spread_point": 15
    }
  }
}
```

使用csv文件测试：
    symbol:     测试产品
    tick_data:  tick data 数据文件
    start_time: 开始时间
    end_time:   结束时间
    max_tick:   测试的最大tick数量，可以减少测试时间
    balance:    测试账户初始资金
    leverage:    测试账户杠杆率
    account:    测试账户名称（在测试配置文件accounts中）
    spread_point: Spread

```json
"testUSDCHF": {
  "symbol": "USDCHF",
  "tick_data": "usdchf_m1_20210315-0415.csv",
  "start_time": "2021-03-15",
  "end_time": "2021-04-16",
  "max_tick": 100,
  "balance": 10000,
  "leverage": 100,
  "currency": "USD",
  "account": "default",
  "spread_point": 15
}
```

使用tradepython 数据测试测试
source: 数据账号
  account@account-server
  例如:
      12345678@PixiuServer01
  或: {"type": "public", "name": "sample-public-feed"}
  type: public 或者 private
  name: 账号名称

period: 数据周期（天）
  例如：
      30 - 最近30天数据
timeframe: 时间帧，以下值
    s1  - 1秒
    m1  - 1分钟
    m5  - 1分钟
    m15 - 15分钟
    m30 - 30分钟
    h1  - 1小时
    h4  - 1小时
    d1  - 1天
    w1  - 1周
    mn1 - 1月

```json
"testUSDCHF_TP": {
   ...
  "tick_data": {
     "channel": "tradepython.com",
     "api_token": "YOUR-API-TOKEN",
     "source": "account@account-server",
     "format": "json",
     "period": 30,
     "timeframe": "m1"
  },
  ...
}
```

交叉货币换算
=======

当交易品种的盈亏币种或保证金币种与账户币种不一致时，Pixiu 可以在测试过程中把盈亏和保证金换算到账户币种。

通过 `currency_conversion_settings` 启用动态换汇：

```json
{
  "tests": {
    "testEURGBP_USD": {
      "symbol": "EURGBP",
      "account": "default",
      "currency": "USD",
      "tick_data": {
        "channel": "tradepython.com",
        "api_token": "YOUR-API-TOKEN",
        "source": {"type": "public", "name": "sample-public-feed"},
        "format": "json",
        "period": 30,
        "timeframe": "m1"
      },
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
  }
}
```

第一版支持的行为：

    mode: dynamic
      使用换汇 symbol 的 tick 数据。

    auto_download: true
      PXTester 会在回测 tick loop 开始前，从相同 tick_data channel 尝试加载缺失的换汇 symbol。

    download_policy: before_test
      换汇数据在测试开始前准备。Pixiu 不会在 tick loop 中下载数据。

    path_policy: direct_then_usd
      Pixiu 先尝试直接或反向换汇对。如果不可用，且两边都不是 USD，则使用 USD 中转。

    time_alignment: latest_before_or_at_tick
      使用当前测试 tick 时间之前或等于当前时间的最近一条换汇 tick。

示例：

    GBP -> JPY:
      优先使用 GBPJPY。
      如果 GBPJPY 不可用，使用 GBPUSD + USDJPY。

    GBP -> USD:
      优先使用 GBPUSD。
      如果 GBPUSD 不可用，使用 USDGBP。

可以通过 `currency_conversions` 显式配置换汇来源：

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

完整开发说明见 `CROSS_CURRENCY.zh.md`。

脚本例子
=======
1.买入或卖出一个产品
    errid, order_uid = Buy(volume=volume, price=Ask())
    errid, order_uid = Sell(volume=0.01, price=Bid())

2.修改一个订单
    errid, order_uid = ModifyOrder(order_uid, stop_loss=stop_loss, take_profit=take_profit)

3.关闭一个订单
    errid, order_uid = CloseOrder(order_uid, price=Ask(), volume=volume)

4.获得当前开仓的订单UIDs
    uids = GetOpenedOrderUIDs()
    for uid in uids:
        o = GetOrder(uid)


API
=======

```python
AccountEquity(self)
   Returns the equity.

           Returns:
                   The account equity.

AccountFreeMargin(self)
   Returns the free margin.

           Returns:
                   The free margin.

CalcProfit(order_type, symbol, volume, open_price, close_price) -> float
   计算一笔假设订单的账户币种盈亏。

           Parameters:
                   order_type: 订单方向，支持 OrderCommand.BUY 和 OrderCommand.SELL。
                   symbol (str): 交易品种。None 表示当前 symbol。
                   volume (float): 手数。
                   open_price (float): 假设开仓价。
                   close_price (float): 假设平仓价。

           Returns:
                   账户币种盈亏。正数表示盈利，负数表示亏损。

OrderCalcProfit(order_type, symbol, volume, open_price, close_price) -> float
   CalcProfit 的 MT5 风格别名。

CalcMargin(order_type, symbol, volume, price) -> float
   计算一笔假设订单的账户币种保证金。

           Parameters:
                   order_type: 订单方向，支持 OrderCommand.BUY 和 OrderCommand.SELL。
                   symbol (str): 交易品种。None 表示当前 symbol。
                   volume (float): 手数。
                   price (float): 假设开仓价。

           Returns:
                   账户币种保证金。

OrderCalcMargin(order_type, symbol, volume, price) -> float
   CalcMargin 的 MT5 风格别名。

TickValue(symbol=None, order_type=OrderCommand.BUY, price=None) -> float
   返回 1 手交易时 1 tick 对应的账户币种价值。

           Parameters:
                   symbol (str): 交易品种。None 表示当前 symbol。
                   order_type: 用于估算的订单方向。
                   price (float): 参考价格。None 表示使用当前市场价格。

           Returns:
                   1 手 1 tick 的账户币种价值。

PipValue(symbol=None, order_type=OrderCommand.BUY, price=None) -> float
   返回 1 手交易时 1 pip 对应的账户币种价值。

           Parameters:
                   symbol (str): 交易品种。None 表示当前 symbol。
                   order_type: 用于估算的订单方向。
                   price (float): 参考价格。None 表示使用当前市场价格。

           Returns:
                   1 手 1 pip 的账户币种价值。

Ask(self, shift=0, symbol=None) -> float
   Returns Ask price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Ask price.

Bid(self, shift=0, symbol=None) -> float
   Returns Bid price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Bid price.

Buy(self, volume: float, type=0, price=None, stop_loss=None, take_profit=None, magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None, tags=None) -> tuple[ErrorID, OrderResult]
   Open a long order.

           Parameters:
                   volume (float): Number of lots.
                   type (OrderType): Order type.
                   price (float): Order price. If price is None, price = Ask().
                   stop_loss (float): Stop loss price.
                   take_profit (float): Take profit price.
                   magic_number (float): Order magic number.
                   symbol (float): Symbol for trading.
                   slippage (float): Maximum price slippage for trading.
                   arrow_color (float): Color of the opening arrow on the MT4/5 chart.
                   expiration (float): Order expiration time (for pending order only)
                   tags (dict): Order tags

           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.


Sell(self, volume: float, type=0, price=None, stop_loss=None, take_profit=None, magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None, tags=None) -> tuple[ErrorID, OrderResult]
   Open a short order.

           Parameters:
                   volume (float): Number of lots.
                   type (OrderType): Order type.
                   price (float): Order price. If price is None, price = Bid().
                   stop_loss (float): Stop loss price.
                   take_profit (float): Take profit price.
                   magic_number (float): Order magic number.
                   symbol (float): Symbol for trading.
                   slippage (float): Maximum price slippage for trading.
                   arrow_color (float): Color of the opening arrow on the MT4/5 chart.
                   expiration (float): Order expiration time (for pending order only)
                   tags (dict): Order tags

           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.


ModifyOrder(self, uid, price=None, stop_loss=None, take_profit=None, arrow_color=None, expiration=None, tags=None) -> tuple[ErrorID, OrderResult]
   Modify a order.

           Parameters:
                   uid : The order UID.
                   price (float): New open price. (for pending order only)
                   stop_loss (float): New stop loss price.
                   take_profit (float): New take profit price.
                   arrow_color (float): New color of the opening arrow on the MT4/5 chart.
                   expiration (float): New order expiration time (for pending order only)
                   tags (dict): Order tags
           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.

UpdateOrderTags(self, uid, tags=None, patch=None, merge=True, remove_keys=None, expected_tag_ver=None) -> tuple[ErrorID, dict]
   只更新已有订单的 tags。

           这个 API 用于记录策略元数据，例如订单由哪个策略创建、当前由哪个
           管理器接管。它不会发送交易平台的改单指令，也不会修改 volume、
           open price、stop loss、take profit、order status 等交易字段。

           Parameters:
                   uid : 订单 UID。
                   tags (dict): 要写入的 tags。merge=True 时会合并到已有
                           tags；merge=False 时会替换已有 tags。
                   patch (dict): 要合并到已有 tags 的局部更新内容，适合表达
                           增量修改。
                   merge (bool): True 表示把 tags/patch 合并到当前 tags；
                           False 表示用 tags 替换当前 tags，如果 tags 为 None
                           则使用 patch 替换。
                   remove_keys (list): 合并或替换后需要删除的 tag key。
                   expected_tag_ver: 可选的乐观锁版本。如果传入该值，且当前
                           tags.tag_ver 不匹配，则更新失败。

           Returns:
                   ErrorID: 0 表示成功。
                   dict: {'order_uid': uid, 'tags': updated_tags, 'sync': True}

SetOrderTags(self, uid, tags) -> tuple[ErrorID, dict]
   替换已有订单的全部 tags。

           这是 UpdateOrderTags(uid, tags=tags, merge=False) 的便捷封装。
           它只更新订单 tags，不会修改任何交易字段。

           Parameters:
                   uid : 订单 UID。
                   tags (dict): 要保存的完整 tag 字典。

           Returns:
                   ErrorID: 0 表示成功。
                   dict: {'order_uid': uid, 'tags': updated_tags, 'sync': True}

CloseOrder(self, uid, price, volume: float, slippage=None, arrow_color=None, tags=None) -> tuple[ErrorID, OrderResult]
   Close a order.

           Parameters:
                   uid : The order UID.
                   price (float): Close price.
                   volume (float): Number of lots.
                   slippage (float): Maximum price slippage for trading.
                   arrow_color (float): New color of the opening arrow on the MT4/5 chart.
                   tags (dict): Order tags

           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.


Close(self, shift=0, symbol=None) -> float
   Returns Close price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                    symbol (str): The symbol name.
                            If None returns current symbol.

           Returns:
                   Close price.

DefaultTimeFrame(self)
   Returns the default time frame.

GetAccount(self)
   Returns the account data.

           Returns:
                   The account data.

GetClosedOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA)
   Returns the UIDs of current closed orders.

           Parameters:
                   symbol: The symbol name.
                           If None returns current symbol.
                           If '*' returns all symbols.
                   scope:
                           EA: The current ea (default).
                           ACCOUNT: The current account.
                           EA_VERSION: The current ea version.

           Returns:
                   The uid list.

GetOpenedOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA)
   Returns the UIDs of current opened orders.

           Parameters:
                   symbol: The symbol name.
                           If None returns current symbol.
                           If '*' returns all symbols.
                   scope:
                           EA: The current ea (default).
                           ACCOUNT: The current account.
                           EA_VERSION: The current ea version.


           Returns:
                   The uid list.


GetPendingOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA)
   Returns the UIDs of current pending orders.

           Parameters:
                   symbol: The symbol name.
                           If None returns current symbol.
                           If '*' returns all symbols.
                   scope:
                           EA: The current ea (default).
                           ACCOUNT: The current account.
                           EA_VERSION: The current ea version.

           Returns:
                   The uid list.

GetOrder(self, order_uid: OrderUID)
   Returns the order object.

           Parameters:
                   order_uid (): The order uid.

           Returns:
                   The order object.

GetParam(self, name, default=None)
   Returns the EA parameter value.

           Parameters:
                   name (): The EA parameter name.
                   default (int): The EA parameter default value.

           Returns:
                   The EA parameter value.

EA_SETTINGS
   只读 EA 参数访问对象，底层读取现有 GetParam/script_settings.params。

           Usage:
                   EA_SETTINGS.grid_pips
                   EA_SETTINGS.get("grid_pips", 0, "int")
                   EA_SETTINGS.get("enabled", False, "bool")

           Notes:
                   属性访问在参数不存在时返回 None。
                   get(name, default, value_type) 支持 raw、bool、int、float。
                   EA_SETTINGS 暂不提供写入或双向通信接口。

EA 参数优化元数据
   Pixiu 将 EA 参数保存在 script_settings.params 中。每个参数都可以在
   config 里定义优化元数据，供 EAOptim 等外部优化器识别“哪些参数允许优化”
   以及“默认优化范围是什么”。

           推荐字段：
                   config.optimizable (bool)：
                           是否允许该参数进入优化。
                           推荐默认值：false。

                   config.optimization (dict)：
                           可选；定义默认优化范围。推荐字段：
                           type、start、stop、step。
                           其中 type 一般与 config.type 保持一致。

           示例：
                   AddParam(
                       "grid_atr_ratio",
                       value=0.5,
                       type="float",
                       min=0.1,
                       max=2.0,
                       required=True,
                       optimizable=True,
                       optimization={"type": "float", "start": 0.1, "stop": 1.5, "step": 0.1},
                       desc={"en": "Grid ATR ratio", "zh": "网格 ATR 比例"}
                   )

                   AddParam(
                       "group_target_profit",
                       param={
                           "value": "1.0%",
                           "config": {
                               "type": "percent",
                               "required": False,
                               "optimizable": True,
                               "optimization": {
                                   "type": "percent",
                                   "start": "0.5%",
                                   "stop": "5.0%",
                                   "step": "0.5%"
                               }
                           }
                       }
                   )

           说明：
                   优化界面应只展示 config.optimizable=true 的参数。
                   optimization.start/stop/step 应与参数类型保持同样的表达方式：
                   int/float 使用数值，percent 使用百分号字符串。
                   运行时的 GetParam 和 EA_SETTINGS 行为不变；这些字段主要用于
                   工具层展示和校验。

GetSettings(self, name, default=None)
    Returns the EA Settings value.

            Parameters:
                    name (): The EA settings name.
                    default (int): The EA settings default value.

            Returns:
                    The EA settings value.

GetSymbol(self, symbol=None)
   Returns the symbol properties.

           Parameters:
                   symbol (str): The symbol name.

           Returns:
                   The symbol properties

GetSymbolData(self, symbol: str, timeframe: str, size: int)
   Get a symbol data.

           Parameters:
                   symbol (str): Symbol name.
                   timeframe (str): Timeframe. See the TimeFrame defining.
                   size (int): Maximum size.

           Returns:
                   Symbol data

High(self, shift=0, symbol=None) -> float
   Returns High price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   High price.

Low(self, shift=0, symbol=None) -> float
   Returns Low price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Low price.

Open(self, shift=0, symbol=None) -> float
   Returns Open price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Open price.

OrderStats(self, order_uids)
   Returns the order statistics.

           Parameters:
                   order_uids : the list of order uids.

           Returns:
                   The order statistics.


StopTester(self, code: int = 0, message: str = None)
   Stop the EA tester. (For tester only.)

           Parameters:
                   code (int): Error code.
                   message (str): Error message.

           Returns:
                   None

Symbol(self) -> str
   Returns the current symbol name.

           Returns:
                   The symbol name.

SymbolInfo(self, item, symbol=None, default=None)
   Returns the symbol information.

           Parameters:
                   item (str): The symbol item name.
                   symbol (str): The symbol name.
                   default (): The default value.

           Returns:
                   The symbol information.

Time(self, shift=0, symbol=None) -> datetime.datetime
   Returns time value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Time.

Volume(self, shift=0, symbol=None) -> float
   Returns volume value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).
                   symbol (str): The symbol name.
                           If None returns current symbol.

           Returns:
                   Volume price.

__init__(self)
   Initialize self.  See help(type(self)) for accurate signature.

iAD(self, symbol_data, shift=0)
   Chaikin A/D Line (Volume Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Chaikin A/D Line

iADX(self, symbol_data, timeperiod, shift=0)
   Average Directional Movement Index (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Average Directional Movement Index

iATR(self, symbol_data, timeperiod, shift=0)
   Average True Range (Volatility Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Average True Range

iBands(self, symbol_data, timeperiod, nbdevup, nbdevdn, matype, shift=0)
   Bollinger Bands (Overlap Studies)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   nbdevup (int): 2
                   nbdevdn (int): 2
                   ma_type: 0 (Simple Moving Average) ,For details see the TA-LIB
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Bollinger Bands

iCCI(self, symbol_data, timeperiod, shift=0)
   Commodity Channel Index (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Commodity Channel Index

iChaikin(self, symbol_data, fastperiod, slowperiod, shift=0)
   Chaikin A/D Oscillator (Volume Indicators)

          Parameters:
                  symbol_data (object): The symbol data.
                  fastperiod (int): The fast period.
                  slowperiod (int): The low period.
                  shift: Index of the value taken from the buffer
                  (shift relative to the current the given amount of periods ago).

          Returns:
                  Chaikin A/D Oscillator

iDEMA(self, symbol_data, timeperiod, shift=0)
   Double Exponential Moving Average (Overlap Studies)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Double Exponential Moving Average

iMA(self, price_data, period, ma_type, shift=0)
   Calculates the Moving Average indicator and returns its value.

           Parameters:
                   price_data (object): The price data. (Close, Open, Low, etc...)
                   period (int): Averaging period for calculation.
                   ma_type: 0 (Simple Moving Average) ,For details see the TA-LIB
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Moving average value.

iMACD(self, symbol_data, fastperiod, slowperiod, signalperiod, shift=0)
   Moving Average Convergence/Divergence (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   fastperiod (int): The fast period.
                   slowperiod (int): The slow period.
                   signalperiod (int): The signal period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Moving Average Convergence/Divergence

iMFI(self, symbol_data, timeperiod, shift=0)
   Money Flow Index (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Money Flow Index

iMomentum(self, symbol_data, timeperiod, shift=0)
   Momentum (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Momentum

iOBV(self, symbol_data, shift=0)
   On Balance Volume (Volume Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   On Balance Volume

iRSI(self, symbol_data, timeperiod, shift=0)
   Relative Strength Index (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Relative Strength Index

iSAR(self, symbol_data, acceleration, maximum, shift=0)
   Parabolic SAR (Overlap Studies)

           Parameters:
                   symbol_data (object): The symbol data.
                   acceleration (int): 0.02
                   maximum (int): 0.2
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Parabolic SAR

iStdDev(self, symbol_data, timeperiod, nbdev, shift=0)
   Standard Deviation (Statistic Functions)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   nbdev (int): 1
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Standard Deviation

iStochastic(self, symbol_data, fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype, shift=0)
   Stochastic (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   fastk_period (int): 5
                   slowk_period (int): 3
                   slowk_matype (int): 0
                   slowd_period (int): 3
                   slowd_matype (int): 0
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Stochastic

iTEMA(self, price_data, timeperiod, shift=0)
   Triple Exponential Moving Average (Overlap Studies)

           Parameters:
                   price_data (object): The price data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Triple Exponential Moving Average

iWPR(self, symbol_data, timeperiod, shift=0)
   Williams' %R (Momentum Indicators)

           Parameters:
                   symbol_data (object): The symbol data.
                   timeperiod (int): The time period.
                   shift: Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Williams' %R

WaitCommand(self, uid, timeout=120)
   Waiting for a asynchronous command execution。

          Parameters:
                  uid : The command UID.
                  timeout : Timeout （seconds）
          Returns:
                  ErrorID: If 0 success.
                  CommandResult: If failed returns None.


 AcquireLock(self, name, timeout=60) -> bool:
     Acquire a lock

             Parameters:
                     name : The lock name
                     timeout : Lock timeout （seconds）
             Returns:
                     If True success.


 ReleaseLock(self, name):
     Release a lock

             Parameters:
                     name : The lock name


 Plot(self, series):
     Plot

             Parameters:
                     series


 DeleteData(self, name, scope: int = DataScope.EA) -> ErrorID:
     Delete data

             Parameters:
                     name : The data name
                     scope : The data scope (current EA settings `EA_SETTINGS`, current account + current EA `ACCOUNT_EA`, EA version, EA, Account)
             Returns:
                     The errorid.

 LoadData(self, name, scope: int = DataScope.EA, format='json'):
     Load data

             Parameters:
                     name : The data name
                     scope : The data scope (current EA settings `EA_SETTINGS`, current account + current EA `ACCOUNT_EA`, EA version, EA, Account)
                     format: Only support JSON.
             Returns:
                     data.

 SaveData(self, name, data, scope: int = DataScope.EA, format='json') -> ErrorID:
     Save data

             Parameters:
                     name : The data name
                     scope : The data scope (current EA settings `EA_SETTINGS`, current account + current EA `ACCOUNT_EA`, EA version, EA, Account)
                     format: Only support JSON.
             Returns:
                     The errorid.

 Notify(self, message) -> ErrorID:
     Send a notification

             Parameters:
                     message: The content of notification
             Returns:
                     The errorid.


```
