import copy
from datetime import datetime, timezone

import dateutil.parser


CHART_PROTOCOL_VERSION = "pixiu-chart-v1"
REDACTED_VALUE = "[REDACTED]"
SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_token",
    "access_token",
    "refresh_token",
    "private_key",
    "authorization",
    "auth",
    "credential",
    "cookie",
    "session",
    "server",
    "broker",
)
PATH_KEYWORDS = ("path", "file")


def sanitize_chart_config(value, key=None):
    """Return a display-safe copy of config values for browser chart reports."""
    key_text = str(key or "").lower()
    if key_text and any(keyword in key_text for keyword in SENSITIVE_KEYWORDS):
        return REDACTED_VALUE
    if isinstance(value, dict):
        return {item_key: sanitize_chart_config(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_chart_config(item) for item in value]
    if isinstance(value, str):
        if key_text and any(keyword in key_text for keyword in PATH_KEYWORDS):
            return _safe_path_label(value)
        if value.startswith(("/", "~")) or ":\\" in value:
            return _safe_path_label(value)
    return value


def _safe_path_label(value):
    name = str(value).replace("\\", "/").rstrip("/").split("/")[-1]
    return "<file: %s>" % (name or "hidden")


class LegacyChartAdapter(object):
    """Convert existing tester chart/log data into the Pixiu chart protocol."""

    def __init__(self, script_settings=None, charts_data=None, graph_data=None,
                 order_logs=None, account_logs=None, print_logs=None, report=None,
                 metadata=None, symbols=None, default_symbol=None, timeframe=None,
                 account=None, explain_status=None, explain_events=None,
                 explain_order_states=None, market_events=None, market_event_manifest=None):
        self.script_settings = script_settings or {}
        self.charts_data = charts_data or []
        self.graph_data = graph_data or {}
        self.order_logs = order_logs or []
        self.account_logs = account_logs or []
        self.print_logs = print_logs or []
        self.report = report or {}
        self.metadata = metadata or {}
        self.symbols = symbols or {}
        self.default_symbol = default_symbol
        self.timeframe = timeframe
        self.account = account or {}
        self.explain_status = explain_status
        self.explain_events = explain_events or []
        self.explain_order_states = explain_order_states or {}
        self.market_events = market_events or []
        self.market_event_manifest = market_event_manifest or {}

    def build(self):
        panes, series = self._build_panes_and_series()
        frames, tick_account, tick_orders = self._build_from_graph_ticks()
        account = self._build_account(tick_account)
        orders = self._build_orders(tick_orders)
        logs = self._build_logs()
        reports = self._build_reports()
        events = self._build_events()
        self._apply_charts_data(series, frames)

        return {
            "version": CHART_PROTOCOL_VERSION,
            "mode": "replay",
            "metadata": self._build_metadata(frames, account),
            "symbols": self._build_symbols(),
            "panes": panes,
            "frames": frames,
            "indicators": [],
            "series": list(series.values()),
            "orders": orders,
            "positions": [],
            "account": account,
            "events": events,
            "market_events": self._to_json_safe(copy.deepcopy(self.market_events)),
            "market_event_manifest": self._to_json_safe(copy.deepcopy(self.market_event_manifest)),
            "objects": [],
            "assets": {},
            "logs": logs,
            "reports": reports,
        }

    def _build_metadata(self, frames, account):
        metadata = sanitize_chart_config(copy.deepcopy(self.metadata))
        metadata.setdefault("mode", "tester")
        metadata.setdefault("script_settings", sanitize_chart_config(self.script_settings))
        if self.account:
            metadata.setdefault("account", {})
            metadata["account"].setdefault("currency", self.account.get("currency"))
            metadata["account"].setdefault("balance", self.account.get("balance"))
            metadata["account"].setdefault("leverage", self.account.get("leverage"))

        times = []
        for item in frames:
            if item.get("time") is not None:
                times.append(item["time"])
        for item in account:
            if item.get("time") is not None:
                times.append(item["time"])
        if times:
            metadata.setdefault("time", {})
            metadata["time"].setdefault("timezone", "UTC")
            metadata["time"].setdefault("start", min(times))
            metadata["time"].setdefault("end", max(times))
        return metadata

    def _build_symbols(self):
        ret = {}
        for symbol, data in self.symbols.items():
            ret[symbol] = self._normalize_symbol(symbol, data)
        if self.default_symbol and self.default_symbol not in ret:
            ret[self.default_symbol] = {"symbol": self.default_symbol}
        return ret

    def _normalize_symbol(self, symbol, data):
        ret = copy.deepcopy(data)
        ret.setdefault("symbol", symbol)
        ret.setdefault("asset_class", "forex")
        if "currency_base" in ret and "base_currency" not in ret:
            ret["base_currency"] = ret["currency_base"]
        if "currency_profit" in ret and "profit_currency" not in ret:
            ret["profit_currency"] = ret["currency_profit"]
        if "currency_margin" in ret and "margin_currency" not in ret:
            ret["margin_currency"] = ret["currency_margin"]
        if "trade_contract_size" in ret and "contract_size" not in ret:
            ret["contract_size"] = ret["trade_contract_size"]
        if "point" in ret and "tick_size" not in ret:
            ret["tick_size"] = ret["point"]
        if "digits" in ret:
            ret.setdefault("display", {})
            ret["display"].setdefault("price_precision", ret["digits"])
        ret.setdefault("volume_unit", "lot")
        return ret

    def _build_panes_and_series(self):
        panes = {}
        series = {}
        charts = self.script_settings.get("charts", {})
        if not isinstance(charts, dict):
            charts = {}
        if not charts:
            charts = {"price": {}}

        for chart_name, chart in charts.items():
            pane_id = self._safe_id(chart_name)
            chart = chart if isinstance(chart, dict) else {}
            panes[pane_id] = {
                "id": pane_id,
                "title": chart.get("title", chart_name),
                "type": chart.get("type", "price" if chart_name == "price" else "indicator"),
                "height": chart.get("height", 0.7 if chart_name == "price" else 0.3),
            }
            if self.default_symbol and panes[pane_id]["type"] == "price":
                panes[pane_id].setdefault("symbol", self.default_symbol)
            for item in chart.get("series", []):
                if not isinstance(item, dict) or "name" not in item:
                    continue
                series_id = self._series_id(pane_id, item["name"])
                series[series_id] = {
                    "id": series_id,
                    "pane": pane_id,
                    "symbol": item.get("symbol", self.default_symbol),
                    "type": item.get("type", "line"),
                    "name": item["name"],
                    "color": item.get("color"),
                    "line_width": item.get("line_width", item.get("width")),
                    "data": [],
                    "source": {
                        "type": "legacy_plot",
                        "chart": chart_name,
                        "name": item["name"],
                    },
                }
        if "price" not in panes:
            panes["price"] = {
                "id": "price",
                "title": self.default_symbol or "price",
                "type": "price",
                "height": 0.7,
                "symbol": self.default_symbol,
            }
        if self.account_logs or self.graph_data.get("ticks"):
            panes.setdefault("account", {
                "id": "account",
                "title": "Account",
                "type": "account",
                "height": 0.3,
            })
        return list(panes.values()), series

    def _build_from_graph_ticks(self):
        frames = []
        accounts = []
        orders = []
        ticks = self.graph_data.get("ticks", [])
        symbol = self.graph_data.get("symbol", self.default_symbol)
        for idx, tick in enumerate(ticks):
            if not isinstance(tick, dict):
                continue
            ts = self._to_timestamp(tick.get("t", tick.get("time")))
            frame = {
                "id": tick.get("id", "bar-%s" % (idx + 1)),
                "type": "bar",
                "symbol": tick.get("symbol", symbol),
                "timeframe": tick.get("timeframe", self.timeframe),
                "time": ts,
                "open": self._to_number(tick.get("o", tick.get("open"))),
                "high": self._to_number(tick.get("h", tick.get("high"))),
                "low": self._to_number(tick.get("l", tick.get("low"))),
                "close": self._to_number(tick.get("c", tick.get("close"))),
                "volume": self._to_number(tick.get("v", tick.get("volume"))),
            }
            for key in ("bid", "ask"):
                if key in tick:
                    frame[key] = self._to_number(tick.get(key))
            frames.append(frame)

            account = self._account_point_from_tick(tick, ts)
            if account:
                accounts.append(account)
            for order in tick.get("orders", []) or []:
                order_copy = copy.deepcopy(order)
                order_copy.setdefault("time", ts)
                order_copy.setdefault("symbol", frame["symbol"])
                orders.append(order_copy)
        return frames, accounts, orders

    def _build_account(self, tick_account):
        if self.account_logs:
            return [self._normalize_account_log(item) for item in self.account_logs]
        return tick_account

    def _account_point_from_tick(self, tick, ts):
        keys = ("balance", "equity", "margin", "free_margin", "profit", "margin_level")
        if not any(key in tick for key in keys):
            return None
        ret = {"time": ts, "currency": self.account.get("currency")}
        for key in keys:
            if key in tick:
                ret[key] = self._to_number(tick.get(key))
        return ret

    def _normalize_account_log(self, item):
        ret = {
            "time": self._to_timestamp(item.get("time", item.get("t"))),
            "currency": item.get("currency", self.account.get("currency")),
        }
        for key in ("balance", "equity", "margin", "free_margin", "profit", "margin_level"):
            if key in item:
                ret[key] = self._to_number(item.get(key))
        return ret

    def _build_orders(self, tick_orders):
        source = self.order_logs if self.order_logs else tick_orders
        return [self._normalize_order(item) for item in source]

    def _normalize_order(self, item):
        old_type = str(item.get("type", item.get("event", ""))).upper()
        event = self._order_event(old_type)
        side = self._order_side(old_type, item)
        ret = {
            "uid": str(item.get("uid", item.get("ticket", ""))),
            "ticket": str(item.get("ticket", item.get("uid", ""))),
            "symbol": item.get("symbol", self.default_symbol),
            "time": self._to_timestamp(item.get("time", item.get("t"))),
            "event": event,
            "side": side,
            "order_type": item.get("order_type", "MARKET"),
            "volume": self._to_number(item.get("volume")),
            "price": self._to_number(item.get("price")),
            "stop_loss": self._to_number(item.get("stop_loss")),
            "take_profit": self._to_number(item.get("take_profit")),
            "profit": self._to_number(item.get("profit")),
            "margin": self._to_number(item.get("margin")),
            "comment": item.get("comment"),
            "magic_number": item.get("magic_number"),
            "tags": item.get("tags", {}),
            "source": "legacy_order_log",
        }
        return {key: value for key, value in ret.items() if value is not None}

    def _order_event(self, old_type):
        if old_type in ("BUY", "SELL"):
            return "OPEN"
        if old_type in ("CLOSE", "CLOSE_MULTI_ORDERS"):
            return "CLOSE"
        if old_type == "MODIFY":
            return "MODIFY"
        if old_type in ("BUYLIMIT", "SELLLIMIT", "BUYSTOP", "SELLSTOP"):
            return "PENDING_CREATE"
        return old_type or "UNKNOWN"

    def _order_side(self, old_type, item):
        side = item.get("side")
        if side:
            return str(side).upper()
        if "BUY" in old_type:
            return "BUY"
        if "SELL" in old_type:
            return "SELL"
        return None

    def _build_logs(self):
        logs = []
        for item in self.print_logs:
            if isinstance(item, dict):
                log_item = copy.deepcopy(item)
                log_item.setdefault("source", "ea")
                log_item.setdefault("level", "info")
                if "time" in log_item:
                    log_item["time"] = self._to_timestamp(log_item["time"])
            else:
                log_item = {
                    "time": None,
                    "level": "info",
                    "source": "ea",
                    "message": str(item),
                    "payload": {},
                }
            logs.append(log_item)
        return logs

    def _build_reports(self):
        summary = {}
        items = {}
        for key, item in self.report.items():
            if isinstance(item, dict) and "value" in item:
                summary[key] = self._to_json_value(item.get("value"))
                items[key] = {
                    name: self._to_json_value(item.get(name))
                    for name in ("desc", "type", "precision")
                    if name in item
                }
            else:
                summary[key] = self._to_json_value(item)
                items[key] = {}
        return {"summary": summary, "items": items}

    def _build_events(self):
        events = []
        for idx, item in enumerate(self.market_events):
            if not isinstance(item, dict):
                continue
            payload = self._to_json_safe(copy.deepcopy(item))
            event_time = payload.get("event_time_ts", payload.get("event_time", payload.get("time")))
            impact = payload.get("impact")
            level = "info"
            if impact == "high":
                level = "warning"
            elif impact == "critical":
                level = "critical"
            event = {
                "id": str(payload.get("id") or "market-event-%s" % (idx + 1)),
                "time": self._to_timestamp(event_time),
                "type": "data",
                "name": payload.get("type", "market_event"),
                "level": level,
                "symbol": (payload.get("symbols") or [self.default_symbol or None])[0],
                "text": payload.get("title"),
                "payload": payload,
            }
            events.append({key: value for key, value in event.items() if value is not None})
        for idx, item in enumerate(self.explain_events):
            if not isinstance(item, dict):
                continue
            payload = self._to_json_safe(copy.deepcopy(item))
            event_type = payload.get("event_type", "ea_explain")
            event_id = payload.get("decision_id") or payload.get("id") or "explain-%s" % (idx + 1)
            event = {
                "id": str(event_id),
                "time": self._to_timestamp(payload.get("time_ts", payload.get("time"))),
                "type": "ea_explain",
                "name": event_type,
                "level": payload.get("level", "info"),
                "symbol": payload.get("symbol", self.default_symbol),
                "price": self._to_number(payload.get("price")),
                "text": payload.get("summary"),
                "payload": payload,
            }
            if payload.get("order_uid") is not None:
                event["order_uid"] = str(payload.get("order_uid"))
            if payload.get("reason_code") is not None:
                event["reason_code"] = payload.get("reason_code")
            events.append({key: value for key, value in event.items() if value is not None})
        return events

    def _apply_charts_data(self, series, frames):
        fallback_time = frames[-1]["time"] if frames else None
        for item in self.charts_data:
            if not isinstance(item, dict):
                continue
            chart_name = item.get("cn", item.get("chart", "default"))
            pane_id = self._safe_id(chart_name)
            data = item.get("data", {})
            point_time = self._to_timestamp(item.get("time", fallback_time))
            if isinstance(data, dict):
                for name, value in data.items():
                    self._append_series_point(series, pane_id, name, value, point_time)
            else:
                self._append_series_point(series, pane_id, "value", data, point_time)

    def _append_series_point(self, series, pane_id, name, value, point_time):
        series_id = self._series_id(pane_id, name)
        if series_id not in series:
            series[series_id] = {
                "id": series_id,
                "pane": pane_id,
                "symbol": self.default_symbol,
                "type": "line",
                "name": str(name),
                "data": [],
                "source": {
                    "type": "legacy_plot",
                    "chart": pane_id,
                    "name": str(name),
                },
            }
        if isinstance(value, dict):
            point = copy.deepcopy(value)
            point["time"] = self._to_timestamp(point.get("time", point_time))
            if "value" in point:
                point["value"] = self._to_number(point["value"])
        else:
            point = {"time": point_time, "value": self._to_number(value)}
        series[series_id]["data"].append(point)

    def _safe_id(self, value):
        if value is None:
            return "default"
        return str(value).replace(" ", "_")

    def _series_id(self, pane_id, name):
        return "%s.%s" % (self._safe_id(pane_id), self._safe_id(name))

    def _to_timestamp(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return self._to_json_value(value)
        if isinstance(value, datetime):
            dt = value
        else:
            dt = dateutil.parser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return self._to_json_value(dt.timestamp())

    def _to_number(self, value):
        if value is None:
            return None
        try:
            if hasattr(value, "item"):
                value = value.item()
        except ValueError:
            pass
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return self._to_json_value(value)
        try:
            return self._to_json_value(float(value))
        except (TypeError, ValueError):
            return value

    def _to_json_value(self, value):
        if isinstance(value, datetime):
            return self._to_timestamp(value)
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    def _to_json_safe(self, value):
        if isinstance(value, dict):
            return {str(key): self._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_json_safe(item) for item in value]
        return self._to_json_value(value)
