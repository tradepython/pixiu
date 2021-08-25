
from ..base.api_base import (API_V1_Base)
import numpy as np
import talib
import logging
from datetime import datetime
from pixiu.api.v1 import (TimeFrame, OrderCommand, OrderType, IndicatiorID, SymbolIndicator, SymbolPrice, SymbolData,
                      Order, Account, Symbol, AccountData, ErrorID, OrderResult, OrderScope)
log = logging.getLogger(__name__)


#---------------------------------------------------------------------------------------------------------------------
# TesterAPI_V1
#---------------------------------------------------------------------------------------------------------------------
class TesterAPI_V1(API_V1_Base):
    def __init__(self, tester, data_source, default_symbol):
        super(TesterAPI_V1, self).__init__(data_source, default_symbol)
        self.tester = tester

    def _print_(self, *args, **kwargs):
        """"""
        return self.tester.get_print_factory(*args, **kwargs)
    #
    def Buy(self, volume, type=OrderType.MARKET, price=0, stop_loss=None, take_profit=None, comment=None,
            magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None):
        if symbol is None:
            symbol = self.default_symbol
        if price <= 0:
            price = self.Ask()

        if type == OrderType.MARKET:
            oct = OrderCommand.BUY
        elif type == OrderType.LIMIT:
            oct = OrderCommand.BUYLIMIT
        elif type == OrderType.STOP:
            oct = OrderCommand.BUYSTOP
        else:
            raise NotImplementedError

        return self.tester.open_order(symbol, oct, price, volume, stop_loss, take_profit,
                                           comment=comment, magic_number=magic_number, slippage=slippage,
                                           arrow_color=arrow_color)

    def Sell(self, volume, type=OrderType.MARKET, price=0, stop_loss=None, take_profit=None, comment=None,
             magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None):
        if symbol is None:
            symbol = self.default_symbol
        if price <= 0:
            price = self.Bid()

        if type == OrderType.MARKET:
            oct = OrderCommand.SELL
        elif type == OrderType.LIMIT:
            oct = OrderCommand.SELLLIMIT
        elif type == OrderType.STOP:
            oct = OrderCommand.SELLSTOP
        else:
            raise NotImplementedError
        return self.tester.open_order(symbol, oct, price, volume, stop_loss, take_profit,
                                           comment=comment, magic_number=magic_number, slippage=slippage,
                                           arrow_color=arrow_color)

    def ModifyOrder(self, uid, price=None, stop_loss=None, take_profit=None, comment=None,
                     arrow_color=None, expiration=None):
        return self.tester.modify_order(uid, price, stop_loss, take_profit,
                              comment=comment, arrow_color=arrow_color, expiration=expiration)

    #
    def CloseOrder(self, uid, volume: float=None, price=None,  slippage=None, arrow_color=None):
        return self.tester.close_order(uid, volume, price, slippage=slippage,
                              arrow_color=arrow_color)

    def WaitCommand(self, uid, timeout=120):
        return self.tester.wait_command(uid, timeout)

    def AcquireLock(self, name, timeout=60):
        return self.tester.acquire_lock(name, timeout)

    def ReleaseLock(self, name):
        return self.tester.release_lock(name)

    def DefaultTimeFrame(self):
        return self.tester.tick_timeframe

    def GetSymbolData(self, symbol: str, timeframe: str, size: int):
        data = self.tester.get_data_info(symbol, timeframe)
        return SymbolData(data, timeframe, getitem_callback=self.tester.symbol_datagetitem_callback)

    def GetAccount(self):
        return Account(self.tester.get_account())

    def GetSymbol(self, symbol=None):
        if symbol is None:
            symbol = self.default_symbol
        sp = self.tester.get_symbol_properties(symbol)
        return Symbol(sp)

    def AccountEquity(self):
        return self.GetAccount().equity

    def AccountFreeMargin(self):
        return self.GetAccount().free_margin

    def SymbolInfo(self, item, symbol=None, default=None):
        if symbol is None:
            symbol = self.default_symbol
        sp = self.tester.get_symbol_properties(symbol)
        return sp.get(item, default)

    def OrderStats(self, order_uids):
        """"""
        ret = {}
        ret['count'] = len(order_uids)
        ret['volume'] = 0
        ret['profit'] = 0
        ret['open_highest'] = 0
        ret['open_lowest'] = 99999999
        #nHoldCount, nTotalVolume, nTotalProfit, nHightest, nLowest
        for oid in order_uids:
            order = self.GetOrder(oid)
            if order is None:
                continue
            ret['volume'] += order.volume
            ret['profit'] += order.profit
            if order.open_price > ret['open_highest']:
                ret['open_highest'] = order.open_price
            if order.open_price < ret['open_lowest']:
                ret['open_lowest'] = order.open_price
        return ret

    def Plot(self, series):
        self.tester.plot('default', series)

    def GetParam(self, name, default=None):
        '''Get params'''
        return self.get_param(name, default)

    def GetOrder(self, order_uid: str):
        return Order(self.tester.get_order(order_uid=order_uid))

    def Close(self, shift=0) -> float:
        return self.tester.Close(shift=shift)

    def Open(self, shift=0) -> float:
        return self.tester.Open(shift=shift)

    def High(self, shift=0) -> float:
        return self.tester.High(shift=shift)

    def Low(self, shift=0) -> float:
        return self.tester.Low(shift=shift)

    def Ask(self, shift=0) -> float:
        return self.tester.Ask(shift=shift)

    def Bid(self, shift=0) -> float:
        return self.tester.Bid(shift=shift)

    def Time(self, shift=0) -> datetime:
        return self.tester.Time(shift=shift)

    def Volume(self, shift=0) -> float:
        return self.tester.Volume(shift=shift)

    def Symbol(self, shift=0) -> str:
        return self.tester.symbol

    def GetOpenedOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA):
        ret = self.tester.get_order_dict(symbol, status="opened", scope=scope)
        return list(ret.keys())

    def GetPendingOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA):
        ret = self.tester.get_order_dict(symbol, status="pending", scope=scope)
        return list(ret.keys())

    def GetClosedOrderUIDs(self, symbol: str = None, scope: int = OrderScope.EA):
        ret = self.tester.get_order_dict(symbol, status="closed", scope=scope)
        return list(ret.keys())

    def StopTester(self, code: int=0, message: str=None):
        return self.tester.stop_tester(code, message)

    def __calculate_indicator__(self, indicator_id, price_data, *args, **kwargs):
        #indicator_id, price_data, period, ma_type
        if not isinstance(price_data, SymbolPrice) and not isinstance(price_data, SymbolData):
            return None
        if indicator_id == IndicatiorID.MA:
            ret = talib.MA(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.AD:
            #high, low, close, volume
            ret = talib.AD(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                           price_data.volume.__price__)
        elif indicator_id == IndicatiorID.ADX:
            #high, low, close[, timeperiod=?]
            ret = talib.ADX(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                            *args, **kwargs)
        elif indicator_id == IndicatiorID.ATR:
            #(high, low, close[, timeperiod=?]
            ret = talib.ATR(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                            *args, **kwargs)
        elif indicator_id == IndicatiorID.BANDS:
            # real[, timeperiod=?, nbdevup=?, nbdevdn=?, matype=?]
            # nbDevUp
            # Deviation multiplier for upper band. Valid range from TRADER_REAL_MIN to TRADER_REAL_MAX.
            #
            # nbDevDn
            # Deviation multiplier for lower band. Valid range from TRADER_REAL_MIN to TRADER_REAL_MAX.
            upper, middle, lower = talib.BBANDS(price_data.__price__, *args, **kwargs)
            ret = np.array([upper, middle, lower]).T #or: np.transpose(a), a.transpose(
            # ret = []
            # for idx in range(upper.volume):
            #     ret.append((upper[idx], middle[idx], lower[idx]))
        elif indicator_id == IndicatiorID.CCI:
            # high, low, close[, timeperiod=?]
            ret = talib.CCI(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                            *args, **kwargs)
        elif indicator_id == IndicatiorID.CHAIKIN:
            # high, low, close, volume[, fastperiod=?, slowperiod=?]
            ret = talib.ADOSC(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                              price_data.volume.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.DEMA:
            #DEMA(real[, timeperiod=?])
            ret = talib.DEMA(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.MOMENTUM:
            # MOM(real[, timeperiod=?])
            ret = talib.MOM(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.MFI:
            # MFI(high, low, close, volume[, timeperiod=?])
            ret = talib.MFI(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                              price_data.volume.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.MACD:
            # MACD(real[, fastperiod=?, slowperiod=?, signalperiod=?])
            macd, macdsignal, macdhist = talib.MACD(price_data.__price__, *args, **kwargs)
            ret = np.array([macd, macdsignal, macdhist]).T #or: np.transpose(a), a.transpose(
        elif indicator_id == IndicatiorID.OBV:
            #  OBV(real, volume)
            ret = talib.OBV(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.SAR:
            # SAR(high, low[, acceleration=?, maximum=?])
            ret = talib.SAR(price_data.high.__price__, price_data.low.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.RSI:
            # RSI(real[, timeperiod=?])
            ret = talib.RSI(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.STDDEV:
            # STDDEV(real[, timeperiod=?, nbdev=?])
            ret = talib.STDDEV(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.STOCHASTIC:
            #  STOCH(high, low, close[, fastk_period=?, slowk_period=?, slowk_matype=?, slowd_period=?, slowd_matype=?])
            slowk, slowd = talib.STOCH(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                              *args, **kwargs)
            ret = np.array([slowk, slowd]).T #or: np.transpose(a), a.transpose(
        elif indicator_id == IndicatiorID.TEMA:
            # TEMA(real[, timeperiod=?])
            ret = talib.TEMA(price_data.__price__, *args, **kwargs)
        elif indicator_id == IndicatiorID.WPR:
            #  WILLR(high, low, close[, timeperiod=?])
            ret = talib.WILLR(price_data.high.__price__, price_data.low.__price__, price_data.close.__price__,
                              *args, **kwargs)
        else:
            return None

        return ret

    def __get_indicator__(self, cache_name, shift, indicator_id, price_data, *args, **kwargs):
        ret = price_data.indicators.get(cache_name, None)
        if ret is None:
            #data, ts_index, timeframe, getitem_callback
            ret = SymbolIndicator(self.__calculate_indicator__(indicator_id, price_data, *args, **kwargs),
                                  price_data.ts_index,
                                  price_data.timeframe,
                                  getitem_callback=price_data.__getitem_callback__)
            price_data.indicators[cache_name] = ret
        if ret is not None and shift is not None:
            return ret[shift]
        return ret

    def iMA(self, price_data, timeperiod, matype, shift=0):
        return self.__get_indicator__(f"ma:{matype}:{timeperiod}", shift, IndicatiorID.MA, price_data, timeperiod, matype)

    def iAD(self, symbol_data, shift=0):
        return self.__get_indicator__(f"ad:", shift, IndicatiorID.AD, symbol_data)

    def iADX(self, symbol_data, timeperiod, shift=0):
        '''
        Average Directional Movement Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"adx:", shift, IndicatiorID.ADX, symbol_data, timeperiod)

    def iATR(self, symbol_data, timeperiod, shift=0):
        '''
        Average True Range
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"atr:", shift, IndicatiorID.ATR, symbol_data, timeperiod)


    def iBands(self, symbol_data, timeperiod, nbdevup, nbdevdn, matype, shift=0):
        '''
        Bollinger Bands®
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"bands:", shift, IndicatiorID.BANDS, symbol_data, timeperiod, nbdevup,
                                      nbdevdn, matype)


    def iCCI(self, symbol_data, timeperiod, shift=0):
        '''
        Commodity Channel Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"cci:", shift, IndicatiorID.CCI, symbol_data, timeperiod)


    def iChaikin(self, symbol_data, fastperiod, slowperiod, shift=0):
        '''
        Chaikin Oscillator/ ADOSC                Chaikin A/D Oscillator
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"chaikin:", shift, IndicatiorID.CHAIKIN, symbol_data, fastperiod, slowperiod)


    def iDEMA(self, symbol_data, timeperiod, shift=0):
        '''
        Double Exponential Moving Average
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"dema:", shift, IndicatiorID.DEMA, symbol_data, timeperiod)


    def iMomentum(self, symbol_data, timeperiod, shift=0):
        '''
        Momentum / MOM                  Momentum
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"momentum:", shift, IndicatiorID.MOMENTUM, symbol_data, timeperiod)


    def iMFI(self, symbol_data, timeperiod, shift=0):
        '''
        Money Flow Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"mfi:", shift, IndicatiorID.MFI, symbol_data, timeperiod)


    def iMACD(self, symbol_data, fastperiod, slowperiod, signalperiod, shift=0):
        '''
        Moving Averages Convergence-Divergence
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"macd:", shift, IndicatiorID.MACD, symbol_data, fastperiod, slowperiod,
                                      signalperiod)


    def iOBV(self, symbol_data, shift=0):
        '''
        On Balance Volume
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"obv:", shift, IndicatiorID.OBV, symbol_data,
                                      symbol_data.__symbol_data__.volume.__price__)

    def iSAR(self, symbol_data, acceleration, maximum, shift=0):
        '''
        Parabolic Stop And Reverse System
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"sar:", shift, IndicatiorID.SAR, symbol_data, acceleration, maximum)


    def iRSI(self, symbol_data, timeperiod, shift=0):
        '''
        Relative Strength Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"rsi:", shift, IndicatiorID.RSI, symbol_data, timeperiod)

    def iStdDev(self, symbol_data, timeperiod, nbdev, shift=0):
        '''
        Standard Deviation
        Parameters
            symbol_data:
        '''
        return self.__get_indicator__(f"stddev:", shift, IndicatiorID.STDDEV, symbol_data, timeperiod, nbdev)

    def iStochastic(self, symbol_data, fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype, shift=0):
        '''
        Stochastic Oscillator
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"stochastic:", shift, IndicatiorID.STOCHASTIC, symbol_data,
                                      fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype)

    def iTEMA(self, symbol_data, timeperiod, shift=0):
        '''
        Triple Exponential Moving Average
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"tema:", shift, IndicatiorID.TEMA, symbol_data, timeperiod)

    def iWPR(self, symbol_data, timeperiod, shift=0):
        '''
        Williams' Percent Range
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"wpr:", shift, IndicatiorID.WPR, symbol_data, timeperiod)
