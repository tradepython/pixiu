
### [2023-02-12]
#### Version:
#####   Package:
#####    pixiu: 0.100.*.20230212
#####
#### **Descriptions：**
     1.ea_tester.py:
       1) Fix get_api missing error.

### [2023-01-11]
#### Version:
#####   Package:
#####    pixiu: 0.99.*.20230111
#####
#### **Descriptions：**
     1.ea_tester.py:
       1) Fix self.current_tick_index exception in execute_(self, ticket)

### [2022-12-28]
#### Version:
#####   Package:
#####    pixiu: 0.98.*.20221228
#####
#### **Descriptions：**
     1.Add global API:
      PX_InitScriptSettings, PX_ValidScriptSettings
      Call order:
       PX_InitScriptSettings -> AddChart/AddParam -> PX_ValidScriptSettings
     2.Add ts_settings.py

### [2022-12-19]
#### Version:
#####   Package:
#####    pixiu: 0.97.*.20221219
#####
#### **Descriptions：**
     1.Add global API:
      PX_InitScriptSettings, PX_ValidScriptSettings
      Call order:
       PX_InitScriptSettings -> AddChart/AddParam -> PX_ValidScriptSettings

### [2022-12-07]
#### Version:
#####   Package:
#####    pixiu: 0.96.*.20221207
#####
#### **Descriptions：**
    1.api.py:
      Add AddChart, AddParam

### [2022-12-06]
#### Version:
#####   Package:
#####    pixiu: 0.95.*.20221206
#####
#### **Descriptions：**
    1.api.py:
      Add AddChart, AddParam

### [2022-12-05]
#### Version:
#####   Package:
#####    pixiu: 0.94.*.20221205
#####
#### **Descriptions：**
   1.pxtester.py:
     1) Replace json with json5

### [2022-12-02]
#### Version:
#####   Package:
#####    pixiu: 0.93.*.20221202
#####
#### **Descriptions：**
   1.pxtester.py:
     1) Fix get_data_info tzinfo error

### [2022-11-04]
#### Version:
#####   Package:
#####    pixiu: 0.92.*.20221104
#####
#### **Descriptions：**
    1.api_base.py:
     1) Add _safe_import

### [2022-10-25]
#### Version:
#####   Package:
#####    pixiu: 0.91.*.20221025
#####
#### **Descriptions：**
    1.ea_tester.py:
     1)Add execute_script

### [2022-08-26]
#### Version:
#####   Package:
#####    pixiu: 0.90.*.20220826
#####
#### **Descriptions：**
    1.test_pixiu.py:
     1) test_ea_tester_func_base: datetime.utcfromtimestamp(new_a['t'][idx])
     2) test_ea_tester_func_indicators: datetime.utcfromtimestamp(new_a['t'][idx])
    2.ts_symbol_data.py:
     1) Change 
            assertEqual(df['time'][valid_shift], get_timeframe_value_by_time(timeframe, c_time, "time").timestamp(),
                f'@ {c_time}, {timeframe}')
        to 
            assertEqual(df['time'][valid_shift], get_timeframe_value_by_time(timeframe, c_time, "time").replace(tzinfo=timezone('UTC')).timestamp(),
                f'@ {c_time}, {timeframe}')
    3.setup.py:
     1) Add requires: dash, plotly


### [2022-08-02]
#### Version:
#####   Package:
#####    pixiu: 0.89.*.20220802
#####
#### **Descriptions：**
    1.ea_tester.py:
     1) Fix calculate_return_ratio return value error

### [2022-07-28]
#### Version:
#####   Package:
#####    pixiu: 0.88.*.20220728
#####
#### **Descriptions：**
    1.pxtester.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp
    2.account.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp
    3.order.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp
    4.symbol.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp
    5.ea_tester.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp
    6.test_pixiu.py:
      1) Change datetime.fromtimestamp to datetime.utcfromtimestamp

### [2022-07-18]
#### Version:
#####   Package:
#####    pixiu: 0.87.*.20220718
#####
#### **Descriptions：**
    1. Fix gen_report_row total_value bug

### [2022-06-20]
#### Version:
#####   Package:
#####    pixiu: 0.86.*.20220620
#####
#### **Descriptions：**
    1.Add ea_tester_graph
       support dash + plotly
        

### [2022-05-18]
#### Version:
#####   Package:
#####    pixiu: 0.85.*.20220518
#####
#### **Descriptions：**
    1.ea_tester.py:
        1) Fix calculate_returns calculation error


### [2022-04-26]
#### Version:
#####   Package:
#####    pixiu: 0.84.*.20220426
#####
#### **Descriptions：**
    1.tester_api_v1.py:
        1) Fix __get_indicator__ cache_name error

### [2022-04-24]
#### Version:
#####   Package:
#####    pixiu: 0.83.*.20220424
#####
#### **Descriptions：**
    1.symbol.py:
      1) SymbolIndicator, SymbolPrice, SymbolTime, SymbolData add getitem_index
      2) SymbolPrice add:
            <	__lt__(self, other)
            >	__gt__(self, other)
            <=	__le__(self, other)
            >=	__ge__(self, other)
            ==	__eq__(self, other)
            !=	__ne__(self, other)
            +	__add__(self, other)
            –	__sub__(self, other)
            * __mul__(self, other)
            /	__truediv__(self, other)
            //	__floordiv__(self, other)
            %	__mod__(self, other)
            **	__pow__(self, other)

### [2022-04-23]
#### Version:
#####   Package:
#####    pixiu: 0.82.*.20220423
#####
#### **Descriptions：**
    1.symbol.py:
      1) Add to_dataframe
    2.api_base.py:
      1) env_dict add _iter_unpack_sequence_ # [abs(value - level) < ave for _, level in levels]
    3.ea_node_transformer.py:
      1) Add EARestrictingNodeTransformer

### [2022-04-22]
#### Version:
#####   Package:
#####    pixiu: 0.81.*.20220422
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) Change min_volume initial value to None
    2.pxtester.py:
      1)  Fix on_end_execute item['value'] None error
    3.main.py:
      1)  Fix gen_report_row item['value'] None error

### [2022-04-21]
#### Version:
#####   Package:
#####    pixiu: 0.80.*.20220421
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) report add max_volume

### [2022-04-20]
#### Version:
#####   Package:
#####    pixiu: 0.79.*.20220420
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) Fix __valid_order__ pending order error

### [2022-04-18]
#### Version:
#####   Package:
#####    pixiu: 0.78.*.20220418
#####
#### **Descriptions：**
    1.api_base.py:
      1) env_dictAdd property

### [2022-04-07]
#### Version:
#####   Package:
#####    pixiu: 0.77.*.20220407
#####
#### **Descriptions：**
    1.ea_tester.py:
        1) Fix calculate_return_ratio error
        2) Add sortino_ratio

### [2022-04-06]
#### Version:
#####   Package:
#####    pixiu: 0.76.*.20220406
#####
#### **Descriptions：**
    1.ea_tester.py:
        1) Add percent_str_to_float
        2) Add calculate_sharpe_ratio

### [2022-04-03]
#### Version:
#####   Package:
#####    pixiu: 0.75.*.20220403
#####
#### **Descriptions：**
    1.ea_tester.py:
        1) Add margin_so_so, margin_so_call checking

### [2022-04-02]
#### Version:
#####   Package:
#####    pixiu: 0.74.*.20220402
#####
#### **Descriptions：**
    1.ea_tester.py:
       Fix modify_order order_log error

### [2022-03-30]
#### Version:
#####   Package:
#####    pixiu: 0.73.*.20220330
#####
#### **Descriptions：**
    1.ea_tester.py:
        __remove_pending_order__ pop add None
    2.Add set:
      env_dict["set"]


### [2022-03-10]
#### Version:
#####   Package:
#####    pixiu: 0.72.*.20220310
#####
#### **Descriptions：**
    1.ts_order_buylimit.py,ts_order_buystop.py,ts_order_selllimit.py,ts_order_sellstop.py:
      Add check order.status
    2.api.py:
      Add GetSettings

### [2022-03-09]
#### Version:
#####   Package:
#####    pixiu: 0.71.*.20220309
#####
#### **Descriptions：**
    1.defines.py:
      Add OrderStatus
    2.order.py:
      Add status

### [2022-03-05]
#### Version:
#####   Package:
#####    pixiu: 0.70.*.20220305
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) __process_order__: Add parameters: ask, last_ask, bid, last_bid
      2) __calculate_profit__: Update calculation m
      3) __valid_order__: Add parameters: ask, bid

### [2022-03-04]
#### Version:
#####   Package:
#####    pixiu: 0.69.*.20220304
#####
#### **Descriptions：**
    1.Add PositionType
    2.Fix __valid_order__ pending order error
    3.Fix __close_order__ close_time error

### [2022-03-02]
#### Version:
#####   Package:
#####    pixiu: 0.68.*.20220301
#####
#### **Descriptions：**
    1.ea_tester.py: Add volume_precision

### [2022-03-01]
#### Version:
#####   Package:
#####    pixiu: 0.67.*.20220301
#####
#### **Descriptions：**
    1.fix __remove_order__ pop bug

### [2022-02-26]
#### Version:
#####   Package:
#####    pixiu: 0.66.*.20220226
#####
#### **Descriptions：**
    1.Add is_dirty method to order
    2.API: add RunMode, CloseMultiOrders
    3.Defines: add RunModeValue

### [2022-02-24]
#### Version:
#####   Package:
#####    pixiu: 0.65.*.20220224
#####
#### **Descriptions：**
    1.Change error name: EID_EAT_MARGIN_CALL -> EID_EAT_NOT_ENOUGH_MONEY

### [2022-02-22]
#### Version:
#####   Package:
#####    pixiu: 0.64.*.20220222
#####
#### **Descriptions：**
    1.Add tags in order data 

### [2022-02-11]
#### Version:
#####   Package:
#####    pixiu: 0.63.*.20220211
#####
#### **Descriptions：**
    1.Add new testing 'test_ea_tester_func_load_lib'

### [2022-02-10]
#### Version:
#####   Package:
#####    pixiu: 0.62.*.20220210
#####
#### **Descriptions：**
    1.Add library function 
        ###[lib|library]=["PriceAction==0.1.0"]
    2.ea_base.py:
      1)Add method parse_script
    


### [2022-02-09]
#### Version:
#####   Package:
#####    pixiu: 0.61.*.20220209
#####
#### **Descriptions：**
    1.Remove OrderScope, using DataScope

### [2021-12-14]
#### Version:
#####   Package:
#####    pixiu: 0.60.*.20211114
#####
#### **Descriptions：**
    1.EA script support timezone
    2.ts_base: Add test_timezone

### [2021-12-11]
#### Version:
#####   Package:
#####    pixiu: 0.59.*.20211111
#####
#### **Descriptions：**
    1.Support auto loading script from tag
        pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 -s ../Test/Test_V2.11.18-3x.py -p report -t 2.11.18-3x -l ea2_7_211209.json
        or
        pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 -s ../Test -p report -t 2.11.18-3x -l ea2_7_211209.json


### [2021-11-26]
#### Version:K
#####   Package:
#####    pixiu: 0.58.*.20211126
#####
#### **Descriptions：**
    1.Update README.md/README.zh.md
    2.ea_tester.py:
      Modify notify output format

### [2021-11-25]
#### Version:
#####   Package:
#####    pixiu: 0.57.*.20211125
#####
#### **Descriptions：**
    1.Update README.md/README.zh.md
    2.ea_tester.py:
      Modify notify output format


### [2021-11-24]
#### Version:
#####   Package:
#####    pixiu: 0.56.*.20211124
#####
#### **Descriptions：**
    1.api.py, tester_api_v1.py:
      Add Notify


### [2021-11-16]
#### Version:
#####   Package:
#####    pixiu: 0.55.*.20211116
#####
#### **Descriptions：**
    1.Fix setup.py requires. 

### [2021-11-15]
#### Version:
#####   Package:
#####    pixiu: 0.54.0.20211115
#####
#### **Descriptions：**
    1.api.py, tester_api_v1.py:
      Add DeleteData, LoadData, SaveData
      Buy/Sell/ModifyOrder/CloseOrder add argument tags 
    2.tests:
      ts_base.py add data test
      ts_order_market.py add tags 
    3.api_base.py:
      Add uuid, hashlib 

### [2021-11-14]
#### Version:
#####   Package:
#####    pixiu: 0.53.0.20211114
#####
#### **Descriptions：**
    1.api.py, tester_api_v1.py:
      Ask, Bid, Time, Volume, Open, Close, Low, High add symbol
    2.order.py:
      Add from_uid, to_uid， group_uid, tags

### [2021-11-13]
#### Version:
#####   Package:
#####    pixiu: 0.52.0.20211113
#####
#### **Descriptions：**
    1.Add arguments : 
        --compare-wit-tag/-r, --tag/-t, --datafile/-l
      sample:
            1)  
               pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 testGBPUSD_TP_Demo1 testNZDUSD_TP_Demo1 testEURUSD_TP_Demo1 testUSDCHF_TP_Demo1 testUSDJPY_TP_Demo1 testUSDCAD_TP_Demo1 -s ../EA/EA_V2.10.0.py -p report -t 2.10.0 -l ea2_7.json
               pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 testGBPUSD_TP_Demo1 testNZDUSD_TP_Demo1 testEURUSD_TP_Demo1 testUSDCHF_TP_Demo1 testUSDJPY_TP_Demo1 testUSDCAD_TP_Demo1 -s ../EA/EA_V2.10.1.py -p report -t 2.10.1 -l ea2_7.json
               pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 testGBPUSD_TP_Demo1 testNZDUSD_TP_Demo1 testEURUSD_TP_Demo1 testUSDCHF_TP_Demo1 testUSDJPY_TP_Demo1 testUSDCAD_TP_Demo1 -s ../EA/EA_V2.10.2.py -p report -t 2.10.2 -l ea2_7.json
               
               pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 testGBPUSD_TP_Demo1 testNZDUSD_TP_Demo1 testEURUSD_TP_Demo1 testUSDCHF_TP_Demo1 testUSDJPY_TP_Demo1 testUSDCAD_TP_Demo1 -t 2.10.0 -r 2.10.1 2.10.2 -l ea2_7.json
                +----+--------------------------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+--------------------+
                |    |                                      | testAUDUSD_TP_Demo1 | testGBPUSD_TP_Demo1 | testNZDUSD_TP_Demo1 | testEURUSD_TP_Demo1 | testUSDCHF_TP_Demo1 | testUSDJPY_TP_Demo1 | testUSDCAD_TP_Demo1 | Total/Avg          |
                +----+--------------------------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+---------------------+--------------------+
                | 1  | Init Balance(2.10.0)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
                | 1  | Init Balance(2.10.1)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
                | 1  | Init Balance(2.10.2)                 | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 5000.0              | 35000.0 / 5000.0   |
                ...
                | 7  | Balance(2.10.0)                      | 4988.31             | 5064.61             | 5041.77             | 5071.6              | 4994.96             | 4996.97             | 4996.94             | 35155.16 / 5022.17 |
                | 7  | Balance(2.10.1)                      | 5003.42 ↑           | 5061.26 ↓           | 5000.58 ↓           | 4965.65 ↓           | 5009.12 ↑           | 5033.44 ↑           | 4931.17 ↓           | 35004.64 / 5000.66 |
                | 7  | Balance(2.10.2)                      | 4981.59 ↓           | 5076.74 ↑           | 5000.58 ↓           | 4985.02 ↓           | 5023.02 ↑           | 5029.35 ↑           | 4965.34 ↓           | 35061.64 / 5008.81 |
                | 8  | Total Net Profit(2.10.0)             | -11.69              | 64.61               | 41.77               | 71.6                | -5.05               | -3.02               | -3.05               | 155.17 / 22.17     |
                | 8  | Total Net Profit(2.10.1)             | 3.42 ↑              | 61.26 ↓             | 0.58 ↓              | -34.35 ↓            | 9.14 ↑              | 33.44 ↑             | -68.84 ↓            | 4.65 / 0.66        |
                | 8  | Total Net Profit(2.10.2)             | -18.41 ↓            | 76.74 ↑             | 0.58 ↓              | -14.98 ↓            | 23.04 ↑             | 29.35 ↑             | -34.68 ↓            | 61.64 / 8.81       |
                | 9  | Total Net Profit Rate(2.10.0)        | -0.23 %             | 1.29 %              | 0.84 %              | 1.43 %              | -0.1 %              | -0.06 %             | -0.06 %             | 3.11 % / 0.44 %    |
                | 9  | Total Net Profit Rate(2.10.1)        | 0.07 % ↑            | 1.23 % ↓            | 0.01 % ↓            | -0.69 % ↓           | 0.18 % ↑            | 0.67 % ↑            | -1.38 % ↓           | 0.09 % / 0.01 %    |
                | 9  | Total Net Profit Rate(2.10.2)        | -0.37 % ↓           | 1.53 % ↑            | 0.01 % ↓            | -0.3 % ↓            | 0.46 % ↑            | 0.59 % ↑            | -0.69 % ↓           | 1.23 % / 0.18 %    |
                ...

               pixiu -c pixiu.json -n testUSDCAD_TP_Demo1 -t 2.10.0 -r 2.10.1 2.10.2 -l ea2_7.json
                +----+--------------------------------------+---------------------+-------------------+
                |    |                                      | testUSDCAD_TP_Demo1 | Total/Avg         |
                +----+--------------------------------------+---------------------+-------------------+
                | 1  | Init Balance(2.10.0)                 | 5000.0              | 5000.0 / 5000.0   |
                | 1  | Init Balance(2.10.1)                 | 5000.0              | 5000.0 / 5000.0   |
                | 1  | Init Balance(2.10.2)                 | 5000.0              | 5000.0 / 5000.0   |
                ...
                | 7  | Balance(2.10.0)                      | 4996.94             | 4996.94 / 4996.94 |
                | 7  | Balance(2.10.1)                      | 4931.17 ↓           | 4931.17 / 4931.17 |
                | 7  | Balance(2.10.2)                      | 4965.34 ↓           | 4965.34 / 4965.34 |
                | 8  | Total Net Profit(2.10.0)             | -3.05               | -3.05 / -3.05     |
                | 8  | Total Net Profit(2.10.1)             | -68.84 ↓            | -68.84 / -68.84   |
                | 8  | Total Net Profit(2.10.2)             | -34.68 ↓            | -34.68 / -34.68   |
                | 9  | Total Net Profit Rate(2.10.0)        | -0.06 %             | -0.06 % / -0.06 % |
                | 9  | Total Net Profit Rate(2.10.1)        | -1.38 % ↓           | -1.38 % / -1.38 % |
                | 9  | Total Net Profit Rate(2.10.2)        | -0.69 % ↓           | -0.69 % / -0.69 % |
                ...





### [2021-11-11]
#### Version:
#####   Package:
#####    pixiu: 0.51.0.20211111
#####
#### **Descriptions：**
    1.api_base:
      Add build-in function: max, min, all, any, ascii, bin, chr, divmod, enumerate, filter, format, hex, next, oct, ord, pow, reversed, sorted, sum
    2.main.py:
      Add argument: multiprocessing

### [2021-10-26]
#### Version:
#####   Package:
#####    pixiu: 0.50.0.20211026
#####
#### **Descriptions：**
    1.ea_tester.py:
        1) Fix report currency bug

### [2021-10-24]
#### Version:
#####   Package:
#####    pixiu: 0.49.0.20211024
#####
#### **Descriptions：**
    1.Using process pool

### [2021-10-23]
#### Version:
#####   Package:
#####    pixiu: 0.48.0.20211023
#####
#### **Descriptions：**
    1.Add support multiple test names:
     pixiu -c pixiu.json -n testAUDUSD_TP_Demo1 testGBPUSD_TP_Demo1 testNZDUSD_TP_Demo1 testEURUSD_TP_Demo1 testUSDCHF_TP_Demo1 testUSDJPY_TP_Demo1 testUSDCAD_TP_Demo1 ...


### [2021-10-19]
#### Version:
#####   Package:
#####    pixiu: 0.47.0.20211019
#####
#### **Descriptions：**
    1.ea_tester.py:
     1) Fix report total_net_profit_rate error.
    2.pxtester.py:
     1) parse_test_config: Add custom account

### [2021-10-18]
#### Version:
#####   Package:
#####    pixiu: 0.46.0.20211018
#####
#### **Descriptions：**
    1.ea_tester.py:
     1) Fix modify_order bug, if take_profit or stop_loss is None

### [2021-10-16]
#### Version:
#####   Package:
#####    pixiu: 0.45.0.20211016
#####
#### **Descriptions：**
    1.pxtester.py:
      1) Report add win rate

### [2021-10-15]
#### Version:
#####   Package:
#####    pixiu: 0.44.0.20211015
#####
#### **Descriptions：**
    1.pxtester.py:
      1) Add argument: print_log_type = account|order|ea|report

### [2021-10-14]
#### Version:
#####   Package:
#####    pixiu: 0.43.0.20211014
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) Fix bugs: __process_order__, close_all_orders call close_order error
      2) Fix bugs: max_drawdown calculation
    2.pxtester.py:
      1) on_end_execute: report output format

### [2021-08-25]
#### Version:
#####   Package:
#####    pixiu: 0.42.0.20210825
#####
#### **Descriptions：**
    1.ea_tester.py:
      1) __add_market_order__:
        new_order['comment'] = f"cuid#{new_order['uid']}|" 
        to
        new_order['comment'] = f"uid#{new_order['uid']}|"

### [2021-08-06]
#### Version:
#####   Package:
#####    pixiu: 0.41.0.20210806
#####
#### **Descriptions：**
    1.API 1 
      1) Add Plot 

### [2021-08-04]
#### Version:
#####   Package:
#####    pixiu: 0.40.0.20210804
#####
#### **Descriptions：**
    1.ea_tester.py:
        1).Change plot parameters to plot(chart_name, {series_name1: data, series_name2: data, ...})

### [2021-07-20]
#### Version:
#####   Package:
#####    pixiu: 0.39.0.20210720
#####
#### **Descriptions：**
    1.ea_tester.py:
        1).Add plot 

### [2021-07-16]
#### Version:
#####   Package:
#####    pixiu: 0.38.0.20210716
#####
#### **Descriptions：**
    1.Update API:
     1) GetOpenedOrderUIDs, GetPendingOrderUIDs, GetClosedOrderUIDs
       Add parameter: scope

### [2021-07-08]
#### Version:
#####   Package:
#####    pixiu: 0.37.0.20210708
#####
#### **Descriptions：**
    1.fix write_log bugs: parameters count


### [2021-06-07]
#### Version:
#####   Package:
#####    pixiu: 0.36.2.20210607
#####
#### **Descriptions：**
    1.fix dependencies bugs
       remove oeoeweb library
       add pymongo library
    2.fix sample.py, sample2.py errors.
    3.API add AcquireLock, ReleaseLock 

    
### [2021-06-04]
#### Version:
#####   Package:
#####    pixiu: 0.35.0.20210604
#####
#### **Descriptions：**
    1.Modify API:
     1) 
       def CloseOrder(self, uid, price, volume: float, slippage=None, arrow_color=None) -> (ErrorID, OrderResult)
       ->
       def CloseOrder(self, uid, volume=None, price=None, slippage=None, arrow_color=None) -> (ErrorID, OrderResult)
    2.fix:
      __valid_order__: EID_EAT_INVALID_ORDER_CLOSE_PRICE 
    3.Add:
      __order_close_price__


### [2021-06-03]
#### Version:
#####   Package:
#####    pixiu: 0.34.0.20210603
#####
#### **Descriptions：**
    1.fix bugs GetSymbolData('*') 
    2. 
      self.orders['ds'] -> order['__ds__']
      self.account_info['ds'] -> self.account_info['__ds__']
    3.Add build-in :
      datetime, timedelta, random

### [2021-06-01]
#### Version:
#####   Package:
#####    pixiu: 0.33.0.20210601
#####
#### **Descriptions：**
    1.add APIs:
      WaitCommand
    2.modify APIs:
      Buy, Sell, CloseOrder, ModifyOrder return order_uid -> OrderResult

### [2021-05-31]
#### Version:
#####   Package:
#####    pixiu: 0.32.0.20210531
#####
#### **Descriptions：**
    1.fix EATesterPrintCollector._call_print write_log bug

### [2021-05-30]
#### Version:
#####   Package:
#####    pixiu: 0.31.0.20210530
#####
#### **Descriptions：**
    1. get_url_data add headers

### [2021-05-29]
#### Version:
#####   Package:
#####    pixiu: 0.30.0.20210529
#####
#### **Descriptions：**
    1.Add output


### [2021-05-28]
#### Version:
#####   Package:
#####    pixiu: 0.29.0.20210528
#####
#### **Descriptions：**
    1.Struct project directories
    2.Complete README.txt


### [2021-05-27]
#### Version:
#####   Package:
#####    pixiu: 0.28.0.20210527
#####
#### **Descriptions：**
    1.Add load channel


### [2021-05-26]
#### Version:
#####   Package:
#####    pixiu: 0.27.0.20210526
#####
#### **Descriptions：**
    1.Add PXTester, main


### [2021-05-24]
#### Version:
#####   Package:
#####    pixiu: 0.26.0.20210524
#####
#### **Descriptions：**
    1. api add help doc string


### [2021-05-22]
#### Version:
#####   Package:
#####    pixiu: 0.25.0.20210522
#####
#### **Descriptions：**
    1.add language
    2.fix sl/tp error:
      ds[((ds['sl'] > 0) & (ds['sl_p'] <= 0)) | ((ds['tp'] > 0) & (ds['tp_p'] >= 0))]
    3.api:
        Dict - > UIDs
        def GetOpenedOrderUIDs(self, symbol: str = None)
        def GetPendingOrderUIDs(self, symbol: str = None)
        def GetClosedOrderUIDs(self, symbol: str = None)


### [2021-05-19]
#### Version:
#####   Package:
#####    pixiu: 0.24.0.20210519
#####
#### **Descriptions：**
    1.add test_pixiu set_test_result

### [2021-05-18]
#### Version:
#####   Package:
#####    pixiu: 0.23.0.20210518
#####
#### **Descriptions：**

### [2021-05-17]
#### Version:
#####   Package:
#####    pixiu: 0.22.0.20210517
#####
#### **Descriptions：**
    1.SymbolIndicator, SymbolPrice, SymbolTime, SymbolData arguments.


### [2021-05-15]
#### Version:
#####   Package:
#####    pixiu: 0.21.0.20210515
#####
#### **Descriptions：**


### [2021-05-13]
#### Version:
#####   Package:
#####    pixiu: 0.20.0.20210513
#####
#### **Descriptions：**



### [2021-05-11]
#### Version:
#####   Package:
#####    pixiu: 0.19.0.20210511
#####
#### **Descriptions：**
    1.fix ea_tester some bugs


### [2021-05-10]
#### Version:
#####   Package:
#####    pixiu: 0.18.0.20210510
#####
#### **Descriptions：**

### [2021-05-09]
#### Version:
#####   Package:
#####    pixiu: 0.17.0.20210509
#####
#### **Descriptions：**
    1. Buy, Sell, ModifyOrder remove arguments comment


### [2021-05-08]
#### Version:
#####   Package:
#####    pixiu: 0.16.0.20210508
#####
#### **Descriptions：**
    1.

### [2021-05-07]
#### Version:
#####   Package:
#####    pixiu: 0.15.0.20210507
#####
#### **Descriptions：**
    1. def GetSymbolData(self, symbol: str, timeframe: str, count: int)


### [2021-05-06]
#### Version:
#####   Package:
#####    pixiu: 0.14.0.20210506
#####
#### **Descriptions：**
    1. some fixs


### [2021-05-01]
#### Version:
#####   Package:
#####    pixiu: 0.13.0.20210501
#####
#### **Descriptions：**
    1.Add test open, modify, close in the EAT testing.

### [2021-04-30]
#### Version:
#####   Package:
#####    pixiu: 0.12.0.20210430
#####
#### **Descriptions：**
    1.Finish EAT's 7 tests.

### [2021-04-29]
#### Version:
#####   Package:
#####    pixiu: 0.11.0.20210429
#####
#### **Descriptions：**
    1.Add Account, Symbol Classes
    2.Add ts_order, ts_base


### [2021-04-28]
#### Version:
#####   Package:
#####    pixiu: 0.10.0.20210428
#####
#### **Descriptions：**
    1.Add some methods


### [2021-04-27]
#### Version:
#####   Package:
#####    pixiu: 0.9.0.20210427
#####
#### **Descriptions：**

### [2021-04-26]
#### Version:
#####   Package:
#####    pixiu: 0.8.0.20210426
#####
#### **Descriptions：**
    1. Add test_ea_tester_func_indicators

