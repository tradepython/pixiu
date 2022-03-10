ood = GetOpenedOrderUIDs()
if len(ood) == 0:
    pod = GetPendingOrderUIDs()
    assertIsNotNone(pod)
    if len(pod) == 0:
        #
        point = SymbolInfo("point")
        volume = 0.01

        # Buy all params
        stop_loss = Bid() - 15 * point
        take_profit = Ask() + 30 * point
        comment = "test buystop"
        magic_number = 4301250
        # failed
        price = Ask()
        errid, result = Buy(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)

        # failed
        price = Ask() - 10 * point
        errid, result = Buy(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)

        #test open, modify, close
        price = valid_buystop_price
        errid, result = Buy(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, 0)
        assertIsNotNone(result['order_uid'])
        errid = exec_command()
        assertEqual(errid, 0)
        oo = GetPendingOrderUIDs()
        assertTrue(result['order_uid'] in oo)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.PENDING)

        # modify
        stop_loss = stop_loss - 15 * point
        take_profit = take_profit + 30 * point
        errid, result = ModifyOrder(result['order_uid'], price=Ask()-1*point, stop_loss=stop_loss, take_profit=take_profit)
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)
        errid, result = ModifyOrder(result['order_uid'], price=Ask()+1*point, stop_loss=stop_loss, take_profit=take_profit)
        assertEqual(errid, 0)
        assertIsNotNone(result['order_uid'])
        errid = exec_command()
        assertEqual(errid, 0)

        #
        order = GetOrder(result['order_uid'])
        assertEqual(order.symbol, Symbol())
        assertEqual(order.uid, result['order_uid'])
        assertEqual(order.volume, volume)
        assertEqual(order.stop_loss, stop_loss)
        assertEqual(order.take_profit, take_profit)
        assertIsNone(order.close_time)
        assertIsNone(order.close_price)
        assertEqual(order.status, OrderStatus.PENDING)

        #close
        errid, ct = CloseOrder(result['order_uid'], volume=volume, price=Bid())
        assertEqual(errid, 0)
        assertEqual(ct['order_uid'], result['order_uid'])
        errid = exec_command()
        assertEqual(errid, 0)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.CANCELLED)

        # The order was closed ?
        oo = GetPendingOrderUIDs()
        assertFalse(result['order_uid'] in oo)

        #
        price = valid_buystop_price
        errid, result = Buy(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, 0)
        assertIsNotNone(result['order_uid'])
        errid = exec_command()
        assertEqual(errid, 0)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.PENDING)

else:
    pass
ctime = Time()
if ctime == valid_buystop_time:
    pod = GetPendingOrderUIDs()
    assertEqual(len(pod), 0)
    assertEqual(len(ood), 1)
    # order = GetOrder(result['order_uid'])
    # assertEqual(order.symbol, Symbol())
    # assertEqual(order.uid, result['order_uid'])
    # assertEqual(order.open_time, ctime)
    # assertEqual(order.volume, volume)
    # assertEqual(order.stop_loss, stop_loss)
    # assertEqual(order.take_profit, take_profit)
    # assertEqual(order.magic_number, magic_number)
    # assertIsNone(order.close_time)
    # assertEqual(order.close_price, nan)
    set_test_result("OK")
    StopTester()

