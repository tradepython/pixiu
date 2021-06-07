#
Buy(0.1, price=Ask())
uids = GetOpenedOrderUIDs()
for uid in uids:
    o = GetOrder(uid)
    if o.profit > 0.5:
        CloseOrder(o.uid)