import math
from datetime import datetime
from pathlib import Path


DEFAULT_COLORS = {
    "background": "#f7efe3",
    "panel": "#fffaf2",
    "plot": "#fffdf8",
    "grid": "#eadfce",
    "axis": "#5b4636",
    "text": "#1f2933",
    "muted": "#6b7280",
    "price": "#111827",
    "line": "#315f72",
    "up": "#0f8b5f",
    "down": "#b8323a",
    "band": "#f6d365",
}


def render_ea_explain_chart_png(chart, output_path, width=1200, height=720):
    """Render a pixiu-explain-chart-v1 payload to a standalone PNG image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise ImportError("render_ea_explain_chart_png requires Pillow. Install it with `pip install Pillow`.") from exc

    chart = _unwrap_chart(chart)
    if not isinstance(chart, dict):
        raise ValueError("chart must be an object")
    if chart.get("success") is False:
        raise ValueError("cannot render failed explain chart: %s" % chart.get("error", "unknown"))

    width = max(640, int(width))
    height = max(420, int(height))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font_regular = _load_font(ImageFont, 15)
    font_small = _load_font(ImageFont, 12)
    font_title = _load_font(ImageFont, 24)
    font_metric = _load_font(ImageFont, 14)

    image = Image.new("RGB", (width, height), DEFAULT_COLORS["background"])
    draw = ImageDraw.Draw(image)

    margin = 34
    header_h = 76
    metrics_w = 280 if chart.get("metrics") else 0
    plot = {
        "x0": margin,
        "y0": header_h + 18,
        "x1": width - margin - metrics_w - (18 if metrics_w else 0),
        "y1": height - margin - 54,
    }
    if plot["x1"] - plot["x0"] < 360:
        metrics_w = 0
        plot["x1"] = width - margin

    title = chart.get("title") or chart.get("chart_type") or "EA Explain Chart"
    subtitle = " | ".join(str(item) for item in (chart.get("symbol"), chart.get("time")) if item)
    draw.text((margin, 24), str(title), fill=DEFAULT_COLORS["text"], font=font_title)
    if subtitle:
        draw.text((margin, 54), subtitle, fill=DEFAULT_COLORS["muted"], font=font_regular)

    draw.rounded_rectangle(
        (plot["x0"], plot["y0"], plot["x1"], plot["y1"]),
        radius=14,
        fill=DEFAULT_COLORS["plot"],
        outline="#d7c9b6",
        width=1,
    )

    values = _collect_price_values(chart)
    if not values:
        values = [0.0, 1.0]
    y_min, y_max = _range_with_padding(values)
    price_precision = _chart_price_precision(chart)
    y_for = lambda value: _scale_y(value, y_min, y_max, plot["y0"] + 18, plot["y1"] - 18)
    frames = _chart_frames(chart)
    x_for = lambda index, count: _scale_x(index, count, plot["x0"] + 22, plot["x1"] - 22)
    x_for_time = lambda value, fallback=None: _x_for_time(value, frames, plot, x_for, fallback=fallback)
    objects = _chart_objects(chart)

    _draw_price_axis(draw, plot, y_min, y_max, y_for, font_small, precision=price_precision)
    _draw_candles(draw, frames, plot, x_for, y_for)
    _draw_object_areas(draw, objects, plot, x_for_time, y_for)
    _draw_objects(draw, objects, plot, x_for_time, y_for, font_small)
    _draw_series(draw, chart.get("series", []), plot, x_for, x_for_time, y_for)
    _draw_current_price(draw, chart.get("price"), plot, y_for, font_small, precision=price_precision)
    _draw_legend(draw, chart, frames, chart.get("series", []), plot, font_small, precision=price_precision)
    _draw_time_axis(draw, frames, plot, x_for, font_small, chart=chart)
    _draw_metrics(draw, chart.get("metrics"), width, height, margin, metrics_w, font_regular, font_metric)

    description = chart.get("summary") or chart.get("description")
    if description:
        draw.text((margin, height - margin + 8), _shorten(str(description), 150), fill=DEFAULT_COLORS["muted"], font=font_small)

    image.save(output_path, "PNG")
    return str(output_path)


def _unwrap_chart(chart):
    if isinstance(chart, dict) and "chart" in chart and isinstance(chart.get("chart"), dict):
        return chart["chart"]
    return chart


def _load_font(ImageFont, size):
    for name in ("Avenir.ttc", "Helvetica.ttc", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _to_number(value):
    try:
        if value is None:
            return None
        value = float(value)
        if math.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass
    return None


def _collect_price_values(chart):
    values = []
    for key in ("price", "open_price", "close_price"):
        value = _to_number(chart.get(key))
        if value is not None:
            values.append(value)
    for item in chart.get("objects", []) or []:
        if not isinstance(item, dict):
            continue
        for key in ("price", "price_from", "price_to", "low", "high"):
            value = _to_number(item.get(key))
            if value is not None:
                values.append(value)
        for point in item.get("points", []) or []:
            if isinstance(point, dict):
                value = _to_number(point.get("price", point.get("value")))
                if value is not None:
                    values.append(value)
    for item in chart.get("zones", []) or []:
        if not isinstance(item, dict):
            continue
        for key in ("price", "price_from", "price_to", "low", "high"):
            value = _to_number(item.get(key))
            if value is not None:
                values.append(value)
    for series in chart.get("series", []) or []:
        if not isinstance(series, dict):
            continue
        for point in series.get("data", []) or []:
            if isinstance(point, dict):
                value = _to_number(point.get("value", point.get("price")))
            else:
                value = _to_number(point)
            if value is not None:
                values.append(value)
    for frame in _chart_frames(chart):
        for key in ("open", "high", "low", "close"):
            value = _to_number(frame.get(key))
            if value is not None:
                values.append(value)
    return values


def _chart_price_precision(chart):
    axis = chart.get("axis", {}) if isinstance(chart.get("axis", {}), dict) else {}
    price_axis = axis.get("price", {}) if isinstance(axis.get("price", {}), dict) else {}
    precision = price_axis.get("precision", chart.get("price_precision"))
    try:
        if precision is not None:
            return max(0, min(10, int(precision)))
    except (TypeError, ValueError):
        pass
    return None


def _chart_frames(chart):
    frames = chart.get("frames", chart.get("candles", chart.get("ohlc", [])))
    if not isinstance(frames, list):
        return []
    return [item for item in frames if isinstance(item, dict)]


def _chart_objects(chart):
    objects = []
    for item in chart.get("objects", []) or []:
        if isinstance(item, dict):
            objects.append(item)
    for item in chart.get("zones", []) or []:
        if isinstance(item, dict):
            zone = dict(item)
            zone.setdefault("type", "rectangle")
            zone.setdefault("id", zone.get("name", "zone-%s" % (len(objects) + 1)))
            objects.append(zone)
    for item in chart.get("markers", []) or []:
        if isinstance(item, dict):
            marker = dict(item)
            marker.setdefault("type", "marker")
            objects.append(marker)
    for item in chart.get("price_lines", []) or []:
        if isinstance(item, dict):
            line = dict(item)
            line.setdefault("type", "price_line")
            objects.append(line)
    for item in chart.get("drawings", []) or []:
        if isinstance(item, dict):
            objects.append(item)
    for item in chart.get("annotations", []) or []:
        if isinstance(item, dict):
            text = dict(item)
            text.setdefault("type", "text")
            objects.append(text)
    return objects


def _range_with_padding(values):
    y_min = min(values)
    y_max = max(values)
    if y_min == y_max:
        pad = abs(y_min) * 0.001 or 1.0
    else:
        pad = (y_max - y_min) * 0.14
    return y_min - pad, y_max + pad


def _scale_y(value, y_min, y_max, top, bottom):
    value = _to_number(value)
    if value is None:
        return None
    if y_max == y_min:
        return (top + bottom) / 2
    return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)


def _scale_x(index, count, left, right):
    if count <= 1:
        return (left + right) / 2
    return left + index / (count - 1) * (right - left)


def _x_for_time(value, frames, plot, x_for, fallback=None):
    if not frames:
        return fallback if fallback is not None else (plot["x0"] + plot["x1"]) / 2
    if value is None:
        return fallback if fallback is not None else x_for(len(frames) - 1, len(frames))
    target = _time_key(value)
    best_index = None
    best_delta = None
    for index, frame in enumerate(frames):
        frame_key = _time_key(frame.get("time", frame.get("t")))
        if target is not None and frame_key is not None:
            delta = abs(frame_key - target)
        else:
            delta = 0 if str(frame.get("time", frame.get("t"))) == str(value) else None
        if delta is None:
            continue
        if best_delta is None or delta < best_delta:
            best_index = index
            best_delta = delta
    if best_index is None:
        return fallback if fallback is not None else x_for(len(frames) - 1, len(frames))
    return x_for(best_index, len(frames))


def _time_key(value):
    number = _to_number(value)
    if number is not None and number > 100000:
        return number
    parsed = _parse_frame_time(value)
    if parsed is None:
        return None
    try:
        return parsed.timestamp()
    except Exception:
        return None


def _draw_price_axis(draw, plot, y_min, y_max, y_for, font, precision=None):
    for idx in range(6):
        value = y_min + (y_max - y_min) * idx / 5
        y = y_for(value)
        draw.line((plot["x0"], y, plot["x1"], y), fill=DEFAULT_COLORS["grid"], width=1)
        label = _format_price(value, precision=precision)
        draw.text((plot["x1"] - 78, y - 7), label, fill=DEFAULT_COLORS["axis"], font=font)


def _draw_candles(draw, frames, plot, x_for, y_for):
    if not frames:
        return
    candle_w = max(3, min(14, (plot["x1"] - plot["x0"] - 44) / max(1, len(frames)) * 0.58))
    for idx, frame in enumerate(frames):
        open_price = _to_number(frame.get("open", frame.get("o")))
        high_price = _to_number(frame.get("high", frame.get("h")))
        low_price = _to_number(frame.get("low", frame.get("l")))
        close_price = _to_number(frame.get("close", frame.get("c")))
        if None in (open_price, high_price, low_price, close_price):
            continue
        x = x_for(idx, len(frames))
        y_open = y_for(open_price)
        y_high = y_for(high_price)
        y_low = y_for(low_price)
        y_close = y_for(close_price)
        if None in (y_open, y_high, y_low, y_close):
            continue
        up = close_price >= open_price
        color = DEFAULT_COLORS["up"] if up else DEFAULT_COLORS["down"]
        body_top = min(y_open, y_close)
        body_bottom = max(y_open, y_close)
        draw.line((x, y_high, x, y_low), fill=color, width=1)
        draw.rounded_rectangle(
            (x - candle_w / 2, body_top, x + candle_w / 2, max(body_top + 1, body_bottom)),
            radius=1,
            fill=color,
            outline=color,
        )


def _draw_time_axis(draw, frames, plot, x_for, font, chart=None):
    if not frames:
        return
    axis_y = plot["y1"] + 18
    label_y = axis_y + 8
    draw.line((plot["x0"] + 1, axis_y, plot["x1"] - 1, axis_y), fill="#d7c9b6", width=1)
    labels = _time_axis_labels(frames, chart=chart)
    for index, label in labels:
        x = x_for(index, len(frames))
        draw.line((x, axis_y, x, axis_y + 5), fill=DEFAULT_COLORS["axis"], width=1)
        text_w = _text_width(draw, label, font)
        label_x = max(plot["x0"] + 4, min(x - text_w / 2, plot["x1"] - text_w - 4))
        draw.text((label_x, label_y), label, fill=DEFAULT_COLORS["axis"], font=font)


def _time_axis_labels(frames, chart=None):
    count = len(frames)
    if count <= 0:
        return []
    target = min(4, max(2, count // 16 + 1))
    indexes = []
    for idx in range(target):
        index = round(idx * (count - 1) / max(1, target - 1))
        if index not in indexes:
            indexes.append(index)
    labels = []
    for index in indexes:
        raw_time = frames[index].get("time", frames[index].get("t"))
        labels.append((index, _format_axis_time(raw_time, _parse_frame_time(raw_time), chart=chart)))
    return labels


def _parse_frame_time(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    number = _to_number(value)
    if number is not None and number > 100000:
        try:
            return datetime.utcfromtimestamp(number)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ").replace("Z", "")
    if "+" in text:
        text = text.split("+", 1)[0].strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def _format_axis_time(raw_value, parsed, chart=None):
    if parsed is None:
        return _shorten(str(raw_value), 19)
    fmt = _axis_time_format(chart)
    if fmt:
        return parsed.strftime(fmt)
    return parsed.strftime("%Y-%m-%d %H:%M")


def _axis_time_format(chart):
    if not isinstance(chart, dict):
        return None
    axis = chart.get("axis", {}) if isinstance(chart.get("axis", {}), dict) else {}
    time_axis = axis.get("time", {}) if isinstance(axis.get("time", {}), dict) else {}
    fmt = time_axis.get("format")
    if not isinstance(fmt, str):
        return None
    replacements = (
        ("YYYY", "%Y"),
        ("MM", "%m"),
        ("DD", "%d"),
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
    )
    for src, dst in replacements:
        fmt = fmt.replace(src, dst)
    return fmt


def _text_width(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except Exception:
        return len(str(text)) * 7


def _draw_object_areas(draw, objects, plot, x_for_time, y_for):
    for item in objects or []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).lower()
        if item_type not in ("price_band", "band", "rectangle", "price_range", "time_range"):
            continue
        bounds = _object_bounds(item, plot, x_for_time, y_for)
        if bounds is None:
            continue
        x1, y1, x2, y2 = bounds
        color = _style_color(item, DEFAULT_COLORS["band"])
        fill = _style_fill_color(item, color)
        outline = _style_border_color(item, color)
        draw.rectangle((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)), fill=fill, outline=outline, width=1)


def _draw_objects(draw, objects, plot, x_for_time, y_for, font):
    for item in objects or []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).lower()
        if item_type in ("horizontal_line", "price_line"):
            y = y_for(item.get("price"))
            if y is None:
                continue
            color = _style_color(item, DEFAULT_COLORS["line"])
            _draw_line(draw, (plot["x0"] + 1, y, plot["x1"] - 1, y), color, item)
            label = _object_label(item)
            if label:
                draw.text((plot["x0"] + 12, y - 18), str(label), fill=color, font=font)
        elif item_type == "vertical_line":
            x = x_for_time(item.get("time"))
            color = _style_color(item, DEFAULT_COLORS["line"])
            _draw_line(draw, (x, plot["y0"] + 1, x, plot["y1"] - 1), color, item)
            label = _object_label(item)
            if label:
                draw.text((x + 6, plot["y0"] + 10), str(label), fill=color, font=font)
        elif item_type == "marker":
            y = y_for(item.get("price", item.get("value")))
            if y is None:
                continue
            color = _style_color(item, _marker_default_color(item))
            x = x_for_time(item.get("time"), fallback=plot["x0"] + 28)
            _draw_marker(draw, x, y, color, item.get("side"), shape=item.get("shape"))
            label = _object_label(item)
            if label:
                _draw_inline_label(draw, x + 12, y - 8, str(label), color, font, plot)
        elif item_type == "text":
            y = y_for(item.get("price", item.get("value")))
            if y is None:
                continue
            x = x_for_time(item.get("time"), fallback=plot["x0"] + 28)
            color = _style_color(item, DEFAULT_COLORS["text"])
            label = _object_label(item)
            if label:
                _draw_text_label(draw, x, y, str(label), color, font, plot)
        elif item_type in ("trend_line", "ray", "extended_line", "path", "channel"):
            points = _object_points(item, x_for_time, y_for)
            if len(points) < 2:
                continue
            color = _style_color(item, DEFAULT_COLORS["line"])
            draw.line(points, fill=color, width=int(_style_value(item, "line_width", 2) or 2))
            label = _object_label(item)
            if label:
                _draw_inline_label(draw, points[-1][0] + 6, points[-1][1] - 8, str(label), color, font, plot)


def _object_bounds(item, plot, x_for_time, y_for):
    points = item.get("points", [])
    if isinstance(points, list) and len(points) >= 2 and all(isinstance(point, dict) for point in points[:2]):
        x1 = x_for_time(points[0].get("time"), fallback=plot["x0"] + 1)
        y1 = y_for(points[0].get("price", points[0].get("value")))
        x2 = x_for_time(points[1].get("time"), fallback=plot["x1"] - 1)
        y2 = y_for(points[1].get("price", points[1].get("value")))
    else:
        x1 = x_for_time(item.get("time_from", item.get("start_time")), fallback=plot["x0"] + 1)
        x2 = x_for_time(item.get("time_to", item.get("end_time")), fallback=plot["x1"] - 1)
        y1 = y_for(item.get("price_from", item.get("low")))
        y2 = y_for(item.get("price_to", item.get("high")))
    if None in (x1, y1, x2, y2):
        return None
    return x1, y1, x2, y2


def _object_points(item, x_for_time, y_for):
    ret = []
    for point in item.get("points", []) or []:
        if not isinstance(point, dict):
            continue
        y = y_for(point.get("price", point.get("value")))
        if y is None:
            continue
        x = x_for_time(point.get("time"))
        ret.append((x, y))
    return ret


def _draw_series(draw, series_list, plot, x_for, x_for_time, y_for):
    for series in series_list or []:
        if not isinstance(series, dict):
            continue
        series_type = str(series.get("type", "line")).lower()
        if series_type == "candlestick":
            _draw_candles(draw, series.get("data", []), plot, x_for, y_for)
            continue
        data = series.get("data", []) or []
        points = []
        for idx, point in enumerate(data):
            if isinstance(point, dict):
                value = point.get("value", point.get("price"))
            else:
                value = point
            y = y_for(value)
            if y is None:
                continue
            x = x_for_time(point.get("time"), fallback=x_for(idx, len(data))) if isinstance(point, dict) else x_for(idx, len(data))
            points.append((x, y))
        if not points:
            continue
        color = _style_color(series, series.get("color") or DEFAULT_COLORS["line"])
        if series_type == "histogram":
            for x, y in points:
                draw.rectangle((x - 3, y, x + 3, plot["y1"] - 1), fill=color)
        elif series_type in ("area", "baseline") and len(points) > 1:
            area_points = [(points[0][0], plot["y1"] - 1)] + points + [(points[-1][0], plot["y1"] - 1)]
            draw.polygon(area_points, fill=_soft_color(color))
            draw.line(points, fill=color, width=int(series.get("line_width", 2) or 2), joint="curve")
        elif len(points) == 1 or series_type in ("point", "scatter"):
            for x, y in points:
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color, outline="#ffffff", width=2)
        else:
            draw.line(points, fill=color, width=int(series.get("line_width", 2) or 2), joint="curve")


def _draw_current_price(draw, price, plot, y_for, font, precision=None):
    y = y_for(price)
    if y is None:
        return
    color = DEFAULT_COLORS["price"]
    _draw_dashed_line(draw, (plot["x0"] + 1, y, plot["x1"] - 1, y), color, width=2, dash=8)
    label = "Price %s" % _format_price(price, precision=precision)
    draw.rounded_rectangle((plot["x1"] - 106, y - 13, plot["x1"] - 8, y + 13), radius=6, fill=color)
    draw.text((plot["x1"] - 100, y - 8), label, fill="#ffffff", font=font)


def _draw_metrics(draw, metrics, width, height, margin, metrics_w, font, font_metric):
    if not metrics or not metrics_w:
        return
    x0 = width - margin - metrics_w
    y0 = 96
    x1 = width - margin
    y1 = height - margin - 34
    draw.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=DEFAULT_COLORS["panel"], outline="#d7c9b6", width=1)
    draw.text((x0 + 18, y0 + 18), "Metrics", fill=DEFAULT_COLORS["text"], font=font)
    y = y0 + 52
    for key, value in list(metrics.items())[:16]:
        label = str(key).replace("_", " ").title()
        draw.text((x0 + 18, y), label, fill=DEFAULT_COLORS["muted"], font=font_metric)
        draw.text((x0 + 150, y), _format_metric(value), fill=DEFAULT_COLORS["text"], font=font_metric)
        y += 28
        if y > y1 - 24:
            break


def _draw_legend(draw, chart, frames, series_list, plot, font, precision=None):
    legend = chart.get("legend", {}) if isinstance(chart.get("legend", {}), dict) else {}
    if legend.get("enabled", True) is False:
        return
    parts = []
    if frames:
        frame = frames[-1]
        o = _format_price(frame.get("open", frame.get("o")), precision=precision)
        h = _format_price(frame.get("high", frame.get("h")), precision=precision)
        l = _format_price(frame.get("low", frame.get("l")), precision=precision)
        c = _format_price(frame.get("close", frame.get("c")), precision=precision)
        parts.append(("OHLC %s %s %s %s" % (o, h, l, c), DEFAULT_COLORS["text"]))
    for series in series_list or []:
        if not isinstance(series, dict):
            continue
        name = series.get("name") or series.get("id")
        if not name:
            continue
        parts.append((str(name), _style_color(series, series.get("color") or DEFAULT_COLORS["line"])))
        if len(parts) >= 4:
            break
    if not parts:
        return
    x = plot["x0"] + 12
    y = plot["y0"] + 10
    for text, color in parts:
        text = _shorten(text, 34)
        draw.text((x, y), text, fill=color, font=font)
        x += _text_width(draw, text, font) + 18
        if x > plot["x1"] - 120:
            break


def _style_color(item, default):
    style = item.get("style") if isinstance(item, dict) else None
    color = None
    if isinstance(style, dict):
        color = style.get("color")
    color = item.get("color", color) if isinstance(item, dict) else color
    return _normalize_color(color or default)


def _style_fill_color(item, default):
    style = item.get("style") if isinstance(item, dict) else None
    if isinstance(style, dict):
        return _normalize_color(style.get("fill_color", _soft_color(default)))
    return _soft_color(default)


def _style_border_color(item, default):
    style = item.get("style") if isinstance(item, dict) else None
    if isinstance(style, dict):
        return _normalize_color(style.get("border_color", style.get("color", default)))
    return default


def _style_value(item, key, default=None):
    style = item.get("style") if isinstance(item, dict) else None
    if isinstance(style, dict) and key in style:
        return style.get(key)
    return item.get(key, default)


def _object_label(item):
    return item.get("label") or item.get("title") or item.get("text") or item.get("name")


def _marker_default_color(item):
    side = str(item.get("side", "")).lower()
    shape = str(item.get("shape", "")).lower()
    if side == "buy" or shape in ("arrow_up", "triangle_up"):
        return DEFAULT_COLORS["up"]
    if side == "sell" or shape in ("arrow_down", "triangle_down"):
        return DEFAULT_COLORS["down"]
    return DEFAULT_COLORS["line"]


def _draw_inline_label(draw, x, y, text, color, font, plot):
    text_w = _text_width(draw, text, font)
    x = max(plot["x0"] + 4, min(x, plot["x1"] - text_w - 4))
    y = max(plot["y0"] + 4, min(y, plot["y1"] - 16))
    draw.text((x, y), text, fill=color, font=font)


def _draw_text_label(draw, x, y, text, color, font, plot):
    text_w = _text_width(draw, text, font)
    x = max(plot["x0"] + 4, min(x, plot["x1"] - text_w - 14))
    y = max(plot["y0"] + 22, min(y, plot["y1"] - 6))
    draw.rounded_rectangle((x - 5, y - 19, x + text_w + 9, y + 3), radius=5, fill="#fffaf2", outline=color, width=1)
    draw.text((x, y - 16), text, fill=color, font=font)


def _normalize_color(value):
    value = str(value)
    if value.startswith("rgba(") or value.startswith("rgb("):
        try:
            parts = value[value.find("(") + 1:value.rfind(")")].split(",")
            red = int(float(parts[0].strip()))
            green = int(float(parts[1].strip()))
            blue = int(float(parts[2].strip()))
            alpha = float(parts[3].strip()) if value.startswith("rgba(") and len(parts) > 3 else 1.0
            if alpha < 1.0:
                red = int(red * alpha + 255 * (1.0 - alpha))
                green = int(green * alpha + 255 * (1.0 - alpha))
                blue = int(blue * alpha + 255 * (1.0 - alpha))
            return "#%02x%02x%02x" % (max(0, min(255, red)), max(0, min(255, green)), max(0, min(255, blue)))
        except Exception:
            return "#f5e6c8"
    if value.startswith("#") and len(value) in (7, 9):
        return value[:7]
    return value


def _soft_color(color):
    color = _normalize_color(color)
    if not color.startswith("#") or len(color) != 7:
        return "#f5e6c8"
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    red = int(red * 0.18 + 255 * 0.82)
    green = int(green * 0.18 + 255 * 0.82)
    blue = int(blue * 0.18 + 255 * 0.82)
    return "#%02x%02x%02x" % (red, green, blue)


def _draw_line(draw, coords, color, item):
    style = item.get("style") if isinstance(item, dict) else {}
    line_style = style.get("line_style") if isinstance(style, dict) else item.get("line_style")
    if line_style == "dashed":
        _draw_dashed_line(draw, coords, color, width=2, dash=8)
    else:
        draw.line(coords, fill=color, width=2)


def _draw_dashed_line(draw, coords, color, width=1, dash=6):
    x0, y0, x1, y1 = coords
    if abs(y1 - y0) < 1:
        x = x0
        while x < x1:
            draw.line((x, y0, min(x + dash, x1), y1), fill=color, width=width)
            x += dash * 2
        return
    draw.line(coords, fill=color, width=width)


def _draw_marker(draw, x, y, color, side=None, shape=None):
    shape = str(shape or "").lower()
    side = str(side or "").lower()
    if shape in ("circle", "dot"):
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline="#ffffff", width=2)
    elif shape == "square":
        draw.rectangle((x - 6, y - 6, x + 6, y + 6), fill=color, outline="#ffffff", width=2)
    elif shape == "diamond":
        draw.polygon([(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)], fill=color)
    elif shape in ("arrow_down", "triangle_down") or side == "sell":
        points = [(x, y + 7), (x - 7, y - 6), (x + 7, y - 6)]
        draw.polygon(points, fill=color)
    else:
        points = [(x, y - 7), (x - 7, y + 6), (x + 7, y + 6)]
        draw.polygon(points, fill=color)


def _format_price(value, precision=None):
    value = _to_number(value)
    if value is None:
        return "-"
    if precision is not None:
        return (("%." + str(precision) + "f") % value).rstrip("0").rstrip(".")
    return ("%.6f" % value).rstrip("0").rstrip(".")


def _format_metric(value):
    number = _to_number(value)
    if number is None:
        return _shorten(str(value), 16)
    if float(number).is_integer() and abs(number) >= 1:
        return str(int(number))
    if abs(number) >= 100:
        return "%.2f" % number
    if abs(number) >= 1:
        return "%.4f" % number
    return "%.6f" % number


def _shorten(value, max_len):
    return value if len(value) <= max_len else value[:max_len - 1] + "..."
