def PX_InitScriptSettings():
    return {}


def PX_ValidScriptSettings(script_settings=None):
    return dict(success=True, errmsg="")


scenario_time = Time()

if scenario_case == "initial_state":
    if scenario_time == valid_initial_time:
        account = GetAccount()
        assertEqual(account.balance, valid_initial_balance)
        assertEqual(account.equity, valid_initial_equity)
        assertEqual(account.free_margin, valid_initial_free_margin)

        opened = GetOpenedOrderUIDs()
        pending = GetPendingOrderUIDs()
        assertEqual(len(opened), 1)
        assertEqual(len(pending), 1)

        opened_order = GetOrder(opened[0])
        pending_order = GetOrder(pending[0])
        assertEqual(opened_order.ticket, str(valid_opened_ticket))
        assertEqual(opened_order.status, OrderStatus.OPENED)
        assertEqual(opened_order.volume, valid_opened_volume)
        assertEqual(opened_order.comment, valid_opened_comment)
        assertEqual(pending_order.ticket, str(valid_pending_ticket))
        assertEqual(pending_order.status, OrderStatus.PENDING)
        assertEqual(pending_order.cmd, OrderCommand.SELLSTOP)

        set_test_result("OK")
        StopTester()

elif scenario_case == "mutate_tick":
    if scenario_time == valid_event_time:
        assertAlmostEqual(Bid(), valid_event_bid)
        assertAlmostEqual(Ask(), valid_event_ask)
        assertAlmostEqual(Close(), valid_event_close)
        assertAlmostEqual(Low(), valid_event_low)
        assertAlmostEqual(High(), valid_event_high)
        set_test_result("OK")
        StopTester()

elif scenario_case == "price_path":
    if scenario_time == valid_event_time:
        assertAlmostEqual(Bid(), valid_event_bid)
        assertAlmostEqual(Ask(), valid_event_ask)
        assertAlmostEqual(Close(), valid_event_close)
        assertAlmostEqual(Low(), valid_event_low)
        assertAlmostEqual(High(), valid_event_high)
        set_test_result("OK")
        StopTester()

elif scenario_case == "place_order":
    if scenario_time == valid_place_time:
        opened = GetOpenedOrderUIDs()
        assertEqual(len(opened), 1)
        placed_order = GetOrder(str(valid_place_ticket))
        assertEqual(placed_order.ticket, str(valid_place_ticket))
        assertEqual(placed_order.status, OrderStatus.OPENED)
        assertEqual(placed_order.cmd, OrderCommand.SELL)
        assertEqual(placed_order.comment, valid_place_comment)
        assertEqual(placed_order.volume, valid_place_volume)
        set_test_result("OK")
        StopTester()

elif scenario_case == "cancel_order":
    if scenario_time == valid_cancel_time:
        pending = GetPendingOrderUIDs()
        assertEqual(len(pending), 0)
        cancelled_order = GetOrder(str(valid_cancel_ticket))
        assertEqual(cancelled_order.ticket, str(valid_cancel_ticket))
        assertEqual(cancelled_order.status, OrderStatus.CANCELLED)
        set_test_result("OK")
        StopTester()

elif scenario_case == "initial_state_open_time":
    if scenario_time == valid_initial_time:
        opened = GetOpenedOrderUIDs()
        assertEqual(len(opened), 1)
        opened_order = GetOrder(opened[0])
        assertEqual(opened_order.ticket, str(valid_opened_ticket))
        assertEqual(opened_order.open_time, valid_open_time)
        set_test_result("OK")
        StopTester()

elif scenario_case == "account_ea_runtime_data":
    if scenario_time == valid_initial_time:
        data = LoadData(valid_data_name, scope=DataScope.ACCOUNT_EA)
        assertEqual(data, valid_data)
        set_test_result("OK")
        StopTester()
