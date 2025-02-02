
import sys
import math
import json
import threading
import importlib
import pkg_resources
from datetime import (datetime, )
import numpy as np
from RestrictedPython import (compile_restricted, safe_globals, utility_builtins,)
from ..base.ea_base import (EABase, )
from .ea_tester_context import (EATesterContext, )
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



# ----------------------------------------------------

MAX_DATA_LENGTH = 1048576 #1MB
class EATester(EABase):
    """EA Tester"""
    FM_MAX_DRAWDOWN_UPDATED           = 0b0000000000000001
    FM_TRADE_MAX_LOSS_UPDATED         = 0b0000000000000010
    FM_TRADE_MAX_PROFIT_UPDATED       = 0b0000000000000100
    FM_MAX_CONSECUTIVE_WINS_UPDATED   = 0b0000000000001000
    FM_MAX_CONSECUTIVE_LOSSES_UPDATED = 0b0000000000010000
    FM_START                          = 0b0000000000100000
    FM_END                            = 0b0000000001000000

    def __init__(self, params):
        super(EATester, self).__init__(EATesterContext(params), params)
        self.context.safe_globals = self.copy_globals()
        self.print_collection = None
        #
        # self.errid = None
        # self.errmsg = None
        # self.context.default_digits = 2
        # self.context.symbol = params["symbol"]
        # self.symbol_properties = {}
        # self.default_symbol_properties = params.get("symbol_properties", None)
        # self.context.spread_point = params.get("spread_point", None)
        # self.commission = params.get("commission", 0) #commission / a lot
        # self.context.tick_mode = params.get("tick_mode", TickMode.EVERY_TICK)
        # self.context.tick_timeframe = params.get("tick_timeframe", TimeFrame.M1)
        # self.context.tick_max_index = params.get('tick_max_index', None)
        # self.tick_start_index = params.get('tick_start_index', 0)
        # self.context.start_time = params["start_time"]
        # self.context.end_time = params["end_time"]

        # self.language = params.get("language", 'en')
        # self.script_path = params.get("script_path", None)
        # self.script_libs = params.get("script_libs", None)
        # self.log_file = None
        # self.log_path = params.get("log_path", None)
        # self.print_log_type = params.get("print_log_type", ['account', 'ea', 'order', 'report'])
        # self.print_collection = None
        # self.add_ea_settings = None

        #
        margin_so_so = self.percent_str_to_float(params.get("margin_so_so", None), 1.0) #100%
        if margin_so_so < 0:
            margin_so_so = 1.0
        margin_so_call = self.percent_str_to_float(params.get("margin_so_call", None), margin_so_so*1.2) #120%
        if margin_so_call < 0:
            margin_so_call = margin_so_so * 1.2
        #
        # if self.log_path:
        #     self.log_file = open(self.log_path, mode='wt')

        # if self.script_path is None:
        #     self.script = params["script"]
        # else:
        #     self.script = open(self.script_path).read()
        #
        self.context.script_metadata = self.parse_script(self.context.script)
        if self.context.script_libs is None:
            self.context.script_libs = self.load_libs(json.loads(self.context.script_metadata.get('lib', self.context.script_metadata.get('library', '[]'))))
        #
        self.context.script_settings = None
        try:
            # ss = params.get("script_settings", self.context.script_metadata.get('script_settings', None))
            ss = self.context.script_metadata.get('script_settings', params.get("script_settings", None))
            if isinstance(ss, str):
                self.context.script_settings = json.loads(ss)
            else:
                self.context.script_settings = ss
        except:
            traceback.print_exc()
        #
        # self.byte_code = None
        # self.context.orders = None
        # self.context.order_logs = []
        # self.context.charts_data = []
        # self.context.account_logs = []
        # self.context.return_logs = []
        # self.context.balance_dead_line = 0.0
        # self.context.account = params.get("account", None)
        if self.context.account is None:
            balance = round(float(params['balance']), self.context.default_digits)
            equity = balance
            try:
                leverage = float(params.get('leverage', 100))
            except:
                leverage = 100
            init_values = dict(
                               balance=balance, equity=balance, free_margin=balance,
                               currency=params.get("currency", None), leverage=leverage,
                               margin_so_call=margin_so_call,
                               margin_so_so=margin_so_so)
            self.context.account = self.get_init_data('account', init_values)
        else:
            default_value = {'equity': self.context.account['balance'], 'margin': 0, 'free_margin': self.context.account['balance']}
            for k in default_value:
                if k not in self.context.account:
                    self.context.account[k] = default_value[k]
        #
        #
        # self.current_api = TesterAPI_V1(tester=self, data_source={}, default_symbol=self.context.symbol)
        self.current_api = self.get_api()
        # self.data = {DataScope.EA_VERSION: {}, DataScope.EA: {}, DataScope.ACCOUNT: {}, DataScope.EA_SETTIGNS: {}}
        self.context.persistent_data = self.get_init_data('persistent_data', None)
        self.context.set_error(EID_OK, 'EID_OK')
        #
        self.context.reset_flags()

    def get_init_data(self, name, values):
        ret = None
        if name == 'account':
            ret = {'balance': values.get('balance', 0.0),
                            'equity': values.get('equity', 0.0),
                            'margin': 0,
                            'free_margin': values.get('free_margin', 0.0),
                            'credit': 0.0,
                            'profit': 0.0,
                            'margin_level': 0,
                            # static
                            'leverage': values.get('leverage', 0),
                            'currency': values.get('currency', None),
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
                            'margin_so_call': values.get('margin_so_call', 0.0),
                            'margin_so_so': values.get('margin_so_so', 0.0),
                            'commission': 0.0,
                            }
        elif name == 'report':
            ret = {
                'start_time': {'value': values['start_time'], 'desc': 'Start Time', 'type': 'datetime'},  #
                'end_time': {'value': values['end_time'], 'desc': 'End Time', 'type': 'datetime'},  #
                'init_balance': {'value': values['init_balance'], 'desc': 'Init Balance'},  #
                'symbol': {'value': values['symbol'], 'desc': 'Symbol', 'type': 'str'},  #
                'currency': {'value': values['currency'], 'desc': 'Currency', 'type': 'str'},  #
                'leverage': {'value': values['leverage'], 'desc': 'Leverage'},  #
                'spread_point': {'value': values['spread_point'], 'desc': 'Spread Points'},  #
                'margin_so_call': {'value': values['margin_so_call'], 'desc': 'Margin Call Level', 'type': '%'},
                #
                'margin_so_so': {'value': values['margin_so_so'], 'desc': 'Stop Out Level', 'type': '%'},  #
                'ticks': {'value': values.get('ticks', 0), 'desc': 'Ticks', 'precision': 0},  #
                'balance': {'value': 0, 'desc': 'Balance'},  #
                'total_net_profit': {'value': 0, 'desc': 'Total Net Profit'},  #
                'total_net_profit_rate': {'value': 0, 'desc': 'Total Net Profit Rate', 'type': '%'},  #
                'sharpe_ratio': {'value': 0, 'desc': 'Sharpe Ratio', 'precision': 2},  #
                'sortino_ratio': {'value': 0, 'desc': 'Sortino Ratio', 'precision': 2},  #
                'absolute_drawdown': {'value': 0, 'desc': 'Absolute Drawdown'},  #
                'max_drawdown': {'value': 0, 'desc': 'Max Drawdown'},  #
                'max_drawdown_rate': {'value': 0, 'desc': 'Max Drawdown Rate', 'type': '%'},  #
                'min_volume': {'value': None, 'desc': 'Min Volume'},  #
                'max_volume': {'value': 0, 'desc': 'Max Volume'},  #
                'total_trades': {'value': 0, 'desc': 'Total Trades', 'precision': 0},  #
                'profit_trades': {'value': 0, 'desc': 'Profit Trades', 'precision': 0},  #
                'win_rate': {'value': 0, 'desc': 'Win Rate', 'type': '%'},  #
                'trade_max_profit': {'value': 0, 'desc': 'Trade Max Profit'},  #
                'trade_avg_profit': {'value': 0, 'desc': 'Trade Avg Profit'},  #
                'trade_max_loss': {'value': np.nan, 'desc': 'Trade Max Loss'},  #
                'trade_avg_loss': {'value': 0, 'desc': 'Trade Avg Loss'},  #
                'loss_trades': {'value': 0, 'desc': 'Loss Trades', 'precision': 0},  #
                'gross_profit': {'value': 0, 'desc': 'Gross Profit'},  #
                'gross_loss': {'value': 0, 'desc': 'Gross Loss'},  #
                'short_positions': {'value': 0, 'desc': 'Short Positions', 'precision': 0},  #
                'short_positions_win': {'value': 0, 'desc': 'Short Positions Win', 'precision': 0},  #
                'long_positions': {'value': 0, 'desc': 'Long Positions', 'precision': 0},  #
                'long_positions_win': {'value': 0, 'desc': 'Long Positions Win', 'precision': 0},  #
                'max_consecutive_wins': {'value': 0, 'desc': 'Max Consecutive Wins', 'precision': 0},  #
                'max_consecutive_wins_money': {'value': 0, 'desc': 'Max Consecutive Wins Money'},  #
                'max_consecutive_losses': {'value': 0, 'desc': 'Max Consecutive Losses', 'precision': 0},  #
                'max_consecutive_losses_money': {'value': 0, 'desc': 'Max Consecutive Losses Money'},  #
            }
        elif name == 'temp':
            ret = {
                'consecutive_wins': 0,
                'consecutive_wins_money': 0,
                'consecutive_losses': 0,
                'consecutive_losses_money': 0,
                'max_volume': 0,
                'max_drawdown': 0,
                'max_drawdown_rate': 0,
                'account_max_equity': values['equity'],
                'account_min_equity': values['equity'],
                'account_min_balance': values['balance'],
            }
        elif name == 'persistent_data':
            ret = {DataScope.EA_VERSION: {}, DataScope.EA: {}, DataScope.ACCOUNT: {}, DataScope.EA_SETTIGNS: {}}
        elif name == 'orders':
            ret = {'opened': {}, 'closed': {}, 'pending': {},
                       'counter': 0, 'opened_counter': 0, 'pending_counter': 0,
                       '__ds__': {},
                       'stop_loss': {True: {values['symbol']: {'data': {}, 'min': 0, 'max': 0}},
                                     False: {values['symbol']: {'data': {}, 'min': 0, 'max': 0}}},
                       'take_profit': {True: {values['symbol']: {'data': {}, 'min': 0, 'max': 0}},
                                       False: {values['symbol']: {'data': {}, 'min': 0, 'max': 0}}},
                       'data': {}
                       }
        elif name == 'account_info':
            ret = {'data_raw': [], '__ds__': None}
        elif name == 'sid':
            ret = {values['symbol']: 0}
        elif name == 'sid_data':
            ret = {0: values['symbol']}
        elif name == 'cid':
            ret = {OrderCommand.BUY: 100, OrderCommand.SELL: 200,
                        OrderCommand.BUYLIMIT: 110, OrderCommand.SELLLIMIT: 210,
                        OrderCommand.BUYSTOP: 120, OrderCommand.SELLSTOP: 220,
                        }
        elif name == 'cid_data':
            ret = {100: OrderCommand.BUY, 200: OrderCommand.SELL}
        else:
            raise
        return ret

    # def set_error(self, errid, errmsg):
    #     self.errid = errid
    #     self.errmsg = errmsg

    # def get_error(self):
    #     return self.errid, self.errmsg
    #
    # def reset_flags(self):
    #     self.context.flags = 0
    #     # self.context.flags = dict(max_drawdown_updated=False, trade_max_loss_updated=False,
    #     #                   max_consecutive_wins_updated=False, max_consecutive_losses_updated=False)

    def get_api(self):
        return TesterAPI_V1(tester=self, data_source={}, default_symbol=self.context.symbol)

    def add_chart(self, name, **kwargs):
        try:
            if self.context.add_ea_settings is None:
                return False
            if 'chart' in kwargs:
                self.context.add_ea_settings['charts'][name] = kwargs['chart']
        except:
            traceback.print_exc()
            return False
        return True

    def add_param(self, name, **kwargs):
        try:
            if self.context.add_ea_settings is None:
                return False
            if 'param' in kwargs:
                # self.add_ea_settings['params'][name] = kwargs['param']
                param = kwargs['param']
            else:
                param = {"value": None, "config": {"type": "bool", "required": True}}
                if 'value' in kwargs:
                    param['value'] = kwargs['value']
                else:
                    return False
                if 'type' in kwargs:
                    param['config']['type'] = kwargs['type']
                else:
                    param['config']['type'] = 'str'
                if 'min' in kwargs:
                    param['config']['min'] = kwargs['min']
                if 'max' in kwargs:
                    param['config']['max'] = kwargs['max']
                if 'options' in kwargs:
                    param['config']['options'] = kwargs['options']
                #
                param['config']['required'] = kwargs.get('required', False)
                # AddParam("debug", value=True, type="bool", required=True)
                # AddParam("notify", param={"value": False, "config": {"type": "bool", "required": True}})
            self.context.add_ea_settings['params'][name] = param

        except:
            traceback.print_exc()
            return False
        return True

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
        self.context.persistent_data[scope].pop(name)
        return 0

    def load_data(self, name, scope, format='json'):
        if format != 'json':
            return None
        data = self.context.persistent_data[scope].get(name, None)
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
        self.context.persistent_data[scope][name] = data
        return EID_OK

    def init_report_data(self):
        init_values = dict(start_time=self.context.start_time, end_time=self.context.end_time, init_balance=self.context.account['balance'],
                           balance=self.context.account['balance'], equity=self.context.account['equity'],
                           symbol=self.context.symbol, currency=self.context.account['currency'], leverage=self.context.account['leverage'],
                           spread_point=self.context.spread_point, margin_so_call=self.context.account['margin_so_call'],
                           margin_so_so=self.context.account['margin_so_so'])
        self.context.report = self.get_init_data('report', init_values)
        self.context.temp = self.get_init_data('temp', init_values)

    def get_print_factory(self, _getattr_=None):
        """print factory"""
        if self.print_collection is None:
            self.print_collection = EATesterPrintCollector(_getattr_, self.write_log)
        return self.print_collection

    def write_log(self, *args, **kwargs):
        log_type = kwargs.get('type', 'eat')
        if log_type == 'eat' or log_type in self.context.print_log_type:
            print(*args)
        #
        if self.context.log_file:
            log_str = ''
            for a in args:
                log_str = f'{log_str} {a}'
            self.context.log_file.write(str(log_str))
            # self.log_file.write(*args)
            self.context.log_file.write('\n')
        return True

    def get_account_data(self, timeframe):
        """"""
        data = None
        data = self.context.account_info.get('__ds__', None)
        if data:
            data = data.get(timeframe, None)
        else:
            self.context.account_info['__ds__'] = {}
        if data is None:
            new_a = np.array([(0.0, )*33]*self.context.tick_info.size,
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
            new_a['t'] = self.context.tick_info['t']
            #init
            new_a['credit'] = self.context.account['credit']
            new_a['balance'] = self.context.account['balance']
            new_a['equity'] = self.context.account['equity']
            new_a['margin'] = self.context.account['margin']
            new_a['free_margin'] = self.context.account['free_margin']
            new_a['credit'] = self.context.account['credit']
            new_a['profit'] = self.context.account['profit']
            new_a['margin_level'] = self.context.account['margin_level']
            new_a['commission'] = self.context.account['commission']
            #static
            new_a['currency'] = self.context.account['currency']
            new_a['free_margin_mode'] = self.context.account['free_margin_mode']
            new_a['leverage'] = self.context.account['leverage']
            new_a['stop_out_level'] = self.context.account['stop_out_level']
            new_a['stop_out_mode'] = self.context.account['stop_out_mode']
            new_a['company'] = self.context.account['company']
            new_a['name'] = self.context.account['name']
            new_a['number'] = self.context.account['number']
            new_a['server'] = self.context.account['server']
            new_a['trade_mode'] = self.context.account['trade_mode']
            new_a['limit_orders'] = self.context.account['limit_orders']
            new_a['margin_so_mode'] = self.context.account['margin_so_mode']
            new_a['trade_allowed'] = self.context.account['trade_allowed']
            new_a['trade_expert'] = self.context.account['trade_expert']
            new_a['margin_so_call'] = self.context.account['margin_so_call']
            new_a['margin_so_so'] = self.context.account['margin_so_so']

            self.context.account_info['__ds__'][timeframe] = new_a

        return self.context.account_info['__ds__'][timeframe]
    #

    def get_data_info(self, symbol, timeframe,  start_time=None, end_time=None, last_count=None):
        raise NotImplementedError

    def add_order_log(self, log_dict):
        """Add order log"""
        log_dict['id'] = len(self.context.order_logs) + 1
        self.context.order_logs.append(log_dict)

    def plot(self, chart_name, series):
        self.context.charts_data.append(dict(cn=chart_name, data=series))
        # self.charts_data.append(dict(cn="default", data=series))

    def add_account_log(self, log_dict):
        """Add account log"""
        prev_equity = 0 if len(self.context.account_logs) == 0 else self.context.account_logs[len(self.context.account_logs)-1]['equity']
        if log_dict['equity'] != prev_equity:
            self.context.return_logs.append(log_dict)
        self.context.account_logs.append(log_dict)

    def add_print_log(self):
        """"""
        if self.print_collection is not None:
            for t in self.print_collection.txt:
                self.context.print_logs.append(t)
            #clear print
            self.print_collection.txt = []

    def symbol_to_sid(self, symbol):
        sid = self.context.sid.get(symbol, None)
        if sid is None:
            sid = len(self.context.sid)
            self.context.sid[symbol] = sid
            self.context.sid_data[sid] = symbol
        return sid

    def command_to_cid(self, cmd):
        return self.context.cid[cmd]

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
        mn = 0 if new_order.get('magic_number', None) is None else new_order['magic_number']
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
        self.context.orders['counter'] = self.context.orders['counter'] + 1
        symbol_orders = self.context.orders['pending'].get(new_order['symbol'], {})

        new_order['uid'] = new_order['ticket']
        new_order['status'] = OrderStatus.PENDING
        self.context.orders['data'][new_order['uid']] = new_order
        symbol_orders[new_order['uid']] = new_order
        self.context.orders['pending'][new_order['symbol']] = symbol_orders
        self.context.orders['pending_counter'] = self.context.orders['pending_counter'] + 1
        #
        sp = self.get_symbol_properties(new_order['symbol'])
        tcs = sp['trade_contract_size']
        #
        ds = self.context.orders['pending'].get('__ds__', None)

        new_a = self.order_to_ndarray(new_order)
        if ds is not None and ds.size > 0:
            self.context.orders['pending']['__ds__'] = np.concatenate([ds, new_a])
        else:
            self.context.orders['pending']['__ds__'] = new_a

        #
        return EID_OK, new_order['uid']

    def __add_market_order__(self, new_order):
        """add a new market order"""
        if not order_is_market(new_order['cmd']):
            return EID_EAT_INVALID_ORDER_TYPE, -1
        #
        sp = self.get_symbol_properties(new_order['symbol'])
        margin = new_order['open_price'] * self.__calculate_pip__(new_order['open_price']) * new_order['volume'] * sp['trade_contract_size'] / self.context.account['leverage']
        margin = round(margin, self.context.default_digits)
        if margin > self.context.account['balance'] - self.context.account['margin']:
            return EID_EAT_NOT_ENOUGH_MONEY, -1
        new_order['uid'] = str(new_order['ticket'])
        if not new_order.get('comment', None):
            new_order['comment'] = f"uid#{new_order['uid']}|"
        new_order['margin'] = margin
        new_order['status'] = OrderStatus.OPENED

        commission = 0.0
        #commissions
        if self.context.commission > 0:
            # see: https://www.houseofborse.com/commission-calculation
            # all commission charged and debited on the opening of the trade
            commission = new_order['volume'] * self.context.commission * self.__calculate_pip__(new_order['open_price']) * 2
        if commission > self.context.account['balance'] - self.context.account['margin']:
            return EID_EAT_NOT_ENOUGH_MONEY, -1
        new_order['commission'] = commission
        #
        self.context.orders['counter'] = self.context.orders['counter'] + 1
        #
        symbol_orders = self.context.orders['opened'].get(new_order['symbol'], {})

        self.context.orders['data'][new_order['uid']] = new_order
        symbol_orders[new_order['uid']] = new_order
        self.context.orders['opened'][new_order['symbol']] = symbol_orders
        self.context.orders['opened_counter'] = self.context.orders['opened_counter'] + 1

        #
        ds = self.context.orders['opened'].get('__ds__', None)
        new_a = self.order_to_ndarray(new_order)
        if ds is not None and ds.size > 0:
            self.context.orders['opened']['__ds__'] = np.concatenate([ds, new_a])
        else:
            self.context.orders['opened']['__ds__'] = new_a
        #update account
        self.context.account['margin'] = round(self.context.account['margin'] + new_order['margin'], self.context.default_digits)
        self.context.account['commission'] = round(self.context.account['commission'] + new_order['commission'], self.context.default_digits)

        #report
        self.context.report['total_trades']['value'] += 1
        if order_is_long(new_order['cmd']):
            self.context.report['long_positions']['value'] += 1
        else:
            self.context.report['short_positions']['value'] += 1
        #
        if self.context.report['max_volume']['value'] < new_order['volume']:
            self.context.report['max_volume']['value'] = new_order['volume']
        if self.context.report['min_volume']['value'] is None or self.context.report['min_volume']['value'] > new_order['volume'] > 0:
            self.context.report['min_volume']['value'] = new_order['volume']

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
                                 # time=str(datetime.fromtimestamp(order_dict['open_time'])),
                                 time=str(datetime.utcfromtimestamp(order_dict['open_time'])),
                                 type=order_dict['cmd'], volume=order_dict['volume'],
                                 price=price,
                                 stop_loss=round(order_dict['stop_loss'], self.context.price_digits),
                                 take_profit=round(order_dict['take_profit'], self.context.price_digits),
                                 comment=order_dict['comment'], tags=order_dict['tags'],
                                 balance=None, profit=None))
        
        return EID_OK, order_uid

    def __modify_order__(self, order):
        if order_is_market(order['cmd']):
            ds = self.context.orders['opened']['__ds__']
        else:
            ds = self.context.orders['pending']['__ds__']
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
        ds = self.context.orders['pending']['__ds__']
        closed_a = ds[ds['oid'] == oid]
        self.context.orders['pending']['__ds__'] = ds[ds['oid'] != oid]
        #
        self.context.orders['pending_counter'] = self.context.orders['pending_counter'] - 1
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
        ds = self.context.orders['opened']['__ds__']
        # closed_a = ds[ds['oid'] == oid]
        closed_a = ds[ds['oid'] == oid][0]
        self.context.orders['opened']['__ds__'] = ds[ds['oid'] != oid]
        #
        order['profit'] = closed_a['pf']
        if add_closed:
            symbol_orders = self.context.orders['closed'].get(order['symbol'], {})
            symbol_orders[oid] = order
            self.context.orders['closed'][order['symbol']] = symbol_orders

        self.context.orders['opened_counter'] = self.context.orders['opened_counter'] - 1
        #

        return order['uid']

    def __calculate_profit__(self, cid, price):
        ''''''
        profit = 0
        ods = self.context.orders['opened'].get('__ds__', None)
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
    
    def get_order(self, order_uid):
        """Get Order"""
        ret = self.context.orders['data'].get(order_uid, None)
        #update order data
        oid = int(order_uid)
        ds = self.context.orders['opened'].get('__ds__', None)
        if ds is not None:
            the_a = ds[ds['oid'] == oid]
            if the_a.size > 0:
                ret['profit'] = the_a[0]['pf']

        return ret

    def get_order_dict(self, symbol, status="opened", scope=DataScope.EA):
        symbol = self.context.symbol if symbol is None else symbol
        order_list = self.context.orders.get(status, {})
        if symbol == '*':
            ret = {}
            for s in order_list:
                if not s.startswith('__'):
                    ret.update(order_list[s])
            return ret
        else:
            return order_list.get(symbol, {})

    def set_order_list(self, symbol, status, value):
        """"""
        self.context.orders[status][symbol] = value

    def get_account(self, ):
        """"""
        return self.context.account_info['data_raw'][-1]

    def set_account(self, account, expiration=None):
        """"""
        self.context.account_info['data_raw'].append(account)
        if self.context.account_info['__ds__'] is None or self.context.account_info['__ds__'].get(self.context.tick_timeframe, None) is None:
            self.get_account_data(self.context.tick_timeframe)
        #
        account_data = self.context.account_info['__ds__'][self.context.tick_timeframe][self.context.tick_current_index]
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
                if order_is_market(order_dict['cmd']):
                    if take_profit > 0 and take_profit <= ask:
                        return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                    if stop_loss > 0 and stop_loss >= ask:
                        return EID_EAT_INVALID_ORDER_STOP_LOSS
                else:
                    if take_profit > 0 and take_profit <= open_price:
                        return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                    if stop_loss > 0 and stop_loss >= open_price:
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
                    if 0 < price < ask:
                        return EID_EAT_INVALID_ORDER_CLOSE_PRICE

            #
            if stage != 2:
                if stop_loss > 0 and take_profit > 0 and stop_loss < take_profit:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
                if order_is_market(order_dict['cmd']):
                    if stop_loss > 0 and stop_loss <= bid:
                        return EID_EAT_INVALID_ORDER_STOP_LOSS
                    if take_profit > 0 and take_profit >= bid:
                        return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                else:
                    if stop_loss > 0 and stop_loss <= open_price:
                        return EID_EAT_INVALID_ORDER_STOP_LOSS
                    if take_profit > 0 and take_profit >= open_price:
                        return EID_EAT_INVALID_ORDER_TAKE_PROFIT


        return EID_OK

    def __new_ticket__(self):
        return str(self.context.orders['counter'] + 1)

    def open_order(self, symbol, cmd, price, volume, stop_loss, take_profit, comment=None, ext_check_open_range=0,
                       ext_check_order_hold_count=0, magic_number=None, slippage=None, arrow_color=None, tags=None,
                       from_uid=None, to_uid=None):
        """"""
        order_uid = None
        account = self.context.account
        if self.context.orders['opened_counter'] >= account['limit_orders']:
            return EID_EAT_LIMIT_ORDERS, None
        if stop_loss is None:
            stop_loss = 0.0
        if take_profit is None:
            take_profit = 0.0
        volume = round(volume, self.context.volume_precision)
        order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=cmd, open_price=price,
                         volume=volume, stop_loss=stop_loss, take_profit=take_profit, margin=0, comment=comment,
                         magic_number=magic_number, open_time=self.current_time(), commission=0,
                         close_time=None, close_price=np.nan, profit=0.0, tags=tags, dirty=False,
                         from_uid=from_uid, to_uid=to_uid)
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
                                 # time=str(datetime.fromtimestamp(order_dict['open_time'])),
                                 time=str(datetime.utcfromtimestamp(order_dict['open_time'])),
                                 type=cmd, volume=volume,
                                 price=round(price, self.context.price_digits),
                                 stop_loss=round(stop_loss, self.context.price_digits),
                                 take_profit=round(take_profit, self.context.price_digits),
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
        if order_dict['symbol'] != self.context.symbol:
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
                                 # time=str(datetime.fromtimestamp(self.current_time())),
                                 time=str(datetime.utcfromtimestamp(self.current_time())),
                                 type="MODIFY",
                                 volume=order_dict['volume'], price=round(price, self.context.price_digits),
                                 # stop_loss=round(stop_loss, self.context.price_digits),
                                 # take_profit=round(take_profit, self.context.price_digits),
                                 profit=round(order_dict['profit'], self.context.default_digits),
                                 balance=round(self.context.account["balance"] + order_dict['profit'], self.context.default_digits),
                                 comment=comment, tags=tags)
        if stop_loss is not None:
            order_log['stop_loss'] = round(stop_loss, self.context.price_digits)
        if take_profit is not None:
            order_log['take_profit'] = round(take_profit, self.context.price_digits)
        self.add_order_log(order_log)
        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)

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
        closed_profit = 0
        if order_dict is None or order_dict.get('close_time', None) is not None:
            return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                                      close_time=close_time, closed_profit=closed_profit)
        # if volume is None:
        #     return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
        if volume is None or volume <= 0:
            volume = float(order_dict['volume'])
        else:
            volume = round(volume, self.context.volume_precision)
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
            # if tags is not None:
            #     order_dict['tags'] = tags
            closed_ratio = volume / order_dict['volume']
            original_volume = order_dict['volume']
            order_dict['volume'] = volume
            order_dict['dirty'] = False
            order_dict['comment'] = comment
            order_dict['close_time'] = close_time
            order_dict['close_price'] = price
            order_dict['status'] = OrderStatus.CLOSED
            order_uid = self.__remove_order__(order_dict)
            # close_profit = round(order_dict['profit'] * closed_ratio, self.context.default_digits)
            closed_profit = order_dict['profit'] * closed_ratio
            order_dict['profit'] = closed_profit
            #
            self.context.account["balance"] = self.context.account["balance"] + closed_profit
            # closed_margin = round(order_dict['margin'] * closed_ratio, self.context.default_digits)
            closed_margin = round(order_dict['margin'], self.context.default_digits)
            self.context.account["margin"] = round(self.context.account["margin"] - closed_margin, self.context.default_digits)
            # self.context.account["margin"] = self.context.account["margin"] - closed_margin
            # new_margin = order_dict['margin'] - closed_margin
            new_volume = round(original_volume - volume, self.context.volume_precision)
        #
            #report
            if update_report_func:
                update_report_func(order_is_long(order_dict['cmd']), closed_profit, 1)
            else:
                self.__update_report__(order_is_long(order_dict['cmd']), closed_profit)

            #
            if new_volume > 0:
                original_order_uid = order_uid
                new_order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=order_dict['cmd'],
                                  open_price=order_dict['open_price'],
                                  volume=new_volume, stop_loss=order_dict['stop_loss'],
                                  # take_profit=order_dict['take_profit'], margin=new_margin,
                                  take_profit=order_dict['take_profit'],
                                  comment=f"from #{order_dict['ticket']}",
                                  open_time=order_dict['open_time'],
                                  from_uid=order_dict['uid'], to_uid=None)
                if tags is not None:
                    new_order_dict['tags'] = tags
                errid, order_uid = self.__add_market_order__(new_order_dict)
                if errid != EID_OK:
                    return errid, dict(order_uid=order_uid, order_dict=order_dict, close_price=price,
                                       close_time=close_time)
                #
                order_dict = self.get_order(order_uid=original_order_uid)
                order_dict['comment'] = f"to #{new_order_dict['ticket']}"
                order_dict['to_uid'] = order_uid
        else:
            order_dict['status'] = OrderStatus.CANCELLED
            order_uid = self.__remove_pending_order__(order_dict)

        return EID_OK, dict(order_uid=order_uid, order_dict=order_dict, close_price=price, close_time=close_time,
                            closed_profit=closed_profit)

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
        closed_profit = ret['closed_profit']
        #
        self.add_order_log(dict(uid=order_dict['uid'], ticket=order_dict['ticket'],
                                    # time=str(datetime.fromtimestamp(close_time)),
                                    time=str(datetime.utcfromtimestamp(close_time)),
                                    type="CLOSE", volume=volume,
                                    price=round(close_price, self.context.price_digits),
                                    stop_loss=round(order_dict['stop_loss'], self.context.price_digits),
                                    take_profit=round(order_dict['take_profit'], self.context.price_digits),
                                    balance=round(self.context.account["balance"], self.context.default_digits),
                                    profit=round(closed_profit, self.context.default_digits),
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
                                            # time=str(datetime.fromtimestamp(close_time)),
                                            time=str(datetime.utcfromtimestamp(close_time)),
                                            type="CLOSE_MULTI_ORDERS", volume=order_dict['volume'],
                                            price=round(close_price, self.context.price_digits),
                                            stop_loss=round(order_dict['stop_loss'], self.context.price_digits),
                                            take_profit=round(order_dict['take_profit'], self.context.price_digits),
                                            balance=round(self.context.account["balance"], self.context.default_digits),
                                            profit=round(order_dict['profit'], self.context.default_digits),
                                            comment=order_dict['comment'], tags=order_dict['tags']))

        return EID_OK, dict(result=result, command_uid=None, sync=True)

    def wait_command(self, uid, timeout=120):
        return 0, {}

    def acquire_lock(self, name, timeout=60):
        return True

    def release_lock(self, name):
        pass

    def notify(self, message):
        self.context.print_logs.append(f"<Notification>: {message}\n")

    #
    def Ask(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        ask = self.context.tick_info['a'][self.context.tick_current_index - shift]
        if ask == 0:
            ask = self.Bid(shift) + self.context.spread_calculated
        return ask

    def Bid(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        bid = self.context.tick_info['b'][self.context.tick_current_index - shift]
        if bid == 0:
            bid = self.Close(shift)
        return bid

    def Close(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        return self.context.tick_info['c'][self.context.tick_current_index - shift]

    def Open(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        return self.context.tick_info['o'][self.context.tick_current_index - shift]

    def High(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        return self.context.tick_info['h'][self.context.tick_current_index - shift]

    def Low(self, shift=0, symbol=None):
        if symbol is not None and symbol != self.context.symbol:
            return None
        return self.context.tick_info['l'][self.context.tick_current_index - shift]

    def Time(self, shift=0, symbol=None) -> datetime:
        if symbol is not None and symbol != self.context.symbol:
            return None
        # return datetime.fromtimestamp(self.context.tick_info['t'][self.context.tick_current_index - shift])
        return datetime.utcfromtimestamp(self.context.tick_info['t'][self.context.tick_current_index - shift])
        # return datetime.utcfromtimestamp(self.context.tick_info['t'][self.context.tick_current_index - shift]).replace(tzinfo=pytz.utc)

    def Volume(self, shift=0, symbol=None) -> float:
        if symbol is not None and symbol != self.context.symbol:
            return None
        return self.context.tick_info['v'][self.context.tick_current_index - shift]
    #
    def __update_report_max_dd__(self):
        #calculate maxdd: https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp
        if self.context.temp['account_min_equity'] < self.context.report['init_balance']['value']:
            self.context.temp['max_drawdown'] = self.context.temp['account_min_equity'] - self.context.temp['account_max_equity']
        if self.context.temp['account_max_equity'] > 0:
            self.context.temp['max_drawdown_rate'] = self.context.temp['max_drawdown'] / self.context.temp['account_max_equity']
        else:
            self.context.temp['max_drawdown_rate'] = 0
        #
        if self.context.report['max_drawdown']['value'] > self.context.temp['max_drawdown']:
            self.context.report['max_drawdown']['value'] = self.context.temp['max_drawdown']
            self.context.report['max_drawdown_rate']['value'] = self.context.temp['max_drawdown_rate']
            # self.context.flags['max_drawdown_updated'] = True
            self.context.flags |= EATester.FM_MAX_DRAWDOWN_UPDATED

    def __update_report__(self, is_long, profit, trades=1):
        ret = False
        if profit == 0:
            return ret
        profit = round(profit, self.context.default_digits)
        if profit > 0:
            self.context.report['profit_trades']['value'] += trades
            self.context.report['gross_profit']['value'] = self.context.report['gross_profit']['value'] + profit
            self.context.report['trade_avg_profit']['value'] = self.context.report['gross_profit']['value'] / \
                                                       self.context.report['profit_trades']['value']

            if self.context.report['trade_max_profit']['value'] < profit:
                self.context.report['trade_max_profit']['value'] = profit
                # self.context.flags['trade_max_profit_updated'] = True
                self.context.flags |= EATester.FM_TRADE_MAX_PROFIT_UPDATED

            if is_long:
                self.context.report['long_positions_win']['value'] += trades
            else:
                self.context.report['short_positions_win']['value'] += trades

            self.context.temp['consecutive_wins'] += trades
            self.context.temp['consecutive_wins_money'] = self.context.temp['consecutive_wins_money'] + profit
            self.context.temp['consecutive_losses'] = 0
            self.context.temp['consecutive_losses_money'] = 0
            #self.context.account['currency']
        else:
            self.context.report['loss_trades']['value'] += trades
            self.context.report['gross_loss']['value'] = self.context.report['gross_loss']['value'] + profit
            self.context.report['trade_avg_loss']['value'] = self.context.report['gross_loss']['value'] / self.context.report['loss_trades'][
                'value']

            if np.isnan(self.context.report['trade_max_loss']['value']) or self.context.report['trade_max_loss']['value'] > profit:
                self.context.report['trade_max_loss']['value'] = profit
                # self.context.flags['trade_max_loss_updated'] = True
                self.context.flags |= EATester.FM_TRADE_MAX_LOSS_UPDATED

            self.context.temp['consecutive_losses'] += trades
            self.context.temp['consecutive_losses_money'] = self.context.temp['consecutive_losses_money'] + profit
            self.context.temp['consecutive_wins'] = 0
            self.context.temp['consecutive_wins_money'] = 0
            #
        #
        #max dd
        if self.context.temp['account_max_equity'] < self.context.account['equity']:
            # #calculate maxdd: https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp
            ret = self.__update_report_max_dd__()
            #
            self.context.temp['account_max_equity'] = self.context.account['equity']
            self.context.temp['account_min_equity'] = self.context.account['equity']
        else:
            if self.context.temp['account_min_equity'] > self.context.account['equity']:
                ret = self.__update_report_max_dd__()
                self.context.temp['account_min_equity'] = self.context.account['equity']
        #

        #
        if self.context.temp['account_min_balance'] > self.context.account['balance']:
            self.context.temp['account_min_balance'] = self.context.account['balance']
            self.context.report['absolute_drawdown']['value'] = self.context.temp['account_min_balance'] - self.context.report['init_balance']['value']

        #
        # self.context.report['max_drawdown']['value'] = self.context.temp['account_max_equity'] - self.context.temp['account_min_equity']
        # if self.context.temp['account_max_equity'] > 0:
        #     self.context.report['max_drawdown_rate']['value'] = self.context.report['max_drawdown']['value'] / self.context.temp['account_max_equity']
        # else:
        #     self.context.report['max_drawdown_rate']['value'] = 0
        if self.context.report['max_consecutive_wins']['value'] < self.context.temp['consecutive_wins']:
            self.context.report['max_consecutive_wins']['value'] = self.context.temp['consecutive_wins']
            # self.context.flags['max_consecutive_wins_updated'] = True
            self.context.flags |= EATester.FM_MAX_CONSECUTIVE_WINS_UPDATED

        if self.context.report['max_consecutive_wins_money']['value'] < self.context.temp['consecutive_wins_money']:
            self.context.report['max_consecutive_wins_money']['value'] = self.context.temp['consecutive_wins_money']
        if self.context.report['max_consecutive_losses']['value'] < self.context.temp['consecutive_losses']:
            self.context.report['max_consecutive_losses']['value'] = self.context.temp['consecutive_losses']
            # self.context.flags['max_consecutive_losses_updated'] = True
            self.context.flags |= EATester.FM_MAX_CONSECUTIVE_LOSSES_UPDATED

        if self.context.report['max_consecutive_losses_money']['value'] > self.context.temp['consecutive_losses_money']:
            self.context.report['max_consecutive_losses_money']['value'] = self.context.temp['consecutive_losses_money']
        self.context.report['total_net_profit']['value'] = self.context.report['gross_profit']['value'] - abs(
            self.context.report['gross_loss']['value'])
        #
        if self.context.report['total_trades']['value'] > 0:
            self.context.report['win_rate']['value'] = self.context.report['profit_trades']['value'] / self.context.report['total_trades']['value']
        #Total net profit rate
        if self.context.report['init_balance']['value'] > 0:
            self.context.report['total_net_profit_rate']['value'] = self.context.report['total_net_profit']['value'] / self.context.report['init_balance']['value']
        self.context.report['balance']['value'] = self.context.account['balance']
        #
        # ratio = self.calculate_return_ratio()
        # self.context.report['sharpe_ratio']['value'] = ratio['sharpe_ratio']
        # self.context.report['sortino_ratio']['value'] = ratio['sortino_ratio']

        return ret

    # def __update_report__(self, is_long, profit, trades=1):
    #     ret = False
    #     if profit == 0:
    #         return ret
    #     profit = round(profit, self.context.default_digits)
    #     if profit > 0:
    #         self.context.report['profit_trades']['value'] += trades
    #         self.context.report['gross_profit']['value'] = self.context.report['gross_profit']['value'] + profit
    #         self.context.report['trade_avg_profit']['value'] = self.context.report['gross_profit']['value'] / \
    #                                                    self.context.report['profit_trades']['value']
    #
    #         if self.context.report['trade_max_profit']['value'] < profit:
    #             self.context.report['trade_max_profit']['value'] = profit
    #             # self.context.flags['trade_max_profit_updated'] = True
    #             self.context.flags |= EATester.FM_TRADE_MAX_PROFIT_UPDATED
    #
    #         if is_long:
    #             self.context.report['long_positions_win']['value'] += trades
    #         else:
    #             self.context.report['short_positions_win']['value'] += trades
    #
    #         self.context.temp['consecutive_wins'] += trades
    #         self.context.temp['consecutive_wins_money'] = self.context.temp['consecutive_wins_money'] + profit
    #         self.context.temp['consecutive_losses'] = 0
    #         self.context.temp['consecutive_losses_money'] = 0
    #         #self.context.account['currency']
    #     else:
    #         self.context.report['loss_trades']['value'] += trades
    #         self.context.report['gross_loss']['value'] = self.context.report['gross_loss']['value'] + profit
    #         self.context.report['trade_avg_loss']['value'] = self.context.report['gross_loss']['value'] / self.context.report['loss_trades'][
    #             'value']
    #
    #         if np.isnan(self.context.report['trade_max_loss']['value']) or self.context.report['trade_max_loss']['value'] > profit:
    #             self.context.report['trade_max_loss']['value'] = profit
    #             # self.context.flags['trade_max_loss_updated'] = True
    #             self.context.flags |= EATester.FM_TRADE_MAX_LOSS_UPDATED
    #
    #         self.context.temp['consecutive_losses'] += trades
    #         self.context.temp['consecutive_losses_money'] = self.context.temp['consecutive_losses_money'] + profit
    #         self.context.temp['consecutive_wins'] = 0
    #         self.context.temp['consecutive_wins_money'] = 0
    #         #
    #     #
    #     #max dd
    #     if self.context.temp['account_max_equity'] < self.context.account['equity']:
    #         # #calculate maxdd: https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp
    #         ret = self.__update_report_max_dd__()
    #         #
    #         self.context.temp['account_max_equity'] = self.context.account['equity']
    #         self.context.temp['account_min_equity'] = self.context.account['equity']
    #     else:
    #         if self.context.temp['account_min_equity'] > self.context.account['equity']:
    #             ret = self.__update_report_max_dd__()
    #             self.context.temp['account_min_equity'] = self.context.account['equity']
    #     #
    #
    #     #
    #     if self.context.temp['account_min_balance'] > self.context.account['balance']:
    #         self.context.temp['account_min_balance'] = self.context.account['balance']
    #         self.context.report['absolute_drawdown']['value'] = self.context.temp['account_min_balance'] - self.context.report['init_balance']['value']
    #
    #     #
    #     # self.context.report['max_drawdown']['value'] = self.context.temp['account_max_equity'] - self.context.temp['account_min_equity']
    #     # if self.context.temp['account_max_equity'] > 0:
    #     #     self.context.report['max_drawdown_rate']['value'] = self.context.report['max_drawdown']['value'] / self.context.temp['account_max_equity']
    #     # else:
    #     #     self.context.report['max_drawdown_rate']['value'] = 0
    #     if self.context.report['max_consecutive_wins']['value'] < self.context.temp['consecutive_wins']:
    #         self.context.report['max_consecutive_wins']['value'] = self.context.temp['consecutive_wins']
    #         # self.context.flags['max_consecutive_wins_updated'] = True
    #         self.context.flags |= EATester.FM_MAX_CONSECUTIVE_WINS_UPDATED
    #
    #     if self.context.report['max_consecutive_wins_money']['value'] < self.context.temp['consecutive_wins_money']:
    #         self.context.report['max_consecutive_wins_money']['value'] = self.context.temp['consecutive_wins_money']
    #     if self.context.report['max_consecutive_losses']['value'] < self.context.temp['consecutive_losses']:
    #         self.context.report['max_consecutive_losses']['value'] = self.context.temp['consecutive_losses']
    #         # self.context.flags['max_consecutive_losses_updated'] = True
    #         self.context.flags |= EATester.FM_MAX_CONSECUTIVE_LOSSES_UPDATED
    #
    #     if self.context.report['max_consecutive_losses_money']['value'] > self.context.temp['consecutive_losses_money']:
    #         self.context.report['max_consecutive_losses_money']['value'] = self.context.temp['consecutive_losses_money']
    #     self.context.report['total_net_profit']['value'] = self.context.report['gross_profit']['value'] - abs(
    #         self.context.report['gross_loss']['value'])
    #     #
    #     if self.context.report['total_trades']['value'] > 0:
    #         self.context.report['win_rate']['value'] = self.context.report['profit_trades']['value'] / self.context.report['total_trades']['value']
    #     #Total net profit rate
    #     if self.context.report['init_balance']['value'] > 0:
    #         self.context.report['total_net_profit_rate']['value'] = self.context.report['total_net_profit']['value'] / self.context.report['init_balance']['value']
    #     self.context.report['balance']['value'] = self.context.account['balance']
    #     #
    #     ratio = self.calculate_return_ratio()
    #     self.context.report['sharpe_ratio']['value'] = ratio['sharpe_ratio']
    #     self.context.report['sortino_ratio']['value'] = ratio['sortino_ratio']
    #
    #     return ret


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
        self.context.stop = True

    def init_data(self):
        """EATester"""
        # self.loc = {}
        self.import_module('pixiu.api.errors', self.context.safe_globals)
        self.current_api.set_fun(self.context.safe_globals)
        #
        for k in self.global_values:
            self.context.safe_globals[k] = self.global_values[k]
        #
        #clear print collection
        self.print_collection = None
        # self.context.account_info = {'data_raw': [], '__ds__': None}
        self.context.account_info = self.get_init_data('account_info', None)
        # self.price_info = {}
        self.context.symbol_data = {}
        self.context.tick_current_index = 0
        self.context.update_log_time = 0
        self.context.update_charts_time = 0
        self.context.last_update_order_log_index = 0
        self.context.last_update_account_log_index = 0
        self.context.last_update_print_log_index = 0
        self.context.last_update_charts_data_index = 0
        # self.cache = {}
        #
        self.context.order_logs = []
        self.context.account_logs = []
        self.context.print_logs = []
        self.context.symbol_properties = {}
        self.context.tick_info = None
        self.context.orders = self.get_init_data('orders', dict(symbol=self.context.symbol))
        self.context.sid = self.get_init_data('sid', dict(symbol=self.context.symbol))
        self.context.sid_data = self.get_init_data('sid_data', dict(symbol=self.context.symbol))
        self.context.cid = self.get_init_data('cid', None)
        self.context.cid_data = self.get_init_data('cid_data', None)

        sp = self.get_symbol_properties(self.context.symbol)
        if self.context.spread_point is None:
            self.context.spread_point = int(sp['spread'])
        self.context.price_digits = int(sp['digits'])
        self.context.volume_precision = int(math.log10(1/sp['volume_min']))
        self.context.spread_calculated = abs(self.context.spread_point * sp['point'])
        #
        if self.context.account['currency'] is None:
            self.context.account['currency'] = sp['currency_profit'].upper()
        #
        if self.context.account['currency'].upper() == sp['currency_base'].upper():
            self.__calculate_pip__ = self.__calculate_pip_with_base_currency__
        else:
            self.__calculate_pip__ = self.__calculate_pip_with_quote_currency__
        self.context.stop = False
        #
        self.init_report_data()

    def get_symbol_properties(self, symbol):
        ''''''
        return self.context.symbol_properties.get(symbol, self.context.default_symbol_properties[symbol])

    def calculate_margin_level(self):
        if self.context.account['margin'] == 0:
            return 0
        margin_level = self.context.account['equity'] / self.context.account['margin']
        return margin_level

    def __check_equity__(self, ):
        margin_level = self.calculate_margin_level()
        if margin_level == 0:
            return True, None
        if self.context.account['margin_so_so'] >= margin_level:
            # so: 91.1%/6.8/7.5
            # 91.1%, your equity at 6.8$ and your margin at 7.5$.
            comment = f"so: {round(margin_level*100, 1)}%/{self.context.account['equity']}/{self.context.account['margin']}"
            self.write_log(f"Stop Out: {comment}")
            return False, comment
        if self.context.account['margin_so_call'] >= margin_level:
            self.write_log(f"Margin Call: {round(margin_level*100, 1)}%/{self.context.account['equity']}/{self.context.account['margin']}")
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
        self.context.account['profit'] = profit
        # account
        check_next = True
        while check_next:
            ret, comment = self.__check_equity__()
            if ret:
                break
            symbol_orders = self.get_order_dict(self.context.symbol)
            check_next = False
            for order_uid in symbol_orders:
                order_dict = self.get_order(order_uid=order_uid)
                if not order_is_market(order_dict['cmd']):
                    continue
                errid, ret =self.close_order(order_uid, order_dict['volume'], 0, comment=comment)
                if errid == EID_OK:
                    check_next = True
                    break

        if self.context.account['balance'] <= self.context.balance_dead_line:
            dead = 1
            comment = "dead"
        elif self.context.account['balance'] + profit - self.context.account['margin'] <= self.context.balance_dead_line:
            dead = 2
            comment = "margin"

        if dead > 0:
            # self.close_all_orders(price, comment=comment)
            self.close_all_orders(0, comment=comment)
            return dead

        #update pending orders
        ds = self.context.orders['pending'].get('__ds__', None)
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

        def update_report_func(is_long, pf, trades):
            order_report[is_long]['profit'] += pf
            order_report[is_long]['trades'] += trades

        ds = self.context.orders['opened'].get('__ds__', None)
        if ds is not None:
            # result = ds[(ds['sl_p'] <= 0) | (ds['tp_p'] >= 0)]
            result = ds[((ds['sl'] > 0) & (ds['sl_p'] <= 0)) | ((ds['tp'] > 0) & (ds['tp_p'] >= 0))]
            for r in result:
                self.close_order(str(r['oid']), r['v'], None,
                                 comment='sl' if r['sl_p'] <= 0 else 'tp',
                                 update_report_func=update_report_func)

        #update reports
        for key in order_report:
            self.__update_report__(key, order_report[key]['profit'], order_report[key]['trades'])

        return dead

    def close_all_orders(self, price, comment):
        ''''''
        symbol_orders = self.get_order_dict(self.context.symbol).copy()
        for order_uid in symbol_orders:
            order_dict = self.get_order(order_uid=order_uid)
            self.close_order(order_uid, order_dict['volume'], price, comment=comment)
    #
    def calculate_returns(self, ):
        count = len(self.context.return_logs)
        if count < 2:
            return None
        column = 'equity'
        ret = pd.DataFrame(self.context.return_logs, columns=[column, ])
        ret['return'] = 0.0
        # calculate returns
        prev_return = 0.0
        for i, row in ret.iterrows():
            value = row[column]
            # r = math.log(value / prev_return) if prev_return != 0.0 else 0.0
            v = value / prev_return if prev_return != 0.0 else 0.0
            if v <= 0:
                r = v
            else:
                r = math.log(v)
            ret.at[i, 'return'] = r
            ret.at[i, 'negative_return'] = r if r < 0 else 0.0
            # ret.at[i, 'return'] = value / prev_return - 1 if prev_return != 0.0 else 0.0
            prev_return = value
        return ret

    def calculate_return_ratio(self):
        ret = {'sharpe_ratio': 0, 'sortino_ratio': 0}
        returns = self.calculate_returns()
        if returns is None:
            return ret
        count = returns.shape[0] - 1
        if count < 1:
            return ret
        #Sharpe
        mean = returns[1:]['return'].mean()
        for n in [('sharpe_ratio', 'return'), ('sortino_ratio', 'negative_return')]:
            std = returns[1:][n[1]].std(ddof=0)
            risk_free = 0.0
            ratio = (mean - risk_free) / std if std > 0 else 0.0
            ratio = math.sqrt(count) * ratio
            ret[n[0]] = ratio
        return ret

    def update_return_ratio(self,):
        ratio = self.calculate_return_ratio()
        self.context.report['sharpe_ratio']['value'] = ratio['sharpe_ratio']
        self.context.report['sortino_ratio']['value'] = ratio['sortino_ratio']

    def __update_account_log(self, ticket):
        ''''''
        price = self.Close()

        time = self.current_time()
        balance = round(self.context.account['balance'], self.context.default_digits)
        margin = round(self.context.account['margin'], self.context.default_digits)
        profit = self.context.account['profit']
        equity = round(balance + profit, self.context.default_digits)
        self.context.account['equity'] = equity
        free_margin = round(equity - margin, self.context.default_digits)
        self.context.account['free_margin'] = free_margin
        # see: https://www.mql5.com/en/forum/46654
        # Margin level percentage = Equity/Margin * 100 %
        if margin != 0:
            # self.context.account['margin_level'] = round(equity / margin * 100, self.context.default_digits)
            self.context.account['margin_level'] = round((equity - margin) / margin * 100, self.context.default_digits)

        # self.add_account_log(dict(time=str(datetime.fromtimestamp(time)), balance=balance, margin=margin,
        self.add_account_log(dict(time=str(datetime.utcfromtimestamp(time)), balance=balance, margin=margin,
                                   equity=equity, free_margin=free_margin,
                                   profit=profit))

        self.add_print_log()
        #


    def last_price_time(self, symbol):
        if symbol == self.context.symbol:
            return self.current_time()
        #
        serials = self.get_data_series(symbol)
        if serials is None or len(serials.index) == 0:
            return None
        if isinstance(serials.index[self.context.tick_current_index], pd.Timestamp):
            return serials.index[self.context.tick_current_index].to_pydatetime()
        return serials.index[self.context.tick_current_index]


    def current_time(self):
        return self.context.tick_info['t'][self.context.tick_current_index]

    #
    def on_before_execute(self, sync=False):
        return 0

    def execute(self, ticket, sync=False):
        self.context.ticket = ticket
        if self.on_before_execute(sync) != 0:
            return None
        if sync:
            self.execute_(self.context.ticket,)
        else:
            thread = threading.Thread(target=self.execute_,
                             args=(self.context.ticket,))
            thread.start()
        return self.context.ticket

    def execute_script(self, ticket, sync=False):
        self.context.ticket = ticket
        if self.on_before_execute(sync) != 0:
            return None
        if sync:
            self.execute_script_(self.context.ticket, )
        else:
            thread = threading.Thread(target=self.execute_script_,
                             args=(self.context.ticket,))
            thread.start()
        return self.context.ticket

    def get_price_count(self, symbol, tf_str='1m'):
        di = self.get_data_info(symbol, tf_str)
        return di['count']

    def on_begin_tick(self, *args, **kwargs):
        return 0

    def on_pre_load_ticks(self, *args, **kwargs):
        self.write_log(f"Loading ticks (tf: {self.context.tick_timeframe}), please wait ...\n")
        return 0

    def on_end_tick(self, *args, **kwargs):
        return 0

    def on_begin_execute(self, *args, **kwargs):
        return 0

    def on_end_execute(self, *args, **kwargs):
        return 0

    def on_execute_status(self, ticket, status, *args, **kwargs):
        self.write_log(f"{ticket}: {status}")

    def on_execute_exception(self):
        idx = 0
        for exc in sys.exc_info():
            log.error(f"exc:{idx}: {str(exc)}")
            idx += 1
        tb_next = sys.exc_info()[2]
        exception = "Exception:\n"
        while tb_next is not None:
            if tb_next.tb_frame.f_code.co_filename == '<inline>':
                exception += "  line %d, in %s \n" % (tb_next.tb_lineno, tb_next.tb_frame.f_code.co_name)
            tb_next = tb_next.tb_next
        return exception

    def execute_(self, ticket):
        """"""
        exception_msg = None
        errid = EID_OK
        update_log_task = None
        exception_message = None
        try:
            self.context.set_error(EID_OK, 'EID_OK')
            test_start_time = datetime.now()
            pixiu_version = pkg_resources.get_distribution('pixiu').version
            self.write_log(
                f"\n\n == PiXiu({pixiu_version}) Backtesting Start: {test_start_time}, Ticket: {ticket}, Symbol: {self.context.symbol}, Period: {self.context.start_time} - {self.context.end_time}, "
                f"Timeframe: {self.context.tick_timeframe}, Mode: {self.context.tick_mode} == \n\n")
            self.write_log(f"\n Script Settings:  {self.context.script_settings} \n\n")
            #
            valid_script_settings = self.context.script_metadata.get('valid_script_settings', None)
            if valid_script_settings is not None:
                if not valid_script_settings['success']:
                    errmsg = valid_script_settings.get('errmsg', None)
                    exception_message = f"ValidScriptSettings Error: {errmsg}"
                    self.context.set_error(EID_EAT_ERROR, exception_message)
                    raise Exception(exception_message)
            #
            self.init_data()
            self.context.update_log_task_running = True
            self.on_pre_load_ticks()

            expiration = 900  # 900s
            self.on_load_ticks()

            count = self.context.tick_info.size
            self.context.tick_current_index = self.context.tick_start_index

            self.write_log(f"Tick Count: {count}, Tick Max Count: {self.context.tick_max_index}")
            status = dict(current=self.context.tick_current_index, max=count, errid=0)
            self.context.report['ticks']['value'] = status['max']
            self.on_execute_status(ticket, status)
            self.on_begin_execute()
            last_call_status_time = 0
            # for i in range(count):
            for i in range(self.context.tick_start_index, count):
                try:
                    #
                    self.context.reset_flags()
                    if i == self.context.tick_start_index:
                        self.context.flags |= EATester.FM_START
                    if self.context.tick_max_index is not None and i >= self.context.tick_max_index > 0:
                        break
                    if self.context.stop:
                        self.context.set_error(EID_EAT_TEST_STOP, 'EID_EAT_TEST_STOP')
                        raise PXErrorCode(EID_EAT_TEST_STOP)
                    #
                    self.on_begin_tick()
                    self.set_account(self.context.account, expiration=expiration)
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
                            self.context.set_error(EID_EAT_NOT_ENOUGH_MONEY, 'EID_EAT_NOT_ENOUGH_MONEY')
                            raise PXErrorCode(EID_EAT_NOT_ENOUGH_MONEY)
                        else:
                            self.context.set_error(EID_EAT_EA_DEAD, 'EID_EAT_EA_DEAD')
                            raise PXErrorCode(EID_EAT_EA_DEAD)
                    # self.context.tick_current_index += 1
                    self.on_end_tick()
                    self.context.tick_current_index += 1
                except Exception as exc:
                    if isinstance(exc, AssertionError):
                        raise exc
                    traceback.print_exc()
                    exception_msg = self.on_execute_exception()
                    errid = EID_EAT_ERROR
                    last_errid, last_errmsg = self.context.get_error()
                    if last_errid == EID_OK:
                        self.context.set_error(EID_EAT_ERROR, exception_msg)
                    break
            #
            self.context.flags |= EATester.FM_END
            try:
                if self.context.tick_current_index >= count:
                    self.context.tick_current_index = count - 1
                self.close_all_orders(self.Close(), comment="stop")
                self.__update_account_log(ticket)
                # update return
                self.update_return_ratio()
            except:
                traceback.print_exc()
            self.on_end_execute()

            # self.write_log(f"\n\n == Execute PiXiu backtesting end: {datetime.now()}, ticket: {ticket} == \n\n")
            test_end_time = datetime.now()
            self.write_log(
                f"\n\n == PiXiu Backtesting End: {test_end_time}, Total Time: {(test_end_time - test_start_time).total_seconds()} sec, Ticket: {ticket} == \n\n")
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
            if exception_message is None:
                exception_message = "Unknown errors, terminated. \n"
            status["exception"] = exception_message
            status["errid"] = 0
            status["stop"] = 1
            self.on_execute_status(ticket, status)

    def execute_script_(self, ticket):
        """"""
        try:
            test_start_time = datetime.now()
            pixiu_version = pkg_resources.get_distribution('pixiu').version
            self.write_log(
                f"\n\n == PiXiu({pixiu_version}) Backtesting Start: {test_start_time}, Ticket: {ticket}, Symbol: {self.context.symbol}, Period: {self.context.start_time} - {self.context.end_time}, "
                f"Timeframe: {self.context.tick_timeframe}, Mode: {self.context.tick_mode} == \n\n")
            self.init_data()
            self.context.update_log_task_running = True
            self.on_pre_load_ticks()
            #
            expiration = 900  # 900s
            self.on_load_ticks()
            #
            count = self.context.tick_info.size
            #
            self.write_log(f"Tick Count: {count}, Tick Max Count: {self.context.tick_max_index}")
            status = dict(current=self.context.tick_current_index, max=count, errid=0)
            self.context.report['ticks']['value'] = status['max']
            self.on_execute_status(ticket, status)
            self.on_begin_execute()
            last_call_status_time = 0
            try:
                #
                self.do_tick()
                while True:
                    # if self.context.stop:
                    #     raise PXErrorCode(EID_EAT_TEST_STOP)
                    #read command
                    # cmd = input('p>>')
                    cmd = f"print(GetOpenedOrderUIDs())"
                    byte_code = EABase.compile(cmd)
                    #execute command
                    # exec(cmd, self.context.safe_globals)
                    exec(byte_code, self.context.safe_globals)
                    #output result
            except Exception as exc:
                if isinstance(exc, AssertionError):
                    raise exc
                traceback.print_exc()
                exception_msg = self.on_execute_exception()
                errid = EID_EAT_ERROR
            self.on_end_execute()

        except Exception as exc:
            if isinstance(exc, AssertionError):
                raise exc
            # traceback.print_exc()
            # status = {}
            # status["exception"] = "Unknown errors, terminated. \n"
            # status["errid"] = 0
            # status["stop"] = 1
            # self.on_execute_status(ticket, status)

