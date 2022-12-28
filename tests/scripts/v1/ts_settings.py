AddChart(name="price", chart={"series": [{"name": "top_signal", "color": "#89F3DAFF"},
                                         {"name": "bottom_signal", "color": "#e7dc48"}]})
AddParam("bool_test", value=True, type="bool", required=True)
AddParam("param_test", param={"value": False, "config": {"type": "bool", "required": True}})
AddParam("options_test", value=100, type="int", options={"0": "Option-0", "100": "Option-100"})
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
    return dict(success=True)

def PX_InitScriptSettings():
    return {"charts": {"price": {"series": [{"name": "top_signal", "color": "#89F3DAFF"},
                                            {"name": "bottom_signal", "color": "#e7dc48"}]}},
            "params": {
                       "init_int_test": {"value": 99, "config": {"type": "int", "required": True, "min": 0}},
                       "init_float_test": {"value": 1.0, "config": {"type": "float", "required": True, "min": 0.5}},
                       "init_value_test": 20,
                       "init_str_test": "-10%",
                       "init_select_test": {"value": 0, "config": {"type": "int", "options": {"0": "Breakout", "100": "Reverse"}}},
            }}

# def PX_OnCommand(command, params):
#     return True

assertEqual(GetParam("init_int_test", None), 99)
assertEqual(GetParam("init_float_test", None), 1.0)
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
set_test_result("OK")
#
StopTester()