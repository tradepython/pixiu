import copy
import csv
import hashlib
import json
import os
from datetime import date, datetime, timezone

import dateutil.parser


MARKET_EVENTS_SCHEMA = "pixiu-market-events-v1"
MARKET_EVENT_MANIFEST_VERSION = "pixiu-market-events-manifest-v1"

IMPACT_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def parse_event_time(value):
    """Parse a market-event time as a UTC epoch timestamp."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            dt = dateutil.parser.parse(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return float(dt.timestamp())


def event_time_string(value):
    ts = parse_event_time(value)
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None).isoformat(sep=" ")


class MarketEventStore(object):
    """Load, normalize, index, and query Pixiu market events."""

    def __init__(self, config=None, base_path=None, default_symbol=None):
        self.config = config if isinstance(config, dict) else {}
        self.base_path = base_path or os.getcwd()
        self.default_symbol = default_symbol
        self.enabled = bool(self.config.get("enabled", False))
        self.alignment = copy.deepcopy(self.config.get("alignment", {}) or {})
        self.show_on_chart = bool(self.config.get("show_on_chart", True))
        self.events = []
        self.manifest = {
            "version": MARKET_EVENT_MANIFEST_VERSION,
            "sources": [],
            "normalized_hash": None,
            "normalization_version": MARKET_EVENTS_SCHEMA,
        }
        if self.enabled:
            self.load_sources(self.config.get("sources", []))

    def load_sources(self, sources):
        if isinstance(sources, dict):
            sources = [sources]
        if not isinstance(sources, list):
            sources = []
        loaded = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            loaded.extend(self._load_source(source))
            self.manifest["sources"].append(self._safe_source_manifest(source))
        self.events = self._dedupe_events(loaded)
        self.events.sort(key=lambda item: (
            item.get("event_time_ts") if item.get("event_time_ts") is not None else float("inf"),
            item.get("available_time_ts") if item.get("available_time_ts") is not None else float("inf"),
            str(item.get("id", "")),
        ))
        self.manifest["normalized_hash"] = self._hash_events(self.events)
        if self.events:
            times = [item.get("event_time") for item in self.events if item.get("event_time") is not None]
            self.manifest["time_range"] = {
                "from": min(times) if times else None,
                "to": max(times) if times else None,
            }

    def _load_source(self, source):
        channel = str(source.get("channel", "file")).lower()
        if channel != "file":
            raise NotImplementedError("market_events source channel %r is not supported" % channel)
        path = source.get("path") or source.get("file")
        if not path:
            raise ValueError("market_events file source requires path")
        path = self._resolve_path(path)
        fmt = str(source.get("format") or self._guess_format(path)).lower()
        raw_events = self._load_file(path, fmt)
        ret = []
        for idx, raw in enumerate(raw_events):
            if not isinstance(raw, dict):
                continue
            ret.append(self.normalize_event(raw, source=source, index=idx))
        return ret

    def _resolve_path(self, path):
        path = os.path.expanduser(str(path))
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.base_path, path))

    def _guess_format(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jsonl", ".ndjson"):
            return "jsonl"
        if ext == ".csv":
            return "csv"
        return "json"

    def _load_file(self, path, fmt):
        if fmt == "jsonl":
            ret = []
            with open(path, "r", encoding="utf-8") as file_obj:
                for line in file_obj:
                    line = line.strip()
                    if line:
                        ret.append(json.loads(line))
            return ret
        if fmt == "json":
            with open(path, "r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("events", "market_events", "data", "rows"):
                    if isinstance(data.get(key), list):
                        return data[key]
            return []
        if fmt == "csv":
            with open(path, "r", encoding="utf-8", newline="") as file_obj:
                return list(csv.DictReader(file_obj))
        raise ValueError("unsupported market_events file format: %s" % fmt)

    def normalize_event(self, raw, source=None, index=0):
        source = source or {}
        item = copy.deepcopy(raw)
        source_id = item.get("source_id", source.get("id"))
        event_type = item.get("type", source.get("type", "custom"))
        event_time = item.get("event_time", item.get("time", item.get("published_at")))
        available_time = item.get("available_time", item.get("published_at", event_time))
        event_time_ts = parse_event_time(event_time)
        available_time_ts = parse_event_time(available_time)
        payload = item.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"value": payload}
        normalized = {
            "id": str(item.get("id") or self._build_event_id(source_id, event_type, index, item)),
            "schema": item.get("schema", MARKET_EVENTS_SCHEMA),
            "type": str(event_type),
            "event_time": event_time_string(event_time),
            "event_time_ts": event_time_ts,
            "available_time": event_time_string(available_time),
            "available_time_ts": available_time_ts,
            "source": item.get("source", source.get("channel", "file")),
            "source_id": source_id,
            "source_snapshot_time": event_time_string(
                item.get("source_snapshot_time", source.get("source_snapshot_time"))
            ),
            "title": item.get("title", item.get("name", "")),
            "summary": item.get("summary"),
            "instrument_ids": self._as_list(item.get("instrument_ids", item.get("instrument_id"))),
            "symbols": self._as_list(item.get("symbols", item.get("symbol", source.get("symbols")))),
            "venues": self._as_list(item.get("venues", item.get("venue", source.get("venues")))),
            "issuer_ids": self._as_list(item.get("issuer_ids", item.get("issuer_id"))),
            "sectors": self._as_list(item.get("sectors", item.get("sector"))),
            "currencies": self._as_list(item.get("currencies", item.get("currency", source.get("currencies")))),
            "countries": self._as_list(item.get("countries", item.get("country", source.get("countries")))),
            "asset_classes": self._as_list(item.get("asset_classes", item.get("asset_class", source.get("asset_classes")))),
            "impact": self._normalize_impact(item.get("impact")),
            "sentiment": item.get("sentiment"),
            "importance_score": self._to_float_or_none(item.get("importance_score")),
            "tags": self._as_list(item.get("tags")),
            "field_visibility": self._normalize_field_visibility(item.get("field_visibility")),
            "payload": payload,
        }
        if not normalized["symbols"] and self.default_symbol:
            normalized["symbols"] = [self.default_symbol]
        return {key: value for key, value in normalized.items() if value is not None}

    def _build_event_id(self, source_id, event_type, index, item):
        text = json.dumps(item, sort_keys=True, default=str)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        return "market-event-%s-%s-%s-%s" % (source_id or "source", event_type, index + 1, digest)

    def _as_list(self, value):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None and item != ""]
        if isinstance(value, tuple):
            return [str(item) for item in value if item is not None and item != ""]
        if isinstance(value, str) and "," in value:
            return [part.strip() for part in value.split(",") if part.strip()]
        return [str(value)]

    def _normalize_impact(self, value):
        if value is None or value == "":
            return None
        text = str(value).strip().lower()
        aliases = {
            "1": "low",
            "2": "medium",
            "3": "high",
            "4": "critical",
            "med": "medium",
            "moderate": "medium",
            "important": "high",
            "severe": "critical",
        }
        return aliases.get(text, text)

    def _to_float_or_none(self, value):
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_field_visibility(self, value):
        if not isinstance(value, dict):
            return {}
        ret = {}
        for key, time_value in value.items():
            ts = parse_event_time(time_value)
            if ts is not None:
                ret[str(key)] = ts
        return ret

    def _safe_source_manifest(self, source):
        ret = {}
        for key, value in source.items():
            key_text = str(key).lower()
            if any(part in key_text for part in ("token", "secret", "password", "authorization", "cookie")):
                ret[key] = "[REDACTED]"
            elif key_text in ("path", "file"):
                ret[key] = os.path.basename(str(value))
            else:
                ret[key] = copy.deepcopy(value)
        return ret

    def _hash_events(self, events):
        text = json.dumps(events, sort_keys=True, default=str)
        return "sha256:%s" % hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _dedupe_events(self, events):
        seen = set()
        ret = []
        for event in events:
            key = self._dedupe_key(event)
            if key in seen:
                continue
            seen.add(key)
            ret.append(event)
        return ret

    def _dedupe_key(self, event):
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        event_type = event.get("type")
        source = event.get("source_id") or event.get("source")
        if event_type == "news" and payload.get("url"):
            return (event_type, source, payload.get("url"))
        if event_type == "filing" and payload.get("accession_number"):
            return (event_type, source, tuple(event.get("issuer_ids", [])), payload.get("accession_number"))
        if event.get("id"):
            return ("id", event.get("id"))
        return (event_type, source, event.get("event_time"), event.get("title"))

    def query(self, current_time=None, instrument_id=None, instrument_ids=None, symbol=None,
              symbols=None, venue=None, issuer_id=None, sector=None, currency=None,
              country=None, asset_class=None, event_type=None, min_impact=None,
              from_time=None, to_time=None, include_future=False,
              include_hidden_fields=False):
        current_ts = parse_event_time(current_time)
        from_ts = parse_event_time(from_time)
        to_ts = parse_event_time(to_time)
        ids = self._query_values(instrument_ids)
        if instrument_id is not None:
            ids.append(str(instrument_id))
        syms = self._query_values(symbols)
        if symbol is not None:
            syms.append(str(symbol))
        ret = []
        for event in self.events:
            if not self._matches_event(event, ids, syms, venue, issuer_id, sector, currency,
                                       country, asset_class, event_type, min_impact):
                continue
            event_ts = event.get("event_time_ts")
            if from_ts is not None and (event_ts is None or event_ts < from_ts):
                continue
            if to_ts is not None and (event_ts is None or event_ts > to_ts):
                continue
            if current_ts is not None and not include_future and event_ts is not None and event_ts > current_ts:
                continue
            if not self._is_event_visible(event, current_ts, include_future):
                continue
            visible = self._visible_copy(event, current_ts, include_hidden_fields)
            if visible is not None:
                ret.append(visible)
        return ret

    def upcoming(self, current_time=None, within_seconds=3600, **kwargs):
        current_ts = parse_event_time(current_time)
        if current_ts is None:
            return []
        kwargs["from_time"] = current_ts
        kwargs["to_time"] = current_ts + float(within_seconds or 0)
        kwargs["include_future"] = True
        return self.query(current_time=current_ts, **kwargs)

    def latest(self, current_time=None, lookback_seconds=3600, **kwargs):
        current_ts = parse_event_time(current_time)
        if current_ts is None:
            return []
        kwargs["from_time"] = current_ts - float(lookback_seconds or 0)
        kwargs["to_time"] = current_ts
        kwargs["include_future"] = False
        return self.query(current_time=current_ts, **kwargs)

    def _query_values(self, value):
        return [str(item) for item in self._as_list(value)]

    def _matches_event(self, event, instrument_ids, symbols, venue, issuer_id, sector,
                       currency, country, asset_class, event_type, min_impact):
        if event_type is not None and str(event.get("type")) != str(event_type):
            return False
        if min_impact is not None:
            event_rank = IMPACT_RANK.get(str(event.get("impact", "")).lower(), 0)
            min_rank = IMPACT_RANK.get(str(min_impact).lower(), 0)
            if event_rank < min_rank:
                return False
        if instrument_ids and not self._intersects(instrument_ids, event.get("instrument_ids", [])):
            return False
        if symbols and not self._intersects(symbols, event.get("symbols", [])):
            return False
        if venue is not None and not self._contains(event.get("venues", []), venue):
            return False
        if issuer_id is not None and not self._contains(event.get("issuer_ids", []), issuer_id):
            return False
        if sector is not None and not self._contains(event.get("sectors", []), sector):
            return False
        if currency is not None and not self._contains(event.get("currencies", []), currency):
            return False
        if country is not None and not self._contains(event.get("countries", []), country):
            return False
        if asset_class is not None and not self._contains(event.get("asset_classes", []), asset_class):
            return False
        return True

    def _contains(self, values, query):
        return str(query).upper() in [str(item).upper() for item in values]

    def _intersects(self, queries, values):
        normalized = set(str(item).upper() for item in values)
        return any(str(item).upper() in normalized for item in queries)

    def _is_event_visible(self, event, current_ts, include_future):
        if current_ts is None:
            return True
        available = event.get("available_time_ts")
        if available is not None and available <= current_ts:
            return True
        if include_future:
            visibility = event.get("field_visibility", {})
            return any(ts <= current_ts for ts in visibility.values())
        return False

    def _visible_copy(self, event, current_ts, include_hidden_fields=False):
        item = copy.deepcopy(event)
        if include_hidden_fields or current_ts is None:
            return self._public_event(item)
        visibility = item.get("field_visibility", {})
        if not visibility:
            available = item.get("available_time_ts")
            if available is None or available <= current_ts:
                return self._public_event(item)
            return None
        for key, visible_ts in visibility.items():
            if visible_ts <= current_ts:
                continue
            if key in item:
                item.pop(key, None)
            payload = item.get("payload")
            if isinstance(payload, dict):
                payload.pop(key, None)
        return self._public_event(item)

    def _public_event(self, event):
        event.pop("event_time_ts", None)
        event.pop("available_time_ts", None)
        return event

    def chart_events(self):
        if not self.show_on_chart:
            return []
        ret = []
        for event in self.events:
            ts = event.get("event_time_ts")
            if ts is None:
                continue
            level = "info"
            if event.get("impact") in ("high", "critical"):
                level = "warning" if event.get("impact") == "high" else "critical"
            ret.append({
                "id": event.get("id"),
                "time": ts,
                "type": "data",
                "name": event.get("type"),
                "level": level,
                "symbol": (event.get("symbols") or [self.default_symbol or None])[0],
                "text": event.get("title"),
                "payload": self._public_event(copy.deepcopy(event)),
            })
        return ret

    def replay_events(self):
        return [self._public_event(copy.deepcopy(item)) for item in self.events]

    def replay_manifest(self):
        return copy.deepcopy(self.manifest)
