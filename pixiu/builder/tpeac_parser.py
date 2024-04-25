import json
import re
import hashlib
from typing import Union

class TPEACParser:

    def __init__(self, options):
        self.expression = []
        self.functions = {}
        self.functions_names = {}
        self.options = options

    def set_defs(self, type, defs):
        if type == 'functions':
            for def_name in defs:
                func = defs[def_name]
                func_md5 = hashlib.md5(json.dumps(func, sort_keys=True).encode('utf-8')).hexdigest()
                #
                data = self.functions.get(func_md5, None)
                if data is not None:
                    if def_name != data['name']:
                        raise f'name exists: {def_name}'
                func_name = func['name'].lower()
                key = f"{func_name}"
                name_list = self.functions_names.get(key, [])
                # if def_name in name_list:
                #     raise f'name exists: {def_name}'
                name_list.append(def_name)
                self.functions_names[key] = name_list
                data = dict(name=def_name, func=func)
                self.functions[func_md5] = data
        return True



    def valid(self, exp: str):
        new_exp = exp.strip()
        if len(new_exp) == 0:
            print(f"valid error: expression is blank.")
            return None
        if new_exp.count('(') != new_exp.count(')'):
            print(f"valid error: ( or ) mismatch.")
            return None
        return new_exp

    def state(self, t, c, idx):
        return dict(type=t, c=c, idx=idx, str=c)

    def combined_json_string(self, output: dict, string: str, val_string: str, end: bool = False) -> str:
        if end:
            if re.match(r"^\[.*\]$", string):
                output['json_string'] = f"{string}" if not output['json_string'] else f"{output['json_string']}{string}"
            else:
                output['json_string'] = f"[{string}]" if not output['json_string'] else f"{output['json_string']}[{string}]"
        s = val_string.strip()
        if not s:
            return string

        val_del = ''
        try:
            float(s)
        except ValueError:
            val_del = '"'
        delimiter_before = ', '
        if len(string) > 0 and string[-1] == '[' or s == ']':
            delimiter_before = ''
        delimiter_after = ''
        if s in ('and', 'or'):
            if re.match(r"^\[.*\]$", string):
                output['json_string'] = f"{string}, \"{s}\", " if not output['json_string'] else f"{output['json_string']}{string}, \"{s}\", "
            else:
                output['json_string'] = f"[{string}], \"{s}\", " if not output['json_string'] else f"{output['json_string']}[{string}], \"{s}\", "
            return ''
        if s in ('not',):
            output['json_string'] = f"{string}, \"{s}\", " if not output['json_string'] else f"{output['json_string']}{string}, \"{s}\", "
            return ''
        if s not in ('[', ']'):
            s = f'{val_del}{s}{val_del}'
        string = f"{s}" if not string else f"{string}{delimiter_before}{s}{delimiter_after}"
        return string

    def parse_token(self, exp, c, idx, state, sub_string, output):
        current = state
        if c == '(':
            if current['type'] == 'str':
                current['type'] = 'func('
                current['c'] = c
            else:
                current = self.state('', '', idx)
                sub_string = self.combined_json_string(output, sub_string, '[')
        elif c == ')':
            if current['type'] in ('func(',):
                sidx = current['idx']
                current['str'] = exp[sidx:idx + 1]
                current['type'] = 'func'
                sub_string = self.combined_json_string(output, sub_string, current['str'])
                current = self.state('', '', idx)
            else:
                sub_string = self.combined_json_string(output, sub_string, current['str'])
                sub_string = self.combined_json_string(output, sub_string, ']')
                current = self.state('', '', idx)
        elif c == ',':
            pass
        elif c in (' ', '>', '<', '=', '!', '+', '-', '*', '/'):
            # if current['type'] not in ('str', ')', 'op', 'func_end'):
            if current['type'] in ('func(',):
                current['str'] += c
            elif current['type'] in ('str',):
                sub_string = self.combined_json_string(output, sub_string, current['str'])
                current = self.state('', '', idx)
            else:
                if current['type'] in ('op', 'op2') and c != ' ':
                    current['str'] += c
                if current['str'] in ('not',):
                    current['type'] = 'op1'
                    current['c'] = c
                elif current['str'] in ('and', 'or', '!=', '==', '>=', '<=') or c in (
                '>', '<', '+', '-', '*', '/', '!', '='):
                    if current['type'] != 'op2':
                        current['str'] = c
                    current['type'] = 'op2'
                    current['c'] = c
                elif current['type'] == '':
                    current['type'] = 'op'
                    current['c'] = c
                    current['str'] = c.strip()
                    current['idx'] = idx
        else:
            if current['type'] in ('str', 'func('):
                current['str'] += c
            else:
                if current['type'] in ('op', 'op1', 'op2'):
                    sub_string = self.combined_json_string(output, sub_string, current['str'])
                    current = self.state('', '', idx)
                current['type'] = 'str'
                current['c'] = c
                current['str'] = c
                current['idx'] = idx

        if len(exp) - 1 == idx:
            if current['type'] != '':
                sub_string = self.combined_json_string(output, sub_string, current['str'])
                current['right'] = self.state('', '', idx)
                current = current['right']
            sub_string = self.combined_json_string(output, sub_string, current['str'], end=True)
        return current, sub_string

    def parse_expression(self, exp, state):
        current = state
        output = dict(json_string='')
        sub_string = ''
        # for i in range(current['idx'], len(exp)):
        for i in range(len(exp)):
            current, sub_string = self.parse_token(exp, exp[i], i, current, sub_string, output)
        return output['json_string']

    def convert_variable_format(self, string):
        if string.startswith('@'):
            sl = string.split('.')
            if sl[0] in ('@var', 'variables'):
                return True, string
        return False, string

    def get_expression_value(self, string):
        if not isinstance(string, str):
            return False, string
        if string.startswith('@'):
            sl = string.split('.')
            if sl[0] in ('@var', 'variables'):
                return True, string
            elif sl[0] in ('@func', '@functions'):
                func = self.find_function_by_name(sl[1])['func']
                func_str = f"{func['module']}.{func['name']}("
                for idx in range(len(func['params'])):
                    p = func['params'][idx]
                    delimiter = ', '
                    if idx == len(func['params']) - 1:
                        delimiter = ''
                    func_str = f"{func_str}{p}{delimiter}"
                func_str = f"{func_str})"
                return True, func_str
        return False, string

    def convert_expression_format(self, string):
        if not isinstance(string, str):
            return False, string
        get_expression_value = self.options.get('get_expression_value', self.get_expression_value)
        return get_expression_value(string)

    def is_function_string(self, fn: str):
        s = fn.strip()
        # reg1 = r'\s*[\w]+\([\s\w:,]+\)\s*[-=]>\s*[\w]+'
        reg = r'\s*[\w\.]+\([\s@\.\'\"/\w:,]+\)$'
        # if re.match(reg1, s):
        #     return True
        if re.match(reg, s):
            return True
        return False

    def parse_function(self, fn: str, module: str):
        if not self.is_function_string(fn):
            return None
        ret = dict(module=module, name='', params=[])
        sa = re.match(r'^[\w\.]+', fn)[0].split('.')
        if len(sa) > 2:
            return None
        ret['module'] = sa[0]
        ret['name'] = sa[1]
        params = re.search(r'[ \( ]\s*([^\)]*)\s*[^\)]*[\)]', fn)
        params = params[0][1:-1]
        ret['params'] = [s.strip() for s in params.split(',')]

        return ret

    def add_functions_dict(self, func):
        func_md5 = hashlib.md5(json.dumps(func, sort_keys=True).encode('utf-8')).hexdigest()
        data = self.functions.get(func_md5, None)
        if data is None:
            func_name = func['name'].lower()
            key = f"{func_name}"
            name_list = self.functions_names.get(key, [])
            n = f"{func_name}"
            i = len(name_list) + 1
            while True:
                n = f"{func_name}_{i}"
                if n not in name_list:
                    break
                i += 1
            name_list.append(n)
            self.functions_names[key] = name_list
            data = dict(name=n, func=func)
            self.functions[func_md5] = data
        n = data['name']
        return n

    def find_function_by_name(self, name):
        for func_md5, func in self.functions.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
            if name == func['name']:
                return func
        return None

    def convert_function_format(self, string):
        ret = self.parse_function(string, '')
        if ret:
            params = []
            for p in ret['params']:
                r, p = self.convert_variable_format(p)
                params.append(p)
            func = dict(module=ret['module'], name=ret['name'], params=params)
            add_functions_dict = self.options.get('add_functions_dict', self.add_functions_dict)
            name = add_functions_dict(func)
            return True, f"@func.{name}"
        return False, string

    def parse_expression_item(self, item):
        if isinstance(item, list):
            for idx in range(len(item)):
                d = item[idx]
                item[idx] = self.parse_expression_item(d)
        elif isinstance(item, str):
            converted, new_val = self.convert_variable_format(item)
            if converted:
                item = new_val
            else:
                converted, new_val = self.convert_function_format(item)
                if converted:
                    item = new_val

        return item

    def parse_build_config_item(self, item, exp_str, layer=0):
        if isinstance(item, list):
            sub_exp = ""
            for idx in range(len(item)):
                d = item[idx]
                sub_exp = self.parse_build_config_item(d, sub_exp, layer + 1)
            if len(item) > 1 and layer > 0:
                exp_str = f"({sub_exp})" if not exp_str else f"{exp_str} ({sub_exp})"
            else:
                exp_str = f"{sub_exp}" if not exp_str else f"{exp_str} {sub_exp}"
        else:
            converted, new_val = self.convert_expression_format(item)
            exp_str = f"{new_val}" if not exp_str else f"{exp_str} {new_val}"
        return exp_str

    def json_config_string_to_build_config(self, json_string):
        json_dict = json.loads(f"[{json_string}]")
        ret = self.parse_expression_item(json_dict)
        return ret

    def build_config_to_expression(self, build_config):
        exp_str = ""
        ret = self.parse_build_config_item(build_config, exp_str)
        return ret

    def expression_to_build_config(self, expression: str) -> Union[dict, None]:
        valid_exp = self.valid(expression)
        if valid_exp is None:
            return None
        state = self.state('', '', 0)
        json_config_string = self.parse_expression(valid_exp, state)
        build_config = self.json_config_string_to_build_config(json_config_string)
        return build_config

    def parse(self, exp: str):
        valid_exp = self.valid(exp)
        if valid_exp is None:
            return False
        state = self.state('', '', 0)
        struct_string = self.parse_expression(valid_exp, state)
        # print(f"state = {state}")
        print(f"struct_string = {struct_string}")
        print(f"exp_json_string = {self.exp_json_string}")
        # print(json.loads(f"{self.exp_json_string}"))
        build_config = self.json_config_string_to_build_config(self.exp_json_string)
        print(f"functions = {self.functions}")
        print(f"functions_names = {self.functions_names}")
        print(f"build_config = {build_config}")
        expression = self.build_config_to_expression(build_config)
        print(f"expression = {expression}")
        return True
