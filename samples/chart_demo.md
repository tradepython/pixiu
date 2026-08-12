# Pixiu Chart Demo

This sample exercises the browser chart replay and the optional on-demand EA Explain Chart API.

## Files

- `chart_demo.json`: backtest config using the local USDCHF sample data.
- `chart_demo_ea.py`: demo EA that plots moving averages, support/resistance, expected entry lines, demo orders, and explain events.
- `run_chart_demo.py`: helper runner that writes a browser HTML report, an explain chart JSON file, and a standalone explain chart PNG.

## Run

```bash
python samples/run_chart_demo.py
```

Output files:

- `${TMPDIR:-/tmp}/pixiu_chart_demo.html`
- `${TMPDIR:-/tmp}/pixiu_chart_demo_explain_chart.json`
- `${TMPDIR:-/tmp}/pixiu_chart_demo_explain_chart.png`

Set `PIXIU_CHART_DEMO_OUTPUT_DIR` to write the files somewhere else.

Open the HTML file in Chrome to test zoom, pan, order markers, report, account chart, and custom series rendering. Open the PNG file to test `PX_GetEAExplainChart(...)` as a standalone, on-demand strategy chart.

## CLI Alternative

```bash
mkdir -p pxdata
test -f pxdata/_pixiu_data.json || printf '{"version":"0.1.0","tags":{}}' > pxdata/_pixiu_data.json
python -m pixiu test \
  -c samples/chart_demo.json \
  -n chartDemoUSDCHF \
  -s samples/chart_demo_ea.py \
  -m false \
  --chart-report "${TMPDIR:-/tmp}/pixiu_chart_demo_cli.html" \
  --explain on
```

The helper runner is still useful because it also calls `PX_GetEAExplainChartTypes()` and `PX_GetEAExplainChart(...)`, then saves the returned JSON.
