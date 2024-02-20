class CodeWriter:

    def __init__(self,):
        pass

    def generate_code(self, function_name, options, params_list):
        params = options['params']
        params_string = ""
        for name in params_list:
            val_name = name
            if isinstance(name, dict):
                d = name
                name = d['name']
                val_name = d['val_name']
            val = params[name]
            params_string = f"{params_string}, {val_name}={val}" if params_string else f"{val_name}={val}"
        code = f"{function_name}({params_string})"
        variables = options.get('variables', None)
        if variables:
            code = f"{variables[0]['name']} = {code}"
        return code


