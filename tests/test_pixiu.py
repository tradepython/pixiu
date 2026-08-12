#coding= utf-8



import os
import argparse
import json
import pytz
from datetime import datetime, timedelta
import sys
import tempfile
from types import SimpleNamespace
from unittest import (TestCase, TestLoader, TestSuite, TextTestRunner, skip, skipIf)

from pixiu.api import utc_from_timestamp, OrderCommand
from pixiu.api.v1 import (TimeFrame, SymbolData, DataScope)
from pixiu.main import MainApp
from pixiu.tester import EATester
from pixiu.chart import (LegacyChartAdapter, render_chart_replay_html, render_chart_live_html,
                         render_ea_explain_chart_png)
from pixiu.optimizer import (EAOptimizer, )
import numpy as np
import time
import talib
import pandas as pd
import dateutil
import pyjson5 as json5


debug_some_tests = False
# debug_some_tests = True

data = np.genfromtxt('usdchf_m1_20210315-0415.csv', delimiter=',',
                     dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                            ('l', float), ('v', float), ('a', float), ('b', float), ], skip_header=1)
new_a = np.array(data,
                 dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                        ('l', float), ('v', float), ('a', float), ('b', float), ])
#
# def to_tf_data(src, seconds):
#     temp_data = []
#     for sd in src:
#         s = sd['s']
#         t = int(sd['t'] / seconds) * seconds
#         o = src[src['t'] >= t]['o'][0]
#         h = src[(src['t'] >= t) & (src['t'] <= sd['t']) ]['h'].max()
#         l = src[(src['t'] >= t) & (src['t'] <= sd['t']) ]['l'].min()
#         c = sd['c']
#         a = sd['a']
#         b = sd['b']
#         v = src[(src['t'] >= t) & (src['t'] <= sd['t']) ]['v'].sum()
#         temp_data.append((s, t, o, h, c, l, v, a, b))
#     ret = np.array(temp_data,
#                  dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
#                         ('l', float), ('v', float), ('a', float), ('b', float), ])
#     return ret

def pandas_to_tf_data(src, timeframe):
    # pd_tf_str = {TimeFrame.S1: '1s', TimeFrame.M1: '1T', TimeFrame.M5: '5T', TimeFrame.M15: '15T', TimeFrame.M30: '30T',
    #              TimeFrame.H1: '1H', TimeFrame.H4: '4H', TimeFrame.D1: '1D', TimeFrame.S1: '1s', }
    pd_tf_str = {TimeFrame.S1: '1s', TimeFrame.M1: '1min', TimeFrame.M5: '5min', TimeFrame.M15: '15min', TimeFrame.M30: '30min',
                 TimeFrame.H1: '1h', TimeFrame.H4: '4h', TimeFrame.D1: '1D' }
    tf_str = pd_tf_str.get(timeframe, None)
    if tf_str is None:
        return None
    da = pd.DataFrame(src)
    da['t'] = pd.to_datetime(da['t'], unit='s')
    da.set_index(pd.DatetimeIndex(da["t"]), inplace=True)
    logic = {'s': 'first',
             'o': 'first',
             'h': 'max',
             'c': 'last',
             'l': 'min',
             'v': 'sum',
             'a': 'last',
             'b': 'last'}
    new_da = da.resample(tf_str).apply(logic).dropna()
    new_da = new_da.reset_index()
    new_da['t'] = new_da['t'].values.astype(np.float64) // 10 ** 9
    ret = new_da.to_records(index=False)
    # ret = np.array(temp_data,
    #              dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
    #                     ('l', float), ('v', float), ('a', float), ('b', float), ])
    return ret



#
# df = pd.DataFrame()
# df = pd.read_csv('usdchf_m1_20210315-0415.csv', sep=',')
# pta.sma(df['c'], length=5)


class EATTester(EATester):
    def __init__(self, test_obj, params):
        super(EATTester, self).__init__(params)
        self.test_obj = test_obj


    def init_data(self):
        super(EATTester, self).init_data()
        self.context.safe_globals['t_check'] = self.t_check


    def on_load_ticks(self, *args, **kwargs):
        self.context.tick_info = self.get_data_info(symbol=self.context.symbol, timeframe=self.context.tick_timeframe,
                                            start_time=self.context.start_time,
                                            end_time=self.context.end_time)
        return 0

    def __update_execuate_log__(self, ticket, count=20, force=False):
        if force or time.time() - self.context.update_log_time > 2:  # 1s
            if count is not None:
                eidx = self.context.last_update_print_log_index + count
            else:
                eidx = None
            logs = self.context.print_logs[self.context.last_update_print_log_index:eidx]
            for l in logs:
                print(l)
            self.context.last_update_print_log_index += len(logs)

            #
            self.update_log_time = time.time()

    def on_end_tick(self, *args, **kwargs):
        self.__update_execuate_log__(self.context.ticket, count=20, force=False)
        return 0

    def on_end_execute(self, *args, **kwargs):
        self.__update_execuate_log__(self.context.ticket, None, force=True)
        return 0

    def GetSymbolData(self, symbol=None, timeframe=None):
        if symbol is None:
            symbol = self.context.symbol
        if timeframe is None:
            timeframe = self.context.tick_timeframe
        return self.get_data_info(symbol, timeframe)

    def __convert_db_price_data__(self, dbo_data, t_unit, t_count, desc):
        ''''''
        raw_data = []
        data = []

        for d in dbo_data:
            ask = d.ask if d.ask is not None else 0
            bid = d.bid if d.bid is not None else 0
            np = dict(t=d.time_frame, s=d.symbol, o=d.open_price,
                      h=d.high_price, c=d.close_price, l=d.low_price, v=d.volume,
                      a=ask, b=bid)
            raw_data.append(np)
            #
            np = (d.symbol, d.time_frame.timestamp(), d.open_price, d.high_price, d.close_price, d.low_price, d.volume,
                  ask, bid)
            data.append(np)

        return raw_data, data

    def symbol_datagetitem_index(self, data_index_ts, timeframe, timeframe_seconds, shift):
        t = int(self.context.tick_info[self.context.tick_current_index]['t']/ timeframe_seconds)*timeframe_seconds
        cidx = np.where(data_index_ts == t)[0][0]
        idx = cidx - shift
        return idx

    def symbol_datagetitem_callback(self, data, data_index_ts, timeframe, timeframe_seconds, shift, fail_value):
        idx = self.symbol_datagetitem_index(data_index_ts, timeframe, timeframe_seconds, shift)
        if idx < 0:
            return fail_value
        return data[idx]

    def get_data_info(self, symbol, timeframe=TimeFrame.M1,  start_time=None, end_time=None, last_count=None):
        """"""
        data = None
        if symbol is None:
            symbol = self.context.symbol
        symbol_tf = self.context.symbol_data.get(symbol, None)
        if symbol_tf:
            data = symbol_tf.get(timeframe, None)
        else:
            self.context.symbol_data[symbol] = {}
        if data is None:

            st = dateutil.parser.parse(self.context.start_time)
            et = dateutil.parser.parse(self.context.end_time)
            ary = new_a[(new_a['t'] >= st.timestamp()) & (new_a['t'] < et.timestamp())]
            #
            data = pandas_to_tf_data(ary, timeframe)
            self.context.symbol_data[symbol][timeframe] = data

        return self.context.symbol_data[symbol][timeframe]

    def t_check(self, name, value, *args, **kwargs):
        if name == "Close":
            # self.test_obj.assertEqual(value, self.Close(), msg=f"{name}: {datetime.fromtimestamp(self.current_time())}: error!")
            self.test_obj.assertEqual(value, self.Close(), msg=f"{name}: {datetime.fromtimestamp(self.current_time(), tz=pytz.utc)}: error!")

class CrossCurrencyEATTester(EATester):
    def __init__(self, params, tick_data_by_symbol):
        self.tick_data_by_symbol = tick_data_by_symbol
        super(CrossCurrencyEATTester, self).__init__(params)

    def get_data_info(self, symbol, timeframe=TimeFrame.M1, start_time=None, end_time=None, last_count=None):
        self.context.symbol_data.setdefault(symbol, {})
        data = self.context.symbol_data[symbol].get(timeframe, None)
        if data is None:
            data = self.tick_data_by_symbol[symbol]
            self.context.symbol_data[symbol][timeframe] = data
        return data

    def on_load_ticks(self, *args, **kwargs):
        self.context.tick_info = self.get_data_info(self.context.symbol, self.context.tick_timeframe,
                                                    self.context.start_time, self.context.end_time)
        return 0

class PiXiuTests(TestCase):
    def setUp(self):
        self.test_result = ""
        self.spread_point = 15
        self.symbol = "USDCHF"
            #     values[datetime.fromtimestamp(new_a['t'][idx])][ti['name']] = ti['values'][idx]
        self.balance = 10000.0
        self.account = {'balance': self.balance,
                        'equity': self.balance,
                        'margin': 0,
                        'free_margin': self.balance,
                        'credit': 0.0,
                        'profit': 0.0,
                        'margin_level': 0,
                        #static
                        'leverage': 100,
                        'currency': 'USD',
                        'free_margin_mode': 0,
                        'stop_out_level': 0,
                        'stop_out_mode': 0,
                        'company': 'PIXIU',
                        'name': 'EATester',
                        'number': '000',
                        'server': 'EATester',
                        'trade_mode': 0,
                        'limit_orders': 500,
                        'margin_so_mode': 0,
                        'trade_allowed': True,
                        'trade_expert': 1,
                        'margin_so_call': 1.2,
                        'margin_so_so': 1.0,
                        'commission': 0.0,
                        }
        self.symbol_properties = dict(USDCHF={'symbol': 'USDCHF', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                                     'trade_contract_size': 100000, 'point': 0.00001,
                                     'currency_profit': 'CHF',
                                     'currency_base': 'USD',
                                     'currency_margin': 'USD', })
        self.eat_params = dict(symbol=self.symbol,
             start_time="2021-03-15",
             end_time="2021-04-16",
             tick_max_index=100,
             balance=self.balance,
             leverage=100,
             currency="USD",
             spread_point=self.spread_point,
             symbol_properties=self.symbol_properties,
             global_values=dict(
                 assertEqual=np.testing.assert_equal,
                 assertAlmostEqual=self.assertAlmostEqual,
                 assertNotEqual=self.assertNotEqual,
                 assertIsNone=self.assertIsNone,
                 assertIsNotNone=self.assertIsNotNone,
                 assertTrue=self.assertTrue,
                 assertFalse=self.assertFalse,
                 exec_command=self.exec_command,
                 set_test_result=self.set_test_result,
             )
             )


    def tearDown(self):
        pass

    def exec_command(self):
        return 0

    def get_value_by_time(self, values, time, item_name):
        return values[time][item_name]

    def make_tick_data(self, symbol, prices, start_ts=1615766400):
        rows = []
        for idx, price_info in enumerate(prices):
            if isinstance(price_info, dict):
                close = float(price_info.get('close', price_info.get('c')))
                bid = float(price_info.get('bid', price_info.get('b', close)))
                ask = float(price_info.get('ask', price_info.get('a', bid)))
            else:
                close = float(price_info)
                bid = close
                ask = close
            rows.append((symbol, float(start_ts + idx * 60), close, close, close, close, 1.0, ask, bid))
        return np.array(rows, dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                                    ('l', float), ('v', float), ('a', float), ('b', float)])

    def make_cross_currency_params(self, account_currency, symbol_properties, script='', global_values=None):
        return dict(
            symbol='EURGBP',
            script=script,
            start_time='2021-03-15',
            end_time='2021-03-16',
            tick_max_index=2,
            balance=10000,
            leverage=100,
            currency=account_currency,
            spread_point=2,
            symbol_properties=symbol_properties,
            account=dict(self.account, currency=account_currency),
            currency_conversion_settings=dict(
                mode='dynamic',
                auto_download=False,
                path_policy='direct_then_usd',
                missing_rate='error',
                time_alignment='latest_before_or_at_tick',
                price_mode='bid_ask',
                fallback_enabled=False,
            ),
            global_values={} if global_values is None else global_values,
        )

    def make_cross_currency_tester(self, account_currency, symbol_properties, tick_data_by_symbol):
        params = self.make_cross_currency_params(account_currency, symbol_properties)
        tester = CrossCurrencyEATTester(params, tick_data_by_symbol)
        tester.init_data()
        tester.context.tick_info = tick_data_by_symbol['EURGBP']
        tester.context.tick_current_index = 0
        return tester

    def set_test_result(self, result):
        self.test_result = result

    def bbands_to_tuple_array(self, value):
        ret = []
        upper = value[0]
        middle = value[1]
        lower = value[2]
        for idx in range(upper.size):
            ret.append((upper[idx], middle[idx], lower[idx]))
        return ret

    def macd_to_tuple_array(self, value):
        ret = []
        macd = value[0]
        macdsignal = value[1]
        macdhist = value[2]
        for idx in range(macd.size):
            ret.append((macd[idx], macdsignal[idx], macdhist[idx]))
        return ret

    def stoch_to_tuple_array(self, value):
        ret = []
        slowk = value[0]
        slowd = value[1]
        for idx in range(slowk.size):
            ret.append((slowk[idx], slowd[idx]))
        return ret

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_func_indicators(self):
        """Test EA Tester"""
        #
        timeperiod = 5
        matype = 0
        shift = 0
        test_items = [
            dict(name="ma",
                 values=talib.MA(new_a['c'], timeperiod=timeperiod, matype=matype),
                 statement=f"value=iMA(symbol_data.close, timeperiod={timeperiod}, matype={matype}, shift={shift})",
                 ),
            dict(name="ad",
                 values=talib.AD(new_a['h'], new_a['l'], new_a['c'], new_a['v']),
                 statement=f"value=iAD(symbol_data, shift={shift})",
                 ),
            dict(name="adx",
                 values=talib.ADX(new_a['h'], new_a['l'], new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iADX(symbol_data, timeperiod={timeperiod}, shift={shift})",
                 ),
            dict(name="atr",
                 values=talib.ATR(new_a['h'], new_a['l'], new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iATR(symbol_data, timeperiod={timeperiod}, shift={shift})",
                 ),
            dict(name="bands",
                 values=self.bbands_to_tuple_array(talib.BBANDS(new_a['c'], timeperiod=timeperiod, nbdevup=2, nbdevdn=2, matype=matype)),
                 statement=f"value=iBands(symbol_data.close, timeperiod={timeperiod}, nbdevup=2, nbdevdn=2, matype={matype}, shift={shift})",
                 ),
            dict(name="cci",
                 values=talib.CCI(new_a['h'], new_a['l'], new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iCCI(symbol_data, timeperiod={timeperiod}, shift={shift})",
                ),
            dict(name="chaikin",
                 values=talib.ADOSC(new_a['h'], new_a['l'], new_a['c'], new_a['v'], fastperiod=5, slowperiod=10),
                 statement=f"value=iChaikin(symbol_data, fastperiod=5, slowperiod=10, shift={shift})",
                ),
            dict(name="dema",
                 values=talib.DEMA(new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iDEMA(symbol_data.close, timeperiod={timeperiod}, shift={shift})",
                ),
            dict(name="momentum",
                 values=talib.MOM(new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iMomentum(symbol_data.close, timeperiod={timeperiod}, shift={shift})",
                ),
            dict(name="mfi",
                 values=talib.MFI(new_a['h'], new_a['l'], new_a['c'], new_a['v'], timeperiod=timeperiod),
                 statement=f"value=iMFI(symbol_data, timeperiod={timeperiod}, shift={shift})",
                ),
            dict(name="macd",
                 values=self.macd_to_tuple_array(talib.MACD(new_a['c'], fastperiod=5, slowperiod=10, signalperiod=7)),
                 statement=f"value=iMACD(symbol_data.close, fastperiod=5, slowperiod=10, signalperiod=7, shift={shift})",
                 ),
            dict(name="obv",
                 values=talib.OBV(new_a['c'], new_a['v']),
                 statement=f"value=iOBV(symbol_data.close, shift={shift})",
                 ),
            dict(name="sar",
                 values=talib.SAR(new_a['h'], new_a['l'], acceleration=0.02, maximum=0.2),
                 statement=f"value=iSAR(symbol_data, acceleration=0.02, maximum=0.2, shift={shift})",
                 ),
            dict(name="rsi",
                 values=talib.RSI(new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iRSI(symbol_data.close, timeperiod={timeperiod}, shift={shift})",
                 ),
            dict(name="stddev",
                 values=talib.STDDEV(new_a['c'], timeperiod=timeperiod, nbdev=2),
                 statement=f"value=iStdDev(symbol_data.close, timeperiod={timeperiod}, nbdev=2, shift={shift})",
                 ),
            dict(name="stochastic",
                 values=self.stoch_to_tuple_array(talib.STOCH(new_a['h'], new_a['l'], new_a['c'], fastk_period=5, slowk_period=3,
                                    slowk_matype=0, slowd_period=3, slowd_matype=0)),
                 statement=f"value=iStochastic(symbol_data, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0, shift={shift})",
                 ),
            dict(name="tema",
                 values=talib.TEMA(new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iTEMA(symbol_data.close, timeperiod={timeperiod}, shift={shift})",
                 ),
            dict(name="wpr",
                 values=talib.WILLR(new_a['h'], new_a['l'], new_a['c'], timeperiod=timeperiod),
                 statement=f"value=iWPR(symbol_data, timeperiod={timeperiod}, shift={shift})",
                 ),
        ]
        values = {}
        # ma_timeperiod = 5
        # ma_matype = 1
        # ma_values = talib.MA(new_a['c'], timeperiod=ma_timeperiod, matype=ma_matype)
        for idx in range(new_a.size):
            # values[datetime.utcfromtimestamp(new_a['t'][idx])] = {}
            values[utc_from_timestamp(new_a['t'][idx])] = {}
            for ti in test_items:
                # values[datetime.utcfromtimestamp(new_a['t'][idx])][ti['name']] = ti['values'][idx]
                values[utc_from_timestamp(new_a['t'][idx])][ti['name']] = ti['values'][idx]

        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_indicators.py")
        self.eat_params['global_values'].update(dict(valid_symbol=self.symbol,
                                                     valid_values=values, valid_account=self.account,
                                                     valid_symbols=self.symbol_properties,
                                                     get_value_by_time=self.get_value_by_time))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_func_load_lib(self):
        """Test EA Tester"""
        #
        values = {}
        self.eat_params['script_libs'] = []
        for i in range(3):
            lib_path = os.path.abspath(f"scripts/v1/ts_lib{i}.py")
            self.eat_params['script_libs'].append(dict(name=f'test_lib{i}', version='1.0', path=lib_path,
                                                code=open(lib_path).read(), metadata={}))
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_lib_load.py")
        self.eat_params['global_values'].update(dict(valid_shift=0, valid_symbol=self.symbol,
                                                     valid_values=values, valid_account=self.account,
                                                     valid_symbols=self.symbol_properties,
                                                     get_value_by_time=self.get_value_by_time))
        self.eat_params['log_path'] = 'tmp_log.txt'
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_func_base(self):
        """Test EA Tester"""
        # ma_timeperiod = 5
        # ma_matype = 1
        # ma_values = talib.MA(new_a['c'], timeperiod=ma_timeperiod, matype=ma_matype)
        values = {}
        for idx in range(new_a.size):
            a = new_a[idx]
            close = a['c']
            ask = a['a']
            bid = a['b']
            if bid == 0:
                bid = close
            if ask == 0:
                ask = bid + (self.spread_point * self.symbol_properties[self.symbol]['point'])
            values[utc_from_timestamp(new_a['t'][idx])] = dict(open=a['o'], close=close,
                                                                   high=a['h'], low=a['l'],
                                                                   ask=ask, bid=bid,
                                                                   volume=a['v'],
                                                                   # time=datetime.utcfromtimestamp(a['t'])
                                                                   time=utc_from_timestamp(a['t'])
                                                                   )

        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_base.py")
        self.eat_params['global_values'].update(dict(valid_shift=0, valid_symbol=self.symbol,
                                                     valid_values=values, valid_account=self.account,
                                                     valid_symbols=self.symbol_properties,
                                                     get_value_by_time=self.get_value_by_time))
        self.eat_params['log_path'] = 'tmp_log.txt'
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_ea_settings(self):
        """Test EA Tester"""
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_settings.py")
        self.eat_params['global_values'].update(dict(valid_shift=0, valid_symbol=self.symbol,
                                                     valid_values=None, valid_account=self.account,
                                                     valid_symbols=self.symbol_properties,
                                                     get_value_by_time=self.get_value_by_time))
        self.eat_params['log_path'] = 'tmp_log.txt'
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_ea_settings_accessor(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script'] = "\n".join([
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {",
            "        'grid_pips': {'value': 25, 'config': {'type': 'int'}},",
            "        'target_profit': {'value': '0.75%', 'config': {'type': 'str'}},",
            "        'enabled_text': {'value': 'true', 'config': {'type': 'str'}},",
            "    }}",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
            "assertEqual(EA_SETTINGS.grid_pips, 25)",
            "assertEqual(EA_SETTINGS.target_profit, '0.75%')",
            "assertIsNone(EA_SETTINGS.missing_param)",
            "assertEqual(EA_SETTINGS.get('grid_pips', 0, 'int'), 25)",
            "assertEqual(EA_SETTINGS.get('grid_pips', 0, 'float'), 25.0)",
            "assertTrue(EA_SETTINGS.get('enabled_text', False, 'bool'))",
            "assertEqual(EA_SETTINGS.get('missing_param', 'fallback'), 'fallback')",
            "set_test_result('OK')",
            "StopTester()",
        ])
        eatt = EATTester(self, params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_script_settings_override_config(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script_settings'] = {
            'params': {
                'grid_pips': 8,
                'orders_queue_timeout_seconds': {'value': 3},
                'risk_min_spread_multiplier': 1.25,
            }
        }
        params['script'] = "\n".join([
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {",
            "        'grid_pips': {'value': 25, 'config': {'type': 'int'}},",
            "        'orders_queue_timeout_seconds': {'value': 60, 'config': {'type': 'int'}},",
            "    }}",
            "AddParam('risk_min_spread_multiplier', value=3.0, type='float')",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': script_settings['params']['grid_pips']['value'] == 8, 'errmsg': 'grid_pips'}",
            "assertEqual(GetParam('grid_pips'), 8)",
            "assertEqual(GetParam('orders_queue_timeout_seconds'), 3)",
            "assertEqual(GetParam('risk_min_spread_multiplier'), 1.25)",
            "assertEqual(EA_SETTINGS.grid_pips, 8)",
            "set_test_result('OK')",
            "StopTester()",
        ])
        eatt = EATTester(self, params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_script_settings_optimization_metadata(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script'] = "\n".join([
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {}}",
            "AddParam('grid_atr_ratio', value=0.5, type='float', min=0.1, max=2.0, required=True,",
            "         optimizable=True,",
            "         optimization={'type': 'float', 'start': 0.1, 'stop': 1.5, 'step': 0.1},",
            "         desc={'en': 'Grid ATR ratio'})",
            "AddParam('mode_switch', value=False, type='bool', required=False)",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
        ])
        eatt = EATTester(self, params)
        metadata = eatt.parse_script(params['script'])
        script_settings = metadata['script_settings']
        grid_atr_ratio = script_settings['params']['grid_atr_ratio']
        self.assertEqual(grid_atr_ratio['value'], 0.5)
        self.assertEqual(grid_atr_ratio['config']['type'], 'float')
        self.assertTrue(grid_atr_ratio['config']['optimizable'])
        self.assertEqual(grid_atr_ratio['config']['optimization']['type'], 'float')
        self.assertEqual(grid_atr_ratio['config']['optimization']['start'], 0.1)
        self.assertEqual(grid_atr_ratio['config']['optimization']['stop'], 1.5)
        self.assertEqual(grid_atr_ratio['config']['optimization']['step'], 0.1)
        self.assertEqual(grid_atr_ratio['config']['desc']['en'], 'Grid ATR ratio')
        self.assertFalse(script_settings['params']['mode_switch']['config'].get('optimizable', False))

    @skipIf(debug_some_tests, "debug some tests")
    def test_legacy_chart_adapter_builds_chart_protocol_replay(self):
        adapter = LegacyChartAdapter(
            script_settings={
                "charts": {
                    "price": {
                        "series": [
                            {"name": "top_signal", "color": "#89F3DAFF"},
                            {"name": "bottom_signal", "color": "#e7dc48"},
                        ]
                    }
                }
            },
            charts_data=[
                {
                    "cn": "price",
                    "time": "2021-03-15 00:00:00",
                    "data": {
                        "top_signal": 0.9321,
                        "bottom_signal": {"value": 0.9310},
                    },
                }
            ],
            graph_data={
                "symbol": self.symbol,
                "ticks": [
                    {
                        "t": 1615766400,
                        "o": 0.9300,
                        "h": 0.9330,
                        "l": 0.9290,
                        "c": 0.9320,
                        "v": 10,
                        "equity": 10010,
                        "balance": 10000,
                        "margin": 100,
                        "orders": [
                            {
                                "uid": "1",
                                "ticket": "1",
                                "type": "BUY",
                                "volume": 0.1,
                                "price": 0.9320,
                                "comment": "open",
                            }
                        ],
                    }
                ],
            },
            print_logs=["hello chart"],
            report={"balance": {"value": 10000}},
            symbols=self.symbol_properties,
            default_symbol=self.symbol,
            timeframe=TimeFrame.M1,
            account=self.account,
            explain_events=[
                {
                    "event_type": "decision_no_action",
                    "reason_code": "condition_blocked",
                    "summary": "Signal was not strong enough.",
                    "time_ts": 1615766400,
                    "symbol": self.symbol,
                    "data": {"score": 68},
                }
            ],
        )

        replay = adapter.build()

        self.assertEqual(replay["version"], "pixiu-chart-v1")
        self.assertEqual(replay["mode"], "replay")
        self.assertEqual(replay["panes"][0]["id"], "price")
        self.assertEqual(replay["frames"][0]["symbol"], self.symbol)
        self.assertEqual(replay["frames"][0]["timeframe"], TimeFrame.M1)
        self.assertEqual(replay["account"][0]["equity"], 10010)
        self.assertEqual(replay["orders"][0]["event"], "OPEN")
        self.assertEqual(replay["orders"][0]["side"], "BUY")
        self.assertEqual(replay["logs"][0]["message"], "hello chart")
        self.assertEqual(replay["reports"]["summary"]["balance"], 10000)
        self.assertEqual(replay["symbols"][self.symbol]["base_currency"], "USD")
        self.assertEqual(replay["symbols"][self.symbol]["profit_currency"], "CHF")
        self.assertEqual(replay["events"][0]["type"], "ea_explain")
        self.assertEqual(replay["events"][0]["name"], "decision_no_action")
        self.assertEqual(replay["events"][0]["reason_code"], "condition_blocked")
        self.assertEqual(replay["events"][0]["payload"]["data"]["score"], 68)

        series = {item["id"]: item for item in replay["series"]}
        self.assertEqual(series["price.top_signal"]["color"], "#89F3DAFF")
        self.assertEqual(series["price.top_signal"]["data"][0]["value"], 0.9321)
        self.assertEqual(series["price.bottom_signal"]["data"][0]["value"], 0.9310)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_build_chart_replay_uses_legacy_chart_settings(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script'] = "\n".join([
            "AddChart(name='price', chart={'series': [{'name': 'top_signal', 'color': '#89F3DAFF'}]})",
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {}}",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
        ])
        eatt = EATTester(self, params)
        eatt.context.charts_data.append({
            "cn": "price",
            "time": 1615766400,
            "data": {"top_signal": 0.9321},
        })

        replay = eatt.build_chart_replay(graph_data={
            "symbol": self.symbol,
            "ticks": [
                {
                    "t": 1615766400,
                    "o": 0.9300,
                    "h": 0.9330,
                    "l": 0.9290,
                    "c": 0.9320,
                    "v": 10,
                    "equity": 10010,
                    "balance": 10000,
                    "margin": 100,
                    "orders": [],
                }
            ],
        })

        self.assertEqual(replay["version"], "pixiu-chart-v1")
        self.assertEqual(replay["panes"][0]["id"], "price")
        self.assertEqual(replay["frames"][0]["close"], 0.9320)
        self.assertEqual(replay["series"][0]["name"], "top_signal")
        self.assertEqual(replay["series"][0]["data"][0]["value"], 0.9321)
        self.assertIsNotNone(replay["metadata"]["pixiu_version"])
        self.assertIn("script_settings", replay["metadata"])
        self.assertIn("charts", replay["metadata"]["script_settings"])

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_explain_api_records_status_events_and_order_state(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script'] = "\n".join([
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {}}",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
        ])
        eatt = EATTester(self, params)
        eatt.context.ticket = "explain-test-run"
        eatt.init_data()

        self.assertTrue(eatt.context.safe_globals["PX_UpdateEAExplainStatus"]({
            "status": "running",
            "phase": "holding",
            "summary": "Waiting for the next signal.",
            "decision_summary": {"last_action": "hold"},
        }))
        self.assertTrue(eatt.context.safe_globals["PX_AppendEAExplainEvent"]({
            "event_type": "decision_open",
            "action": "open_buy",
            "reason_code": "score_passed",
            "summary": "Open conditions passed.",
            "order_uid": "order-1",
            "order_state": {"open_reason_code": "score_passed"},
        }))
        self.assertTrue(eatt.context.safe_globals["PX_AppendEAExplainEvent"]([
            {"event_type": "score_update", "summary": "Score refreshed.", "data": {"score": np.float64(72)}},
            {"event_type": "decision_no_action", "reason_code": "condition_blocked", "summary": "Waiting."},
        ]))
        self.assertFalse(eatt.context.safe_globals["PX_AppendEAExplainEvent"]({"summary": "missing event type"}))

        status = eatt.context.ctx["explain_status"]
        self.assertEqual(status["schema"], "pixiu-ea-explain-v1")
        self.assertEqual(status["type"], "status")
        self.assertEqual(status["symbol"], self.symbol)
        self.assertEqual(status["run_id"], "explain-test-run")
        self.assertEqual(status["decision_summary"]["last_action"], "hold")
        self.assertEqual(len(eatt.context.ctx["explain_events"]), 3)
        self.assertEqual(eatt.context.ctx["explain_events"][0]["type"], "event")
        self.assertEqual(eatt.context.ctx["explain_events"][1]["data"]["score"], 72)
        self.assertEqual(eatt.context.ctx["explain_order_states"]["order-1"]["type"], "order_state")
        self.assertEqual(eatt.context.ctx["explain_order_states"]["order-1"]["open_reason_code"], "score_passed")

        replay = eatt.build_chart_replay(graph_data={
            "symbol": self.symbol,
            "ticks": [
                {
                    "t": 1615766400,
                    "o": 0.9300,
                    "h": 0.9330,
                    "l": 0.9290,
                    "c": 0.9320,
                    "v": 10,
                    "orders": [],
                }
            ],
        })
        self.assertEqual(len(replay["events"]), 3)
        self.assertEqual(replay["events"][0]["order_uid"], "order-1")
        self.assertEqual(replay["events"][0]["payload"]["order_state"]["open_reason_code"], "score_passed")

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = eatt.save_ea_explain_files(tmp_dir)
            with open(paths["status"], "r", encoding="utf-8") as file_obj:
                status_data = json.load(file_obj)
            with open(paths["events"], "r", encoding="utf-8") as file_obj:
                event_lines = [json.loads(line) for line in file_obj if line.strip()]
            with open(paths["orders"], "r", encoding="utf-8") as file_obj:
                order_data = json.load(file_obj)
            self.assertEqual(status_data["type"], "status")
            self.assertEqual(len(event_lines), 3)
            self.assertEqual(order_data["order-1"]["open_reason_code"], "score_passed")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_explain_api_can_be_disabled_for_fast_tests(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['explain_enabled'] = False
        params['script_path'] = None
        params['script'] = "\n".join([
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {}}",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
        ])
        eatt = EATTester(self, params)
        eatt.context.ticket = "explain-disabled-test-run"
        eatt.init_data()

        self.assertTrue(eatt.context.safe_globals["PX_UpdateEAExplainStatus"]({"status": "running"}))
        self.assertTrue(eatt.context.safe_globals["PX_AppendEAExplainEvent"]({"summary": "ignored invalid event"}))
        self.assertIsNone(eatt.context.ctx["explain_status"])
        self.assertEqual(eatt.context.ctx["explain_events"], [])
        self.assertEqual(eatt.context.ctx["explain_order_states"], {})
        self.assertEqual(eatt.context.ctx["explain_warnings"], [])

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_explain_chart_api_returns_on_demand_chart(self):
        """Test optional EA-exported explain chart API"""
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['tick_max_index'] = 1
        params['script_path'] = os.path.abspath("scripts/v1/ts_explain_chart.py")
        eatt = EATTester(self, params)
        eatt.execute("explain-chart-test-run", sync=True)

        chart_types = eatt.get_ea_explain_chart_types()
        self.assertTrue(chart_types["success"])
        self.assertEqual(chart_types["schema"], "pixiu-ea-explain-chart-types-v1")
        self.assertEqual(chart_types["chart_types"][0]["type"], "open_context")
        self.assertEqual(chart_types["chart_types"][0]["symbols"], [self.symbol])

        chart = eatt.get_ea_explain_chart({
            "chart_type": "open_context",
            "params": {"include_orders": True},
        })
        self.assertTrue(chart["success"])
        self.assertEqual(chart["schema"], "pixiu-explain-chart-v1")
        self.assertEqual(chart["chart_type"], "open_context")
        self.assertEqual(chart["symbol"], self.symbol)
        self.assertEqual(chart["run_id"], "explain-chart-test-run")
        self.assertEqual(chart["objects"][0]["type"], "horizontal_line")
        self.assertEqual(chart["metrics"]["stage"], 5)
        self.assertEqual(chart["payload"]["request"]["chart_type"], "open_context")

        unsupported_chart = eatt.get_ea_explain_chart({"chart_type": "unknown"})
        self.assertFalse(unsupported_chart["success"])
        self.assertEqual(unsupported_chart["error"], "unsupported_chart_type")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_explain_chart_api_unsupported_when_ea_does_not_export(self):
        """Test explain chart API is optional for EAs"""
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['tick_max_index'] = 1
        params['script_path'] = None
        params['script'] = "pass"
        eatt = EATTester(self, params)
        eatt.execute("explain-chart-unsupported-run", sync=True)

        chart_types = eatt.get_ea_explain_chart_types()
        self.assertFalse(chart_types["success"])
        self.assertEqual(chart_types["error"], "unsupported")
        self.assertEqual(chart_types["chart_types"], [])

        chart = eatt.get_ea_explain_chart({"chart_type": "open_context"})
        self.assertFalse(chart["success"])
        self.assertEqual(chart["error"], "unsupported")
        self.assertEqual(chart["symbol"], self.symbol)

    @skipIf(debug_some_tests, "debug some tests")
    def test_render_ea_explain_chart_png_writes_standalone_png(self):
        """Test rendering a single on-demand explain chart payload to PNG"""
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow is not installed")
        chart = {
            "success": True,
            "schema": "pixiu-explain-chart-v1",
            "chart_type": "open_context",
            "symbol": self.symbol,
            "time": "2021-03-15 00:01:00",
            "title": "Open Context",
            "price": 0.9302,
            "frames": [
                {"time": "2021-03-15 00:00:00", "open": 0.9298, "high": 0.9304, "low": 0.9295, "close": 0.9302},
                {"time": "2021-03-15 00:01:00", "open": 0.9302, "high": 0.9305, "low": 0.9299, "close": 0.9300},
                {"time": "2021-03-15 00:02:00", "open": 0.9300, "high": 0.9308, "low": 0.9298, "close": 0.9306},
            ],
            "series": [
                {"id": "ma_fast", "type": "line", "color": "#0f766e",
                 "data": [{"value": 0.9298}, {"value": 0.9300}, {"value": 0.9302}]},
                {"id": "risk_score", "type": "histogram", "color": "#f97316",
                 "data": [{"time": "2021-03-15 00:00:00", "value": 0.9297},
                          {"time": "2021-03-15 00:01:00", "value": 0.9301}]},
            ],
            "objects": [
                {"id": "support", "type": "price_line", "price": 0.9295, "title": "Support",
                 "color": "#2563eb"},
                {"id": "resistance", "type": "horizontal_line", "price": 0.9310, "label": "Resistance",
                 "line_style": "dashed"},
                {"id": "open_marker", "type": "marker", "time": "2021-03-15 00:01:00",
                 "price": 0.9300, "position": "below_bar", "shape": "arrow_up", "text": "BUY"},
                {"id": "support_zone", "type": "rectangle",
                 "points": [{"time": "2021-03-15 00:00:00", "price": 0.9293},
                            {"time": "2021-03-15 00:02:00", "price": 0.9297}],
                 "style": {"fill_color": "rgba(37, 99, 235, 0.12)", "border_color": "#2563eb"}},
                {"id": "trend", "type": "trend_line",
                 "points": [{"time": "2021-03-15 00:00:00", "price": 0.9298},
                            {"time": "2021-03-15 00:02:00", "price": 0.9306}],
                 "style": {"color": "#7c3aed", "line_width": 1}},
                {"id": "event_time", "type": "vertical_line", "time": "2021-03-15 00:01:00",
                 "text": "Event"},
                {"id": "note", "type": "text", "time": "2021-03-15 00:02:00",
                 "price": 0.9307, "text": "Note"},
            ],
            "metrics": {"stage": 5, "risk_score": 31},
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "explain_chart.png")
            saved_path = render_ea_explain_chart_png(chart, output_path)
            self.assertEqual(saved_path, output_path)
            with open(saved_path, "rb") as file_obj:
                self.assertEqual(file_obj.read(8), b"\x89PNG\r\n\x1a\n")

    @skipIf(debug_some_tests, "debug some tests")
    def test_main_fast_runtime_options_disable_explain_by_default(self):
        fast_args = SimpleNamespace(fast=True, explain="auto", chartreport=None, max_tick=500)
        fast_options = MainApp.build_test_runtime_options(fast_args)
        self.assertEqual(fast_options["profile"], "fast")
        self.assertFalse(fast_options["explain_enabled"])
        self.assertFalse(fast_options["collect_graph_data"])
        self.assertFalse(fast_options["collect_chart_replay"])
        self.assertEqual(fast_options["graph_sample_ticks"], 100)
        self.assertEqual(fast_options["tick_max_index"], 500)

        explain_args = SimpleNamespace(fast=True, explain="on", chartreport="report.html", max_tick=None)
        explain_options = MainApp.build_test_runtime_options(explain_args)
        self.assertTrue(explain_options["explain_enabled"])
        self.assertTrue(explain_options["collect_graph_data"])
        self.assertTrue(explain_options["collect_chart_replay"])

        normal_args = SimpleNamespace(fast=False, explain="auto", chartreport=None, max_tick=None)
        normal_options = MainApp.build_test_runtime_options(normal_args)
        self.assertEqual(normal_options["profile"], "default")
        self.assertTrue(normal_options["explain_enabled"])
        self.assertTrue(normal_options["collect_graph_data"])

    @skipIf(debug_some_tests, "debug some tests")
    def test_px_tester_graph_tick_time_uses_raw_epoch(self):
        from pixiu.pxtester import PXTester

        class GraphMessageCollector(object):
            def __init__(self):
                self.messages = []

            def send_message(self, message):
                self.messages.append(json5.loads(message))

        class GraphTimestampPXTester(PXTester):
            def __init__(self, symbol, tick_data, account):
                self.test_name = "timestamp-test"
                self.context = SimpleNamespace(
                    ticket="timestamp-test",
                    symbol=symbol,
                    tick_info=tick_data,
                    tick_current_index=0,
                    account=account,
                    script_metadata={"name": "Timestamp EA", "version": "1.0"},
                    script_settings={"params": {"grid_pips": {"value": 8}}},
                    ctx={"chart_metadata": {"test_config": {"test_name": "timestamp-test"}}},
                    report={
                        "balance": {"value": account["balance"], "desc": "Balance"},
                    },
                )
                self.graph_data = {"ticks": [], "name": "timestamp-test", "symbol": symbol, "group": "test"}
                self.tick_order_logs = []
                self.tester_graph_server = None
                self.live_report_interval_seconds = 999
                self.live_report_interval_ticks = 2
                self.live_report_last_time = 0
                self.live_report_last_tick_index = None
                self.live_metadata_sent = False

            def __update_execuate_log__(self, *args, **kwargs):
                return None

        tick_ts = 1615766400.0
        tester = GraphTimestampPXTester(
            self.symbol,
            self.make_tick_data(self.symbol, [
                {"close": 0.9320, "ask": 0.9321, "bid": 0.9319},
                {"close": 0.9330, "ask": 0.9331, "bid": 0.9329},
                {"close": 0.9340, "ask": 0.9341, "bid": 0.9339},
            ], start_ts=tick_ts),
            self.account,
        )

        tester.on_end_tick()

        self.assertEqual(tester.graph_data["ticks"][0]["t"], tick_ts)

        graph_server = GraphMessageCollector()
        tester.tester_graph_server = graph_server
        tester.on_end_tick()
        tester.context.tick_current_index = 1
        tester.on_end_tick()
        update_messages = [item for item in graph_server.messages if item.get("cmd") == "update_data"]
        self.assertEqual(update_messages[0]["data"]["metadata"]["test_config"]["test_name"], "timestamp-test")
        self.assertEqual(update_messages[0]["data"]["metadata"]["script_settings"]["params"]["grid_pips"]["value"], 8)
        self.assertNotIn("metadata", update_messages[1]["data"])
        self.assertEqual(update_messages[0]["data"]["report"]["live_balance"]["value"], self.balance)
        self.assertNotIn("report", update_messages[1]["data"])

        tester.context.tick_current_index = 2
        tester.on_end_tick()
        update_messages = [item for item in graph_server.messages if item.get("cmd") == "update_data"]
        self.assertEqual(update_messages[2]["data"]["report"]["live_tick"]["value"], 3)

        tester.__send_graph_report__(force=True)
        report_messages = [item for item in graph_server.messages if item.get("cmd") == "update_report"]
        self.assertEqual(len(report_messages), 1)
        self.assertEqual(report_messages[0]["data"]["report"]["balance"]["value"], self.balance)

    @skipIf(debug_some_tests, "debug some tests")
    def test_chart_live_html_uses_chart_protocol_events(self):
        replay = {
            "version": "pixiu-chart-v1",
            "mode": "live",
            "metadata": {"mode": "tester_live"},
            "symbols": {self.symbol: {"symbol": self.symbol}},
            "panes": [{"id": "price", "title": "Live Price", "type": "price"}],
            "frames": [],
            "orders": [],
            "account": [],
            "logs": [],
            "reports": {"summary": {}},
        }

        html_report = render_chart_live_html(
            replay,
            title="Live Chart",
            event_url="/events",
            snapshot_url="/snapshot",
        )

        self.assertIn("<title>Live Chart</title>", html_report)
        self.assertIn("new EventSource", html_report)
        self.assertIn('"/events"', html_report)
        self.assertIn("function applyLiveDelta", html_report)
        self.assertIn("function applyLiveSnapshot", html_report)
        self.assertIn("replaceArray(rawFrames", html_report)
        self.assertIn("appendLiveItems(orders", html_report)
        self.assertIn("Object.assign(reportItems", html_report)

    @skipIf(debug_some_tests, "debug some tests")
    def test_chart_live_state_converts_update_data_to_protocol_snapshot(self):
        from pixiu.chart.live_server import PixiuChartLiveState

        state = PixiuChartLiveState()
        update = {
            "cmd": "update_data",
            "name": "test-live",
            "symbol": self.symbol,
            "group": "live-group",
            "data": {
                "price": {
                    "t": 1615766400,
                    "o": 0.9300,
                    "h": 0.9330,
                    "l": 0.9290,
                    "c": 0.9320,
                    "v": 10,
                    "equity": 10010,
                    "balance": 10000,
                    "margin": 100,
                    "orders": [
                        {
                            "uid": "1",
                            "type": "BUY",
                            "volume": 0.1,
                            "price": 0.9320,
                        }
                    ],
                },
                "report": {
                    "live_balance": {"value": 10000, "type": "value"},
                    "live_equity": {"value": 10010, "type": "value"},
                },
                "metadata": {
                    "test_config": {
                        "test_name": "live-group",
                        "tick_source": {
                            "channel": "tradepython.com",
                            "api_token": "redacted_value_a",
                            "file_path": "/example/data/ticks.csv",
                        },
                    },
                    "script_settings": {
                        "params": {
                            "grid_pips": {"value": 8},
                            "password": {"value": "redacted_value_b"},
                        },
                    },
                },
            },
        }

        delta = state.append_update_data(update)
        snapshot = state.snapshot()

        self.assertEqual(delta["type"], "append")
        self.assertEqual(snapshot["mode"], "live")
        self.assertEqual(snapshot["frames"][0]["time"], 1615766400)
        self.assertEqual(snapshot["frames"][0]["close"], 0.9320)
        self.assertEqual(snapshot["account"][0]["equity"], 10010)
        self.assertEqual(snapshot["reports"]["summary"]["live_equity"], 10010)
        self.assertEqual(snapshot["orders"][0]["event"], "OPEN")
        self.assertEqual(snapshot["orders"][0]["side"], "BUY")
        self.assertEqual(snapshot["metadata"]["test_name"], "live-group")
        self.assertEqual(snapshot["metadata"]["script_settings"]["params"]["grid_pips"]["value"], 8)
        metadata_json = json.dumps(snapshot["metadata"], ensure_ascii=False)
        self.assertIn("[REDACTED]", metadata_json)
        self.assertIn("<file: ticks.csv>", metadata_json)
        self.assertNotIn("redacted_value_a", metadata_json)
        self.assertNotIn("redacted_value_b", metadata_json)
        self.assertNotIn("/example/data", metadata_json)

    @skipIf(debug_some_tests, "debug some tests")
    def test_chart_live_state_converts_update_report_to_protocol_snapshot(self):
        from pixiu.chart.live_server import PixiuChartLiveState, _json_dumps

        state = PixiuChartLiveState()
        delta = state.append_message({
            "cmd": "update_report",
            "name": "test-live",
            "symbol": self.symbol,
            "group": "live-group",
            "data": {
                "time": 1615766460,
                "message": "-- Result --",
                "report": {
                    "balance": {"value": 10020.5, "type": "value"},
                    "win_rate": {"value": 0.75, "type": "%"},
                },
            },
        })
        snapshot = state.snapshot()

        self.assertEqual(delta["type"], "report")
        self.assertEqual(snapshot["reports"]["summary"]["balance"], 10020.5)
        self.assertEqual(snapshot["reports"]["summary"]["win_rate"], 0.75)
        self.assertEqual(snapshot["reports"]["items"]["balance"]["type"], "value")
        self.assertEqual(snapshot["reports"]["items"]["win_rate"]["type"], "%")
        self.assertNotIn("text", snapshot["reports"])
        self.assertEqual(snapshot["logs"][0]["source"], "report")
        self.assertEqual(snapshot["metadata"]["test_name"], "live-group")

        nan_delta = state.append_message({
            "cmd": "update_report",
            "name": "test-live",
            "symbol": self.symbol,
            "group": "live-group",
            "data": {
                "time": 1615766520,
                "report": {
                    "trade_max_loss": {"value": float("nan"), "type": "value"},
                    "bad_ratio": {"value": float("inf"), "type": "value"},
                },
            },
        })
        event_json = _json_dumps(nan_delta)
        self.assertNotIn("NaN", event_json)
        self.assertNotIn("Infinity", event_json)
        self.assertIsNone(state.snapshot()["reports"]["summary"]["trade_max_loss"])

    @skipIf(debug_some_tests, "debug some tests")
    def test_main_app_parse_graph_url(self):
        from pixiu.main import MainApp

        graph_config = MainApp.parse_graph_url("http://127.0.0.1:8051")

        self.assertEqual(graph_config["url"], "http://127.0.0.1:8051/")
        self.assertEqual(graph_config["host"], "127.0.0.1")
        self.assertEqual(graph_config["port"], 8051)
        self.assertEqual(MainApp.parse_graph_url("127.0.0.1:8052")["url"], "http://127.0.0.1:8052/")
        self.assertEqual(MainApp.parse_graph_url("true")["url"], "http://127.0.0.1:8050/")
        self.assertIsNone(MainApp.parse_graph_url("false"))

    @skipIf(debug_some_tests, "debug some tests")
    def test_chart_replay_browser_report_html(self):
        replay = LegacyChartAdapter(
            script_settings={
                "charts": {"price": {"series": [{"name": "top_signal", "color": "#89F3DAFF"}]}},
                "params": {
                    "grid_pips": {"value": 8},
                    "api_token": {"value": "redacted_value_c"},
                },
            },
            charts_data=[{"cn": "price", "time": 1615766400, "data": {"top_signal": 0.9321}}],
            graph_data={
                "symbol": self.symbol,
                "ticks": [
                    {
                        "t": 1615766400,
                        "o": 0.9300,
                        "h": 0.9330,
                        "l": 0.9290,
                        "c": 0.9320,
                        "v": 10,
                        "equity": 10010,
                        "balance": 10000,
                        "margin": 100,
                        "orders": [],
                    }
                ],
            },
            symbols=self.symbol_properties,
            default_symbol=self.symbol,
            timeframe=TimeFrame.M1,
            account=self.account,
            metadata={
                "test_config": {
                    "test_name": "test-settings",
                    "symbol": self.symbol,
                    "timeframe": TimeFrame.M1,
                    "start_time": "2026-01-02 08:31:00",
                    "end_time": "2026-02-02 18:06:00",
                    "tick_source": {
                        "channel": "tradepython.com",
                        "api_token": "redacted_value_a",
                        "file_path": "/example/data/ticks.csv",
                    },
                    "account": {
                        "currency": "USD",
                        "balance": 10000,
                        "leverage": 100,
                        "server": "redacted_value_d",
                        "password": "redacted_value_b",
                    },
                }
            },
            report={
                "balance": {"value": 10000.123, "desc": "Balance", "type": "value", "precision": 2},
                "win_rate": {"value": 0.75, "desc": "Win Rate", "type": "%", "precision": 2},
                "sortino_ratio": {"value": 1.25, "desc": "Sortino Ratio", "type": "value", "precision": 2},
                "max_drawdown": {"value": -123.45, "desc": "Max Drawdown", "type": "value", "precision": 2},
            },
        ).build()

        html_report = render_chart_replay_html(replay, title="Sample Chart")

        self.assertIn("<title>Sample Chart</title>", html_report)
        self.assertIn('id="pixiu-chart-data"', html_report)
        self.assertIn('"version":"pixiu-chart-v1"', html_report)
        self.assertIn("renderPriceChart", html_report)
        self.assertIn('id="zoom-in"', html_report)
        self.assertIn('id="zoom-out"', html_report)
        self.assertIn('id="window-range"', html_report)
        self.assertIn('id="orders-scope"', html_report)
        self.assertIn('class="card orders-card"', html_report)
        self.assertIn('id="orders-panel"', html_report)
        self.assertIn('<summary>Orders</summary>', html_report)
        self.assertIn('class="report-details" open', html_report)
        self.assertNotIn('id="orders-toggle"', html_report)
        self.assertNotIn("view.ordersCollapsed", html_report)
        self.assertIn('id="orders-page-size"', html_report)
        self.assertIn('value="50"', html_report)
        self.assertIn('id="orders-prev"', html_report)
        self.assertIn('id="orders-next"', html_report)
        self.assertIn('id="show-account"', html_report)
        self.assertIn('checked> Account', html_report)
        self.assertIn('id="timeframe-select"', html_report)
        self.assertIn('tabindex="0" aria-label="Chart area"', html_report)
        self.assertIn('value="tick" selected>tick', html_report)
        self.assertIn('let activeTimeframe = "tick"', html_report)
        self.assertIn('value="h1">1hour', html_report)
        self.assertIn('value="d1">1day', html_report)
        self.assertIn("function aggregateFramesForTimeframe", html_report)
        self.assertIn("function normalizeFrames", html_report)
        self.assertIn("function frameValue", html_report)
        self.assertIn("Math.floor(ts / 60) * 60", html_report)
        self.assertIn("Math.floor(ts / 3600) * 3600", html_report)
        self.assertIn("Math.floor(ts / 86400) * 86400", html_report)
        self.assertIn("function makeXIndexScale", html_report)
        self.assertIn("function panBars", html_report)
        self.assertIn("function clampNumber", html_report)
        self.assertIn("function frameIndexForTime", html_report)
        self.assertIn("function xAxisLabels", html_report)
        self.assertIn("function latestPointByVisibleFrame", html_report)
        self.assertIn("function orderPriceValues", html_report)
        self.assertIn("function orderLabelText", html_report)
        self.assertIn("function orderKey", html_report)
        self.assertIn("function orderTooltipHtml", html_report)
        self.assertIn("function locateOrder", html_report)
        self.assertIn("function bindOrdersInteraction", html_report)
        self.assertIn("function updateOrderTooltipFromEvent", html_report)
        self.assertIn("function renderOrderMarker", html_report)
        self.assertIn('id="order-tooltip"', html_report)
        self.assertIn('class="order-tooltip"', html_report)
        self.assertIn('class="order-marker${focusedClass}"', html_report)
        self.assertIn('class="label-bg"', html_report)
        self.assertIn('data-order-key', html_report)
        self.assertIn('role="button" tabindex="0"', html_report)
        self.assertIn("scrollIntoView", html_report)
        self.assertIn("showOrderTooltip", html_report)
        self.assertIn("hideOrderTooltip", html_report)
        self.assertIn("concat(orderPriceValues(visibleOrderItems))", html_report)
        self.assertIn("const markerY = clampNumber", html_report)
        self.assertIn("order.ticket || order.uid", html_report)
        self.assertIn("window.__pixiuChartDebug", html_report)
        self.assertIn('id="price-crosshair"', html_report)
        self.assertIn('id="account-crosshair"', html_report)
        self.assertIn('id="price-crosshair-value"', html_report)
        self.assertIn('id="account-crosshair-time"', html_report)
        self.assertIn("updateChartCrosshairs", html_report)
        self.assertIn("renderChartCrosshairs", html_report)
        self.assertIn('data-pane="price"', html_report)
        self.assertIn('data-pane="account"', html_report)
        self.assertIn("const maxRenderBars = 1800", html_report)
        self.assertIn("function scheduleRender()", html_report)
        self.assertIn("function displayFrames", html_report)
        self.assertIn("function axisLabels", html_report)
        self.assertIn("function renderReport()", html_report)
        self.assertIn("function renderLogs()", html_report)
        self.assertIn("function renderSettings()", html_report)
        self.assertIn("function hydrateSettingsJson", html_report)
        self.assertIn("function bindSettingsJsonDetails", html_report)
        self.assertIn("requestIdleCallback", html_report)
        self.assertIn("Expand to load formatted settings JSON.", html_report)
        self.assertIn('class="card settings-card"', html_report)
        self.assertIn("Test Config", html_report)
        self.assertIn("EA Script Settings", html_report)
        self.assertIn("[REDACTED]", html_report)
        self.assertIn("<file: ticks.csv>", html_report)
        self.assertIn('"grid_pips"', html_report)
        self.assertNotIn("redacted_value_a", html_report)
        self.assertNotIn("redacted_value_b", html_report)
        self.assertNotIn("redacted_value_c", html_report)
        self.assertNotIn("redacted_value_d", html_report)
        self.assertNotIn("/example/data", html_report)
        self.assertIn("const metricLabel", html_report)
        self.assertIn('replace(/_/g, " ")', html_report)
        self.assertIn('"sortino_ratio":1.25', html_report)
        self.assertIn('"items":{"balance":{"desc":"Balance","type":"value","precision":2}', html_report)
        self.assertIn("const reportItems", html_report)
        self.assertIn("const terminalRound", html_report)
        self.assertIn('itemType === "%"', html_report)
        self.assertIn("item.precision ?? 2", html_report)
        self.assertIn('"max_drawdown":-123.45', html_report)
        self.assertIn("function metricValueClass", html_report)
        self.assertIn("negative-value", html_report)
        self.assertIn('class="${metricValueClass(v).trim()}"', html_report)
        self.assertIn("grid-template-columns: minmax(0, 1fr) max-content", html_report)
        self.assertIn(".order-row > span", html_report)
        self.assertIn("overflow-wrap: anywhere", html_report)
        self.assertIn("max-height: none", html_report)
        self.assertIn("overflow: visible", html_report)
        self.assertNotIn('class="report-text"', html_report)
        self.assertNotIn("const reportText", html_report)
        self.assertIn('class="report-overview"', html_report)
        self.assertIn('class="metric-grid"', html_report)
        self.assertIn('All report metrics', html_report)
        self.assertIn('All logs', html_report)
        self.assertIn("toLocaleString()", html_report)
        self.assertIn('value="all">All orders', html_report)
        self.assertIn("visibleOrders()", html_report)
        self.assertIn('addEventListener("wheel"', html_report)
        self.assertIn('addEventListener("mousedown"', html_report)
        self.assertIn('addEventListener("mousemove"', html_report)
        self.assertIn('addEventListener("keydown"', html_report)
        self.assertIn('event.key === "ArrowLeft"', html_report)
        self.assertIn('event.key === "ArrowUp"', html_report)
        self.assertIn("pagedOrders()", html_report)
        self.assertNotIn('class="card account-card"', html_report)
        self.assertNotIn("orders.slice(-12)", html_report)
        self.assertNotIn("<polygon points=", html_report)
        self.assertNotIn("Object.entries(reports).slice(0, 14)", html_report)
        self.assertNotIn("(replay.logs || []).slice(-30)", html_report)
        self.assertIn("Math.min(...priceValues)", html_report)
        self.assertIn("Math.max(...priceValues)", html_report)
        self.assertIn("const formatMetric", html_report)
        self.assertIn('--number-font: "DIN Alternate"', html_report)
        self.assertIn("font-family: var(--number-font)", html_report)
        self.assertIn("svg text", html_report)
        self.assertIn("font-variant-numeric: tabular-nums", html_report)
        self.assertIn("isPercentMetric", html_report)
        self.assertIn("const integerMetrics", html_report)
        self.assertIn('"live_tick"', html_report)
        self.assertIn('"total_trades"', html_report)
        self.assertIn('"max_consecutive_losses"', html_report)
        self.assertIn("const isTimeMetric", html_report)
        self.assertIn("!Number.isFinite(date.getTime())", html_report)
        self.assertIn('typeof t === "string"', html_report)
        self.assertIn("return t", html_report)
        self.assertIn("return String(t)", html_report)
        self.assertIn("String(Math.round(n))", html_report)
        html_with_nan = render_chart_replay_html({
            "version": "pixiu-chart-v1",
            "reports": {"summary": {"bad": float("nan")}},
        })
        self.assertNotIn("NaN", html_with_nan)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_return_ratio_uses_account_equity_curve(self):
        params = dict(self.eat_params)
        params['script'] = ""
        tester = EATTester(self, params)
        tester.init_data()
        equity_values = [10000.0, 10100.0, 10050.0, 10200.0]
        tester.context.account_logs = [{"equity": value} for value in equity_values]
        tester.context.return_logs.extend([{"equity": 10000.0}, {"equity": 10200.0}])

        ratio = tester.calculate_return_ratio()
        returns = np.array([np.log(equity_values[i] / equity_values[i - 1]) for i in range(1, len(equity_values))])
        expected_sharpe = np.sqrt(len(returns)) * (returns.mean() / returns.std(ddof=0))
        downside = np.minimum(returns, 0.0)
        expected_sortino = np.sqrt(len(returns)) * (returns.mean() / np.sqrt(np.mean(np.square(downside))))

        self.assertAlmostEqual(ratio["sharpe_ratio"], expected_sharpe)
        self.assertAlmostEqual(ratio["sortino_ratio"], expected_sortino)

        tester.context.account_logs = [{"equity": 10500.0}, {"equity": 10200.0}]
        ratio = tester.calculate_return_ratio()
        self.assertGreater(ratio["sharpe_ratio"], 0)
        self.assertGreater(ratio["sortino_ratio"], 0)

        tester.context.report["balance"]["value"] = 10200.0
        tester.context.account["balance"] = 10200.0
        tester.context.account_logs = [{"equity": 10500.0}, {"equity": 9700.0}]
        ratio = tester.calculate_return_ratio()
        self.assertGreater(ratio["sharpe_ratio"], 0)
        self.assertGreater(ratio["sortino_ratio"], 0)

        tester.context.account["profit"] = -500.0
        tester.context.account["margin"] = 100.0
        tester.close_all_orders(price=1.0, comment="stop")
        self.assertEqual(tester.context.account["profit"], 0.0)
        self.assertEqual(tester.context.account["margin"], 0.0)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_save_chart_report_html(self):
        params = dict(self.eat_params)
        params['global_values'] = dict(self.eat_params['global_values'])
        params['script_path'] = None
        params['script'] = "\n".join([
            "AddChart(name='price', chart={'series': [{'name': 'top_signal', 'color': '#89F3DAFF'}]})",
            "def PX_InitScriptSettings():",
            "    return {'charts': {}, 'params': {}}",
            "def PX_ValidScriptSettings(script_settings=None):",
            "    return {'success': True, 'errmsg': ''}",
        ])
        eatt = EATTester(self, params)
        eatt.context.charts_data.append({"cn": "price", "time": 1615766400, "data": {"top_signal": 0.9321}})
        graph_data = {
            "symbol": self.symbol,
            "ticks": [
                {
                    "t": 1615766400,
                    "o": 0.9300,
                    "h": 0.9330,
                    "l": 0.9290,
                    "c": 0.9320,
                    "v": 10,
                    "equity": 10010,
                    "balance": 10000,
                    "margin": 100,
                    "orders": [],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "chart.html")
            saved_path = eatt.save_chart_report_html(output_path, graph_data=graph_data, title="Saved Chart")
            self.assertEqual(saved_path, output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("<title>Saved Chart</title>", content)
            self.assertIn('"frames":[', content)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_account_ea_scope(self):
        shared_persistent_data = {}

        def build_tester(script_name, account_number):
            params = dict(self.eat_params)
            params['global_values'] = dict(self.eat_params['global_values'])
            params['script'] = "\n".join([
                f"###[name]={script_name}",
                "def PX_InitScriptSettings():",
                "    return {'charts': {}, 'params': {}}",
                "def PX_ValidScriptSettings(script_settings=None):",
                "    return {'success': True, 'errmsg': ''}",
            ])
            params['script_path'] = None
            params['persistent_data'] = shared_persistent_data
            params['account'] = dict(self.account, number=account_number)
            return EATTester(self, params)

        writer = build_tester("account-ea-a", "001")
        same_account_same_ea = build_tester("account-ea-a", "001")
        different_account = build_tester("account-ea-a", "002")
        different_ea = build_tester("account-ea-b", "001")

        payload = {"value": "writer-data"}
        self.assertEqual(writer.save_data("shared-key", payload, DataScope.ACCOUNT_EA), 0)
        self.assertEqual(same_account_same_ea.load_data("shared-key", DataScope.ACCOUNT_EA), payload)
        self.assertIsNone(different_account.load_data("shared-key", DataScope.ACCOUNT_EA))
        self.assertIsNone(different_ea.load_data("shared-key", DataScope.ACCOUNT_EA))

        self.assertEqual(different_account.save_data("shared-key", {"value": "account-b"}, DataScope.ACCOUNT_EA), 0)
        self.assertEqual(different_ea.save_data("shared-key", {"value": "ea-b"}, DataScope.ACCOUNT_EA), 0)
        self.assertEqual(writer.load_data("shared-key", DataScope.ACCOUNT_EA), payload)
        self.assertEqual(different_account.load_data("shared-key", DataScope.ACCOUNT_EA), {"value": "account-b"})
        self.assertEqual(different_ea.load_data("shared-key", DataScope.ACCOUNT_EA), {"value": "ea-b"})

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_cross_currency_direct_profit_conversion(self):
        """Test dynamic direct conversion for cross-currency profit and margin"""
        symbols = {
            'EURGBP': {'symbol': 'EURGBP', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'GBP', 'currency_base': 'EUR', 'currency_margin': 'GBP'},
            'GBPUSD': {'symbol': 'GBPUSD', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'USD', 'currency_base': 'GBP', 'currency_margin': 'GBP'},
        }
        ticks = {
            'EURGBP': self.make_tick_data('EURGBP', [{'bid': 0.8500, 'ask': 0.8502, 'close': 0.8500},
                                                     {'bid': 0.8510, 'ask': 0.8512, 'close': 0.8510}]),
            'GBPUSD': self.make_tick_data('GBPUSD', [{'bid': 1.2500, 'ask': 1.2502, 'close': 1.2500},
                                                     {'bid': 1.2500, 'ask': 1.2502, 'close': 1.2500}]),
        }
        tester = self.make_cross_currency_tester('USD', symbols, ticks)
        tester.prepare_currency_conversion_data()
        order_uid = tester.seed_order({'kind': 'market', 'side': 'buy', 'volume': 1, 'open_price': 0.8500})
        order = tester.get_order(order_uid)
        self.assertEqual(order['margin'], 1062.5)

        tester.context.tick_current_index = 1
        profit = tester.__calculate_profit__(100, 0.8510)
        self.assertAlmostEqual(profit, 125.0)
        self.assertAlmostEqual(tester.get_order(order_uid)['profit'], 125.0)
        self.assertAlmostEqual(tester.calc_profit(OrderCommand.BUY, 'EURGBP', 1, 0.8500, 0.8510), 125.0)
        self.assertAlmostEqual(tester.calc_margin(OrderCommand.BUY, 'EURGBP', 1, 0.8500), 1062.5)
        self.assertAlmostEqual(tester.tick_value('EURGBP', OrderCommand.BUY, 0.8500), 1.25)
        self.assertAlmostEqual(tester.pip_value('EURGBP', OrderCommand.BUY, 0.8500), 12.5)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_cross_currency_prefers_direct_pair(self):
        """Test direct cross pair is preferred when available"""
        symbols = {
            'EURGBP': {'symbol': 'EURGBP', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'GBP', 'currency_base': 'EUR', 'currency_margin': 'GBP'},
            'GBPJPY': {'symbol': 'GBPJPY', 'spread': 3, 'digits': 3, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.001,
                       'currency_profit': 'JPY', 'currency_base': 'GBP', 'currency_margin': 'GBP'},
            'GBPUSD': {'symbol': 'GBPUSD', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'USD', 'currency_base': 'GBP', 'currency_margin': 'GBP'},
            'USDJPY': {'symbol': 'USDJPY', 'spread': 3, 'digits': 3, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.001,
                       'currency_profit': 'JPY', 'currency_base': 'USD', 'currency_margin': 'USD'},
        }
        ticks = {
            'EURGBP': self.make_tick_data('EURGBP', [0.8500, 0.8510]),
            'GBPJPY': self.make_tick_data('GBPJPY', [{'bid': 195.0, 'ask': 195.03, 'close': 195.0},
                                                     {'bid': 195.0, 'ask': 195.03, 'close': 195.0}]),
            'GBPUSD': self.make_tick_data('GBPUSD', [1.25, 1.25]),
            'USDJPY': self.make_tick_data('USDJPY', [156.0, 156.0]),
        }
        tester = self.make_cross_currency_tester('JPY', symbols, ticks)
        tester.prepare_currency_conversion_data()
        path = tester.currency_conversion_paths[('GBP', 'JPY')]
        self.assertEqual([leg['symbol'] for leg in path], ['GBPJPY'])
        self.assertAlmostEqual(tester.convert_currency(100, 'GBP', 'JPY', at_time=ticks['EURGBP'][1]['t']), 19500.0)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_cross_currency_uses_usd_bridge_without_direct_pair(self):
        """Test USD bridge is used when direct cross pair is unavailable"""
        symbols = {
            'EURGBP': {'symbol': 'EURGBP', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'GBP', 'currency_base': 'EUR', 'currency_margin': 'GBP'},
            'GBPUSD': {'symbol': 'GBPUSD', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'USD', 'currency_base': 'GBP', 'currency_margin': 'GBP'},
            'USDJPY': {'symbol': 'USDJPY', 'spread': 3, 'digits': 3, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.001,
                       'currency_profit': 'JPY', 'currency_base': 'USD', 'currency_margin': 'USD'},
        }
        ticks = {
            'EURGBP': self.make_tick_data('EURGBP', [0.8500, 0.8510]),
            'GBPUSD': self.make_tick_data('GBPUSD', [{'bid': 1.25, 'ask': 1.2502, 'close': 1.25},
                                                     {'bid': 1.25, 'ask': 1.2502, 'close': 1.25}]),
            'USDJPY': self.make_tick_data('USDJPY', [{'bid': 156.0, 'ask': 156.03, 'close': 156.0},
                                                     {'bid': 156.0, 'ask': 156.03, 'close': 156.0}]),
        }
        tester = self.make_cross_currency_tester('JPY', symbols, ticks)
        tester.prepare_currency_conversion_data()
        path = tester.currency_conversion_paths[('GBP', 'JPY')]
        self.assertEqual([leg['symbol'] for leg in path], ['GBPUSD', 'USDJPY'])
        self.assertAlmostEqual(tester.convert_currency(100, 'GBP', 'JPY', at_time=ticks['EURGBP'][1]['t']), 19500.0)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_cross_currency_calc_api_script(self):
        """Test EA-facing CalcProfit/CalcMargin/TickValue/PipValue API"""
        symbols = {
            'EURGBP': {'symbol': 'EURGBP', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'GBP', 'currency_base': 'EUR', 'currency_margin': 'GBP'},
            'GBPUSD': {'symbol': 'GBPUSD', 'spread': 2, 'digits': 5, 'stop_level': 0, 'volume_min': 0.01,
                       'trade_contract_size': 100000, 'point': 0.00001,
                       'currency_profit': 'USD', 'currency_base': 'GBP', 'currency_margin': 'GBP'},
        }
        ticks = {
            'EURGBP': self.make_tick_data('EURGBP', [{'bid': 0.8500, 'ask': 0.8502, 'close': 0.8500},
                                                     {'bid': 0.8510, 'ask': 0.8512, 'close': 0.8510}]),
            'GBPUSD': self.make_tick_data('GBPUSD', [{'bid': 1.2500, 'ask': 1.2502, 'close': 1.2500},
                                                     {'bid': 1.2500, 'ask': 1.2502, 'close': 1.2500}]),
        }
        script = "\n".join([
            "assertAlmostEqual(CalcProfit(OrderCommand.BUY, 'EURGBP', 1.0, 0.8500, 0.8510), 125.0)",
            "assertAlmostEqual(OrderCalcProfit(OrderCommand.BUY, 'EURGBP', 1.0, 0.8500, 0.8510), 125.0)",
            "assertAlmostEqual(CalcProfit(OrderCommand.SELL, 'EURGBP', 1.0, 0.8510, 0.8500), 125.0)",
            "assertAlmostEqual(CalcMargin(OrderCommand.BUY, 'EURGBP', 1.0, 0.8500), 1062.5)",
            "assertAlmostEqual(OrderCalcMargin(OrderCommand.BUY, 'EURGBP', 1.0, 0.8500), 1062.5)",
            "assertAlmostEqual(TickValue('EURGBP', OrderCommand.BUY, 0.8500), 1.25)",
            "assertAlmostEqual(PipValue('EURGBP', OrderCommand.BUY, 0.8500), 12.5)",
            "set_test_result('OK')",
            "StopTester()",
        ])
        params = self.make_cross_currency_params(
            'USD',
            symbols,
            script=script,
            global_values=dict(assertAlmostEqual=self.assertAlmostEqual, set_test_result=self.set_test_result),
        )
        tester = CrossCurrencyEATTester(params, ticks)
        tester.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    def get_timeframe_value_by_time(self, timeframe, v_time, item_name):
        tfd = self.timeframe_data.get(timeframe, None)
        seconds = tfd['seconds']
        # print(f"{v_time}, {v_time.replace(tzinfo=pytz.utc).timestamp()}")
        # print(f"{datetime.utcfromtimestamp(tfd['data']['t'][0])}, {tfd['data']['t'][0]}")
        # ts = int(v_time.timestamp() / seconds) * seconds
        ts = int(v_time.replace(tzinfo=pytz.utc).timestamp() / seconds) * seconds
        a = tfd['data'][tfd['data']['t'] == ts][0]
        close = a['c']
        ask = a['a']
        bid = a['b']
        # if bid == 0:
        #     bid = close
        # if ask == 0:
        #     ask = bid + (self.spread_point * self.symbol_properties[self.symbol]['point'])
        v = dict(open=a['o'], close=close,
                            high=a['h'], low=a['l'],
                   ask=ask, bid=bid,
                   volume=a['v'],
                   # time=datetime.utcfromtimestamp(a['t'])
                   time=utc_from_timestamp(a['t'])
                   )
        return v[item_name]

    def init_values(self):
        self.values = {}
        self.timeframe_data = {TimeFrame.S1: {'seconds': 1}, TimeFrame.M1: {'seconds': 60}, TimeFrame.M5: {'seconds': 300},
                          TimeFrame.M15: {'seconds': 900}, TimeFrame.M30: {'seconds': 1800},
                          TimeFrame.H1: {'seconds': 3600}, TimeFrame.H4: {'seconds': 14400},
                          TimeFrame.D1: {'seconds': 86400}}
        for tf in self.timeframe_data:
            self.timeframe_data[tf]['data'] = pandas_to_tf_data(new_a, tf)
            self.values[tf] = {}

        for idx in range(new_a.size):
            a = new_a[idx]
            close = a['c']
            ask = a['a']
            bid = a['b']
            # if bid == 0:
            #     bid = close
            # if ask == 0:
            #     ask = bid + (self.spread_point * self.symbol_properties[self.symbol]['point'])
            # self.values[datetime.utcfromtimestamp(new_a['t'][idx])] = dict(open=a['o'], close=close,
            self.values[utc_from_timestamp(new_a['t'][idx])] = dict(open=a['o'], close=close,
                                                                   high=a['h'], low=a['l'],
                                                                   ask=ask, bid=bid,
                                                                   volume=a['v'],
                                                                   # time=datetime.utcfromtimestamp(a['t'])
                                                                   time=utc_from_timestamp(a['t'])
                                                                   )


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_func_symbol_data(self):
        """Test EA Tester"""
        # ma_timeperiod = 5
        # ma_matype = 1
        # ma_values = talib.MA(new_a['c'], timeperiod=ma_timeperiod, matype=ma_matype)
        self.init_values()

        #tick > 1day
        self.eat_params['tick_max_index'] = 1500
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_symbol_data.py")
        self.eat_params['global_values'].update(dict(valid_shift=0, valid_symbol=self.symbol,
                                                     valid_values=self.values, valid_account=self.account,
                                                     valid_symbols=self.symbol_properties,
                                                     get_value_by_time=self.get_value_by_time,
                                                     get_timeframe_value_by_time=self.get_timeframe_value_by_time),
                                                )
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")



    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_order_market(self):
        """Test EA Tester"""
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_order_market.py")
        # self.eat_params['global_values']['valid_buylimit_price'] = buylimit_price
        # self.eat_params['global_values']['valid_buylimit_time'] = buylimit_time
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_order_buylimit(self):
        """Test EA Tester"""
        #
        a = new_a['a'][0]
        for idx in range(new_a.size):
            p = new_a[idx]['a']
            if p < a:
                buylimit_price = p
                # buylimit_time = datetime.utcfromtimestamp(new_a[idx]['t'])
                buylimit_time = utc_from_timestamp(new_a[idx]['t'])
                break
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_order_buylimit.py")
        self.eat_params['global_values']['valid_buylimit_price'] = buylimit_price
        self.eat_params['global_values']['valid_buylimit_time'] = buylimit_time
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_order_buystop(self):
        """Test EA Tester"""
        #
        #
        a = new_a['a'][0]
        for idx in range(new_a.size):
            p = new_a[idx]['a']
            if p > a:
                buystop_price = p
                # buystop_time = datetime.utcfromtimestamp(new_a[idx]['t'])
                buystop_time = utc_from_timestamp(new_a[idx]['t'])
                break
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_order_buystop.py")
        self.eat_params['global_values']['valid_buystop_price'] = buystop_price
        self.eat_params['global_values']['valid_buystop_time'] = buystop_time
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")


    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_order_selllimit(self):
        """Test EA Tester"""
        #
        b = new_a['b'][0]
        for idx in range(new_a.size):
            p = new_a[idx]['b']
            if p > b:
                selllimit_price = p
                # selllimit_time = datetime.utcfromtimestamp(new_a[idx]['t'])
                selllimit_time = utc_from_timestamp(new_a[idx]['t'])
                break
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_order_selllimit.py")
        self.eat_params['global_values']['valid_selllimit_price'] = selllimit_price
        self.eat_params['global_values']['valid_selllimit_time'] = selllimit_time
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_order_sellstop(self):
        """Test EA Tester"""
        b = new_a['b'][0]
        for idx in range(new_a.size):
            p = new_a[idx]['b']
            if p < b:
                sellstop_price = p
                # sellstop_time = datetime.utcfromtimestamp(new_a[idx]['t'])
                sellstop_time = utc_from_timestamp(new_a[idx]['t'])
                break
        #
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_order_sellstop.py")
        self.eat_params['global_values']['valid_sellstop_price'] = sellstop_price
        self.eat_params['global_values']['valid_sellstop_time'] = sellstop_time

        eatt = EATTester(self, self.eat_params)
        # with self.assertRaisesRegex(Exception, "EID_EAT_TEST_STOP"):
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_initial_state(self):
        """Test EA Tester scenario initial state"""
        self.eat_params['tick_max_index'] = 2
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'initial_state': {
                'account_overrides': {
                    'balance': 8000.0,
                    'equity': 8000.0,
                    'free_margin': 8000.0,
                },
                'orders': [
                    {
                        'ticket': 7001,
                        'kind': 'market',
                        'side': 'buy',
                        'volume': 0.2,
                        'open_price': float(new_a[0]['a']),
                        'comment': 'seed long',
                        'count_in_report': False,
                    },
                    {
                        'ticket': 7002,
                        'kind': 'pending',
                        'side': 'sell_stop',
                        'volume': 0.1,
                        'open_price': round(float(new_a[0]['b']) - 20 * self.symbol_properties[self.symbol]['point'], 5),
                        'comment': 'seed pending',
                    }
                ]
            }
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='initial_state',
            valid_initial_time=utc_from_timestamp(new_a[0]['t']),
            valid_initial_balance=8000.0,
            valid_initial_equity=8000.0,
            valid_initial_free_margin=8000.0,
            valid_opened_ticket=7001,
            valid_pending_ticket=7002,
            valid_opened_volume=0.2,
            valid_opened_comment='seed long',
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_initial_state_open_time_string(self):
        """Test EA Tester scenario initial state open_time string"""
        self.eat_params['tick_max_index'] = 2
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        open_time = utc_from_timestamp(new_a[0]['t']).isoformat()
        self.eat_params['scenario'] = {
            'initial_state': {
                'orders': [
                    {
                        'ticket': 7003,
                        'kind': 'market',
                        'side': 'buy',
                        'volume': 0.2,
                        'open_price': float(new_a[0]['a']),
                        'open_time': open_time,
                        'comment': 'seed open_time',
                        'count_in_report': False,
                    }
                ]
            }
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='initial_state_open_time',
            valid_initial_time=utc_from_timestamp(new_a[0]['t']),
            valid_opened_ticket=7003,
            valid_open_time=utc_from_timestamp(new_a[0]['t']),
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_account_ea_runtime_data(self):
        """Test EA Tester scenario initial ACCOUNT_EA runtime data"""
        data_name = "open_info_USDCHF"
        data = {
            "symbol": "USDCHF",
            "status": "running",
            "orders": ["7001", "7002"],
            "stage": 5,
        }
        self.eat_params['tick_max_index'] = 2
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'initial_state': {
                'data': [
                    {
                        'scope': 'ACCOUNT_EA',
                        'name': data_name,
                        'data': data,
                    }
                ]
            }
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='account_ea_runtime_data',
            valid_initial_time=utc_from_timestamp(new_a[0]['t']),
            valid_data_name=data_name,
            valid_data=data,
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_mutate_tick(self):
        """Test EA Tester scenario mutate tick and spread"""
        event_index = 2
        event_time = utc_from_timestamp(new_a[event_index]['t'])
        event_bid = 0.91195
        event_close = 0.91200
        event_low = 0.91000
        event_high = 0.92400
        spread_point = 80
        point = self.symbol_properties[self.symbol]['point']
        event_ask = event_bid + spread_point * point
        self.eat_params['tick_max_index'] = 5
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'events': [
                {
                    'id': 'flash_crash',
                    'phase': 'pre_tick',
                    'at_tick': event_index,
                    'action': 'mutate_tick',
                    'params': {
                        'bid': event_bid,
                        'close': event_close,
                        'low': event_low,
                        'high': event_high,
                    }
                },
                {
                    'id': 'wide_spread',
                    'phase': 'pre_tick',
                    'at_tick': event_index,
                    'action': 'override_spread',
                    'params': {
                        'spread_point': spread_point,
                    }
                }
            ]
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='mutate_tick',
            valid_event_time=event_time,
            valid_event_bid=event_bid,
            valid_event_ask=event_ask,
            valid_event_close=event_close,
            valid_event_low=event_low,
            valid_event_high=event_high,
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_price_path(self):
        """Test EA Tester scenario generated price path"""
        event_index = 3
        event_time = utc_from_timestamp(new_a[event_index]['t'])
        start_bid = 0.92000
        step = -0.00100
        spread_point = 15
        point = self.symbol_properties[self.symbol]['point']
        event_bid = start_bid + step * (event_index - 1)
        event_ask = event_bid + spread_point * point
        event_close = event_bid
        event_low = event_bid - spread_point * point
        event_high = event_ask + spread_point * point
        self.eat_params['tick_max_index'] = 5
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'events': [
                {
                    'id': 'extreme_downtrend',
                    'phase': 'pre_tick',
                    'from_tick': 1,
                    'to_tick': 4,
                    'action': 'price_path',
                    'params': {
                        'start_bid': start_bid,
                        'step': step,
                        'spread_point': spread_point,
                    }
                }
            ]
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='price_path',
            valid_event_time=event_time,
            valid_event_bid=event_bid,
            valid_event_ask=event_ask,
            valid_event_close=event_close,
            valid_event_low=event_low,
            valid_event_high=event_high,
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_place_order(self):
        """Test EA Tester scenario place order event"""
        place_index = 1
        place_time = utc_from_timestamp(new_a[place_index]['t'])
        self.eat_params['tick_max_index'] = 3
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'events': [
                {
                    'id': 'manual_hedge',
                    'phase': 'post_order_processing',
                    'at_tick': place_index,
                    'action': 'place_order',
                    'params': {
                        'ticket': 7011,
                        'kind': 'market',
                        'side': 'sell',
                        'volume': 0.1,
                        'comment': 'scenario hedge',
                        'count_in_report': False,
                        'write_log': False,
                    }
                }
            ]
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='place_order',
            valid_place_time=place_time,
            valid_place_ticket=7011,
            valid_place_comment='scenario hedge',
            valid_place_volume=0.1,
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_scenario_cancel_order(self):
        """Test EA Tester scenario cancel pending order"""
        cancel_index = 1
        cancel_time = utc_from_timestamp(new_a[cancel_index]['t'])
        self.eat_params['tick_max_index'] = 3
        self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_scenario.py")
        self.eat_params['scenario'] = {
            'initial_state': {
                'orders': [
                    {
                        'ticket': 7021,
                        'kind': 'pending',
                        'side': 'buy_limit',
                        'volume': 0.1,
                        'open_price': round(float(new_a[0]['a']) - 20 * self.symbol_properties[self.symbol]['point'], 5),
                        'comment': 'cancel me',
                    }
                ]
            },
            'events': [
                {
                    'id': 'cancel_pending',
                    'phase': 'pre_tick',
                    'at_tick': cancel_index,
                    'action': 'cancel_order',
                    'params': {
                        'ticket': 7021,
                        'comment': 'scenario cancel',
                    }
                }
            ]
        }
        self.eat_params['global_values'].update(dict(
            scenario_case='cancel_order',
            valid_cancel_time=cancel_time,
            valid_cancel_ticket=7021,
        ))
        eatt = EATTester(self, self.eat_params)
        eatt.execute("123456", sync=True)
        self.assertEqual(self.test_result, "OK")

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_market_events_field_visibility(self):
        """Test market event upcoming/latest queries and field visibility"""
        visible_index = 1
        release_index = 3
        visible_before_time = utc_from_timestamp(new_a[visible_index]['t'])
        release_time = utc_from_timestamp(new_a[release_index]['t'])
        event = {
            'id': 'us-nfp-20210315',
            'type': 'economic_calendar',
            'event_time': str(release_time),
            'available_time': str(release_time),
            'title': 'Nonfarm Payrolls',
            'symbols': ['USDCHF'],
            'currencies': ['USD'],
            'countries': ['US'],
            'asset_classes': ['forex'],
            'impact': 'high',
            'field_visibility': {
                'title': str(visible_before_time),
                'impact': str(visible_before_time),
                'forecast': str(visible_before_time),
                'previous': str(visible_before_time),
                'actual': str(release_time),
            },
            'payload': {
                'forecast': '180K',
                'previous': '175K',
                'actual': '220K',
            },
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as fp:
            fp.write(json.dumps(event) + "\n")
            events_path = fp.name
        try:
            self.eat_params['tick_max_index'] = 5
            self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_market_events.py")
            self.eat_params['market_events'] = {
                'enabled': True,
                'sources': [
                    {
                        'id': 'calendar_file',
                        'type': 'economic_calendar',
                        'channel': 'file',
                        'format': 'jsonl',
                        'path': events_path,
                    }
                ],
            }
            self.eat_params['global_values'].update(dict(
                market_event_case='field_visibility',
                visible_before_time=visible_before_time,
                release_time=release_time,
            ))
            eatt = EATTester(self, self.eat_params)
            eatt.execute("123456", sync=True)
            self.assertEqual(self.test_result, "OK")
        finally:
            os.unlink(events_path)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_market_events_instrument_filter(self):
        """Test market event multi-asset instrument and venue filters"""
        event_time = utc_from_timestamp(new_a[0]['t'])
        event = {
            'id': 'aapl-earnings-20210315',
            'type': 'earnings',
            'event_time': str(event_time),
            'available_time': str(event_time),
            'title': 'AAPL Earnings',
            'instrument_ids': ['stock:NASDAQ:AAPL'],
            'symbols': ['AAPL'],
            'venues': ['NASDAQ'],
            'issuer_ids': ['issuer:apple'],
            'sectors': ['technology'],
            'currencies': ['USD'],
            'countries': ['US'],
            'asset_classes': ['stock'],
            'impact': 'high',
            'payload': {
                'fiscal_period': '2021-Q1',
                'eps_actual': '2.24',
            },
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as fp:
            json.dump([event], fp)
            events_path = fp.name
        try:
            self.eat_params['tick_max_index'] = 2
            self.eat_params['script_path'] = os.path.abspath("scripts/v1/ts_market_events.py")
            self.eat_params['market_events'] = {
                'enabled': True,
                'sources': [
                    {
                        'id': 'earnings_file',
                        'type': 'earnings',
                        'channel': 'file',
                        'format': 'json',
                        'path': events_path,
                    }
                ],
            }
            self.eat_params['global_values'].update(dict(
                market_event_case='instrument_filter',
                instrument_event_time=event_time,
            ))
            eatt = EATTester(self, self.eat_params)
            eatt.execute("123456", sync=True)
            self.assertEqual(self.test_result, "OK")
        finally:
            os.unlink(events_path)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_tester_market_events_chart_replay(self):
        """Test market events are exported to chart replay packages"""
        event_time = utc_from_timestamp(new_a[0]['t'])
        event = {
            'id': 'market-message-1',
            'type': 'market_message',
            'event_time': str(event_time),
            'available_time': str(event_time),
            'title': 'Spread warning',
            'symbols': ['USDCHF'],
            'asset_classes': ['forex'],
            'impact': 'medium',
            'payload': {'message_code': 'spread_widening'},
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as fp:
            fp.write(json.dumps(event) + "\n")
            events_path = fp.name
        try:
            self.eat_params['tick_max_index'] = 1
            self.eat_params['script'] = 'pass'
            self.eat_params['script_path'] = None
            self.eat_params['market_events'] = {
                'enabled': True,
                'sources': [
                    {
                        'id': 'message_file',
                        'type': 'market_message',
                        'channel': 'file',
                        'format': 'jsonl',
                        'path': events_path,
                    }
                ],
            }
            eatt = EATTester(self, self.eat_params)
            eatt.execute("123456", sync=True)
            replay = eatt.build_chart_replay()
            self.assertEqual(len(replay['market_events']), 1)
            self.assertEqual(replay['market_events'][0]['id'], 'market-message-1')
            self.assertEqual(replay['market_event_manifest']['sources'][0]['path'], os.path.basename(events_path))
            chart_events = [item for item in replay['events'] if item.get('name') == 'market_message']
            self.assertEqual(len(chart_events), 1)
        finally:
            os.unlink(events_path)

    @skipIf(debug_some_tests, "debug some tests")
    def test_ea_optimizer_config(self):
        """Test EA Optimizer config format"""
        config_file_path = "./optimizer/optim_config_01.json"
        optimizer_params = dict(optimization_config=json5.loads(open(config_file_path).read()),
                                config_file_path=config_file_path)
        ea_optimizer = EAOptimizer(optimizer_params)
        ret, errmsg = ea_optimizer.valid_config()
        self.assertEqual(ret, True, errmsg)
        opt_config = ea_optimizer.parse_config()
        self.assertIsNotNone(opt_config)
        # Checking the generated values
        var_info = optimizer_params['optimization_config']['optimization']['variables']
        variables = opt_config['variables']
        for key in variables:
            var = variables[key]
            for var_name in var_info:
                generated_value = var[var_name]
                var_val = var_info[var_name]
                var_name = var_val.get('name', var_name)
                var_type = var_val['type']
                var_precision = 0
                if var_type == 'float':
                    var_precision = var_val.get('precision', 5)
                    self.assertTrue(abs(float(var_val['stop'])) > abs(generated_value) >= abs(float(var_val['start'])), f"{var_name} value ({generated_value}) should be between {float(var_val['start'])} and {float(var_val['stop'])}")
                elif var_type == 'int':
                    self.assertTrue(abs(int(var_val['stop'])) > abs(generated_value) >= abs(int(var_val['start'])), f"{var_name} value ({generated_value}) should be between {int(var_val['start'])} and {int(var_val['stop'])}")
                elif var_type in ('%', 'percent'):
                    var_precision = var_val.get('precision', 5)
                    gv = ea_optimizer.parse_percent(generated_value)
                    start_value = ea_optimizer.parse_percent(var_val['start'])
                    stop_value = ea_optimizer.parse_percent(var_val['stop'])
                    step_value = ea_optimizer.parse_percent(var_val['step'])
                    self.assertTrue(abs(stop_value) > abs(gv) >= abs(start_value), f"{var_name} value ({generated_value}) should be between {var_val['start']} and {var_val['step']}")


# --------------------------------------------------------------------
def test(test_cases=[]):
    pixiuTests = TestLoader().loadTestsFromTestCase(PiXiuTests)

    #
    test_suites = TestSuite([pixiuTests])
    tmp_ts = TestSuite()
    if len(test_cases) > 0:
        for ts in test_suites:
            for t in ts:
                if t._testMethodName in test_cases:
                    tmp_ts.addTest(t)
        test_suites = tmp_ts
    #
    test_result = TextTestRunner(verbosity=2).run(test_suites)

    return test_result.wasSuccessful()

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--test_cases', nargs='+', default=[], required=False,
                        help='test cases, ex: case1 case2 case3 ... caseN')
    args = parser.parse_args()
    ret = test(test_cases=args.test_cases)
    if ret:
        sys.exit(0)
    else:
        sys.exit(1)
