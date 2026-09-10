from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

import pandas as pd

SCHEMA_VERSION = "1.0"
PUBLIC_PROFILE_ID = "public-demo"
PUBLIC_OPEN_TABLES = frozenset({"gdp_annual", "gdp_real_annual"})
SYNTHETIC_DISCLOSURE = "Synthetic demonstration data. Values are fictional and are not observed measurements."


class DataLoadError(RuntimeError):
    """Raised when an analysis profile fails directory-boundary validation."""


@dataclass(frozen=True)
class DatasetSpec:
    filename: str
    columns: tuple[str, ...]
    string_columns: tuple[str, ...] = ()
    integer_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()
    nullable_columns: tuple[str, ...] = ()
    nonnegative_columns: tuple[str, ...] = ()
    unique_key: tuple[str, ...] = ()


DATASET_SPECS: Mapping[str, DatasetSpec] = MappingProxyType(
    {
        "gdp_annual": DatasetSpec(
            "gdp_annual.csv",
            ("country_name", "country_code", "year", "nominal_gdp_usd", "is_aggregate"),
            string_columns=("country_name", "country_code", "is_aggregate"),
            integer_columns=("year",),
            numeric_columns=("nominal_gdp_usd",),
            nonnegative_columns=("nominal_gdp_usd",),
            unique_key=("country_code", "year"),
        ),
        "gdp_real_annual": DatasetSpec(
            "gdp_real_annual.csv",
            ("country_name", "country_code", "year", "real_gdp_2015_usd", "is_aggregate"),
            string_columns=("country_name", "country_code", "is_aggregate"),
            integer_columns=("year",),
            numeric_columns=("real_gdp_2015_usd",),
            nonnegative_columns=("real_gdp_2015_usd",),
            unique_key=("country_code", "year"),
        ),
        "arms_by_category_annual": DatasetSpec(
            "arms_by_category_annual.csv",
            ("direction", "category", "year", "activity_value"),
            string_columns=("direction", "category"),
            integer_columns=("year",),
            numeric_columns=("activity_value",),
            nonnegative_columns=("activity_value",),
            unique_key=("direction", "category", "year"),
        ),
        "arms_by_entity_annual": DatasetSpec(
            "arms_by_entity_annual.csv",
            (
                "direction",
                "source_entity",
                "country_name",
                "country_code",
                "mapping_status",
                "exclusion_reason",
                "year",
                "activity_value",
            ),
            string_columns=(
                "direction",
                "source_entity",
                "country_name",
                "country_code",
                "mapping_status",
                "exclusion_reason",
            ),
            integer_columns=("year",),
            numeric_columns=("activity_value",),
            nullable_columns=("country_name", "country_code", "exclusion_reason"),
            nonnegative_columns=("activity_value",),
            unique_key=("direction", "source_entity", "year"),
        ),
        "aircraft_orders_monthly": DatasetSpec(
            "aircraft_orders_monthly.csv",
            ("date", "manufacturer", "net_orders"),
            string_columns=("manufacturer",),
            integer_columns=("net_orders",),
            date_columns=("date",),
            unique_key=("date", "manufacturer"),
        ),
        "defense_budget_annual": DatasetSpec(
            "defense_budget_annual.csv",
            ("request_year", "category", "nominal_usd_bn"),
            string_columns=("category",),
            integer_columns=("request_year",),
            numeric_columns=("nominal_usd_bn",),
            nonnegative_columns=("nominal_usd_bn",),
            unique_key=("request_year", "category"),
        ),
        "cyber_fund_flows_monthly": DatasetSpec(
            "cyber_fund_flows_monthly.csv",
            ("date", "fund", "net_flow_usd_m"),
            string_columns=("fund",),
            numeric_columns=("net_flow_usd_m",),
            date_columns=("date",),
            unique_key=("date", "fund"),
        ),
        "airline_cds_monthly": DatasetSpec(
            "airline_cds_monthly.csv",
            ("date", "region", "spread_bps"),
            string_columns=("region",),
            numeric_columns=("spread_bps",),
            date_columns=("date",),
            nonnegative_columns=("spread_bps",),
            unique_key=("date", "region"),
        ),
        "homebuilder_confidence_annual": DatasetSpec(
            "homebuilder_confidence_annual.csv",
            ("year", "index_value"),
            integer_columns=("year",),
            numeric_columns=("index_value",),
            unique_key=("year",),
        ),
    }
)


@dataclass(frozen=True)
class AnalysisProfile:
    schema_version: str
    profile_id: str
    description: str
    directory: Path
    datasets: Mapping[str, Mapping[str, object]]

    def metadata_for(self, table_name: str) -> Mapping[str, object]:
        return self.datasets[table_name]


@dataclass(frozen=True)
class AnalysisBundle:
    profile: AnalysisProfile
    gdp_annual: pd.DataFrame
    gdp_real_annual: pd.DataFrame
    arms_by_category_annual: pd.DataFrame
    arms_by_entity_annual: pd.DataFrame
    aircraft_orders_monthly: pd.DataFrame
    defense_budget_annual: pd.DataFrame
    cyber_fund_flows_monthly: pd.DataFrame
    airline_cds_monthly: pd.DataFrame
    homebuilder_confidence_annual: pd.DataFrame

    def table(self, table_name: str) -> pd.DataFrame:
        if table_name not in DATASET_SPECS:
            raise KeyError(table_name)
        return getattr(self, table_name)


def _default_public_profile_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "profiles" / PUBLIC_PROFILE_ID


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _profile_directory(data_dir: str | Path | None) -> Path:
    if data_dir is not None:
        return Path(data_dir).expanduser().resolve()
    configured = os.environ.get("GEIA_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_public_profile_dir()


def _validate_manifest(raw: object) -> tuple[dict[str, object], list[str]]:
    problems: list[str] = []
    if not isinstance(raw, dict):
        return {}, ["profile.json: root must be an object"]

    schema_version = raw.get("schema_version")
    profile_id = raw.get("profile_id")
    description = raw.get("description")
    datasets = raw.get("datasets")
    if schema_version != SCHEMA_VERSION:
        problems.append(f"profile.json: schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(profile_id, str) or not profile_id.strip():
        problems.append("profile.json: profile_id must be a nonempty string")
    if not isinstance(description, str) or not description.strip():
        problems.append("profile.json: description must be a nonempty string")
    if not isinstance(datasets, dict):
        problems.append("profile.json: datasets must be an object")
        datasets = {}

    missing = sorted(set(DATASET_SPECS) - set(datasets))
    extra = sorted(set(datasets) - set(DATASET_SPECS))
    if missing:
        problems.append("profile.json: missing datasets " + ", ".join(missing))
    if extra:
        problems.append("profile.json: unknown datasets " + ", ".join(extra))

    for table_name in sorted(set(DATASET_SPECS) & set(datasets)):
        entry = datasets[table_name]
        if not isinstance(entry, dict):
            problems.append(f"profile.json: {table_name} metadata must be an object")
            continue
        if entry.get("filename") != DATASET_SPECS[table_name].filename:
            problems.append(
                f"profile.json: {table_name} filename must be {DATASET_SPECS[table_name].filename!r}"
            )
        if entry.get("classification") not in {"open", "synthetic", "licensed"}:
            problems.append(
                f"profile.json: {table_name} classification must be open, synthetic, or licensed"
            )
        sha256 = entry.get("sha256")
        if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            problems.append(
                f"profile.json: {table_name} sha256 must be lowercase hexadecimal"
            )
        provenance_key = (
            "generator" if entry.get("classification") == "synthetic" else "source"
        )
        provenance = entry.get(provenance_key)
        if not isinstance(provenance, dict) or not provenance:
            problems.append(
                f"profile.json: {table_name} requires {provenance_key} metadata"
            )
        if profile_id == PUBLIC_PROFILE_ID:
            expected_classification = (
                "open" if table_name in PUBLIC_OPEN_TABLES else "synthetic"
            )
            if entry.get("classification") != expected_classification:
                problems.append(
                    f"profile.json: public-demo {table_name} must be {expected_classification}"
                )
            if table_name in PUBLIC_OPEN_TABLES and isinstance(provenance, dict):
                if provenance.get("license") != "CC BY 4.0" or "World Bank" not in str(
                    provenance.get("name", "")
                ):
                    problems.append(
                        f"profile.json: public-demo {table_name} requires World Bank and CC BY 4.0 attribution"
                    )
            if table_name not in PUBLIC_OPEN_TABLES and isinstance(provenance, dict):
                if provenance.get("disclosure") != SYNTHETIC_DISCLOSURE:
                    problems.append(
                        f"profile.json: public-demo {table_name} requires the synthetic disclosure"
                    )

    return raw, problems


def _validate_table(
    table_name: str, frame: pd.DataFrame, spec: DatasetSpec
) -> tuple[pd.DataFrame, list[str]]:
    problems: list[str] = []
    expected = list(spec.columns)
    if list(frame.columns) != expected:
        return frame, [f"{spec.filename}: columns must be {', '.join(expected)}"]
    if frame.empty:
        problems.append(f"{spec.filename}: table must not be empty")

    parsed = frame.copy()
    for column in spec.string_columns:
        parsed[column] = parsed[column].astype("string")
        if (
            column not in spec.nullable_columns
            and (parsed[column].isna() | (parsed[column].str.strip() == "")).any()
        ):
            problems.append(f"{spec.filename}: {column} contains blank values")

    for column in spec.integer_columns:
        numeric = pd.to_numeric(parsed[column], errors="coerce")
        if numeric.isna().any() or ((numeric % 1) != 0).any():
            problems.append(f"{spec.filename}: {column} must contain integers")
        else:
            parsed[column] = numeric.astype("int64")

    for column in spec.numeric_columns:
        numeric = pd.to_numeric(parsed[column], errors="coerce")
        if numeric.isna().any():
            problems.append(f"{spec.filename}: {column} must contain numbers")
        else:
            parsed[column] = numeric.astype("float64")

    for column in spec.date_columns:
        dates = pd.to_datetime(parsed[column], format="%Y-%m-%d", errors="coerce")
        if dates.isna().any():
            problems.append(f"{spec.filename}: {column} must use YYYY-MM-DD dates")
        else:
            parsed[column] = dates

    for column in spec.nonnegative_columns:
        if (
            column in parsed
            and pd.api.types.is_numeric_dtype(parsed[column])
            and (parsed[column] < 0).any()
        ):
            problems.append(f"{spec.filename}: {column} must be nonnegative")

    if "is_aggregate" in parsed.columns:
        aggregate_flags = parsed["is_aggregate"].str.lower()
        if not set(aggregate_flags.dropna()).issubset({"true", "false"}):
            problems.append(f"{spec.filename}: is_aggregate must contain true or false")
        else:
            parsed["is_aggregate"] = aggregate_flags.map({"true": True, "false": False})

    if table_name in {"arms_by_category_annual", "arms_by_entity_annual"}:
        directions = set(parsed["direction"].dropna())
        if not directions.issubset({"inbound", "outbound"}):
            problems.append(f"{spec.filename}: direction must be inbound or outbound")

    if table_name == "arms_by_entity_annual":
        statuses = set(parsed["mapping_status"].dropna())
        if not statuses.issubset({"mapped", "excluded"}):
            problems.append(
                f"{spec.filename}: mapping_status must be mapped or excluded"
            )
        mapped = parsed["mapping_status"].eq("mapped")
        excluded = parsed["mapping_status"].eq("excluded")
        if parsed.loc[mapped, ["country_name", "country_code"]].isna().any().any():
            problems.append(
                f"{spec.filename}: mapped rows require country_name and country_code"
            )
        if parsed.loc[excluded, "exclusion_reason"].isna().any():
            problems.append(f"{spec.filename}: excluded rows require exclusion_reason")

    if spec.unique_key and parsed.duplicated(list(spec.unique_key)).any():
        problems.append(
            f"{spec.filename}: duplicate key rows for {', '.join(spec.unique_key)}"
        )
    return parsed, problems


def load_analysis_bundle(data_dir: str | Path | None = None) -> AnalysisBundle:
    """Load one complete profile and fail without returning partial data."""

    profile_dir = _profile_directory(data_dir)
    manifest_path = profile_dir / "profile.json"
    if not profile_dir.is_dir():
        raise DataLoadError(f"Analysis profile directory not found: {profile_dir}")
    if not manifest_path.is_file():
        raise DataLoadError(f"Analysis profile manifest not found: {manifest_path}")

    try:
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DataLoadError(f"profile.json: could not be read ({exc})") from exc

    manifest, problems = _validate_manifest(raw_manifest)
    entries = manifest.get("datasets", {}) if isinstance(manifest, dict) else {}
    loaded: dict[str, pd.DataFrame] = {}

    for table_name, spec in DATASET_SPECS.items():
        path = profile_dir / spec.filename
        entry = entries.get(table_name, {}) if isinstance(entries, dict) else {}
        if not path.is_file():
            problems.append(f"{spec.filename}: file is missing")
            continue
        if isinstance(entry, dict) and isinstance(entry.get("sha256"), str):
            if _sha256(path) != entry["sha256"]:
                problems.append(f"{spec.filename}: SHA-256 does not match profile.json")
        try:
            frame = pd.read_csv(path, keep_default_na=True)
        except Exception as exc:
            problems.append(f"{spec.filename}: could not be read ({exc})")
            continue
        parsed, table_problems = _validate_table(table_name, frame, spec)
        problems.extend(table_problems)
        if not table_problems:
            loaded[table_name] = parsed

    if problems:
        raise DataLoadError("Invalid analysis profile:\n- " + "\n- ".join(problems))

    dataset_metadata = {
        name: MappingProxyType(dict(value)) for name, value in entries.items()
    }
    profile = AnalysisProfile(
        schema_version=str(manifest["schema_version"]),
        profile_id=str(manifest["profile_id"]),
        description=str(manifest["description"]),
        directory=profile_dir,
        datasets=MappingProxyType(dataset_metadata),
    )
    return AnalysisBundle(profile=profile, **loaded)
