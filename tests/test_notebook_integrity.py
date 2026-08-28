from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Global Economic Impact Analysis.ipynb"
SYNTHETIC_DISCLOSURE = "Synthetic demonstration data. Values are fictional and are not observed measurements."


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


def test_notebook_has_14_unique_plotly_chart_ids():
    figures = _figures()
    chart_ids = [figure["layout"]["meta"]["chart_id"] for figure in figures]

    assert len(figures) == 14
    assert len(set(chart_ids)) == 14


def test_every_saved_figure_discloses_its_provenance():
    figures = _figures()
    open_figures = [
        figure
        for figure in figures
        if figure["layout"]["meta"]["classification"] == "open"
    ]
    synthetic_figures = [
        figure
        for figure in figures
        if figure["layout"]["meta"]["classification"] == "synthetic"
    ]

    assert len(open_figures) == 5
    assert len(synthetic_figures) == 9
    for figure in open_figures:
        title = figure["layout"]["title"]["text"]
        assert "World Bank Open Data" in title
        assert "CC BY 4.0" in title
        assert "World Bank Open Data" in figure["layout"]["meta"]["provenance"]
    for figure in synthetic_figures:
        title = figure["layout"]["title"]["text"]
        assert SYNTHETIC_DISCLOSURE in title
        assert figure["layout"]["meta"]["provenance"] == SYNTHETIC_DISCLOSURE


def test_fifth_figure_is_a_gdp_only_ranking():
    fifth = _figures()[4]

    assert fifth["layout"]["meta"]["chart_id"] == "gdp-latest-ranking"
    assert fifth["layout"]["meta"]["table"] == "gdp_annual"
    assert "GDP" in fifth["layout"]["title"]["text"]


def test_geographic_figures_keep_year_animation_controls():
    for chart_id in ("gdp-country-map", "transfer-geographic-scenarios"):
        figure = _figure(chart_id)
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


def test_readme_uses_public_paths_and_has_no_image_gallery():
    readme = (ROOT / "README.md").read_text()

    assert "data/profiles/public-demo" in readme
    assert "scripts/build_notebook.py --execute" in readme
    assert "GEIA_DATA_DIR" in readme
    assert not re.search(r"!\[[^\]]*\]\([^)]*\)", readme)
