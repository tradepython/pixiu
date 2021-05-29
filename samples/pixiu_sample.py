#
print(f"time={Time()}")
point = SymbolInfo("point")
volume = 0.01
errid, order_uid = Buy(volume=volume)
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)


#Buy with sl and tp
stop_loss=Bid()-15*point
take_profit=Ask()+30*point
errid, order_uid = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit)
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Buy all params
stop_loss=Bid()-15*point
take_profit=Ask()+30*point
magic_number=4291651
errid, order_uid = Buy(volume=0.01, price=Ask(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="white")
print(f"Buy: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#
stop_loss = stop_loss - 15 * point
take_profit = take_profit + 30 * point
errid, order_uid = ModifyOrder(order_uid, stop_loss=stop_loss, take_profit=take_profit)
print(f"ModifyOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#close order
errid, order_uid = CloseOrder(order_uid, price=Ask(), volume=volume)
print(f"CloseOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)



# Sell
errid, order_uid = Sell(volume=0.01)
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Sell with sl and tp
stop_loss = Ask() + 15 * point
take_profit = Bid() - 30 * point
errid, order_uid = Sell(volume=0.01, price=Bid(), stop_loss=Ask()+15*point,
                    take_profit=Bid()-30*point)
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

#Sell all params
magic_number=4291652
errid, order_uid = Sell(volume=volume, price=Bid(), stop_loss=stop_loss,
                    take_profit=take_profit, magic_number=magic_number,
                    symbol=Symbol(), slippage=3, arrow_color="red")
print(f"Sell: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)
#
stop_loss = stop_loss + 15 * point
take_profit = take_profit - 30 * point
errid, order_uid = ModifyOrder(order_uid, stop_loss=stop_loss, take_profit=take_profit)
print(f"ModifyOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)
#close order
errid, order_uid = CloseOrder(order_uid, price=Bid(), volume=volume)
print(f"CloseOrder: errid={errid}, order_uid={order_uid}")
order = GetOrder(order_uid)

StopTester()