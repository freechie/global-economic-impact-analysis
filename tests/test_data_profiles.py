from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from scripts import generate_public_profile as generator
from src.data_loader import (
    DATASET_SPECS,
    DataLoadError,
    load_analysis_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PROFILE = ROOT / "data" / "profiles" / "public-demo"


def _artifact_bytes(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "README.md"
    }


def test_generator_is_byte_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output = tmp_path / "public-demo"
    monkeypatch.setattr(generator, "OUTPUT_DIR", output)
    gdp_source = PUBLIC_PROFILE / "gdp_annual.csv"

    generator.generate(gdp_source)
    first = _artifact_bytes(output)
    generator.generate(gdp_source)
    second = _artifact_bytes(output)

    assert first == second


def test_manifest_hashes_and_provenance_match_public_files():
    manifest = json.loads((PUBLIC_PROFILE / "profile.json").read_text())

    assert manifest["schema_version"] == "1.0"
    assert manifest["profile_id"] == "public-demo"
    assert set(manifest["datasets"]) == set(DATASET_SPECS)
    for table_name, entry in manifest["datasets"].items():
        path = PUBLIC_PROFILE / entry["filename"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        if table_name == "gdp_annual":
            assert entry["classification"] == "open"
            assert entry["source"]["license"] == "CC BY 4.0"
            assert "World Bank" in entry["source"]["name"]
            assert "Normalized" in entry["source"]["changes"]
            assert (
                entry["source"]["coverage"]["start_year"]
                <= entry["source"]["coverage"]["end_year"]
            )
        else:
            assert entry["classification"] == "synthetic"
            assert "fictional" in entry["generator"]["disclosure"].lower()


def test_loader_returns_all_canonical_tables_with_exact_columns():
    bundle = load_analysis_bundle()

    assert bundle.profile.profile_id == "public-demo"
    for table_name, spec in DATASET_SPECS.items():
        assert list(bundle.table(table_name).columns) == list(spec.columns)
        assert not bundle.table(table_name).empty


def test_loader_aggregates_directory_errors_and_returns_no_partial_bundle(
    tmp_path: Path,
):
    profile = tmp_path / "broken-profile"
    shutil.copytree(PUBLIC_PROFILE, profile)
    (profile / "aircraft_orders_monthly.csv").write_text("wrong\n1\n")
    (profile / "airline_cds_monthly.csv").unlink()

    with pytest.raises(DataLoadError) as exc_info:
        load_analysis_bundle(profile)

    message = str(exc_info.value)
    assert "aircraft_orders_monthly.csv" in message
    assert "airline_cds_monthly.csv" in message
    assert "SHA-256" in message
    assert "file is missing" in message


def test_explicit_and_environment_profiles_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    missing = tmp_path / "missing"
    monkeypatch.setenv("GEIA_DATA_DIR", str(missing))

    with pytest.raises(DataLoadError, match="directory not found"):
        load_analysis_bundle()
    with pytest.raises(DataLoadError, match="directory not found"):
        load_analysis_bundle(missing)


def test_dataset_registry_is_frozen():
    with pytest.raises(TypeError):
        DATASET_SPECS["extra"] = DATASET_SPECS["gdp_annual"]
