
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

    def adx(self, symbol_data, period, shift):
        code = f"iATR({symbol_data}, timeperiod={period}, shift={shift})"
        return code

    def ma(self, symbol_data, period, matype, shift):
        codes = (f"iMA({symbol_data}, timeperiod={period}, matype={matype}, shift={shift})", )
        return codes

class ElementBuilder:

    def __init__(self, config, index):
        self.config = config
        self.index = index

    def build_code(self):
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

    def build_code(self):
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

    def get_module(self, module):
        cls = eval(module_config[module]['class'])
        return cls

    def call_function(self, module, name):
        func_config = module_config[module]['functions'][name]
        cls = self.get_module(module)
        func = getattr(cls, func_config['method'])
        param_dict = {}
        for key in func_config['params']:
            param_dict[key] = self.params[key]

        return func(cls, **param_dict)

    def build_code(self):
        code = self.call_function(self.module, self.name)
        return code


class EntryBuilder(ElementBuilder):

    def __init__(self, config, index):
        super(EntryBuilder, self).__init__(config, index)


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
        entry = {}
        index = 0
        for key in entry_config:
            entry[key] = EntryBuilder(entry_config[key], index)
            index += 1
        build_data['entry'] = entry
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
            for key in build_data['symbols']:
                sd = build_data['symbols'][key]
                codes.append(sd.build_code())

            for key in build_data['functions']:
                fd = build_data['functions'][key]
                codes.append(fd.build_code())

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
