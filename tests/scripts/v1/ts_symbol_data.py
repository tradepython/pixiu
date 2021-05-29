c_time = Time(valid_shift)

#default timeframe
timeframe = DefaultTimeFrame()
symbol_data = GetSymbolData(Symbol(), timeframe, 50)

#Test basic values
assertEqual(c_time, get_value_by_time(valid_values, c_time, "time"))
assertEqual(symbol_data.time[valid_shift], get_value_by_time(valid_values, c_time, "time"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.open[valid_shift], get_value_by_time(valid_values, c_time, "open"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.close[valid_shift], get_value_by_time(valid_values, c_time, "close"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.high[valid_shift], get_value_by_time(valid_values, c_time, "high"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.low[valid_shift], get_value_by_time(valid_values, c_time, "low"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.ask[valid_shift], get_value_by_time(valid_values, c_time, "ask"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.bid[valid_shift], get_value_by_time(valid_values, c_time, "bid"),
                f'@ {c_time}, {timeframe}')
assertEqual(symbol_data.volume[valid_shift], get_value_by_time(valid_values, c_time, "volume"),
                f'@ {c_time}, {timeframe}')

#default timeframe
timeframe_data = {TimeFrame.S1: {'seconds': 1}, TimeFrame.M1: {'seconds': 60}, TimeFrame.M5: {'seconds': 300},
                       TimeFrame.M15: {'seconds': 900}, TimeFrame.M30: {'seconds': 1800},
                       TimeFrame.H1: {'seconds': 3600}, TimeFrame.H4: {'seconds': 14400},
                       TimeFrame.D1: {'seconds': 86400}}
for timeframe in timeframe_data:
    symbol_data = GetSymbolData(Symbol(), timeframe, 50)

    #Test basic values
    assertEqual(symbol_data.time[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "time"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.open[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "open"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.close[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "close"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.high[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "high"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.low[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "low"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.ask[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "ask"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.bid[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "bid"),
                f'@ {c_time}, {timeframe}')
    assertEqual(symbol_data.volume[valid_shift], get_timeframe_value_by_time(timeframe, c_time, "volume"),
                f'@ {c_time}, {timeframe}')

set_test_result("OK")
#
# StopTester()