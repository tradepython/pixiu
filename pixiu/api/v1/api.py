'''
PIXIU API
'''
from typing import NewType, TypeVar, Generic
import abc
from datetime import datetime
from pixiu.api.defines import (TimeFrame, OrderType, OrderCommand)
from .order import Order

class IndicatiorID():
    MA = 1000
    AD = 2000
    ADX = 3000
    ATR = 4000
    BANDS = 5000
    CCI = 6000
    CHAIKIN = 7000
    DEMA = 8000
    MOMENTUM = 9000
    MFI = 10000
    MACD = 11000
    OBV = 12000
    SAR = 13000
    RSI = 14000
    STDDEV = 15000
    STOCHASTIC = 16000
    TEMA = 17000
    WPR = 18000

ErrorID = NewType('ErrorID', int)
Result = NewType('Result', dict)
UID = NewType('UID', str)
OrderUID = NewType('OrderUID', UID)
OrderResult = NewType('OrderResult', Result)
CommandResult = NewType('CommandResult', Result)


class APIStub(abc.ABC):
    __global_defines__ = dict(
        TimeFrame=TimeFrame,
        OrderType=OrderType,
        OrderCommand=OrderCommand,
        Order=Order,
    )

    def __init__(self):
        pass

    @abc.abstractmethod
    def DefaultTimeFrame(self):
        '''
        Returns the default time frame.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Buy(self, volume: float, type=OrderType.MARKET, price=None, stop_loss=None, take_profit=None,
            magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None) -> (ErrorID, OrderResult):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Sell(self, volume: float, type=OrderType.MARKET, price=None, stop_loss=None, take_profit=None,
             magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None) -> (ErrorID, OrderResult):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def ModifyOrder(self, uid, price=None, stop_loss=None, take_profit=None,
                     arrow_color=None, expiration=None) -> (ErrorID, OrderResult):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    # def CloseOrder(self, uid, price, volume: float, slippage=None, arrow_color=None) -> (ErrorID, OrderResult):
    def CloseOrder(self, uid, volume=None, price=None, slippage=None, arrow_color=None) -> (ErrorID, OrderResult):
        '''
        Close a order.

                Parameters:
                        uid : The order UID.
                        volume (float): Number of lots. If volume is None or zero, volume = order.volume
                        price (float): Close price. If price is None or zero, price = OrderClosePrice(MT4/MT5)
                        slippage (float): Maximum price slippage for trading.
                        arrow_color (float): New color of the opening arrow on the MT4/5 chart.
                Returns:
                        ErrorID: If 0 success.
                        OrderResult: The order result.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetSymbolData(self, symbol: str, timeframe: str, size: int):
        '''
        Get a symbol data.

                Parameters:
                        symbol (str): Symbol name.
                        timeframe (str): Timeframe. See the TimeFrame defining.
                        size (int): Maximum size.

                Returns:
                        Symbol data
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def StopTester(self, code: int = 0, message: str = None):
        '''
        Stop the EA tester. (For tester only.)

                Parameters:
                        code (int): Error code.
                        message (str): Error message.

                Returns:
                        None
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetSymbol(self, symbol=None):
        '''
        Returns the symbol properties.

                Parameters:
                        symbol (int): The symbol name.

                Returns:
                        The symbol properties
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetAccount(self):
        '''
        Returns the account data.

                Returns:
                        The account data.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def AccountEquity(self, ):
        '''
        Returns the equity.

                Returns:
                        The account equity.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def AccountFreeMargin(self, ):
        '''
        Returns the free margin.

                Returns:
                        The free margin.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def SymbolInfo(self, item, symbol=None, default=None):
        '''
        Returns the symbol information.

                Parameters:
                        item (str): The symbol item name.
                        symbol (str): The symbol name.
                        default (): The default value.

                Returns:
                        The symbol information.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetParam(self, name, default=None):
        '''
        Returns the EA parameter value.

                Parameters:
                        name (): The EA parameter name.
                        default (int): The EA parameter default value.

                Returns:
                        The EA parameter value.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def OrderStats(self, order_uids):
        '''
        Returns the order statistics.

                Parameters:
                        order_uids : the list of order uids.

                Returns:
                        The order statistics.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetOrder(self, order_uid: OrderUID):
        '''
        Returns the order object.

                Parameters:
                        order_uid (): The order uid.

                Returns:
                        The order object.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Close(self, shift=0) -> float:
        '''
        Returns Close price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Close price.
        '''
        raise NotImplementedError
    #
    @abc.abstractmethod
    def Open(self, shift=0) -> float:
        '''
        Returns Open price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Open price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def High(self, shift=0) -> float:
        '''
        Returns High price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        High price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Low(self, shift=0) -> float:
        '''
        Returns Low price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Low price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Ask(self, shift=0) -> float:
        '''
        Returns Ask price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Ask price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Bid(self, shift=0) -> float:
        '''
        Returns Bid price value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Bid price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Time(self, shift=0) -> datetime:
        '''
        Returns time value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Time.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Volume(self, shift=0) -> float:
        '''
        Returns volume value for the default symbol with default timeframe and shift.

                Parameters:
                        shift (int): Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Volume price.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def Symbol(self) -> str:
        '''
        Returns the current symbol name.

                Returns:
                        The symbol name.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetOpenedOrderUIDs(self, symbol: str = None):
        '''
        Returns the UIDs of current opened orders.

                Parameters:
                        symbol: The symbol name.
                                If None returns current symbol.
                                If '*' returns all symbols.

                Returns:
                        The uid list.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetPendingOrderUIDs(self, symbol: str = None):
        '''
        Returns the UIDs of current pending orders.

                Parameters:
                        symbol: The symbol name.
                                If None returns current symbol.
                                If '*' returns all symbols.

                Returns:
                        The uid list.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def GetClosedOrderUIDs(self, symbol: str = None):
        '''
        Returns the UIDs of current closed orders.

                Parameters:
                        symbol: The symbol name.
                                If None returns current symbol.
                                If '*' returns all symbols.

                Returns:
                        The uid list.
        '''
        raise NotImplementedError

    # --------------------------------
    @abc.abstractmethod
    def iMA(self, price_data, period, ma_type, shift=0):
        '''
        Calculates the Moving Average indicator and returns its value.

                Parameters:
                        price_data (object): The price data. (Close, Open, Low, etc...)
                        period (int): Averaging period for calculation.
                        ma_type: 0 (Simple Moving Average) ,For details see the TA-LIB
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Moving average value.
        '''
        raise NotImplementedError

    # https://mrjbq7.github.io/ta-lib/func_groups/volume_indicators.html
    @abc.abstractmethod
    def iAD(self, symbol_data, shift=0):
        '''
        Chaikin A/D Line (Volume Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Chaikin A/D Line
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iADX(self, symbol_data, timeperiod, shift=0):
        '''
        Average Directional Movement Index (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Average Directional Movement Index
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iATR(self, symbol_data, timeperiod, shift=0):
        '''
        Average True Range (Volatility Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Average True Range
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iBands(self, symbol_data, timeperiod, nbdevup, nbdevdn, matype, shift=0):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iCCI(self, symbol_data, timeperiod, shift=0):
        '''
        Commodity Channel Index (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Commodity Channel Index
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iChaikin(self, symbol_data, fastperiod, slowperiod, shift=0):
        '''
         Chaikin A/D Oscillator (Volume Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        fastperiod (int): The fast period.
                        slowperiod (int): The low period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Chaikin A/D Oscillator
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iDEMA(self, symbol_data, timeperiod, shift=0):
        '''
        Double Exponential Moving Average (Overlap Studies)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Double Exponential Moving Average
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iMomentum(self, symbol_data, timeperiod, shift=0):
        '''
        Momentum (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Momentum
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iMFI(self, symbol_data, timeperiod, shift=0):
        '''
        Money Flow Index (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Money Flow Index
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iMACD(self, symbol_data, fastperiod, slowperiod, signalperiod, shift=0):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iOBV(self, symbol_data, shift=0):
        '''
        On Balance Volume (Volume Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        On Balance Volume
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iSAR(self, symbol_data, acceleration, maximum, shift=0):
        '''
        Parabolic SAR (Overlap Studies)

                Parameters:
                        symbol_data (object): The symbol data.
                        acceleration (int): 0.02
                        maximum (int): 0.2
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Parabolic SAR
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iRSI(self, symbol_data, timeperiod, shift=0):
        '''
        Relative Strength Index (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Relative Strength Index
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iStdDev(self, symbol_data, timeperiod, nbdev, shift=0):
        '''
        Standard Deviation (Statistic Functions)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        nbdev (int): 1
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Standard Deviation
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iStochastic(self, symbol_data, fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype, shift=0):
        '''
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
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iTEMA(self, symbol_data, timeperiod, shift=0):
        '''
        Triple Exponential Moving Average (Overlap Studies)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Triple Exponential Moving Average
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def iWPR(self, symbol_data, timeperiod, shift=0):
        '''
        Williams' %R (Momentum Indicators)

                Parameters:
                        symbol_data (object): The symbol data.
                        timeperiod (int): The time period.
                        shift: Index of the value taken from the buffer
                        (shift relative to the current the given amount of periods ago).

                Returns:
                        Williams' %R
        '''
        raise NotImplementedError

    #
    @abc.abstractmethod
    def WaitCommand(self, uid, timeout=120) -> (ErrorID, CommandResult):
        '''
        Waiting for a asynchronous command execution。

                Parameters:
                        uid : The command UID.
                        timeout : Timeout （seconds）
                Returns:
                        ErrorID: If 0 success.
                        CommandResult: If failed returns None.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def AcquireLock(self, name, timeout=60) -> bool:
        '''
        Acquire a lock

                Parameters:
                        name : The lock name
                        timeout : Lock timeout （seconds）
                Returns:
                        If True success.
        '''
        raise NotImplementedError

    @abc.abstractmethod
    def ReleaseLock(self, name):
        '''
        Release a lock。

                Parameters:
                        name : The lock name
        '''
        raise NotImplementedError


