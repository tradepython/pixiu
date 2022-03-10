
import re
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
        self.script_libs = []
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

    # parseScript(scriptText){
    #   //testerForm.script
    #   let ret = {}
    #   if(!scriptText)
    #     return ret
    #   let arrayOfLines = scriptText.match(/[^\r\n]+/g)
    #   for (var idx in arrayOfLines){
    #     let line = arrayOfLines[idx]
    #     if(!line)
    #       break
    #     if(!line.startsWith('###'))
    #       break
    #     let ary = line.split('=')
    #     if(ary.length === 2){
    #       const l = ['name', 'version', 'label', 'script_settings']
    #       let beginText = ary[0]
    #       //###[name]=DT-MA
    #       //###[version]=1.8
    #       //###[label]=timeout: 5min, near:4h, far:24h, open: ma-breakout, close: ma+c_stoploss, tp:profit+pips
    #       //###[script_settings]
    #       for(var li in l){
    #         if(beginText === `###[${l[li]}]`){
    #           ret[l[li]] = ary[1]
    #           break
    #         }
    #       }
    #     }
    #   }
    #   return ret
    # }
    def lib_path(self, name, version):
        return f"{name}_V{version}.py"

    def load_libs(self, lib_list):
        # ["PriceAction==0.1.0"]
        ret = []
        for lib in lib_list:
            lib_name, lib_version = lib.split("==")
            lib_path = self.lib_path(lib_name, lib_version)
            code = open(lib_path).read()
            lib_metadata = self.parse_script(code)
            lib_data = dict(name=lib_name, version=lib_version, path=lib_path, code=code, metadata=lib_metadata)
            ret.append(lib_data)
        return ret

    @staticmethod
    def parse_script(script_text):
        ret = {}
        try:
            if not script_text or not isinstance(script_text, str):
                return ret
            keywords = ['author', 'copyright', 'name', 'version', 'label', 'script_settings', 'lib', 'library']
            array_of_lines = script_text.splitlines()
            for line in array_of_lines:
                if not line:
                    break
                tags = re.findall(r"^###\[\w+]=", line)
                if len(tags) == 0:
                    break
                for kw in keywords:
                    lh = f"###[{kw}]="
                    if tags[0] == lh:
                        ret[kw] = line[len(tags[0]):].strip()
                        break
        except:
            traceback.print_exc()
        return ret

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
    def get_settings(self, name, default=None):
        try:
            pass
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
            #load libs
            for lib in self.script_libs:
                lib_bc = EABase.compile(lib['code'], lib['path'])
                exec(lib_bc, self.safe_globals)
            #
            if self.script_path is None:
                self.byte_code = EABase.compile(self.script)
            else:
                # self.byte_code = EABase.compile(open(self.script_path).read(), self.script_path)
                self.byte_code = EABase.compile(self.script, self.script_path)

        self.order_log = []
        stime = time.time()
        exec(self.byte_code, self.safe_globals)
        self.last_exec_time = time.time() - stime
    #
    # def do_tick(self,):
    #     if not self.byte_code:
    #         if self.script_path is None:
    #             self.byte_code = EABase.compile(self.script)
    #         else:
    #             # self.byte_code = EABase.compile(open(self.script_path).read(), self.script_path)
    #             self.byte_code = EABase.compile(self.script, self.script_path)
    #
    #     self.order_log = []
    #     stime = time.time()
    #     exec(self.byte_code, self.safe_globals)
    #     self.last_exec_time = time.time() - stime
    #     #

