#coding= utf-8



import os
import argparse
import pytz
from datetime import datetime, timedelta
import sys
from unittest import (TestCase, TestLoader, TestSuite, TextTestRunner, skip, skipIf)

from pixiu.api import utc_from_timestamp
from pixiu.api.v1 import (TimeFrame, SymbolData)
from pixiu.tester import (EATester, )
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


