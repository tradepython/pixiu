import copy
import traceback
from datetime import timezone

import dateutil

from pixiu.api import OrderCommand
from pixiu.api.v1 import DataScope


class ScenarioEngine:
    DEFAULT_PHASE = "pre_tick"
    PHASES = ("pre_tick", "post_order_processing", "post_tick")

    def __init__(self, config=None):
        self.raw_config = copy.deepcopy(config or {})
        self.initial_state = copy.deepcopy(self.raw_config.get("initial_state", {}))
        self.events = [self._normalize_event(event, idx) for idx, event in enumerate(self.raw_config.get("events", []))]
        self.executed_events = set()
        self.base_spread_point = None

    @property
    def enabled(self):
        return bool(self.initial_state or self.events)

    def reset(self, tester):
        self.executed_events = set()
        self.base_spread_point = tester.context.spread_point

    def apply_initial_state(self, tester):
        if not self.enabled:
            return
        account_overrides = self.initial_state.get("account_overrides", {})
        if isinstance(account_overrides, dict):
            tester.context.account.update(account_overrides)
        for order_spec in self.initial_state.get("orders", []):
            tester.seed_order(order_spec,
                              affect_report=bool(order_spec.get("count_in_report", False)),
                              affect_logs=bool(order_spec.get("write_log", False)))
        for data_spec in self._iter_initial_data_specs():
            self._save_data(tester, data_spec)

    def before_tick(self, tester):
        if not self.enabled:
            return
        self._reset_tick_state(tester)
        self._run_phase(tester, "pre_tick")

    def after_order_processing(self, tester):
        if not self.enabled:
            return
        self._run_phase(tester, "post_order_processing")

    def after_tick(self, tester):
        if not self.enabled:
            return
        self._run_phase(tester, "post_tick")

    def _normalize_event(self, event, idx):
        normalized = copy.deepcopy(event or {})
        normalized["id"] = str(normalized.get("id", f"scenario_event_{idx}"))
        normalized["action"] = str(normalized.get("action", "")).strip()
        normalized["phase"] = normalized.get("phase", self.DEFAULT_PHASE)
        if normalized["phase"] not in self.PHASES:
            normalized["phase"] = self.DEFAULT_PHASE
        normalized["params"] = copy.deepcopy(normalized.get("params", {}))
        normalized["once"] = bool(normalized.get("once", self._default_once(normalized["action"])))
        normalized["at_ts"] = self._parse_time(normalized.get("at"))
        normalized["from_ts"] = self._parse_time(normalized.get("from"))
        normalized["to_ts"] = self._parse_time(normalized.get("to"))
        normalized["at_tick"] = self._parse_int(normalized.get("at_tick"))
        normalized["from_tick"] = self._parse_int(normalized.get("from_tick"))
        normalized["to_tick"] = self._parse_int(normalized.get("to_tick"))
        return normalized

    def _default_once(self, action):
        return action not in ("override_spread", "mutate_tick", "price_path")

    def _parse_time(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        parsed = dateutil.parser.parse(value, ignoretz=True)
        return parsed.replace(tzinfo=timezone.utc).timestamp()

    def _parse_int(self, value):
        if value is None:
            return None
        return int(value)

    def _reset_tick_state(self, tester):
        if self.base_spread_point is not None:
            tester.context.spread_point = self.base_spread_point
            tester.context.spread_calculated = abs(self.base_spread_point * tester.get_symbol_properties(tester.context.symbol)["point"])

    def _run_phase(self, tester, phase):
        for event in self.events:
            if event["phase"] != phase:
                continue
            if not self._event_matches(tester, event):
                continue
            if event["once"] and event["id"] in self.executed_events:
                continue
            self._apply_event(tester, event)
            if event["once"]:
                self.executed_events.add(event["id"])

    def _event_matches(self, tester, event):
        tick_index = tester.context.tick_current_index
        tick_time = tester.current_time()
        exact_tick = event["at_tick"]
        exact_time = event["at_ts"]
        if exact_tick is not None:
            return tick_index == exact_tick
        if exact_time is not None:
            return abs(tick_time - exact_time) < 0.000001
        tick_in_range = self._in_range(tick_index, event["from_tick"], event["to_tick"])
        time_in_range = self._in_range(tick_time, event["from_ts"], event["to_ts"])
        if event["from_tick"] is not None or event["to_tick"] is not None:
            return tick_in_range
        if event["from_ts"] is not None or event["to_ts"] is not None:
            return time_in_range
        return False

    def _in_range(self, value, start, end):
        if start is not None and value < start:
            return False
        if end is not None and value > end:
            return False
        return start is not None or end is not None

    def _apply_event(self, tester, event):
        action = event["action"]
        params = event["params"]
        try:
            if action == "mutate_tick":
                self._mutate_tick(tester, params)
            elif action == "price_path":
                self._price_path(tester, event, params)
            elif action == "override_spread":
                self._override_spread(tester, params)
            elif action == "place_order":
                tester.seed_order(params,
                                  affect_report=bool(params.get("count_in_report", True)),
                                  affect_logs=bool(params.get("write_log", True)),
                                  current_time=tester.current_time())
            elif action == "close_order":
                self._close_order(tester, params)
            elif action == "cancel_order":
                self._cancel_order(tester, params)
            elif action == "save_data":
                self._save_data(tester, params)
            else:
                tester.write_log(f"Scenario event skipped: unsupported action={action}", type="ea")
                return
            tester.write_log(f"Scenario event applied: id={event['id']}, action={action}", type="ea")
        except Exception:
            traceback.print_exc()
            tester.write_log(f"Scenario event failed: id={event['id']}, action={action}", type="ea")

    def _mutate_tick(self, tester, params):
        tick_index = tester.context.tick_current_index
        tick_info = tester.context.tick_info
        rename = {"open": "o", "high": "h", "close": "c", "low": "l", "volume": "v", "ask": "a", "bid": "b"}
        fields = ("o", "h", "c", "l", "v", "a", "b")
        for field in fields:
            if field in params:
                tick_info[field][tick_index] = params[field]
        for source, target in rename.items():
            if source in params:
                tick_info[target][tick_index] = params[source]
        deltas = params.get("delta", {})
        if isinstance(deltas, dict):
            for source, delta in deltas.items():
                target = rename.get(source, source)
                if target in fields:
                    tick_info[target][tick_index] = tick_info[target][tick_index] + delta

    def _price_path(self, tester, event, params):
        tick_index = tester.context.tick_current_index
        tick_info = tester.context.tick_info
        path_index, path_total, path_ratio = self._price_path_position(tester, event)
        point = tester.get_symbol_properties(tester.context.symbol)["point"]

        start_bid = params.get("start_bid", params.get("start", params.get("price")))
        if start_bid is None:
            start_bid = tick_info["b"][tick_index] or tick_info["c"][tick_index]
        start_bid = float(start_bid)

        end_bid = params.get("end_bid", params.get("end"))
        if end_bid is not None and path_total > 0:
            bid = start_bid + (float(end_bid) - start_bid) * path_ratio
        else:
            step = params.get("step")
            if step is None:
                step = float(params.get("step_points", 0)) * point
            bid = start_bid + float(step) * path_index

        spread_point = params.get("spread_point", params.get("spread_points", tester.context.spread_point))
        spread = float(spread_point) * point
        ask = params.get("ask")
        if ask is None:
            ask = bid + spread
        ask = float(ask)

        close_price = float(params.get("close", bid))
        open_price = float(params.get("open", close_price))
        high_offset = float(params.get("high_offset", spread))
        low_offset = float(params.get("low_offset", spread))
        high_price = float(params.get("high", max(open_price, close_price, ask) + abs(high_offset)))
        low_price = float(params.get("low", min(open_price, close_price, bid) - abs(low_offset)))

        tick_info["o"][tick_index] = open_price
        tick_info["h"][tick_index] = high_price
        tick_info["l"][tick_index] = low_price
        tick_info["c"][tick_index] = close_price
        tick_info["b"][tick_index] = bid
        tick_info["a"][tick_index] = ask
        if "volume" in params:
            tick_info["v"][tick_index] = params["volume"]
        elif "v" in params:
            tick_info["v"][tick_index] = params["v"]

        tester.context.spread_point = float(spread_point)
        tester.context.spread_calculated = abs(spread)

    def _price_path_position(self, tester, event):
        tick_index = tester.context.tick_current_index
        if event["from_tick"] is not None:
            start = event["from_tick"]
            end = event["to_tick"] if event["to_tick"] is not None else start
            path_index = max(0, tick_index - start)
            path_total = max(0, end - start)
            path_ratio = path_index / path_total if path_total else 0
            return path_index, path_total, path_ratio

        tick_time = tester.current_time()
        if event["from_ts"] is not None:
            start = event["from_ts"]
            end = event["to_ts"] if event["to_ts"] is not None else start
            path_total = max(0, end - start)
            path_index = max(0, tick_time - start)
            path_ratio = path_index / path_total if path_total else 0
            return path_index, path_total, path_ratio

        return 0, 0, 0

    def _override_spread(self, tester, params):
        spread_point = params.get("spread_point", params.get("value"))
        if spread_point is None:
            return
        spread_point = float(spread_point)
        tester.context.spread_point = spread_point
        tester.context.spread_calculated = abs(spread_point * tester.get_symbol_properties(tester.context.symbol)["point"])
        tick_index = tester.context.tick_current_index
        bid = tester.context.tick_info["b"][tick_index]
        if bid == 0:
            bid = tester.context.tick_info["c"][tick_index]
            tester.context.tick_info["b"][tick_index] = bid
        tester.context.tick_info["a"][tick_index] = bid + tester.context.spread_calculated

    def _close_order(self, tester, params):
        order_uid = self._resolve_order_uid(tester, params)
        if order_uid is None:
            return
        order = tester.get_order(order_uid)
        if order is None:
            return
        volume = params.get("volume", order["volume"])
        price = params.get("price")
        comment = params.get("comment", "scenario_close")
        tester.close_order(order_uid, volume, price, comment=comment, tags=params.get("tags"))

    def _cancel_order(self, tester, params):
        order_uid = self._resolve_order_uid(tester, params)
        if order_uid is None:
            return
        order = tester.get_order(order_uid)
        if order is None:
            return
        tester.close_order(order_uid, order["volume"], 0, comment=params.get("comment", "scenario_cancel"), tags=params.get("tags"))

    def _iter_initial_data_specs(self):
        for key in ("data", "persistent_data", "runtime_data"):
            value = self.initial_state.get(key, [])
            if isinstance(value, list):
                for item in value:
                    yield item
            elif isinstance(value, dict):
                for scope, scope_items in value.items():
                    if isinstance(scope_items, dict):
                        for name, data in scope_items.items():
                            yield {"scope": scope, "name": name, "data": data}

    def _save_data(self, tester, params):
        scope = self._resolve_data_scope(params.get("scope", DataScope.EA))
        name = params.get("name")
        if not name:
            return
        data = params.get("data")
        data_format = params.get("format", "json")
        tester.save_data(name, data, scope, data_format)

    def _resolve_data_scope(self, scope):
        if isinstance(scope, int):
            return scope
        scope_name = str(scope).upper()
        scopes = {
            "EA": DataScope.EA,
            "EA_VERSION": DataScope.EA_VERSION,
            "ACCOUNT": DataScope.ACCOUNT,
            "EA_SETTINGS": DataScope.EA_SETTINGS,
            "ACCOUNT_EA": DataScope.ACCOUNT_EA,
        }
        return scopes.get(scope_name, DataScope.EA)

    def _resolve_order_uid(self, tester, params):
        order_uid = params.get("order_uid")
        if order_uid is not None:
            return str(order_uid)
        ticket = params.get("ticket")
        if ticket is None:
            return None
        for uid, order in tester.context.orders["data"].items():
            if str(order.get("ticket")) == str(ticket):
                return str(uid)
        return None


def resolve_order_command(order_spec):
    cmd = order_spec.get("cmd")
    if cmd:
        return str(cmd).upper()
    kind = str(order_spec.get("kind", "market")).lower()
    side = str(order_spec.get("side", "")).lower()
    side_map = {
        "buy": OrderCommand.BUY,
        "sell": OrderCommand.SELL,
        "buy_limit": OrderCommand.BUYLIMIT,
        "buylimit": OrderCommand.BUYLIMIT,
        "sell_limit": OrderCommand.SELLLIMIT,
        "selllimit": OrderCommand.SELLLIMIT,
        "buy_stop": OrderCommand.BUYSTOP,
        "buystop": OrderCommand.BUYSTOP,
        "sell_stop": OrderCommand.SELLSTOP,
        "sellstop": OrderCommand.SELLSTOP,
    }
    if side in side_map:
        return side_map[side]
    if kind == "market":
        return OrderCommand.BUY if side != "sell" else OrderCommand.SELL
    if kind == "pending":
        raise ValueError("pending order requires side like buy_limit/sell_stop")
    raise ValueError(f"unsupported order spec: {order_spec}")
