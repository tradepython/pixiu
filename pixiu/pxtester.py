# env
import csv
import json
import pyjson5 as json5
import time
import pytz
import dateutil
import hashlib
import traceback
import numpy as np
import pandas as pd
from datetime import (timedelta, datetime)
from pixiu.api import utc_from_timestamp
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path
import os

#
from pixiu.api import (TimeFrame, )
from pixiu.tester import (EATester, EATesterGraphServer)


class PXTester(EATester):
    def __init__(self, test_config_path, test_name, script_path, log_path=None, print_log_type=None, test_result=None,
                 tester_graph_server=None, test_graph_data=None):
        self.test_name = test_name
        self.test_result = test_result
        self.test_graph_data = test_graph_data
        self.parse_test_config(test_config_path, test_name, script_path, log_path, print_log_type)
        super(PXTester, self).__init__(self.eat_params)
        self.tester_graph_server = tester_graph_server
        self.tick_order_logs = []
        name = f"{self.test_name} ({self.eat_params['script_path']})"
        self.graph_data = dict(ticks=[], name=name, symbol=self.symbol, group=self.test_name)

    def lib_path(self, name, version):
        return f"libs/{name}/{name}_V{version}.py"

    def add_order_log(self, log_dict):
        super(PXTester, self).add_order_log(log_dict)
        self.write_log(f"Order Log: #{log_dict['id']}: {log_dict}", type='order')
        self.tick_order_logs.append(log_dict)

    def add_account_log(self, log_dict):
        super(PXTester, self).add_account_log(log_dict)
        self.write_log(f"Account Log: {log_dict}", type='account')

    def read_test_config(self, test_config_path):
        with open(test_config_path) as f:
            s = f.read()
            return json5.loads(s)

    def config_path_to_abs_path(self, config_file_path, file_path):
        ret = file_path
        if not os.path.isabs(file_path):
            dir = os.path.dirname(config_file_path)
            ret = os.path.abspath(os.path.join(dir, file_path))
        return ret

    def parse_test_config(self, test_config_path, test_name, script_path, log_path=None, print_log_type=None):
        test_config = self.read_test_config(test_config_path)
        test_params = test_config['tests'][test_name]
        symbol = test_params['symbol']
        account = test_params['account']
        if not isinstance(account, dict):
            account = test_config['accounts'][account]
        #custom account
        for k in account:
            if k in test_params:
                account[k] = test_params[k]
        #
        symbol_properties = test_config['symbols']
        #
        tick_data = test_params['tick_data']
        if isinstance(tick_data, str):
            tick_data = self.config_path_to_abs_path(test_config_path, tick_data)
            try:
                data = np.genfromtxt(tick_data, delimiter=',',
                                     dtype=[('s', object), ('t', 'datetime64[s]'), ('o', float), ('h', float), ('c', float),
                                            ('l', float), ('v', float), ('a', float), ('b', float), ], skip_header=1)
            except ValueError as ex:
                data = np.genfromtxt(tick_data, delimiter=',',
                                     dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                                            ('l', float), ('v', float), ('a', float), ('b', float), ], skip_header=1)

        else:
            data = self.get_tick_data_from_channel(symbol, tick_data)

        self.new_a = np.array(data,
                         dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                                ('l', float), ('v', float), ('a', float), ('b', float), ])
        #
        self.eat_params = test_params
        self.eat_params['symbol_properties'] = symbol_properties
        self.eat_params['account'] = account
        self.eat_params['script_path'] = script_path
        self.eat_params['log_path'] = log_path
        if print_log_type is not None:
            self.eat_params['print_log_type'] = print_log_type
        #
        if "start_time" not in self.eat_params.keys():
            # self.eat_params['start_time'] = str(datetime.utcfromtimestamp(self.new_a[0]['t']))
            self.eat_params['start_time'] = str(utc_from_timestamp(self.new_a[0]['t']))
        if "end_time" not in self.eat_params.keys():
            # self.eat_params['end_time'] = str(datetime.utcfromtimestamp(self.new_a[-1]['t']))
            self.eat_params['end_time'] = str(utc_from_timestamp(self.new_a[-1]['t']))
        #
        test_period = self.eat_params.get('test_period', 0)
        if test_period > 0:
            date_dict = {}
            for index in reversed(range(self.new_a.size)):
                # date_str = str(datetime.utcfromtimestamp(self.new_a[index]['t']).date())
                date_str = str(utc_from_timestamp(self.new_a[index]['t']).date())
                if date_str not in date_dict:
                    if len(date_dict) < test_period:
                        date_dict[date_str] = index
                    else:
                        self.eat_params['tick_start_index'] = index + 1
                        break

    def get_url_data(self, url, timeout=90):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
            }
            req = Request(url, headers=headers)
            r = urlopen(req, timeout=timeout)
            content_type = r.headers.get('Content-Type', None)
            return r.code, content_type, r.read()
        except Exception as ex:
            traceback.print_exc()
        return None, None, None

    def load_channel_cache_file(self, channel, name):
        try:
            fp = f"./pxcache/data/{channel}/{name}.csv"
            data = np.genfromtxt(fp, delimiter=',',
                                 dtype=[('s', object), ('t', 'datetime64[s]'), ('o', float), ('h', float), ('c', float),
                                        ('l', float), ('v', float), ('a', float), ('b', float), ], skip_header=1)
            return data
        except:
            traceback.print_exc()
        return None

    def save_channel_cache_file(self, channel, name, data):
        try:
            fp = f"./pxcache/data/{channel}"
            Path(fp).mkdir(parents=True, exist_ok=True)
            with open(f"{fp}/{name}.csv", 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(data['columns'])
                writer.writerows(data['rows'])
            return data
        except:
            traceback.print_exc()
        return None

    def get_tick_data_from_tradepython(self, symbol, tick_source):
        channel = "tradepython.com"
        api_token = tick_source['api_token']
        source = tick_source['source']
        if isinstance(source, dict):
            source_type = source['type']
            source_name = source['name']
        else:
            source_type = "private"
            source_name = source
        #
        timeframe = tick_source.get('timeframe', 'm1')
        format = tick_source.get('format', 'json')
        period = tick_source.get('period', None)
        if period is not None:
            end_time = datetime.now().date()
            start_time = end_time - timedelta(days=period)
        else:
            end_time = tick_source.get('end_time', datetime.now().date())
            if isinstance(end_time, str):
                end_time = dateutil.parser.parse(end_time)
            start_time = tick_source.get('start_time', end_time - timedelta(days=7))
            if isinstance(start_time, str):
                start_time = dateutil.parser.parse(start_time)
        #
        cache_file_name = f"tradepython-{source_type}-{source_name}-{symbol}-{timeframe}-{start_time}-{end_time}"
        data = self.load_channel_cache_file(channel, cache_file_name)
        if data is not None:
            return data
        # url = "http://www.tradepython.com/logger/api/v2/tick/get"
        url_params = dict(ats=hashlib.md5(api_token.encode("utf-8")).hexdigest(), s=symbol, f=format,
                          tf=timeframe,
                          st=start_time, et=end_time,
                          srt=source_type, srn=source_name)
        #
        url = f"http://www.tradepython.com/logger/api/v2/tick/get?{urlencode(url_params)}"
        http_code, content_type, ret = self.get_url_data(url)
        data = None
        if ret is not None:
            result = json.loads(ret)
            if result['errid'] != 0:
                raise Exception(f"tradepython error: {result['errid']}, {result['errmsg']}")
            else:
                data = result['data']
                self.save_channel_cache_file(channel, cache_file_name, data)
                return self.load_channel_cache_file(channel, cache_file_name)
        else:
            raise Exception('get_url_data error')

    def get_tick_data_from_yfinance(self, symbol, tick_source):
        import yfinance as yf
        channel = "yfinance"
        # api_token = tick_source['api_token']
        # source = tick_source['source']
        # if isinstance(source, dict):
        #     source_type = source['type']
        #     source_name = source['name']
        # else:
        #     source_type = "private"
        #     source_name = source
        #
        timeframe = tick_source.get('timeframe', 'm1')
        format = tick_source.get('format', 'json')
        period = tick_source.get('period', None)
        if period is not None:
            end_time = datetime.now().date()
            start_time = end_time - timedelta(days=period)
        else:
            end_time = tick_source.get('end_time', datetime.now().date())
            if isinstance(end_time, str):
                end_time = dateutil.parser.parse(end_time)
            start_time = tick_source.get('start_time', end_time - timedelta(days=7))
            if isinstance(start_time, str):
                start_time = dateutil.parser.parse(start_time)
        #
        cache_file_name = f"{channel}-{symbol}-{timeframe}-{start_time}-{end_time}"
        data = self.load_channel_cache_file(channel, cache_file_name)
        if data is not None:
            return data
        # url = "http://www.tradepython.com/logger/api/v2/tick/get"
        # url_params = dict(ats=hashlib.md5(api_token.encode("utf-8")).hexdigest(), s=symbol, f=format,
        #                   tf=timeframe,
        #                   st=start_time, et=end_time,
        #                   srt=source_type, srn=source_name)
        #
        yfObj = yf.Ticker(symbol)
        data = yfObj.history(start=start_time, end=end_time)
        # url = f"http://www.tradepython.com/logger/api/v2/tick/get?{urlencode(url_params)}"
        # http_code, content_type, ret = self.get_url_data(url)
        if data is not None:
            json_data = self.covert_yfinance_data_to_json(symbol, data)
            self.save_channel_cache_file(channel, cache_file_name, json_data)
            return self.load_channel_cache_file(channel, cache_file_name)
        else:
            raise Exception('get_url_data error')

    def covert_yfinance_data_to_json(self, symbol, data):
        # s,t,o,h,c,l,v,a,b
        d = dict(columns=['s','t','o','h','c','l','v','a','b'], rows=[])
        for i in range(data.index.size):
            d['rows'].append([symbol, str(data.index[i]), data.Open[i], data.High[i], data.Close[i], data.Low[i], data.Volume[i], 0, 0])
        return d


    def get_tick_data_from_channel(self, symbol, tick_source):
        channels = {"tradepython.com": self.get_tick_data_from_tradepython,
                    "yfinance": self.get_tick_data_from_yfinance, }
        channel = channels.get(tick_source['channel'], None)
        if channel is None:
            raise NotImplementedError
        else:
            return channel(symbol, tick_source)

    def init_data(self):
        super(PXTester, self).init_data()
        self.tick_order_logs = []

    def on_load_ticks(self, *args, **kwargs):
        self.tick_info = self.get_data_info(symbol=self.symbol, timeframe=self.tick_timeframe,
                                            start_time=self.start_time,
                                            end_time=self.end_time)
        return 0

    def __update_execuate_log__(self, ticket, count=20, force=False):
        if force or time.time() - self.context.update_log_time > 2:  # 1s
            if count is not None:
                eidx = self.context.last_update_print_log_index + count
            else:
                eidx = None
            logs = self.context.print_logs[self.context.last_update_print_log_index:eidx]
            # OEOEHuiEATester.add_logs(self.ticket, 'print', logs)
            for l in logs:
                self.write_log(l, type='ea')
            self.context.last_update_print_log_index += len(logs)
            # #
            #
            self.context.update_log_time = time.time()
    #
    # def __update_execuate_log__(self, ticket, count=20, force=False):
    #     if force or time.time() - self.context.update_log_time > 2:  # 1s
    #         if count is not None:
    #             eidx = self.context.last_update_print_log_index + count
    #         else:
    #             eidx = None
    #         logs = self.context.print_logs[self.context.last_update_print_log_index:eidx]
    #         # OEOEHuiEATester.add_logs(self.ticket, 'print', logs)
    #         for l in logs:
    #             self.write_log(l, type='ea')
    #         self.context.last_update_print_log_index += len(logs)
    #         # #
    #
    #         #
    #         self.context.update_log_time = time.time()


    def on_end_tick(self, *args, **kwargs):
        try:
            self.__update_execuate_log__(self.ticket, count=20, force=False)
            tick = dict(t=self.Time().timestamp(), o=self.Open(), c=self.Close(),
                                                                    h=self.High(), l=self.Low(), v=self.Volume(),
                                                                    equity=self.context.account['equity'],
                                                                    balance=self.context.account['balance'],
                                                                    margin=self.context.account['margin'],
                                                                    orders=self.tick_order_logs)
            self.graph_data['ticks'].append(tick)
            if self.tester_graph_server is not None:
                data = dict(cmd='update_data', name=self.graph_data['name'],
                            symbol=self.graph_data['symbol'], group=self.graph_data['group'],
                                                data=dict(price=tick))
                # self.tester_graph_server.send_message(json5.dumps(data, quote_keys=True))
                self.tester_graph_server.send_message(json.dumps(data))
            self.tick_order_logs = []
        except:
            traceback.print_exc()
        return 0

    def on_end_execute(self, *args, **kwargs):
        self.__update_execuate_log__(self.ticket, None, force=True)
        report_str = "\n-- Result --\n"
        idx = 1
        for key in self.context.report:
            item = self.context.report[key]
            #
            precision = item.get('precision', 2)
            item_type = item.get('type', 'value')
            rs = None
            if item['value'] is not None:
                if item_type == 'value':
                    rs = f"{idx:02d}). {item['desc']}: {round(item['value'], precision)}\n"
                elif item_type == '%': #%
                    rs = f"{idx:02d}). {item['desc']}: {round(item['value']*100, precision)} %\n"
            #str
            if rs is None:
                rs = f"{idx:02d}). {item['desc']}: {item['value']}\n"
            report_str += rs

            idx += 1
        self.write_log(f"{report_str}", type='report')
        if self.test_result is not None:
            # self.test_result.value = json5.dumps(dict(report=self.context.report), quote_keys=True)
            self.test_result.value = json.dumps(dict(report=self.context.report))
        if self.test_graph_data is not None:
            # self.test_graph_data.value = json5.dumps(dict(graph_data=self.graph_data), quote_keys=True)
            self.test_graph_data.value = json.dumps(dict(graph_data=self.graph_data))

        return 0
    #
    # def on_end_execute(self, *args, **kwargs):
    #     self.__update_execuate_log__(self.ticket, None, force=True)
    #     report_str = "\n-- Result --\n"
    #     idx = 1
    #     for key in self.context.report:
    #         item = self.context.report[key]
    #         precision = item.get('precision', 2)
    #         item_type = item.get('type', 'value')
    #         if item_type == 'value':
    #             report_str += f"{idx:02d}). {item['desc']}: {round(item['value'], precision)}\n"
    #         elif item_type == '%': #%
    #             report_str += f"{idx:02d}). {item['desc']}: {round(item['value']*100, precision)} %\n"
    #         else: #str
    #             report_str += f"{idx:02d}). {item['desc']}: {item['value']}\n"
    #
    #         idx += 1
    #     self.write_log(f"{report_str}", type='report')
    #     return 0



    def GetSymbolData(self, symbol=None, timeframe=None):
        if symbol is None:
            symbol = self.symbol
        if timeframe is None:
            timeframe = self.tick_timeframe
        return self.get_data_info(symbol, timeframe)

    def __convert_db_price_data__(self, dbo_data, t_unit, t_count, desc):
        '''转换DB数据'''
        # seconds = calculate_second_intervals(t_unit, t_count)
        raw_data = []
        data = []
        # for d in dbo_data:
        #     data.append(dict(t=d.time_frame, s=d.symbol, o=d.open_price,
        #                            h=d.high_price, c=d.close_price, l=d.low_price, v=d.volume,
        #                            a=d.ask, b=d.bid))
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
            # self.fill_price_list(seconds, raw_data, np, desc, check=False)
            # self.fill_price_list(seconds, data, np, desc, check=True)
            # new_a = np.array(data,
            #                  dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
            #                         ('l', float), ('v', float), ('a', float), ('b', float), ])
        return raw_data, data

    def symbol_datagetitem_index(self, data_index_ts, timeframe, timeframe_seconds, shift):
        t = int(self.tick_info[self.context.tick_current_index]['t']/ timeframe_seconds)*timeframe_seconds
        cidx = np.where(data_index_ts == t)[0][0]
        idx = cidx - shift
        return idx

    def symbol_datagetitem_callback(self, data, data_index_ts, timeframe, timeframe_seconds, shift, fail_value):
        idx = self.symbol_datagetitem_index(data_index_ts, timeframe, timeframe_seconds, shift)
        # idx = self.context.tick_current_index - shift
        if idx < 0:
            return fail_value
        return data[idx]

    def pandas_to_tf_data(self, src, timeframe):
        pd_tf_str = {TimeFrame.S1: '1s', TimeFrame.M1: '1T', TimeFrame.M5: '5T', TimeFrame.M15: '15T',
                     TimeFrame.M30: '30T',
                     TimeFrame.H1: '1H', TimeFrame.H4: '4H', TimeFrame.D1: '1D', TimeFrame.S1: '1s', }
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
        return ret

    def get_data_info(self, symbol, timeframe=TimeFrame.M1,  start_time=None, end_time=None, last_count=None):
        """"""
        data = None
        if symbol is None:
            symbol = self.symbol
        symbol_tf = self.symbol_data.get(symbol, None)
        if symbol_tf:
            data = symbol_tf.get(timeframe, None)
        else:
            self.symbol_data[symbol] = {}
        if data is None:
            st = dateutil.parser.parse(self.start_time)
            et = dateutil.parser.parse(self.end_time)
            # ary = self.new_a[(self.new_a['t'] >= st.timestamp()) & (self.new_a['t'] < et.timestamp())]
            ary = self.new_a[(self.new_a['t'] >= st.replace(tzinfo=pytz.utc).timestamp()) & (self.new_a['t'] < et.replace(tzinfo=pytz.utc).timestamp())]
            #
            data = self.pandas_to_tf_data(ary, timeframe)
            self.symbol_data[symbol][timeframe] = data

        return self.symbol_data[symbol][timeframe]

