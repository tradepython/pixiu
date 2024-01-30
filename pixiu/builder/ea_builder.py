
import os
import io
import token
import json5 as json
from tokenize import generate_tokens
from token import tok_name
import traceback


def LoadModuleConfig(config_path):
    module_config = {}
    with open(config_path) as f:
        module_list = json.loads(f.read())
        for module_dict in module_list:
            mc = module_dict['module_config']
            module_config[mc['name']] = mc
    return module_config



module_config = LoadModuleConfig('/Users/digiyouth/local_files/codes/oeoehui_pixiu/samples/builder/module_indicator.json')


# indicator
class IndicatorModule:

    def __init__(self,):
        pass

    def adx(self, options):
        params = options['params']
        symbol_data = params['symbol_data']
        period = params['period']
        shift = params['shift']
        code = f"iATR({symbol_data}, timeperiod={period}, shift={shift})"
        variables = options.get('variables', None)
        if variables:
            code = f"{variables[0]['name']} = {code}"
        return code

    def ma(self, options):
        params = options['params']
        symbol_data = params['symbol_data']
        period = params['period']
        matype = params['matype']
        shift = params['shift']
        code = f"iMA({symbol_data}, timeperiod={period}, matype={matype}, shift={shift})"
        variables = options.get('variables', None)
        if variables:
            code = f"{variables[0]['name']} = {code}"
        codes = (code, )
        return codes

class ElementBuilder:

    def __init__(self, config, index):
        self.config = config
        self.index = index

    def build_code(self, options):
        return None


class SymbolBuilder(ElementBuilder):

    def __init__(self, config, index):
        super(SymbolBuilder, self).__init__(config, index)

    @property
    def symbol(self):
        return self.config['symbol']

    @property
    def size(self):
        return self.config['size']

    @property
    def timeframe(self):
        tf = self.config['timeframe']
        return f"TimeFrame.{tf.upper()}"

    def get_variable_name(self):
        return f"symbol_{self.index}"

    def build_code(self, options):
        code = f"{self.get_variable_name()} = GetSymbolData('{self.symbol}', timeframe={self.timeframe}, size={self.size})"
        return code


class FunctionBuilder(ElementBuilder):

    def __init__(self, config, index):
        super(FunctionBuilder, self).__init__(config, index)

    @property
    def module(self):
        module = self.config['module']
        return module

    @property
    def name(self):
        name = self.config['name']
        return name

    @property
    def params(self):
        params = self.config['params']
        return params

    def get_module_config(self, module):
        return module_config[module]

    def get_function_config(self, module, name):
        return self.get_module_config(module)['functions'][name]

    def get_module(self, module):
        cls = eval(self.get_module_config(module)['class'])
        return cls

    def call_function(self, module, name, options):
        func_config = self.get_function_config(module, name)
        cls = self.get_module(module)
        func = getattr(cls, func_config['method'])
        param_dict = {}
        for key in func_config['params']:
            param_dict[key] = self.params[key]
        options['params'] = param_dict

        return func(cls, options)

    def get_variables(self, module, name):
        func_config = self.get_function_config(module, name)
        return_config = func_config.get('return', None)
        if return_config is None:
            return None
        if isinstance(return_config, dict):
            return_config = [return_config, ]
        ret = []
        for rc in return_config:
            var = rc.get('variable', dict(prefix=func_config['method']))
            var_name = f"{var['prefix']}_{self.index}"
            ret.append(dict(name=var_name))

        return ret

    def build_code(self, options):
        if 'variables' not in options.keys():
            variables = self.get_variables(self.module, self.name)
            options['variables'] = variables
        code = self.call_function(self.module, self.name, options)
        return code


class EntryBuilder(ElementBuilder):

    def __init__(self, config, index):
        super(EntryBuilder, self).__init__(config, index)

    @property
    def long(self):
        long = self.config['long']
        return long

    @property
    def short(self):
        short = self.config['short']
        return short

    def generate_operation_element_code(self, element):
        c = f"{element[0]} {element[1]} {element[2]}"
        # code = f"{code} {op} {c}" if code else f"{c}"
        return c

    def generate_condition_elements_code(self, code,  condition_elements):
        op = condition_elements['op']
        values = condition_elements['values']
        for val in values:
            if isinstance(val, list):
                c = self.generate_operation_element_code(val)
            else:
                c = self.generate_condition_elements_code('', val)
            code = f"{code} {op} {c}" if code else f"{c}"
        return f"({code})"

    def generate_condition_code(self, condition_config):
        code = ''
        for cc in condition_config:
            code = self.generate_condition_elements_code(code, cc)
        return code

    def build_code(self, options):
        long_config = self.long
        condition_config = long_config['condition']
        long_code = self.generate_condition_code(condition_config)
        short_config = self.short
        condition_config = short_config['condition']
        short_code = self.generate_condition_code(condition_config)
        codes = (f"if {long_code}:", f"    open_long()", f"if {short_code}:", f"    open_short()")

        return codes


class EABuilder:
    """EA Builder"""

    def __init__(self, params):
        super(object, self).__init__()

    def generate_ea(self):
        pass

    def get_code(self):
        code = '''
# --------------
# main
# --------------
runner = EAStrategyRunner()
strategy = Strategy(runner)
# order_processes = [
#     # {'name': 'trailing_profit', 'func': strategy.process_order_trailing_profit,
#     #  'start_pips': 19, 'step_pips': 10},
#     # {'name': 'trailing_profit', 'func': strategy.process_order_trailing_profit,
#     #  'start_profit': TRAILING_PROFIT_START_PROFIT, 'step_profit': TRAILING_PROFIT_STEP_PROFIT},
#     # {'name': 'close_check_market_open', 'func': strategy.close_check_market_open},
# ]
# runner.options = {'open_processes': open_processes, 'order_processes': order_processes}

run_processes = [
    {'name': 'process_hedging_orders', 'func': strategy.process_hedging_orders},
    {'name': 'open_orders'},
    # {'name': 'post_open_orders', 'func': strategy.post_open_orders},
]
open_processes = [
    {'name': 'open_new', 'func': strategy.open_new, 'order_list': True},
    {'name': 'open_check_open_main_order_time', 'func': strategy.open_check_open_group_first_order_time},
]
order_processes = [
]
runner.options = {
    'debug_mode': DEBUG, 'enable_notify': NOTIFY,
    'run_processes': run_processes, 'open_processes': open_processes, 'order_processes': order_processes
}

runner.run()
'''
        return code

    def call_module_function(self, module, func, params):
        pass

    def parse_symbols_config(self, build_data, symbols_config):
        symbols = {}
        index = 0
        for key in symbols_config:
            symbols[key] = SymbolBuilder(symbols_config[key], index)
            index += 1
        build_data['symbols'] = symbols
        return build_data

    def parse_functions_config(self, build_data, functions_config):
        functions = {}
        index = 0
        for key in functions_config:
            functions[key] = FunctionBuilder(functions_config[key], index)
            index += 1
        build_data['functions'] = functions
        return build_data

    def parse_entry_config(self, build_data, entry_config):
        build_data['entry'] = EntryBuilder(entry_config, 0)
        return build_data

    def parse_build_config(self, config):
        build_data = {}
        build_config = None
        try:
            build_config = config['build_config']
            if build_config['version'] != "v1.0alpha":
                return None
            trading = build_config['trading']
            self.parse_symbols_config(build_data, trading['symbols'])
            self.parse_functions_config(build_data, trading['functions'])
            self.parse_entry_config(build_data, trading['entry'])
            #
            codes = []
            options = {}
            for key in build_data['symbols']:
                sd = build_data['symbols'][key]
                codes.append(sd.build_code(options))

            for key in build_data['functions']:
                options = {}
                fd = build_data['functions'][key]
                codes.append(fd.build_code(options))

            options = {}
            ed = build_data['entry']
            codes.append(ed.build_code(options))

            for c in codes:
                if isinstance(c, tuple):
                    for t in c:
                        print(t)
                else:
                    print(c)

        except:
            traceback.print_exc()
        return build_data

    def parse_condition(self, condition):
        pass



    # def parse_condition(self, condition):
    #     condition = "Ind::ADX(symbol='main', 5, 0) > 20 and Ind::MA(main, 60, 0) > ind::MA(main, 90, 0)"
    #     name = None
    #     op_ary = None
    #     function_start = False
    #     function_params = None
    #     module_name = None
    #     function_name = None
    #     for t in generate_tokens(io.StringIO(condition).readline):
    #         tn = tok_name[t[0]]
    #         tv = t[1]
    #         print(tn, tv)
    #         if t[0] == token.NAME:
    #             if name is None:
    #                 name = tv
    #                 op_ary = []
    #             else:
    #                 if not function_start:
    #                     if len(op_ary) == 2:
    #                         if op_ary[0] == ':' and op_ary[1] == ':':
    #                             module_name = name
    #                             name = tv
    #                             op_ary = []
    #                     elif len(op_ary) > 0:
    #                         if op_ary[0] == '(':
    #                             function_start = True
    #                             function_name = name
    #                             function_params = [tv,]
    #                 else:
    #                     function_params.append(tv)
    #         elif t[0] == token.OP:
    #             op_ary.append(tv)
    #             if function_start:
    #                 if tv == ')':
    #                     function_start = False
    #                     self.call_module_function(module_name, function_name, function_params)
    #         elif t[0] == token.NUMBER:
    #             if function_start:
    #                 function_params.append(tv)
    #
    #

    def build(self, config):
        build_data = self.parse_build_config(config[0])
        return
        #
        file_dir = os.path.dirname(__file__)
        runner_file = open(f"{file_dir}/templates/runner/EAStrategyRunner_V1.07.00.py")
        strategy_file = open(f"{file_dir}/templates/strategies/strategy_samples.py")
        with open(f"{file_dir}/ea_out.py", "w") as f:
            f.write(strategy_file.read())
            f.write(runner_file.read())
            f.write(self.get_code())
