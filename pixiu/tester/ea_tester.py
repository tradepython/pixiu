
import sys
import math
import json
import threading
import importlib
import pkg_resources
from datetime import (datetime, )
import numpy as np
from RestrictedPython import (compile_restricted, safe_globals, utility_builtins,)
from ..base.ea_base import (EABase)
from .tester_api_v1 import (TesterAPI_V1, )
import pandas as pd
from pixiu.api.errors import *
from pixiu.api import (TimeFrame, OrderCommand, order_is_long, order_is_short, order_is_market, order_is_stop,
                       order_is_limit, order_is_pending, OrderStatus)
from pixiu.api.v1 import (DataScope, )
import traceback
import logging
log = logging.getLogger(__name__)


#
class EATesterPrintCollector(object):
    """Collect written text, and return it when called."""

    def __init__(self, _getattr_=None, write_log=None):
        self.txt = []
        self._getattr_ = _getattr_
        self.write_log = write_log

    def write(self, text):
        self.txt.append(text)

    def __call__(self):
        return ''.join(self.txt)

    def _call_print(self, *objects, **kwargs):
        if kwargs.get('file', None) is None:
            kwargs['file'] = self
        else:
            self._getattr_(kwargs['file'], 'write')
        if not self.write_log(*objects, type='ea'):
            print(*objects, **kwargs)


#---------------------------------------------------------------------------------------------------------------------
# EATester
#---------------------------------------------------------------------------------------------------------------------
class TickMode():
    EVERY_TICK = 100
    ONLY_OPEN = 200


MAX_DATA_LENGTH = 1048576 #1MB
class EATester(EABase):
    """EA Tester"""
    def __init__(self, params):
        super(EATester, self).__init__(params)
        #
        self.default_digits = 2
        self.symbol = params["symbol"]
        self.default_symbol_properties = params.get("symbol_properties", None)
        self.spread_point = params.get("spread_point", None)
        self.commission = params.get("commission", 0) #commission / a lot
        self.tick_mode = params.get("tick_mode", TickMode.EVERY_TICK)
        self.tick_timeframe = params.get("tick_timeframe", TimeFrame.M1)
        self.tick_max_count = params.get('tick_max_count', None)
        self.start_time = params["start_time"]
        self.end_time = params["end_time"]

        self.language = params.get("language", 'en')
        self.script_path = params.get("script_path", None)
        self.script_libs = params.get("script_libs", None)
        self.log_file = None
        self.log_path = params.get("log_path", None)
        self.print_log_type = params.get("print_log_type", ['account', 'ea', 'order', 'report'])
        #
        margin_so_so = self.percent_str_to_float(params.get("margin_so_so", None), 1.0) #100%
        if margin_so_so < 0:
            margin_so_so = 1.0
        margin_so_call = self.percent_str_to_float(params.get("margin_so_call", None), margin_so_so*1.2) #120%
        if margin_so_call < 0:
            margin_so_call = margin_so_so * 1.2
        #
        if self.log_path:
            self.log_file = open(self.log_path, mode='at')

        if self.script_path is None:
            self.script = params["script"]
        else:
            self.script = open(self.script_path).read()
        #
        self.script_metadata = self.parse_script(self.script)
        if self.script_libs is None:
            self.script_libs = self.load_libs(json.loads(self.script_metadata.get('lib', self.script_metadata.get('library', '[]'))))
        #
        self.script_settings = None
        try:
            ss = params.get("script_settings", self.script_metadata.get('script_settings', None))
            if ss:
                self.script_settings = json.loads(ss)
        except:
            traceback.print_exc()
        #
        self.byte_code = None
        self.orders = None
        self.order_logs = []
        self.charts_data = []
        self.account_logs = []
        self.balance_dead_line = 0.0
        self.account = params.get("account", None)
        if self.account is None:
            balance = round(float(params['balance']), self.default_digits)
            equity = balance
            try:
                leverage = float(params.get('leverage', 100))
            except:
                leverage = 100
            self.account = {'balance': balance,
                            'equity': equity,
                            'margin': 0,
                            'free_margin': balance,
                            'credit': 0.0,
                            'profit': 0.0,
                            'margin_level': 0,
                            #static
                            'leverage': leverage,
                            'currency': params.get("currency", None),
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
                            'margin_so_call': margin_so_call,
                            'margin_so_so': margin_so_so,
                            'commission': 0.0,
                            }
        else:
            default_value = {'equity': self.account['balance'], 'margin': 0, 'free_margin': self.account['balance']}
            for k in default_value:
                if k not in self.account:
                    self.account[k] = default_value[k]
        #
        self.print_collection = None
        #
        self.current_api = TesterAPI_V1(tester=self, data_source={}, default_symbol=params["symbol"])
        self.data = {DataScope.EA_VERSION: {}, DataScope.EA: {}, DataScope.ACCOUNT: {}, DataScope.EA_SETTIGNS: {}}

    def percent_str_to_float(self, val, default):
        try:
            if val is not None:
                if isinstance(val, str) and '%' in val:
                    return float(val.strip('%')) / 100
                return float(val)
        except:
            traceback.print_exc()
        return default

    def delete_data(self, name, scope):
        self.data[scope].pop(name)
        return 0

    def load_data(self, name, scope, format='json'):
        if format != 'json':
            return None
        data = self.data[scope].get(name, None)
        if data is None:
            return None
        return json.loads(data)

    def save_data(self, name, data, scope, format='json'):
        if format != 'json':
            return EID_EAT_INVALID_DATA_FORMAT
        if data is not None:
            data = json.dumps(data)
            if len(data) > MAX_DATA_LENGTH:
                return EID_EAT_INVALID_DATA_LENGTH
        self.data[scope][name] = data
        return EID_OK

    def init_report_data(self):
        self.report = {
                        'init_balance': {'value': self.account['balance'], 'desc': 'Init Balance'}, #
                        'symbol': {'value': self.symbol, 'desc': 'Symbol', 'type': 'str'}, #
                        'currency': {'value': self.account['currency'], 'desc': 'Currency', 'type': 'str'}, #
                        'leverage': {'value': self.account['leverage'], 'desc': 'Leverage'}, #
                        'spread_point': {'value': self.spread_point, 'desc': 'Spread Points'}, #
                        'margin_so_call': {'value': self.account['margin_so_call'], 'desc': 'Margin Call Level', 'type': '%'},  #
                        'margin_so_so': {'value': self.account['margin_so_so'], 'desc': 'Stop Out Level', 'type': '%'},  #
                        'ticks': {'value': 0, 'desc': 'Ticks', 'precision': 0}, #
                        'balance': {'value': 0, 'desc': 'Balance'}, #
                        'total_net_profit': {'value': 0, 'desc': 'Total Net Profit'}, #
                        'total_net_profit_rate': {'value': 0, 'desc': 'Total Net Profit Rate', 'type': '%'}, #
                        'sharpe_ratio': {'value': 0, 'desc': 'Sharpe Ratio', 'type': '%'}, #
                        'absolute_drawdown': {'value': 0, 'desc': 'Absolute Drawdown'}, #
                        'max_drawdown': {'value': 0, 'desc': 'Max Drawdown'}, #
                        'max_drawdown_rate': {'value': 0, 'desc': 'Max Drawdown Rate', 'type': '%'}, #
                        'total_trades': {'value': 0, 'desc': 'Total Trades', 'precision': 0},#
                        'profit_trades': {'value': 0, 'desc': 'Profit Trades', 'precision': 0},#
                        'win_rate': {'value': 0, 'desc': 'Win Rate', 'type': '%'},  #
                        'trade_max_profit': {'value': 0, 'desc': 'Trade Max Profit'}, #
                        'trade_avg_profit': {'value': 0, 'desc': 'Trade Avg Profit'}, #
                        'trade_max_loss': {'value': np.nan, 'desc': 'Trade Max Loss'}, #
                        'trade_avg_loss': {'value': 0, 'desc': 'Trade Avg Loss'}, #
                        'loss_trades': {'value': 0, 'desc': 'Loss Trades', 'precision': 0}, #
                        'gross_profit': {'value': 0, 'desc': 'Gross Profit'}, #
                        'gross_loss': {'value': 0, 'desc': 'Gross Loss'}, #
                        'short_positions': {'value': 0, 'desc': 'Short Positions', 'precision': 0}, #
                        'short_positions_win': {'value': 0, 'desc': 'Short Positions Win', 'precision': 0}, #
                        'long_positions': {'value': 0, 'desc': 'Long Positions', 'precision': 0}, #
                        'long_positions_win': {'value': 0, 'desc': 'Long Positions Win', 'precision': 0}, #
                        'max_consecutive_wins': {'value': 0, 'desc': 'Max Consecutive Wins', 'precision': 0}, #
                        'max_consecutive_wins_money': {'value': 0, 'desc': 'Max Consecutive Wins Money'}, #
                        'max_consecutive_losses': {'value': 0, 'desc': 'Max Consecutive Losses', 'precision': 0}, #
                        'max_consecutive_losses_money': {'value': 0, 'desc': 'Max Consecutive Losses Money'}, #
        }
        self.temp = {
            'consecutive_wins': 0,
            'consecutive_wins_money': 0,
            'consecutive_losses': 0,
            'consecutive_losses_money': 0,
            'max_drawdown': 0,
            'max_drawdown_rate': 0,
            'account_max_equity': self.account['equity'],
            'account_min_equity': self.account['equity'],
            'account_min_balance': self.account['balance'],
        }

    def get_print_factory(self, _getattr_=None):
        """print factory"""
        if self.print_collection is None:
            self.print_collection = EATesterPrintCollector(_getattr_, self.write_log)
        return self.print_collection

    def write_log(self, *args, **kwargs):
        log_type = kwargs.get('type', 'eat')
        if log_type == 'eat' or log_type in self.print_log_type:
            print(*args)
        #
        if self.log_file:
            log_str = ''
            for a in args:
                log_str = f'{log_str} {a}'
            self.log_file.write(str(log_str))
            # self.log_file.write(*args)
            self.log_file.write('\n')
        return True
    #
    # def write_log(self, *args, **kwargs):
    #     print_ = kwargs.get('print_', True)
    #     if print_:
    #         print(*args)
    #     #
    #     if self.log_file:
    #         log_str = ''
    #         for a in args:
    #             log_str = f'{log_str} {a}'
    #         self.log_file.write(str(log_str))
    #         # self.log_file.write(*args)
    #         self.log_file.write('\n')
    #     return True

    def get_account_data(self, timeframe):
        """"""
        data = None
        data = self.account_info.get('__ds__', None)
        if data:
            data = data.get(timeframe, None)
        else:
            self.account_info['__ds__'] = {}
        if data is None:
            new_a = np.array([(0.0, )*33]*self.tick_info.size,
                             dtype=[('t', float), ('credit', float),
                                    ('balance', float), ('max_balance', float), ('min_balance', float),
                                    ('equity', float), ('max_equity', float), ('min_equity', float),
                                    ('margin', float), ('max_margin', float), ('min_margin', float),
                                    ('margin_level', float),
                                    ('profit', float), ('max_profit', float), ('min_profit', float),
                                    ('free_margin', float),
                                    ('commission', float),
                                    #static
                                    ('currency', object),
                                    ('free_margin_mode', float),
                                    ('leverage', float),
                                    ('stop_out_level', float),
                                    ('stop_out_mode', float),
                                    ('company', object),
                                    ('name', object),
                                    ('number', float),
                                    ('server', object),
                                    ('trade_mode', float),
                                    ('limit_orders', float),
                                    ('margin_so_mode', float),
                                    ('trade_allowed', float),
                                    ('trade_expert', float),
                                    ('margin_so_call', float),
                                    ('margin_so_so', float),
                                    ])
            new_a['t'] = self.tick_info['t']
            #init
            new_a['credit'] = self.account['credit']
            new_a['balance'] = self.account['balance']
            new_a['equity'] = self.account['equity']
            new_a['margin'] = self.account['margin']
            new_a['free_margin'] = self.account['free_margin']
            new_a['credit'] = self.account['credit']
            new_a['profit'] = self.account['profit']
            new_a['margin_level'] = self.account['margin_level']
            new_a['commission'] = self.account['commission']
            #static
            new_a['currency'] = self.account['currency']
            new_a['free_margin_mode'] = self.account['free_margin_mode']
            new_a['leverage'] = self.account['leverage']
            new_a['stop_out_level'] = self.account['stop_out_level']
            new_a['stop_out_mode'] = self.account['stop_out_mode']
            new_a['company'] = self.account['company']
            new_a['name'] = self.account['name']
            new_a['number'] = self.account['number']
            new_a['server'] = self.account['server']
            new_a['trade_mode'] = self.account['trade_mode']
            new_a['limit_orders'] = self.account['limit_orders']
            new_a['margin_so_mode'] = self.account['margin_so_mode']
            new_a['trade_allowed'] = self.account['trade_allowed']
            new_a['trade_expert'] = self.account['trade_expert']
            new_a['margin_so_call'] = self.account['margin_so_call']
            new_a['margin_so_so'] = self.account['margin_so_so']

            self.account_info['__ds__'][timeframe] = new_a

        return self.account_info['__ds__'][timeframe]
    #

    def get_data_info(self, symbol, timeframe,  start_time=None, end_time=None, last_count=None):
        raise NotImplementedError

    def add_order_log(self, log_dict):
        """Add order log"""
        log_dict['id'] = len(self.order_logs) + 1
        self.order_logs.append(log_dict)

    def plot(self, chart_name, series):
        self.charts_data.append(dict(cn=chart_name, data=series))
        # self.charts_data.append(dict(cn="default", data=series))

    def add_account_log(self, log_dict):
        """Add account log"""
        self.account_logs.append(log_dict)

    def add_print_log(self):
        """"""
        if self.print_collection is not None:
            for t in self.print_collection.txt:
                self.print_logs.append(t)
            #clear print
            self.print_collection.txt = []

    def symbol_to_sid(self, symbol):
        sid = self.sid.get(symbol, None)
        if sid is None:
            sid = len(self.sid)
            self.sid[symbol] = sid
            self.sid_data[sid] = symbol
        return sid

    def command_to_cid(self, cmd):
        return self.cid[cmd]

    def order_to_ndarray(self, new_order):
        oid = int(new_order['uid'])
        sp = self.get_symbol_properties(new_order['symbol'])
        tcs = sp['trade_contract_size']
        #
        sid = self.symbol_to_sid(new_order['symbol'])
        cid = self.command_to_cid(new_order['cmd'])
        sl = np.nan if new_order['stop_loss'] is None else new_order['stop_loss']
        tp = np.nan if new_order['take_profit'] is None else new_order['take_profit']
        mar = np.nan if new_order['margin'] is None else new_order['margin']
        com = None if new_order['comment'] is None else new_order['comment']
        mn = 0 if new_order['magic_number'] is None else new_order['magic_number']
        ot = new_order['open_time']
        ct = 0
        c = np.nan
        sl_p = tp_p = np.nan
        pf_f = 1 if order_is_long(new_order['cmd']) else -1
        new_a = np.array([(oid, sid, cid, new_order['open_price'], new_order['volume'], sl, tp, mar, com, mn, ot, ct,
                           c, tcs, 0, pf_f,
                           sl_p, tp_p, new_order['commission'])],
                         dtype=[('oid', int), ('sid', int), ('cid', int), ('o', float), ('v', float),
                                ('sl', float), ('tp', float), ('mar', float), ('com', object),
                                ('mn', int), ('ot', int), ('ct', int), ('c', float),
                                ('tcs', float), ('pf', float), ('pf_f', int), ('sl_p', float), ('tp_p', float),
                                ('comm', float)])
        return new_a

    #
    def __add_pending_order__(self, new_order):
        """add a new pending order"""
        if not order_is_limit(new_order['cmd']) and not order_is_stop(new_order['cmd']):
            return EID_EAT_INVALID_ORDER_TYPE, -1
        #
        self.orders['counter'] = self.orders['counter'] + 1
        symbol_orders = self.orders['pending'].get(new_order['symbol'], {})

        new_order['uid'] = new_order['ticket']
        new_order['status'] = OrderStatus.PENDING
        self.orders['data'][new_order['uid']] = new_order
        symbol_orders[new_order['uid']] = new_order
        self.orders['pending'][new_order['symbol']] = symbol_orders
        self.orders['pending_counter'] = self.orders['pending_counter'] + 1
        #
        sp = self.get_symbol_properties(new_order['symbol'])
        tcs = sp['trade_contract_size']
        #
        ds = self.orders['pending'].get('__ds__', None)

        new_a = self.order_to_ndarray(new_order)
        if ds is not None and ds.size > 0:
            self.orders['pending']['__ds__'] = np.concatenate([ds, new_a])
        else:
            self.orders['pending']['__ds__'] = new_a

        #
        return EID_OK, new_order['uid']

    def __add_market_order__(self, new_order):
        """add a new market order"""
        if not order_is_market(new_order['cmd']):
            return EID_EAT_INVALID_ORDER_TYPE, -1

        #
        sp = self.get_symbol_properties(new_order['symbol'])
        margin = new_order['open_price'] * self.__calculate_pip__(new_order['open_price']) * new_order['volume'] * sp['trade_contract_size'] / self.account['leverage']
        margin = round(margin, self.default_digits)
        if margin > self.account['balance'] - self.account['margin']:
            return EID_EAT_NOT_ENOUGH_MONEY, -1
        new_order['uid'] = str(new_order['ticket'])
        new_order['comment'] = f"uid#{new_order['uid']}|"
        new_order['margin'] = margin
        new_order['status'] = OrderStatus.OPENED

        commission = 0.0
        #commissions
        if self.commission > 0:
            # see: https://www.houseofborse.com/commission-calculation
            # all commission charged and debited on the opening of the trade
            commission = new_order['volume'] * self.commission * self.__calculate_pip__(new_order['open_price']) * 2
        if commission > self.account['balance'] - self.account['margin']:
            return EID_EAT_NOT_ENOUGH_MONEY, -1
        new_order['commission'] = commission
        #
        self.orders['counter'] = self.orders['counter'] + 1
        #
        symbol_orders = self.orders['opened'].get(new_order['symbol'], {})

        self.orders['data'][new_order['uid']] = new_order
        symbol_orders[new_order['uid']] = new_order
        self.orders['opened'][new_order['symbol']] = symbol_orders
        self.orders['opened_counter'] = self.orders['opened_counter'] + 1

        #
        ds = self.orders['opened'].get('__ds__', None)
        new_a = self.order_to_ndarray(new_order)
        if ds is not None and ds.size > 0:
            self.orders['opened']['__ds__'] = np.concatenate([ds, new_a])
        else:
            self.orders['opened']['__ds__'] = new_a
        #update account
        self.account['margin'] = round(self.account['margin'] + new_order['margin'], self.default_digits)
        self.account['commission'] = round(self.account['commission'] + new_order['commission'], self.default_digits)

        #report
        self.report['total_trades']['value'] += 1
        if order_is_long(new_order['cmd']):
            self.report['long_positions']['value'] += 1
        else:
            self.report['short_positions']['value'] += 1

        #
        return EID_OK, new_order['uid']

    def __active_pending_order__(self, order_uid, price, comment=None, tags=None):
        """"""
        order_dict = self.get_order(order_uid=order_uid)
        if order_dict is None:
            return EID_EAT_INVALID_ORDER_TICKET, order_uid
        order_uid = self.__remove_pending_order__(order_dict)
        if order_is_long(order_dict['cmd']):
            order_dict['cmd'] = OrderCommand.BUY
        else:
            order_dict['cmd'] = OrderCommand.SELL
        #
        order_dict['comment'] = comment
        if tags:
            order_dict['tags'] = tags
        order_dict['dirty'] = False
        order_dict['open_time'] = self.current_time()
        order_dict['status'] = OrderStatus.OPENED
        #
        errid, order_uid = self.__add_market_order__(order_dict)
        if errid != EID_OK:
            return errid, order_uid
        #
        self.add_order_log(dict(uid=order_uid, ticket=order_dict['ticket'],
                                 time=str(datetime.fromtimestamp(order_dict['open_time'])),
                                 type=order_dict['cmd'], volume=order_dict['volume'],
                                 price=price,
                                 stop_loss=round(order_dict['stop_loss'], self.price_digits),
                                 take_profit=round(order_dict['take_profit'], self.price_digits),
                                 comment=order_dict['comment'], tags=order_dict['tags'],
                                 balance=None, profit=None))
        
        return EID_OK, order_uid

    def __modify_order__(self, order):
        if order_is_market(order['cmd']):
            ds = self.orders['opened']['__ds__']
        else:
            ds = self.orders['pending']['__ds__']
        #
        oid = int(order['uid'])
        modify_a = ds[ds['oid'] == oid]
        modify_a['o'] = order['open_price']
        modify_a['sl'] = np.nan if order['stop_loss'] <= 0 else order['stop_loss']
        modify_a['tp'] = np.nan if order['take_profit'] <= 0 else order['take_profit']
        modify_a['com'] = None if order['comment'] is None else order['comment']
        ds[ds['oid'] == oid] = modify_a

        return order['uid']
        
    def __remove_pending_order__(self, order):
        """"""
        order_list = self.get_order_dict(order['symbol'], 'pending')
        # ret = order_list.pop(order['uid'])
        ret = order_list.pop(order['uid'], None)
        if ret is None:
            return order['uid']
        #
        oid = int(order['uid'])
        ds = self.orders['pending']['__ds__']
        closed_a = ds[ds['oid'] == oid]
        self.orders['pending']['__ds__'] = ds[ds['oid'] != oid]
        #
        self.orders['pending_counter'] = self.orders['pending_counter'] - 1
        #
        return order['uid']

    def __remove_order__(self, order, add_closed=True):
        """"""
        order_list = self.get_order_dict(order['symbol'], 'opened')
        ret = order_list.pop(order['uid'], None)
        if ret is None:
            return order['uid']
        #
        oid = int(order['uid'])
        ds = self.orders['opened']['__ds__']
        # closed_a = ds[ds['oid'] == oid]
        closed_a = ds[ds['oid'] == oid][0]
        self.orders['opened']['__ds__'] = ds[ds['oid'] != oid]
        #
        order['profit'] = closed_a['pf']
        if add_closed:
            symbol_orders = self.orders['closed'].get(order['symbol'], {})
            symbol_orders[oid] = order
            self.orders['closed'][order['symbol']] = symbol_orders

        self.orders['opened_counter'] = self.orders['opened_counter'] - 1
        #

        return order['uid']

    # 
    # def __remove_order__(self, order, add_closed=True):
    #     """"""
    #     order_list = self.get_order_dict(order['symbol'], 'opened')
    #     order_list.pop(order['uid'])
    #     #
    #     oid = int(order['uid'])
    #     ds = self.orders['opened']['__ds__']
    #     # closed_a = ds[ds['oid'] == oid]
    #     closed_a = ds[ds['oid'] == oid][0]
    #     self.orders['opened']['__ds__'] = ds[ds['oid'] != oid]
    #     #
    #     order['profit'] = closed_a['pf']
    #     if add_closed:
    #         symbol_orders = self.orders['closed'].get(order['symbol'], {})
    #         symbol_orders[oid] = order
    #         self.orders['closed'][order['symbol']] = symbol_orders
    # 
    #     self.orders['opened_counter'] = self.orders['opened_counter'] - 1
    #     #
    # 
    #     return order['uid']
    # 

    def __calculate_profit__(self, cid, price):
        ''''''
        profit = 0
        ods = self.orders['opened'].get('__ds__', None)
        if ods is not None:
            ds = ods[ods['cid'] == cid]
            if len(ds) == 0:
                return 0
            pips = self.__calculate_pip__(price)
            ds['pf'] = pips * (price - ds['o']) * ds['v'] * ds['tcs'] * ds['pf_f']
            ds['sl_p'] = (price - ds['sl']) * ds['pf_f']
            ds['tp_p'] = (price - ds['tp']) * ds['pf_f']
            profit = ds['pf'].sum()
            ods[ods['cid'] == cid] = ds
        return profit

    # def __calculate_profit__(self, price):
    #     ''''''
    #     profit = 0
    #     ds = self.orders['opened'].get('__ds__', None)
    #     if ds is not None:
    #         pips = self.__calculate_pip__(price)
    #         ds['pf'] = pips * (price - ds['o']) * ds['v'] * ds['tcs'] * ds['pf_f']
    #         ds['sl_p'] = (price - ds['sl']) * ds['pf_f']
    #         ds['tp_p'] = (price - ds['tp']) * ds['pf_f']
    #         profit = ds['pf'].sum()
    #     return profit
    #
    #
    def get_order(self, order_uid):
        """Get Order"""
        ret = self.orders['data'].get(order_uid, None)
        #update order data
        oid = int(order_uid)
        ds = self.orders['opened'].get('__ds__', None)
        if ds is not None:
            the_a = ds[ds['oid'] == oid]
            if the_a.size > 0:
                ret['profit'] = the_a[0]['pf']

        return ret

    def get_order_dict(self, symbol, status="opened", scope=DataScope.EA):
        symbol = self.symbol if symbol is None else symbol
        order_list = self.orders.get(status, {})
        if symbol == '*':
            ret = {}
            for s in order_list:
                if not s.startswith('__'):
                    ret.update(order_list[s])
            return ret
        else:
            return order_list.get(symbol, {})

    # def get_order_dict(self, symbol, status="opened", script_name=None):
    #     """"""
    #     symbol = self.symbol if symbol is None else symbol
    #     order_list = self.orders.get(status, {})
    #     return order_list.get(symbol, {})
    #
    def set_order_list(self, symbol, status, value):
        """"""
        self.orders[status][symbol] = value

    def get_account(self, ):
        """"""
        return self.account_info['data_raw'][-1]

    def set_account(self, account, expiration=None):
        """"""
        self.account_info['data_raw'].append(account)
        if self.account_info['__ds__'] is None or self.account_info['__ds__'].get(self.tick_timeframe, None) is None:
            self.get_account_data(self.tick_timeframe)
        #
        account_data = self.account_info['__ds__'][self.tick_timeframe][self.current_tick_index]
        account_data['credit'] = account['credit']
        account_data['balance'] = account['balance']
        account_data['equity'] = account['equity']
        account_data['margin'] = account['margin']
        account_data['free_margin'] = account['free_margin']
        account_data['credit'] = account['credit']
        account_data['profit'] = account['profit']
        account_data['margin_level'] = account['margin_level']
        account_data['commission'] = account['commission']

    def __valid_order__(self, stage, order_dict, price):
        #buy
        ask = self.Ask()
        bid = self.Bid()
        open_price = None
        if stage == 0:
            if order_dict['volume'] <= 0:
                return EID_EAT_INVALID_ORDER_VOLUME
            open_price = order_dict['open_price']
        elif stage == 1:
            open_price = order_dict.get('price', None)

        stop_loss = order_dict.get('stop_loss', 0)
        take_profit = order_dict.get('take_profit', 0)

        if order_is_long(order_dict['cmd']):
            # open
            if stage == 0 or (stage == 1 and order_is_pending(order_dict['cmd'])):
                if order_is_market(order_dict['cmd']):
                    if open_price < ask:
                        return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_limit(order_dict['cmd']):
                    #buy limit
                    if open_price >= ask:
                        return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_stop(order_dict['cmd']):
                    #buy stop
                    if open_price <= ask:
                        return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
                else:
                    return EID_EAT_INVALID_ORDER_TYPE

            #close
            elif stage == 2:
                if price is not None and order_is_market(order_dict['cmd']):
                    if price > 0 and price > bid:
                        return EID_EAT_INVALID_ORDER_CLOSE_PRICE

            if stage != 2:
                if stop_loss > 0 and take_profit > 0 and stop_loss > take_profit:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
                if take_profit > 0 and take_profit <= ask:
                    return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                if stop_loss > 0 and stop_loss >= ask:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
        #sell
        elif order_is_short(order_dict['cmd']):
            # open
            if stage == 0 or (stage == 1 and order_is_pending(order_dict['cmd'])):
                if order_is_market(order_dict['cmd']):
                    if open_price > bid:
                        return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_limit(order_dict['cmd']):
                    #sell limit
                    if open_price <= bid:
                        return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_stop(order_dict['cmd']):
                    #sell stop
                    if open_price >= bid:
                        return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
                else:
                    return EID_EAT_INVALID_ORDER_TYPE
            #close
            elif stage == 2:
                if price is not None and order_is_market(order_dict['cmd']):
                    if price > 0 and price < ask:
                        return EID_EAT_INVALID_ORDER_CLOSE_PRICE

            #
            if stage != 2:
                if stop_loss > 0 and take_profit > 0 and stop_loss < take_profit:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
                if stop_loss > 0 and stop_loss <= bid:
                    return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                if take_profit > 0 and take_profit >= bid:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS

        return EID_OK
    # #
    # def __valid_order__(self, stage, order_dict, price):
    #     #buy
    #     ask = self.Ask()
    #     bid = self.Bid()
    #     open_price = None
    #     if stage == 0:
    #         if order_dict['volume'] <= 0:
    #             return EID_EAT_INVALID_ORDER_VOLUME
    #         open_price = order_dict['open_price']
    #     elif stage == 1:
    #         open_price = order_dict.get('price', None)
    #
    #     stop_loss = order_dict.get('stop_loss', 0)
    #     take_profit = order_dict.get('take_profit', 0)
    #
    #     if order_is_long(order_dict['cmd']):
    #         # open
    #         if stage == 0 or (stage == 1 and order_is_pending(order_dict['cmd'])):
    #             if order_is_market(order_dict['cmd']):
    #                 if open_price < ask:
    #                     return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
    #             elif open_price is not None and order_is_limit(order_dict['cmd']):
    #                 #buy limit
    #                 if open_price >= ask:
    #                     return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
    #             elif open_price is not None and order_is_stop(order_dict['cmd']):
    #                 #buy stop
    #                 if open_price <= ask:
    #                     return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
    #             else:
    #                 return EID_EAT_INVALID_ORDER_TYPE
    #
    #         #close
    #         elif stage == 2:
    #             if price is not None:
    #                 if price > 0 and price > bid:
    #                     return EID_EAT_INVALID_ORDER_CLOSE_PRICE
    #
    #         if stage != 2:
    #             if stop_loss > 0 and take_profit > 0 and stop_loss > take_profit:
    #                 return EID_EAT_INVALID_ORDER_STOP_LOSS
    #             if take_profit > 0 and take_profit <= ask:
    #                 return EID_EAT_INVALID_ORDER_TAKE_PROFIT
    #             if stop_loss > 0 and stop_loss >= ask:
    #                 return EID_EAT_INVALID_ORDER_STOP_LOSS
    #     #sell
    #     elif order_is_short(order_dict['cmd']):
    #         # open
    #         if stage == 0 or (stage == 1 and order_is_pending(order_dict['cmd'])):
    #             if order_is_market(order_dict['cmd']):
    #                 if open_price > bid:
    #                     return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
    #             elif open_price is not None and order_is_limit(order_dict['cmd']):
    #                 #sell limit
    #                 if open_price <= bid:
    #                     return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
    #             elif open_price is not None and order_is_stop(order_dict['cmd']):
    #                 #sell stop
    #                 if open_price >= bid:
    #                     return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
    #             else:
    #                 return EID_EAT_INVALID_ORDER_TYPE
    #         #close
    #         elif stage == 2:
    #             if price is not None:
    #                 if price > 0 and price < ask:
    #                     return EID_EAT_INVALID_ORDER_CLOSE_PRICE
    #
    #         #
    #         if stage != 2:
    #             if stop_loss > 0 and take_profit > 0 and stop_loss < take_profit:
    #                 return EID_EAT_INVALID_ORDER_STOP_LOSS
    #             if stop_loss > 0 and stop_loss <= bid:
    #                 return EID_EAT_INVALID_ORDER_TAKE_PROFIT
    #             if take_profit > 0 and take_profit >= bid:
    #                 return EID_EAT_INVALID_ORDER_STOP_LOSS
    #
    #     return EID_OK
    # #

    def __new_ticket__(self):
        return str(self.orders['counter'] + 1)

    def open_order(self, symbol, cmd, price, volume, stop_loss, take_profit, comment=None, ext_check_open_range=0,
                       ext_check_order_hold_count=0, magic_number=None, slippage=None, arrow_color=None, tags=None):
        """"""
        order_uid = None
        account = self.account
        if self.orders['opened_counter'] >= account['limit_orders']:
            return EID_EAT_LIMIT_ORDERS, None
        if stop_loss is None:
            stop_loss = 0.0
        if take_profit is None:
            take_profit = 0.0
        volume = round(volume, self.volume_precision)
        order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=cmd, open_price=price,
                         volume=volume, stop_loss=stop_loss, take_profit=take_profit, margin=0, comment=comment,
                         magic_number=magic_number, open_time=self.current_time(), commission=0,
                         close_time=None, close_price=np.nan, profit=0.0, tags=tags, dirty=False)
        errid = self.__valid_order__(0, order_dict, None)
        if errid != EID_OK:
            return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        #
        if order_is_market(order_dict['cmd']):
            errid, order_uid = self.__add_market_order__(order_dict)
        else:
            errid, order_uid = self.__add_pending_order__(order_dict)
        if errid != EID_OK:
            return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        #add order log
        self.add_order_log(dict(uid=order_uid, ticket=order_dict['ticket'],
                                 time=str(datetime.fromtimestamp(order_dict['open_time'])),
                                 type=cmd, volume=volume,
                                 price=round(price, self.price_digits),
                                 stop_loss=round(stop_loss, self.price_digits),
                                 take_profit=round(take_profit, self.price_digits),
                                 comment=order_dict['comment'], tags=order_dict['tags'],
                                 balance=None, profit=None))


        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)
    #

    def modify_order(self, order_uid, price, stop_loss, take_profit, comment=None, arrow_color=None,
                     expiration=None, tags=None):
        """modify_order"""
        order_dict = self.get_order(order_uid=order_uid)
        if order_dict is None:
            return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, command_uid=None, sync=True)
        if order_dict['symbol'] != self.symbol:
            return EID_EAT_INVALID_SYMBOL, dict(order_uid=order_uid, command_uid=None, sync=True)
        order_tmp = order_dict.copy()
        if stop_loss is not None:
            order_tmp['stop_loss'] = stop_loss
        if take_profit is not None:
            order_tmp['take_profit'] = take_profit
        order_tmp['comment'] = comment
        if tags is not None:
            order_tmp['tags'] = tags
        #
        close_price = self.Close()
        if order_is_market(order_dict['cmd']):
            if price is None:
                price = close_price
            #
        else:
            if price is None:
                price = close_price
            else:
                order_tmp['price'] = price
                order_tmp['open_price'] = price
        #
        errid = self.__valid_order__(1, order_tmp, None)
        if errid != EID_OK:
            return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        #
        order_dict['open_price'] = order_tmp['open_price']
        if 'stop_loss' in order_tmp:
            order_dict['stop_loss'] = order_tmp['stop_loss']
        if 'take_profit' in order_tmp:
            order_dict['take_profit'] = order_tmp['take_profit']
        order_dict['comment'] = order_tmp['comment']
        order_dict['dirty'] = False
        self.__modify_order__(order_dict)

        #
        order_log = dict(uid=order_uid, ticket=order_dict['ticket'],
                                 time=str(datetime.fromtimestamp(self.current_time())),
                                 type="MODIFY",
                                 volume=order_dict['volume'], price=round(price, self.price_digits),
                                 # stop_loss=round(stop_loss, self.price_digits),
                                 # take_profit=round(take_profit, self.price_digits),
                                 profit=round(order_dict['profit'], self.default_digits),
                                 balance=round(self.account["balance"] + order_dict['profit'], self.default_digits),
                                 comment=comment, tags=tags)
        if stop_loss is not None:
            order_log['stop_loss'] = round(stop_loss, self.price_digits)
        if take_profit is not None:
            order_log['take_profit'] = round(take_profit, self.price_digits)
        self.add_order_log(order_log)
        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)
    #
    # def modify_order(self, order_uid, price, stop_loss, take_profit, comment=None, arrow_color=None,
    #                  expiration=None):
    #     """"""
    #     order_dict = self.get_order(order_uid=order_uid)
    #     if order_dict is None:
    #         return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     if order_dict['symbol'] != self.symbol:
    #         return EID_EAT_INVALID_SYMBOL, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     order_tmp = order_dict.copy()
    #     order_tmp['stop_loss'] = stop_loss
    #     order_tmp['take_profit'] = take_profit
    #     order_tmp['comment'] = comment
    #     #
    #     close_price = self.Close()
    #     if order_is_market(order_dict['cmd']):
    #         if price is None:
    #             price = close_price
    #         #
    #     else:
    #         if price is None:
    #             price = close_price
    #         else:
    #             order_tmp['price'] = price
    #             order_tmp['open_price'] = price
    #     #
    #     errid = self.__valid_order__(1, order_tmp, close_price)
    #     if errid != EID_OK:
    #         return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     #
    #     order_dict['open_price'] = order_tmp['open_price']
    #     order_dict['stop_loss'] = order_tmp['stop_loss']
    #     order_dict['take_profit'] = order_tmp['take_profit']
    #     order_dict['comment'] = order_tmp['comment']
    #     self.__modify_order__(order_dict)
    #
    #     #
    #     self.add_order_log(dict(uid=order_uid, ticket=order_dict['ticket'],
    #                              time=str(datetime.fromtimestamp(self.current_time())),
    #                              type="MODIFY",
    #                              volume=order_dict['volume'], price=round(price, self.price_digits),
    #                              stop_loss=round(stop_loss, self.price_digits),
    #                              take_profit=round(take_profit, self.price_digits),
    #                              profit=round(order_dict['profit'], self.default_digits),
    #                              balance=round(self.account["balance"] + order_dict['profit'], self.default_digits),
    #                              comment=comment))
    #     return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)

    def __order_close_price__(self, order_dict):
        if order_is_market(order_dict['cmd']):
            return self.Bid() if order_is_long(order_dict['cmd']) else self.Ask()
        else:
            return 0

    def __close_order__(self, order_uid, volume, price, slippage=None, comment=None, arrow_color=None,
                    update_report_func=None, tags=None):
        """Close order"""
        close_time = self.current_time()
        order_dict = self.get_order(order_uid=order_uid)
        if order_dict is None or order_dict.get('close_time', None) is not None:
            return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                                      close_time=close_time)
        # if volume is None:
        #     return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
        if volume is None or volume <= 0:
            volume = float(order_dict['volume'])
        else:
            volume = round(volume, self.volume_precision)
        if price is None or price <= 0:
            price = self.__order_close_price__(order_dict)
        #
        if order_is_market(order_dict['cmd']):
            symbol = order_dict['symbol']
            if volume > order_dict['volume']:
                return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                                          close_time=close_time)
            #
            errid = self.__valid_order__(2, order_dict, price)
            if errid != EID_OK:
                return errid, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                   close_time=close_time)
            if tags is not None:
                order_dict['tags'] = tags
            order_dict['dirty'] = False
            order_dict['comment'] = comment
            order_dict['close_time'] = close_time
            order_dict['close_price'] = price
            order_dict['status'] = OrderStatus.CLOSED
            order_uid = self.__remove_order__(order_dict)
            self.account["balance"] = self.account["balance"] + order_dict['profit']
            closed_margin = round(order_dict['margin'] * volume / order_dict['volume'], self.default_digits)
            self.account["margin"] = round(self.account["margin"] - closed_margin, self.default_digits)
            # self.account["margin"] = self.account["margin"] - closed_margin
            new_margin = order_dict['margin'] - closed_margin
            new_volume = order_dict['volume'] - volume
        #
            #report
            if update_report_func:
                update_report_func(order_is_long(order_dict['cmd']), order_dict['profit'], 1)
            else:
                self.__update_report__(order_is_long(order_dict['cmd']), order_dict['profit'])

            #
            if new_volume > 0:
                new_order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=order_dict['cmd'], open_price=price,
                                  volume=new_volume, stop_loss=order_dict['stop_loss'],
                                  take_profit=order_dict['take_profit'], margin=new_margin,
                                  comment=f"close by#{order_dict['ticket']}",
                                  open_time=close_time)
                errid, order_uid = self.__add_market_order__(new_order_dict)
                if errid != EID_OK:
                    return errid, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                       close_time=close_time)
        else:
            order_dict['status'] = OrderStatus.CANCELLED
            order_uid = self.__remove_pending_order__(order_dict)

        return EID_OK, dict(order_uid=order_uid, order_dict=order_dict, close_price=price, close_time=close_time)
    #
    # def __close_order__(self, order_uid, volume, price, slippage=None, comment=None, arrow_color=None,
    #                 update_report_func=None, tags=None):
    #     """Close order"""
    #     order_dict = self.get_order(order_uid=order_uid)
    #     if order_dict is None:
    #         return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     # if volume is None:
    #     #     return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     if volume is None or volume <= 0:
    #         volume = float(order_dict['volume'])
    #     if price is None or price <= 0:
    #         price = self.__order_close_price__(order_dict)
    #     #
    #     close_time = self.current_time()
    #     if order_is_market(order_dict['cmd']):
    #         symbol = order_dict['symbol']
    #         if volume > order_dict['volume']:
    #             return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
    #         #
    #         errid = self.__valid_order__(2, order_dict, price)
    #         if errid != EID_OK:
    #             return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
    #         if tags is not None:
    #             order_dict['tags'] = tags
    #         order_dict['dirty'] = False
    #         order_dict['comment'] = comment
    #         order_dict['close_time'] = close_time
    #         order_dict['close_price'] = price
    #         order_uid = self.__remove_order__(order_dict)
    #         self.account["balance"] = self.account["balance"] + order_dict['profit']
    #         closed_margin = order_dict['margin'] * volume / order_dict['volume']
    #         self.account["margin"] = self.account["margin"] - closed_margin
    #         new_margin = order_dict['margin'] - closed_margin
    #         new_volume = order_dict['volume'] - volume
    #     #
    #         #report
    #         if update_report_func:
    #             update_report_func(order_is_long(order_dict['cmd']), order_dict['profit'], 1)
    #         else:
    #             self.__update_report__(order_is_long(order_dict['cmd']), order_dict['profit'])
    #
    #         #
    #         if new_volume > 0:
    #             new_order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=order_dict['cmd'], open_price=price,
    #                               volume=new_volume, stop_loss=order_dict['stop_loss'],
    #                               take_profit=order_dict['take_profit'], margin=new_margin,
    #                               comment=f"close by#{order_dict['ticket']}",
    #                               open_time=close_time)
    #             errid, order_uid = self.__add_market_order__(new_order_dict)
    #             if errid != EID_OK:
    #                 return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
    #     else:
    #         order_uid = self.__remove_pending_order__(order_dict)
    #
    #     #
    #     self.add_order_log(dict(uid=order_dict['uid'], ticket=order_dict['ticket'],
    #                                 time=str(datetime.fromtimestamp(close_time)),
    #                                 type="CLOSE", volume=order_dict['volume'],
    #                                 price=round(price, self.price_digits),
    #                                 stop_loss=round(order_dict['stop_loss'], self.price_digits),
    #                                 take_profit=round(order_dict['take_profit'], self.price_digits),
    #                                 balance=round(self.account["balance"], self.default_digits),
    #                                 profit=round(order_dict['profit'], self.default_digits),
    #                                 comment=order_dict['comment'], tags=order_dict['tags']))
    #
    #     return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)


    def close_order(self, order_uid, volume, price, slippage=None, comment=None, arrow_color=None,
                    update_report_func=None, tags=None):
        """Close order"""
        errid, ret = self.__close_order__(order_uid, volume, price, slippage=slippage, comment=comment, arrow_color=arrow_color,
                    update_report_func=update_report_func, tags=tags,)
        if errid != EID_OK:
            return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        order_dict = ret['order_dict']
        close_time = ret['close_time']
        close_price = ret['close_price']
        #
        self.add_order_log(dict(uid=order_dict['uid'], ticket=order_dict['ticket'],
                                    time=str(datetime.fromtimestamp(close_time)),
                                    type="CLOSE", volume=order_dict['volume'],
                                    price=round(close_price, self.price_digits),
                                    stop_loss=round(order_dict['stop_loss'], self.price_digits),
                                    take_profit=round(order_dict['take_profit'], self.price_digits),
                                    balance=round(self.account["balance"], self.default_digits),
                                    profit=round(order_dict['profit'], self.default_digits),
                                    comment=order_dict['comment'], tags=order_dict['tags']))

        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)

    def close_multi_orders(self, orders):
        """Close multi orders"""
        ret = {}
        multi_info = []
        if isinstance(orders, list):
            for order_uid in orders:
                order_dict = self.get_order(order_uid)
                if order_dict is None:
                    errid = EID_EAT_INVALID_ORDER_TICKET
                else:
                    multi_info.append(dict(order_id=order_dict['ticket'], order_uid=order_uid))
                    errid = EID_OK
                ret[order_uid] = dict(errid=errid)
        elif isinstance(orders, dict):
            for order_uid in orders:
                order_dict = self.get_order(order_uid)
                if order_dict is None:
                    errid = EID_EAT_INVALID_ORDER_TICKET
                else:
                    errid = EID_OK
                    info = orders[order_uid]
                    price = info.get('price', None)
                    volume = info.get('volume', float(order_dict['volume']))
                    slippage = info.get('slippage', None)
                    comment = info.get('comment', None)
                    tags = info.get('tags', None)
                    arrow_color = info.get('arrow_color', None)
                    #
                    order_params = {'order_id': order_dict['ticket'],
                                    'volume': volume,
                                    'order_uid': order_uid,
                                    }
                    if price is not None and isinstance(price, float):
                        order_params['close_price'] = price
                    if comment is not None and isinstance(comment, str):
                        order_params['comment'] = comment
                    if tags is not None and isinstance(tags, dict):
                        order_params['tags'] = tags
                    if slippage is not None:
                        order_params['slippage'] = slippage
                    if arrow_color is not None and isinstance(arrow_color, str):
                        order_params['arrow_color'] = arrow_color
                    multi_info.append(order_params)
                ret[order_uid] = dict(errid=errid)
        else:
            return EID_EAT_ERROR, None

        result = {}
        for mi in multi_info:
            errid, ret = self.__close_order__(mi['order_uid'], mi.get('volume', 0),
                                              mi.get('close_price', 0), slippage=mi.get('slippage', None),
                                              comment=mi.get('comment', None),
                                              arrow_color=mi.get('arrow_color', None),
                                              tags=mi.get('tags', None))
            result[mi['order_uid']] = dict(errid=errid, ret=ret)
            if errid != EID_OK:
                # return errid, dict(orders=orders, command_uid=None, sync=True)
                pass
            else:
                order_dict = ret['order_dict']
                close_time = ret['close_time']
                close_price = ret['close_price']
                #
                self.add_order_log(dict(uid=order_dict['uid'], ticket=order_dict['ticket'],
                                            time=str(datetime.fromtimestamp(close_time)),
                                            type="CLOSE_MULTI_ORDERS", volume=order_dict['volume'],
                                            price=round(close_price, self.price_digits),
                                            stop_loss=round(order_dict['stop_loss'], self.price_digits),
                                            take_profit=round(order_dict['take_profit'], self.price_digits),
                                            balance=round(self.account["balance"], self.default_digits),
                                            profit=round(order_dict['profit'], self.default_digits),
                                            comment=order_dict['comment'], tags=order_dict['tags']))

        return EID_OK, dict(result=result, command_uid=None, sync=True)

    def wait_command(self, uid, timeout=120):
        return 0, {}

    def acquire_lock(self, name, timeout=60):
        return True

    def release_lock(self, name):
        pass

    def notify(self, message):
        self.print_logs.append(f"<Notification>: {message}\n")

    #
    def Ask(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        ask = self.tick_info['a'][self.current_tick_index - shift]
        if ask == 0:
            ask = self.Bid(shift) + self.spread_calculated
        return ask

    def Bid(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        bid = self.tick_info['b'][self.current_tick_index - shift]
        if bid == 0:
            bid = self.Close(shift)
        return bid

    def Close(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        return self.tick_info['c'][self.current_tick_index - shift]

    def Open(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        return self.tick_info['o'][self.current_tick_index - shift]

    def High(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        return self.tick_info['h'][self.current_tick_index - shift]

    def Low(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.symbol:
            return None
        return self.tick_info['l'][self.current_tick_index - shift]

    def Time(self, shift=0, symbol=None) -> datetime:
        if symbol is not None and symbol != self.symbol:
            return None
        return datetime.fromtimestamp(self.tick_info['t'][self.current_tick_index - shift])

    def Volume(self, shift=0, symbol=None) -> float:
        if symbol is not None and symbol != self.symbol:
            return None
        return self.tick_info['v'][self.current_tick_index - shift]
    #
    def __update_report_max_dd__(self):
        #calculate maxdd: https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp
        if self.temp['account_min_equity'] < self.report['init_balance']['value']:
            self.temp['max_drawdown'] = self.temp['account_min_equity'] - self.temp['account_max_equity']
        if self.temp['account_max_equity'] > 0:
            self.temp['max_drawdown_rate'] = self.temp['max_drawdown'] / self.temp['account_max_equity']
        else:
            self.temp['max_drawdown_rate'] = 0
        #
        if self.report['max_drawdown']['value'] > self.temp['max_drawdown']:
            self.report['max_drawdown']['value'] = self.temp['max_drawdown']
            self.report['max_drawdown_rate']['value'] = self.temp['max_drawdown_rate']

    def __update_report__(self, is_long, profit, trades=1):
        if profit == 0:
            return
        profit = round(profit, self.default_digits)
        if profit > 0:
            self.report['profit_trades']['value'] += trades
            self.report['gross_profit']['value'] = self.report['gross_profit']['value'] + profit
            self.report['trade_avg_profit']['value'] = self.report['gross_profit']['value'] / \
                                                       self.report['profit_trades']['value']

            if self.report['trade_max_profit']['value'] < profit:
                self.report['trade_max_profit']['value'] = profit
            if is_long:
                self.report['long_positions_win']['value'] += trades
            else:
                self.report['short_positions_win']['value'] += trades

            self.temp['consecutive_wins'] += trades
            self.temp['consecutive_wins_money'] = self.temp['consecutive_wins_money'] + profit
            self.temp['consecutive_losses'] = 0
            self.temp['consecutive_losses_money'] = 0
            #self.account['currency']
        else:
            self.report['loss_trades']['value'] += trades
            self.report['gross_loss']['value'] = self.report['gross_loss']['value'] + profit
            self.report['trade_avg_loss']['value'] = self.report['gross_loss']['value'] / self.report['loss_trades'][
                'value']

            if np.isnan(self.report['trade_max_loss']['value']) or self.report['trade_max_loss']['value'] > profit:
                self.report['trade_max_loss']['value'] = profit

            self.temp['consecutive_losses'] += trades
            self.temp['consecutive_losses_money'] = self.temp['consecutive_losses_money'] + profit
            self.temp['consecutive_wins'] = 0
            self.temp['consecutive_wins_money'] = 0
            #
        #
        #max dd
        if self.temp['account_max_equity'] < self.account['equity']:
            # #calculate maxdd: https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp
            self.__update_report_max_dd__()
            #
            self.temp['account_max_equity'] = self.account['equity']
            self.temp['account_min_equity'] = self.account['equity']
        else:
            if self.temp['account_min_equity'] > self.account['equity']:
                self.__update_report_max_dd__()
                self.temp['account_min_equity'] = self.account['equity']
        #

        #
        if self.temp['account_min_balance'] > self.account['balance']:
            self.temp['account_min_balance'] = self.account['balance']
            self.report['absolute_drawdown']['value'] = self.temp['account_min_balance'] - self.report['init_balance']['value']

        #
        # self.report['max_drawdown']['value'] = self.temp['account_max_equity'] - self.temp['account_min_equity']
        # if self.temp['account_max_equity'] > 0:
        #     self.report['max_drawdown_rate']['value'] = self.report['max_drawdown']['value'] / self.temp['account_max_equity']
        # else:
        #     self.report['max_drawdown_rate']['value'] = 0
        if self.report['max_consecutive_wins']['value'] < self.temp['consecutive_wins']:
            self.report['max_consecutive_wins']['value'] = self.temp['consecutive_wins']
        if self.report['max_consecutive_wins_money']['value'] < self.temp['consecutive_wins_money']:
            self.report['max_consecutive_wins_money']['value'] = self.temp['consecutive_wins_money']
        if self.report['max_consecutive_losses']['value'] < self.temp['consecutive_losses']:
            self.report['max_consecutive_losses']['value'] = self.temp['consecutive_losses']
        if self.report['max_consecutive_losses_money']['value'] > self.temp['consecutive_losses_money']:
            self.report['max_consecutive_losses_money']['value'] = self.temp['consecutive_losses_money']
        self.report['total_net_profit']['value'] = self.report['gross_profit']['value'] - abs(
            self.report['gross_loss']['value'])
        #
        if self.report['total_trades']['value'] > 0:
            self.report['win_rate']['value'] = self.report['profit_trades']['value'] / self.report['total_trades']['value']
        #Total net profit rate
        if self.report['init_balance']['value'] > 0:
            self.report['total_net_profit_rate']['value'] = self.report['total_net_profit']['value'] / self.report['init_balance']['value']
        self.report['balance']['value'] = self.account['balance']
        #
        self.report['sharpe_ratio']['value'] = self.calculate_sharpe_ratio()

    # def __update_report__(self, is_long, profit, trades=1):
    #     if profit == 0:
    #         return
    #     profit = round(profit, self.default_digits)
    #     if profit > 0:
    #         self.report['profit_trades']['value'] += trades
    #         self.report['gross_profit']['value'] = self.report['gross_profit']['value'] + profit
    #         self.report['trade_avg_profit']['value'] = self.report['gross_profit']['value'] / \
    #                                                    self.report['profit_trades']['value']
    #
    #         if self.report['trade_max_profit']['value'] < profit:
    #             self.report['trade_max_profit']['value'] = profit
    #         if is_long:
    #             self.report['long_positions_win']['value'] += trades
    #         else:
    #             self.report['short_positions_win']['value'] += trades
    #
    #         self.temp['consecutive_wins'] += trades
    #         self.temp['consecutive_wins_money'] = self.temp['consecutive_wins_money'] + profit
    #         self.temp['consecutive_losses'] = 0
    #         self.temp['consecutive_losses_money'] = 0
    #         #self.account['currency']
    #     else:
    #         self.report['loss_trades']['value'] += trades
    #         self.report['gross_loss']['value'] = self.report['gross_loss']['value'] + profit
    #         self.report['trade_avg_loss']['value'] = self.report['gross_loss']['value'] / self.report['loss_trades'][
    #             'value']
    #
    #         if np.isnan(self.report['trade_max_loss']['value']) or self.report['trade_max_loss']['value'] > profit:
    #             self.report['trade_max_loss']['value'] = profit
    #
    #         self.temp['consecutive_losses'] += trades
    #         self.temp['consecutive_losses_money'] = self.temp['consecutive_losses_money'] + profit
    #         self.temp['consecutive_wins'] = 0
    #         self.temp['consecutive_wins_money'] = 0
    #         #
    #     #
    #     #
    #     if self.temp['account_max_equity'] < self.account['equity']:
    #         self.temp['account_max_equity'] = self.account['equity']
    #     if self.temp['account_min_equity'] > self.account['equity']:
    #         self.temp['account_min_equity'] = self.account['equity']
    #     #
    #     self.report['max_drawdown']['value'] = self.temp['account_max_equity'] - self.temp['account_min_equity']
    #     if self.temp['account_max_equity'] > 0:
    #         self.report['max_drawdown_rate']['value'] = self.report['max_drawdown']['value'] / self.temp['account_max_equity']
    #     else:
    #         self.report['max_drawdown_rate']['value'] = 0
    #     if self.report['max_consecutive_wins']['value'] < self.temp['consecutive_wins']:
    #         self.report['max_consecutive_wins']['value'] = self.temp['consecutive_wins']
    #     if self.report['max_consecutive_wins_money']['value'] < self.temp['consecutive_wins_money']:
    #         self.report['max_consecutive_wins_money']['value'] = self.temp['consecutive_wins_money']
    #     if self.report['max_consecutive_losses']['value'] < self.temp['consecutive_losses']:
    #         self.report['max_consecutive_losses']['value'] = self.temp['consecutive_losses']
    #     if self.report['max_consecutive_losses_money']['value'] > self.temp['consecutive_losses_money']:
    #         self.report['max_consecutive_losses_money']['value'] = self.temp['consecutive_losses_money']
    #     self.report['total_net_profit']['value'] = self.report['gross_profit']['value'] - abs(
    #         self.report['gross_loss']['value'])
    #     if self.report['total_net_profit']['value'] < 0:
    #         self.report['absolute_drawdown']['value'] = abs(self.report['total_net_profit']['value'])
    #     #
    #     if self.report['total_trades']['value'] > 0:
    #         self.report['win_rate']['value'] = self.report['profit_trades']['value'] / self.report['total_trades']['value']
    #     #Total net profit rate
    #     if self.report['init_balance']['value'] > 0:
    #         self.report['total_net_profit_rate']['value'] = self.report['total_net_profit']['value'] / self.report['init_balance']['value']
    #

    def __calculate_pip_with_quote_currency__(self, price):
        return 1.0

    def __calculate_pip_with_base_currency__(self, price):
        return 1.0 / price

    def import_module(self, name, target):
        # get a handle on the module
        mdl = importlib.import_module(name)

        # is there an __all__?  if so respect it
        if "__all__" in mdl.__dict__:
            names = mdl.__dict__["__all__"]
        else:
            # otherwise we import all names that don't begin with _
            names = [x for x in mdl.__dict__ if not x.startswith("_")]

        # now drag them in
        target.update({k: getattr(mdl, k) for k in names})
        #

    def stop_tester(self, code: int=0, message: str=None):
        self.stop = True

    def init_data(self):
        """EATester"""
        self.loc = {}
        self.import_module('pixiu.api.errors', self.safe_globals)
        self.current_api.set_fun(self.safe_globals)
        #
        for k in self.global_values:
            self.safe_globals[k] = self.global_values[k]
        #
        #clear print collection
        self.print_collection = None
        self.account_info = {'data_raw': [], '__ds__': None}
        self.price_info = {}
        self.symbol_data = {}
        self.current_tick_index = 0
        self.update_log_time = 0
        self.update_charts_time = 0
        self.last_update_order_log_index = 0
        self.last_update_account_log_index = 0
        self.last_update_print_log_index = 0
        self.last_update_charts_data_index = 0
        self.cache = {}
        #
        self.order_logs = []
        self.account_logs = []
        self.print_logs = []
        self.symbol_properties = {}
        self.tick_info = None
        self.orders = {'opened': {}, 'closed': {}, 'pending': {},
                       'counter': 0, 'opened_counter': 0, 'pending_counter': 0,
                       '__ds__': {},
                       'stop_loss': {True: {self.symbol: {'data': {}, 'min': 0, 'max': 0}},
                                     False: {self.symbol: {'data': {}, 'min': 0, 'max': 0}}},
                       'take_profit': {True: {self.symbol: {'data': {}, 'min': 0, 'max': 0}},
                                       False: {self.symbol: {'data': {}, 'min': 0, 'max': 0}}},
                       'data': {}
                       }
        self.sid = {self.symbol: 0}
        self.sid_data = {0: self.symbol}
        self.cid = {OrderCommand.BUY: 100, OrderCommand.SELL: 200,
                    OrderCommand.BUYLIMIT: 110, OrderCommand.SELLLIMIT: 210,
                    OrderCommand.BUYSTOP: 120, OrderCommand.SELLSTOP: 220,
                    }
        self.cid_data = {100: OrderCommand.BUY, 200: OrderCommand.SELL}
        sp = self.get_symbol_properties(self.symbol)
        if self.spread_point is None:
            self.spread_point = int(sp['spread'])
        self.price_digits = int(sp['digits'])
        self.volume_precision = int(math.log10(1/sp['volume_min']))
        self.spread_calculated = abs(self.spread_point * sp['point'])
        #
        if self.account['currency'] is None:
            self.account['currency'] = sp['currency_profit'].upper()
        #
        if self.account['currency'].upper() == sp['currency_base'].upper():
            self.__calculate_pip__ = self.__calculate_pip_with_base_currency__
        else:
            self.__calculate_pip__ = self.__calculate_pip_with_quote_currency__
        self.stop = False
        #
        self.init_report_data()

    def get_symbol_properties(self, symbol):
        ''''''
        return self.symbol_properties.get(symbol, self.default_symbol_properties[symbol])

    def calculate_margin_level(self):
        if self.account['margin'] == 0:
            return 0
        margin_level = self.account['equity'] / self.account['margin']
        return margin_level

    def __check_equity__(self, ):
        margin_level = self.calculate_margin_level()
        if margin_level == 0:
            return True, None
        if self.account['margin_so_so'] >= margin_level:
            # so: 91.1%/6.8/7.5
            # 91.1%, your equity at 6.8$ and your margin at 7.5$.
            comment = f"so: {round(margin_level*100, 1)}%/{self.account['equity']}/{self.account['margin']}"
            self.write_log(f"Stop Out: {comment}")
            return False, comment
        if self.account['margin_so_call'] >= margin_level:
            self.write_log(f"Margin Call: {round(margin_level*100, 1)}%/{self.account['equity']}/{self.account['margin']}")
            return True, None
        return True, None
    #
    def __process_order__(self, price, last_price, ask, last_ask, bid, last_bid):
        ''''''
        comment = None
        dead = 0
        # equity
        profit_buy = self.__calculate_profit__(100, bid)
        profit_sell = self.__calculate_profit__(200, ask)
        profit = profit_buy + profit_sell
        self.account['profit'] = profit
        # account
        check_next = True
        while check_next:
            ret, comment = self.__check_equity__()
            if ret:
                break
            symbol_orders = self.get_order_dict(self.symbol)
            check_next = False
            for order_uid in symbol_orders:
                order_dict = self.get_order(order_uid=order_uid)
                if not order_is_market(order_dict['cmd']):
                    continue
                errid, ret =self.close_order(order_uid, order_dict['volume'], 0, comment=comment)
                if errid == EID_OK:
                    check_next = True
                    break

        if self.account['balance'] <= self.balance_dead_line:
            dead = 1
            comment = "dead"
        elif self.account['balance'] + profit - self.account['margin'] <= self.balance_dead_line:
            dead = 2
            comment = "margin"

        if dead > 0:
            # self.close_all_orders(price, comment=comment)
            self.close_all_orders(0, comment=comment)
            return dead

        #update pending orders
        ds = self.orders['pending'].get('__ds__', None)
        if ds is not None:
            # if last_price is not None:
            #110-BUYLIMIT, 120-BUYSTOP, 210-SELLLIMIT, 220-SELLSTOP
            try:
                result = ds[((ds['cid'] == 110) & (last_ask > ds['o']) & (ds['o'] >= ask )) |
                            ((ds['cid'] == 210) & (last_bid < ds['o']) & (ds['o'] <= bid )) |
                            ((ds['cid'] == 120) & (last_ask < ds['o']) & (ds['o'] <= ask )) |
                            ((ds['cid'] == 220) & (last_bid > ds['o']) & (ds['o'] >= bid ))
                            ]
                # result = ds[((ds['cid'] == 110) & (last_price > ds['o']) & (ds['o'] >= price )) |
                #             ((ds['cid'] == 210) & (last_price < ds['o']) & (ds['o'] <= price )) |
                #             ((ds['cid'] == 120) & (last_price < ds['o']) & (ds['o'] <= price )) |
                #             ((ds['cid'] == 220) & (last_price > ds['o']) & (ds['o'] >= price ))
                #             ]
                for r in result:
                    self.__active_pending_order__(str(r['oid']), price, comment='open')
            except:
                traceback.print_exc()

        #update opened orders
        order_report = {True: dict(profit=0.0, trades=0), False: dict(profit=0.0, trades=0)}

        def update_report_func(is_long, profit, trades):
            order_report[is_long]['profit'] += profit
            order_report[is_long]['trades'] += trades

        ds = self.orders['opened'].get('__ds__', None)
        if ds is not None:
            # result = ds[(ds['sl_p'] <= 0) | (ds['tp_p'] >= 0)]
            result = ds[((ds['sl'] > 0) & (ds['sl_p'] <= 0)) | ((ds['tp'] > 0) & (ds['tp_p'] >= 0))]
            for r in result:
                self.close_order(str(r['oid']), r['v'], None,
                                 comment='sl' if r['sl_p'] <= 0 else 'tp',
                                 update_report_func=update_report_func)
                # self.close_order(str(r['oid']), r['v'], price,
                #                  comment='sl' if r['sl_p'] <= 0 else 'tp',
                #                  update_report_func=update_report_func)

        #update reports
        for key in order_report:
            self.__update_report__(key, order_report[key]['profit'], order_report[key]['trades'])

        return dead
    # #
    # def __process_order__(self, price, last_price, ask, last_ask, bid, last_bid):
    #     ''''''
    #     comment = None
    #     dead = 0
    #     # equity
    #     profit_buy = self.__calculate_profit__(100, bid)
    #     profit_sell = self.__calculate_profit__(200, ask)
    #     profit = profit_buy + profit_sell
    #     self.account['profit'] = profit
    #     # account
    #     if self.account['balance'] <= self.balance_dead_line:
    #         dead = 1
    #         comment = "dead"
    #     elif self.account['balance'] + profit - self.account['margin'] <= self.balance_dead_line:
    #         dead = 2
    #         comment = "margin"
    #
    #     if dead > 0:
    #         self.close_all_orders(price, comment=comment)
    #         return dead
    #
    #     #update pending orders
    #     ds = self.orders['pending'].get('__ds__', None)
    #     if ds is not None:
    #         # if last_price is not None:
    #         #110-BUYLIMIT, 120-BUYSTOP, 210-SELLLIMIT, 220-SELLSTOP
    #         try:
    #             result = ds[((ds['cid'] == 110) & (last_ask > ds['o']) & (ds['o'] >= ask )) |
    #                         ((ds['cid'] == 210) & (last_bid < ds['o']) & (ds['o'] <= bid )) |
    #                         ((ds['cid'] == 120) & (last_ask < ds['o']) & (ds['o'] <= ask )) |
    #                         ((ds['cid'] == 220) & (last_bid > ds['o']) & (ds['o'] >= bid ))
    #                         ]
    #             # result = ds[((ds['cid'] == 110) & (last_price > ds['o']) & (ds['o'] >= price )) |
    #             #             ((ds['cid'] == 210) & (last_price < ds['o']) & (ds['o'] <= price )) |
    #             #             ((ds['cid'] == 120) & (last_price < ds['o']) & (ds['o'] <= price )) |
    #             #             ((ds['cid'] == 220) & (last_price > ds['o']) & (ds['o'] >= price ))
    #             #             ]
    #             for r in result:
    #                 self.__active_pending_order__(str(r['oid']), price, comment='open')
    #         except:
    #             traceback.print_exc()
    #
    #     #update opened orders
    #     order_report = {True: dict(profit=0.0, trades=0), False: dict(profit=0.0, trades=0)}
    #
    #     def update_report_func(is_long, profit, trades):
    #         order_report[is_long]['profit'] += profit
    #         order_report[is_long]['trades'] += trades
    #
    #     ds = self.orders['opened'].get('__ds__', None)
    #     if ds is not None:
    #         # result = ds[(ds['sl_p'] <= 0) | (ds['tp_p'] >= 0)]
    #         result = ds[((ds['sl'] > 0) & (ds['sl_p'] <= 0)) | ((ds['tp'] > 0) & (ds['tp_p'] >= 0))]
    #         for r in result:
    #             self.close_order(str(r['oid']), r['v'], None,
    #                              comment='sl' if r['sl_p'] <= 0 else 'tp',
    #                              update_report_func=update_report_func)
    #             # self.close_order(str(r['oid']), r['v'], price,
    #             #                  comment='sl' if r['sl_p'] <= 0 else 'tp',
    #             #                  update_report_func=update_report_func)
    #
    #     #update reports
    #     for key in order_report:
    #         self.__update_report__(key, order_report[key]['profit'], order_report[key]['trades'])
    #
    #     return dead

    #
    def close_all_orders(self, price, comment):
        ''''''
        symbol_orders = self.get_order_dict(self.symbol).copy()
        for order_uid in symbol_orders:
            order_dict = self.get_order(order_uid=order_uid)
            self.close_order(order_uid, order_dict['volume'], price, comment=comment)
    #
    def calculate_sharpe_ratio(self):
        count = len(self.account_logs)
        if count == 0:
            return 0.0
        mean = 0.0
        for al in self.account_logs:
            mean += al['balance']
        mean = mean / count
        std = 0.0
        for al in self.account_logs:
            std += math.pow(al['balance'] - mean, 2)
        std = std / count
        sharpe_ratio = (mean - self.report['init_balance']['value']) / std if std > 0 else 0.0
        # sharpe_ratio = math.sqrt(count) * sharpe_ratio
        return sharpe_ratio


    def __update_account_log(self, ticket):
        ''''''
        price = self.Close()

        time = self.current_time()
        balance = round(self.account['balance'], self.default_digits)
        margin = round(self.account['margin'], self.default_digits)
        profit = self.account['profit']
        equity = round(balance + profit, self.default_digits)
        self.account['equity'] = equity
        free_margin = round(equity - margin, self.default_digits)
        self.account['free_margin'] = free_margin
        # see: https://www.mql5.com/en/forum/46654
        # Margin level percentage = Equity/Margin * 100 %
        if margin != 0:
            # self.account['margin_level'] = round(equity / margin * 100, self.default_digits)
            self.account['margin_level'] = round((equity - margin) / margin * 100, self.default_digits)

        self.add_account_log(dict(time=str(datetime.fromtimestamp(time)), balance=balance, margin=margin,
                                   equity=equity, free_margin=free_margin,
                                   profit=profit))

        self.add_print_log()

    def last_price_time(self, symbol):
        if symbol == self.symbol:
            return self.current_time()
        #
        serials = self.get_data_series(symbol)
        if serials is None or len(serials.index) == 0:
            return None
        if isinstance(serials.index[self.current_tick_index], pd.Timestamp):
            return serials.index[self.current_tick_index].to_pydatetime()
        return serials.index[self.current_tick_index]


    def current_time(self):
        return self.tick_info['t'][self.current_tick_index]

    #
    def on_before_execute(self, sync=False):
        return 0

    def execute(self, ticket, sync=False):
        self.ticket = ticket
        if self.on_before_execute(sync) != 0:
            return None
        if sync:
            self.execute_(self.ticket,)
        else:
            thread = threading.Thread(target=self.execute_,
                             args=(self.ticket,))
            thread.start()
        return self.ticket
    #

    def get_price_count(self, symbol, tf_str='1m'):
        di = self.get_data_info(symbol, tf_str)
        return di['count']

    def on_begin_tick(self, *args, **kwargs):
        return 0

    def on_pre_load_ticks(self, *args, **kwargs):
        self.write_log(f"Loading ticks (tf: {self.tick_timeframe}), please wait ...\n")
        return 0

    def on_end_tick(self, *args, **kwargs):
        return 0

    def on_begin_execute(self, *args, **kwargs):
        return 0

    def on_end_execute(self, *args, **kwargs):
        return 0

    def on_execute_status(self, ticket, status, *args, **kwargs):
        self.write_log(f"{ticket}: {status}")

    def execute_(self, ticket):
        """"""
        exception_msg = None
        errid = EID_OK
        update_log_task = None
        try:
            test_start_time = datetime.now()
            pixiu_version = pkg_resources.get_distribution('pixiu').version
            self.write_log(f"\n\n == PiXiu({pixiu_version}) Backtesting Start: {test_start_time}, Ticket: {ticket}, Symbol: {self.symbol}, Period: {self.start_time} - {self.end_time}, "
                           f"Timeframe: {self.tick_timeframe}, Mode: {self.tick_mode} == \n\n")
            self.init_data()
            self.update_log_task_running = True
            self.on_pre_load_ticks()

            expiration = 900 #900s
            self.on_load_ticks()

            count = self.tick_info.size

            self.write_log(f"Tick Count: {count}, Tick Max Count: {self.tick_max_count}")
            status = dict(current=self.current_tick_index, max=count, errid=0)
            self.report['ticks']['value'] = status['max']
            self.on_execute_status(ticket, status)
            self.on_begin_execute()
            last_call_status_time = 0
            for i in range(count):
                try:
                    #
                    if self.tick_max_count is not None and i >= self.tick_max_count:
                        break
                    if self.stop:
                        raise PXErrorCode(EID_EAT_TEST_STOP)
                    self.on_begin_tick()
                    self.set_account(self.account, expiration=expiration)
                    # #
                    ask = self.Ask()
                    last_ask = self.Ask(1)
                    bid = self.Bid()
                    last_bid = self.Bid(1)
                    last_c_price = self.Close(1)
                    c_price = self.Close()
                    exit = self.__process_order__(c_price, last_c_price, ask, last_ask, bid, last_bid)
                    #
                    if exit == 0:
                        self.do_tick()
                    self.__update_account_log(ticket)
                    # #
                    if exit != 0:
                        if exit == 2:
                            raise PXErrorCode(EID_EAT_NOT_ENOUGH_MONEY)
                        else:
                            raise PXErrorCode(EID_EAT_EA_DEAD)
                    self.current_tick_index += 1
                    self.on_end_tick()
                except Exception as exc:
                    if isinstance(exc, AssertionError):
                        raise exc
                    traceback.print_exc()
                    exception_msg = self.on_execute_exception()

                    errid = EID_EAT_ERROR
                    break
            #
            try:
                if self.current_tick_index >= count:
                    self.current_tick_index = count - 1
                self.close_all_orders(self.Close(), comment="stop")
                self.__update_account_log(ticket)
            except:
                traceback.print_exc()
            self.on_end_execute()

            # self.write_log(f"\n\n == Execute PiXiu backtesting end: {datetime.now()}, ticket: {ticket} == \n\n")
            test_end_time = datetime.now()
            self.write_log(f"\n\n == PiXiu Backtesting End: {test_end_time}, Total Time: {(test_end_time-test_start_time).total_seconds()} sec, Ticket: {ticket} == \n\n")
            status = {}
            if exception_msg is not None:
                status["exception"] = exception_msg
            else:
                status["exception"] = "Test end. \n"
            status["errid"] = errid
            status["stop"] = 1
            self.on_execute_status(ticket, status)
        except Exception as exc:
            if isinstance(exc, AssertionError):
                raise exc
            traceback.print_exc()
            status = {}
            status["exception"] = "Unknown errors, terminated. \n"
            status["errid"] = 0
            status["stop"] = 1
            self.on_execute_status(ticket, status)

    def on_execute_exception(self):
        id = 0
        for exc in sys.exc_info():
            log.error(f"exc:{id}: {str(exc)}")
            id += 1
        tb_next = sys.exc_info()[2]
        exception = "Exception:\n"
        while tb_next is not None:
            if tb_next.tb_frame.f_code.co_filename == '<inline>':
                exception += "  line %d, in %s \n" % (tb_next.tb_lineno, tb_next.tb_frame.f_code.co_name)
            tb_next = tb_next.tb_next
        return exception
