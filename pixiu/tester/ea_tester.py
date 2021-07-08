
import sys

import json
import threading
import importlib
from datetime import (datetime, )
import numpy as np
from RestrictedPython import (compile_restricted, safe_globals, utility_builtins,)
from ..base.ea_base import (EABase)
from .tester_api_v1 import (TesterAPI_V1, )
import pandas as pd
from pixiu.api.errors import *
from pixiu.api import (TimeFrame, OrderCommand, order_is_long, order_is_short, order_is_market, order_is_stop,
                       order_is_limit, order_is_pending)
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
        if not self.write_log(*objects):
            print(*objects, **kwargs)


#---------------------------------------------------------------------------------------------------------------------
# EATester
#---------------------------------------------------------------------------------------------------------------------
class TickMode():
    EVERY_TICK = 100
    ONLY_OPEN = 200


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
        self.log_file = None
        self.log_path = params.get("log_path", None)
        #
        if self.log_path:
            self.log_file = open(self.log_path, mode='at')

        if self.script_path is None:
            self.script = params["script"]
        #
        self.script_settings = None
        try:
            ss = params.get("script_settings", None)
            if ss:
                self.script_settings = json.loads(ss)
        except:
            traceback.print_exc()
        #
        self.byte_code = None
        self.orders = None
        self.order_logs = []
        self.account_logs = []
        self.balance_dead_line = 0.0
        self.account = params.get("account", None)
        if self.account is None:
            balance = round(float(params['balance']), self.default_digits)
            self.account = {'balance': balance,
                            'equity': balance,
                            'margin': 0,
                            'free_margin': balance,
                            'credit': 0.0,
                            'profit': 0.0,
                            'margin_level': 0,
                            #static
                            'leverage': params.get('leverage', 100),
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
                            'margin_so_call': 0.0,
                            'margin_so_so': 0.0,
                            'commission': 0.0,
                            }


        self.report = {
                        'init_balance': {'value': self.account['balance'], 'desc': 'Init Balance'}, #
                        'ticks': {'value': 0, 'desc': 'Ticks'}, #
                        'total_net_profit': {'value': 0, 'desc': 'Total net profit'}, #
                        'absolute_drawdown': {'value': 0, 'desc': 'Absolute Drawdown'}, #
                        'max_drawdown': {'value': 0, 'desc': 'Max Drawdown'}, #
                        'total_trades': {'value': 0, 'desc': 'Total Trades'},#
                        'profit_trades': {'value': 0, 'desc': 'Profit Trades'},#
                        'trade_max_profit': {'value': 0, 'desc': 'Trade Max Profit'}, #
                        'trade_avg_profit': {'value': 0, 'desc': 'Trade Avg Profit'}, #
                        'trade_max_loss': {'value': 0, 'desc': 'Trade Max Loss'}, #
                        'trade_avg_loss': {'value': 0, 'desc': 'Trade Avg Loss'}, #
                        'loss_trades': {'value': 0, 'desc': 'Loss Trades'}, #
                        'gross_profit': {'value': 0, 'desc': 'Gross Profit'}, #
                        'gross_loss': {'value': 0, 'desc': 'Gross Loss'}, #
                        'short_positions': {'value': 0, 'desc': 'Short Positions'}, #
                        'short_positions_win': {'value': 0, 'desc': 'Short Positions Win'}, #
                        'long_positions': {'value': 0, 'desc': 'Long Positions'}, #
                        'long_positions_win': {'value': 0, 'desc': 'Long Positions Win'}, #
                        'max_consecutive_wins': {'value': 0, 'desc': 'Max Consecutive Wins'}, #
                        'max_consecutive_wins_money': {'value': 0, 'desc': 'Max Consecutive Wins Money'}, #
                        'max_consecutive_losses': {'value': 0, 'desc': 'Max Consecutive Losses'}, #
                        'max_consecutive_losses_money': {'value': 0, 'desc': 'Max Consecutive Losses Money'}, #
        }
        self.temp = {
            'consecutive_wins': 0,
            'consecutive_wins_money': 0,
            'consecutive_losses': 0,
            'consecutive_losses_money': 0,
        }
        self.print_collection = None
        #
        self.current_api = TesterAPI_V1(tester=self, data_source={}, default_symbol=params["symbol"])


    def get_print_factory(self, _getattr_=None):
        """print factory"""
        if self.print_collection is None:
            self.print_collection = EATesterPrintCollector(_getattr_, self.write_log)
        return self.print_collection

    def write_log(self, *args, **kwargs):
        print_ = kwargs.get('print_', True)
        if print_:
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
    # def write_log(self, log_str, print_=True):
    #     if print_:
    #         print(log_str)
    #     #
    #     if self.log_file:
    #         self.log_file.write(str(log_str))
    #         self.log_file.write('\n')
    #     return True
    #

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
        if margin > self.account['balance'] - self.account['margin']:
            return EID_EAT_MARGIN_CALL, -1
        new_order['uid'] = str(new_order['ticket'])
        new_order['comment'] = f"cuid#{new_order['uid']}|"
        new_order['margin'] = margin
        commission = 0.0
        #commissions
        if self.commission > 0:
            # see: https://www.houseofborse.com/commission-calculation
            # all commission charged and debited on the opening of the trade
            commission = new_order['volume'] * self.commission * self.__calculate_pip__(new_order['open_price']) * 2
        if commission > self.account['balance'] - self.account['margin']:
            return EID_EAT_MARGIN_CALL, -1
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
        self.account['margin'] = self.account['margin'] + new_order['margin']
        self.account['commission'] = self.account['commission'] + new_order['commission']

        #report
        self.report['total_trades']['value'] += 1
        if order_is_long(new_order['cmd']):
            self.report['long_positions']['value'] += 1
        else:
            self.report['short_positions']['value'] += 1

        #
        return EID_OK, new_order['uid']

    def __active_pending_order__(self, order_uid, price, comment=None):
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
        order_dict['open_time'] = self.current_time()
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
        order_list.pop(order['uid'])
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
        order_list.pop(order['uid'])
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


    def __calculate_profit__(self, price):
        ''''''
        profit = 0
        ds = self.orders['opened'].get('__ds__', None)
        if ds is not None:
            pips = self.__calculate_pip__(price)
            ds['pf'] = pips * (price - ds['o']) * ds['v'] * ds['tcs'] * ds['pf_f']
            ds['sl_p'] = (price - ds['sl']) * ds['pf_f']
            ds['tp_p'] = (price - ds['tp']) * ds['pf_f']
            profit = ds['pf'].sum()
        return profit

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

    def get_order_dict(self, symbol, status="opened", script_name=None):
        """"""
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
                    if open_price < price:
                        return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_limit(order_dict['cmd']):
                    if open_price <= price:
                        return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_stop(order_dict['cmd']):
                    if open_price >= price:
                        return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
                else:
                    return EID_EAT_INVALID_ORDER_TYPE

            #close
            elif stage == 2:
                if price is not None:
                    if price > 0 and price > self.Bid():
                        return EID_EAT_INVALID_ORDER_CLOSE_PRICE

            if stage != 2:
                if stop_loss > 0 and take_profit > 0 and stop_loss > take_profit:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
                if take_profit > 0 and take_profit <= price:
                    return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                if stop_loss > 0 and stop_loss >= price:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
        #sell
        elif order_is_short(order_dict['cmd']):
            # open
            if stage == 0 or (stage == 1 and order_is_pending(order_dict['cmd'])):
                if order_is_market(order_dict['cmd']):
                    if open_price > price:
                        return EID_EAT_INVALID_MARKET_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_limit(order_dict['cmd']):
                    if open_price >= price:
                        return EID_EAT_INVALID_LIMIT_ORDER_OPEN_PRICE
                elif open_price is not None and order_is_stop(order_dict['cmd']):
                    if open_price <= price:
                        return EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE
                else:
                    return EID_EAT_INVALID_ORDER_TYPE
            #close
            elif stage == 2:
                if price is not None:
                    if price > 0 and price < self.Ask():
                        return EID_EAT_INVALID_ORDER_CLOSE_PRICE

            #
            if stage != 2:
                if stop_loss > 0 and take_profit > 0 and stop_loss < take_profit:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS
                if stop_loss > 0 and stop_loss <= price:
                    return EID_EAT_INVALID_ORDER_TAKE_PROFIT
                if take_profit > 0 and take_profit >= price:
                    return EID_EAT_INVALID_ORDER_STOP_LOSS

        return EID_OK

    def __new_ticket__(self):
        return str(self.orders['counter'] + 1)

    def open_order(self, symbol, cmd, price, volume, stop_loss, take_profit, comment=None, ext_check_open_range=0,
                       ext_check_order_hold_count=0, magic_number=None, slippage=None, arrow_color=None):
        """"""
        order_uid = None
        account = self.account
        if self.orders['opened_counter'] >= account['limit_orders']:
            return EID_EAT_LIMIT_ORDERS, None
        if stop_loss is None:
            stop_loss = 0.0
        if take_profit is None:
            take_profit = 0.0

        order_dict = dict(ticket=self.__new_ticket__(), symbol=symbol, cmd=cmd, open_price=price,
                         volume=volume, stop_loss=stop_loss, take_profit=take_profit, margin=0, comment=comment,
                         magic_number=magic_number, open_time=self.current_time(), commission=0,
                         close_time=None, close_price=np.nan, profit=0.0)
        errid = self.__valid_order__(0, order_dict, self.Close())
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
                                 balance=None, profit=None))


        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)
    #

    def modify_order(self, order_uid, price, stop_loss, take_profit, comment=None, arrow_color=None,
                     expiration=None):
        """"""
        order_dict = self.get_order(order_uid=order_uid)
        if order_dict is None:
            return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, command_uid=None, sync=True)
        if order_dict['symbol'] != self.symbol:
            return EID_EAT_INVALID_SYMBOL, dict(order_uid=order_uid, command_uid=None, sync=True)
        order_tmp = order_dict.copy()
        order_tmp['stop_loss'] = stop_loss
        order_tmp['take_profit'] = take_profit
        order_tmp['comment'] = comment
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
        errid = self.__valid_order__(1, order_tmp, close_price)
        if errid != EID_OK:
            return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        #
        order_dict['open_price'] = order_tmp['open_price']
        order_dict['stop_loss'] = order_tmp['stop_loss']
        order_dict['take_profit'] = order_tmp['take_profit']
        order_dict['comment'] = order_tmp['comment']
        self.__modify_order__(order_dict)

        #
        self.add_order_log(dict(ticket=order_dict['ticket'],
                                 time=str(datetime.fromtimestamp(self.current_time())),
                                 type="MODIFY",
                                 size=order_dict['volume'], price=round(price, self.price_digits),
                                 stop_loss=round(stop_loss, self.price_digits),
                                 take_profit=round(take_profit, self.price_digits),
                                 profit=round(order_dict['profit'], self.default_digits),
                                 balance=round(self.account["balance"] + order_dict['profit'], self.default_digits),
                                 comment=comment))
        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)

    def __order_close_price__(self, order_dict):
        if order_is_market(order_dict['cmd']):
            return self.Bid() if order_is_long(order_dict['cmd']) else self.Ask()
        else:
            return 0


    def close_order(self, order_uid, volume, price, slippage=None, comment=None, arrow_color=None,
                    update_report_func=None):
        """Close order"""
        order_dict = self.get_order(order_uid=order_uid)
        if order_dict is None:
            return EID_EAT_INVALID_ORDER_TICKET, dict(order_uid=order_uid, command_uid=None, sync=True)
        # if volume is None:
        #     return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
        if volume is None or volume <= 0:
            volume = float(order_dict['volume'])
        if price is None or price <= 0:
            price = self.__order_close_price__(order_dict)
        #
        close_time = self.current_time()
        if order_is_market(order_dict['cmd']):
            symbol = order_dict['symbol']
            if volume > order_dict['volume']:
                return EID_EAT_INVALID_ORDER_VOLUME, dict(order_uid=order_uid, command_uid=None, sync=True)
            #
            errid  = self.__valid_order__(2, order_dict, price)
            if errid != EID_OK:
                return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
            order_dict['comment'] = comment
            order_dict['close_time'] = close_time
            order_dict['close_price'] = price
            order_uid = self.__remove_order__(order_dict)
            self.account["balance"] = self.account["balance"] + order_dict['profit']
            closed_margin = order_dict['margin'] * volume / order_dict['volume']
            self.account["margin"] = self.account["margin"] - closed_margin
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
                    return errid, dict(order_uid=order_uid, command_uid=None, sync=True)
        else:
            order_uid = self.__remove_pending_order__(order_dict)

        #
        self.add_order_log(dict(uid=order_dict['uid'], ticket=order_dict['ticket'],
                                    time=str(datetime.fromtimestamp(close_time)),
                                    type="CLOSE", volume=order_dict['volume'],
                                    price=round(price, self.price_digits),
                                    stop_loss=round(order_dict['stop_loss'], self.price_digits),
                                    take_profit=round(order_dict['take_profit'], self.price_digits),
                                    balance=round(self.account["balance"], self.default_digits),
                                    profit=round(order_dict['profit'], self.default_digits),
                                    comment=comment))

        return EID_OK, dict(order_uid=order_uid, command_uid=None, sync=True)


    def wait_command(self, uid, timeout=120):
        return 0, {}

    def acquire_lock(self, name, timeout=60):
        return True

    def release_lock(self, name):
        pass

    #
    def Ask(self, shift=0):
        ask = self.tick_info['a'][self.current_tick_index - shift]
        if ask == 0:
            ask = self.Bid(shift) + self.spread_calculated
        return ask

    def Bid(self, shift=0):
        bid = self.tick_info['b'][self.current_tick_index - shift]
        if bid == 0:
            bid = self.Close(shift)
        return bid

    def Close(self, shift=0):
        return self.tick_info['c'][self.current_tick_index - shift]

    def Open(self, shift=0):
        return self.tick_info['o'][self.current_tick_index - shift]

    def High(self, shift=0):
        return self.tick_info['h'][self.current_tick_index - shift]

    def Low(self, shift=0):
        return self.tick_info['l'][self.current_tick_index - shift]

    def Time(self, shift=0) -> datetime:
        return datetime.fromtimestamp(self.tick_info['t'][self.current_tick_index - shift])

    def Volume(self, shift=0) -> float:
        return self.tick_info['v'][self.current_tick_index - shift]
    #
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
        else:
            self.report['loss_trades']['value'] += trades
            self.report['gross_loss']['value'] = self.report['gross_loss']['value'] + profit
            self.report['max_drawdown']['value'] = self.report['gross_loss']['value']
            self.report['trade_avg_loss']['value'] = self.report['gross_loss']['value'] / self.report['loss_trades'][
                'value']

            if self.report['trade_max_loss']['value'] < profit:
                self.report['trade_max_loss']['value'] = profit

            self.temp['consecutive_losses'] += trades
            self.temp['consecutive_losses_money'] = self.temp['consecutive_losses_money'] + profit
            self.temp['consecutive_wins'] = 0
            self.temp['consecutive_wins_money'] = 0
        #
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
        if self.report['total_net_profit']['value'] < 0:
            self.report['absolute_drawdown']['value'] = abs(self.report['total_net_profit']['value'])

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
        self.last_update_order_log_index = 0
        self.last_update_account_log_index = 0
        self.last_update_print_log_index = 0
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
        self.price_digits =  int(sp['digits'])
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

    def get_symbol_properties(self, symbol):
        ''''''
        return self.symbol_properties.get(symbol, self.default_symbol_properties[symbol])

    #
    def __process_order__(self, price, last_price):
        ''''''
        comment = None
        dead = 0
        # equity
        profit = self.__calculate_profit__(price)
        self.account['profit'] = profit
        # account
        if self.account['balance'] <= self.balance_dead_line:
            dead = 1
            comment = "dead"
        elif self.account['balance'] + profit - self.account['margin'] <= self.balance_dead_line:
            dead = 2
            comment = "margin"

        if dead > 0:
            self.close_all_orders(price, comment=comment)
            return dead

        #update pending orders
        ds = self.orders['pending'].get('__ds__', None)
        if ds is not None:
            # if last_price is not None:
            result = ds[((ds['cid'] == 110) & (ds['o'] > last_price) & (ds['o'] <= price)) |
                        ((ds['cid'] == 210) & (ds['o'] < last_price) & (ds['o'] >= price)) |
                        ((ds['cid'] == 120) & (ds['o'] < last_price) & (ds['o'] >= price)) |
                        ((ds['cid'] == 220) & (ds['o'] > last_price) & (ds['o'] <= price))
                        ]
            for r in result:
                self.__active_pending_order__(str(r['oid']), price, comment='open')


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
                self.close_order(str(r['oid']), price, r['v'],
                                 comment='sl' if r['sl_p'] <= 0 else 'tp',
                                 update_report_func=update_report_func)

        #update reports
        for key in order_report:
            self.__update_report__(key, order_report[key]['profit'], order_report[key]['trades'])

        return dead
    #
    def close_all_orders(self, price, comment):
        ''''''
        symbol_orders = self.get_order_dict(self.symbol).copy()
        for order_uid in symbol_orders:
            order_dict = self.get_order(order_uid=order_uid)
            self.close_order(order_uid, price, order_dict['volume'], comment=comment)
    #
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
            self.account['margin_level'] = equity / margin * 100

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
            self.write_log(f"\n\n == Execute PiXiu backtesting: {datetime.now()}, ticket: {ticket}, symbol: {self.symbol}, period: {self.start_time} - {self.end_time}, "
                           f"tick_timeframe: {self.tick_timeframe}, tick_mode: {self.tick_mode} == \n\n")
            self.init_data()
            self.update_log_task_running = True
            self.on_pre_load_ticks()

            expiration = 900 #900s
            self.on_load_ticks()

            count = self.tick_info.size

            self.write_log(f"execute start ... count={count}, tick_max_count={self.tick_max_count}")
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
                    last_c_price = self.Close(1)
                    c_price = self.Close()
                    exit = self.__process_order__(c_price, last_c_price)
                    #
                    if exit == 0:
                        self.do_tick()
                    self.__update_account_log(ticket)
                    # #
                    if exit != 0:
                        if exit == 2:
                            raise PXErrorCode(EID_EAT_MARGIN_CALL)
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

            self.write_log(f"\n\n == Execute PiXiu backtesting end: {datetime.now()}, ticket: {ticket} == \n\n")
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
