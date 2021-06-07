import json
from bson import json_util
from datetime import datetime, date
from dateutil.parser import parse
from pixiu.api.defines import OrderCommand
# ----------------------------------------------------------------------------------------------------------------------
#    UTILS
# ----------------------------------------------------------------------------------------------------------------------
def order_is_long(order_cmd):
    long_types = [OrderCommand.BUY, OrderCommand.BUYLIMIT, OrderCommand.BUYSTOP]
    return order_cmd.upper() in long_types

def order_is_short(order_cmd):
    long_types = [OrderCommand.SELL, OrderCommand.SELLLIMIT, OrderCommand.SELLSTOP]
    return order_cmd.upper() in long_types

def order_is_market(order_cmd) -> bool:
    market_types = [OrderCommand.BUY, OrderCommand.SELL]
    return order_cmd.upper() in market_types

def order_is_stop(order_cmd) -> bool:
    stop_types = [OrderCommand.BUYSTOP, OrderCommand.SELLSTOP]
    return order_cmd.upper() in stop_types

def order_is_limit(order_cmd) -> bool:
    limit_types = [OrderCommand.BUYLIMIT, OrderCommand.SELLLIMIT]
    return order_cmd.upper() in limit_types

def order_is_pending(order_cmd) -> bool:
    return order_is_limit(order_cmd) or order_is_stop(order_cmd)

def parse_timeframe(timeframe):
    '''Parse the timeframe'''
    unit = timeframe[0]
    idx = 1
    if unit == 'm':
        if len(timeframe) > 1 and timeframe[1] == 'n':
            unit = 'mn'
            idx = 2

    count = timeframe[idx:]
    if not count:
        count = 1
    return unit, int(count)


def calculate_minute_intervals(t_unit, t_count):
    '''Calculate minute intervals'''
    return int(calculate_second_intervals(t_unit, t_count) / 60)

def calculate_second_intervals(t_unit, t_count):
    '''Calculate second intervals'''
    seconds = None
    MINUTE_SEC = 60
    HOUR_SEC = 3600
    DAY_SEC = 86400
    WEEK_SEC = 604800
    if t_unit == 's':
        seconds = t_count
    elif t_unit == 'm':
        seconds = MINUTE_SEC * t_count
    elif t_unit == 'h':
        seconds = HOUR_SEC * t_count
    elif t_unit == 'd':
        seconds = DAY_SEC * t_count
    elif t_unit == 'w':
        seconds = WEEK_SEC * t_count
    else:
        pass
    return seconds

def timeframe_to_seconds(timeframe):
    '''Timeframe to seconds'''
    t_unit, t_count = parse_timeframe(timeframe)
    return calculate_second_intervals(t_unit, t_count)

def parse_datetime_string(time_str, ignoretz=True):
    ''''''
    if time_str is None:
        return None
    if(isinstance(time_str, datetime) or isinstance(time_str, date)):
        return time_str
    return parse(time_str, ignoretz=ignoretz)

def load_json(source, object_hook=json_util.object_hook):
    """"""
    ret = source
    if isinstance(source, bytes):
        source = source.decode('utf-8')
    if isinstance(source, str):
        ret = json.loads(source, object_hook=object_hook)
    return ret

def dump_json(value, default=json_util.default):
    """"""
    svalue = json.dumps(value, default=default)
    return svalue