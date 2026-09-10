from __future__ import annotations

import json
from pathlib import Path

import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Global Economic Impact Analysis.ipynb"
OUTPUT_DIR = ROOT / "docs" / "previews"
PREVIEWS = {
    "gdp-world-trend": "world-gdp-trend.png",
    "gdp-selected-trajectories": "selected-gdp-trajectories.png",
    "gdp-arima-backtest": "gdp-arima-backtest.png",
}


def saved_figures() -> dict[str, dict[str, object]]:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    figures = {}
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            figure = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if figure is not None:
                figures[figure["layout"]["meta"]["chart_id"]] = figure
    return figures


def main() -> None:
    figures = saved_figures()
    missing = sorted(set(PREVIEWS) - set(figures))
    if missing:
        raise RuntimeError("Missing saved notebook figures: " + ", ".join(missing))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for chart_id, filename in PREVIEWS.items():
        figure = pio.from_json(json.dumps(figures[chart_id]))
        figure.update_layout(width=1400, height=800)
        pio.write_image(figure, OUTPUT_DIR / filename, width=1400, height=800)


if __name__ == "__main__":
    main()
