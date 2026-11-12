

import numpy as np
import pandas
from pixiu.api.utils import (parse_timeframe, calculate_minute_intervals, timeframe_to_seconds, utc_from_timestamp)


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
        self._values = data
        self.__ts_index__ = ts_index
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    @property
    def data(self):
        refresh = getattr(self, '_tester_refresh', None)
        return refresh() if refresh else self._values

    @property
    def ts_index(self):
        if getattr(self, '_tester_refresh', None):
            self.data
        return self.__ts_index__

    @property
    def timeframe(self):
        return self.__timeframe__

    @property
    def timeframe_seconds(self):
        return self.__timeframe_seconds__

    def __getitem__(self, key):
        # return self.__getitem_callback__(self.data, self.__timeframe__, key)
        if not isinstance(key, (int, np.integer)) or key < 0:
            raise ValueError('shift must be a non-negative integer')
        return self.__getitem_callback__(self.data, self.__ts_index__,
                                       self.__timeframe__,
                                       self.__timeframe_seconds__,
                                       key, fail_value=np.nan)


class SymbolPrice(object):
    def __init__(self, symbol_data, price, getitem_callback, getitem_index):
        # self.__timeframe__ = timeframe
        # self.__timeframe_seconds__ = timeframe_to_seconds(timeframe)
        self._price = price
        self.__symbol_data__ = symbol_data
        self.indicators = {}
        self.__getitem_callback__ = getitem_callback
        self.__getitem_index__ = getitem_index

    def _refresh(self):
        self.__symbol_data__._refresh()

    @property
    def __price__(self):
        self._refresh()
        return self._price

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
        if not isinstance(key, (int, np.integer)) or key < 0:
            raise ValueError('shift must be a non-negative integer')
        parent = self.__symbol_data__
        parent._refresh()
        current_index = getattr(parent, '_tester_scalar_index', None)
        if current_index is not None:
            index = current_index - int(key)
            return self._price[index] if 0 <= index < len(self._price) else np.nan
        ret = self.__getitem_callback__(self._price, parent.ts_index,
                                       parent.timeframe,
                                       parent.timeframe_seconds,
                                       key, fail_value=np.nan)
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
        if not isinstance(key, (int, np.integer)) or key < 0:
            raise ValueError('shift must be a non-negative integer')
        self.__symbol_data__._refresh()
        current_index = getattr(self.__symbol_data__, '_tester_scalar_index', None)
        if current_index is not None:
            index = current_index - int(key)
            ts = self.__time__[index] if 0 <= index < len(self.__time__) else None
        else:
            ts = self.__getitem_callback__(self.__time__, self.__symbol_data__.ts_index,
                                           self.__symbol_data__.timeframe,
                                           self.__symbol_data__.timeframe_seconds,
                                           key, fail_value=None)
        if ts is None:
            return None
        # return datetime.utcfromtimestamp(ts)
        return utc_from_timestamp(ts)

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

    def _refresh(self):
        provider = getattr(self, '_tester_refresh', None)
        if provider is None or getattr(self, '_refreshing', False):
            return
        self._refreshing = True
        try:
            fresh = provider()
            if fresh is None:
                return
            self.__data__ = fresh.__data__
            self.__ts_index__ = fresh.__ts_index__
            self.__size__ = fresh.__size__
            self.__time__.__time__ = fresh.__time__.__time__
            if hasattr(fresh, '_tester_scalar_index'):
                self._tester_scalar_index = fresh._tester_scalar_index
            else:
                self.__dict__.pop('_tester_scalar_index', None)
            if hasattr(fresh, '_tester_batch_source'):
                self._tester_batch_source = fresh._tester_batch_source
            else:
                self.__dict__.pop('_tester_batch_source', None)
            if hasattr(fresh, '_tester_shared_revision'):
                self._tester_shared_revision = fresh._tester_shared_revision
            else:
                self.__dict__.pop('_tester_shared_revision', None)
            for field in ('close', 'open', 'high', 'low', 'ask', 'bid', 'volume'):
                old_price = getattr(self, field)
                new_price = getattr(fresh, field)
                old_price._price = new_price._price
                old_price.indicators.clear()
                for attr in ('_tester_batch_source', '_tester_batch_field', '_tester_shared_revision'):
                    if hasattr(new_price, attr):
                        setattr(old_price, attr, getattr(new_price, attr))
                    else:
                        old_price.__dict__.pop(attr, None)
            self.indicators.clear()
        finally:
            self._refreshing = False

    def __getitem__(self, key):
        self._refresh()
        # return self.__getitem_callback__(self.__data__, key)
        if not isinstance(key, (int, np.integer)) or key < 0:
            raise ValueError('shift must be a non-negative integer')
        value = self.__getitem_callback__(self.__data__, self.__data__['t'],
                                       self.timeframe,
                                       self.timeframe_seconds,
                                       key, fail_value=None)
        return value.copy() if value is not None else None

    def to_dataframe(self, index=0, size=None):
        self._refresh()
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
                                'volume': a['v'], 'ask': a['a'], 'bid': a['b']}, copy=True)
        return ret

    @property
    def timeframe(self):
        return self.__timeframe__

    @property
    def ts_index(self):
        self._refresh()
        return self.__ts_index__.copy()

    @property
    def timeframe_seconds(self):
        return self.__timeframe_seconds__

    @property
    def size(self):
        self._refresh()
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
