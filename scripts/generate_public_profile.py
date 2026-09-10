from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis_utils import WORLD_BANK_AGGREGATE_CODES
from src.data_loader import DATASET_SPECS, PUBLIC_PROFILE_ID, SCHEMA_VERSION

OPEN_GDP_SOURCES = {
    "gdp_annual": {
        "name": "World Bank Open Data, GDP (current US$)",
        "open_filename": "gdp.csv",
        "series_code": "NY.GDP.MKTP.CD",
        "url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        "value_column": "nominal_gdp_usd",
    },
    "gdp_real_annual": {
        "name": "World Bank Open Data, GDP (constant 2015 US$)",
        "open_filename": "gdp-real.csv",
        "series_code": "NY.GDP.MKTP.KD",
        "url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD",
        "value_column": "real_gdp_2015_usd",
    },
}

OUTPUT_DIR = ROOT / "data" / "profiles" / PUBLIC_PROFILE_ID
PROFILE_KEEP = {spec.filename for spec in DATASET_SPECS.values()} | {
    "profile.json",
    "README.md",
}


def _table_source(
    explicit_source: Path | None, *, canonical_filename: str, open_filename: str
) -> Path:
    candidates = [
        explicit_source,
        OUTPUT_DIR / canonical_filename,
        ROOT / "data" / "open" / "world-bank" / open_filename,
    ]
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No World Bank source is available for {canonical_filename}")


def normalize_gdp(source: Path, *, table_name: str) -> pd.DataFrame:
    open_source = OPEN_GDP_SOURCES[table_name]
    canonical = list(DATASET_SPECS[table_name].columns)
    value_column = open_source["value_column"]
    frame = pd.read_csv(source)
    if list(frame.columns) == canonical:
        result = frame.copy()
        result["is_aggregate"] = result["is_aggregate"].astype(str).str.lower()
        return result.sort_values(["country_code", "year"]).reset_index(drop=True)

    series_code = open_source["series_code"]
    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame["GDP"] = pd.to_numeric(frame["GDP"], errors="coerce")
    frame = frame[frame["Series Code"].astype(str).str.strip().eq(series_code)].copy()
    frame["Country Name"] = frame["Country Name"].astype("string").str.strip()
    frame["Country Code"] = frame["Country Code"].astype("string").str.strip()
    frame = frame.dropna(subset=["Country Name", "Country Code", "Year", "GDP"])
    frame = frame[
        frame["Country Name"].ne("0")
        & frame["Country Code"].ne("0")
        & frame["GDP"].gt(0)
    ].copy()
    if frame.empty:
        raise ValueError(f"{source} has no {series_code} rows")
    frame["year"] = frame["Year"].astype(int)
    frame[value_column] = frame["GDP"].round(2)
    frame["country_name"] = frame["Country Name"]
    frame["country_code"] = frame["Country Code"]
    frame["is_aggregate"] = (
        frame["country_code"]
        .isin(WORLD_BANK_AGGREGATE_CODES)
        .map({True: "true", False: "false"})
    )
    result = frame[canonical].drop_duplicates(["country_code", "year"])
    return result.sort_values(["country_code", "year"]).reset_index(drop=True)


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.2f")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(
    gdp_source: Path | None = None, gdp_real_source: Path | None = None
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = {
        "gdp_annual": normalize_gdp(
            _table_source(
                gdp_source,
                canonical_filename="gdp_annual.csv",
                open_filename=OPEN_GDP_SOURCES["gdp_annual"]["open_filename"],
            ),
            table_name="gdp_annual",
        ),
        "gdp_real_annual": normalize_gdp(
            _table_source(
                gdp_real_source,
                canonical_filename="gdp_real_annual.csv",
                open_filename=OPEN_GDP_SOURCES["gdp_real_annual"]["open_filename"],
            ),
            table_name="gdp_real_annual",
        ),
    }
    for table_name, frame in tables.items():
        _write_csv(frame, OUTPUT_DIR / DATASET_SPECS[table_name].filename)
    for path in OUTPUT_DIR.iterdir():
        if path.is_file() and path.name not in PROFILE_KEEP:
            path.unlink()

    datasets = {}
    for table_name, spec in DATASET_SPECS.items():
        open_source = OPEN_GDP_SOURCES[table_name]
        datasets[table_name] = {
            "classification": "open",
            "filename": spec.filename,
            "sha256": _sha256(OUTPUT_DIR / spec.filename),
            "source": {
                "changes": "Normalized to canonical columns, removed invalid and nonpositive observations, and added aggregate flags.",
                "coverage": {
                    "end_year": int(tables[table_name]["year"].max()),
                    "start_year": int(tables[table_name]["year"].min()),
                },
                "license": "CC BY 4.0",
                "name": open_source["name"],
                "series_code": open_source["series_code"],
                "url": open_source["url"],
            },
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": PUBLIC_PROFILE_ID,
        "description": "Public World Bank GDP in current and constant 2015 US dollars.",
        "datasets": datasets,
    }
    (OUTPUT_DIR / "profile.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gdp-source", type=Path)
    parser.add_argument("--gdp-real-source", type=Path)
    args = parser.parse_args()
    generate(args.gdp_source, args.gdp_real_source)


if __name__ == "__main__":
    main()
