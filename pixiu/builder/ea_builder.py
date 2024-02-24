
import os
import io
import token
import json5 as json
from tokenize import generate_tokens
from token import tok_name
import traceback
from jinja2 import Template
from pixiu.api.defines import (TimeFrame, OrderType, OrderCommand, RunModeValue, PositionType, OrderStatus)
from black import format_str, FileMode
import importlib

file_dir = os.path.dirname(__file__)


class ElementBuilder:

    def __init__(self, builder, key, config, index, build_data):
        self.builder = builder
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
                if va[0] in ('@variables', '@var'):
                    items = va[1].split('.')
                    parameter_builder = self.build_data['variables'][items[0]]
                    ret = parameter_builder.get_variable_name()
                    # if len(items) > 1:
                    #     for i in items[1:]:
                    #         ret = f"{ret}.{i}"
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] in ('@symbols', '@sym'):
                    items = va[1].split('.')
                    symbol_builder = self.build_data['symbols'][items[0]]
                    ret = symbol_builder.get_variable_name()
                    # if len(items) > 1:
                    #     for i in items[1:]:
                    #         ret = f"{ret}.{i}"
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] in ('@functions', '@func'):
                    func_builder = self.build_data['functions'][va[1]]
                    var_list = func_builder.get_variables(func_builder.module, func_builder.name)
                    ret = var_list[0]['name']
                else:
                    raise f"Unknown path name: {va[0]}"

        return ret

    def build_code(self, options):
        return None


class VariableBuilder(ElementBuilder):

    def __init__(self, builder, key, config, index, build_data):
        super(VariableBuilder, self).__init__(builder, key, config, index, build_data)
        self.script_settings_dict = None
        self.valid_script_settings_codes = None

    @property
    def name(self):
        return self.config.get('name', self.key)

    @property
    def type(self):
        return self.config.get('type', "string")

    @property
    def valid(self):
        return self.config.get('valid', None)

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

    def get_valid_script_settings_codes(self):
        return self.valid_script_settings_codes

    def build_code(self, options):
        value_type = self.type
        value = None
        value_string = ''
        if value_type == 'timeframe':
            tf = self.value
            value = tf.lower()
            value_string = f"'{value}'"
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
            if self.valid:
                self.valid_script_settings_codes = []
                self.valid_script_settings_codes.append(f"# valid {self.name}")
                for v in self.valid:
                    condition = v['condition']
                    errmsg = v.get('errmsg', None)
                    condition = condition.replace('%obj', self.name)
                    if not errmsg:
                        errmsg = f"{condition}"
                    self.valid_script_settings_codes.append(f"{self.name} = params['{self.name}']")
                    self.valid_script_settings_codes.append(f"if {condition}:")
                    self.valid_script_settings_codes.append(f"    return dict(success=False, errmsg=\"{errmsg}\")")

        else:
            code = f"{self.get_variable_name()} = {value_string}"
        #

        return code

class SymbolBuilder(ElementBuilder):

    def __init__(self, builder, key, config, index, build_data):
        super(SymbolBuilder, self).__init__(builder, key, config, index, build_data)

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

    def __init__(self, builder, key, config, index, build_data):
        super(FunctionBuilder, self).__init__(builder, key, config, index, build_data)
        self.modules = {}

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
        module_config = self.builder.get_builder_config('module_config')
        return module_config[module]

    def get_function_config(self, module, name):
        return self.get_module_config(module)['functions'][name]

    def get_module(self, module_name):
        module_config = self.get_module_config(module_name)
        module = self.modules.get(module_name, None)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, module_config['file_abs_path'])
            module = importlib.util.module_from_spec(spec)
            self.modules[module_name] = module
            spec.loader.exec_module(module)
            # module.MyClass()
        cls = eval(f"module.{module_config['class']}")
        return cls

    def call_function(self, module, name, options):
        func_config = self.get_function_config(module, name)
        cls = self.get_module(module)
        func = getattr(cls, func_config['method'])
        param_dict = {}
        for key in func_config['params']:
            param_dict[key] = self.get_value(func_config['params'][key], self.params[key])
        options['params'] = param_dict

        return func(cls(), options)

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

    def __init__(self, builder, key, config, index, build_data):
        super(EntryBuilder, self).__init__(builder, key, config, index, build_data)
        self.order_settings = {}

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

    def parse_order_config(self, config):
        ret = None
        os = config.get('order', None)
        if os:
            ret = os.copy()
            profit_loss_ratio = ret.get('profit_loss_ratio', 0)
            if profit_loss_ratio > 0:
                ret['profit_loss_ratio'] = profit_loss_ratio
            positions = ret.get('positions', None)
            if isinstance(positions, dict):
                pos_type = positions['type']
                if pos_type == 'fixed':
                    pos_volume = positions['volume']
            #
            take_profit = ret.get('take_profit', None)
            if isinstance(take_profit, dict):
                tp_type = take_profit['type']
                if tp_type == 'pips':
                    tp_pips = take_profit['pips']
                elif tp_type == 'money':
                    tp_money = take_profit['money']
                elif tp_type == 'percent':
                    tp_percent = take_profit['percent']
                    tp_percent_source = take_profit['source']
                    if tp_percent_source == 'atr':
                        tp_percent_atr_period = take_profit['period']
                        tp_percent_atr_timeframe = take_profit['timeframe']
                elif tp_type == 'pl-ratio':
                    pass

            stop_loss = ret.get('stop_loss', None)
            if isinstance(stop_loss, dict):
                sl_type = stop_loss['type']
                if sl_type == 'pips':
                    sl_pips = stop_loss['pips']
                elif sl_type == 'money':
                    sl_money = stop_loss['money']
                elif sl_type == 'percent':
                    sl_percent = stop_loss['percent']
                    sl_percent_source = stop_loss['source']
                    if sl_percent_source == 'atr':
                        sl_percent_atr_period = stop_loss['period']
                        sl_percent_atr_timeframe = stop_loss['timeframe']
                elif sl_type == 'pl-ratio':
                    pass
            #
        return ret

    def build_code(self, options):
        #
        default_order_config = self.parse_order_config(self.config)
        #
        long_config = self.long
        condition_config = long_config['condition']
        long_code = self.generate_condition_code(condition_config)
        long_order_config = self.parse_order_config(long_config)
        if long_order_config is None:
            long_order_config = default_order_config
        #
        short_config = self.short
        condition_config = short_config['condition']
        short_code = self.generate_condition_code(condition_config)
        short_order_config = self.parse_order_config(short_config)
        if short_order_config is None:
            short_order_config = default_order_config
        if long_order_config is None or short_order_config is None:
            raise f"Error: Entry order config not found!"
        #
        codes = (f"ret = dict()",
                 f"if {long_code}:",
                 f"    ret[PositionType.LONG] = dict(price=None, order_config={long_order_config})",
                 f"if {short_code}:",
                 f"    ret[PositionType.SHORT] = dict(price=None, order_config={short_order_config})",
                 f"return ret")

        return codes


class ExitBuilder(EntryBuilder):

    def __init__(self, builder, key, config, index, build_data):
        super(ExitBuilder, self).__init__(builder, key, config, index, build_data)

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
        self.builder_config = {}
        # load base config
        base_config_path = f"{file_dir}/strategies/conf"
        base_config_files = self.search_path_config_files(base_config_path)
        for config_path in base_config_files:
            self.load_builder_config(config_path, self.builder_config)
        #
        config_path_list = params.get('config_path_list', [])
        for config_path in config_path_list:
            self.load_builder_config(config_path, self.builder_config)

    def get_builder_config(self, config_name=None):
        if config_name is None:
            return self.builder_config
        return self.builder_config.get(config_name, None)

    def generate_ea(self):
        pass

    def get_code(self):
        code = '''
'''
        return code

    def call_module_function(self, module, func, params):
        pass

    def parse_strategy_variables_config(self, build_data, strategy_name):
        strategy_config = self.builder_config['strategy_config']
        sc = strategy_config[strategy_name]
        #
        variables = {}
        index = 0
        for key in sc['variables']:
            variables[key] = VariableBuilder(self, key, sc['variables'][key], index, build_data)
            index += 1
        build_data['strategy_variables'] = variables
        return build_data

    def parse_variables_config(self, build_data, variables_config):
        variables = {}
        index = 0
        for key in variables_config:
            variables[key] = VariableBuilder(self, key, variables_config[key], index, build_data)
            index += 1
        build_data['variables'] = variables
        return build_data

    def parse_symbols_config(self, build_data, symbols_config):
        symbols = {}
        index = 0
        for key in symbols_config:
            symbols[key] = SymbolBuilder(self, key, symbols_config[key], index, build_data)
            index += 1
        build_data['symbols'] = symbols
        return build_data

    def parse_functions_config(self, build_data, functions_config):
        functions = {}
        index = 0
        for key in functions_config:
            functions[key] = FunctionBuilder(self, key, functions_config[key], index, build_data)
            index += 1
        build_data['functions'] = functions
        return build_data

    def parse_entry_config(self, build_data, entry_config):
        build_data['entry'] = EntryBuilder(self, None,  entry_config, 0, build_data)
        return build_data

    def parse_exit_config(self, build_data, entry_config):
        build_data['exit'] = ExitBuilder(self, None,  entry_config, 0, build_data)
        return build_data

    def generate_code_string_list(self, codes):
        ret = []
        for c in codes:
            if isinstance(c, tuple) or isinstance(c, list):
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
            self.parse_strategy_variables_config(build_data,  coding['strategy']['name'])
            self.parse_variables_config(build_data, trading['variables'])
            self.parse_symbols_config(build_data, trading['symbols'])
            self.parse_functions_config(build_data, trading['functions'])
            self.parse_entry_config(build_data, trading['entry'])
            self.parse_exit_config(build_data, trading['exit'])
            build_info = dict(config=build_config, data=build_data)
        except:
            traceback.print_exc()
        return build_info

    def generate_entry_exit_code(self, build_data, options, code_type):
        codes = []
        for key in build_data['symbols']:
            sd = build_data['symbols'][key]
            codes.append(sd.build_code(options))

        for key in build_data['functions']:
            options = {}
            fd = build_data['functions'][key]
            codes.append(fd.build_code(options))

        options = {}
        ed = build_data[code_type]
        codes.append(ed.build_code(options))
        return codes

    def generate_ea_code(self, build_info):
        ret = None
        try:
            #
            build_data = build_info['data']
            build_config = build_info['config']
            options = {}
            variables_codes = []
            valid_script_settings_codes = []
            script_settings = dict(params={}, charts={"price": {"series": [
                                            {"name": "top_signal", "color": "#89F3DAFF"},
                                            {"name": "bottom_signal", "color": "#e7dc48"}]
                  }})
            for key in build_data['strategy_variables']:
                pd = build_data['strategy_variables'][key]
                variables_codes.append(pd.build_code(options))
                ss = pd.get_script_settings()
                if pd.script_settings:
                    script_settings['params'][pd.name] = ss
                    vssc = pd.get_valid_script_settings_codes()
                    if vssc is not None:
                        valid_script_settings_codes.append(vssc)
            for key in build_data['variables']:
                pd = build_data['variables'][key]
                variables_codes.append(pd.build_code(options))
                ss = pd.get_script_settings()
                if pd.script_settings:
                    script_settings['params'][pd.name] = ss
                    vssc = pd.get_valid_script_settings_codes()
                    if vssc is not None:
                        valid_script_settings_codes.append(vssc)
            #
            # for key in build_data['symbols']:
            #     sd = build_data['symbols'][key]
            #     codes.append(sd.build_code(options))
            #
            # for key in build_data['functions']:
            #     options = {}
            #     fd = build_data['functions'][key]
            #     codes.append(fd.build_code(options))
            #
            # options = {}
            # ed = build_data['entry']
            # codes.append(ed.build_code(options))
            entry_codes = self.generate_entry_exit_code(build_data, options, 'entry')
            exit_codes = self.generate_entry_exit_code(build_data, options, 'exit')
            #
            pc = self.generate_code_string_list(variables_codes)
            ecl = self.generate_code_string_list(entry_codes)
            exl = self.generate_code_string_list(exit_codes)
            vsscl = self.generate_code_string_list(valid_script_settings_codes)
            # script_settings_code = json.dumps(script_settings, quote_keys=True)
            strategy = dict(class_name=build_config['name'],
                            code=dict(variables=pc, get_entry_data=ecl, get_exit_data=exl,
                                      valid_script_settings=vsscl),
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
            # load strategy template
            strategy_name = build_config['coding']['strategy']['name']
            strategy_config = self.get_builder_config('strategy_config')
            config_data = strategy_config[strategy_name]
            j2_file = open(config_data['template_abs_path'])
            template = Template(j2_file.read())
            strategy_class_code = template.render(strategy=strategy)
            print(strategy_class_code)
            runner['strategy_class_name'] = strategy['class_name']
            runner['code']['strategy_class'] = strategy_class_code
            # runner['code']['main'] = self.get_code()
            #
            # load strategy template
            runner_name = build_config['coding']['runner']['name']
            runner_config = self.get_builder_config('runner_config')
            config_data = runner_config[runner_name]
            j2_file = open(config_data['template_abs_path'])
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

    def load_builder_config(self, config_path, builder_config):
        module_config = builder_config.get('module_config', {})
        strategy_config = builder_config.get('strategy_config', {})
        runner_config = builder_config.get('runner_config', {})
        config_dir = os.path.dirname(config_path)
        with open(config_path) as f:
            strategy_list = json.loads(f.read())
            for conf_dict in strategy_list:
                for conf_type in conf_dict:
                    conf_name = None
                    check_abs_path_name = None
                    conf_data = conf_dict[conf_type]
                    if conf_type == 'module_config':
                        conf_name = conf_data['name']
                        builder_conf = module_config
                        check_abs_path_name = 'file'
                    elif conf_type == 'strategy_config':
                        conf_name = conf_data['name']
                        builder_conf = strategy_config
                        check_abs_path_name = 'template'
                    elif conf_type == 'runner_config':
                        conf_name = conf_data['name']
                        builder_conf = runner_config
                        check_abs_path_name = 'template'
                    else:
                        raise "Unknown conf type"
                    if conf_name in builder_conf:
                        raise f"Error: {conf_name} in {conf_type}"
                    #check abs_path
                    if check_abs_path_name:
                        abs_path_name = f"{check_abs_path_name}_abs_path"
                        abs_path = conf_data.get(abs_path_name, None)
                        if not abs_path:
                            file_path = conf_data[check_abs_path_name]
                            conf_data[abs_path_name] = os.path.abspath(os.path.join(config_dir, file_path))
                    builder_conf[conf_name] = conf_data
        #
        builder_config['module_config'] = module_config
        builder_config['strategy_config'] = strategy_config
        builder_config['runner_config'] = runner_config

        return builder_config

    def search_path_config_files(self, config_path):
        ret = []
        for filename in os.listdir(config_path):
            if filename.endswith(".json"):
                ret.append(os.path.join(config_path, filename))
        return ret

    def build(self, config, output_path, format_code=True):
        #
        build_info = self.parse_build_config(config[0])
        ea_code = self.generate_ea_code(build_info)
        if ea_code is None:
            return False
        if format_code:
            ea_code = format_str(ea_code, mode=FileMode())
        # print(ea_code)
        with open(output_path, "w") as f:
            f.write(ea_code)
        return True
