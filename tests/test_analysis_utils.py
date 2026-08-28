from __future__ import annotations

import pandas as pd
import pytest

from src.analysis_utils import (
    annual_percent_change,
    country_gdp,
    latest_gdp_ranking,
    transfer_mapping_coverage,
)


def test_country_gdp_uses_canonical_aggregate_flag():
    frame = pd.DataFrame(
        {
            "country_name": ["World", "Example"],
            "country_code": ["WLD", "EXA"],
            "year": [2022, 2022],
            "nominal_gdp_usd": [100.0, 25.0],
            "is_aggregate": [True, False],
        }
    )

    assert country_gdp(frame)["country_code"].tolist() == ["EXA"]


def test_annual_percent_change_stays_within_each_group():
    frame = pd.DataFrame(
        {
            "country_name": ["B", "A", "A", "B"],
            "year": [2021, 2021, 2022, 2022],
            "nominal_gdp_usd": [50.0, 100.0, 110.0, 40.0],
        }
    )

    result = annual_percent_change(
        frame,
        group_column="country_name",
        value_column="nominal_gdp_usd",
    )

    changes = result.dropna().set_index("country_name")["annual_change_pct"]
    assert changes["A"] == pytest.approx(10.0)
    assert changes["B"] == pytest.approx(-20.0)


def test_latest_gdp_ranking_uses_latest_year_and_excludes_aggregates():
    frame = pd.DataFrame(
        {
            "country_name": ["World", "A", "B", "A", "B"],
            "country_code": ["WLD", "AAA", "BBB", "AAA", "BBB"],
            "year": [2022, 2021, 2021, 2022, 2022],
            "nominal_gdp_usd": [1000.0, 10.0, 20.0, 15.0, 25.0],
            "is_aggregate": [True, False, False, False, False],
        }
    )

    ranking = latest_gdp_ranking(frame, limit=1)

    assert ranking[["country_name", "year"]].to_dict("records") == [
        {"country_name": "B", "year": 2022}
    ]


def test_transfer_mapping_coverage_uses_activity_weights():
    frame = pd.DataFrame(
        {
            "mapping_status": ["mapped", "excluded"],
            "activity_value": [75.0, 25.0],
        }
    )

    assert transfer_mapping_coverage(frame) == pytest.approx(0.75)
    assert transfer_mapping_coverage(frame.assign(activity_value=0.0)) == 0.0
