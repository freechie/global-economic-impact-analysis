from pathlib import Path

from scripts.verify_public_release import LEGACY_TERMS, scan

ROOT = Path(__file__).resolve().parents[1]


def test_denylist_covers_legacy_sources_fields_and_filenames():
    combined = "\n".join(LEGACY_TERMS)

    assert "Bloomberg" in combined
    assert "SIPRI" in combined
    assert "PX_LAST" in combined
    assert "Field ID" in combined
    assert "all_arms_exports" in combined
    assert "img/" in combined


def test_current_public_release_passes_denylist_scan():
    assert scan() == []


def test_reproducible_environment_and_ci_are_committed():
    workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text()

    assert (ROOT / "uv.lock").is_file()
    assert not (ROOT / "requirements-lock.txt").exists()
    assert (ROOT / "LICENSE").read_text().startswith("MIT License")
    assert "uv sync --locked --dev" in workflow
    assert "make verify" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1f" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9" in workflow
