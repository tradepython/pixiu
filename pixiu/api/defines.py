# ----------------------------------------------------------------------------------------------------------------------
#    DEFINES
# ----------------------------------------------------------------------------------------------------------------------
class TimeFrame(object):
    S1 = "s1"
    M1 = "m1"
    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    H1 = "h1"
    H4 = "h4"
    D1 = "d1"
    W1 = "w1"
    MN1 = "mn1"

class OrderCommand(object):
    ''''''
    BUY = 'BUY'
    SELL = 'SELL'
    BUYLIMIT = 'BUYLIMIT'
    SELLLIMIT = 'SELLLIMIT'
    BUYSTOP = 'BUYSTOP'
    SELLSTOP = 'SELLSTOP'
    #mt5
    BUYSTOPLIMIT = 'BUYSTOPLIMIT'
    SELLSTOPLIMIT = 'SELLSTOPLIMIT'
    CLOSEBY = 'CLOSEBY'


class OrderType(object):
    MARKET = 0
    LIMIT = 100
    STOP = 200

#
class RunModeValue(object):
    TEST = 'TEST'
    LIVE = 'LIVE'

class PositionType(object):
    SHORT = 'SHORT'
    LONG = 'LONG'

class OrderStatus(object):
    OPENED = 0
    CLOSED = 100
    PENDING = 200
    DELETED = 300
    CANCELLED = 400