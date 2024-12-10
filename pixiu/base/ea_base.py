
import re
import time
import traceback
from RestrictedPython import (compile_restricted, safe_globals, utility_builtins,)
from RestrictedPython.PrintCollector import PrintCollector
#
from .ea_node_transformer import EARestrictingNodeTransformer
import numpy as np

import logging
log = logging.getLogger(__name__)


from ..base.api_base import (API_V1_Base)


class EABaseContext:

    def __init__(self):
        self.symbol = None
        self.script_settings = None


#---------------------------------------------------------------------------------------------------------------------
# EABase Classes
#---------------------------------------------------------------------------------------------------------------------
class EABase:
    """"""
    def __init__(self, context, params):
        # self.language = 'en'
        # self.symbol = None
        # self.byte_code = None
        # self.script = None
        # self.script_path = None
        # self.script_settings = None
        # self.script_libs = []
        # self.last_exec_time = 0
        self.global_values = params.get('global_values', {})
        # self.loc = {}
        self.df_columns = ('t', 's', 'o', 'h', 'l', 'c', 'v', 'a', 'b')
        # self.ea_log_callback = params.get('ea_log_callback', None)
        # self.add_ea_settings = None
        # self.context.tick_info = None
        #
        self.context = context

    @property
    def symbol(self):
        return self.context.symbol

    @property
    def tick_timeframe(self):
        return self.context.tick_timeframe

    @property
    def ticket(self):
        return self.context.ticket

    @property
    def start_time(self):
        return self.context.start_time

    @property
    def end_time(self):
        return self.context.end_time

    @property
    def default_symbol_properties(self):
        return self.context.default_symbol_properties

    @property
    def symbol_properties(self):
        return self.context.symbol_properties

    @symbol_properties.setter
    def symbol_properties(self, value):
        self.context.symbol_properties = value

    @property
    def symbol_data(self):
        return self.context.symbol_data

    @symbol_data.setter
    def symbol_data(self, value):
        self.context.symbol_data = value

    @property
    def tick_info(self):
        return self.context.tick_info

    @tick_info.setter
    def tick_info(self, value):
        self.context.tick_info = value

    # @property
    # def start_time(self):
    #     return self.context.start_time
    #
    # @property
    # def end_time(self):
    #     return self.context.end_time

    def copy_globals(self, globals=None):
        return safe_globals.copy()

    def get_print_factory(self, _getattr_=None):
        """"""
        if self.print_collection is None:
            self.print_collection = PrintCollector(_getattr_)
        return self.print_collection

    # parseScript(scriptText){
    #   //testerForm.script
    #   let ret = {
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
            #
        return ret

    @staticmethod
    def parse_script_text(script_text):
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

    def init_script_env(self, script_text):
        ret = {}
        org_context = self.context
        try:
            if not script_text or not isinstance(script_text, str):
                return None
            self.context = EABaseContext()
            sg = safe_globals.copy()
            loc = {}
            # self.import_module('pixiu.api.errors', self.safe_globals)
            api = self.get_api()
            api.set_fun(sg)
            for k in self.global_values:
                sg[k] = self.global_values[k]
            #
            self.context.tick_current_index = 0
            # self.context.tick_info = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0]],
            # temp_ti = self.context.tick_info
            self.context.tick_info = np.zeros((1,),
                     dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
                        ('l', float), ('v', float), ('a', float), ('b', float), ])
            self.context.account_info = None
            self.context.add_ea_settings = dict(charts={}, params={})

            #
            # for k in sg:
            #     sg[k] = self.global_values[k]

            # keywords = ['author', 'copyright', 'name', 'version', 'label', 'script_settings', 'lib', 'library']
            lib_bc = EABase.compile(script_text, 'init_script')
            # ret = eval(lib_bc, "InitConfig()")
            try:
                exec(lib_bc, sg)
            except:
                # traceback.print_exc()
                pass
            # self.context.tick_info = temp_ti
            script_settings = {}
            try:
                settings = eval("PX_InitScriptSettings()", sg)
                if isinstance(settings, dict):
                    script_settings = settings.copy()
            except:
                traceback.print_exc()

            #copy add ea settings
            for cn in self.context.add_ea_settings['charts']:
                script_settings['charts'][cn] = self.context.add_ea_settings['charts'][cn].copy()
            for pn in self.context.add_ea_settings['params']:
                script_settings['params'][pn] = self.context.add_ea_settings['params'][pn].copy()
            ret['script_settings'] = script_settings
            ret['globals'] = sg
            ret['locals'] = loc
        except:
            traceback.print_exc()
        self.context = org_context
        return ret


    # def init_script_env(self, script_text):
    #     ret = {}
    #     try:
    #         if not script_text or not isinstance(script_text, str):
    #             return None
    #         sg = safe_globals.copy()
    #         loc = {}
    #         # self.import_module('pixiu.api.errors', self.safe_globals)
    #         api = self.get_api()
    #         api.set_fun(sg)
    #         for k in self.global_values:
    #             sg[k] = self.global_values[k]
    #         #
    #         self.context.tick_current_index = 0
    #         # self.context.tick_info = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0]],
    #         temp_ti = self.context.tick_info
    #         self.context.tick_info = np.zeros((1,),
    #                  dtype=[('s', object), ('t', float), ('o', float), ('h', float), ('c', float),
    #                     ('l', float), ('v', float), ('a', float), ('b', float), ])
    #         self.context.account_info = None
    #         self.context.add_ea_settings = dict(charts={}, params={})
    #
    #         #
    #         # for k in sg:
    #         #     sg[k] = self.global_values[k]
    #
    #         # keywords = ['author', 'copyright', 'name', 'version', 'label', 'script_settings', 'lib', 'library']
    #         lib_bc = EABase.compile(script_text, 'init_script')
    #         # ret = eval(lib_bc, "InitConfig()")
    #         try:
    #             exec(lib_bc, sg)
    #         except:
    #             # traceback.print_exc()
    #             pass
    #         self.context.tick_info = temp_ti
    #         # exec PX_InitScriptSettings
    #         script_settings = {}
    #         try:
    #             settings = eval("PX_InitScriptSettings()", sg)
    #             if isinstance(settings, dict):
    #                 script_settings = settings.copy()
    #         except:
    #             traceback.print_exc()
    #
    #         #copy add ea settings
    #         for cn in self.context.add_ea_settings['charts']:
    #             script_settings['charts'][cn] = self.context.add_ea_settings['charts'][cn].copy()
    #         for pn in self.context.add_ea_settings['params']:
    #             script_settings['params'][pn] = self.context.add_ea_settings['params'][pn].copy()
    #         ret['script_settings'] = script_settings
    #         ret['globals'] = sg
    #         ret['locals'] = loc
    #     except:
    #         traceback.print_exc()
    #     return ret

    def valid_script_settings(self, script_settings, script_env):
        try:
            valid_ret = eval(f"PX_ValidScriptSettings", script_env['globals'])(script_settings)
            return valid_ret
            # if valid_ret is not None:
            #     if not valid_ret['success']:
            #         print(f"PX_ValidScriptSettings: errmsg={valid_ret.get('errmsg', None)}")
            #         return None
        except:
            traceback.print_exc()
        return None

    def get_script_init_settings(self, script_text):
        ret = {}
        try:
            env = self.init_script_env(script_text)
            if env is None:
                return ret
            valid_ret = self.valid_script_settings(env['script_settings'], env)
            if valid_ret is not None:
                if not valid_ret['success']:
                    print(f"PX_ValidScriptSettings: errmsg={valid_ret.get('errmsg', None)}")
                    ret['valid_script_settings'] = valid_ret
            ret['script_settings'] = env['script_settings']
        except:
            traceback.print_exc()
        return ret

    def parse_script(self, script_text):
        ret = {}
        try:
            ret = EABase.parse_script_text(script_text)
            script_init_settings = {}
            r = self.get_script_init_settings(script_text)
            for name in ('script_settings', 'valid_script_settings'):
                if name in r:
                    ret[name] = r[name]
        except:
            traceback.print_exc()
        return ret


    def get_param(self, name, default=None):
        try:
            if self.context.script_settings and isinstance(self.context.script_settings, dict):
                params = self.context.script_settings.get("params", {})
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
        # return compile_restricted(script, filename, 'exec')
        return compile_restricted(script, filename, 'exec', policy=EARestrictingNodeTransformer)

    def do_tick(self,):
        if not self.context.byte_code:
            #load libs
            for lib in self.context.script_libs:
                lib_bc = EABase.compile(lib['code'], lib['path'])
                exec(lib_bc, self.context.safe_globals)
            #
            if self.context.script_path is None:
                self.context.byte_code = EABase.compile(self.context.script)
            else:
                # self.byte_code = EABase.compile(open(self.script_path).read(), self.script_path)
                self.context.byte_code = EABase.compile(self.context.script, self.context.script_path)

        self.context.order_log = []
        stime = time.time()
        exec(self.context.byte_code, self.context.safe_globals)
        self.context.last_exec_time = time.time() - stime
