#
print(f"time={Time()}")
point = SymbolInfo("point")
volume = 0.01
errid, result = Buy(volume=volume)
order_uid = result['order_uid']
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)


#Buy with sl and tp
stop_loss=Bid()-15*point
take_profit=Ask()+30*point
errid, result = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit)
order_uid = result['order_uid']
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Buy all params
stop_loss=Bid()-15*point
take_profit=Ask()+30*point
magic_number=4291651
errid, result = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="white")
order_uid = result['order_uid']
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#
stop_loss = stop_loss - 15 * point
take_profit = take_profit + 30 * point
errid, result = ModifyOrder(order_uid, stop_loss=stop_loss, take_profit=take_profit)
order_uid = result['order_uid']
print(f"ModifyOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#close order
errid, result = CloseOrder(order_uid)
order_uid = result['order_uid']
print(f"CloseOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)



# Sell
errid, result = Sell(volume=0.01)
order_uid = result['order_uid']
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Sell with sl and tp
stop_loss = Ask() + 15 * point
take_profit = Bid() - 30 * point
errid, result = Sell(volume=0.01, price=Bid(), stop_loss=Ask()+15*point,
                    take_profit=Bid()-30*point)
order_uid = result['order_uid']
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Sell all params
magic_number=4291652
errid, result = Sell(volume=volume, price=Bid(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="red")
order_uid = result['order_uid']
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)
#
stop_loss = stop_loss + 15 * point
take_profit = take_profit - 30 * point
errid, result = ModifyOrder(order_uid, stop_loss=stop_loss, take_profit=take_profit)
order_uid = result['order_uid']
print(f"ModifyOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)
#close order
errid, result = CloseOrder(order_uid)
order_uid = result['order_uid']
print(f"CloseOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

StopTester()