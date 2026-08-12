name = "Pixiu Chart Demo EA"
version = "0.1.0"
label = "chart_demo"


def PX_InitScriptSettings():
    return {
        "charts": {
            "default": {
                "title": "Demo overlays",
                "type": "price",
                "height": 0.7,
                "series": [
                    {"name": "ma_fast", "label": "Fast MA", "color": "#0f766e", "line_width": 2},
                    {"name": "ma_slow", "label": "Slow MA", "color": "#b45309", "line_width": 2},
                    {"name": "support", "label": "Support", "color": "#2563eb", "line_width": 1},
                    {"name": "resistance", "label": "Resistance", "color": "#dc2626", "line_width": 1},
                    {"name": "expected_buy", "label": "Expected Buy", "color": "#16a34a", "line_width": 1},
                    {"name": "expected_sell", "label": "Expected Sell", "color": "#ea580c", "line_width": 1}
                ]
            }
        },
        "params": {
            "fast_ma_period": {"value": 10, "config": {"type": "int", "min": 2, "required": True}},
            "slow_ma_period": {"value": 30, "config": {"type": "int", "min": 3, "required": True}},
            "atr_period": {"value": 14, "config": {"type": "int", "min": 2, "required": True}},
            "support_points": {"value": 80, "config": {"type": "int", "min": 1, "required": True}},
            "resistance_points": {"value": 80, "config": {"type": "int", "min": 1, "required": True}},
            "demo_volume": {"value": 0.01, "config": {"type": "float", "min": 0.01, "required": True}},
            "trade_demo_orders": {"value": True, "config": {"type": "bool", "required": True}}
        }
    }


def PX_ValidScriptSettings(script_settings=None):
    params = script_settings.get("params", {}) if isinstance(script_settings, dict) else {}
    fast_param = params.get("fast_ma_period", 10)
    slow_param = params.get("slow_ma_period", 30)
    if isinstance(fast_param, dict):
        fast_param = fast_param.get("value", 10)
    if isinstance(slow_param, dict):
        slow_param = slow_param.get("value", 30)
    if int(fast_param) >= int(slow_param):
        return {"success": False, "errmsg": "fast_ma_period must be smaller than slow_ma_period"}
    return {"success": True, "errmsg": ""}


def DemoState():
    state = LoadData("chart_demo_state", scope=DataScope.EA)
    if state is None:
        state = {"tick": 0, "buy_uid": None, "sell_uid": None}
    return state


def PlotDemoSeries(price, point, ma_fast, ma_slow, atr):
    support = price - int(GetParam("support_points", 80)) * point
    resistance = price + int(GetParam("resistance_points", 80)) * point
    expected_buy = support + 25 * point
    expected_sell = resistance - 25 * point
    if atr is None or atr != atr:
        atr = 0
    Plot({
        "ma_fast": ma_fast,
        "ma_slow": ma_slow,
        "support": support,
        "resistance": resistance,
        "expected_buy": expected_buy,
        "expected_sell": expected_sell
    })
    return {
        "price": price,
        "support": support,
        "resistance": resistance,
        "expected_buy": expected_buy,
        "expected_sell": expected_sell,
        "ma_fast": ma_fast,
        "ma_slow": ma_slow,
        "atr": atr
    }


def MaybeTradeDemoOrders(state, point):
    if not GetParam("trade_demo_orders", True):
        return
    volume = float(GetParam("demo_volume", 0.01))
    tick = int(state.get("tick", 0))
    if tick == 20 and state.get("buy_uid") is None:
        stop_loss = Bid() - 120 * point
        take_profit = Ask() + 180 * point
        errid, result = Buy(volume=volume, stop_loss=stop_loss, take_profit=take_profit, tags={
            "demo": "chart",
            "reason": "fast MA observation"
        })
        if errid == 0:
            state["buy_uid"] = result.get("order_uid")
            PX_AppendEAExplainEvent({
                "event_type": "decision_open",
                "action": "open_buy",
                "reason_code": "chart_demo_buy",
                "summary": "Demo BUY marker: price is being tracked near the fast MA.",
                "order_uid": state["buy_uid"],
                "data": {"price": Ask()}
            })
    if tick == 60 and state.get("buy_uid") is not None:
        CloseOrder(state.get("buy_uid"), tags={"demo": "chart", "reason": "close demo buy"})
    if tick == 90 and state.get("sell_uid") is None:
        stop_loss = Ask() + 120 * point
        take_profit = Bid() - 180 * point
        errid, result = Sell(volume=volume, stop_loss=stop_loss, take_profit=take_profit, tags={
            "demo": "chart",
            "reason": "resistance observation"
        })
        if errid == 0:
            state["sell_uid"] = result.get("order_uid")
            PX_AppendEAExplainEvent({
                "event_type": "decision_open",
                "action": "open_sell",
                "reason_code": "chart_demo_sell",
                "summary": "Demo SELL marker: price is being tracked near the resistance line.",
                "order_uid": state["sell_uid"],
                "data": {"price": Bid()}
            })
    if tick == 135 and state.get("sell_uid") is not None:
        CloseOrder(state.get("sell_uid"), tags={"demo": "chart", "reason": "close demo sell"})


def BuildExplainChartFrames(symbol_data, size):
    frames = []
    last_shift = size - 1
    for shift in range(last_shift, -1, -1):
        bar_time = symbol_data.time[shift]
        bar_open = symbol_data.open[shift]
        bar_high = symbol_data.high[shift]
        bar_low = symbol_data.low[shift]
        bar_close = symbol_data.close[shift]
        if bar_time is None:
            continue
        if bar_open != bar_open or bar_high != bar_high or bar_low != bar_low or bar_close != bar_close:
            continue
        frames.append({
            "time": str(bar_time),
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
            "volume": symbol_data.volume[shift]
        })
    return frames


def BuildExplainChartLine(symbol_data, name, color, period, size):
    data = []
    last_shift = size - 1
    for shift in range(last_shift, -1, -1):
        bar_time = symbol_data.time[shift]
        if bar_time is None:
            continue
        value = iMA(symbol_data.close, timeperiod=period, matype=0, shift=shift)
        if value != value:
            continue
        data.append({"time": str(bar_time), "value": value})
    return {"id": name, "type": "line", "name": name, "color": color, "data": data}


def PX_GetEAExplainChartTypes():
    return {
        "chart_types": [
            {
                "type": "open_context",
                "title": "Open Context Demo",
                "description": "Shows support/resistance, expected entries, current price, and MA context.",
                "symbols": [Symbol()],
                "params": [
                    {"name": "include_orders", "type": "bool", "default": True}
                ]
            }
        ]
    }


def PX_GetEAExplainChart(request):
    chart_type = request.get("chart_type", "open_context")
    if chart_type != "open_context":
        return {
            "success": False,
            "error": "unsupported_chart_type",
            "message": "Supported chart_type: open_context"
        }
    state = DemoState()
    point = SymbolInfo("point")
    price = Close()
    snapshot = state.get("last_snapshot", {})
    support = snapshot.get("support", price - 80 * point)
    resistance = snapshot.get("resistance", price + 80 * point)
    expected_buy = snapshot.get("expected_buy", support + 25 * point)
    expected_sell = snapshot.get("expected_sell", resistance - 25 * point)
    ma_fast = snapshot.get("ma_fast", price)
    ma_slow = snapshot.get("ma_slow", price)
    symbol_data = GetSymbolData(Symbol(), DefaultTimeFrame(), 80)
    frame_size = 50
    frames = BuildExplainChartFrames(symbol_data, frame_size)
    start_time = frames[0].get("time") if len(frames) > 0 else str(Time())
    end_time = frames[-1].get("time") if len(frames) > 0 else str(Time())
    fast_period = int(GetParam("fast_ma_period", 10))
    slow_period = int(GetParam("slow_ma_period", 30))
    return {
        "chart_type": chart_type,
        "title": "Pixiu Chart Demo - Open Context",
        "summary": "On-demand strategy chart data generated by the EA and rendered by the caller.",
        "symbol": Symbol(),
        "timeframe": DefaultTimeFrame(),
        "time": str(Time()),
        "price": price,
        "axis": {
            "time": {"format": "YYYY-MM-DD HH:mm", "timezone": "UTC"},
            "price": {"precision": 5, "side": "right"}
        },
        "panes": [
            {"id": "price", "type": "price", "title": Symbol(), "height": 1.0, "symbol": Symbol()}
        ],
        "frames": frames,
        "series": [
            {"id": "current_price", "type": "point", "name": "Current Price", "color": "#111827",
             "data": [{"time": str(Time()), "value": price}]},
            BuildExplainChartLine(symbol_data, "ma_fast", "#0f766e", fast_period, frame_size),
            BuildExplainChartLine(symbol_data, "ma_slow", "#b45309", slow_period, frame_size)
        ],
        "objects": [
            {"id": "support", "type": "price_line", "pane": "price", "price": support,
             "color": "#2563eb", "title": "Support", "axis_label_visible": True},
            {"id": "resistance", "type": "price_line", "pane": "price", "price": resistance,
             "color": "#dc2626", "title": "Resistance", "axis_label_visible": True},
            {"id": "expected_buy_line", "type": "price_line", "pane": "price", "price": expected_buy,
             "color": "#16a34a", "title": "Expected Buy", "line_style": "dashed"},
            {"id": "expected_sell_line", "type": "price_line", "pane": "price", "price": expected_sell,
             "color": "#ea580c", "title": "Expected Sell", "line_style": "dashed"},
            {"id": "expected_buy_marker", "type": "marker", "pane": "price", "time": str(Time()),
             "price": expected_buy, "position": "below_bar", "shape": "arrow_up", "color": "#16a34a",
             "text": "Expected Buy"},
            {"id": "expected_sell_marker", "type": "marker", "pane": "price", "time": str(Time()),
             "price": expected_sell, "position": "above_bar", "shape": "arrow_down", "color": "#ea580c",
             "text": "Expected Sell"},
            {"id": "support_zone", "type": "rectangle", "pane": "price",
             "points": [{"time": start_time, "price": support - 15 * point},
                        {"time": end_time, "price": support + 15 * point}],
             "text": "Support Zone",
             "style": {"fill_color": "rgba(37, 99, 235, 0.12)", "border_color": "#2563eb"}},
            {"id": "ma_context_trend", "type": "trend_line", "pane": "price",
             "points": [{"time": start_time, "price": ma_slow},
                        {"time": end_time, "price": ma_fast}],
             "text": "MA Context",
             "style": {"color": "#7c3aed", "line_width": 1, "line_style": "dotted"}},
            {"id": "stage_note", "type": "text", "pane": "price", "time": str(Time()),
             "price": resistance, "text": "Stage context"}
        ],
        "metrics": {
            "tick": state.get("tick", 0),
            "price": price,
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "atr": snapshot.get("atr", 0),
            "opened_orders": len(GetOpenedOrderUIDs())
        },
        "payload": {
            "request": request,
            "state": state
        }
    }


state = DemoState()
state["tick"] = int(state.get("tick", 0)) + 1
symbol_data = GetSymbolData(Symbol(), DefaultTimeFrame(), 80)
fast_period = int(GetParam("fast_ma_period", 10))
slow_period = int(GetParam("slow_ma_period", 30))
atr_period = int(GetParam("atr_period", 14))
price = Close()
point = SymbolInfo("point")
ma_fast = iMA(symbol_data.close, timeperiod=fast_period, matype=0, shift=0)
ma_slow = iMA(symbol_data.close, timeperiod=slow_period, matype=0, shift=0)
atr = iATR(symbol_data, timeperiod=atr_period, shift=0)
snapshot = PlotDemoSeries(price, point, ma_fast, ma_slow, atr)
state["last_snapshot"] = snapshot
PX_UpdateEAExplainStatus({
    "status": "running",
    "phase": "chart_demo",
    "summary": "Collecting chart demo overlays and explain context.",
    "decision_summary": {
        "price": price,
        "ma_fast": ma_fast,
        "ma_slow": ma_slow,
        "support": snapshot.get("support"),
        "resistance": snapshot.get("resistance")
    }
})
MaybeTradeDemoOrders(state, point)
SaveData("chart_demo_state", state, scope=DataScope.EA)
