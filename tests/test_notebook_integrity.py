from __future__ import annotations

import base64
import json
from pathlib import Path
import re

import numpy as np
import pytest

from src.analysis_utils import (
    country_gdp,
    expanding_arima_backtest,
    expanding_arima_projection,
    latest_gdp_ranking,
    nominal_gdp_story,
    nominal_vs_real_changes,
    world_gdp_series,
)
from src.data_loader import load_analysis_bundle

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


def _plotly_array(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and "bdata" in value:
        return np.frombuffer(
            base64.b64decode(value["bdata"]), dtype=value["dtype"]
        ).tolist()
    raise TypeError(f"Unsupported plotly array: {type(value)!r}")


def _annotation_text(chart_id: str) -> str:
    figure = _figure(chart_id)
    return " ".join(
        str(item.get("text", "")) for item in figure["layout"].get("annotations") or []
    )


def _hovertemplates(chart_id: str) -> list[str]:
    return [
        str(trace.get("hovertemplate") or "")
        for trace in _figure(chart_id)["data"]
        if trace.get("hoverinfo") != "skip"
    ]


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
    assert "2009: current -5.2%, constant 2015 -1.3%" in readme
    assert "2015: current -5.5%, constant 2015 3.1%" in readme
    assert "2020: current -2.7%, constant 2015 -2.9%" in readme
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


def test_world_trend_trace_matches_world_csv_and_states_the_2015_split():
    bundle = load_analysis_bundle()
    world = world_gdp_series(bundle.gdp_annual)
    checks = {
        row.year: row
        for row in nominal_vs_real_changes(world, world_gdp_series(bundle.gdp_real_annual))
    }
    figure = _figure("gdp-world-trend")
    trace = figure["data"][0]
    years = [int(year) for year in _plotly_array(trace["x"])]
    values = _plotly_array(trace["y"])
    text = _annotation_text("gdp-world-trend")

    assert years == [int(year) for year in world.index]
    assert values == pytest.approx([float(world.loc[year]) for year in years])
    assert figure["layout"]["hovermode"] == "x unified"
    assert all("trillion" in template for template in _hovertemplates("gdp-world-trend"))
    assert "2015 FX" in text
    assert f"{checks[2015].nominal_change_pct:.1f}%" in text
    assert f"{checks[2015].real_change_pct:.1f}%" in text


def test_nominal_vs_real_traces_match_yoy_and_show_dollar_year_claims():
    bundle = load_analysis_bundle()
    nominal = world_gdp_series(bundle.gdp_annual)
    real = world_gdp_series(bundle.gdp_real_annual)
    checks = {row.year: row for row in nominal_vs_real_changes(nominal, real)}
    figure = _figure("gdp-nominal-vs-real")
    traces = {trace["name"]: trace for trace in figure["data"]}
    text = _annotation_text("gdp-nominal-vs-real")
    zero_line = any(
        shape.get("y0") == 0 and shape.get("y1") == 0
        for shape in figure["layout"].get("shapes") or []
    )

    for name, series in (("Current US$", nominal), ("Constant 2015 US$", real)):
        trace = traces[name]
        years = [int(year) for year in _plotly_array(trace["x"])]
        values = _plotly_array(trace["y"])
        expected = (series.pct_change() * 100).loc[years]
        assert values == pytest.approx(expected.to_numpy(dtype=float).tolist())
    assert figure["layout"]["hovermode"] == "x unified"
    assert all(".1f" in template and "%" in template for template in _hovertemplates("gdp-nominal-vs-real"))
    assert zero_line
    for year in (2009, 2015, 2020):
        assert f"{checks[year].nominal_change_pct:.1f}%" in text
        assert f"{checks[year].real_change_pct:.1f}%" in text
    assert "FX" in text


def test_selected_trajectories_match_country_csv_and_mark_the_2010_crossing():
    bundle = load_analysis_bundle()
    story = nominal_gdp_story(bundle.gdp_annual)
    countries = country_gdp(bundle.gdp_annual)
    figure = _figure("gdp-selected-trajectories")
    text = _annotation_text("gdp-selected-trajectories")

    for trace in figure["data"]:
        years = [int(year) for year in _plotly_array(trace["x"])]
        values = _plotly_array(trace["y"])
        subset = countries.loc[countries["country_name"] == trace["name"]].set_index("year")[
            "nominal_gdp_usd"
        ]
        assert values == pytest.approx([float(subset.loc[year]) for year in years])
    assert figure["layout"]["hovermode"] == "x unified"
    assert all("trillion" in template for template in _hovertemplates("gdp-selected-trajectories"))
    assert "China passes Japan" in text
    assert any(
        shape.get("x0") == story.china_passes_japan_year
        for shape in figure["layout"].get("shapes") or []
    )


def test_ranking_bars_match_latest_country_gdp_and_label_trillions():
    bundle = load_analysis_bundle()
    ranking = latest_gdp_ranking(bundle.gdp_annual, limit=15)
    figure = _figure("gdp-latest-ranking")
    trace = figure["data"][0]
    values = _plotly_array(trace["x"])
    names = list(trace["y"])
    labels = list(trace.get("text") or [])

    assert names == ranking["country_name"].tolist()
    assert values == pytest.approx(ranking["nominal_gdp_usd"].tolist())
    assert figure["layout"]["hovermode"] == "closest"
    assert all("trillion" in template for template in _hovertemplates("gdp-latest-ranking"))
    assert labels == [f"${value / 1e12:.1f}T" for value in ranking["nominal_gdp_usd"]]


def test_arima_backtest_traces_match_model_and_show_mape():
    bundle = load_analysis_bundle()
    backtest = expanding_arima_backtest(world_gdp_series(bundle.gdp_annual))
    figure = _figure("gdp-arima-backtest")
    traces = {trace["name"]: trace for trace in figure["data"]}
    text = _annotation_text("gdp-arima-backtest")
    observed = traces["Observed"]

    assert [int(year) for year in _plotly_array(observed["x"])] == list(backtest.years)
    assert _plotly_array(observed["y"]) == pytest.approx(list(backtest.observed))
    assert _plotly_array(traces[f"ARIMA{backtest.order}"]["y"]) == pytest.approx(
        list(backtest.arima_one_step)
    )
    assert _plotly_array(traces["Previous-year baseline"]["y"]) == pytest.approx(
        list(backtest.naive_one_step)
    )
    assert figure["layout"]["hovermode"] == "x unified"
    assert all("trillion" in template for template in _hovertemplates("gdp-arima-backtest"))
    assert f"{backtest.arima_mape:.3f}%" in text
    assert f"{backtest.naive_mape:.3f}%" in text


def test_arima_projection_traces_match_model_and_show_interval():
    bundle = load_analysis_bundle()
    series = world_gdp_series(bundle.gdp_annual)
    backtest = expanding_arima_backtest(series)
    projection = expanding_arima_projection(series, backtest.order)
    figure = _figure("gdp-arima-projection")
    traces = {trace["name"]: trace for trace in figure["data"]}
    text = _annotation_text("gdp-arima-projection")
    observed = traces["Observed"]
    median = next(trace for name, trace in traces.items() if name and "median" in name)

    assert int(_plotly_array(observed["x"])[-1]) == int(series.index.max())
    assert _plotly_array(observed["y"])[-1] == pytest.approx(float(series.iloc[-1]))
    assert [int(year) for year in _plotly_array(median["x"])] == list(projection.years)
    assert _plotly_array(median["y"]) == pytest.approx(list(projection.median))
    assert _plotly_array(traces["95% interval"]["y"]) == pytest.approx(list(projection.lower))
    assert figure["layout"]["hovermode"] == "x unified"
    money_hovers = [template for template in _hovertemplates("gdp-arima-projection") if template]
    assert money_hovers
    assert all("trillion" in template for template in money_hovers)
    assert f"{projection.years[-1]} median" in text
    assert f"{projection.median[-1] / 1e12:.2f} trillion" in text
    assert (
        f"{projection.lower[-1] / 1e12:.2f} to "
        f"{projection.upper[-1] / 1e12:.2f} trillion"
    ) in text.replace("<br>", " ")
    assert "$" not in text
