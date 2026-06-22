import copy
import json
import math
import os
import queue
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import Process, Value
from urllib.parse import urlparse

from .chart_protocol import CHART_PROTOCOL_VERSION, LegacyChartAdapter, sanitize_chart_config
from .chart_viewer import render_chart_live_html


class PixiuChartLiveState(object):
    """In-process store and broadcaster for live chart protocol deltas."""

    def __init__(self):
        self.lock = threading.RLock()
        self.clients = []
        self.replay = self._empty_replay()

    def _empty_replay(self):
        return {
            "version": CHART_PROTOCOL_VERSION,
            "mode": "live",
            "metadata": {
                "mode": "tester_live",
                "time": {"timezone": "UTC"},
            },
            "symbols": {},
            "panes": [
                {"id": "price", "title": "Live Price", "type": "price", "height": 0.7},
                {"id": "account", "title": "Account", "type": "account", "height": 0.3},
            ],
            "frames": [],
            "indicators": [],
            "series": [],
            "orders": [],
            "positions": [],
            "account": [],
            "events": [],
            "objects": [],
            "assets": {},
            "logs": [],
            "reports": {"summary": {}, "items": {}},
        }

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.replay)

    def live_html(self):
        return render_chart_live_html(self.snapshot(), title="Pixiu Live Chart")

    def add_client(self):
        client_queue = queue.Queue(maxsize=1000)
        with self.lock:
            self.clients.append(client_queue)
        return client_queue

    def remove_client(self, client_queue):
        with self.lock:
            if client_queue in self.clients:
                self.clients.remove(client_queue)

    def append_update_data(self, data):
        delta = self._delta_from_update_data(data)
        if delta is None:
            return None
        self.apply_delta(delta)
        return delta

    def append_message(self, data):
        if not isinstance(data, dict):
            return None
        if data.get("cmd") == "update_data":
            return self.append_update_data(data)
        if data.get("cmd") == "update_report":
            delta = self._delta_from_report_data(data)
            if delta is not None:
                self.apply_delta(delta)
            return delta
        return None

    def apply_delta(self, delta):
        with self.lock:
            self._merge_delta(delta)
            clients = list(self.clients)
        for client_queue in clients:
            try:
                client_queue.put_nowait(delta)
            except queue.Full:
                pass

    def _merge_delta(self, delta):
        for key in ("frames", "orders", "account", "logs", "events", "objects"):
            items = delta.get(key)
            if isinstance(items, list) and items:
                self.replay.setdefault(key, []).extend(copy.deepcopy(items))

        for symbol, value in delta.get("symbols", {}).items():
            self.replay.setdefault("symbols", {})[symbol] = copy.deepcopy(value)

        if delta.get("metadata"):
            self._deep_update(self.replay.setdefault("metadata", {}), delta["metadata"])

        if delta.get("reports", {}).get("summary"):
            self.replay.setdefault("reports", {}).setdefault("summary", {}).update(
                copy.deepcopy(delta["reports"]["summary"])
            )
        if delta.get("reports", {}).get("items"):
            self.replay.setdefault("reports", {}).setdefault("items", {}).update(
                copy.deepcopy(delta["reports"]["items"])
            )
        times = []
        for frame in self.replay.get("frames", []):
            if frame.get("time") is not None:
                times.append(frame["time"])
        for item in self.replay.get("account", []):
            if item.get("time") is not None:
                times.append(item["time"])
        if times:
            metadata = self.replay.setdefault("metadata", {})
            metadata.setdefault("time", {})
            metadata["time"].setdefault("timezone", "UTC")
            metadata["time"]["start"] = min(times)
            metadata["time"]["end"] = max(times)

    def _delta_from_update_data(self, data):
        if not isinstance(data, dict) or data.get("cmd") != "update_data":
            return None
        symbol = data.get("symbol")
        price = (data.get("data") or {}).get("price")
        if not symbol or not isinstance(price, dict):
            return None

        adapter = LegacyChartAdapter(
            graph_data={"symbol": symbol, "ticks": [price]},
            default_symbol=symbol,
            timeframe=price.get("timeframe", "m1"),
        )
        tick_replay = adapter.build()
        delta = {
            "type": "append",
            "symbols": tick_replay.get("symbols", {}),
            "frames": tick_replay.get("frames", []),
            "orders": tick_replay.get("orders", []),
            "account": tick_replay.get("account", []),
        }
        report = (data.get("data") or {}).get("report")
        summary = self._summary_from_report(report)
        if summary:
            delta["reports"] = {
                "summary": summary,
                "items": self._items_from_report(report),
            }
        metadata = {
            "test_name": data.get("group"),
            "name": data.get("name"),
        }
        message_metadata = (data.get("data") or {}).get("metadata")
        if isinstance(message_metadata, dict):
            metadata.update(sanitize_chart_config(message_metadata))
        delta["metadata"] = {key: value for key, value in metadata.items() if value is not None}
        return delta

    def _delta_from_report_data(self, data):
        report = (data.get("data") or {}).get("report", data.get("report"))
        summary = self._summary_from_report(report)
        if not summary:
            return None
        delta = {
            "type": "report",
            "reports": {
                "summary": summary,
                "items": self._items_from_report(report),
            },
            "metadata": {
                key: value for key, value in {
                    "test_name": data.get("group"),
                    "name": data.get("name"),
                    "symbol": data.get("symbol"),
                }.items() if value is not None
            },
        }
        report_text = (data.get("data") or {}).get("message")
        if report_text:
            delta["logs"] = [{
                "time": (data.get("data") or {}).get("time"),
                "level": "info",
                "source": "report",
                "message": report_text,
            }]
        return delta

    def _summary_from_report(self, report):
        if not isinstance(report, dict):
            return {}
        summary = {}
        for key, item in report.items():
            if isinstance(item, dict) and "value" in item:
                summary[key] = self._to_json_value(item.get("value"))
            else:
                summary[key] = self._to_json_value(item)
        return summary

    def _items_from_report(self, report):
        if not isinstance(report, dict):
            return {}
        items = {}
        for key, item in report.items():
            items[key] = {}
            if not isinstance(item, dict):
                continue
            for name in ("desc", "type", "precision"):
                if name in item:
                    items[key][name] = self._to_json_value(item.get(name))
        return items

    def _to_json_value(self, value):
        try:
            if hasattr(value, "item"):
                value = value.item()
        except ValueError:
            pass
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    def _deep_update(self, target, source):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_update(target[key], value)
            else:
                target[key] = copy.deepcopy(value)


class _PixiuChartRequestHandler(BaseHTTPRequestHandler):
    server_version = "PixiuChartLive/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("", "/"):
            self._send_html(self.server.live_state.live_html())
        elif parsed.path == "/snapshot":
            self._send_json(self.server.live_state.snapshot())
        elif parsed.path == "/events":
            self._send_events()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt, *args):
        return

    def _send_html(self, content):
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, content):
        body = _json_dumps(content).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_events(self):
        client_queue = self.server.live_state.add_client()
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self._write_event({"type": "snapshot", "snapshot": self.server.live_state.snapshot()})
            while self.server.running.value:
                try:
                    delta = client_queue.get(timeout=15)
                    self._write_event(delta)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.server.live_state.remove_client(client_queue)

    def _write_event(self, payload):
        body = "data: %s\n\n" % _json_dumps(payload)
        self.wfile.write(body.encode("utf-8"))
        self.wfile.flush()


class _PixiuChartHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, live_state, running):
        super(_PixiuChartHTTPServer, self).__init__(server_address, handler_class)
        self.live_state = live_state
        self.running = running


class EATesterGraphServer:
    def __init__(self, message_queue, host=None, port=None):
        self.running = Value("b", False)
        self.message_queue = message_queue
        self.host = host or os.environ.get("PIXIU_GRAPH_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("PIXIU_GRAPH_PORT", "8050"))
        self.process = None

    def __process_queue_message__(self, message, live_state):
        try:
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            if message == "stop":
                self.running.value = False
                return
            if not isinstance(message, str):
                return
            data = json.loads(message)
            live_state.append_message(data)
        except Exception:
            traceback.print_exc()

    def __message_thread__(self, message_queue, live_state, http_server):
        while self.running.value:
            try:
                message = message_queue.get(timeout=0.2)
                if message == "stop":
                    self.running.value = False
                    break
                self.__process_queue_message__(message, live_state)
            except queue.Empty:
                continue
            except Exception:
                traceback.print_exc()
        try:
            http_server.shutdown()
        except Exception:
            traceback.print_exc()

    def __run_server__(self, message_queue):
        live_state = PixiuChartLiveState()
        http_server = _PixiuChartHTTPServer(
            (self.host, self.port),
            _PixiuChartRequestHandler,
            live_state,
            self.running,
        )
        self.running.value = True
        thread = threading.Thread(
            target=self.__message_thread__,
            args=(message_queue, live_state, http_server),
            daemon=True,
        )
        thread.start()
        print("Pixiu live chart: http://%s:%s" % (self.host, self.port))
        try:
            http_server.serve_forever(poll_interval=0.2)
        finally:
            self.running.value = False
            http_server.server_close()

    def start(self):
        self.process = Process(target=self.__run_server__, args=(self.message_queue,))
        self.process.start()
        time.sleep(0.2)

    def join(self):
        if self.process is not None:
            self.process.join()

    def stop(self):
        try:
            self.message_queue.put("stop")
        except Exception:
            pass
        if self.process is not None and self.process.is_alive():
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=3)

    def send_message(self, message):
        self.message_queue.put(message)


def _json_dumps(value):
    return json.dumps(_json_safe(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _json_safe(value):
    try:
        if hasattr(value, "item"):
            value = value.item()
    except ValueError:
        pass
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
