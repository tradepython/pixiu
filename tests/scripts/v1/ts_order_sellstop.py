POINT = SymbolInfo("point")
DIGITS = int(SymbolInfo("digits"))

ood = GetOpenedOrderUIDs()
if len(ood) == 0:
    pod = GetPendingOrderUIDs()
    assertIsNotNone(pod)
    if len(pod) == 0:
        #
        volume = 0.01

        # Buy all params
        stop_loss = round(Ask() + 15 * POINT, DIGITS)
        take_profit = round(Bid() - 30 * POINT, DIGITS)
        comment = "test sellstop"
        magic_number = 4301250
        # failed
        price = Bid()
        errid, result = Sell(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)

        # failed
        price = round(Bid() + 10 * POINT, DIGITS)
        errid, result = Sell(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)

        #test open, modify, close
        price = valid_sellstop_price
        errid, result = Sell(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, 0)
        assertIsNotNone(result)
        errid = exec_command()
        assertEqual(errid, 0)
        oo = GetPendingOrderUIDs()
        assertTrue(result['order_uid'] in oo)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.PENDING)

        # modify
        stop_loss = round(stop_loss + 15 * POINT, DIGITS)
        take_profit = round(take_profit - 30 * POINT, DIGITS)
        errid, result = ModifyOrder(result['order_uid'], price=Bid()+1*POINT, stop_loss=stop_loss, take_profit=take_profit)
        assertEqual(errid, EID_EAT_INVALID_STOP_ORDER_OPEN_PRICE)
        errid, result = ModifyOrder(result['order_uid'], price=Bid()-1*POINT, stop_loss=stop_loss, take_profit=take_profit)
        assertEqual(errid, 0)
        assertIsNotNone(result)
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
        errid, close_result = CloseOrder(result['order_uid'], volume=volume, price=Ask())
        assertEqual(errid, 0)
        assertEqual(close_result['order_uid'], result['order_uid'])
        errid = exec_command()
        assertEqual(errid, 0)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.CANCELLED)

        # The order was closed ?
        oo = GetPendingOrderUIDs()
        assertFalse(result['order_uid'] in oo)

        #
        price = valid_sellstop_price
        errid, result = Sell(volume=0.01, type=OrderType.STOP, price=price, stop_loss=stop_loss,
                            take_profit=take_profit, magic_number=magic_number,
                            symbol=Symbol(), slippage=3, arrow_color="white")
        assertEqual(errid, 0)
        assertIsNotNone(result)
        errid = exec_command()
        assertEqual(errid, 0)
        order = GetOrder(result['order_uid'])
        assertEqual(order.status, OrderStatus.PENDING)

else:
    pass
ctime = Time()
if ctime == valid_sellstop_time:
    pod = GetPendingOrderUIDs()
    assertEqual(len(pod), 0)
    assertEqual(len(ood), 1)
    # order = GetOrder(order_uid)
    # assertEqual(order.symbol, Symbol())
    # assertEqual(order.order_uid, order_uid)
    # assertEqual(order.open_time, ctime)
    # assertEqual(order.volume, volume)
    # assertEqual(order.stop_loss, stop_loss)
    # assertEqual(order.take_profit, take_profit)
    # assertEqual(order.comment, "open")
    # assertEqual(order.magic_number, magic_number)
    # assertIsNone(order.close_time)
    # assertEqual(order.close_price, nan)
    set_test_result("OK")
    StopTester()


