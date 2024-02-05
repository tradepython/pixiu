
import os
import io
import token
import json5 as json
from tokenize import generate_tokens
from token import tok_name
import traceback
from jinja2 import Template

file_dir = os.path.dirname(__file__)


def LoadModuleConfig(config_path):
    module_config = {}
    with open(config_path) as f:
        module_list = json.loads(f.read())
        for module_dict in module_list:
            mc = module_dict['module_config']
            module_config[mc['name']] = mc
    return module_config

def LoadStrategyConfig(config_path):
    strategy_config = {}
    with open(config_path) as f:
        strategy_list = json.loads(f.read())
        for strategy_dict in strategy_list:
            sc = strategy_dict['strategy_config']
            strategy_config[sc['name']] = sc
    return strategy_config


module_config = LoadModuleConfig('/Users/digiyouth/local_files/codes/oeoehui_pixiu/samples/builder/module_indicator.json')
strategy_config = LoadStrategyConfig('/Users/digiyouth/local_files/codes/oeoehui_pixiu/samples/builder/strategy_default.json')


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

    def __init__(self, key, config, index, build_data):
        self.key = key
        self.config = config
        self.index = index
        self.build_data = build_data

    def __write_value_items__(self, value_name, items):
        # items = value.split('.')
        ret = value_name
        if len(items) > 1:
            for i in items[1:]:
                ret = f"{ret}.{i}"
        return ret

    def get_value(self, config, value):
        ret = value
        if isinstance(value, str):
            va = value.split('/')
            if len(va) > 1:
                if va[0] == '@parameters':
                    items = va[1].split('.')
                    parameter_builder = self.build_data['parameters'][items[0]]
                    ret = parameter_builder.get_variable_name()
                    # if len(items) > 1:
                    #     for i in items[1:]:
                    #         ret = f"{ret}.{i}"
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] == '@symbols':
                    items = va[1].split('.')
                    symbol_builder = self.build_data['symbols'][items[0]]
                    ret = symbol_builder.get_variable_name()
                    # if len(items) > 1:
                    #     for i in items[1:]:
                    #         ret = f"{ret}.{i}"
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] == '@functions':
                    func_builder = self.build_data['functions'][va[1]]
                    var_list = func_builder.get_variables(func_builder.module, func_builder.name)
                    ret = var_list[0]['name']

        return ret

    def build_code(self, options):
        return None


class ParameterBuilder(ElementBuilder):

    def __init__(self, key, config, index, build_data):
        super(ParameterBuilder, self).__init__(key, config, index, build_data)
        self.script_settings_dict = None

    @property
    def name(self):
        return self.config.get('name', self.key)

    @property
    def type(self):
        return self.config.get('type', "string")

    @property
    def value(self):
        return self.config['value']

    @property
    def required(self):
        return self.config.get('required', False)

    @property
    def script_settings(self):
        return self.config.get('script_settings', False)

    @property
    def min(self):
        return self.config.get('min', None)

    @property
    def max(self):
        return self.config.get('max', None)

    @property
    def desc(self):
        return self.config.get('desc', None)

    @property
    def options(self):
        return self.config.get('options', None)

    def get_variable_name(self):
        return f"{self.name.upper()}"

    def get_script_settings(self):
        return self.script_settings_dict

    def build_code(self, options):
        value_type = self.type
        value = None
        value_string = ''
        if value_type == 'timeframe':
            tf = self.value
            value = f"TimeFrame.{tf.upper()}"
            value_string = value
        elif value_type == 'bool':
            value = self.value
            value_string = f"{value}"
        elif value_type == 'int':
            value = int(self.value)
            value_string = f"{value}"
        elif value_type == 'float':
            value = float(self.value)
            value_string = f"{value}"
        elif value_type == 'str':
            value = str(self.value)
            value_string = f"'{value}'"

        if self.script_settings:
            self.script_settings_dict = dict(value=value,
                                             config=dict(required=self.required, type=self.type))
            if self.min is not None:
                self.script_settings_dict['config']['min'] = self.min
            if self.max is not None:
                self.script_settings_dict['config']['max'] = self.max
            if self.options is not None:
                self.script_settings_dict['config']['options'] = self.options
            if self.desc is not None:
                self.script_settings_dict['config']['desc'] = self.desc
            #
            code = f"{self.get_variable_name()} = GetParam(\"{self.name}\", {value_string})" if self.type in ('string', 'str', 'timeframe') else f"{self.get_variable_name()} = {value_type}(GetParam(\"{self.name}\", {value_string}))"
            # code = f"{self.get_variable_name()} = GetParam(\"{self.name}\")"
        else:
            code = f"{self.get_variable_name()} = {value_string}"

        return code

class SymbolBuilder(ElementBuilder):

    def __init__(self, key, config, index, build_data):
        super(SymbolBuilder, self).__init__(key, config, index, build_data)

    @property
    def symbol(self):
        return self.config['symbol']

    @property
    def size(self):
        return self.config['size']

    @property
    def timeframe(self):
        tf = self.config['timeframe']
        return tf

    def get_variable_name(self):
        return f"symbol_{self.index}"

    def build_code(self, options):
        symbol = self.get_value({}, self.symbol)
        if isinstance(symbol, str):
            symbol = f"'{symbol}'"
        elif symbol == 0:
            symbol = 'Symbol()'
        else:
            symbol = None

        timeframe = self.get_value({}, self.timeframe)
        # tf = self.get_value({}, self.timeframe)
        # return f"TimeFrame.{tf.upper()}"
        size = self.get_value({}, self.size)
        code = f"{self.get_variable_name()} = GetSymbolData({symbol}, timeframe={timeframe}, size={size})"
        return code


class FunctionBuilder(ElementBuilder):

    def __init__(self, key, config, index, build_data):
        super(FunctionBuilder, self).__init__(key, config, index, build_data)

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
            param_dict[key] = self.get_value(func_config['params'][key], self.params[key])
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

    def __init__(self, key, config, index, build_data):
        super(EntryBuilder, self).__init__(key, config, index, build_data)

    @property
    def long(self):
        long = self.config['long']
        return long

    @property
    def short(self):
        short = self.config['short']
        return short


    def generate_operation_element_code(self, element):
        v0 = self.get_value(None, element[0])
        v1 = self.get_value(None, element[1])
        v2 = self.get_value(None, element[2])
        c = f"{v0} {v1} {v2}"
        # code = f"{code} {op} {c}" if code else f"{c}"
        return c

    def generate_condition_elements_code(self, code,   condition_elements):
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
        codes = (f"ret = dict()",
                 f"if {long_code}:",
                 f"    ret[PositionType.LONG] = dict(price=None)",
                 f"if {short_code}:",
                 f"    ret[PositionType.SHORT] = dict(price=None)",
                 f"return ret")

        return codes


class EABuilder:
    """EA Builder"""

    def __init__(self, params):
        super(object, self).__init__()

    def generate_ea(self):
        pass

    def get_code(self):
        code = '''
'''
        return code

    def call_module_function(self, module, func, params):
        pass

    def parse_strategy_parameters_config(self, build_data, strategy_name):
        sc = strategy_config[strategy_name]
        #
        parameters = {}
        index = 0
        for key in sc['parameters']:
            parameters[key] = ParameterBuilder(key, sc['parameters'][key], index, build_data)
            index += 1
        build_data['strategy_parameters'] = parameters
        return build_data

    def parse_parameters_config(self, build_data, parameters_config):
        parameters = {}
        index = 0
        for key in parameters_config:
            parameters[key] = ParameterBuilder(key, parameters_config[key], index, build_data)
            index += 1
        build_data['parameters'] = parameters
        return build_data

    def parse_symbols_config(self, build_data, symbols_config):
        symbols = {}
        index = 0
        for key in symbols_config:
            symbols[key] = SymbolBuilder(key, symbols_config[key], index, build_data)
            index += 1
        build_data['symbols'] = symbols
        return build_data

    def parse_functions_config(self, build_data, functions_config):
        functions = {}
        index = 0
        for key in functions_config:
            functions[key] = FunctionBuilder(key, functions_config[key], index, build_data)
            index += 1
        build_data['functions'] = functions
        return build_data

    def parse_entry_config(self, build_data, entry_config):
        build_data['entry'] = EntryBuilder(None,  entry_config, 0, build_data)
        return build_data

    def generate_code_string_list(self, codes):
        ret = []
        for c in codes:
            if isinstance(c, tuple):
                for t in c:
                    # print(f"    {t}")
                    ret.append(t)
            else:
                # print(f"    {c}")
                ret.append(c)
        return ret

    def parse_build_config(self, config):
        build_info = None
        build_data = {}
        build_config = None
        try:
            build_config = config['build_config']
            if build_config['version'] != "v1.0alpha":
                return None
            trading = build_config['trading']
            coding = build_config['coding']
            self.parse_strategy_parameters_config(build_data,  coding['strategy']['name'])
            self.parse_parameters_config(build_data, trading['parameters'])
            self.parse_symbols_config(build_data, trading['symbols'])
            self.parse_functions_config(build_data, trading['functions'])
            self.parse_entry_config(build_data, trading['entry'])
            build_info = dict(config=build_config, data=build_data)
        except:
            traceback.print_exc()
        return build_info

    def generate_ea_code(self, build_info):
        ret = None
        try:
            #
            build_data = build_info['data']
            build_config = build_info['config']
            codes = []
            options = {}
            parameters_codes = []
            script_settings = dict(params={}, charts={"price": {"series": [
                                            {"name": "top_signal", "color": "#89F3DAFF"},
                                            {"name": "bottom_signal", "color": "#e7dc48"}]
                  }})
            for key in build_data['strategy_parameters']:
                pd = build_data['strategy_parameters'][key]
                parameters_codes.append(pd.build_code(options))
                ss = pd.get_script_settings()
                if pd.script_settings:
                    script_settings['params'][pd.name] = ss
            for key in build_data['parameters']:
                pd = build_data['parameters'][key]
                parameters_codes.append(pd.build_code(options))
                ss = pd.get_script_settings()
                if pd.script_settings:
                    script_settings['params'][pd.name] = ss
            #
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
            #
            pc = self.generate_code_string_list(parameters_codes)
            sl = self.generate_code_string_list(codes)
            # script_settings_code = json.dumps(script_settings, quote_keys=True)
            strategy = dict(class_name=build_config['name'],
                            code=dict(parameters=pc, get_entry_data=sl),
                            script_settings=script_settings
                            )
            runner = dict(code=dict())
            # print(f"def can_open_order(self):")
            # for c in codes:
            #     if isinstance(c, tuple):
            #         for t in c:
            #             print(f"    {t}")
            #     else:
            #         print(f"    {c}")
            #
            j2_file = open(f"{file_dir}/templates/code/ea_strategy_class.j2")
            template = Template(j2_file.read())
            strategy_class_code = template.render(strategy=strategy)
            print(strategy_class_code)
            runner['strategy_class_name'] = strategy['class_name']
            runner['code']['strategy_class'] = strategy_class_code
            # runner['code']['main'] = self.get_code()
            #
            j2_file = open(f"{file_dir}/templates/code/ea_strategy_runner_V1.07.00.j2")
            template = Template(j2_file.read())
            ret = template.render(runner=runner)
            print(ret)
        except:
            traceback.print_exc()
        return ret



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

    def build(self, config, output_path):
        build_info = self.parse_build_config(config[0])
        ea_code = self.generate_ea_code(build_info)
        if ea_code is None:
            return False
        with open(output_path, "w") as f:
            f.write(ea_code)
        return True
