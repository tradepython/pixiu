
import os
import json5 as json
import traceback
from jinja2 import Template
from black import format_str, FileMode
import importlib
import hashlib
from .tpeac_parser import (TPEACParser, )


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
            va = value.split('.')
            if len(va) > 1:
                if va[0] in ('@variables', '@var'):
                    items = va[1:]
                    parameter_builder = self.build_data['variables'][items[0]]
                    ret = parameter_builder.get_variable_name()
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] in ('@symbols', '@sym'):
                    items = va[1:]
                    symbol_builder = self.build_data['symbols'][items[0]]
                    ret = symbol_builder.get_variable_name()
                    ret = self.__write_value_items__(ret,  items)
                elif va[0] in ('@functions', '@func'):
                    func_builder = self.build_data['functions'][va[1]]
                    var_list = func_builder.get_variables(func_builder.package, func_builder.module, func_builder.name)
                    ret = var_list[0]['name']
                else:
                    raise Exception(f"Unknown path name: {va[0]}")

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
        # ret = self.config['value']
        # if isinstance(ret, dict):
        #     ret = ret['value']
        # return ret

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
    def md5(self):
        func_md5 = hashlib.md5(json.dumps(self.config, sort_keys=True).encode('utf-8')).hexdigest()
        return func_md5

    @property
    def package(self):
        package = self.config.get('package', 'pixiu')
        return package

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

    def get_module_config(self, package, module, version='latest'):
        module_config = self.builder.get_builder_config('module_config')
        return module_config[package][module][version]

    def get_function_config(self, package, module, name):
        return self.get_module_config(package, module)['functions'][name]

    def get_module(self, package, module_name):
        module_config = self.get_module_config(package, module_name)
        module = self.modules.get(module_name, None)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, module_config['file_abs_path'])
            module = importlib.util.module_from_spec(spec)
            self.modules[module_name] = module
            spec.loader.exec_module(module)
            # module.MyClass()
        cls = eval(f"module.{module_config['class']}")
        return cls

    def call_function(self, package, module, name, options):
        func_config = self.get_function_config(package, module, name)
        cls = self.get_module(package, module)
        func = getattr(cls, func_config['method'])
        param_dict = {}
        # for key in func_config['params']:
        #     param_dict[key] = self.get_value(func_config['params'][key], self.params[key])
        for idx in range(len(func_config['params'])):
            fc = func_config['params'][idx]
            key = fc['name']
            if isinstance(self.params, dict):
                val = self.params[key]
            else:
                val = self.params[idx]
            param_dict[key] = self.get_value(fc, val)
        options['params'] = param_dict

        return func(cls(), options)

    def get_variables(self, package, module, name):
        func_config = self.get_function_config(package, module, name)
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
            variables = self.get_variables(self.package, self.module, self.name)
            options['variables'] = variables
        code = self.call_function(self.package, self.module, self.name, options)
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

    # def generate_operation_element_code(self, element):
    #     v0 = self.get_value(None, element[0])
    #     v1 = self.get_value(None, element[1])
    #     v2 = self.get_value(None, element[2])
    #     c = f"{v0} {v1} {v2}"
    #     # code = f"{code} {op} {c}" if code else f"{c}"
    #     return c

    # def generate_condition_elements_code(self, code,   condition_elements):
    #     # op = condition_elements['op']
    #     # values = condition_elements['values']
    #     val = condition_elements
    #     op = ''
    #     # for val in values:
    #     if isinstance(val, list):
    #         c = self.generate_operation_element_code(val)
    #     else:
    #         # c = self.generate_condition_elements_code('', val)
    #         c = val
    #     code = f"{code} {op} {c}" if code else f"{c}"
    #     return f"({code})"

    # def generate_condition_elements_code(self, code,   condition_elements):
    #     op = condition_elements['op']
    #     values = condition_elements['values']
    #     for val in values:
    #         if isinstance(val, list):
    #             c = self.generate_operation_element_code(val)
    #         else:
    #             c = self.generate_condition_elements_code('', val)
    #         code = f"{code} {op} {c}" if code else f"{c}"
    #     return f"({code})"
    #
    def get_expression_value(self, string):
        v = self.get_value(None, string)
        return True, v

    def add_functions_dict(self, func):
        func_obj = self.builder.find_functions_config(self.build_data, func)
        if func_obj is None:
            func_obj = self.builder.add_functions_config(self.build_data, None, func)
        return func_obj.key

    def generate_condition_code(self, condition_config):
        tpeac = TPEACParser(options=dict(get_expression_value=self.get_expression_value,
                                         add_functions_dict=self.add_functions_dict))
        if isinstance(condition_config, list):
            code = tpeac.build_config_to_expression(condition_config)
        elif isinstance(condition_config, str):
            bc = tpeac.expression_to_build_config(condition_config)
            code = tpeac.build_config_to_expression(bc)
        else:
            raise Exception('Error: Invalid condition format')
        # code = ''
        # for cc in condition_config:
        #     code = self.generate_condition_elements_code(code, cc)
        return code

    def valid_source(self, source):
        valid_source = ('balance',)
        return source in valid_source

    def p2f(self, x, failed_value=None):
        try:
            source = None
            if isinstance(x, str) and len(x) > 1:
                s = x.strip(' ')
                if s[-1:] == '%':
                    return float(x.rstrip('%')) / 100, 'percent', source
                else:
                    ary = s.split(':')
                    if len(ary) == 2:
                        if ary[0][-1:] == '%':
                            source = ary[1].lower()
                            return float(ary[0].rstrip('%')) / 100, 'percent', source
        except:
            pass
        return failed_value, None, None

    def to_float(self, x, failed_value=None):
        ret = failed_value
        ret_type = None
        ret_source = None
        try:
            if isinstance(x, float):
                ret = x
                ret_type = 'float'
            elif isinstance(x, int):
                ret = x
                ret_type = 'int'
            else:
                ret, ret_type, ret_source = self.p2f(x)
                if ret is None:
                    ret = float(x)
                    ret_type = 'float'
        except:
            pass
        return ret, ret_type, ret_source

    def valid_order_config_tp_sl(self, dir, is_tp, conf, tp_type, sl_type, order_volume):
        conf_name = 'take profit' if is_tp else 'stop loss'
        conf_type = tp_type if is_tp else sl_type
        neg_or_pos = 'positive' if is_tp else 'negative'
        sign = 1 if is_tp else -1
        check_order_volume = False

        if conf:
            errmsg = f'Invalid {conf_name} of {dir} order !'
            try:
                conf_type = conf.get('type', None)
                if conf_type is None or conf_type not in ('pips', 'money', 'percent', 'pl-ratio'):
                    errmsg = f'Invalid {conf_name} type of {dir} order !'
                    return False, errmsg
                if conf_type == 'pips':
                    pips = int(conf.get('pips', 0))
                    if pips <= 0:
                        errmsg = f'Invalid {conf_name} pips of {dir} order (must be {neg_or_pos}) !'
                        return False, errmsg
                elif conf_type == 'money':
                    money = float(conf.get('money', 0))
                    if money * sign <= 0:
                        errmsg = f'Invalid {conf_name} money of {dir} order (must be {neg_or_pos}) !'
                        return False, errmsg
                    check_order_volume = True
                elif conf_type == 'percent':
                    percent = conf.get('percent', None)
                    v, rt, rs = self.to_float(percent)
                    if v is None or v * sign <= 0:
                        errmsg = f'Invalid {conf_name} percent of {dir} order (must be {neg_or_pos}) !'
                        return False, errmsg
                    source = conf.get('source', 'balance')
                    if source:
                        source_dict = {'params': {}}
                        if isinstance(source, str):
                            pass
                        elif isinstance(source, dict):
                            source_dict = source
                            source = source_dict['name']
                        else:
                            errmsg = f'Invalid {conf_name} source of {dir} order !'
                            return False, errmsg
                        if source not in ('balance', 'atr'):
                            errmsg = f'Invalid {conf_name} source of {dir} order !'
                            return False, errmsg
                        if source in ('atr',):
                            period = source_dict['params'].get('period', 0)
                            if period <= 0:
                                errmsg = f'Invalid {conf_name} atr period of {dir} order !'
                                return False, errmsg
                            timeframe = source_dict['params'].get('timeframe', None)
                            if timeframe is None:
                                errmsg = f'Invalid {conf_name} atr timeframe of {dir} order !'
                                return False, errmsg
                            shift = source_dict['params'].get('shift', 0)
                            if shift < 0:
                                errmsg = f'Invalid {conf_name} atr shift of {dir} order !'
                                return False, errmsg
                        else:
                            check_order_volume = True
                elif conf_type == 'pl-ratio':
                    ratio = float(conf.get('ratio', 0))
                    if ratio <= 0:
                        errmsg = f'Invalid profit loss ratio of {dir} order (must be positive) !'
                        return False, errmsg
                else:
                    errmsg = f'Unknown {conf_name} type of {dir} order !'
                    return False, errmsg

                if tp_type == 'pl-ratio' and sl_type == 'pl-ratio':
                    errmsg = f'The stop loss and take profit types of {dir} order cannot be \'pl-ratio\' at the same time !'
                    return False, errmsg

                if check_order_volume and order_volume <= 0:
                    errmsg = f'Invalid positions volume of {dir} order (must be positive) !'
                    return False, errmsg

            except:
                return False, errmsg
        return True, ''

    def valid_order_config(self, dir, order_config):
        tp_type = None
        sl_type = None
        pos_conf = order_config.get('positions', None)
        tp_conf = order_config.get('take_profit', None)
        sl_conf = order_config.get('stop_loss', None)
        if pos_conf is None:
            errmsg = f'Positions of {dir} order is None !'
            return False, errmsg

        order_volume = 0
        errmsg = f'Invalid positions of {dir} order !'
        try:
            pos_type = pos_conf.get('type', None)
            if pos_type is None or pos_type not in ('volume', 'money', 'percent'):
                errmsg = f'Invalid positions type of {dir} order !'
                return False, errmsg
            pos_martingale = pos_conf.get('martingale', None)
            if pos_martingale is not None:
                if isinstance(pos_martingale, bool):
                    pass
                elif isinstance(pos_martingale, dict):
                    multiplier = pos_martingale.get('multiplier', 0)
                    if multiplier < 0:
                        errmsg = f'Invalid positions martingale multiplier of {dir} order (must be positive) !'
                        return False, errmsg
                else:
                    errmsg = f'Invalid positions martingale of {dir} order !'
                    return False, errmsg

            if pos_type == 'volume':
                order_volume = float(pos_conf.get('volume', 0))
                if order_volume <= 0:
                    errmsg = f'Invalid positions volume of {dir} order (must be positive) !'
                    return False, errmsg
            elif pos_type == 'money':
                order_money = float(pos_conf.get('money', 0))
                if order_money == 0:
                    errmsg = f'Invalid positions money of {dir} order (must not be zero) !'
                    return False, errmsg
            elif pos_type == 'percent':
                order_percent = pos_conf.get('percent', None)
                v, rt, rs = self.to_float(order_percent)
                if v == 0:
                    errmsg = f'Invalid positions percent of {dir} order (must not be zero) !'
                    return False, errmsg
                order_percent_source = pos_conf.get('source', 'balance')
                if order_percent_source != 'balance':
                    errmsg = f'Invalid positions source of {dir} order (must be balance) !'
                    return False, errmsg
        except:
            return False, errmsg

        if tp_conf:
            tp_type = tp_conf.get('type', None)

        if sl_conf:
            sl_type = sl_conf.get('type', None)

        ret, errmsg = self.valid_order_config_tp_sl(dir, True, tp_conf, tp_type, sl_type, order_volume)
        if not ret:
            return ret, errmsg

        ret, errmsg = self.valid_order_config_tp_sl(dir, False, sl_conf, tp_type, sl_type, order_volume)
        if not ret:
            return ret, errmsg

        return True, ''

    def parse_order_config(self, config):
        ret = None
        os = config.get('order', None)
        if os:
            ret = os.copy()
            profit_loss_ratio = int(ret.get('profit_loss_ratio', 0))
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

    def get_order_config(self, options):
        default_order_config = self.parse_order_config(self.config)
        #
        long_config = self.long
        long_order_config = self.parse_order_config(long_config)
        if long_order_config is None:
            long_order_config = default_order_config
        #
        short_config = self.short
        short_order_config = self.parse_order_config(short_config)
        if short_order_config is None:
            short_order_config = default_order_config
        if long_order_config is None or short_order_config is None:
            raise Exception(f"Error: Entry order config not found!")
        #
        valid, errmsg = self.valid_order_config('long', long_order_config)
        if not valid:
            raise Exception(errmsg)
        valid, errmsg = self.valid_order_config('short', short_order_config)
        if not valid:
            raise Exception(errmsg)
        return dict(long=long_order_config, short=short_order_config)

    def build_code(self, options):
        #
        long_config = self.long
        condition_config = long_config['condition']
        long_code = self.generate_condition_code(condition_config)
        #
        short_config = self.short
        condition_config = short_config['condition']
        short_code = self.generate_condition_code(condition_config)
        #
        codes = (f"ret = dict()",
                 f"if {long_code}:",
                 f"    ret[PositionType.LONG] = dict(price=None)",
                 f"if {short_code}:",
                 f"    ret[PositionType.SHORT] = dict(price=None)",
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

    def parse_template_variables_config(self, build_data, template):
        template_config = self.builder_config['template_config']
        rc = self.get_template_data(template, template_config)
        #
        variables = {}
        index = 0
        for key in rc['variables']:
            variables[key] = VariableBuilder(self, key, rc['variables'][key], index, build_data)
            index += 1
        build_data['template_variables'] = variables
        return build_data

    def get_template_data(self, template, template_config):
        package = template.get('package', 'pixiu')
        strategy_name = template['name']
        strategy_version = template['version']
        rc = template_config[package][strategy_name][strategy_version]
        return rc

    # def parse_runner_variables_config(self, build_data, strategy_name):
    #     runner_config = self.builder_config['runner_config']
    #     rc = runner_config[strategy_name]
    #     #
    #     variables = {}
    #     index = 0
    #     for key in rc['variables']:
    #         variables[key] = VariableBuilder(self, key, rc['variables'][key], index, build_data)
    #         index += 1
    #     build_data['runner_variables'] = variables
    #     return build_data
    #
    # def parse_strategy_variables_config(self, build_data, strategy_name):
    #     strategy_config = self.builder_config['strategy_config']
    #     sc = strategy_config[strategy_name]
    #     #
    #     variables = {}
    #     index = 0
    #     for key in sc['variables']:
    #         variables[key] = VariableBuilder(self, key, sc['variables'][key], index, build_data)
    #         index += 1
    #     build_data['strategy_variables'] = variables
    #     return build_data

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

    def add_functions_config(self, build_data, key, func_config, index=None):
        functions = build_data['functions']
        functions_md5 = build_data['functions_md5']
        functions_names = build_data['functions_names']
        #
        if index is None:
            index = len(functions)

        if key is None:
            func_name = func_config['name'].lower()
            n = f"{func_name}"
            name_list = functions_names.get(n, [])
            i = len(name_list) + 1
            key = n
            while True:
                key = f"{func_name}_{i}"
                if key not in name_list:
                    break
                i += 1
        #
        func = FunctionBuilder(self, key, func_config, index, build_data)
        functions[key] = func
        functions_md5[func.md5] = func
        fn = f"{func.name.lower()}"
        name_list = functions_names.get(fn, [])
        name_list.append(key)
        functions_names[fn] = name_list
        return func

    def find_functions_config(self, build_data, func_config):
        # functions = build_data['functions']
        functions_md5 = build_data['functions_md5']
        # functions_names = build_data['functions_names']
        #
        func = FunctionBuilder(self, None, func_config, 0, build_data)
        #
        ret = functions_md5.get(func.md5, None)
        return ret


    def parse_functions_config(self, build_data, functions_config):
        build_data['functions'] = {}
        build_data['functions_md5'] = {}
        build_data['functions_names'] = {}
        index = 0
        for key in functions_config:
            self.add_functions_config(build_data, key, functions_config[key], index)
            index += 1
        # build_data['functions'] = functions
        # build_data['functions_md5'] = functions_md5
        # build_data['functions_names'] = functions_names
        return build_data

    # def parse_functions_config(self, build_data, functions_config):
    #     functions = {}
    #     functions_md5 = {}
    #     functions_names = {}
    #     index = 0
    #     for key in functions_config:
    #         func = FunctionBuilder(self, key, functions_config[key], index, build_data)
    #         functions[key] = func
    #         functions_md5[func.md5] = func
    #         fn = f"{func.name.lower()}"
    #         name_list = functions_names.get(fn, [])
    #         name_list.append(key)
    #         functions_names[fn] = name_list
    #         index += 1
    #     build_data['functions'] = functions
    #     build_data['functions_md5'] = functions_md5
    #     build_data['functions_names'] = functions_names
    #     return build_data
    #
    def parse_options_config(self, build_data, options_config):
        template_variables = build_data.get('template_variables', {})
        # checking options
        for opt_name in options_config:
            var = template_variables[opt_name]
            opt_val = options_config[opt_name]
            opt_script_settings = None
            if isinstance(opt_val, dict):
                opt_script_settings = opt_val.get('script_settings', None)
                opt_val = opt_val['value']
            var.config['value'] = json.dumps(opt_val, quote_keys=True) if var.config['type'] == 'str' else opt_val
            if opt_script_settings is not None:
                var.config['script_settings'] = opt_script_settings

        return build_data
    # def parse_options_config(self, build_data, options_config):
    #
    #     default_options = dict(
    #         enable_trailing_profit=dict(default=True, type='bool',
    #                              desc=dict(en=f"Enable order trailing profit.")),
    #         enable_weekend_holding=dict(default=True, type='bool',
    #                              desc=dict(en=f"Enable holding positions over the weekend.")),
    #         enable_night_open=dict(default=True, type='bool',
    #                              desc=dict(en=f"Enable opening positions at night (21-23).")),
    #         enable_night_holding=dict(default=True, type='bool',
    #                              desc=dict(en=f"Enable holding positions overnight.")),
    #         enable_group_across_days=dict(default=True, type='bool',
    #                              desc=dict(en=f"Allow trading groups across days.")),
    #         enable_open_crossing=dict(default=True, type='bool',
    #                              desc=dict(en=f"When the price is volatile, you can open positions across the price "
    #                                           f"the low or high point.")),
    #     )
    #     system_variables = build_data.get('system_variables', {})
    #     index = len(system_variables)
    #     # checking options
    #     for opt_name in default_options:
    #         if opt_name not in options_config:
    #             options_config[opt_name] = default_options[opt_name]['default']
    #     #
    #     for opt_name in options_config:
    #         key = f"options_{opt_name}"
    #         opt_val = options_config[opt_name]
    #         script_settings = True
    #         #
    #         opt_type = 'str'
    #         opt_desc = dict(en="")
    #         default_item = default_options.get(opt_name, None)
    #         if default_item is not None:
    #             opt_type = default_item['type']
    #             opt_desc = default_item['desc']
    #         #
    #         config = dict(type=opt_type, value=json.dumps(opt_val, quote_keys=True) if opt_type == 'str' else opt_val,
    #                       desc=opt_desc, required=True, script_settings=script_settings
    #                       )
    #         system_variables[key] = VariableBuilder(self, key, config, index, build_data)
    #         index += 1
    #     build_data['system_variables'] = system_variables
    #
    #     return build_data

    def parse_entry_config(self, build_data, entry_config):
        build_data['entry'] = EntryBuilder(self, None,  entry_config, 0, build_data)
        #
        system_variables = build_data.get('system_variables', {})
        oc = build_data['entry'].get_order_config(None)
        index = 0
        for d in ('long', 'short'):
            oc_dir = oc[d]
            for oc_item in oc_dir:
                script_settings = oc_dir.get('script_settings', True)
                oc_val = oc_dir[oc_item]
                key = f"entry_{d}_{oc_item}"
                #
                if oc_item == 'profit_loss_ratio':
                    oc_item_type = "int"
                else:
                    oc_item_type = "str"
                #
                oc_item_desc = dict(en="")
                if oc_item == 'profit_loss_ratio':
                    oc_item_desc = dict(en=f"Profit/loss ratio of {d} orders.")
                elif oc_item == 'positions':
                    oc_item_desc = dict(en=f"The positions of {d} orders.")
                elif oc_item == 'take_profit':
                    oc_item_desc = dict(en=f"Take profit on {d} orders.")
                elif oc_item == 'stop_loss':
                    oc_item_desc = dict(en=f"Stop loss on {d} orders.")
                elif oc_item == 'script_settings':
                    continue
                #
                config = dict(type=oc_item_type, value=json.dumps(oc_val, quote_keys=True),
                              desc=oc_item_desc, required=True, script_settings=script_settings
                              )
                system_variables[key] = VariableBuilder(self, key, config, index, build_data)
                index += 1
        build_data['system_variables'] = system_variables

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
        errmsg = ''
        try:
            build_config = config['build_config']
            if build_config['version'] != "v1.0alpha":
                return None, 'Invalid build config version'
            trading = build_config['trading']
            coding = build_config['coding']
            # self.parse_runner_variables_config(build_data,  coding['runner']['name'])
            self.parse_template_variables_config(build_data,  coding['template'])
            # self.parse_strategy_variables_config(build_data,  coding['strategy']['name'])
            self.parse_variables_config(build_data, trading['variables'])
            self.parse_symbols_config(build_data, trading['symbols'])
            self.parse_functions_config(build_data, trading['functions'])
            self.parse_entry_config(build_data, trading['entry'])
            self.parse_exit_config(build_data, trading['exit'])
            self.parse_options_config(build_data, trading['options'])
            build_info = dict(config=build_config, data=build_data)
        except Exception as e:
            errmsg = str(e)
            traceback.print_exc()
        return build_info, errmsg

    def generate_entry_exit_code(self, build_data, options, code_type):
        codes = []
        #
        ed = build_data[code_type]
        code = ed.build_code({})
        #
        for key in build_data['symbols']:
            sd = build_data['symbols'][key]
            codes.append(sd.build_code(options))

        for key in build_data['functions']:
            options = {}
            fd = build_data['functions'][key]
            codes.append(fd.build_code(options))

        # options = {}
        # ed = build_data[code_type]
        # codes.append(ed.build_code(options))
        codes.append(code)
        return codes

    def generate_ea_code(self, build_info):
        ret = None
        errmsg = ''
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
            #
            # for var_cat in ('system_variables', 'runner_variables', 'strategy_variables', 'variables'):
            for var_cat in ('system_variables', 'template_variables', 'variables'):
                for key in build_data[var_cat]:
                    pd = build_data[var_cat][key]
                    variables_codes.append(pd.build_code(options))
                    ss = pd.get_script_settings()
                    if pd.script_settings:
                        script_settings['params'][pd.name] = ss
                        vssc = pd.get_valid_script_settings_codes()
                        if vssc is not None:
                            valid_script_settings_codes.append(vssc)

            entry_codes = self.generate_entry_exit_code(build_data, options, 'entry')
            exit_codes = self.generate_entry_exit_code(build_data, options, 'exit')
            #
            pc = self.generate_code_string_list(variables_codes)
            ecl = self.generate_code_string_list(entry_codes)
            exl = self.generate_code_string_list(exit_codes)
            vsscl = self.generate_code_string_list(valid_script_settings_codes)
            # script_settings_code = json.dumps(script_settings, quote_keys=True)

            # template_name = build_config['coding']['template']['name']
            # template_config = self.get_builder_config('template_config')
            # config_data = template_config[template_name]
            config_data = self.get_template_data(build_config['coding']['template'],
                                                 self.get_builder_config('template_config'))
            template_code = dict(variables=pc, get_entry_data=ecl, get_exit_data=exl, valid_script_settings=vsscl)
            if isinstance(config_data['entry'], str):
                entry_func_name = config_data['entry']
            if isinstance(config_data['exit'], str):
                exit_func_name = config_data['exit']
            template_code[entry_func_name] = ecl
            template_code[exit_func_name] = exl
            strategy = dict(class_name=build_config['name'],
                            code=template_code,
                            script_settings=script_settings
                            )

            j2_file = open(config_data['template_abs_path'])
            template = Template(j2_file.read())
            ret = template.render(strategy=strategy)
            # print(ret)
        except Exception as e:
            if isinstance(e, KeyError):
                errmsg = f"Undefined variable {str(e)}"
            else:
                errmsg = repr(e)
            traceback.print_exc()
        return ret, errmsg
    #
    # def generate_ea_code(self, build_info):
    #     ret = None
    #     try:
    #         #
    #         build_data = build_info['data']
    #         build_config = build_info['config']
    #         options = {}
    #         variables_codes = []
    #         valid_script_settings_codes = []
    #         script_settings = dict(params={}, charts={"price": {"series": [
    #                                         {"name": "top_signal", "color": "#89F3DAFF"},
    #                                         {"name": "bottom_signal", "color": "#e7dc48"}]
    #               }})
    #         #
    #         for var_cat in ('system_variables', 'runner_variables', 'strategy_variables', 'variables'):
    #             for key in build_data[var_cat]:
    #                 pd = build_data[var_cat][key]
    #                 variables_codes.append(pd.build_code(options))
    #                 ss = pd.get_script_settings()
    #                 if pd.script_settings:
    #                     script_settings['params'][pd.name] = ss
    #                     vssc = pd.get_valid_script_settings_codes()
    #                     if vssc is not None:
    #                         valid_script_settings_codes.append(vssc)
    #
    #         entry_codes = self.generate_entry_exit_code(build_data, options, 'entry')
    #         exit_codes = self.generate_entry_exit_code(build_data, options, 'exit')
    #         #
    #         pc = self.generate_code_string_list(variables_codes)
    #         ecl = self.generate_code_string_list(entry_codes)
    #         exl = self.generate_code_string_list(exit_codes)
    #         vsscl = self.generate_code_string_list(valid_script_settings_codes)
    #         # script_settings_code = json.dumps(script_settings, quote_keys=True)
    #         strategy = dict(class_name=build_config['name'],
    #                         code=dict(variables=pc, get_entry_data=ecl, get_exit_data=exl,
    #                                   valid_script_settings=vsscl),
    #                         script_settings=script_settings
    #                         )
    #         runner = dict(code=dict())
    #         strategy_name = build_config['coding']['strategy']['name']
    #         strategy_config = self.get_builder_config('strategy_config')
    #         config_data = strategy_config[strategy_name]
    #         j2_file = open(config_data['template_abs_path'])
    #         template = Template(j2_file.read())
    #         strategy_class_code = template.render(strategy=strategy)
    #         print(strategy_class_code)
    #         runner['strategy_class_name'] = strategy['class_name']
    #         runner['code']['strategy_class'] = strategy_class_code
    #
    #         # load strategy template
    #         runner_name = build_config['coding']['runner']['name']
    #         runner_config = self.get_builder_config('runner_config')
    #         config_data = runner_config[runner_name]
    #         j2_file = open(config_data['template_abs_path'])
    #         template = Template(j2_file.read())
    #         ret = template.render(runner=runner)
    #         print(ret)
    #     except:
    #         traceback.print_exc()
    #     return ret

    def load_builder_config(self, config_path, builder_config):
        module_config = builder_config.get('module_config', {})
        # strategy_config = builder_config.get('strategy_config', {})
        # runner_config = builder_config.get('runner_config', {})
        # package, name, version
        template_config = builder_config.get('template_config', {})
        config_dir = os.path.dirname(config_path)
        with open(config_path) as f:
            strategy_list = json.loads(f.read())
            for conf_dict in strategy_list:
                for conf_type in conf_dict:
                    conf_name = None
                    check_abs_path_name = None
                    conf_data = conf_dict[conf_type]
                    if conf_type == 'module_config':
                        package = conf_data.get('package', 'pixiu')
                        conf_name = conf_data['name']
                        version = 'latest' #conf_data['version']
                        builder_conf = module_config
                        check_abs_path_name = 'file'
                    # elif conf_type == 'strategy_config':
                    #     conf_name = conf_data['name']
                    #     builder_conf = strategy_config
                    #     check_abs_path_name = 'template'
                    # elif conf_type == 'runner_config':
                    #     conf_name = conf_data['name']
                    #     builder_conf = runner_config
                    #     check_abs_path_name = 'template'
                    elif conf_type == 'template_config':
                        package = conf_data.get('package', 'pixiu')
                        conf_name = conf_data['name']
                        version = conf_data['version']
                        builder_conf = template_config
                        check_abs_path_name = 'template'
                    else:
                        raise Exception("Unknown conf type")
                    # if conf_name in builder_conf:
                    #     raise Exception(f"Error: {conf_name} in {conf_type}")
                    #check abs_path
                    if check_abs_path_name:
                        abs_path_name = f"{check_abs_path_name}_abs_path"
                        abs_path = conf_data.get(abs_path_name, None)
                        if not abs_path:
                            file_path = conf_data[check_abs_path_name]
                            conf_data[abs_path_name] = os.path.abspath(os.path.join(config_dir, file_path))
                    #
                    pack = builder_conf.get(package, {})
                    cg = pack.get(conf_name, {})
                    if version in cg:
                        raise Exception(f"Error: {package}.{conf_name}.{version} in {conf_type}")
                    cg[version] = conf_data
                    pack[conf_name] = cg
                    builder_conf[package] = pack
        #
        builder_config['module_config'] = module_config
        builder_config['template_config'] = template_config
        # builder_config['strategy_config'] = strategy_config
        # builder_config['runner_config'] = runner_config

        return builder_config

    def search_path_config_files(self, config_path):
        ret = []
        for filename in os.listdir(config_path):
            if filename.endswith(".json"):
                ret.append(os.path.join(config_path, filename))
        return ret

    def build_code(self, config, format_code=False):
        #
        errmsg = ''
        build_info, errmsg = self.parse_build_config(config[0])
        if build_info is None:
            return None, errmsg
        ea_code, errmsg = self.generate_ea_code(build_info)
        if ea_code is None:
            return None, errmsg
        if format_code:
            ea_code = format_str(ea_code, mode=FileMode())
        return ea_code, errmsg

    def build(self, config, output_path, format_code=True):
        ea_code, errmsg = self.build_code(config, format_code=format_code)
        if ea_code is None:
            return False
        with open(output_path, "w") as f:
            f.write(ea_code)
        return True
