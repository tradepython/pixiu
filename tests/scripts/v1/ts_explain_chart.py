def PX_GetEAExplainChartTypes():
    return {
        "chart_types": [
            {
                "type": "open_context",
                "title": "Open Context",
                "description": "Show decision context for opening orders.",
                "symbols": [Symbol()],
                "params": {
                    "include_orders": {"type": "bool", "default": True},
                    "include_levels": {"type": "bool", "default": True},
                },
            }
        ]
    }


def PX_GetEAExplainChart(request):
    chart_type = request.get("chart_type")
    if chart_type != "open_context":
        return {
            "success": False,
            "error": "unsupported_chart_type",
            "message": "Unsupported chart type.",
        }
    price = Close()
    return {
        "chart_type": chart_type,
        "title": "Open Context",
        "description": "Current open decision context.",
        "price": price,
        "objects": [
            {
                "type": "horizontal_line",
                "name": "support",
                "price": price - 0.001,
                "text": "Support",
            },
            {
                "type": "horizontal_line",
                "name": "resistance",
                "price": price + 0.001,
                "text": "Resistance",
            },
            {
                "type": "marker",
                "name": "expected_buy",
                "side": "buy",
                "price": price - 0.0005,
                "text": "Expected Buy",
            },
        ],
        "metrics": {
            "stage": 5,
            "direction_score": 72,
        },
        "payload": {
            "request": request,
        },
    }
