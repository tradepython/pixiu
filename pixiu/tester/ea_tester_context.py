
from pixiu.api.errors import *
from pixiu.api import (TimeFrame, OrderCommand, order_is_long, order_is_short, order_is_market, order_is_stop,
                       order_is_limit, order_is_pending, OrderStatus)
import logging
log = logging.getLogger(__name__)

#---------------------------------------------------------------------------------------------------------------------
# EATesterContext
#---------------------------------------------------------------------------------------------------------------------
class TickMode():
    EVERY_TICK = 100
    ONLY_OPEN = 200

class EATesterContext:

    def __init__(self, params):
        self.ctx = dict(
            errid=0,
            errmsg='',
            flags=0,
            ticket=None,
            # language='en',
            symbol=params.get('symbol', None),
            byte_code=None,
            script=None,
            script_path=params.get("script_path", None),
            script_settings=None,
            script_libs=params.get("script_libs", None),
            last_exec_time=0,
            safe_globals=None, #copy_globals(),
            # global_values=params.get('global_values', {}),
            loc={},
            # df_columns=('t', 's', 'o', 'h', 'l', 'c', 'v', 'a', 'b'),
            ea_log_callback=params.get('ea_log_callback', None),
            add_ea_settings=None,
#
            # errid=None,
            # errmsg=None,
            # flags=0,
            default_digits=params.get("default_digits", 2),
            # symbol=params["symbol"],
            persistent_data=None,
            symbol_properties={},
            default_symbol_properties=params.get("symbol_properties", None),
            spread_point=params.get("spread_point", None),
            commission=params.get("commission", 0),  # commission / a lot
            tick_mode=params.get("tick_mode", TickMode.EVERY_TICK),
            tick_timeframe=params.get("tick_timeframe", TimeFrame.M1),
            tick_max_index=params.get('tick_max_index', None),
            tick_start_index=params.get('tick_start_index', 0),
            start_time=params.get('start_time', None),
            end_time=params.get('end_time', None),
            language=params.get("language", 'en'),
            # script_path=params.get("script_path", None),
            # script_libs=params.get("script_libs", None),
            log_path=params.get("log_path", None),
            print_log_type=params.get("print_log_type", ['account', 'ea', 'order', 'report']),
            print_collection=None,
            # add_ea_settings=None,
            # safe_globals=None,
            # script_settings=None,
            # byte_code=None,
            orders=None,
            order_logs=[],
            charts_data=[],
            account_logs=[],
            return_logs=[],
            balance_dead_line=params.get("balance_dead_line", 0.0),
            account=params.get("account", None),
            #
            log_file=None,
            tick_info = None
            )

        #
        # margin_so_so = self.percent_str_to_float(params.get("margin_so_so", None), 1.0)  # 100%
        # if margin_so_so < 0:
        #     margin_so_so = 1.0
        # margin_so_call = self.percent_str_to_float(params.get("margin_so_call", None), margin_so_so * 1.2)  # 120%
        # if margin_so_call < 0:
        #     margin_so_call = margin_so_so * 1.2
        #
        if self.log_path:
            # self.log_file = open(self.log_path, mode='at')
            self.ctx['log_file'] = open(self.log_path, mode='wt')

        if self.script_path is None:
            self.ctx['script'] = params.get("script", None)
        else:
            self.ctx['script'] = open(self.script_path).read()
        #
        # self.script_metadata = self.parse_script(self.script)
        # if self.script_libs is None:
        #     self.script_libs = self.load_libs(
        #         json.loads(self.script_metadata.get('lib', self.script_metadata.get('library', '[]'))))
        #
        # try:
        #     # ss = params.get("script_settings", self.script_metadata.get('script_settings', None))
        #     ss = self.script_metadata.get('script_settings', params.get("script_settings", None))
        #     if isinstance(ss, str):
        #         self.script_settings = json.loads(ss)
        #     else:
        #         self.script_settings = ss
        # except:
        #     traceback.print_exc()
        #
        # self.byte_code = None
        # self.orders = None
        # self.order_logs = []
        # self.charts_data = []
        # self.account_logs = []
        # self.return_logs = []
        # self.balance_dead_line = 0.0
        # self.account = params.get("account", None)
        # if self.account is None:
        #     balance = round(float(params['balance']), self.default_digits)
        #     equity = balance
        #     try:
        #         leverage = float(params.get('leverage', 100))
        #     except:
        #         leverage = 100
        #     init_values = dict(
        #         balance=balance, equity=balance, free_margin=balance,
        #         currency=params.get("currency", None), leverage=leverage,
        #         margin_so_call=margin_so_call,
        #         margin_so_so=margin_so_so)
        #     self.account = self.get_init_data('account', init_values)
        # else:
        #     default_value = {'equity': self.account['balance'], 'margin': 0, 'free_margin': self.account['balance']}
        #     for k in default_value:
        #         if k not in self.account:
        #             self.account[k] = default_value[k]
        # self.current_api = self.get_api()
        # self.data = {DataScope.EA_VERSION: {}, DataScope.EA: {}, DataScope.ACCOUNT: {}, DataScope.EA_SETTIGNS: {}}
        # self.data = self.get_init_data('data', None)
        self.set_error(EID_OK, 'EID_OK')
        #
        self.reset_flags()

    # ---------------------------------------------
    # base
    # ---------------------------------------------
    def get_error(self):
        return self.errid, self.errmsg

    def set_error(self, errid, errmsg):
        self.errid = errid
        self.errmsg = errmsg

    def reset_flags(self):
        self.flags = 0
        # self.flags = dict(max_drawdown_updated=False, trade_max_loss_updated=False,
        #                   max_consecutive_wins_updated=False, max_consecutive_losses_updated=False)
    @property
    def ticket(self):
        return self.ctx['ticket']

    @ticket.setter
    def ticket(self, value):
        self.ctx['ticket'] = value

    @property
    def errid(self):
        return self.ctx['errid']

    @errid.setter
    def errid(self, value):
        self.ctx['errid'] = value

    @property
    def errmsg(self):
        return self.ctx['errmsg']

    @errmsg.setter
    def errmsg(self, value):
        self.ctx['errmsg'] = value

    @property
    def flags(self):
        return self.ctx['flags']

    @flags.setter
    def flags(self, value):
        self.ctx['flags'] = int(value)

    @property
    def language(self):
        return self.ctx['language']

    @property
    def symbol(self):
        return self.ctx['symbol']

    @property
    def byte_code(self):
        return self.ctx['byte_code']

    @byte_code.setter
    def byte_code(self, value):
        self.ctx['byte_code'] = value

    @property
    def script(self):
        return self.ctx['script']

    @property
    def script_path(self):
        return self.ctx['script_path']

    @property
    def script_settings(self):
        return self.ctx['script_settings']

    @script_settings.setter
    def script_settings(self, value):
        self.ctx['script_settings'] = value

    @property
    def script_libs(self):
        return self.ctx['script_libs']

    @script_libs.setter
    def script_libs(self, value):
        self.ctx['script_libs'] = value

    @property
    def last_exec_time(self):
        return self.ctx['last_exec_time']

    @last_exec_time.setter
    def last_exec_time(self, value):
        self.ctx['last_exec_time'] = value

    @property
    def safe_globals(self):
        return self.ctx['safe_globals']

    @safe_globals.setter
    def safe_globals(self, value):
        self.ctx['safe_globals'] = value

    @property
    def loc(self):
        return self.ctx['loc']

    @property
    def ea_log_callback(self):
        return self.ctx['ea_log_callback']

    @property
    def add_ea_settings(self):
        return self.ctx['add_ea_settings']

    @add_ea_settings.setter
    def add_ea_settings(self, value):
        self.ctx['add_ea_settings'] = value

    # ---------------------------------------------
    @property
    def log_path(self):
        return self.ctx['log_path']

    @property
    def log_file(self):
        return self.ctx['log_file']

    @property
    def account(self):
        return self.ctx['account']

    @account.setter
    def account(self, value):
        self.ctx['account'] = value

    @property
    def default_digits(self):
        return self.ctx['default_digits']

    # @property
    # def symbol(self):
    #     return self.ctx['symbol']

    @property
    def start_time(self):
        return self.ctx['start_time']

    @property
    def end_time(self):
        return self.ctx['end_time']

    @property
    def tick_timeframe(self):
        return self.ctx['tick_timeframe']

    @property
    def tick_mode(self):
        return self.ctx['tick_mode']

    @property
    def default_symbol_properties(self):
        return self.ctx['default_symbol_properties']

    @property
    def tick_start_index(self):
        return self.ctx['tick_start_index']

    @tick_start_index.setter
    def tick_start_index(self, value):
        self.ctx['tick_start_index'] = int(value)

    @property
    def tick_current_index(self):
        return self.ctx['tick_current_index']

    @tick_current_index.setter
    def tick_current_index(self, value):
        self.ctx['tick_current_index'] = int(value)

    @property
    def tick_max_index(self):
        return self.ctx['tick_max_index']

    @tick_max_index.setter
    def tick_max_index(self, value):
        self.ctx['tick_max_index'] = int(value)

    @property
    def balance_dead_line(self):
        return self.ctx['balance_dead_line']

    @property
    def return_logs(self):
        return self.ctx['return_logs']

    @property
    def commission(self):
        return self.ctx['commission']

    @property
    def print_log_type(self):
        return self.ctx['print_log_type']

    @property
    def account_info(self):
        return self.ctx['account_info']

    @account_info.setter
    def account_info(self, value):
        self.ctx['account_info'] = value

    @property
    def tick_info(self):
        return self.ctx['tick_info']

    @tick_info.setter
    def tick_info(self, value):
        self.ctx['tick_info'] = value

    @property
    def persistent_data(self):
        return self.ctx['persistent_data']

    @persistent_data.setter
    def persistent_data(self, value):
        self.ctx['persistent_data'] = value

    @property
    def symbol_data(self):
        return self.ctx['symbol_data']

    @symbol_data.setter
    def symbol_data(self, value):
        self.ctx['symbol_data'] = value

    @property
    def update_log_time(self):
        return self.ctx['update_log_time']

    @update_log_time.setter
    def update_log_time(self, value):
        self.ctx['update_log_time'] = value

    @property
    def update_charts_time(self):
        return self.ctx['update_charts_time']

    @update_charts_time.setter
    def update_charts_time(self, value):
        self.ctx['update_charts_time'] = value

    @property
    def last_update_order_log_index(self):
        return self.ctx['last_update_order_log_index']

    @last_update_order_log_index.setter
    def last_update_order_log_index(self, value):
        self.ctx['last_update_order_log_index'] = value

    @property
    def last_update_account_log_index(self):
        return self.ctx['last_update_account_log_index']

    @last_update_account_log_index.setter
    def last_update_account_log_index(self, value):
        self.ctx['last_update_account_log_index'] = value

    @property
    def last_update_print_log_index(self):
        return self.ctx['last_update_print_log_index']

    @last_update_print_log_index.setter
    def last_update_print_log_index(self, value):
        self.ctx['last_update_print_log_index'] = value

    @property
    def last_update_charts_data_index(self):
        return self.ctx['last_update_charts_data_index']

    @last_update_charts_data_index.setter
    def last_update_charts_data_index(self, value):
        self.ctx['last_update_charts_data_index'] = value

    @property
    def charts_data(self):
        return self.ctx['charts_data']

    @charts_data.setter
    def charts_data(self, value):
        self.ctx['charts_data'] = value

    @property
    def order_logs(self):
        return self.ctx['order_logs']

    @order_logs.setter
    def order_logs(self, value):
        self.ctx['order_logs'] = value

    @property
    def account_logs(self):
        return self.ctx['account_logs']

    @account_logs.setter
    def account_logs(self, value):
        self.ctx['account_logs'] = value

    @property
    def print_logs(self):
        return self.ctx['print_logs']

    @print_logs.setter
    def print_logs(self, value):
        self.ctx['print_logs'] = value

    @property
    def symbol_properties(self):
        return self.ctx['symbol_properties']

    @symbol_properties.setter
    def symbol_properties(self, value):
        self.ctx['symbol_properties'] = value

    @property
    def orders(self):
        return self.ctx['orders']

    @orders.setter
    def orders(self, value):
        self.ctx['orders'] = value

    @property
    def sid(self):
        return self.ctx['sid']

    @sid.setter
    def sid(self, value):
        self.ctx['sid'] = value

    @property
    def sid_data(self):
        return self.ctx['sid_data']

    @sid_data.setter
    def sid_data(self, value):
        self.ctx['sid_data'] = value

    @property
    def cid(self):
        return self.ctx['cid']

    @cid.setter
    def cid(self, value):
        self.ctx['cid'] = value

    @property
    def cid_data(self):
        return self.ctx['cid_data']

    @cid_data.setter
    def cid_data(self, value):
        self.ctx['cid_data'] = value

    @property
    def spread_point(self):
        return self.ctx['spread_point']

    @spread_point.setter
    def spread_point(self, value):
        self.ctx['spread_point'] = value

    @property
    def price_digits(self):
        return self.ctx['price_digits']

    @price_digits.setter
    def price_digits(self, value):
        self.ctx['price_digits'] = value

    @property
    def volume_precision(self):
        return self.ctx['volume_precision']

    @volume_precision.setter
    def volume_precision(self, value):
        self.ctx['volume_precision'] = value

    @property
    def spread_calculated(self):
        return self.ctx['spread_calculated']

    @spread_calculated.setter
    def spread_calculated(self, value):
        self.ctx['spread_calculated'] = value

    @property
    def report(self):
        return self.ctx['report']

    @report.setter
    def report(self, value):
        self.ctx['report'] = value

    @property
    def temp(self):
        return self.ctx['temp']

    @temp.setter
    def temp(self, value):
        self.ctx['temp'] = value

    # @return_logs.setter
    # def return_logs(self, value):
    #     self.ctx['return_logs'] = value

    # @property
    # def add_ea_settings(self):
    #     return self.ctx['add_ea_settings']

    # @log_path.setter
    # def log_path(self, value):
    #     self.ctx['log_path'] = value


