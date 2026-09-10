from __future__ import annotations

import argparse
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Global Economic Impact Analysis.ipynb"


def markdown(cell_id: str, source: str):
    cell = nbformat.v4.new_markdown_cell(source.strip() + "\n")
    cell["id"] = cell_id
    return cell


def code(cell_id: str, source: str):
    cell = nbformat.v4.new_code_cell(source.strip() + "\n")
    cell["id"] = cell_id
    return cell


def build_notebook() -> nbformat.NotebookNode:
    cells = [
        markdown(
            "introduction",
            """
# Global economic impact analysis

Every chart uses World Bank GDP in current US dollars, license CC BY 4.0. Numbers come from `gdp_annual.csv`. Set `GEIA_DATA_DIR` to point at another complete profile. The loader does not fall back to `public-demo`.
""",
        ),
        code(
            "setup",
            """
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path.cwd()
if not (ROOT / "src").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.analysis_utils import (
    SELECTED_TRAJECTORY_COUNTRIES,
    annual_percent_change,
    country_gdp,
    expanding_arima_backtest,
    expanding_arima_projection,
    latest_gdp_ranking,
    nominal_gdp_story,
    projection_decision_text,
    world_gdp_series,
)
from src.data_loader import load_analysis_bundle

pio.renderers.default = "plotly_mimetype"
bundle = load_analysis_bundle()
story = nominal_gdp_story(bundle.gdp_annual)
world_series = world_gdp_series(bundle.gdp_annual)
backtest = expanding_arima_backtest(world_series)
projection = (
    expanding_arima_projection(world_series, backtest.order)
    if backtest.publishes_projection
    else None
)
OPEN_DISCLOSURE = "World Bank Open Data, GDP (current US$). License: CC BY 4.0."

def disclose(fig, chart_id, title, table_name):
    fig.update_layout(
        title={"text": f"{title}<br><sup>{OPEN_DISCLOSURE}</sup>"},
        template="plotly_white",
        autosize=True,
        meta={
            "chart_id": chart_id,
            "classification": "open",
            "provenance": OPEN_DISCLOSURE,
            "table": table_name,
            "profile_id": bundle.profile.profile_id,
        },
    )
    return fig

def trillions(value):
    return f"${value / 1e12:.2f} trillion"
""",
        ),
        markdown("findings-heading", "## Findings"),
        code(
            "findings",
            """
declines = ", ".join(
    f"{year} {change:.1f}%" for year, change in story.sharpest_declines
)
print(
    f"World nominal GDP rose from {trillions(story.start_usd)} in {story.start_year} "
    f"to {trillions(story.end_usd)} in {story.end_year}, {story.growth_multiple:.1f}×."
)
print(
    f"The sharpest current-dollar year-over-year declines are {declines}. "
    "The 2015 drop is mostly a strong dollar, not a collapse in world output."
)
print(
    f"China was {story.china_share_1990_pct:.1f}% of U.S. GDP in 1990 and "
    f"{story.china_share_latest_pct:.1f}% in {story.latest_year}. "
    f"China passed Japan in {story.china_passes_japan_year}."
)
print(
    f"Selected ARIMA{backtest.order}: {backtest.arima_mape:.3f}% MAPE; "
    f"naive baseline: {backtest.naive_mape:.3f}% MAPE."
)
print(projection_decision_text(backtest))
""",
        ),
        markdown("open-heading", "## Open-data GDP figures"),
        code(
            "chart-01",
            """
world = bundle.gdp_annual.loc[bundle.gdp_annual["country_code"] == "WLD"]
fig = px.line(world, x="year", y="nominal_gdp_usd", labels={"nominal_gdp_usd": "Current US$", "year": "Year"})
for year, label in ((2009, "2009"), (2015, "2015 FX"), (2020, "2020")):
    fig.add_vline(x=year, line_dash="dot", annotation_text=label, annotation_position="top")
disclose(fig, "gdp-world-trend", "1. World nominal GDP over time", "gdp_annual").show()
""",
        ),
        markdown(
            "chart-01-note",
            """
Current-dollar World GDP mixes real output, inflation, and exchange rates. 2015 is the largest drop in this series. It is not a 2009-scale or 2020-scale world recession.
""",
        ),
        code(
            "chart-02",
            """
selected = country_gdp(bundle.gdp_annual).loc[
    lambda frame: frame["country_name"].isin(SELECTED_TRAJECTORY_COUNTRIES)
]
fig = px.line(
    selected,
    x="year",
    y="nominal_gdp_usd",
    color="country_name",
    labels={"nominal_gdp_usd": "Current US$", "country_name": "Country", "year": "Year"},
)
fig.update_yaxes(type="log")
disclose(fig, "gdp-selected-trajectories", "2. Selected nominal GDP trajectories, log scale", "gdp_annual").show()
""",
        ),
        markdown(
            "chart-02-note",
            """
Log scale keeps early China and India visible. A linear axis hides them behind the United States. China sits above Japan in 1960 in this file. That early reading is a World Bank current-dollar artifact. The first year China exceeds Japan after 1980 is 2010.
""",
        ),
        code(
            "chart-03",
            """
growth = annual_percent_change(selected, group_column="country_name", value_column="nominal_gdp_usd")
fig = px.line(growth.dropna(subset=["annual_change_pct"]), x="year", y="annual_change_pct", color="country_name", labels={"annual_change_pct": "Annual change (%)", "country_name": "Country", "year": "Year"})
disclose(fig, "gdp-annual-change", "3. Annual nominal GDP change", "gdp_annual").show()
""",
        ),
        markdown(
            "chart-03-note",
            """
These are current-dollar changes, so inflation and exchange rates move the lines. China's swings are larger than the United States. 2015 is a dollar year, not a China collapse.
""",
        ),
        code(
            "chart-04",
            """
ranking = latest_gdp_ranking(bundle.gdp_annual, limit=15)
ranking_year = int(ranking["year"].iloc[0])
fig = px.bar(ranking, x="nominal_gdp_usd", y="country_name", orientation="h", labels={"nominal_gdp_usd": "Current US$", "country_name": "Country"})
disclose(fig, "gdp-latest-ranking", f"4. Largest nominal GDP observations in {ranking_year}", "gdp_annual").show()
print(
    f"Largest {ranking_year} current-dollar GDP: "
    + ", ".join(ranking.sort_values("nominal_gdp_usd", ascending=False)["country_name"].head(5))
    + "."
)
""",
        ),
        markdown(
            "chart-04-note",
            """
The ranking uses current US dollars in the latest year. Exchange rates can move the order. World Bank aggregates are excluded.
""",
        ),
        markdown(
            "arima-heading",
            """
## ARIMA backtest

`p` and `q` run from 0 to 2 with one difference. Each candidate is scored with expanding one-step forecasts from 2013 through the latest World GDP year, then compared with last year's value.

A ten-year projection is published only if the selected ARIMA MAPE is strictly below that baseline. The model uses log nominal GDP. It does not include inflation, policy, or crises.
""",
        ),
        code(
            "chart-05",
            """
backtest_frame = pd.DataFrame(
    {
        "year": list(backtest.years),
        "Observed": list(backtest.observed),
        f"ARIMA{backtest.order}": list(backtest.arima_one_step),
        "Previous-year baseline": list(backtest.naive_one_step),
    }
)
fig = go.Figure()
fig.add_trace(go.Scatter(x=backtest_frame["year"], y=backtest_frame["Observed"], mode="lines+markers", name="Observed"))
fig.add_trace(
    go.Scatter(
        x=backtest_frame["year"],
        y=backtest_frame[f"ARIMA{backtest.order}"],
        mode="lines+markers",
        name=f"ARIMA{backtest.order}",
        line={"dash": "dash"},
    )
)
fig.add_trace(
    go.Scatter(
        x=backtest_frame["year"],
        y=backtest_frame["Previous-year baseline"],
        mode="lines+markers",
        name="Previous-year baseline",
        line={"dash": "dot"},
    )
)
disclose(fig, "gdp-arima-backtest", "5. Nominal World GDP expanding one-step backtest", "gdp_annual")
fig.update_layout(xaxis_title="Year", yaxis_title="Nominal GDP, current US$")
fig.show()
print(
    f"Selected ARIMA{backtest.order}: {backtest.arima_mape:.3f}% MAPE; "
    f"naive baseline: {backtest.naive_mape:.3f}% MAPE."
)
print(projection_decision_text(backtest))
""",
        ),
        code(
            "chart-06",
            """
if projection is None:
    print(projection_decision_text(backtest))
else:
    recent = world_series.loc[world_series.index >= projection.origin_year - 14]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(recent.index),
            y=list(recent.to_numpy()),
            mode="lines+markers",
            name="Observed",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(projection.years),
            y=list(projection.upper),
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
            name="95% upper",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(projection.years),
            y=list(projection.lower),
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            name="95% interval",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(projection.years),
            y=list(projection.median),
            mode="lines+markers",
            name=f"ARIMA{projection.order} median",
        )
    )
    disclose(fig, "gdp-arima-projection", "6. Ten-year World GDP projection", "gdp_annual")
    fig.update_layout(xaxis_title="Year", yaxis_title="Nominal GDP, current US$")
    fig.show()
    print(
        f"Median path: {trillions(world_series.loc[projection.origin_year])} in {projection.origin_year} "
        f"to {trillions(projection.median[-1])} in {projection.years[-1]}."
    )
    print("Bands are 95% intervals on log nominal GDP. They are not a policy forecast.")
""",
        ),
        markdown(
            "chart-06-note",
            """
The projection uses the selected log ARIMA order on current-dollar World GDP. Interval bands widen quickly. This series still mixes real output, inflation, and exchange rates.
""",
        ),
        markdown(
            "conclusion",
            """
## Conclusion

Current-dollar GDP mixes real output, inflation, and exchange rates. A ten-year path is published only when the selected ARIMA specification beats last year's value. The bands are wide. Event-impact claims need a causal design and real GDP. Rankings exclude World Bank aggregates.
""",
        ),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3"},
    }
    return notebook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    notebook = build_notebook()
    if args.execute:
        executor = ExecutePreprocessor(timeout=600, kernel_name="python3")
        executor.preprocess(notebook, {"metadata": {"path": str(ROOT)}})
        for cell in notebook.cells:
            cell.metadata.pop("execution", None)
    nbformat.write(notebook, NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
