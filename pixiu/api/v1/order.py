from datetime import datetime

import numpy as np
from pixiu.api.defines import (OrderCommand)
from pixiu.api.utils import (parse_datetime_string)



class Order(object):

    def __init__(self, params={'volume': 0}):
        self.order_dict = params.copy()
        open_time = self.order_dict.get("open_time", None)
        if open_time is not None:
            if isinstance(open_time, int) or isinstance(open_time, float):
                self.order_dict["open_time"] = datetime.fromtimestamp(open_time)
            else:
                self.order_dict["open_time"] = parse_datetime_string(open_time)
        close_time = self.order_dict.get("close_time", None)
        if close_time is not None:
            if isinstance(close_time, int) or isinstance(close_time, float):
                self.order_dict["close_time"] = datetime.fromtimestamp(close_time)
            else:
                self.order_dict["close_time"] = parse_datetime_string(close_time)
        self.order_dict["commission"] = self.order_dict.get("commission", 0.0)
        self.order_dict["swap"] = self.order_dict.get("swap", 0.0)
        #cmd upper
        cmd = self.order_dict.get("cmd", None)
        if cmd is not None:
            self.order_dict["cmd"] = cmd.upper()

    def clone(self):
        return Order(self.order_dict.copy())

    def is_long(self) -> bool:
        long_types = [OrderCommand.BUY, OrderCommand.BUYLIMIT, OrderCommand.BUYSTOP]
        # cmd = self.cmd.upper()
        return self.cmd in long_types

    def is_short(self) -> bool:
        long_types = [OrderCommand.SELL, OrderCommand.SELLLIMIT, OrderCommand.SELLSTOP]
        # cmd = self.cmd.upper()
        return self.cmd in long_types

    def is_market(self) -> bool:
        market_types = [OrderCommand.BUY, OrderCommand.SELL]
        # cmd = self.cmd.upper()
        return self.cmd in market_types

    def is_stop(self) -> bool:
        stop_types = [OrderCommand.BUYSTOP, OrderCommand.SELLSTOP]
        # cmd = self.cmd.upper()
        return self.cmd in stop_types

    def is_limit(self) -> bool:
        limit_types = [OrderCommand.BUYLIMIT, OrderCommand.SELLLIMIT]
        # cmd = self.cmd.upper()
        return self.cmd in limit_types

    def is_pending(self) -> bool:
        return self.is_limit() or self.is_stop()

    @property
    def uid(self) -> str:
        return str(self.order_dict["uid"])

    @property
    def ticket(self) -> str:
        return str(self.order_dict.get("order_id", self.order_dict.get("ticket", None)))

    @property
    def profit(self) -> float:
        return float(self.order_dict.get("profit", 0))

    @property
    def margin(self) -> float:
        return float(self.order_dict.get("margin", None))

    @property
    def take_profit(self) -> float:
        value = self.order_dict.get("take_profit", None)
        if value is None:
            return None
        return float(value)

    @property
    def stop_loss(self) -> float:
        value = self.order_dict.get("stop_loss", None)
        if value is None:
            return None
        return float(value)

    @property
    def comment(self):
        return self.order_dict["comment"]

    @property
    def symbol(self):
        return str(self.order_dict["symbol"])

    @property
    def cmd(self):
        return str(self.order_dict["cmd"])

    @property
    def volume(self) -> float:
        return float(self.order_dict["volume"])

    @property
    def commission(self) -> float:
        return float(self.order_dict["commission"])

    @property
    def swap(self) -> float:
        return float(self.order_dict["swap"])

    @property
    def magic_number(self) -> float:
        ret = self.order_dict.get("magic_number", None)
        return int(ret) if ret is not None else None

    @property
    def open_price(self) -> float:
        return float(self.order_dict["open_price"])

    @property
    def open_time(self):
        return self.order_dict["open_time"]

    @property
    def close_time(self):
        return self.order_dict["close_time"]

    @property
    def close_price(self):
        return self.order_dict["close_price"] if self.order_dict["close_price"] is not None and not np.isnan(self.order_dict["close_price"]) else None

    @property
    def description(self):
        return self.order_dict["description"]


