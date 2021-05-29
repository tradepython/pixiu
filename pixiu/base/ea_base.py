
import time
import traceback
from RestrictedPython import (compile_restricted, safe_globals, utility_builtins,)
from RestrictedPython.PrintCollector import PrintCollector



import logging
log = logging.getLogger(__name__)

#---------------------------------------------------------------------------------------------------------------------
# EA Classes
#---------------------------------------------------------------------------------------------------------------------
class EABase():
    """"""
    def __init__(self, params):
        self.language = 'en'
        self.symbol = None
        self.byte_code = None
        self.script = None
        self.script_path = None
        self.script_settings = None
        self.last_exec_time = 0
        self.safe_globals = safe_globals.copy()
        self.global_values = params.get('global_values', {})
        self.loc = {}
        self.df_columns = ('t', 's', 'o', 'h', 'l', 'c', 'v', 'a', 'b')
        self.ea_log_callback = params.get('ea_log_callback', None)
        #

    def get_print_factory(self, _getattr_=None):
        """"""
        if self.print_collection is None:
            self.print_collection = PrintCollector(_getattr_)
        return self.print_collection

    def get_param(self, name, default=None):
        try:
            if self.script_settings and isinstance(self.script_settings, dict):
                params = self.script_settings.get("params", {})
                if name in params.keys():
                    params_value = params[name]
                    if params_value is None or not isinstance(params_value, dict):
                        return params_value
                    if "config" in params_value.keys():
                        return params_value.get("value", default)
                    else:
                        return params_value
        except:
            traceback.print_exc()
        return default
    #
    # #
    def get_symbol_properties(self, symbol):
        ''''''
        raise NotImplemented

    @staticmethod
    def compile(script, filename='<inline>'):
        '''编译脚本'''
        return compile_restricted(script, filename, 'exec')

    def do_tick(self,):
        if not self.byte_code:
            if self.script_path is None:
                self.byte_code = EABase.compile(self.script)
            else:
                self.byte_code = EABase.compile(open(self.script_path).read(), self.script_path)

        self.order_log = []
        stime = time.time()
        exec(self.byte_code, self.safe_globals)
        self.last_exec_time = time.time() - stime
        #

