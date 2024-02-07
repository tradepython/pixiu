# indicator
class IndicatorModule:

    def __init__(self,):
        pass

    def adx(self, options):
        params = options['params']
        symbol_data = params['symbol_data']
        period = params['period']
        shift = params['shift']
        code = f"iADX({symbol_data}, timeperiod={period}, shift={shift})"
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
