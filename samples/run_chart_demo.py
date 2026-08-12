import json
import os
import sys
import tempfile
from pathlib import Path

from pixiu.pxtester import PXTester
from pixiu.chart import render_ea_explain_chart_png


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "samples" / "chart_demo.json"
SCRIPT_PATH = ROOT / "samples" / "chart_demo_ea.py"
OUTPUT_DIR = Path(os.environ.get("PIXIU_CHART_DEMO_OUTPUT_DIR", tempfile.gettempdir()))
OUTPUT_HTML = OUTPUT_DIR / "pixiu_chart_demo.html"
OUTPUT_EXPLAIN_JSON = OUTPUT_DIR / "pixiu_chart_demo_explain_chart.json"
OUTPUT_EXPLAIN_PNG = OUTPUT_DIR / "pixiu_chart_demo_explain_chart.png"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tester = PXTester(
        str(CONFIG_PATH),
        "chartDemoUSDCHF",
        str(SCRIPT_PATH),
        print_log_type=["report"],
    )
    tester.execute("chart-demo", sync=True)
    saved_html = tester.save_chart_report_html(str(OUTPUT_HTML), graph_data=tester.graph_data, title="Pixiu Chart Demo")
    chart_types = tester.get_ea_explain_chart_types()
    explain_chart = tester.get_ea_explain_chart({
        "chart_type": "open_context",
        "params": {"include_orders": True},
    })
    OUTPUT_EXPLAIN_JSON.write_text(json.dumps({
        "chart_types": chart_types,
        "chart": explain_chart,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    saved_png = None
    if explain_chart.get("success"):
        saved_png = render_ea_explain_chart_png(explain_chart, OUTPUT_EXPLAIN_PNG)
    print("Chart report: %s" % saved_html)
    print("Explain chart JSON: %s" % OUTPUT_EXPLAIN_JSON)
    if saved_png:
        print("Explain chart PNG: %s" % saved_png)
    print("Open in browser: file://%s" % saved_html)
    return 0 if explain_chart.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
