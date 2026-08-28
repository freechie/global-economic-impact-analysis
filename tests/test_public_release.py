from scripts.verify_public_release import LEGACY_TERMS, scan


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
