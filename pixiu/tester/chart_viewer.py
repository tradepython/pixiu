import html
import json
from pathlib import Path


def render_chart_replay_html(replay, title=None):
    """Render a self-contained browser report for a pixiu-chart-v1 replay."""
    title = title or _default_title(replay)
    replay_json = _safe_script_json(replay)
    safe_title = html.escape(title)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --panel: #fffaf0;
      --ink: #1f2933;
      --muted: #6b7280;
      --line: #d8c7a7;
      --up: #0f8b5f;
      --down: #c24132;
      --accent: #315f72;
      --gold: #b7791f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 10%, rgba(183, 121, 31, .18), transparent 28rem),
        linear-gradient(135deg, #f8efe0 0%, #e8f0ed 100%);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .shell {{ max-width: 1240px; margin: 0 auto; padding: 28px; }}
    header {{
      display: flex;
      gap: 20px;
      align-items: flex-end;
      justify-content: space-between;
      padding: 20px 0 26px;
    }}
    h1 {{ margin: 0; font-size: clamp(28px, 4vw, 54px); letter-spacing: -.04em; }}
    .subhead {{ color: var(--muted); font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 18px; }}
    .card {{
      background: rgba(255, 250, 240, .86);
      border: 1px solid rgba(91, 70, 42, .18);
      border-radius: 22px;
      box-shadow: 0 24px 70px rgba(44, 35, 23, .10);
      overflow: hidden;
    }}
    .card h2 {{ margin: 0 0 8px; font-size: 18px; }}
    .card-body {{ padding: 18px; }}
    .price-card {{ grid-column: span 12; }}
    .side-card {{ grid-column: span 12; }}
    .orders-card {{ grid-column: span 12; }}
    .logs-card {{ grid-column: span 12; }}
    #price-chart svg, #account-chart svg {{ cursor: crosshair; user-select: none; }}
    #price-chart svg.dragging, #account-chart svg.dragging {{ cursor: grabbing; }}
    .crosshair {{ pointer-events: none; }}
    .crosshair line {{ stroke: #334155; stroke-width: 1; stroke-dasharray: 5 5; opacity: .72; }}
    .crosshair text {{ fill: #1f2933; font-size: 12px; paint-order: stroke; stroke: #fff7e7; stroke-width: 3px; }}
    .order-marker {{ pointer-events: auto; }}
    .order-marker .stem {{ stroke-width: 1.2; stroke-linecap: round; opacity: .72; }}
    .order-marker .dot {{ stroke: #fff7e7; stroke-width: 1.6; filter: drop-shadow(0 1px 2px rgba(31, 41, 51, .24)); }}
    .order-marker .label-bg {{ fill: rgba(255, 250, 240, .9); stroke: rgba(91, 70, 42, .22); stroke-width: .8; }}
    .order-marker .label {{ fill: #1f2933; font-size: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 700; }}
    .order-marker.focused .dot {{ stroke: #111827; stroke-width: 2.4; filter: drop-shadow(0 0 8px rgba(183, 121, 31, .58)); }}
    .order-marker.focused .label-bg {{ stroke: #b7791f; stroke-width: 1.4; fill: rgba(255, 247, 231, .98); }}
    .order-tooltip {{
      position: fixed;
      z-index: 30;
      max-width: min(340px, calc(100vw - 28px));
      padding: 12px 14px;
      border: 1px solid rgba(91, 70, 42, .22);
      border-radius: 14px;
      background: rgba(31, 41, 51, .94);
      color: #fffaf0;
      box-shadow: 0 18px 48px rgba(31, 41, 51, .22);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      pointer-events: none;
    }}
    .order-tooltip[hidden] {{ display: none; }}
    .order-tooltip strong {{ color: #f6dca7; }}
    .order-tooltip .muted {{ color: rgba(255, 250, 240, .68); }}
    svg {{ display: block; width: 100%; height: auto; background: linear-gradient(180deg, #fffdf7, #fff7e7); }}
    .metric-row, .order-row, .log-row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 9px 0;
      border-bottom: 1px solid rgba(91, 70, 42, .12);
      font-size: 14px;
    }}
    .metric-row:last-child, .order-row:last-child, .log-row:last-child {{ border-bottom: 0; }}
    .order-row {{
      cursor: pointer;
      border-radius: 12px;
      padding-left: 8px;
      padding-right: 8px;
    }}
    .order-row:hover, .order-row:focus {{
      background: rgba(49, 95, 114, .09);
      outline: 1px solid rgba(49, 95, 114, .18);
    }}
    .order-row.focused {{
      background: rgba(183, 121, 31, .12);
      outline: 1px solid rgba(183, 121, 31, .32);
    }}
    .report-overview {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    .metric-card {{
      min-width: 0;
      padding: 12px;
      border: 1px solid rgba(91, 70, 42, .14);
      border-radius: 16px;
      background: rgba(255, 255, 255, .46);
    }}
    .metric-card .label {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .metric-card strong {{
      display: block;
      margin-top: 5px;
      font-size: 18px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }}
    details.report-details {{
      border-top: 1px solid rgba(91, 70, 42, .14);
      padding-top: 10px;
    }}
    details.report-details summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 700;
      list-style-position: inside;
      margin-bottom: 10px;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 0 18px;
      max-height: 360px;
      overflow: auto;
      padding-right: 6px;
    }}
    .log-list {{
      max-height: 420px;
      overflow: auto;
      padding-right: 6px;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
    }}
    button, select, input[type="range"], input[type="number"] {{
      accent-color: var(--accent);
    }}
    button, select, input[type="number"] {{
      border: 1px solid rgba(91, 70, 42, .22);
      border-radius: 999px;
      background: #fff7e7;
      color: var(--ink);
      padding: 7px 12px;
      font: inherit;
    }}
    button, select {{
      cursor: pointer;
    }}
    button:hover, select:hover {{ background: #f4e8d4; }}
    input[type="number"] {{ width: 86px; }}
    input[type="range"] {{ min-width: 180px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 9px;
      background: #e7dac3;
      color: #563d1d;
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .empty {{ color: var(--muted); font-style: italic; padding: 16px 0; }}
    @media (max-width: 860px) {{
      .shell {{ padding: 16px; }}
      header {{ display: block; }}
      .side-card, .orders-card {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>{title}</h1>
        <div class="subhead" id="meta"></div>
      </div>
      <div class="badge" id="version"></div>
    </header>
    <main class="grid">
      <section class="card price-card" tabindex="0" aria-label="Chart area">
        <div class="card-body">
          <h2>Price Replay</h2>
          <div class="subhead" id="price-summary"></div>
          <div class="toolbar">
            <label>Timeframe
              <select id="timeframe-select">
                <option value="tick" selected>tick</option>
                <option value="m1">1m</option>
                <option value="h1">1hour</option>
                <option value="d1">1day</option>
              </select>
            </label>
            <button type="button" id="pan-left">Left</button>
            <button type="button" id="zoom-in">Zoom In</button>
            <button type="button" id="zoom-out">Zoom Out</button>
            <button type="button" id="pan-right">Right</button>
            <button type="button" id="reset-view">Reset</button>
            <label><input id="show-account" type="checkbox" checked> Account</label>
            <input id="window-range" type="range" min="0" max="0" value="0">
            <span class="badge" id="window-label"></span>
          </div>
        </div>
        <div id="price-chart"></div>
        <div id="account-chart"></div>
        <div id="order-tooltip" class="order-tooltip" hidden></div>
      </section>
      <aside class="card side-card">
        <div class="card-body">
          <h2>Report</h2>
          <div id="report"></div>
        </div>
      </aside>
      <section class="card orders-card">
        <div class="card-body">
          <h2>Orders</h2>
          <div class="toolbar">
            <select id="orders-scope">
              <option value="visible">Visible window</option>
              <option value="all">All orders</option>
            </select>
            <label>Page size <input id="orders-page-size" type="number" min="1" max="1000" value="50"></label>
            <button type="button" id="orders-prev">Prev</button>
            <button type="button" id="orders-next">Next</button>
            <span class="badge" id="orders-count"></span>
          </div>
          <div id="orders"></div>
        </div>
      </section>
      <section class="card logs-card">
        <div class="card-body">
          <h2>Logs</h2>
          <div id="logs"></div>
        </div>
      </section>
    </main>
  </div>
  <script id="pixiu-chart-data" type="application/json">{replay_json}</script>
  <script>
    const replay = JSON.parse(document.getElementById("pixiu-chart-data").textContent);
    const rawFrameSource = replay.frames || [];
    let activeTimeframe = "tick";
    let activeFrames = [];
    const account = replay.account || [];
    const orders = replay.orders || [];
    const series = replay.series || [];
    const reports = (replay.reports && replay.reports.summary) || {{}};
    const metadata = replay.metadata || {{}};

    const fmtTime = (t) => {{
      if (t === null || t === undefined) return "";
      return new Date(Number(t) * 1000).toISOString().replace("T", " ").slice(0, 19);
    }};
    const num = (v) => Number.isFinite(Number(v)) ? Number(v) : null;
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
    const compact = (v) => {{
      const n = num(v);
      if (n === null) return esc(v);
      return Math.abs(n) >= 100 ? n.toFixed(2) : n.toFixed(5).replace(/0+$/, "").replace(/\\.$/, "");
    }};
    const rawFrames = normalizeFrames(rawFrameSource);
    activeFrames = aggregateFramesForTimeframe(rawFrames, activeTimeframe);

    document.getElementById("version").textContent = replay.version || "unknown";
    document.getElementById("meta").textContent = [
      metadata.script_name,
      metadata.script_version,
      metadata.account && metadata.account.currency,
      metadata.time ? `${{fmtTime(metadata.time.start)}} - ${{fmtTime(metadata.time.end)}}` : null
    ].filter(Boolean).join(" · ");

    const maxInitialBars = 1500;
    const minWindowBars = 3;
    const chartStates = {{}};
    let activeCursor = null;
    const view = {{
      start: activeFrames.length > maxInitialBars ? activeFrames.length - maxInitialBars : 0,
      end: activeFrames.length,
      ordersScope: "visible",
      orderPage: 1,
      orderPageSize: 50,
      showAccount: true,
      isDragging: false,
      dragStartX: 0,
      dragStartViewStart: 0,
      dragStartViewEnd: 0,
      dragStartWidth: 1,
      focusOrderKey: null
    }};

    function scale(values, minPx, maxPx) {{
      let min = Infinity, max = -Infinity;
      for (const raw of values) {{
        const v = num(raw);
        if (v === null) continue;
        if (v < min) min = v;
        if (v > max) max = v;
      }}
      if (!Number.isFinite(min) || !Number.isFinite(max)) {{ min = 0; max = 1; }}
      if (min === max) {{ min -= 1; max += 1; }}
      const fn = (v) => maxPx - ((Number(v) - min) / (max - min)) * (maxPx - minPx);
      fn.min = min;
      fn.max = max;
      return fn;
    }}

    function clampNumber(value, min, max) {{
      return Math.max(min, Math.min(max, Number(value)));
    }}

    const maxRenderBars = 1800;
    let renderScheduled = false;

    function scheduleRender() {{
      if (renderScheduled) return;
      renderScheduled = true;
      requestAnimationFrame(() => {{
        renderScheduled = false;
        renderAll();
      }});
    }}

    function bucketTime(time, timeframe) {{
      const ts = Number(time);
      if (timeframe === "d1") return Math.floor(ts / 86400) * 86400;
      if (timeframe === "h1") return Math.floor(ts / 3600) * 3600;
      return Math.floor(ts / 60) * 60;
    }}

    function frameValue(frame, canonical, alias) {{
      const value = frame[canonical] !== undefined ? frame[canonical] : frame[alias];
      return num(value);
    }}

    function normalizeFrames(sourceFrames) {{
      const ret = [];
      for (const frame of sourceFrames) {{
        if (!frame || typeof frame !== "object") continue;
        const time = num(frame.time !== undefined ? frame.time : frame.t);
        const open = frameValue(frame, "open", "o");
        const high = frameValue(frame, "high", "h");
        const low = frameValue(frame, "low", "l");
        const close = frameValue(frame, "close", "c");
        if (time === null || open === null || high === null || low === null || close === null) continue;
        const priceValues = [open, high, low, close];
        ret.push({{
          ...frame,
          time,
          open,
          high: Math.max(...priceValues),
          low: Math.min(...priceValues),
          close,
          volume: num(frame.volume !== undefined ? frame.volume : frame.v) ?? 0
        }});
      }}
      return ret.sort((a, b) => Number(a.time) - Number(b.time));
    }}

    function normalizeFrame(frame, index, timeframe, startTime, endTime) {{
      return {{
        ...frame,
        __idx: index,
        __sourceStart: startTime === undefined ? Number(frame.time) : Number(startTime),
        __sourceEnd: endTime === undefined ? Number(frame.time) : Number(endTime),
        timeframe
      }};
    }}

    function aggregateFramesForTimeframe(sourceFrames, timeframe) {{
      if (timeframe === "tick") return sourceFrames.map((frame, index) => normalizeFrame(frame, index, timeframe));
      const ret = [];
      let current = null;
      for (const frame of sourceFrames) {{
        const bucket = bucketTime(frame.time, timeframe);
        if (!current || current.time !== bucket) {{
          current = {{
            ...frame,
            time: bucket,
            timeframe,
            open: frame.open,
            high: frame.high,
            low: frame.low,
            close: frame.close,
            volume: Number(frame.volume || 0),
            __sourceStart: Number(frame.time),
            __sourceEnd: Number(frame.time)
          }};
          ret.push(current);
          continue;
        }}
        current.high = Math.max(Number(current.high), Number(frame.high), Number(frame.open), Number(frame.close));
        current.low = Math.min(Number(current.low), Number(frame.low), Number(frame.open), Number(frame.close));
        current.close = frame.close;
        current.volume += Number(frame.volume || 0);
        current.__sourceEnd = Number(frame.time);
      }}
      return ret.map((frame, index) => normalizeFrame(frame, index, timeframe, frame.__sourceStart, frame.__sourceEnd));
    }}

    function resetViewToEnd() {{
      const size = Math.min(maxInitialBars, activeFrames.length);
      view.start = Math.max(0, activeFrames.length - size);
      view.end = activeFrames.length;
      view.orderPage = 1;
    }}

    function setTimeframe(timeframe) {{
      activeTimeframe = timeframe;
      activeFrames = aggregateFramesForTimeframe(rawFrames, timeframe);
      resetViewToEnd();
      scheduleRender();
    }}

    function clampView() {{
      if (!activeFrames.length) {{ view.start = 0; view.end = 0; return; }}
      const size = Math.max(minWindowBars, Math.min(activeFrames.length, view.end - view.start));
      view.start = Math.max(0, Math.min(view.start, activeFrames.length - size));
      view.end = Math.min(activeFrames.length, view.start + size);
    }}

    function setWindow(start, size) {{
      view.start = Math.round(start);
      view.end = view.start + Math.round(size);
      clampView();
      view.orderPage = 1;
      scheduleRender();
    }}

    function zoom(factor, anchorRatio = 0.5) {{
      const size = Math.max(minWindowBars, view.end - view.start);
      const nextSize = Math.max(minWindowBars, Math.min(activeFrames.length, Math.round(size * factor)));
      const anchor = view.start + size * anchorRatio;
      setWindow(anchor - nextSize * anchorRatio, nextSize);
    }}

    function pan(factor) {{
      const size = Math.max(minWindowBars, view.end - view.start);
      setWindow(view.start + size * factor, size);
    }}

    function panBars(deltaBars) {{
      const size = Math.max(minWindowBars, view.end - view.start);
      setWindow(view.start + deltaBars, size);
    }}

    function visibleFrames() {{
      return activeFrames.slice(view.start, view.end);
    }}

    function visibleSourceTimeRange() {{
      const vf = visibleFrames();
      if (!vf.length) return [null, null];
      return [Number(vf[0].__sourceStart), Number(vf[vf.length - 1].__sourceEnd)];
    }}

    function visibleOrders() {{
      if (view.ordersScope === "all") return orders;
      const [startTime, endTime] = visibleSourceTimeRange();
      if (startTime === null) return [];
      return orders.filter(o => Number(o.time) >= startTime && Number(o.time) <= endTime);
    }}

    function pagedOrders() {{
      const items = visibleOrders().slice().reverse();
      const pageSize = Math.max(1, Math.min(1000, Number(view.orderPageSize) || 50));
      const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
      view.orderPage = Math.max(1, Math.min(totalPages, Number(view.orderPage) || 1));
      const start = (view.orderPage - 1) * pageSize;
      return {{
        items: items.slice(start, start + pageSize),
        total: items.length,
        totalPages,
        pageSize
      }};
    }}

    function visibleAccount() {{
      const [startTime, endTime] = visibleSourceTimeRange();
      if (startTime === null) return account;
      return account.filter(a => Number(a.time) >= startTime && Number(a.time) <= endTime);
    }}

    function frameIndexForTime(time) {{
      const t = Number(time);
      if (!activeFrames.length || !Number.isFinite(t)) return -1;
      let lo = 0, hi = activeFrames.length - 1;
      while (lo <= hi) {{
        const mid = (lo + hi) >> 1;
        const start = Number(activeFrames[mid].__sourceStart);
        const end = Number(activeFrames[mid].__sourceEnd);
        if (t >= start && t <= end) return mid;
        if (end < t) lo = mid + 1;
        else hi = mid - 1;
      }}
      if (lo <= 0) return 0;
      if (lo >= activeFrames.length) return activeFrames.length - 1;
      const before = Number(activeFrames[lo - 1].__sourceEnd);
      const after = Number(activeFrames[lo].__sourceStart);
      return Math.abs(t - before) <= Math.abs(after - t) ? lo - 1 : lo;
    }}

    function displayFrames(vf) {{
      if (vf.length <= maxRenderBars) return vf;
      const step = Math.ceil(vf.length / maxRenderBars);
      const ret = [];
      for (let i = 0; i < vf.length; i += step) {{
        const bucket = vf.slice(i, i + step);
        let high = -Infinity, low = Infinity, volume = 0;
        for (const item of bucket) {{
          high = Math.max(high, Number(item.high));
          low = Math.min(low, Number(item.low));
          volume += Number(item.volume || 0);
        }}
        ret.push({{
          ...bucket[Math.floor(bucket.length / 2)],
          __idx: bucket[Math.floor(bucket.length / 2)].__idx,
          __sourceStart: bucket[0].__sourceStart,
          __sourceEnd: bucket[bucket.length - 1].__sourceEnd,
          open: bucket[0].open,
          high,
          low,
          close: bucket[bucket.length - 1].close,
          volume
        }});
      }}
      return ret;
    }}

    function displayPoints(items) {{
      if (items.length <= maxRenderBars) return items;
      const step = Math.ceil(items.length / maxRenderBars);
      return items.filter((_, index) => index % step === 0);
    }}

    function latestPointByVisibleFrame(items, valueKeys) {{
      const rows = [];
      let itemIndex = 0;
      const sorted = items.slice().sort((a, b) => Number(a.time) - Number(b.time));
      for (let frameIndex = view.start; frameIndex < view.end; frameIndex++) {{
        const frame = activeFrames[frameIndex];
        if (!frame) continue;
        let latest = null;
        while (itemIndex < sorted.length && Number(sorted[itemIndex].time) <= Number(frame.__sourceEnd)) {{
          if (Number(sorted[itemIndex].time) >= Number(frame.__sourceStart)) latest = sorted[itemIndex];
          itemIndex += 1;
        }}
        if (latest) rows.push({{...latest, __idx: frameIndex}});
      }}
      const filtered = valueKeys
        ? rows.filter(row => valueKeys.some(key => num(row[key]) !== null))
        : rows;
      return displayPoints(filtered);
    }}

    function makeXIndexScale(leftIndex, rightIndex, leftPx, rightPx) {{
      if (!Number.isFinite(leftIndex) || !Number.isFinite(rightIndex) || leftIndex === rightIndex) {{
        return () => (leftPx + rightPx) / 2;
      }}
      return (index) => leftPx + ((Number(index) - leftIndex) / (rightIndex - leftIndex)) * (rightPx - leftPx);
    }}

    function axisLabels(y, x, pad, formatFn = compact) {{
      return Array.from({{length: 5}}, (_, i) => {{
        const value = y.max - i * ((y.max - y.min) / 4);
        const yy = y(value);
        return `<line x1="${{pad.l}}" x2="${{x}}" y1="${{yy}}" y2="${{yy}}" stroke="#eadcc5" />
          <text x="${{x + 6}}" y="${{yy + 4}}" fill="#6b7280" font-size="12">${{formatFn(value)}}</text>`;
      }}).join("");
    }}

    function formatAxisTime(time) {{
      const d = new Date(Number(time) * 1000);
      const iso = d.toISOString();
      if (activeTimeframe === "d1") return iso.slice(0, 10);
      if (activeTimeframe === "h1") return iso.slice(11, 13) + ":00";
      return iso.slice(11, 16);
    }}

    function shouldLabelFrame(time, previousBucket) {{
      const d = new Date(Number(time) * 1000);
      if (activeTimeframe === "d1") return String(d.getUTCFullYear()) + "-" + d.getUTCMonth() + "-" + d.getUTCDate();
      if (activeTimeframe === "h1") return String(d.getUTCFullYear()) + "-" + d.getUTCMonth() + "-" + d.getUTCDate() + "-" + d.getUTCHours();
      const minute = d.getUTCMinutes();
      if (minute % 15 !== 0) return null;
      return String(d.getUTCFullYear()) + "-" + d.getUTCMonth() + "-" + d.getUTCDate() + "-" + d.getUTCHours() + "-" + minute;
    }}

    function xAxisLabels(vf, xForIndex, y, pad, chartHeight) {{
      let lastX = -Infinity;
      let previousBucket = null;
      const labels = [];
      for (let i = 0; i < vf.length; i++) {{
        const bucket = shouldLabelFrame(vf[i].time, previousBucket);
        if (!bucket || bucket === previousBucket) continue;
        previousBucket = bucket;
        const x = xForIndex(view.start + i);
        if (x - lastX < 70) continue;
        lastX = x;
        labels.push(`<line x1="${{x}}" x2="${{x}}" y1="${{pad.t}}" y2="${{chartHeight - pad.b}}" stroke="#f0e2cb" />
          <text x="${{x}}" y="${{chartHeight - 12}}" text-anchor="middle" fill="#6b7280" font-size="12">${{formatAxisTime(vf[i].time)}}</text>`);
      }}
      return labels.join("");
    }}

    function orderPriceValues(orderItems) {{
      return orderItems.flatMap(order => [order.price, order.stop_loss, order.take_profit])
        .map(value => num(value))
        .filter(value => value !== null && value !== 0);
    }}

    function orderLabelText(order) {{
      const raw = order.ticket || order.uid || order.id || "";
      const text = String(raw);
      if (!text) return "";
      return text.length > 12 ? `${{text.slice(0, 4)}}…${{text.slice(-5)}}` : text;
    }}

    function orderKey(order) {{
      const index = Math.max(0, orders.indexOf(order));
      return [
        order.ticket || order.uid || order.id || "order",
        order.event || "",
        order.side || "",
        order.time || "",
        index
      ].map(v => String(v).replace(/[^a-zA-Z0-9_.:-]/g, "_")).join("__");
    }}

    function findOrderByKey(key) {{
      return orders.find(order => orderKey(order) === key) || null;
    }}

    function orderTooltipHtml(order) {{
      const id = order.ticket || order.uid || order.id || "";
      const rows = [
        ["Operation", `${{order.event || ""}} ${{order.side || ""}} #${{id}}`],
        ["Time", fmtTime(order.time)],
        ["Price", compact(order.price)],
        ["Volume", compact(order.volume)],
        ["Profit", compact(order.profit)],
        ["SL / TP", `${{compact(order.stop_loss)}} / ${{compact(order.take_profit)}}`],
        ["Comment", order.comment || ""]
      ].filter(([, value]) => value !== "" && value !== " / ");
      const tags = order.tags && Object.keys(order.tags).length ? JSON.stringify(order.tags) : "";
      const body = rows.map(([label, value]) =>
        `<div><span class="muted">${{esc(label)}}:</span> <strong>${{esc(value)}}</strong></div>`
      ).join("");
      return `${{body}}${{tags ? `<div class="muted" style="margin-top:6px">${{esc(tags)}}</div>` : ""}}`;
    }}

    function positionOrderTooltip(event) {{
      const tooltip = document.getElementById("order-tooltip");
      if (!tooltip || tooltip.hidden) return;
      const margin = 14;
      const rect = tooltip.getBoundingClientRect();
      let left = event.clientX + margin;
      let top = event.clientY + margin;
      if (left + rect.width > window.innerWidth - margin) left = event.clientX - rect.width - margin;
      if (top + rect.height > window.innerHeight - margin) top = event.clientY - rect.height - margin;
      tooltip.style.left = `${{Math.max(margin, left)}}px`;
      tooltip.style.top = `${{Math.max(margin, top)}}px`;
    }}

    function showOrderTooltip(orderKeyValue, event) {{
      const order = findOrderByKey(orderKeyValue);
      const tooltip = document.getElementById("order-tooltip");
      if (!order || !tooltip) return;
      tooltip.innerHTML = orderTooltipHtml(order);
      tooltip.hidden = false;
      positionOrderTooltip(event);
    }}

    function hideOrderTooltip() {{
      const tooltip = document.getElementById("order-tooltip");
      if (tooltip) tooltip.hidden = true;
    }}

    function renderOrderMarker(order, x, yCoord, color, pad, chartHeight) {{
      const isBuy = order.side === "BUY";
      const isClose = order.event === "CLOSE";
      const label = orderLabelText(order);
      const key = orderKey(order);
      const focusedClass = view.focusOrderKey === key ? " focused" : "";
      const plotTop = pad.t;
      const plotBottom = chartHeight - pad.b;
      const markerY = clampNumber(yCoord, plotTop, plotBottom);
      const direction = isBuy ? -1 : 1;
      const preferredLabelY = markerY + direction * (isClose ? 18 : 21);
      const labelY = clampNumber(preferredLabelY, plotTop + 10, plotBottom - 10);
      const stemEnd = clampNumber(markerY + direction * (isClose ? 8 : 11), plotTop, plotBottom);
      const labelWidth = Math.max(22, label.length * 6.1 + 10);
      const labelX = Math.max(62, Math.min(1070 - labelWidth, x - labelWidth / 2));
      const textY = labelY + 3.5;
      const markerSize = isClose ? 4 : 4.8;
      const outOfRange = Math.abs(Number(yCoord) - markerY) > 0.5;
      const shape = isClose
        ? `<rect class="dot" x="${{x - markerSize}}" y="${{markerY - markerSize}}" width="${{markerSize * 2}}" height="${{markerSize * 2}}" rx="2" fill="${{color}}" />`
        : `<circle class="dot" cx="${{x}}" cy="${{markerY}}" r="${{markerSize}}" fill="${{color}}" />`;
      const labelNode = label
        ? `<rect class="label-bg" x="${{labelX}}" y="${{labelY - 8}}" width="${{labelWidth}}" height="15" rx="7.5" />
           <text class="label" x="${{labelX + labelWidth / 2}}" y="${{textY}}" text-anchor="middle">${{esc(label)}}</text>`
        : "";
      return `<g class="order-marker${{focusedClass}}" data-order-key="${{esc(key)}}" aria-label="${{esc(order.event)}} ${{esc(order.side)}} #${{esc(order.ticket || order.uid || "")}}">
        ${{outOfRange ? `<line class="stem" x1="${{x}}" x2="${{x}}" y1="${{markerY}}" y2="${{yCoord < plotTop ? plotTop : plotBottom}}" stroke="${{color}}" stroke-dasharray="3 3" />` : ""}}
        <line class="stem" x1="${{x}}" x2="${{x}}" y1="${{markerY}}" y2="${{stemEnd}}" stroke="${{color}}" />
        ${{shape}}
        ${{labelNode}}
      </g>`;
    }}

    function updateWindowControls() {{
      const size = view.end - view.start;
      const maxStart = Math.max(0, activeFrames.length - size);
      const slider = document.getElementById("window-range");
      slider.max = String(maxStart);
      slider.value = String(view.start);
      slider.disabled = activeFrames.length <= size;
      document.getElementById("window-label").textContent = activeFrames.length
        ? `${{view.start + 1}}-${{view.end}} / ${{activeFrames.length}}`
        : "0 / 0";
      const vf = visibleFrames();
      document.getElementById("price-summary").textContent = `${{vf.length}} visible / ${{activeFrames.length}} ${{activeTimeframe}} bars · ${{rawFrames.length}} raw bars · ${{orders.length}} order events · ${{series.length}} series`;
    }}

    function renderPriceChart() {{
      const el = document.getElementById("price-chart");
      const vf = visibleFrames();
      if (!vf.length) {{ el.innerHTML = '<div class="card-body empty">No price frames.</div>'; return; }}
      const df = displayFrames(vf);
      const w = 1180, h = 430, pad = {{l: 58, r: 76, t: 18, b: 36}};
      const [startTime, endTime] = visibleSourceTimeRange();
      const leftIndex = view.start;
      const rightIndex = Math.max(view.start + 1, view.end - 1);
      const xForIndex = makeXIndexScale(leftIndex, rightIndex, pad.l, w - pad.r);
      const visibleOrderItems = visibleOrders();
      const y = scale(df.flatMap(f => [f.high, f.low, f.open, f.close]).concat(orderPriceValues(visibleOrderItems)), pad.t, h - pad.b);
      const cw = Math.max(2, Math.min(14, (w - pad.l - pad.r) / Math.max(1, df.length) * .58));
      const grid = axisLabels(y, w - pad.r, pad);
      const timeGrid = xAxisLabels(vf, xForIndex, y, pad, h);
      const candles = df.map((f) => {{
        const x = xForIndex(f.__idx), yo = y(f.open), yc = y(f.close), yh = y(f.high), yl = y(f.low);
        const up = Number(f.close) >= Number(f.open);
        const color = up ? "var(--up)" : "var(--down)";
        return `<line x1="${{x}}" x2="${{x}}" y1="${{yh}}" y2="${{yl}}" stroke="${{color}}" stroke-width="1.4" />
          <rect x="${{x - cw / 2}}" y="${{Math.min(yo, yc)}}" width="${{cw}}" height="${{Math.max(1, Math.abs(yc - yo))}}" fill="${{color}}" rx="1" />`;
      }}).join("");
      const seriesLines = series.filter(s => Array.isArray(s.data) && s.data.length).map(s => {{
        const visiblePoints = s.data.filter(p => Number(p.time) >= startTime && Number(p.time) <= endTime);
        const pts = latestPointByVisibleFrame(visiblePoints, ["value"]).map(p => {{
          const x = xForIndex(p.__idx);
          const yy = y(p.value);
          return !Number.isFinite(x) || !Number.isFinite(yy) ? null : `${{x}},${{yy}}`;
        }}).filter(Boolean).join(" ");
        return pts ? `<polyline points="${{pts}}" fill="none" stroke="${{esc(s.color || '#315f72')}}" stroke-width="${{s.line_width || 2}}" opacity=".9" />` : "";
      }}).join("");
      const markers = visibleOrderItems.map(o => {{
        const idx = frameIndexForTime(o.time);
        if (idx < view.start || idx >= view.end) return "";
        const x = xForIndex(idx);
        if (!Number.isFinite(x)) return "";
        const price = num(o.price);
        if (price === null) return "";
        const yy = y(price);
        const isBuy = o.side === "BUY";
        const color = o.event === "CLOSE" ? (Number(o.profit || 0) >= 0 ? "var(--up)" : "var(--down)") : (isBuy ? "var(--accent)" : "var(--gold)");
        return renderOrderMarker(o, x, yy, color, pad, h);
      }}).join("");
      chartStates.price = {{paneId: "price", w, h, pad, yMin: y.min, yMax: y.max, leftIndex, rightIndex}};
      el.innerHTML = `<svg id="price-svg" data-pane="price" viewBox="0 0 ${{w}} ${{h}}" role="img">${{grid}}${{timeGrid}}${{candles}}${{seriesLines}}${{markers}}
        <g id="price-crosshair" class="crosshair" style="display:none">
          <line id="price-crosshair-h" x1="${{pad.l}}" x2="${{w - pad.r}}" y1="0" y2="0"></line>
          <line id="price-crosshair-v" x1="0" x2="0" y1="${{pad.t}}" y2="${{h - pad.b}}"></line>
          <text id="price-crosshair-value" x="${{w - pad.r + 8}}" y="0"></text>
          <text id="price-crosshair-time" x="0" y="${{h - 12}}" text-anchor="middle"></text>
        </g>
        <text x="${{pad.l}}" y="${{h - 12}}" fill="#6b7280" font-size="12">${{fmtTime(vf[0].time)}}</text>
        <text x="${{w - pad.r}}" y="${{h - 12}}" text-anchor="end" fill="#6b7280" font-size="12">${{fmtTime(vf[vf.length - 1].time)}}</text>
      </svg>`;
    }}

    function renderAccountChart() {{
      const el = document.getElementById("account-chart");
      if (!view.showAccount) {{ el.innerHTML = ""; return; }}
      const va = visibleAccount();
      if (!va.length) {{ el.innerHTML = '<div class="card-body empty">No account data in this window.</div>'; return; }}
      const displayAccount = latestPointByVisibleFrame(va, ["equity", "balance", "margin"]);
      const w = 1180, h = 240, pad = {{l: 58, r: 76, t: 24, b: 34}};
      const vf = visibleFrames();
      const leftIndex = view.start;
      const rightIndex = Math.max(view.start + 1, view.end - 1);
      const xForIndex = makeXIndexScale(leftIndex, rightIndex, pad.l, w - pad.r);
      const fields = ["equity", "balance", "margin"].filter(k => displayAccount.some(a => num(a[k]) !== null));
      const y = scale(displayAccount.flatMap(a => fields.map(k => a[k])), pad.t, h - pad.b);
      const colors = {{equity: "#315f72", balance: "#0f8b5f", margin: "#b7791f"}};
      const lines = fields.map(k => {{
        const pts = displayAccount.filter(a => num(a[k]) !== null).map((a) => `${{xForIndex(a.__idx)}},${{y(a[k])}}`).join(" ");
        return `<polyline points="${{pts}}" fill="none" stroke="${{colors[k]}}" stroke-width="2"><title>${{k}}</title></polyline>`;
      }}).join("");
      const legend = fields.map((k, i) => `<text x="${{pad.l + i * 90}}" y="18" fill="${{colors[k]}}" font-size="12">${{k}}</text>`).join("");
      chartStates.account = {{paneId: "account", w, h, pad, yMin: y.min, yMax: y.max, leftIndex, rightIndex}};
      el.innerHTML = `<svg id="account-svg" data-pane="account" viewBox="0 0 ${{w}} ${{h}}" role="img">${{axisLabels(y, w - pad.r, pad, v => Math.round(v).toLocaleString())}}${{xAxisLabels(vf, xForIndex, y, pad, h)}}${{legend}}${{lines}}
        <g id="account-crosshair" class="crosshair" style="display:none">
          <line id="account-crosshair-h" x1="${{pad.l}}" x2="${{w - pad.r}}" y1="0" y2="0"></line>
          <line id="account-crosshair-v" x1="0" x2="0" y1="${{pad.t}}" y2="${{h - pad.b}}"></line>
          <text id="account-crosshair-value" x="${{w - pad.r + 8}}" y="0"></text>
          <text id="account-crosshair-time" x="0" y="${{h - 12}}" text-anchor="middle"></text>
        </g>
        <text x="${{pad.l}}" y="${{h - 12}}" fill="#6b7280" font-size="12">${{fmtTime(va[0].time)}}</text>
        <text x="${{w - pad.r}}" y="${{h - 12}}" text-anchor="end" fill="#6b7280" font-size="12">${{fmtTime(va[va.length - 1].time)}}</text>
      </svg>`;
    }}

    function renderList(id, items, empty, rowFn) {{
      const el = document.getElementById(id);
      el.innerHTML = items.length ? items.map(rowFn).join("") : `<div class="empty">${{empty}}</div>`;
    }}

    function reportEntries() {{
      return Object.entries(reports).filter(([k]) => k !== undefined && k !== null);
    }}

    function renderReport() {{
      const el = document.getElementById("report");
      const entries = reportEntries();
      if (!entries.length) {{
        el.innerHTML = '<div class="empty">No report summary.</div>';
        return;
      }}
      const highlights = entries.slice(0, Math.min(8, entries.length)).map(([k, v]) =>
        `<div class="metric-card"><div class="label">${{esc(k)}}</div><strong>${{compact(v)}}</strong></div>`
      ).join("");
      const allRows = entries.map(([k, v]) =>
        `<div class="metric-row"><span>${{esc(k)}}</span><strong>${{compact(v)}}</strong></div>`
      ).join("");
      el.innerHTML = `
        <div class="report-overview">${{highlights}}</div>
        <details class="report-details" open>
          <summary>All report metrics (${{entries.length}})</summary>
          <div class="metric-grid">${{allRows}}</div>
        </details>`;
    }}

    function renderLogs() {{
      const logs = replay.logs || [];
      const rows = logs.slice().reverse().map(l =>
        `<div class="log-row"><span><span class="badge">${{esc(l.level || "info")}}</span> ${{esc(l.message || l.text || "")}}</span><small>${{fmtTime(l.time)}}</small></div>`
      ).join("");
      document.getElementById("logs").innerHTML = logs.length
        ? `<details class="report-details" open><summary>All logs (${{logs.length}})</summary><div class="log-list">${{rows}}</div></details>`
        : '<div class="empty">No logs.</div>';
    }}

    function locateOrder(orderKeyValue) {{
      const order = findOrderByKey(orderKeyValue);
      if (!order) return;
      const idx = frameIndexForTime(order.time);
      if (idx < 0) return;
      const size = Math.max(minWindowBars, Math.min(activeFrames.length, view.end - view.start || maxInitialBars));
      const currentOrderPage = view.orderPage;
      view.focusOrderKey = orderKeyValue;
      setWindow(idx - Math.floor(size / 2), size);
      if (view.ordersScope === "all") view.orderPage = currentOrderPage;
      const priceCard = document.querySelector(".price-card");
      if (priceCard) priceCard.scrollIntoView({{behavior: "smooth", block: "start"}});
    }}

    function renderOrders() {{
      const page = pagedOrders();
      document.getElementById("orders-page-size").value = String(page.pageSize);
      document.getElementById("orders-count").textContent = `Page ${{view.orderPage}} / ${{page.totalPages}} · ${{page.total}} / ${{orders.length}}`;
      document.getElementById("orders-prev").disabled = view.orderPage <= 1;
      document.getElementById("orders-next").disabled = view.orderPage >= page.totalPages;
      renderList("orders", page.items, "No order events in this scope.", o => {{
        const key = orderKey(o);
        const focusedClass = view.focusOrderKey === key ? " focused" : "";
        return `<div class="order-row${{focusedClass}}" data-order-key="${{esc(key)}}" role="button" tabindex="0" title="Locate this order on the price chart">
          <span>
            ${{esc(o.event)}} ${{esc(o.side)}} #${{esc(o.ticket || o.uid)}}<br>
            <small>${{fmtTime(o.time)}} · vol ${{compact(o.volume)}} · profit ${{compact(o.profit)}}<br>
            SL ${{compact(o.stop_loss)}} · TP ${{compact(o.take_profit)}} · ${{esc(o.comment || "")}}<br>
            ${{esc(JSON.stringify(o.tags || {{}}))}}</small>
          </span>
          <strong>${{compact(o.price)}}</strong>
        </div>`;
      }});
    }}

    function bindOrdersInteraction() {{
      const orderList = document.getElementById("orders");
      if (!orderList) return;
      orderList.addEventListener("click", (event) => {{
        const row = event.target.closest(".order-row");
        if (!row || !row.dataset.orderKey) return;
        locateOrder(row.dataset.orderKey);
      }});
      orderList.addEventListener("keydown", (event) => {{
        if (event.key !== "Enter" && event.key !== " ") return;
        const row = event.target.closest(".order-row");
        if (!row || !row.dataset.orderKey) return;
        event.preventDefault();
        locateOrder(row.dataset.orderKey);
      }});
    }}

    function svgEventPoint(svg, event) {{
      const rect = svg.getBoundingClientRect();
      const box = svg.viewBox.baseVal;
      return {{
        x: box.x + ((event.clientX - rect.left) / Math.max(1, rect.width)) * box.width,
        y: box.y + ((event.clientY - rect.top) / Math.max(1, rect.height)) * box.height
      }};
    }}

    function updateChartCrosshairs(event) {{
      const svg = event.target.closest("svg");
      const paneId = svg && svg.dataset ? svg.dataset.pane : null;
      const state = paneId ? chartStates[paneId] : null;
      if (!svg || !state) return;
      const {{w, h, pad, leftIndex, rightIndex}} = state;
      const point = svgEventPoint(svg, event);
      const x = Math.max(pad.l, Math.min(w - pad.r, point.x));
      const yCoord = Math.max(pad.t, Math.min(h - pad.b, point.y));
      const ratioX = (x - pad.l) / Math.max(1, w - pad.l - pad.r);
      const idx = Math.max(0, Math.min(activeFrames.length - 1, Math.round(leftIndex + ratioX * (rightIndex - leftIndex))));
      activeCursor = {{paneId, idx, yByPane: {{[paneId]: yCoord}}}};
      renderChartCrosshairs();
    }}

    function renderChartCrosshairs() {{
      for (const [paneId, state] of Object.entries(chartStates)) {{
        const group = document.getElementById(`${{paneId}}-crosshair`);
        if (!group) continue;
        if (!activeCursor || !activeFrames[activeCursor.idx]) {{
          group.style.display = "none";
          continue;
        }}
        const {{w, h, pad, yMin, yMax, leftIndex, rightIndex}} = state;
        const xForIndex = makeXIndexScale(leftIndex, rightIndex, pad.l, w - pad.r);
        const x = Math.max(pad.l, Math.min(w - pad.r, xForIndex(activeCursor.idx)));
        const vertical = document.getElementById(`${{paneId}}-crosshair-v`);
        vertical.setAttribute("x1", String(x));
        vertical.setAttribute("x2", String(x));
        const timeLabel = document.getElementById(`${{paneId}}-crosshair-time`);
        timeLabel.setAttribute("x", String(x));
        timeLabel.textContent = fmtTime(activeFrames[activeCursor.idx].time);

        const horizontal = document.getElementById(`${{paneId}}-crosshair-h`);
        const valueLabel = document.getElementById(`${{paneId}}-crosshair-value`);
        const yCoord = activeCursor.yByPane[paneId];
        if (Number.isFinite(yCoord)) {{
          const ratioY = (yCoord - pad.t) / Math.max(1, h - pad.t - pad.b);
          const value = yMax - ratioY * (yMax - yMin);
          horizontal.style.display = "";
          valueLabel.style.display = "";
          horizontal.setAttribute("y1", String(yCoord));
          horizontal.setAttribute("y2", String(yCoord));
          valueLabel.setAttribute("y", String(yCoord + 4));
          valueLabel.textContent = paneId === "account" ? Math.round(value).toLocaleString() : compact(value);
        }} else {{
          horizontal.style.display = "none";
          valueLabel.style.display = "none";
        }}
        group.style.display = "";
      }}
    }}

    function hideChartCrosshairs() {{
      activeCursor = null;
      for (const paneId of Object.keys(chartStates)) {{
        const group = document.getElementById(`${{paneId}}-crosshair`);
        if (group) group.style.display = "none";
      }}
    }}

    function updateOrderTooltipFromEvent(event) {{
      const marker = event.target.closest(".order-marker");
      if (!marker || !marker.dataset.orderKey) {{
        hideOrderTooltip();
        return false;
      }}
      showOrderTooltip(marker.dataset.orderKey, event);
      return true;
    }}

    function bindChartMouseControls() {{
      const chartArea = document.querySelector(".price-card");
      if (!chartArea) return;
      chartArea.addEventListener("wheel", (event) => {{
        const svg = event.target.closest("svg");
        if (!svg || !svg.dataset.pane) return;
        event.preventDefault();
        const rect = svg.getBoundingClientRect();
        const anchorRatio = Math.max(0, Math.min(1, (event.clientX - rect.left) / Math.max(1, rect.width)));
        zoom(event.deltaY < 0 ? 0.8 : 1.25, anchorRatio);
      }}, {{passive: false}});
      chartArea.addEventListener("mousedown", (event) => {{
        const svg = event.target.closest("svg");
        if (!svg || !svg.dataset.pane) return;
        if (event.button !== 0) return;
        if (event.target.closest(".order-marker")) {{
          event.preventDefault();
          chartArea.focus({{preventScroll: true}});
          return;
        }}
        event.preventDefault();
        chartArea.focus({{preventScroll: true}});
        view.isDragging = true;
        view.dragStartX = event.clientX;
        view.dragStartViewStart = view.start;
        view.dragStartViewEnd = view.end;
        view.dragStartWidth = svg.getBoundingClientRect().width;
        svg.classList.add("dragging");
      }});
      chartArea.addEventListener("mousemove", (event) => {{
        updateOrderTooltipFromEvent(event);
        updateChartCrosshairs(event);
      }});
      chartArea.addEventListener("click", (event) => {{
        const marker = event.target.closest(".order-marker");
        if (!marker || !marker.dataset.orderKey) return;
        locateOrder(marker.dataset.orderKey);
      }});
      chartArea.addEventListener("mouseleave", () => {{
        hideOrderTooltip();
        hideChartCrosshairs();
      }});
      chartArea.addEventListener("keydown", (event) => {{
        const size = Math.max(minWindowBars, view.end - view.start);
        if (event.key === "ArrowLeft") {{
          event.preventDefault();
          panBars(-Math.max(1, Math.round(size * 0.12)));
        }} else if (event.key === "ArrowRight") {{
          event.preventDefault();
          panBars(Math.max(1, Math.round(size * 0.12)));
        }} else if (event.key === "ArrowUp") {{
          event.preventDefault();
          zoom(0.8);
        }} else if (event.key === "ArrowDown") {{
          event.preventDefault();
          zoom(1.25);
        }}
      }});
      window.addEventListener("mousemove", (event) => {{
        if (!view.isDragging) return;
        event.preventDefault();
        const size = Math.max(minWindowBars, view.end - view.start);
        const deltaBars = Math.round((event.clientX - view.dragStartX) / Math.max(1, view.dragStartWidth || 1) * size);
        view.start = view.dragStartViewStart - deltaBars;
        view.end = view.dragStartViewEnd - deltaBars;
        clampView();
        scheduleRender();
      }});
      window.addEventListener("mouseup", () => {{
        if (!view.isDragging) return;
        view.isDragging = false;
        document.querySelectorAll(".price-card svg.dragging").forEach(svg => svg.classList.remove("dragging"));
      }});
    }}

    function renderAll() {{
      updateWindowControls();
      renderPriceChart();
      renderAccountChart();
      renderOrders();
    }}

    window.__pixiuChartDebug = () => ({{
      timeframe: activeTimeframe,
      rawFrames: rawFrames.length,
      activeFrames: activeFrames.length,
      view: {{start: view.start, end: view.end}},
      visibleFrames: visibleFrames().map(f => ({{
        time: f.time,
        open: f.open,
        high: f.high,
        low: f.low,
        close: f.close,
        volume: f.volume,
        sourceStart: f.__sourceStart,
        sourceEnd: f.__sourceEnd
      }}))
    }});

    document.getElementById("zoom-in").addEventListener("click", () => zoom(0.5));
    document.getElementById("zoom-out").addEventListener("click", () => zoom(2));
    document.getElementById("pan-left").addEventListener("click", () => pan(-0.5));
    document.getElementById("pan-right").addEventListener("click", () => pan(0.5));
    document.getElementById("reset-view").addEventListener("click", () => setWindow(0, activeFrames.length));
    document.getElementById("timeframe-select").addEventListener("change", (event) => setTimeframe(event.target.value));
    document.getElementById("show-account").addEventListener("change", (event) => {{
      view.showAccount = event.target.checked;
      renderAccountChart();
    }});
    document.getElementById("window-range").addEventListener("input", (event) => {{
      setWindow(Number(event.target.value), view.end - view.start);
    }});
    document.getElementById("orders-scope").addEventListener("change", (event) => {{
      view.ordersScope = event.target.value;
      view.orderPage = 1;
      renderAll();
    }});
    document.getElementById("orders-page-size").addEventListener("change", (event) => {{
      view.orderPageSize = Number(event.target.value) || 50;
      view.orderPage = 1;
      renderAll();
    }});
    document.getElementById("orders-prev").addEventListener("click", () => {{
      view.orderPage -= 1;
      renderOrders();
    }});
    document.getElementById("orders-next").addEventListener("click", () => {{
      view.orderPage += 1;
      renderOrders();
    }});

    renderReport();
    renderLogs();
    clampView();
    bindChartMouseControls();
    bindOrdersInteraction();
    renderAll();
  </script>
</body>
</html>
""".format(title=safe_title, replay_json=replay_json)


def write_chart_replay_html(replay, output_path, title=None):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_chart_replay_html(replay, title=title), encoding="utf-8")
    return str(output)


def _default_title(replay):
    metadata = replay.get("metadata", {}) if isinstance(replay, dict) else {}
    return metadata.get("test_name") or metadata.get("script_name") or "Pixiu Chart Replay"


def _safe_script_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
