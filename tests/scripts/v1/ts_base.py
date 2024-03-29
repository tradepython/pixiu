# SetMetadata("copyright", "2022")

# settings = {"charts":{"price":{"series":[{"name":"top_signal","color":"#89F3DAFF"},{"name":"bottom_signal","color":"#e7dc48"}]}},
#             "params":{"debug": {"value": true, "config": {"type": "bool", "required": true}},
#                       "notify": {"value": false, "config": {"type": "bool", "required": true}},
#                       "brake_hedging_orders": {"value": 99, "config": {"type": "int", "required": true, "min": 0}},
#                       "return_ratio": {"value": 1.0, "config": {"type": "float", "required": true, "min": 0.5}},
#                       "group_max_loss_orders": 15, "group_max_loss": 0, "group_max_order_size": 5.0, "group_size_calc_mode": {"value": 100, "config": {"type": "int", "options": {"0": "Group Loss Orders", "100": "Group Profit"}}}, "group_main_order_direction": {"value": 0, "config": {"type": "int", "options": {"0": "Breakout", "100": "Reverse"}}}, "brake_hedging_volume": 99, "brake_hedging_time": 0, "brake_hedging_margin_level": 10, "brake_amount": 20, "brake_cold_down_minute": 240, "clean_group_id": 0, "cmd_exec": "", "group_target_profit": 0, "profit_protection": "40:30:pips", "risk_open_pause": "", "risk_recal_offset_pips": 25, "open_direction": {"value": 0, "config": {"type": "int", "options": {"0": "LONG & SHORT", "1": "LONG ONLY", "2": "SHORT ONLY", "3": "DISABLE"}}}, "trading_style": {"value": 1.3, "config": {"type": "float", "options": {"1.3": "Greedy (1.3)", "1.25": "Robust (1.25)", "1.2": "Conservative (1.2)", "1.1": "!!Loss (1.1)"}}}}}

#AddSettings("charts", "price", {"series":[{"name":"top_signal","color":"#89F3DAFF"},{"name":"bottom_signal","color":"#e7dc48"}]})
AddChart(name="price", chart={"series":[{"name":"top_signal","color":"#89F3DAFF"},{"name":"bottom_signal","color":"#e7dc48"}]})
# AddSettings("debug", {"value": True, "config": {"type": "bool", "required": True}})
AddParam("debug", value=True, type="bool", required=True)
AddParam("notify", param={"value": False, "config": {"type": "bool", "required": True}})
#
def PX_ValidScriptSettings():
    success = True
    if success:
        cmd_exec = GetParam("cmd_exec", None)
        if cmd_exec is None:
            success = False
            errmsg = ''
    if success:
        pass
    return dict(success=success, errmsg=errmsg)

def PX_InitScriptSettings():
    return {"charts":{"price":{"series":[{"name":"top_signal","color":"#89F3DAFF"},{"name":"bottom_signal","color":"#e7dc48"}]}},
            "params":{"debug": {"value": True, "config": {"type": "bool", "required": True}}, "notify": {"value": False, "config": {"type": "bool", "required": True}},  "brake_hedging_orders": {"value": 99, "config": {"type": "int", "required": True, "min": 0}},  "return_ratio": {"value": 1.0, "config": {"type": "float", "required": True, "min": 0.5}}, "group_max_loss_orders": 20, "group_max_loss": "-10%", "group_max_order_size": 5.0, "group_size_calc_mode": {"value": 100, "config": {"type": "int", "options": {"0": "Group Loss Orders", "100": "Group Profit"}}}, "group_main_order_direction": {"value": 0, "config": {"type": "int", "options": {"0": "Breakout", "100": "Reverse"}}}, "brake_hedging_volume": 99, "brake_hedging_time": 0, "brake_hedging_margin_level": 10, "brake_amount": 20, "brake_cold_down_minute": 240, "clean_group_id": 0, "cmd_exec": "", "group_target_profit": 0, "profit_protection": "40:30:pips", "risk_open_pause": "", "risk_recal_offset_pips": 25, "open_direction": {"value": 0, "config": {"type": "int", "options": {"0": "LONG & SHORT", "1": "LONG ONLY", "2": "SHORT ONLY", "3": "DISABLE"}}}, "trading_style": {"value": 1.3, "config": {"type": "float", "options": {"1.3": "Greedy (1.3)", "1.25": "Robust (1.25)", "1.2": "Conservative (1.2)", "1.1": "!!Loss (1.1)"}}}}}

# def PX_OnCommand(command, params):
#     return True

def test_timezone():
    tz = timezone('EST')
    d = Time().astimezone(tz)
    assertIsNotNone(d)


assertTrue(RunMode() in (RunModeValue.TEST, RunModeValue.LIVE))

print("ts_base: ", "test print", "1", "2", "3", "4", "5")
assertEqual(TimeFrame.S1, "s1")
assertEqual(TimeFrame.M1, "m1")
assertEqual(TimeFrame.M5, "m5")
assertEqual(TimeFrame.M15, "m15")
assertEqual(TimeFrame.M30, "m30")
assertEqual(TimeFrame.H1, "h1")
assertEqual(TimeFrame.H4, "h4")
assertEqual(TimeFrame.D1, "d1")
assertEqual(TimeFrame.W1, "w1")
assertEqual(TimeFrame.MN1, "mn1")

#OrderType
assertEqual(OrderType.MARKET, 0)
assertEqual(OrderType.LIMIT, 100)
assertEqual(OrderType.STOP, 200)

#OrderCommand
assertEqual(OrderCommand.BUY, 'BUY')
assertEqual(OrderCommand.SELL, 'SELL')
assertEqual(OrderCommand.BUYLIMIT, 'BUYLIMIT')
assertEqual(OrderCommand.SELLLIMIT, 'SELLLIMIT')
assertEqual(OrderCommand.BUYSTOP, 'BUYSTOP')
assertEqual(OrderCommand.SELLSTOP, 'SELLSTOP')
assertEqual(OrderCommand.BUYSTOPLIMIT, 'BUYSTOPLIMIT')
assertEqual(OrderCommand.SELLSTOPLIMIT, 'SELLSTOPLIMIT')
assertEqual(OrderCommand.CLOSEBY, 'CLOSEBY')

#symbol
assertEqual(Symbol(), valid_symbol)

c_time = Time(valid_shift)

#Test basic values (Cache)
assertEqual(c_time, get_value_by_time(valid_values, c_time, "time"))
assertEqual(Open(valid_shift), get_value_by_time(valid_values, c_time, "open"))
assertEqual(Close(valid_shift), get_value_by_time(valid_values, c_time, "close"))
assertEqual(High(valid_shift), get_value_by_time(valid_values, c_time, "high"))
assertEqual(Low(valid_shift), get_value_by_time(valid_values, c_time, "low"))
assertEqual(Ask(valid_shift), get_value_by_time(valid_values, c_time, "ask"), f'@ {c_time}')
assertEqual(Bid(valid_shift), get_value_by_time(valid_values, c_time, "bid"))
assertEqual(Volume(valid_shift), get_value_by_time(valid_values, c_time, "volume"))

#Account
account = GetAccount()
assertEqual(account.balance, valid_account['balance'])
assertEqual(account.equity, valid_account['equity'])
assertEqual(account.margin, valid_account['margin'])
assertEqual(account.free_margin, valid_account['free_margin'])
assertEqual(account.credit, valid_account['credit'])
assertEqual(account.profit, valid_account['profit'])
assertEqual(account.margin_level, valid_account['margin_level'])
assertEqual(account.leverage, valid_account['leverage'])
assertEqual(account.currency, valid_account['currency'])
assertEqual(account.free_margin_mode, valid_account['free_margin_mode'])
assertEqual(account.stop_out_level, valid_account['stop_out_level'])
assertEqual(account.stop_out_mode, valid_account['stop_out_mode'])
assertEqual(account.company, valid_account['company'])
assertEqual(account.name, valid_account['name'])
assertEqual(account.number, valid_account['number'])
assertEqual(account.server, valid_account['server'])
assertEqual(account.trade_mode, valid_account['trade_mode'])
assertEqual(account.limit_orders, valid_account['limit_orders'])
assertEqual(account.margin_so_mode, valid_account['margin_so_mode'])
assertEqual(account.trade_allowed, valid_account['trade_allowed'])
assertEqual(account.trade_expert, valid_account['trade_expert'])
assertEqual(account.margin_so_call, valid_account['margin_so_call'])
assertEqual(account.margin_so_so, valid_account['margin_so_so'])
assertEqual(account.commission, valid_account['commission'])

#Symbol
symbol = GetSymbol(Symbol())
assertEqual(symbol.name, valid_symbols[Symbol()]['symbol'])
assertEqual(symbol.spread, valid_symbols[Symbol()]['spread'])
assertEqual(symbol.digits, valid_symbols[Symbol()]['digits'])
assertEqual(symbol.stop_level, valid_symbols[Symbol()]['stop_level'])
assertEqual(symbol.volume_min, valid_symbols[Symbol()]['volume_min'])
assertEqual(symbol.trade_contract_size, valid_symbols[Symbol()]['trade_contract_size'])
assertEqual(symbol.point, valid_symbols[Symbol()]['point'])
assertEqual(symbol.currency_profit, valid_symbols[Symbol()]['currency_profit'])
assertEqual(symbol.currency_base, valid_symbols[Symbol()]['currency_base'])
assertEqual(symbol.currency_margin, valid_symbols[Symbol()]['currency_margin'])


#Data
for scope in (DataScope.EA, DataScope.EA_VERSION, DataScope.ACCOUNT, DataScope.EA_SETTIGNS):
    name = hashlib.md5(str(uuid.uuid4()).encode("utf-8")).hexdigest()
    for i in range(3):
        data = dict(value=UID())
        SaveData(scope=scope, name=name, data=data)
        d = LoadData(scope=scope, name=name)
        assertEqual(d['value'], data['value'], f"scope={scope}, i={i}")
    DeleteData(scope=scope, name=name)
    d = LoadData(scope=scope, name=name)
    assertIsNone(d, f"scope={scope}")

# Test functions
test_timezone()

#
set_test_result("OK")
#
StopTester()