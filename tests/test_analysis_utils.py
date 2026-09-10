from __future__ import annotations

import warnings

import pandas as pd
import pytest

from src.analysis_utils import (
    ExpandingArimaBacktest,
    annual_percent_change,
    country_gdp,
    expanding_arima_backtest,
    expanding_arima_projection,
    latest_gdp_ranking,
    nominal_gdp_story,
    nominal_vs_real_changes,
    projection_decision_text,
    select_arima_candidate,
    transfer_mapping_coverage,
    world_gdp_series,
)
from src.data_loader import load_analysis_bundle


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


def _backtest(
    *,
    arima_mape: float,
    naive_mape: float,
) -> ExpandingArimaBacktest:
    return ExpandingArimaBacktest(
        order=(0, 1, 1),
        arima_mape=arima_mape,
        naive_mape=naive_mape,
        arima_rmse=1.0,
        naive_rmse=1.0,
        years=(2013, 2014),
        observed=(1.0, 1.1),
        arima_one_step=(1.0, 1.0),
        naive_one_step=(0.9, 1.0),
    )


def test_projection_requires_strictly_better_mape():
    tied = _backtest(arima_mape=4.527, naive_mape=4.527)
    better = _backtest(arima_mape=4.5, naive_mape=4.527)

    assert tied.publishes_projection is False
    assert better.publishes_projection is True
    assert "not published" in projection_decision_text(tied)
    assert "ten-year projection is published" in projection_decision_text(better)


def test_world_gdp_series_keeps_world_rows_only():
    frame = pd.DataFrame(
        {
            "country_name": ["World", "Example", "World"],
            "country_code": ["WLD", "EXA", "WLD"],
            "year": [1960, 1960, 1961],
            "nominal_gdp_usd": [10.0, 1.0, 12.0],
            "is_aggregate": [True, False, True],
        }
    )

    series = world_gdp_series(frame)

    assert series.to_dict() == {1960: 10.0, 1961: 12.0}


def test_nominal_gdp_story_uses_world_path_and_post_1980_china_japan_crossing():
    rows = []
    for year, world_usd in (
        (1960, 10.0),
        (1989, 100.0),
        (1990, 110.0),
        (2009, 100.0),
        (2010, 95.0),
        (2014, 120.0),
        (2015, 100.0),
        (2019, 130.0),
        (2020, 120.0),
        (2022, 200.0),
    ):
        rows.append(
            {
                "country_name": "World",
                "country_code": "WLD",
                "year": year,
                "nominal_gdp_usd": world_usd,
                "is_aggregate": True,
            }
        )
    country_years = {
        "United States": {1990: 100.0, 2010: 100.0, 2022: 100.0},
        "China": {1990: 6.0, 2009: 5.0, 2010: 8.0, 2022: 70.0},
        "Japan": {1990: 50.0, 2009: 6.0, 2010: 6.0, 2022: 40.0},
    }
    codes = {"United States": "USA", "China": "CHN", "Japan": "JPN"}
    for name, values in country_years.items():
        for year, usd in values.items():
            rows.append(
                {
                    "country_name": name,
                    "country_code": codes[name],
                    "year": year,
                    "nominal_gdp_usd": usd,
                    "is_aggregate": False,
                }
            )

    story = nominal_gdp_story(pd.DataFrame(rows))

    assert story.start_year == 1960
    assert story.end_year == 2022
    assert story.growth_multiple == pytest.approx(20.0)
    assert [year for year, _change in story.sharpest_declines] == [2015, 2009, 2020]
    assert story.china_share_1990_pct == pytest.approx(6.0)
    assert story.china_share_latest_pct == pytest.approx(70.0)
    assert story.china_passes_japan_year == 2010


def test_nominal_vs_real_changes_keep_named_years():
    nominal = pd.Series(
        {2008: 100.0, 2009: 90.0, 2014: 100.0, 2015: 90.0, 2019: 100.0, 2020: 97.0}
    )
    real = pd.Series(
        {2008: 100.0, 2009: 97.0, 2014: 100.0, 2015: 103.0, 2019: 100.0, 2020: 96.0}
    )

    checks = {row.year: row for row in nominal_vs_real_changes(nominal, real)}

    assert checks[2009].nominal_change_pct == pytest.approx(-10.0)
    assert checks[2009].real_change_pct == pytest.approx(-3.0)
    assert checks[2015].nominal_change_pct == pytest.approx(-10.0)
    assert checks[2015].real_change_pct == pytest.approx(3.0)
    assert checks[2020].nominal_change_pct == pytest.approx(-3.0)
    assert checks[2020].real_change_pct == pytest.approx(-4.0)


def _numpy_shape_deprecations(caught: list[warnings.WarningMessage]) -> list[str]:
    return [
        str(item.message)
        for item in caught
        if issubclass(item.category, DeprecationWarning)
        and "Setting the shape on a NumPy array" in str(item.message)
    ]


def test_expanding_arima_backtest_returns_one_step_paths_for_each_test_year():
    years = list(range(2000, 2023))
    series = pd.Series([100.0 * (1.04 ** index) for index in range(len(years))], index=years)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = expanding_arima_backtest(series)
    test = series.loc[list(result.years)]
    naive = series.shift(1).loc[test.index]
    independent_naive_mape = float((abs(test - naive) / test).mean() * 100)

    assert result.years == tuple(range(2013, 2023))
    assert len(result.arima_one_step) == 10
    assert result.naive_mape == pytest.approx(independent_naive_mape)
    assert _numpy_shape_deprecations(caught) == []


def test_arima_selection_prefers_simpler_order_within_mape_tie():
    selected = select_arima_candidate(
        [
            ((1, 1, 2), 3.804, 1.0, (1.0,)),
            ((1, 1, 1), 3.805, 1.1, (1.0,)),
        ]
    )

    assert selected[0] == (1, 1, 1)
    assert selected[1] == 3.805


def test_arima_selection_keeps_a_clear_mape_winner():
    selected = select_arima_candidate(
        [
            ((2, 1, 2), 3.50, 1.0, (1.0,)),
            ((0, 1, 0), 4.00, 1.0, (1.0,)),
        ]
    )

    assert selected[0] == (2, 1, 2)


def test_public_world_gdp_backtest_beats_naive():
    series = world_gdp_series(load_analysis_bundle().gdp_annual)
    result = expanding_arima_backtest(series)
    test = series.loc[list(result.years)]
    naive = series.shift(1).loc[test.index]
    independent_naive_mape = float((abs(test - naive) / test).mean() * 100)

    assert result.years[0] == 2013
    assert result.years[-1] == int(series.index.max())
    assert result.order == (1, 1, 1)
    assert result.arima_mape == pytest.approx(3.804, abs=0.01)
    assert result.naive_mape == pytest.approx(4.574, abs=0.01)
    assert result.naive_mape == pytest.approx(independent_naive_mape)
    assert result.publishes_projection is True


def test_public_2015_is_a_dollar_year_not_a_real_contraction():
    bundle = load_analysis_bundle()
    checks = {
        row.year: row
        for row in nominal_vs_real_changes(
            world_gdp_series(bundle.gdp_annual),
            world_gdp_series(bundle.gdp_real_annual),
        )
    }

    assert round(checks[2009].nominal_change_pct, 1) == -5.2
    assert round(checks[2009].real_change_pct, 1) == -1.3
    assert round(checks[2015].nominal_change_pct, 1) == -5.5
    assert round(checks[2015].real_change_pct, 1) == 3.1
    assert round(checks[2020].nominal_change_pct, 1) == -2.7
    assert round(checks[2020].real_change_pct, 1) == -2.9


def test_public_world_gdp_projection_starts_after_the_latest_observed_year():
    series = world_gdp_series(load_analysis_bundle().gdp_annual)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        backtest = expanding_arima_backtest(series)
        projection = expanding_arima_projection(series, backtest.order)

    assert projection.origin_year == int(series.index.max())
    assert projection.years[0] == projection.origin_year + 1
    assert len(projection.years) == 10
    assert projection.years == tuple(range(projection.origin_year + 1, projection.origin_year + 11))
    assert all(low < mid < high for low, mid, high in zip(projection.lower, projection.median, projection.upper))
    assert _numpy_shape_deprecations(caught) == []
