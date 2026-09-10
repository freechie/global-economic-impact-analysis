from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_public_profile import generate

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

Charts use World Bank GDP in current US dollars and constant 2015 US dollars, license CC BY 4.0. Numbers come from `gdp_annual.csv` and `gdp_real_annual.csv`. Set `GEIA_DATA_DIR` to load another complete profile. The loader does not fall back to `public-demo`.
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
    country_gdp,
    expanding_arima_backtest,
    expanding_arima_projection,
    latest_gdp_ranking,
    nominal_gdp_story,
    nominal_vs_real_changes,
    projection_decision_text,
    world_gdp_series,
)
from src.data_loader import load_analysis_bundle

pio.renderers.default = "plotly_mimetype"
bundle = load_analysis_bundle()
story = nominal_gdp_story(bundle.gdp_annual)
world_series = world_gdp_series(bundle.gdp_annual)
real_series = world_gdp_series(bundle.gdp_real_annual)
output_checks = nominal_vs_real_changes(world_series, real_series)
backtest = expanding_arima_backtest(world_series)
projection = (
    expanding_arima_projection(world_series, backtest.order)
    if backtest.publishes_projection
    else None
)
OPEN_DISCLOSURES = {
    "gdp_annual": "World Bank Open Data, GDP (current US$). License: CC BY 4.0.",
    "gdp_real_annual": "World Bank Open Data, GDP (constant 2015 US$). License: CC BY 4.0.",
}

def disclose(fig, chart_id, title, table_name, disclosure=None):
    provenance = disclosure or OPEN_DISCLOSURES[table_name]
    fig.update_layout(
        title={"text": f"{title}<br><sup>{provenance}</sup>"},
        template="plotly_white",
        autosize=True,
        meta={
            "chart_id": chart_id,
            "classification": "open",
            "provenance": provenance,
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
    f"The sharpest current-dollar year-over-year declines are {declines}."
)
for check in output_checks:
    print(
        f"{check.year}: current {check.nominal_change_pct:.1f}%, "
        f"constant 2015 {check.real_change_pct:.1f}%."
    )
print("2015 is a dollar year. 2009 and 2020 are real contractions.")
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
        markdown("open-heading", "## GDP charts"),
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
Current-dollar World GDP mixes real output, inflation, and exchange rates. 2015 is the largest drop in this series. 2009 and 2020 were recessions. 2015 was not.
""",
        ),
        code(
            "chart-02",
            """
nominal_yoy = world_series.pct_change() * 100
real_yoy = real_series.pct_change() * 100
years = nominal_yoy.index.intersection(real_yoy.index)
compare = pd.DataFrame(
    {
        "year": years,
        "Current US$": nominal_yoy.loc[years].to_numpy(),
        "Constant 2015 US$": real_yoy.loc[years].to_numpy(),
    }
)
long = compare.melt(id_vars="year", var_name="series", value_name="annual_change_pct")
fig = px.line(
    long.dropna(),
    x="year",
    y="annual_change_pct",
    color="series",
    labels={"annual_change_pct": "Annual change (%)", "series": "Series", "year": "Year"},
)
for year, label in ((2009, "2009"), (2015, "2015 FX"), (2020, "2020")):
    fig.add_vline(x=year, line_dash="dot", annotation_text=label, annotation_position="top")
disclose(
    fig,
    "gdp-nominal-vs-real",
    "2. World GDP annual change, current vs constant 2015 dollars",
    "gdp_real_annual",
    disclosure="World Bank Open Data, GDP current US dollars and constant 2015 US dollars. License: CC BY 4.0.",
).show()
for check in output_checks:
    print(
        f"{check.year}: current {check.nominal_change_pct:.1f}%, "
        f"constant 2015 {check.real_change_pct:.1f}%."
    )
""",
        ),
        markdown(
            "chart-02-note",
            """
Constant 2015 dollars remove most of the exchange-rate and US-inflation movement in the current-dollar series. 2015 is a dollar year. 2009 and 2020 remain real contractions.
""",
        ),
        code(
            "chart-03",
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
disclose(fig, "gdp-selected-trajectories", "3. Selected nominal GDP trajectories, log scale", "gdp_annual").show()
""",
        ),
        markdown(
            "chart-03-note",
            """
Log scale keeps early China and India visible. A linear axis hides them behind the United States. China sits above Japan in 1960 in this file. That early reading is a World Bank current-dollar artifact. The first year China exceeds Japan after 1980 is 2010.
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
The ranking uses current US dollars in the latest year. Exchange rates can change the order. The ranking excludes World Bank aggregates.
""",
        ),
        markdown(
            "arima-heading",
            """
## ARIMA backtest

`p` and `q` run from 0 to 2 with one difference. Each candidate gets expanding one-step forecasts from 2013 through the latest World GDP year. The code compares the winner with last year's value.

The notebook publishes a ten-year projection only if the selected ARIMA MAPE is strictly below that baseline. The model uses log nominal GDP. It does not model inflation or policy.
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
The projection uses the selected log ARIMA order on current-dollar World GDP. Interval bands widen quickly. Current-dollar GDP still mixes real output, inflation, and exchange rates.
""",
        ),
        markdown(
            "conclusion",
            """
## Conclusion

Current-dollar GDP mixes real output, inflation, and exchange rates. Constant 2015 dollars show 2015 as a dollar year. They keep 2009 and 2020 as real contractions. The notebook publishes a ten-year path only when the selected ARIMA specification beats last year's value. The bands are wide. These charts cannot measure the effect of an event. That needs a causal design. Rankings exclude World Bank aggregates.
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
        generate()
        executor = ExecutePreprocessor(timeout=600, kernel_name="python3")
        executor.preprocess(notebook, {"metadata": {"path": str(ROOT)}})
        for cell in notebook.cells:
            cell.metadata.pop("execution", None)
    nbformat.write(notebook, NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
