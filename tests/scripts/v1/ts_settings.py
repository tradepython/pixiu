AddChart(name="price", chart={"series": [{"name": "top_signal", "color": "#89F3DAFF"},
                                         {"name": "bottom_signal", "color": "#e7dc48"}]})
AddParam("bool_test", value=True, type="bool", required=True)
AddParam("param_test", param={"value": False, "config": {"type": "bool", "required": True}})
AddParam("options_test", value=100, type="int", options={"0": "Option-0", "100": "Option-100"})
AddParam("optimizable_float_test", value=0.5, type="float", min=0.1, max=2.0, required=True,
         desc={"en": "Optimizable float sample", "zh": "可优化浮点参数示例"},
         optimizable=True,
         optimization={"type": "float", "start": 0.1, "stop": 2.0, "step": 0.1})
#
def PX_ValidScriptSettings(new_settings):
    if 'params' not in new_settings:
        return dict(success=False, errmsg='Not found params')
    params = new_settings['params']
    if 'bool_test' not in params:
        return dict(success=False, errmsg='Not found bool_test')

    if 'param_test' not in params:
        return dict(success=False, errmsg='Not found param_test')

    if 'options_test' not in params:
        return dict(success=False, errmsg='Not found options_test')
    if 'optimizable_float_test' not in params:
        return dict(success=False, errmsg='Not found optimizable_float_test')
    optimizable_float_test = params['optimizable_float_test']
    config = optimizable_float_test.get('config', {})
    if config.get('optimizable', False) is not True:
        return dict(success=False, errmsg='optimizable_float_test.config.optimizable invalid')
    optimization = config.get('optimization', {})
    if optimization.get('type', None) != 'float':
        return dict(success=False, errmsg='optimizable_float_test.config.optimization.type invalid')
    if optimization.get('start', None) != 0.1:
        return dict(success=False, errmsg='optimizable_float_test.config.optimization.start invalid')
    if optimization.get('stop', None) != 2.0:
        return dict(success=False, errmsg='optimizable_float_test.config.optimization.stop invalid')
    if optimization.get('step', None) != 0.1:
        return dict(success=False, errmsg='optimizable_float_test.config.optimization.step invalid')
    return dict(success=True)

def PX_InitScriptSettings():
    return {"charts": {"price": {"series": [{"name": "top_signal", "color": "#89F3DAFF"},
                                            {"name": "bottom_signal", "color": "#e7dc48"}]}},
            "params": {
                       "init_int_test": {"value": 99, "config": {"type": "int", "required": True, "min": 0}},
                       "init_float_test": {"value": 1.0, "config": {"type": "float", "required": True, "min": 0.5}},
                       "init_optimizable_percent_test": {"value": "1.0%", "config": {"type": "percent", "required": False,
                                                                                       "optimizable": True,
                                                                                       "optimization": {"type": "percent",
                                                                                                        "start": "0.5%",
                                                                                                        "stop": "5.0%",
                                                                                                        "step": "0.5%"}}},
                       "init_value_test": 20,
                       "init_str_test": "-10%",
                       "init_select_test": {"value": 0, "config": {"type": "int", "options": {"0": "Breakout", "100": "Reverse"}}},
            }}

# def PX_OnCommand(command, params):
#     return True

assertEqual(GetParam("init_int_test", None), 99)
assertEqual(GetParam("init_float_test", None), 1.0)
assertEqual(GetParam("init_optimizable_percent_test", None), '1.0%')
assertEqual(GetParam("init_value_test", None), 20)
assertEqual(GetParam("init_str_test", None), '-10%')
assertEqual(GetParam("init_select_test", None), 0)
#
assertTrue(GetParam("bool_test", None))
#
param_test = GetParam("param_test", None)
assertFalse(param_test)
#
options_test = GetParam("options_test", None)
assertEqual(options_test, 100)
#
optimizable_float_test = GetParam("optimizable_float_test", None)
assertEqual(optimizable_float_test, 0.5)



#
set_test_result("OK")
#
StopTester()
