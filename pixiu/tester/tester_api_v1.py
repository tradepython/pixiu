
from ..base.api_base import (API_V1_Base)
import numpy as np
import talib
import logging
from datetime import datetime
from collections import OrderedDict
from .higher_timeframe import HigherTimeframeCache
from pixiu.api.utils import timeframe_to_seconds
from pixiu.api import RunModeValue
from pixiu.api.v1 import (OrderCommand, OrderType, IndicatiorID, SymbolIndicator, SymbolPrice, SymbolData,
                      Order, Account, Symbol, AccountData, ErrorID, OrderResult, DataScope)
log = logging.getLogger(__name__)


#---------------------------------------------------------------------------------------------------------------------
# TesterAPI_V1
#---------------------------------------------------------------------------------------------------------------------
class TesterAPI_V1(API_V1_Base):
    def __init__(self, tester, data_source, default_symbol):
        super(TesterAPI_V1, self).__init__(data_source, default_symbol)
        self.tester = tester
        self._batch_indicators = OrderedDict()
        self._higher_timeframes = OrderedDict()
        self._shared_indicators = OrderedDict()
        self._scalar_indices = OrderedDict()
        self._use_higher_timeframe_cache = True
        self._use_shared_indicators = True
        self._use_scalar_index_cache = True
        self._scalar_index_lookups = 0
        self._scalar_index_hits = 0
        self._shared_indicator_hits = 0
        self._market_run_revision = 0

    def reset_performance_cache(self):
        self._market_run_revision += 1
        self._batch_indicators.clear()
        self._higher_timeframes.clear()
        self._shared_indicators.clear()
        self._scalar_indices.clear()
        self._scalar_index_lookups = 0
        self._scalar_index_hits = 0
        self._shared_indicator_hits = 0

    def _print_(self, *args, **kwargs):
        """"""
        return self.tester.get_print_factory(*args, **kwargs)
    #
    def Buy(self, volume, type=OrderType.MARKET, price=0, stop_loss=None, take_profit=None, comment=None,
            magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None, tags=None):
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
                                           arrow_color=arrow_color, tags=tags)

    def Sell(self, volume, type=OrderType.MARKET, price=0, stop_loss=None, take_profit=None, comment=None,
             magic_number=None, symbol=None, slippage=None, arrow_color=None, expiration=None, tags=None):
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
                                           arrow_color=arrow_color, tags=tags)

    def ModifyOrder(self, uid, price=None, stop_loss=None, take_profit=None, comment=None,
                     arrow_color=None, expiration=None, tags=None):
        return self.tester.modify_order(uid, price, stop_loss, take_profit,
                              comment=comment, arrow_color=arrow_color, expiration=expiration, tags=tags)

    def UpdateOrderTags(self, uid, tags=None, patch=None, merge=True, remove_keys=None, expected_tag_ver=None):
        return self.tester.update_order_tags(uid, tags=tags, patch=patch, merge=merge,
                                             remove_keys=remove_keys,
                                             expected_tag_ver=expected_tag_ver)

    def SetOrderTags(self, uid, tags):
        return self.tester.set_order_tags(uid, tags)

    #
    def CloseOrder(self, uid, volume: float=None, price=None,  slippage=None, arrow_color=None, tags=None):
        return self.tester.close_order(uid, volume, price, slippage=slippage,
                              arrow_color=arrow_color, tags=tags)

    def CloseMultiOrders(self, orders):
        return self.tester.close_multi_orders(orders)

    def Notify(self, message):
        return self.tester.notify(message)

    def RunMode(self):
        return RunModeValue.TEST

    def WaitCommand(self, uid, timeout=120):
        return self.tester.wait_command(uid, timeout)

    def AcquireLock(self, name, timeout=60):
        return self.tester.acquire_lock(name, timeout)

    def ReleaseLock(self, name):
        return self.tester.release_lock(name)

    def DefaultTimeFrame(self):
        return self.tester.tick_timeframe

    def _get_scalar_index(self, source, symbol, timeframe, seconds, data):
        context = self.tester.context
        key = (id(source), symbol, context.tick_timeframe, timeframe, seconds)
        entry = self._scalar_indices.get(key)
        cursor = context.tick_current_index
        if entry is not None and entry[0] is source and entry[1] == cursor:
            self._scalar_index_hits += 1
        else:
            # Resolve against the visible timestamps, not the full source or an
            # assumed last bar: unaligned timestamps must retain missing values.
            index = int(self.tester.symbol_datagetitem_index(data['t'], timeframe, seconds, 0)) if len(data) else -1
            entry = (source, cursor, index)
            self._scalar_indices[key] = entry
            self._scalar_index_lookups += 1
            if len(self._scalar_indices) > 128:
                self._scalar_indices.popitem(last=False)
        self._scalar_indices.move_to_end(key)
        return entry[2]

    def GetSymbolData(self, symbol: str, timeframe: str, size: int):
        context = self.tester.context
        symbol = context.symbol if symbol is None else symbol
        timeframe = context.tick_timeframe if timeframe is None else timeframe
        primary = symbol == context.symbol
        source = context.tick_info if primary else self.tester.get_data_info(symbol, context.tick_timeframe)
        # The primary cursor disambiguates ticks with identical timestamps. For a
        # foreign feed with no shared sequence, conservatively use earlier quotes.
        end = context.tick_current_index + 1 if primary else int(np.searchsorted(source['t'], self.tester.current_time()))
        visible = source[:end]
        seconds = timeframe_to_seconds(timeframe)
        static_source = primary and not self.tester.scenario_engine.enabled
        aggregation = None
        if static_source:
            source.setflags(write=False)
        if timeframe == context.tick_timeframe:
            data = visible.view()
        elif static_source and self._use_higher_timeframe_cache and seconds > timeframe_to_seconds(context.tick_timeframe):
            key = (id(source), symbol, context.tick_timeframe, timeframe, seconds, 'utc_fixed')
            aggregation = self._higher_timeframes.get(key)
            if aggregation is None:
                aggregation = HigherTimeframeCache(source, seconds)
                self._higher_timeframes[key] = aggregation
                if len(self._higher_timeframes) > 32:
                    self._higher_timeframes.popitem(last=False)
            self._higher_timeframes.move_to_end(key)
            aggregation.advance(end)
            data = aggregation.snapshot()
        else:
            # Aggregate only observations that have actually arrived, including
            # the forming bar. Whole-period resampling leaks future sub-bars.
            labels = np.floor(visible['t'] / seconds) * seconds
            starts = np.flatnonzero(np.r_[True, labels[1:] != labels[:-1]]) if len(visible) else np.array([], dtype=int)
            ends = np.r_[starts[1:] - 1, len(visible) - 1] if len(starts) else starts
            data = visible[starts].copy()
            if len(starts):
                data['t'] = labels[starts]
                data['h'] = np.maximum.reduceat(visible['h'], starts)
                data['l'] = np.minimum.reduceat(visible['l'], starts)
                data['v'] = np.add.reduceat(visible['v'], starts)
                for field in ('c', 'a', 'b'):
                    data[field] = visible[field][ends]
        data.setflags(write=False)
        result = SymbolData(data, timeframe, getitem_callback=self.tester.symbol_datagetitem_callback,
                            getitem_index=self.tester.symbol_datagetitem_index)
        if static_source and self._use_scalar_index_cache:
            result._tester_scalar_index = self._get_scalar_index(source, symbol, timeframe, seconds, data)
        batch_static = static_source and timeframe == context.tick_timeframe
        if static_source:
            # The primary input array cannot change during an ordinary replay.
            # Mark it read-only for every requested timeframe so retained H1/D1
            # views can use the cursor as their revision instead of hashing the
            # growing M1 prefix on every property access.
            source.setflags(write=False)
        if batch_static:
            # Static base-timeframe input can be computed internally in batches
            # for whitelisted causal indicators; the public output stays clipped.
            result._tester_batch_source = source
            for field in ('open', 'high', 'low', 'close', 'ask', 'bid', 'volume'):
                price = getattr(result, field)
                price._tester_batch_source = source
                price._tester_batch_field = dict(open='o', high='h', low='l', close='c', ask='a', bid='b', volume='v')[field]
        if aggregation is not None:
            result._tester_shared_revision = (aggregation, aggregation.revision, None)
            for field in ('open', 'high', 'low', 'close', 'ask', 'bid', 'volume'):
                getattr(result, field)._tester_shared_revision = (aggregation, aggregation.revision, field)
        def cursor_stamp():
            current_source = context.tick_info if primary else self.tester.get_data_info(symbol, context.tick_timeframe)
            policy = (context.tick_timeframe, self.tester.scenario_engine.enabled, self._use_scalar_index_cache)
            if static_source and not policy[1]:
                return (self._market_run_revision, id(current_source), context.tick_current_index, policy)
            return (self._market_run_revision, id(current_source), context.tick_current_index,
                    (current_source[:context.tick_current_index + 1].tobytes() if current_source.flags.writeable else None)
                    if primary else current_source.tobytes(),
                    context.spread_point, policy)
        stamp = cursor_stamp()
        def refresh():
            nonlocal stamp
            current = cursor_stamp()
            if current == stamp:
                return None
            fresh = self.GetSymbolData(symbol, timeframe, size)
            stamp = current
            return fresh
        result._tester_refresh = refresh
        return result

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

    def CalcProfit(self, order_type, symbol, volume, open_price, close_price):
        return self.tester.calc_profit(order_type, symbol, volume, open_price, close_price)

    def OrderCalcProfit(self, order_type, symbol, volume, open_price, close_price):
        return self.CalcProfit(order_type, symbol, volume, open_price, close_price)

    def CalcMargin(self, order_type, symbol, volume, price):
        return self.tester.calc_margin(order_type, symbol, volume, price)

    def OrderCalcMargin(self, order_type, symbol, volume, price):
        return self.CalcMargin(order_type, symbol, volume, price)

    def TickValue(self, symbol=None, order_type=OrderCommand.BUY, price=None):
        return self.tester.tick_value(symbol=symbol, order_type=order_type, price=price)

    def PipValue(self, symbol=None, order_type=OrderCommand.BUY, price=None):
        return self.tester.pip_value(symbol=symbol, order_type=order_type, price=price)

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

    def AddChart(self, name, **kwargs):
        return self.tester.add_chart(name, **kwargs)

    def AddParam(self, name, **kwargs):
        return self.tester.add_param(name, **kwargs)

    def GetParam(self, name, default=None):
        '''Get params'''
        return self.tester.get_param(name, default)


    def GetSettings(self, name, default=None):
        return self.tester.get_settings(name, default)

    def DeleteData(self, name, scope: int = DataScope.EA):
        return self.tester.delete_data(name, scope)

    def LoadData(self, name, scope: int = DataScope.EA, format='json', path=None):
        if path is None:
            return self.tester.load_data(name, scope, format)
        return self.tester.load_data(name, scope, format, path=path)

    def SaveData(self, name, data, scope: int = DataScope.EA, format='json'):
        return self.tester.save_data(name, data, scope, format)

    def GetOrder(self, order_uid: str):
        return Order(self.tester.get_order(order_uid=order_uid))

    def Close(self, shift=0, symbol=None) -> float:
        return self.tester.Close(shift=shift, symbol=symbol)

    def Open(self, shift=0, symbol=None) -> float:
        return self.tester.Open(shift=shift, symbol=symbol)

    def High(self, shift=0, symbol=None) -> float:
        return self.tester.High(shift=shift, symbol=symbol)

    def Low(self, shift=0, symbol=None) -> float:
        return self.tester.Low(shift=shift, symbol=symbol)

    def Ask(self, shift=0, symbol=None) -> float:
        return self.tester.Ask(shift=shift, symbol=symbol)

    def Bid(self, shift=0, symbol=None) -> float:
        return self.tester.Bid(shift=shift, symbol=symbol)

    def Time(self, shift=0, symbol=None) -> datetime:
        return self.tester.Time(shift=shift, symbol=symbol)

    def Volume(self, shift=0, symbol=None) -> float:
        return self.tester.Volume(shift=shift, symbol=symbol)

    def Symbol(self, shift=0) -> str:
        return self.tester.symbol

    def GetOpenedOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA):
        ret = self.tester.get_order_dict(symbol, status="opened", scope=scope)
        return list(ret.keys())

    def GetPendingOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA):
        ret = self.tester.get_order_dict(symbol, status="pending", scope=scope)
        return list(ret.keys())

    def GetClosedOrderUIDs(self, symbol: str = None, scope: int = DataScope.EA):
        ret = self.tester.get_order_dict(symbol, status="closed", scope=scope)
        return list(ret.keys())

    def StopTester(self, code: int=0, message: str=None):
        return self.tester.stop_tester(code, message)

    def PX_UpdateEAExplainStatus(self, data):
        return self.tester.update_ea_explain_status(data)

    def PX_AppendEAExplainEvent(self, data):
        return self.tester.append_ea_explain_event(data)

    def GetMarketEvents(self, instrument_id=None, instrument_ids=None, symbol=None, symbols=None,
                        venue=None, issuer_id=None, sector=None, currency=None, country=None,
                        asset_class=None, event_type=None, min_impact=None, from_time=None,
                        to_time=None, include_future=False, include_hidden_fields=False):
        return self.tester.get_market_events(
            instrument_id=instrument_id,
            instrument_ids=instrument_ids,
            symbol=symbol,
            symbols=symbols,
            venue=venue,
            issuer_id=issuer_id,
            sector=sector,
            currency=currency,
            country=country,
            asset_class=asset_class,
            event_type=event_type,
            min_impact=min_impact,
            from_time=from_time,
            to_time=to_time,
            include_future=include_future,
            include_hidden_fields=include_hidden_fields,
        )

    def GetUpcomingMarketEvents(self, instrument_id=None, symbol=None, venue=None,
                                issuer_id=None, sector=None, currency=None, country=None,
                                asset_class=None, event_type=None, within_seconds=3600,
                                min_impact=None):
        return self.tester.get_upcoming_market_events(
            instrument_id=instrument_id,
            symbol=symbol,
            venue=venue,
            issuer_id=issuer_id,
            sector=sector,
            currency=currency,
            country=country,
            asset_class=asset_class,
            event_type=event_type,
            within_seconds=within_seconds,
            min_impact=min_impact,
        )

    def GetLatestMarketEvents(self, instrument_id=None, symbol=None, venue=None,
                              issuer_id=None, sector=None, currency=None, country=None,
                              asset_class=None, event_type=None, lookback_seconds=3600,
                              min_impact=None):
        return self.tester.get_latest_market_events(
            instrument_id=instrument_id,
            symbol=symbol,
            venue=venue,
            issuer_id=issuer_id,
            sector=sector,
            currency=currency,
            country=country,
            asset_class=asset_class,
            event_type=event_type,
            lookback_seconds=lookback_seconds,
            min_impact=min_impact,
        )

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
        refresh = getattr(price_data, '_refresh', None)
        if refresh:
            refresh()
        ret = price_data.indicators.get(cache_name, None)
        if ret is None:
            source = getattr(price_data, '_tester_batch_source', None)
            causal = indicator_id == IndicatiorID.ATR or (indicator_id == IndicatiorID.MA and args[1] == 0)
            values = None
            shared = getattr(price_data, '_tester_shared_revision', None) if self._use_shared_indicators else None
            if shared is not None:
                aggregation, revision, field = shared
                shared_key = (aggregation, field, indicator_id, cache_name, repr(args), repr(sorted(kwargs.items())))
                entry = self._shared_indicators.get(shared_key)
                if entry is not None and entry[0] == revision:
                    values = entry[1].copy()
                    self._shared_indicators.move_to_end(shared_key)
                    self._shared_indicator_hits += 1
            if source is not None and causal:
                field = getattr(price_data, '_tester_batch_field', None)
                key = (id(source), field, price_data.timeframe, cache_name)
                cached = self._batch_indicators.get(key)
                if cached is None:
                    full = SymbolData(source, price_data.timeframe,
                                      getitem_callback=price_data.__getitem_callback__,
                                      getitem_index=price_data.__getitem_index__)
                    fields = dict(o='open', h='high', l='low', c='close', a='ask', b='bid', v='volume')
                    input_data = getattr(full, fields[field]) if field else full
                    cached = (source, self.__calculate_indicator__(indicator_id, input_data, *args, **kwargs))
                    self._batch_indicators[key] = cached
                    if len(self._batch_indicators) > 128:
                        self._batch_indicators.popitem(last=False)
                self._batch_indicators.move_to_end(key)
                values = cached[1][:len(price_data.ts_index)].copy()
            if values is None:
                values = self.__calculate_indicator__(indicator_id, price_data, *args, **kwargs)
                if shared is not None and values is not None:
                    # Keep only the latest version per logical indicator, not
                    # one full-history array for every M1 cursor ever visited.
                    self._shared_indicators[shared_key] = (revision, values.copy())
                    self._shared_indicators.move_to_end(shared_key)
                    if len(self._shared_indicators) > 128:
                        self._shared_indicators.popitem(last=False)
            #data, ts_index, timeframe, getitem_callback
            ret = SymbolIndicator(values,
                                  price_data.ts_index,
                                  price_data.timeframe,
                                  getitem_callback=price_data.__getitem_callback__,
                                  getitem_index=price_data.__getitem_index__,
                                  )
            price_data.indicators[cache_name] = ret
            def refresh_indicator():
                fresh = self.__get_indicator__(cache_name, None, indicator_id, price_data, *args, **kwargs)
                ret.__ts_index__ = fresh.__ts_index__
                return fresh._values
            ret._tester_refresh = refresh_indicator
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
        return self.__get_indicator__(f"adx:{timeperiod}", shift, IndicatiorID.ADX, symbol_data, timeperiod)

    def iATR(self, symbol_data, timeperiod, shift=0):
        '''
        Average True Range
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"atr:{timeperiod}", shift, IndicatiorID.ATR, symbol_data, timeperiod)


    def iBands(self, symbol_data, timeperiod, nbdevup, nbdevdn, matype, shift=0):
        '''
        Bollinger Bands®
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"bands:{matype}:{timeperiod}:{nbdevup}:{nbdevdn}", shift, IndicatiorID.BANDS, symbol_data, timeperiod, nbdevup,
                                      nbdevdn, matype)


    def iCCI(self, symbol_data, timeperiod, shift=0):
        '''
        Commodity Channel Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"cci:{timeperiod}", shift, IndicatiorID.CCI, symbol_data, timeperiod)


    def iChaikin(self, symbol_data, fastperiod, slowperiod, shift=0):
        '''
        Chaikin Oscillator/ ADOSC                Chaikin A/D Oscillator
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"chaikin:{fastperiod}:{slowperiod}", shift, IndicatiorID.CHAIKIN, symbol_data, fastperiod, slowperiod)


    def iDEMA(self, symbol_data, timeperiod, shift=0):
        '''
        Double Exponential Moving Average
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"dema:{timeperiod}", shift, IndicatiorID.DEMA, symbol_data, timeperiod)


    def iMomentum(self, symbol_data, timeperiod, shift=0):
        '''
        Momentum / MOM                  Momentum
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"momentum:{timeperiod}", shift, IndicatiorID.MOMENTUM, symbol_data, timeperiod)


    def iMFI(self, symbol_data, timeperiod, shift=0):
        '''
        Money Flow Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"mfi:{timeperiod}", shift, IndicatiorID.MFI, symbol_data, timeperiod)


    def iMACD(self, symbol_data, fastperiod, slowperiod, signalperiod, shift=0):
        '''
        Moving Averages Convergence-Divergence
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"macd:{fastperiod}:{slowperiod}:{signalperiod}", shift, IndicatiorID.MACD, symbol_data, fastperiod, slowperiod,
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
        return self.__get_indicator__(f"sar:{acceleration}:{maximum}", shift, IndicatiorID.SAR, symbol_data, acceleration, maximum)


    def iRSI(self, symbol_data, timeperiod, shift=0):
        '''
        Relative Strength Index
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"rsi:{timeperiod}", shift, IndicatiorID.RSI, symbol_data, timeperiod)

    def iStdDev(self, symbol_data, timeperiod, nbdev, shift=0):
        '''
        Standard Deviation
        Parameters
            symbol_data:
        '''
        return self.__get_indicator__(f"stddev:{timeperiod}:{nbdev}", shift, IndicatiorID.STDDEV, symbol_data, timeperiod, nbdev)

    def iStochastic(self, symbol_data, fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype, shift=0):
        '''
        Stochastic Oscillator
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"stochastic:{fastk_period}:{slowk_period}:{slowk_matype}:{slowd_period}:{slowd_matype}", shift, IndicatiorID.STOCHASTIC, symbol_data,
                                      fastk_period, slowk_period, slowk_matype, slowd_period, slowd_matype)

    def iTEMA(self, price_data, timeperiod, shift=0):
        '''
        Triple Exponential Moving Average
        Parameters
            price_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"tema:{timeperiod}", shift, IndicatiorID.TEMA, price_data, timeperiod)

    def iWPR(self, symbol_data, timeperiod, shift=0):
        '''
        Williams' Percent Range
        Parameters
            symbol_data:
        '''
        # real = ADX(high, low, close, timeperiod=14)
        return self.__get_indicator__(f"wpr:{timeperiod}", shift, IndicatiorID.WPR, symbol_data, timeperiod)
