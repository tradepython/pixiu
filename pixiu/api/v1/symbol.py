from datetime import datetime

import numpy as np
import pandas
from pixiu.api.utils import (parse_timeframe, calculate_minute_intervals, timeframe_to_seconds)


class Symbol(object):
    '''Symbol class'''
    def __init__(self, params={}):
        self.__symbol_dict__ = params.copy()

    @property
    def type(self) -> int:
        return int(self.__symbol_dict__["type"])

    @property
    def name(self) -> str:
        return str(self.__symbol_dict__["symbol"])

    @property
    def spread(self) -> int:
        return int(self.__symbol_dict__["spread"])

    @property
    def digits(self) -> int:
        return int(self.__symbol_dict__["digits"])

    @property
    def stop_level(self) -> int:
        return int(self.__symbol_dict__.get("stop_level", 0))

    @property
    def volume_min(self) -> float:
        return float(self.__symbol_dict__["volume_min"])

    @property
    def trade_contract_size(self) -> float:
        return float(self.__symbol_dict__["trade_contract_size"])

    @property
    def point(self) -> float:
        return float(self.__symbol_dict__["point"])

    @property
    def currency_profit(self) -> str:
        return str(self.__symbol_dict__["currency_profit"])

    @property
    def currency_base(self) -> str:
        return str(self.__symbol_dict__["currency_base"])

    @property
    def currency_margin(self) -> str:
        return str(self.__symbol_dict__["currency_margin"])


#---------------------------------------------------------------------------------------------------------------------
# SymbolData
#---------------------------------------------------------------------------------------------------------------------
class SymbolIndicator(object):
    def __init__(self, data, ts_index, timeframe, getitem_callback, getitem_index):
        self.__timeframe__ = timeframe
        self.__timeframe_seconds__ = timeframe_to_seconds(timeframe)
        self.data = data
        self.__ts_index__ = ts_index
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    @property
    def ts_index(self):
        return self.__ts_index__

    @property
    def timeframe(self):
        return self.__timeframe__

    @property
    def timeframe_seconds(self):
        return self.__timeframe_seconds__

    def __getitem__(self, key):
        # return self.__getitem_callback__(self.data, self.__timeframe__, key)
        return self.__getitem_callback__(self.data, self.__ts_index__,
                                       self.__timeframe__,
                                       self.__timeframe_seconds__,
                                       key, fail_value=np.NaN)


class SymbolPrice(object):
    def __init__(self, symbol_data, price, getitem_callback, getitem_index):
        # self.__timeframe__ = timeframe
        # self.__timeframe_seconds__ = timeframe_to_seconds(timeframe)
        self.__price__ = price
        self.__symbol_data__ = symbol_data
        self.indicators = {}
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    @property
    def ts_index(self):
        return self.__symbol_data__.ts_index

    @property
    def timeframe(self):
        return self.__symbol_data__.timeframe

    @property
    def timeframe_seconds(self):
        return self.__symbol_data__.timeframe_seconds

    def __getitem__(self, key):
        ret = self.__getitem_callback__(self.__price__, self.__symbol_data__.ts_index,
                                       self.__symbol_data__.timeframe,
                                       self.__symbol_data__.timeframe_seconds,
                                       key, fail_value=np.NaN)
        return ret

    def __add__(self, other):
        return self.__price__ + other.__price__

    def __sub__(self, other):
        return self.__price__ - other.__price__

    def __mul__(self, other):
        return self.__price__ * other.__price__

    def __truediv__(self, other):
        return self.__price__ / other.__price__

    def __floordiv__(self, other):
        return self.__price__ // other.__price__

    def __mod__(self, other):
        return self.__price__ % other.__price__

    def __pow__(self, other):
        return self.__price__ ** other.__price__

    def __lt__(self, other):
        return self.__price__ < other.__price__

    def __gt__(self, other):
        return self.__price__ > other.__price__

    def __le__(self, other):
        return self.__price__ <= other.__price__

    def __ge__(self, other):
        return self.__price__ >= other.__price__

    def __eq__(self, other):
        return self.__price__ == other.__price__

    def __ne__(self, other):
        return self.__price__ != other.__price__


class SymbolTime(object):
    def __init__(self, symbol_data, price, getitem_callback, getitem_index):
        self.__time__ = price
        self.__symbol_data__ = symbol_data
        self.indicators = {}
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    @property
    def ts_index(self):
        return self.__symbol_data__.ts_index

    @property
    def timeframe(self):
        return self.__symbol_data__.timeframe

    @property
    def timeframe_seconds(self):
        return self.__symbol_data__.timeframe_seconds

    def __getitem__(self, key):
        ts = self.__getitem_callback__(self.__time__, self.__symbol_data__.ts_index,
                                       self.__symbol_data__.timeframe,
                                       self.__symbol_data__.timeframe_seconds,
                                       key, fail_value=None)
        if ts is None:
            return None
        # return datetime.fromtimestamp(ts)

        return datetime.utcfromtimestamp(ts)

class SymbolData(object):
    def __init__(self, data, timeframe, getitem_callback, getitem_index):
        self.__timeframe__ = timeframe
        self.__timeframe_seconds__ = timeframe_to_seconds(timeframe)
        self.__data__ = data
        self.__size__ = data.size
        self.__ts_index__ = data['t']
        self.__time__ = SymbolTime(self, data['t'], getitem_callback=getitem_callback, getitem_index=getitem_index)
        self.__close_price__ = SymbolPrice(self, data['c'], getitem_callback=getitem_callback,
                                           getitem_index=getitem_index)
        self.__open_price__ = SymbolPrice(self, data['o'], getitem_callback=getitem_callback,
                                          getitem_index=getitem_index)
        self.__high_price__ = SymbolPrice(self, data['h'], getitem_callback=getitem_callback,
                                          getitem_index=getitem_index)
        self.__low_price__ = SymbolPrice(self, data['l'], getitem_callback=getitem_callback,
                                         getitem_index=getitem_index)
        self.__ask_price__ = SymbolPrice(self, data['a'], getitem_callback=getitem_callback,
                                         getitem_index=getitem_index)
        self.__bid_price__ = SymbolPrice(self, data['b'], getitem_callback=getitem_callback,
                                         getitem_index=getitem_index)
        self.__volume__ = SymbolPrice(self, data['v'], getitem_callback=getitem_callback,
                                      getitem_index=getitem_index)
        self.indicators = {}
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    def __getitem__(self, key):
        # return self.__getitem_callback__(self.__data__, key)
        return self.__getitem_callback__(self.__data__, self.__data__['t'],
                                       self.timeframe,
                                       self.timeframe_seconds,
                                       key)

    def to_dataframe(self, index=0, size=None):
        if index < 0:
            return None
        if size is None or size > self.__size__:
            size = self.__size__
        offset = self.__getitem_index__(self.__data__['t'],
                                       self.timeframe,
                                       self.timeframe_seconds,
                                       index)
        if offset >= 0:
            idx = offset - size - 1
            a = self.__data__[0 if idx < 0 else idx: offset+1]
        else:
            a = self.__data__[self.__size__ - size : self.__size__ - offset + 1]
        a = a[::-1]
        ret = pandas.DataFrame({'time': a['t'], 'symbol': a['s'],
                                'open': a['o'], 'high': a['h'], 'low': a['l'], 'close': a['c'],
                                'volume': a['v'], 'ask': a['a'], 'bid': a['b']})
        return ret

    @property
    def timeframe(self):
        return self.__timeframe__

    @property
    def ts_index(self):
        return self.__ts_index__

    @property
    def timeframe_seconds(self):
        return self.__timeframe_seconds__

    @property
    def size(self):
        return self.__size__

    @property
    def close(self):
        return self.__close_price__

    @property
    def open(self):
        return self.__open_price__

    @property
    def high(self):
        return self.__high_price__

    @property
    def low(self):
        return self.__low_price__

    @property
    def ask(self):
        return self.__ask_price__

    @property
    def bid(self):
        return self.__bid_price__

    @property
    def time(self):
        return self.__time__

    @property
    def volume(self):
        return self.__volume__