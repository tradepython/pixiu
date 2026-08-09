# env
import csv
import copy
import json
import math
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
from pixiu.tester.chart_protocol import sanitize_chart_config

np.set_printoptions(legacy="1.25")

class PXTester(EATester):
    def __init__(self, test_config_path, test_name, script_path, log_path=None, print_log_type=None, test_result=None,
                 tester_graph_server=None, test_graph_data=None, runtime_options=None):
        self.test_name = test_name
        self.test_result = test_result
        self.test_graph_data = test_graph_data
        self.runtime_options = copy.deepcopy(runtime_options or {})
        self.parse_test_config(test_config_path, test_name, script_path, log_path, print_log_type)
        super(PXTester, self).__init__(self.eat_params)
        self.tester_graph_server = tester_graph_server
        self.tick_order_logs = []
        self.live_report_interval_seconds = float(os.environ.get("PIXIU_GRAPH_REPORT_INTERVAL_SECONDS", "2"))
        self.live_report_interval_ticks = int(os.environ.get("PIXIU_GRAPH_REPORT_INTERVAL_TICKS", "100"))
        self.live_report_last_time = 0
        self.live_report_last_tick_index = None
        self.live_metadata_sent = False
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
        self.tick_source = tick_data
        self.symbol_tick_data = {}
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
        self.symbol_tick_data[symbol] = self.new_a
        #
        self.eat_params = test_params
        self.eat_params['symbol_properties'] = symbol_properties
        self.eat_params['account'] = account
        self.eat_params['script_path'] = script_path
        self.eat_params['log_path'] = log_path
        if print_log_type is not None:
            self.eat_params['print_log_type'] = print_log_type
        self.apply_runtime_options()
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
        self.eat_params['chart_metadata'] = {
            "test_config": self.__build_chart_test_config_metadata__(
                test_config_path=test_config_path,
                test_name=test_name,
                test_params=self.eat_params,
                account=account,
            )
        }

    def apply_runtime_options(self):
        runtime_options = copy.deepcopy(self.runtime_options)
        for key in ("explain_enabled", "collect_graph_data", "collect_chart_replay", "graph_sample_ticks"):
            if key in runtime_options:
                self.eat_params[key] = runtime_options[key]
        if runtime_options.get("tick_max_index") is not None:
            self.eat_params["tick_max_index"] = runtime_options["tick_max_index"]
        if runtime_options:
            self.eat_params["runtime_options"] = runtime_options

    def __build_chart_test_config_metadata__(self, test_config_path, test_name, test_params, account):
        safe_account_keys = (
            "currency",
            "balance",
            "credit",
            "leverage",
            "margin_so_call",
            "margin_so_so",
            "free_margin_mode",
            "stop_out_level",
            "stop_out_mode",
        )
        safe_account = {}
        if isinstance(account, dict):
            for key in safe_account_keys:
                if key in account:
                    safe_account[key] = copy.deepcopy(account[key])
        return {
            "config_file": test_config_path,
            "test_name": test_name,
            "symbol": test_params.get("symbol"),
            "timeframe": test_params.get("tick_timeframe", test_params.get("timeframe", TimeFrame.M1)),
            "start_time": test_params.get("start_time"),
            "end_time": test_params.get("end_time"),
            "test_period": test_params.get("test_period"),
            "tick_start_index": test_params.get("tick_start_index"),
            "tick_max_index": test_params.get("tick_max_index"),
            "tick_source": copy.deepcopy(test_params.get("tick_data")),
            "account": safe_account,
            "scenario": copy.deepcopy(test_params.get("scenario")),
            "currency_conversion_settings": copy.deepcopy(test_params.get("currency_conversion_settings")),
        }

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

    def load_symbol_tick_data(self, symbol):
        data = self.symbol_tick_data.get(symbol, None)
        if data is not None:
            return data
        if not isinstance(self.tick_source, dict):
            return None
        data = self.get_tick_data_from_channel(symbol, self.tick_source)
        data = np.array(data,
                        dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                               ('l', float), ('v', float), ('a', float), ('b', float), ])
        self.symbol_tick_data[symbol] = data
        return data

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
            if not self.__should_emit_graph_tick__():
                self.tick_order_logs = []
                return 0
            # Keep chart replay on the raw feed epoch; Time() returns a naive UTC datetime.
            tick_time = float(self.current_time())
            tick = dict(t=tick_time, o=self.Open(), c=self.Close(),
                                                                    h=self.High(), l=self.Low(), v=self.Volume(),
                                                                    equity=self.context.account['equity'],
                                                                    balance=self.context.account['balance'],
                                                                    margin=self.context.account['margin'],
                                                                    orders=self.tick_order_logs)
            if self.__should_collect_graph_data__():
                self.graph_data['ticks'].append(tick)
            if self.tester_graph_server is not None:
                data = dict(cmd='update_data', name=self.graph_data['name'],
                            symbol=self.graph_data['symbol'], group=self.graph_data['group'],
                                                data=dict(price=tick))
                if not self.live_metadata_sent:
                    data['data']['metadata'] = self.__build_live_graph_metadata__()
                    self.live_metadata_sent = True
                report = self.__build_live_graph_report__(force=False)
                if report is not None:
                    data['data']['report'] = report
                # self.tester_graph_server.send_message(json5.dumps(data, quote_keys=True))
                self.tester_graph_server.send_message(self.__json_dumps__(data))
            self.tick_order_logs = []
        except:
            traceback.print_exc()
        return 0

    def __should_collect_graph_data__(self):
        return bool(self.context.ctx.get("collect_graph_data", True))

    def __should_collect_chart_replay__(self):
        return bool(self.context.ctx.get("collect_chart_replay", True))

    def __graph_sample_ticks__(self):
        try:
            return max(1, int(self.context.ctx.get("graph_sample_ticks", 1) or 1))
        except (TypeError, ValueError):
            return 1

    def __should_emit_graph_tick__(self):
        if not self.__should_collect_graph_data__() and self.tester_graph_server is None:
            return False
        tick_index = getattr(self.context, "tick_current_index", 0) or 0
        tick_start_index = getattr(self.context, "tick_start_index", 0) or 0
        if self.tester_graph_server is not None and not self.live_metadata_sent:
            return True
        if self.tick_order_logs:
            return True
        sample_ticks = self.__graph_sample_ticks__()
        if sample_ticks <= 1:
            return True
        return (tick_index - tick_start_index) % sample_ticks == 0

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
        self.__send_graph_report__(force=True, message=report_str)
        if self.test_result is not None:
            # self.test_result.value = json5.dumps(dict(report=self.context.report), quote_keys=True)
            self.test_result.value = json.dumps(dict(report=self.context.report))
        if self.test_graph_data is not None:
            # self.test_graph_data.value = json5.dumps(dict(graph_data=self.graph_data), quote_keys=True)
            graph_data = self.graph_data if self.__should_collect_graph_data__() else dict(
                ticks=[],
                name=self.graph_data.get("name"),
                symbol=self.graph_data.get("symbol"),
                group=self.graph_data.get("group"),
            )
            result = dict(graph_data=graph_data)
            if self.__should_collect_chart_replay__():
                result["chart_replay"] = self.build_chart_replay(graph_data=graph_data)
            self.test_graph_data.value = json.dumps(result)

        return 0

    def __send_graph_report__(self, force=False, message=None):
        if self.tester_graph_server is None:
            return False
        report = self.__build_live_graph_report__(force=force)
        if report is None:
            return False
        try:
            data = dict(cmd='update_report', name=self.graph_data['name'],
                        symbol=self.graph_data['symbol'], group=self.graph_data['group'],
                        data=dict(report=report, time=float(self.current_time())))
            if message:
                data['data']['message'] = message
            self.tester_graph_server.send_message(self.__json_dumps__(data))
            return True
        except:
            traceback.print_exc()
        return False

    def __build_live_graph_report__(self, force=False):
        if not force and not self.__should_send_live_graph_report__():
            return None
        report = self.__live_graph_report_snapshot__()
        self.__mark_live_graph_report_sent__()
        return report

    def __should_send_live_graph_report__(self):
        tick_index = getattr(self.context, "tick_current_index", None)
        if self.live_report_last_tick_index is None:
            return True
        if self.live_report_interval_ticks > 0 and tick_index is not None:
            if tick_index - self.live_report_last_tick_index >= self.live_report_interval_ticks:
                return True
        if self.live_report_interval_seconds > 0:
            if time.time() - self.live_report_last_time >= self.live_report_interval_seconds:
                return True
        return False

    def __mark_live_graph_report_sent__(self):
        self.live_report_last_time = time.time()
        self.live_report_last_tick_index = getattr(self.context, "tick_current_index", None)

    def __live_graph_report_snapshot__(self):
        account = getattr(self.context, "account", {}) or {}
        tick_index = getattr(self.context, "tick_current_index", None)
        tick_value = tick_index + 1 if tick_index is not None else None
        balance = account.get("balance")
        equity = account.get("equity")
        margin = account.get("margin")
        free_margin = account.get("free_margin")
        live_report = {
            "live_time": {"value": self.current_time(), "desc": "Live Time"},
            "live_tick": {"value": tick_value, "desc": "Live Tick"},
            "live_balance": {"value": balance, "desc": "Live Balance"},
            "live_equity": {"value": equity, "desc": "Live Equity"},
            "live_margin": {"value": margin, "desc": "Live Margin"},
            "live_free_margin": {"value": free_margin, "desc": "Live Free Margin"},
        }
        if balance is not None and equity is not None:
            live_report["live_floating_profit"] = {
                "value": equity - balance,
                "desc": "Live Floating Profit",
            }
        if margin:
            live_report["live_margin_level"] = {
                "value": equity / margin if equity is not None else None,
                "desc": "Live Margin Level",
                "type": "%",
            }
        report = copy.deepcopy(getattr(self.context, "report", {}) or {})
        live_report.update(report)
        return live_report

    def __build_live_graph_metadata__(self):
        symbol = getattr(self.context, "symbol", None) or self.graph_data.get("symbol")
        metadata = {
            "mode": "tester_live",
            "test_name": self.test_name,
            "symbol": symbol,
        }
        script_metadata = getattr(self.context, "script_metadata", None)
        if isinstance(script_metadata, dict):
            for key in ("name", "version", "label"):
                if script_metadata.get(key) is not None:
                    metadata[f"script_{key}"] = script_metadata.get(key)
        ctx = getattr(self.context, "ctx", None)
        if isinstance(ctx, dict) and isinstance(ctx.get("chart_metadata"), dict):
            metadata.update(copy.deepcopy(ctx["chart_metadata"]))
        script_settings = getattr(self.context, "script_settings", None)
        metadata["script_settings"] = copy.deepcopy(script_settings) if isinstance(script_settings, dict) else {}
        account = getattr(self.context, "account", None)
        if isinstance(account, dict):
            metadata["account"] = {
                key: copy.deepcopy(account[key])
                for key in ("currency", "balance", "credit", "leverage")
                if key in account
            }
        return sanitize_chart_config(metadata)

    def __json_default__(self, value):
        if hasattr(value, "item"):
            return value.item()
        return str(value)

    def __json_dumps__(self, value):
        return json.dumps(self.__json_safe__(value), ensure_ascii=False, allow_nan=False)

    def __json_safe__(self, value):
        try:
            if hasattr(value, "item"):
                value = value.item()
        except ValueError:
            pass
        if isinstance(value, dict):
            return {key: self.__json_safe__(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.__json_safe__(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        try:
            json.dumps(value, allow_nan=False)
            return value
        except (TypeError, ValueError):
            return self.__json_default__(value)
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
            source_data = self.load_symbol_tick_data(symbol)
            if source_data is None:
                source_data = self.new_a
            source_symbols = source_data['s'].astype(str)
            symbol_data = source_data[source_symbols == symbol]
            if symbol_data.size == 0:
                symbol_data = source_data
            ary = symbol_data[(symbol_data['t'] >= st.replace(tzinfo=pytz.utc).timestamp()) & (symbol_data['t'] < et.replace(tzinfo=pytz.utc).timestamp())]
            #
            data = self.pandas_to_tf_data(ary, timeframe)
            self.symbol_data[symbol][timeframe] = data

        return self.symbol_data[symbol][timeframe]
