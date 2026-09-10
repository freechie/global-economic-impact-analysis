from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Global Economic Impact Analysis.ipynb"
OPEN_CHART_IDS = (
    "gdp-world-trend",
    "gdp-nominal-vs-real",
    "gdp-selected-trajectories",
    "gdp-latest-ranking",
    "gdp-arima-backtest",
    "gdp-arima-projection",
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
    assert all(
        figure["layout"]["meta"]["table"] in {"gdp_annual", "gdp_real_annual"}
        for figure in figures
    )
    for figure in figures:
        title = figure["layout"]["title"]["text"]
        assert "World Bank Open Data" in title
        assert "CC BY 4.0" in title
        assert "World Bank Open Data" in figure["layout"]["meta"]["provenance"]


def test_nominal_vs_real_figure_compares_current_and_constant_series():
    names = [trace.get("name") for trace in _figure("gdp-nominal-vs-real")["data"]]
    meta = _figure("gdp-nominal-vs-real")["layout"]["meta"]

    assert "Current US$" in names
    assert "Constant 2015 US$" in names
    assert meta["table"] == "gdp_real_annual"
    assert "constant 2015" in meta["provenance"]


def test_ranking_figure_is_gdp_only():
    ranking = _figure("gdp-latest-ranking")

    assert ranking["layout"]["meta"]["table"] == "gdp_annual"
    assert "GDP" in ranking["layout"]["title"]["text"]


def test_selected_trajectories_use_log_y_axis():
    yaxis = _figure("gdp-selected-trajectories")["layout"]["yaxis"]

    assert yaxis.get("type") == "log"


def test_arima_projection_includes_observed_and_median_path():
    names = [trace.get("name") for trace in _figure("gdp-arima-projection")["data"]]

    assert names[0] == "Observed"
    assert any(name and "median" in name for name in names)
    assert "95% interval" in names


def test_arima_backtest_compares_observed_arima_and_naive():
    names = [trace.get("name") for trace in _figure("gdp-arima-backtest")["data"]]

    assert names[0] == "Observed"
    assert any(name and name.startswith("ARIMA") for name in names)
    assert "Previous-year baseline" in names


def test_saved_figures_are_not_animated():
    for figure in _figures():
        assert not figure.get("frames")


def test_notebook_notes_the_1960_china_japan_artifact():
    source = "\n".join("".join(cell.get("source", [])) for cell in _notebook()["cells"])

    assert "China sits above Japan in 1960" in source
    assert "after 1980 is 2010" in source


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
    assert "86.5×" in readme
    assert "3.804%" in readme
    assert "4.574%" in readme
    assert "China passed Japan in 2010" in readme
    assert "ten-year projection is published" in readme
    assert "2009: current -5.2%, constant 2015 -1.3%." in readme
    assert "2015: current -5.5%, constant 2015 3.1%." in readme
    assert "2020: current -2.7%, constant 2015 -2.9%." in readme
    assert "2015 is a dollar year" in readme
    assert "2009 and 2020 are real contractions" in readme


def test_readme_uses_public_paths_and_safe_previews():
    readme = (ROOT / "README.md").read_text()
    image_references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    preview_references = {
        reference
        for reference in image_references
        if reference.startswith("docs/previews/")
    }

    assert "data/profiles/public-demo" in readme
    assert "data/open/world-bank" in readme
    assert "uv sync --locked --dev" in readme
    assert "make verify" in readme
    assert "make notebook" in readme
    assert "make fetch" in readme
    assert "make fetch-gdp" not in readme
    assert "GEIA_DATA_DIR" in readme
    assert preview_references == {
        "docs/previews/gdp-arima-backtest.png",
        "docs/previews/gdp-arima-projection.png",
        "docs/previews/gdp-latest-ranking.png",
        "docs/previews/gdp-nominal-vs-real.png",
        "docs/previews/selected-gdp-trajectories.png",
        "docs/previews/world-gdp-trend.png",
    }
    assert all((ROOT / reference).is_file() for reference in preview_references)
    assert all(
        (ROOT / reference).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        for reference in preview_references
    )
    assert not any(reference.startswith("img/") for reference in image_references)
