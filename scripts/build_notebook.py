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

This notebook contains 14 interactive Plotly figures. Figures 1 through 5 use World Bank Open Data for GDP under the CC BY 4.0 license. Figures 6 through 14 use deterministic synthetic demonstration data. Synthetic values are fictional and are not observed measurements.

The `public-demo` profile is the default. Set `GEIA_DATA_DIR` before execution to select a complete compatible local profile. The loader validates the selected profile and never falls back to another directory.
""",
        ),
        code(
            "setup",
            """
from pathlib import Path
import sys

import plotly.express as px
import plotly.io as pio

ROOT = Path.cwd()
if not (ROOT / "src").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src.analysis_utils import annual_percent_change, country_gdp, latest_gdp_ranking
from src.data_loader import load_analysis_bundle

pio.renderers.default = "plotly_mimetype"
bundle = load_analysis_bundle()
OPEN_DISCLOSURE = "World Bank Open Data, GDP (current US$). License: CC BY 4.0."
SYNTHETIC_DISCLOSURE = "Synthetic demonstration data. Values are fictional and are not observed measurements."

def disclose(fig, chart_id, title, classification, table_name):
    disclosure = OPEN_DISCLOSURE if classification == "open" else SYNTHETIC_DISCLOSURE
    fig.update_layout(
        title={"text": f"{title}<br><sup>{disclosure}</sup>"},
        template="plotly_white",
        autosize=True,
        meta={
            "chart_id": chart_id,
            "classification": classification,
            "provenance": disclosure,
            "table": table_name,
            "profile_id": bundle.profile.profile_id,
        },
    )
    return fig
""",
        ),
        markdown("open-heading", "## Open-data GDP figures"),
        code(
            "chart-01",
            """
world = bundle.gdp_annual.loc[bundle.gdp_annual["country_code"] == "WLD"]
fig = px.line(world, x="year", y="nominal_gdp_usd", labels={"nominal_gdp_usd": "Current US$", "year": "Year"})
disclose(fig, "gdp-world-trend", "1. World nominal GDP over time", "open", "gdp_annual").show()
""",
        ),
        code(
            "chart-02",
            """
selected_names = ["United States", "China", "Japan", "Germany", "India"]
selected = country_gdp(bundle.gdp_annual).loc[lambda frame: frame["country_name"].isin(selected_names)]
fig = px.line(selected, x="year", y="nominal_gdp_usd", color="country_name", labels={"nominal_gdp_usd": "Current US$", "country_name": "Country", "year": "Year"})
disclose(fig, "gdp-selected-trajectories", "2. Selected nominal GDP trajectories", "open", "gdp_annual").show()
""",
        ),
        code(
            "chart-03",
            """
growth = annual_percent_change(selected, group_column="country_name", value_column="nominal_gdp_usd")
fig = px.line(growth.dropna(subset=["annual_change_pct"]), x="year", y="annual_change_pct", color="country_name", labels={"annual_change_pct": "Annual change (%)", "country_name": "Country", "year": "Year"})
disclose(fig, "gdp-annual-change", "3. Annual nominal GDP change", "open", "gdp_annual").show()
""",
        ),
        code(
            "chart-04",
            """
countries = country_gdp(bundle.gdp_annual)
fig = px.choropleth(countries, locations="country_code", color="nominal_gdp_usd", hover_name="country_name", animation_frame="year", color_continuous_scale="Blues", labels={"nominal_gdp_usd": "Current US$", "year": "Year"})
disclose(fig, "gdp-country-map", "4. Nominal GDP by country over time", "open", "gdp_annual").show()
""",
        ),
        code(
            "chart-05",
            """
ranking = latest_gdp_ranking(bundle.gdp_annual, limit=15)
ranking_year = int(ranking["year"].iloc[0])
fig = px.bar(ranking, x="nominal_gdp_usd", y="country_name", orientation="h", labels={"nominal_gdp_usd": "Current US$", "country_name": "Country"})
disclose(fig, "gdp-latest-ranking", f"5. Largest nominal GDP observations in {ranking_year}", "open", "gdp_annual").show()
""",
        ),
        markdown(
            "synthetic-heading",
            """
## Synthetic demonstration figures

The remaining figures demonstrate chart behavior and the canonical table contract. Do not interpret their values as historical, market, budget, credit, or survey observations.
""",
        ),
        code(
            "chart-06",
            """
inbound_categories = bundle.arms_by_category_annual.loc[lambda frame: frame["direction"] == "inbound"]
fig = px.area(inbound_categories, x="year", y="activity_value", color="category", groupnorm="percent", labels={"activity_value": "Share (%)", "category": "Illustrative category", "year": "Year"})
disclose(fig, "transfer-inbound-composition", "6. Illustrative inbound transfer activity composition", "synthetic", "arms_by_category_annual").show()
""",
        ),
        code(
            "chart-07",
            """
outbound_categories = bundle.arms_by_category_annual.loc[lambda frame: frame["direction"] == "outbound"]
fig = px.line(outbound_categories, x="year", y="activity_value", color="category", labels={"activity_value": "Fictional activity index", "category": "Illustrative category", "year": "Year"})
disclose(fig, "transfer-outbound-categories", "7. Illustrative outbound transfer activity", "synthetic", "arms_by_category_annual").show()
""",
        ),
        code(
            "chart-08",
            """
entities = bundle.arms_by_entity_annual
scenario_map = entities.loc[(entities["direction"] == "inbound") & (entities["mapping_status"] == "mapped")]
fig = px.choropleth(scenario_map, locations="country_code", color="activity_value", hover_name="source_entity", animation_frame="year", color_continuous_scale="Oranges", labels={"activity_value": "Fictional activity index", "year": "Year"})
disclose(fig, "transfer-geographic-scenarios", "8. Geographic transfer scenarios over time", "synthetic", "arms_by_entity_annual").show()
""",
        ),
        code(
            "chart-09",
            """
scenario_lines = entities.loc[(entities["direction"] == "outbound") & (entities["mapping_status"] == "mapped")]
fig = px.line(scenario_lines, x="year", y="activity_value", color="source_entity", labels={"activity_value": "Fictional activity index", "source_entity": "Geographic scenario", "year": "Year"})
disclose(fig, "transfer-entity-scenarios", "9. Illustrative outbound geographic scenarios", "synthetic", "arms_by_entity_annual").show()
""",
        ),
        code(
            "chart-10",
            """
fig = px.bar(bundle.aircraft_orders_monthly, x="date", y="net_orders", color="manufacturer", barmode="group", labels={"net_orders": "Fictional net orders", "manufacturer": "Manufacturer", "date": "Month"})
disclose(fig, "aircraft-orders", "10. Monthly net aircraft orders", "synthetic", "aircraft_orders_monthly").show()
""",
        ),
        code(
            "chart-11",
            """
fig = px.area(bundle.defense_budget_annual, x="request_year", y="nominal_usd_bn", color="category", labels={"nominal_usd_bn": "Fictional nominal US$ billions", "category": "Illustrative category", "request_year": "Request year"})
disclose(fig, "defense-budget-categories", "11. Illustrative budget categories", "synthetic", "defense_budget_annual").show()
""",
        ),
        code(
            "chart-12",
            """
fig = px.bar(bundle.cyber_fund_flows_monthly, x="date", y="net_flow_usd_m", color="fund", barmode="group", labels={"net_flow_usd_m": "Fictional net flow (US$ millions)", "fund": "Fund", "date": "Month"})
disclose(fig, "cyber-fund-flows", "12. Monthly cybersecurity fund flows", "synthetic", "cyber_fund_flows_monthly").show()
""",
        ),
        code(
            "chart-13",
            """
fig = px.line(bundle.airline_cds_monthly, x="date", y="spread_bps", color="region", labels={"spread_bps": "Fictional spread (basis points)", "region": "Region", "date": "Month"})
disclose(fig, "airline-credit-spreads", "13. Regional airline credit spread scenarios", "synthetic", "airline_cds_monthly").show()
""",
        ),
        code(
            "chart-14",
            """
fig = px.line(bundle.homebuilder_confidence_annual, x="year", y="index_value", markers=True, labels={"index_value": "Fictional confidence index", "year": "Year"})
disclose(fig, "homebuilder-confidence", "14. Year-end homebuilder confidence scenario", "synthetic", "homebuilder_confidence_annual").show()
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
