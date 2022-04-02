#
POINT = SymbolInfo("point")
DIGITS = int(SymbolInfo("digits"))
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
assertEqual(order.status, OrderStatus.OPENED)

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
stop_loss = round(Bid() - 15 * POINT, DIGITS)
take_profit = round(Ask() + 30 * POINT, DIGITS)
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
assertEqual(order.status, OrderStatus.OPENED)

#Buy all params
stop_loss = round(Bid() - 15 * POINT, DIGITS)
take_profit = round(Ask() + 30 * POINT, DIGITS)
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
assertEqual(order.status, OrderStatus.OPENED)

#
stop_loss = round(stop_loss - 15 * POINT, DIGITS)
take_profit = round(take_profit + 30 * POINT, DIGITS)
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
assertEqual(order.status, OrderStatus.OPENED)

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
assertEqual(order.status, OrderStatus.CLOSED)

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
assertEqual(order.status, OrderStatus.OPENED)

#Sell with sl and tp
stop_loss = round(Ask() + 15 * POINT, DIGITS)
take_profit = round(Bid() - 30 * POINT, DIGITS)
errid, result = Sell(volume=0.01, price=Bid(), stop_loss=Ask()+15*POINT,
                    take_profit=Bid()-30*POINT, tags={'score': score})
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
assertEqual(order.status, OrderStatus.OPENED)

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
assertEqual(order.status, OrderStatus.OPENED)

#
stop_loss = round(stop_loss + 15 * POINT, DIGITS)
take_profit = round(take_profit - 30 * POINT, DIGITS)
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
assertEqual(order.status, OrderStatus.OPENED)

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
assertEqual(order.status, OrderStatus.CLOSED)

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
    assertEqual(order.status, OrderStatus.OPENED)

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
    assertEqual(order.status, OrderStatus.CLOSED)

#
set_test_result("OK")
StopTester()