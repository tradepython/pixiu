<p align="center">
<img width="128" height="128" src="https://raw.githubusercontent.com/tradepython/pixiu/main/pixiu-128x128-8bit.png">
</p>


PiXiu - 貔貅
=======
貔貅是一款交易回测工具，它是仿照 MT4/MT5 的测试器开发的。
它有一套标准的API定义，使用这些API编写的回测代码，可以无需更改的在www.TradePython.com上运行。

安装
=======
pip install pixiu


使用方法
=======
参数:
    -c  测试配置文件
    -n  测试名称（测试配置文件中）
    -s  脚本文件
    -o  日志文件

pixiu -c pixiu_sample.json -n testUSDCHF_TP -s pixiu_sample.py
pixiu -c pixiu_sample.json -n testUSDCHF_TP -s pixiu_sample.py
pixiu -c pixiu_sample.json -n testUSDCHF -s pixiu_sample2.py -o log.txt

测试配置文件格式
=======
json 格式:
例子：
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
         "source": {"type": "public", "name": "Demo1"},
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

使用tradepython 数据测试测试
source: 数据账号
  account@account-server
  例如:
      12345678@PixiuServer01
  或: {"type": "public", "name": "Demo1"}
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

Ask(self, shift=0) -> float
   Returns Ask price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Ask price.

Bid(self, shift=0) -> float
   Returns Bid price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Bid price.

Buy(self, volume: float, type=0, price=None, stop_loss=None, take_profit=None, magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None) -> (<function NewType.<locals>.new_type at 0x7fe120629dc0>, <function NewType.<locals>.new_type at 0x7fe122ed0940>)
   Open a buy order.

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
           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.

Close(self, shift=0) -> float
   Returns Close price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Close price.

CloseOrder(self, uid, price, volume: float, slippage=None, arrow_color=None) -> (<function NewType.<locals>.new_type at 0x7fe120629dc0>, <function NewType.<locals>.new_type at 0x7fe122ed0940>)
   Close a order.

           Parameters:
                   uid : The order UID.
                   price (float): Close price.
                   volume (float): Number of lots.
                   slippage (float): Maximum price slippage for trading.
                   arrow_color (float): New color of the opening arrow on the MT4/5 chart.
           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.

DefaultTimeFrame(self)
   Returns the default time frame.

GetAccount(self)
   Returns the account data.

           Returns:
                   The account data.

GetClosedOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA)
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

GetOpenedOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA)
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


GetPendingOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA)
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

GetOrder(self, order_uid: <function NewType.<locals>.new_type at 0x7fe122ed0940>)
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

GetSymbol(self, symbol=None)
   Returns the symbol properties.

           Parameters:
                   symbol (int): The symbol name.

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

High(self, shift=0) -> float
   Returns High price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   High price.

Low(self, shift=0) -> float
   Returns Low price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Low price.

ModifyOrder(self, uid, price=None, stop_loss=None, take_profit=None, arrow_color=None, expiration=None) -> (<function NewType.<locals>.new_type at 0x7fe120629dc0>, <function NewType.<locals>.new_type at 0x7fe122ed0940>)
   Modify a order.

           Parameters:
                   uid : The order UID.
                   price (float): New open price. (for pending order only)
                   stop_loss (float): New stop loss price.
                   take_profit (float): New take profit price.
                   arrow_color (float): New color of the opening arrow on the MT4/5 chart.
                   expiration (float): New order expiration time (for pending order only)
           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.

Open(self, shift=0) -> float
   Returns Open price value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Open price.

OrderStats(self, order_uids)
   Returns the order statistics.

           Parameters:
                   order_uids : the list of order uids.

           Returns:
                   The order statistics.

Sell(self, volume: float, type=0, price=None, stop_loss=None, take_profit=None, magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None) -> (<function NewType.<locals>.new_type at 0x7fe120629dc0>, <function NewType.<locals>.new_type at 0x7fe122ed0940>)
   Open a sell order.

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
           Returns:
                   ErrorID: If 0 success.
                   OrderResult: The order result.

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

Time(self, shift=0) -> datetime.datetime
   Returns time value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

           Returns:
                   Time.

Volume(self, shift=0) -> float
   Returns volume value for the default symbol with default timeframe and shift.

           Parameters:
                   shift (int): Index of the value taken from the buffer
                   (shift relative to the current the given amount of periods ago).

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

iTEMA(self, symbol_data, timeperiod, shift=0)
   Triple Exponential Moving Average (Overlap Studies)

           Parameters:
                   symbol_data (object): The symbol data.
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

```
