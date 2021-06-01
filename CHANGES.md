
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

