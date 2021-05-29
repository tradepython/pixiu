from datetime import datetime

class Account(object):
    '''Account class'''
    def __init__(self, params={}):
        self.__account_dict__ = params.copy()

    @property
    def balance(self) -> float:
        return float(self.__account_dict__["balance"])

    @property
    def equity(self) -> float:
        return float(self.__account_dict__["equity"])

    @property
    def margin(self) -> float:
        return float(self.__account_dict__["margin"])

    @property
    def free_margin(self) -> float:
        return float(self.__account_dict__["free_margin"])

    @property
    def credit(self) -> float:
        return float(self.__account_dict__["credit"])

    @property
    def profit(self) -> float:
        return float(self.__account_dict__["profit"])

    @property
    def margin_level(self) -> float:
        return float(self.__account_dict__["margin_level"])

    @property
    def leverage(self) -> int:
        return int(self.__account_dict__["leverage"])

    @property
    def currency(self) -> str:
        return str(self.__account_dict__["currency"])

    @property
    def free_margin_mode(self) -> float:
        return float(self.__account_dict__["free_margin_mode"])

    @property
    def stop_out_level(self) -> float:
        return float(self.__account_dict__["stop_out_level"])

    @property
    def stop_out_mode(self) -> float:
        return float(self.__account_dict__["stop_out_mode"])

    @property
    def company(self) -> str:
        return str(self.__account_dict__["company"])

    @property
    def name(self) -> str:
        return str(self.__account_dict__["name"])

    @property
    def number(self) -> str:
        return str(self.__account_dict__["number"])

    @property
    def server(self) -> str:
        return str(self.__account_dict__["server"])

    @property
    def trade_mode(self) -> int:
        return int(self.__account_dict__["trade_mode"])

    @property
    def limit_orders(self) -> int:
        return int(self.__account_dict__["limit_orders"])

    @property
    def margin_so_mode(self) -> int:
        return int(self.__account_dict__["margin_so_mode"])

    @property
    def trade_allowed(self) -> int:
        return int(self.__account_dict__["trade_allowed"])

    @property
    def trade_expert(self) -> int:
        return int(self.__account_dict__["trade_expert"])

    @property
    def margin_so_call(self) -> float:
        return float(self.__account_dict__["margin_so_call"])

    @property
    def margin_so_so(self) -> float:
        return float(self.__account_dict__["margin_so_so"])

    @property
    def commission(self) -> float:
        return float(self.__account_dict__.get("commission", 0.0))


class AccountDataNumber(object):
    def __init__(self, account_data, data, timeframe, getitem_callback):
        self.__timeframe__ = timeframe
        self.__data__ = data
        self.__account_data__ = account_data
        self.__getitem_callback__ = getitem_callback

    def __getitem__(self, key):
        return self.__getitem_callback__(self.__data__, self.__timeframe__,
                                         key)

class AccountDataString(object):
    def __init__(self, account_data, data, timeframe, getitem_callback):
        self.__timeframe__ = timeframe
        self.__data__ = data
        self.__account_data__ = account_data
        self.__getitem_callback__ = getitem_callback

    def __getitem__(self, key):
        return self.__getitem_callback__(self.__data__, self.__timeframe__,
                                         key)


class AccountDataTime(object):
    def __init__(self, account_data, data, timeframe, getitem_callback):
        self.__timeframe__ = timeframe
        self.__time__ = data
        self.__account_data__ = account_data
        self.__getitem_callback__ = getitem_callback

    def __getitem__(self, key):
        ts = self.__getitem_callback__(self.__time__, self.__timeframe__,
                                       key)
        if ts is None:
            return None
        return datetime.fromtimestamp(ts)

class AccountData(object):
    def __init__(self, data, timeframe, getitem_callback):
        self.__timeframe__ = timeframe
        self.__data__ = data
        self.__size__ = data.size
        self.__time__ = AccountDataTime(self, data['t'], timeframe, getitem_callback=getitem_callback)
        #
        self.__credit__ = AccountDataNumber(self, data['credit'], timeframe, getitem_callback=getitem_callback)
        self.__balance__ = AccountDataNumber(self, data['balance'], timeframe, getitem_callback=getitem_callback)
        self.__max_balance__ = AccountDataNumber(self, data['max_balance'], timeframe, getitem_callback=getitem_callback)
        self.__min_balance__ = AccountDataNumber(self, data['min_balance'], timeframe, getitem_callback=getitem_callback)
        self.__equity__ = AccountDataNumber(self, data['equity'], timeframe, getitem_callback=getitem_callback)
        self.__max_equity__ = AccountDataNumber(self, data['max_equity'], timeframe, getitem_callback=getitem_callback)
        self.__min_equity__ = AccountDataNumber(self, data['min_equity'], timeframe, getitem_callback=getitem_callback)
        self.__margin__ = AccountDataNumber(self, data['margin'], timeframe, getitem_callback=getitem_callback)
        self.__max_margin__ = AccountDataNumber(self, data['max_margin'], timeframe, getitem_callback=getitem_callback)
        self.__min_margin__ = AccountDataNumber(self, data['min_margin'], timeframe, getitem_callback=getitem_callback)
        self.__margin_level__ = AccountDataNumber(self, data['margin_level'], timeframe, getitem_callback=getitem_callback)
        self.__profit__ = AccountDataNumber(self, data['profit'], timeframe, getitem_callback=getitem_callback)
        self.__max_profit__ = AccountDataNumber(self, data['max_profit'], timeframe, getitem_callback=getitem_callback)
        self.__min_profit__ = AccountDataNumber(self, data['min_profit'], timeframe, getitem_callback=getitem_callback)
        self.__free_margin__ = AccountDataNumber(self, data['free_margin'], timeframe, getitem_callback=getitem_callback)
        self.__commission__ = AccountDataNumber(self, data['commission'], timeframe, getitem_callback=getitem_callback)
        #static
        self.__currency__ = AccountDataString(self, data['currency'], timeframe, getitem_callback=getitem_callback)
        self.__free_margin_mode__ = AccountDataNumber(self, data['free_margin_mode'], timeframe, getitem_callback=getitem_callback)
        self.__leverage__ = AccountDataNumber(self, data['leverage'], timeframe, getitem_callback=getitem_callback)
        self.__stop_out_level__ = AccountDataNumber(self, data['stop_out_level'], timeframe, getitem_callback=getitem_callback)
        self.__stop_out_mode__ = AccountDataNumber(self, data['stop_out_mode'], timeframe, getitem_callback=getitem_callback)
        self.__company__ = AccountDataString(self, data['company'], timeframe, getitem_callback=getitem_callback)
        self.__name__ = AccountDataString(self, data['name'], timeframe, getitem_callback=getitem_callback)
        self.__number__ = AccountDataString(self, data['number'], timeframe, getitem_callback=getitem_callback)
        self.__server__ = AccountDataString(self, data['server'], timeframe, getitem_callback=getitem_callback)
        self.__trade_mode__ = AccountDataNumber(self, data['trade_mode'], timeframe, getitem_callback=getitem_callback)
        self.__limit_orders__ = AccountDataNumber(self, data['limit_orders'], timeframe, getitem_callback=getitem_callback)
        self.__margin_so_mode__ = AccountDataNumber(self, data['margin_so_mode'], timeframe, getitem_callback=getitem_callback)
        self.__trade_allowed__ = AccountDataNumber(self, data['trade_allowed'], timeframe, getitem_callback=getitem_callback)
        self.__trade_expert__ = AccountDataNumber(self, data['trade_expert'], timeframe, getitem_callback=getitem_callback)
        self.__margin_so_call__ = AccountDataNumber(self, data['margin_so_call'], timeframe, getitem_callback=getitem_callback)
        self.__margin_so_so__ = AccountDataNumber(self, data['margin_so_so'], timeframe, getitem_callback=getitem_callback)
        self.__getitem_callback__ = getitem_callback

    def __getitem__(self, key):
        return self.__getitem_callback__(self.__data__, self.__timeframe__, key)

    @property
    def size(self):
        return self.__size__

    @property
    def commission(self):
        return self.__commission__

    @property
    def credit(self):
        return self.__credit__

    @property
    def balance(self):
        return self.__balance__

    @property
    def max_balance(self):
        return self.__max_balance__

    @property
    def min_balance(self):
        return self.__min_balance__

    @property
    def equity(self):
        return self.__equity__

    @property
    def max_equity(self):
        return self.__max_equity__

    @property
    def min_equity(self):
        return self.__min_equity__

    @property
    def margin(self):
        return self.__margin__

    @property
    def max_margin(self):
        return self.__max_margin__

    @property
    def min_margin(self):
        return self.__min_margin__

    @property
    def margin_level(self):
        return self.__margin_level__

    @property
    def profit(self):
        return self.__profit__

    @property
    def max_profit(self):
        return self.__max_profit__

    @property
    def min_profit(self):
        return self.__min_profit__

    @property
    def free_margin(self):
        return self.__free_margin__

    @property
    def currency(self):
        return self.__currency__

    @property
    def free_margin_mode(self):
        return self.__free_margin_mode__

    @property
    def leverage(self):
        return self.__leverage__

    @property
    def stop_out_level(self):
        return self.__stop_out_level__

    @property
    def stop_out_mode(self):
        return self.__stop_out_mode__

    @property
    def company(self):
        return self.__company__

    @property
    def name(self):
        return self.__name__

    @property
    def number(self):
        return self.__number__

    @property
    def server(self):
        return self.__server__

    @property
    def trade_mode(self):
        return self.__trade_mode__

    @property
    def limit_orders(self):
        return self.__limit_orders__

    @property
    def margin_so_mode(self):
        return self.__margin_so_mode__

    @property
    def trade_allowed(self):
        return self.__trade_allowed__

    @property
    def trade_expert(self):
        return self.__trade_expert__

    @property
    def margin_so_call(self):
        return self.__margin_so_call__

    @property
    def margin_so_so(self):
        return self.__margin_so_so__