from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Global Economic Impact Analysis.ipynb"
OPEN_CHART_IDS = (
    "gdp-world-trend",
    "gdp-selected-trajectories",
    "gdp-annual-change",
    "gdp-country-map",
    "gdp-latest-ranking",
    "gdp-arima-backtest",
)


def _notebook():
    return json.loads(NOTEBOOK_PATH.read_text())


def _figures():
    figures = []
    for cell in _notebook()["cells"]:
        for output in cell.get("outputs", []):
            figure = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if figure is not None:
                figures.append(figure)
    return figures


def _figure(chart_id: str):
    return next(
        figure
        for figure in _figures()
        if figure["layout"]["meta"]["chart_id"] == chart_id
    )


def test_notebook_has_clean_saved_execution_and_generic_kernel():
    notebook = _notebook()
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    assert all(cell["execution_count"] is not None for cell in code_cells)
    assert all("execution" not in cell.get("metadata", {}) for cell in code_cells)
    assert all(
        output.get("output_type") != "error"
        for cell in code_cells
        for output in cell.get("outputs", [])
    )


def test_notebook_has_six_unique_open_plotly_chart_ids():
    figures = _figures()
    chart_ids = [figure["layout"]["meta"]["chart_id"] for figure in figures]

    assert chart_ids == list(OPEN_CHART_IDS)
    assert len(set(chart_ids)) == 6


def test_every_saved_figure_discloses_open_gdp_provenance():
    figures = _figures()

    assert all(figure["layout"]["meta"]["classification"] == "open" for figure in figures)
    assert all(figure["layout"]["meta"]["table"] == "gdp_annual" for figure in figures)
    for figure in figures:
        title = figure["layout"]["title"]["text"]
        assert "World Bank Open Data" in title
        assert "CC BY 4.0" in title
        assert "World Bank Open Data" in figure["layout"]["meta"]["provenance"]


def test_fifth_figure_is_a_gdp_only_ranking():
    fifth = _figures()[4]

    assert fifth["layout"]["meta"]["chart_id"] == "gdp-latest-ranking"
    assert fifth["layout"]["meta"]["table"] == "gdp_annual"
    assert "GDP" in fifth["layout"]["title"]["text"]


def test_selected_trajectories_use_log_y_axis():
    yaxis = _figure("gdp-selected-trajectories")["layout"]["yaxis"]

    assert yaxis.get("type") == "log"


def test_arima_backtest_compares_observed_arima_and_naive():
    names = [trace.get("name") for trace in _figure("gdp-arima-backtest")["data"]]

    assert names[0] == "Observed"
    assert any(name and name.startswith("ARIMA") for name in names)
    assert "Previous-year baseline" in names


def test_geographic_figures_keep_year_animation_controls():
    figure = _figure("gdp-country-map")
    assert len(figure["frames"]) > 1
    assert "sliders" in figure["layout"]
    assert any(
        button.get("label") in {"&#9654;", "Play"}
        for menu in figure["layout"].get("updatemenus", [])
        for button in menu.get("buttons", [])
    )


def test_notebook_has_no_raw_data_appendix():
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in _notebook()["cells"]
    ).lower()

    assert "raw-data appendix" not in source
    assert "source-data appendix" not in source


def test_notebook_does_not_plot_synthetic_tables():
    source = "\n".join("".join(cell.get("source", [])) for cell in _notebook()["cells"])

    assert "SYNTHETIC_DISCLOSURE" not in source
    assert "aircraft_orders_monthly" not in source
    assert "arms_by_category_annual" not in source


def test_readme_leads_with_computed_gdp_findings():
    readme = (ROOT / "README.md").read_text()

    assert readme.index("World nominal GDP rose") < readme.index("## Preview")
    assert "72.6×" in readme
    assert "4.527%" in readme
    assert "4.506%" in readme
    assert "China passed Japan in 2010" in readme
    assert "future projection is not published" in readme


def test_readme_uses_public_paths_and_safe_previews():
    readme = (ROOT / "README.md").read_text()
    image_references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    preview_references = {
        reference
        for reference in image_references
        if reference.startswith("docs/previews/")
    }

    assert "data/profiles/public-demo" in readme
    assert "uv sync --locked --dev" in readme
    assert "make verify" in readme
    assert "GEIA_DATA_DIR" in readme
    assert preview_references == {
        "docs/previews/selected-gdp-trajectories.png",
        "docs/previews/gdp-arima-backtest.png",
        "docs/previews/world-gdp-trend.png",
    }
    assert all((ROOT / reference).is_file() for reference in preview_references)
    assert all(
        (ROOT / reference).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        for reference in preview_references
    )
    assert not any(reference.startswith("img/") for reference in image_references)
