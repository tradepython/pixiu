#
point = SymbolInfo("point")
volume = 0.01

assertEqual(AcquireLock("test"), True)
ReleaseLock("test")

score = 1.0
errid, result = Buy(volume=volume, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
errid, ret = WaitCommand(result['command_uid'])
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, 0)
assertEqual(order.take_profit, 0)
assertEqual(order.tags['score'], score)

if result['command_uid']:
    assertEqual(order.comment, f"cuid#{result['command_uid']}|")
else:
    assertEqual(order.comment, f"uid#{result['order_uid']}|")
# assertIsNone(order.magic_number)
assertIsNone(order.close_time)
assertIsNone(order.close_price)

#


score = score + 1
#Buy with sl and tp
stop_loss = Bid()-15*point
take_profit = Ask()+30*point
errid, result = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#Buy all params
stop_loss = Bid()-15*point
take_profit = Ask()+30*point
magic_number = 4291651
errid, result = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="white", tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertEqual(order.magic_number, magic_number)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#
stop_loss = stop_loss - 15 * point
take_profit = take_profit + 30 * point
errid, result = ModifyOrder(result['order_uid'], stop_loss=stop_loss, take_profit=take_profit, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#close order
# errid, result = CloseOrder(result['order_uid'], price=Ask(), volume=volume)
errid, result = CloseOrder(result['order_uid'], tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
order = GetOrder(result['order_uid'])
assertEqual(order.is_dirty, RunMode() == RunModeValue.LIVE)

errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertFalse(order.is_dirty)
assertEqual(order.symbol, Symbol())
assertIsNotNone(order.close_time)
assertEqual(order.close_price, Bid())
assertEqual(order.tags['score'], score)

#The order was closed ?
oo = GetOpenedOrderUIDs()
for t in oo:
    assertNotEqual(t, result['order_uid'])


# Sell
errid, result = Sell(volume=0.01, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, 0)
assertEqual(order.take_profit, 0)
assertIsNone(order.magic_number)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#Sell with sl and tp
stop_loss = Ask() + 15 * point
take_profit = Bid() - 30 * point
errid, result = Sell(volume=0.01, price=Bid(), stop_loss=Ask()+15*point,
                    take_profit=Bid()-30*point, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#Sell all params
magic_number=4291652
errid, result = Sell(volume=volume, price=Bid(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="red", tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertEqual(order.magic_number, magic_number)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#
stop_loss = stop_loss + 15 * point
take_profit = take_profit - 30 * point
errid, result = ModifyOrder(result['order_uid'], stop_loss=stop_loss, take_profit=take_profit, tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
order = GetOrder(result['order_uid'])
assertEqual(order.is_dirty, RunMode() == RunModeValue.LIVE)

errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertFalse(order.is_dirty)
assertEqual(order.symbol, Symbol())
assertEqual(order.uid, result['order_uid'])
assertEqual(order.volume, volume)
assertEqual(order.stop_loss, stop_loss)
assertEqual(order.take_profit, take_profit)
assertIsNone(order.close_time)
assertIsNone(order.close_price)
assertEqual(order.tags['score'], score)

#close order
# errid, result = CloseOrder(result['order_uid'], price=Bid(), volume=volume)
errid, result = CloseOrder(result['order_uid'], tags={'score': score})
assertEqual(errid, 0)
assertNotEqual(result['order_uid'], None)
order = GetOrder(result['order_uid'])
assertEqual(order.is_dirty, RunMode() == RunModeValue.LIVE)

errid = exec_command()
assertEqual(errid, 0)
order = GetOrder(result['order_uid'])
assertIsNotNone(order)
assertFalse(order.is_dirty)
assertEqual(order.symbol, Symbol())
assertIsNotNone(order.close_time)
assertEqual(order.close_price, Ask())
assertEqual(order.tags['score'], score)

#The order was closed ?
oo = GetOpenedOrderUIDs()
for t in oo:
    assertNotEqual(t, result['order_uid'])

#close multiple orders
orders = []
for i in range(5):
    errid, result = Buy(volume=0.01, price=Ask())
    assertEqual(errid, 0)
    assertNotEqual(result['order_uid'], None)
    orders.append(result['order_uid'])
    errid = exec_command()
    assertEqual(errid, 0)
for order_uid in orders:
    order = GetOrder(order_uid)
    assertIsNotNone(order)
    assertFalse(order.is_dirty)

errid, result = CloseMultiOrders(orders)
assertEqual(errid, 0)
for order_uid in orders:
    order = GetOrder(order_uid)
    assertIsNotNone(order)
    assertEqual(order.is_dirty, RunMode() == RunModeValue.LIVE)
errid = exec_command()
assertEqual(errid, 0)
for order_uid in orders:
    order = GetOrder(order_uid)
    assertIsNotNone(order)
    assertFalse(order.is_dirty)
    assertIsNotNone(order.close_time)

#
set_test_result("OK")
StopTester()