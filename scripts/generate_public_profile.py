from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis_utils import WORLD_BANK_AGGREGATE_CODES
from src.data_loader import DATASET_SPECS, PUBLIC_PROFILE_ID, SCHEMA_VERSION

OUTPUT_DIR = ROOT / "data" / "profiles" / PUBLIC_PROFILE_ID
SYNTHETIC_DISCLOSURE = "Synthetic demonstration data. Values are fictional and are not observed measurements."


def _gdp_source(explicit_source: Path | None) -> Path:
    candidates = [
        explicit_source,
        OUTPUT_DIR / "gdp_annual.csv",
        ROOT / "data" / "open" / "world-bank" / "gdp.csv",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError("No World Bank GDP source is available")


def normalize_gdp(source: Path) -> pd.DataFrame:
    frame = pd.read_csv(source)
    canonical = list(DATASET_SPECS["gdp_annual"].columns)
    if list(frame.columns) == canonical:
        result = frame.copy()
        result["is_aggregate"] = result["is_aggregate"].astype(str).str.lower()
        return result.sort_values(["country_code", "year"]).reset_index(drop=True)

    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame["GDP"] = pd.to_numeric(frame["GDP"], errors="coerce")
    frame = frame[
        frame["Series Code"].astype(str).str.strip().eq("NY.GDP.MKTP.CD")
    ].copy()
    frame["Country Name"] = frame["Country Name"].astype("string").str.strip()
    frame["Country Code"] = frame["Country Code"].astype("string").str.strip()
    frame = frame.dropna(subset=["Country Name", "Country Code", "Year", "GDP"])
    frame = frame[
        frame["Country Name"].ne("0")
        & frame["Country Code"].ne("0")
        & frame["GDP"].gt(0)
    ].copy()
    frame["year"] = frame["Year"].astype(int)
    frame["nominal_gdp_usd"] = frame["GDP"].round(2)
    frame["country_name"] = frame["Country Name"]
    frame["country_code"] = frame["Country Code"]
    frame["is_aggregate"] = (
        frame["country_code"]
        .isin(WORLD_BANK_AGGREGATE_CODES)
        .map({True: "true", False: "false"})
    )
    result = frame[canonical].drop_duplicates(["country_code", "year"])
    return result.sort_values(["country_code", "year"]).reset_index(drop=True)


def arms_by_category_annual() -> pd.DataFrame:
    rows = []
    categories = [
        "Illustrative Air Systems",
        "Illustrative Land Systems",
        "Illustrative Maritime Systems",
        "Illustrative Support Systems",
    ]
    for direction_index, direction in enumerate(("inbound", "outbound")):
        for category_index, category in enumerate(categories):
            for year in range(2000, 2024):
                offset = year - 2000
                value = 85 + direction_index * 18 + category_index * 27 + offset * 3
                value += ((offset + 2 * category_index) % 7) * 4
                rows.append((direction, category, year, round(value, 2)))
    return pd.DataFrame(rows, columns=DATASET_SPECS["arms_by_category_annual"].columns)


def arms_by_entity_annual() -> pd.DataFrame:
    rows = []
    scenarios = [
        ("Geographic scenario: United States", "United States", "USA"),
        ("Geographic scenario: China", "China", "CHN"),
        ("Geographic scenario: India", "India", "IND"),
        ("Geographic scenario: France", "France", "FRA"),
        ("Geographic scenario: Brazil", "Brazil", "BRA"),
    ]
    for direction_index, direction in enumerate(("inbound", "outbound")):
        for scenario_index, (source_entity, country_name, country_code) in enumerate(
            scenarios
        ):
            for year in range(2000, 2024):
                offset = year - 2000
                value = 70 + direction_index * 21 + scenario_index * 19 + offset * 2
                value += ((offset + scenario_index) % 5) * 5
                rows.append(
                    (
                        direction,
                        source_entity,
                        country_name,
                        country_code,
                        "mapped",
                        None,
                        year,
                        round(value, 2),
                    )
                )
        for year in range(2000, 2024):
            rows.append(
                (
                    direction,
                    "Unmapped fictional scenario",
                    None,
                    None,
                    "excluded",
                    "No geographic scenario mapping",
                    year,
                    round(12 + direction_index * 3 + (year - 2000) % 4, 2),
                )
            )
    return pd.DataFrame(rows, columns=DATASET_SPECS["arms_by_entity_annual"].columns)


def aircraft_orders_monthly() -> pd.DataFrame:
    rows = []
    for date_index, date in enumerate(
        pd.date_range("2016-01-01", "2024-12-01", freq="MS")
    ):
        for maker_index, maker in enumerate(("Manufacturer A", "Manufacturer B")):
            value = (
                18
                + maker_index * 5
                + int(14 * math.sin((date_index + maker_index * 3) / 4))
            )
            value += (date_index % 6) - 3
            rows.append((date.strftime("%Y-%m-%d"), maker, value))
    return pd.DataFrame(rows, columns=DATASET_SPECS["aircraft_orders_monthly"].columns)


def defense_budget_annual() -> pd.DataFrame:
    rows = []
    categories = [
        "Illustrative Personnel",
        "Illustrative Operations",
        "Illustrative Equipment",
        "Illustrative Research",
    ]
    for category_index, category in enumerate(categories):
        for year in range(2000, 2025):
            offset = year - 2000
            value = 52 + category_index * 19 + offset * (1.7 + category_index * 0.35)
            value += ((offset + category_index) % 4) * 1.25
            rows.append((year, category, round(value, 2)))
    return pd.DataFrame(rows, columns=DATASET_SPECS["defense_budget_annual"].columns)


def cyber_fund_flows_monthly() -> pd.DataFrame:
    rows = []
    for date_index, date in enumerate(
        pd.date_range("2022-01-01", "2024-12-01", freq="MS")
    ):
        for fund_index, fund in enumerate(("Fund A", "Fund B", "Fund C")):
            value = 8 * math.sin((date_index + fund_index * 2) / 2.7)
            value += fund_index * 2.5 + (date_index % 5) - 2
            rows.append((date.strftime("%Y-%m-%d"), fund, round(value, 2)))
    return pd.DataFrame(rows, columns=DATASET_SPECS["cyber_fund_flows_monthly"].columns)


def airline_cds_monthly() -> pd.DataFrame:
    rows = []
    for date_index, date in enumerate(
        pd.date_range("2018-01-01", "2024-12-01", freq="MS")
    ):
        pulse = max(0, 20 - abs(date_index - 29)) * 8
        for region_index, region in enumerate(("Region A", "Region B")):
            value = (
                95
                + region_index * 24
                + pulse
                + 12 * math.sin((date_index + region_index) / 5)
            )
            rows.append((date.strftime("%Y-%m-%d"), region, round(value, 2)))
    return pd.DataFrame(rows, columns=DATASET_SPECS["airline_cds_monthly"].columns)


def homebuilder_confidence_annual() -> pd.DataFrame:
    rows = []
    for year in range(1985, 2025):
        offset = year - 1985
        value = 52 + 13 * math.sin(offset / 3.1) + 5 * math.cos(offset / 6.3)
        rows.append((year, round(value, 2)))
    return pd.DataFrame(
        rows, columns=DATASET_SPECS["homebuilder_confidence_annual"].columns
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.2f")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(gdp_source: Path | None = None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = {
        "gdp_annual": normalize_gdp(_gdp_source(gdp_source)),
        "arms_by_category_annual": arms_by_category_annual(),
        "arms_by_entity_annual": arms_by_entity_annual(),
        "aircraft_orders_monthly": aircraft_orders_monthly(),
        "defense_budget_annual": defense_budget_annual(),
        "cyber_fund_flows_monthly": cyber_fund_flows_monthly(),
        "airline_cds_monthly": airline_cds_monthly(),
        "homebuilder_confidence_annual": homebuilder_confidence_annual(),
    }
    for table_name, frame in tables.items():
        _write_csv(frame, OUTPUT_DIR / DATASET_SPECS[table_name].filename)

    datasets = {}
    for table_name, spec in DATASET_SPECS.items():
        entry = {
            "classification": "open" if table_name == "gdp_annual" else "synthetic",
            "filename": spec.filename,
            "sha256": _sha256(OUTPUT_DIR / spec.filename),
        }
        if table_name == "gdp_annual":
            entry["source"] = {
                "changes": "Normalized to canonical columns, removed invalid and nonpositive observations, and added aggregate flags.",
                "coverage": {
                    "end_year": int(tables[table_name]["year"].max()),
                    "start_year": int(tables[table_name]["year"].min()),
                },
                "license": "CC BY 4.0",
                "name": "World Bank Open Data, GDP (current US$)",
                "series_code": "NY.GDP.MKTP.CD",
                "url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
            }
        else:
            entry["generator"] = {
                "disclosure": SYNTHETIC_DISCLOSURE,
                "formula_version": "1",
                "script": "scripts/generate_public_profile.py",
            }
        datasets[table_name] = entry

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": PUBLIC_PROFILE_ID,
        "description": "Public profile with World Bank open GDP data and deterministic synthetic demonstration tables.",
        "datasets": datasets,
    }
    (OUTPUT_DIR / "profile.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gdp-source", type=Path)
    args = parser.parse_args()
    generate(args.gdp_source)


if __name__ == "__main__":
    main()
