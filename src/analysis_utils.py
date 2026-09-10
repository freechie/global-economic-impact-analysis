from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import warnings

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA

MAPE_TIE_EPSILON = 1e-9
ARIMA_ORIGIN_YEAR = 2013
ARIMA_MAX_LAG = 2
ARIMA_DIFFERENCE = 1
ARIMA_FORECAST_STEPS = 10
CHINA_JAPAN_CROSSING_AFTER_YEAR = 1980
CHINA_SHARE_START_YEAR = 1990
NOMINAL_GDP_COLUMN = "nominal_gdp_usd"
REAL_GDP_COLUMN = "real_gdp_2015_usd"
OUTPUT_CHECK_YEARS = (2009, 2015, 2020)
SELECTED_TRAJECTORY_COUNTRIES = (
    "United States",
    "China",
    "Japan",
    "Germany",
    "India",
)

WORLD_BANK_AGGREGATE_CODES = frozenset(
    {
        "AFE",
        "AFW",
        "ARB",
        "CEB",
        "CSS",
        "EAP",
        "EAR",
        "EAS",
        "ECA",
        "ECS",
        "EMU",
        "EUU",
        "FCS",
        "HIC",
        "HPC",
        "IBD",
        "IBT",
        "IDA",
        "IDB",
        "IDX",
        "LAC",
        "LCN",
        "LDC",
        "LIC",
        "LMC",
        "LMY",
        "LTE",
        "MEA",
        "MIC",
        "MNA",
        "NAC",
        "OED",
        "OSS",
        "PRE",
        "PSS",
        "PST",
        "SAS",
        "SSA",
        "SSF",
        "SST",
        "TEA",
        "TEC",
        "TLA",
        "TMN",
        "TSA",
        "TSS",
        "UMC",
        "WLD",
    }
)


def country_gdp(gdp_annual: pd.DataFrame) -> pd.DataFrame:
    """Return country records from a validated canonical GDP table."""

    return gdp_annual.loc[~gdp_annual["is_aggregate"]].copy()


def annual_percent_change(
    frame: pd.DataFrame,
    *,
    group_column: str,
    value_column: str,
    output_column: str = "annual_change_pct",
) -> pd.DataFrame:
    """Calculate within-group annual percentage changes in stable year order."""

    result = frame.sort_values([group_column, "year"]).copy()
    result[output_column] = (
        result.groupby(group_column, sort=False)[value_column].pct_change() * 100
    )
    return result


def latest_gdp_ranking(gdp_annual: pd.DataFrame, *, limit: int = 15) -> pd.DataFrame:
    """Return the largest country GDP observations in the latest common year."""

    countries = country_gdp(gdp_annual)
    latest_year = int(countries["year"].max())
    return (
        countries.loc[countries["year"] == latest_year]
        .nlargest(limit, "nominal_gdp_usd")
        .sort_values("nominal_gdp_usd", ascending=True)
        .reset_index(drop=True)
    )


def transfer_mapping_coverage(arms_by_entity_annual: pd.DataFrame) -> float:
    """Return the activity-weighted share with a geographic scenario mapping."""

    total = arms_by_entity_annual["activity_value"].sum()
    if total == 0:
        return 0.0
    mapped = arms_by_entity_annual.loc[
        arms_by_entity_annual["mapping_status"] == "mapped", "activity_value"
    ].sum()
    return float(mapped / total)


@dataclass(frozen=True)
class ExpandingArimaBacktest:
    order: tuple[int, int, int]
    arima_mape: float
    naive_mape: float
    arima_rmse: float
    naive_rmse: float
    years: tuple[int, ...]
    observed: tuple[float, ...]
    arima_one_step: tuple[float, ...]
    naive_one_step: tuple[float, ...]

    @property
    def publishes_projection(self) -> bool:
        return self.arima_mape < self.naive_mape - MAPE_TIE_EPSILON


@dataclass(frozen=True)
class ExpandingArimaProjection:
    order: tuple[int, int, int]
    origin_year: int
    years: tuple[int, ...]
    median: tuple[float, ...]
    lower: tuple[float, ...]
    upper: tuple[float, ...]


@dataclass(frozen=True)
class NominalGdpStory:
    start_year: int
    end_year: int
    start_usd: float
    end_usd: float
    growth_multiple: float
    sharpest_declines: tuple[tuple[int, float], ...]
    china_share_1990_pct: float
    china_share_latest_pct: float
    latest_year: int
    china_passes_japan_year: int


@dataclass(frozen=True)
class NominalVsRealChange:
    year: int
    nominal_change_pct: float
    real_change_pct: float


def _gdp_value_column(gdp_table: pd.DataFrame, value_column: str | None) -> str:
    if value_column is not None:
        return value_column
    has_nominal = NOMINAL_GDP_COLUMN in gdp_table.columns
    has_real = REAL_GDP_COLUMN in gdp_table.columns
    if has_nominal and not has_real:
        return NOMINAL_GDP_COLUMN
    if has_real and not has_nominal:
        return REAL_GDP_COLUMN
    if has_nominal and has_real:
        raise ValueError("Pass value_column when both nominal and real GDP columns are present")
    raise ValueError("GDP table needs nominal_gdp_usd or real_gdp_2015_usd")


def world_gdp_series(
    gdp_table: pd.DataFrame, *, value_column: str | None = None
) -> pd.Series:
    """Return World GDP indexed by calendar year."""

    column = _gdp_value_column(gdp_table, value_column)
    world = gdp_table.loc[gdp_table["country_code"] == "WLD"].sort_values("year")
    if world.empty:
        raise ValueError("GDP table has no World (WLD) rows")
    series = pd.Series(
        world[column].to_numpy(dtype=float),
        index=world["year"].astype(int).to_numpy(),
        name=column,
    )
    if series.index.has_duplicates:
        raise ValueError("World GDP has duplicate years")
    return series


def nominal_vs_real_changes(
    nominal: pd.Series,
    real: pd.Series,
    years: tuple[int, ...] = OUTPUT_CHECK_YEARS,
) -> tuple[NominalVsRealChange, ...]:
    """Compare current-dollar and constant-dollar World GDP changes in named years."""

    nominal_yoy = nominal.sort_index().pct_change() * 100
    real_yoy = real.sort_index().pct_change() * 100
    rows = []
    for year in years:
        if year not in nominal_yoy.index or year not in real_yoy.index:
            raise ValueError(f"Missing year {year} in nominal or real World GDP")
        nominal_change = nominal_yoy.loc[year]
        real_change = real_yoy.loc[year]
        if pd.isna(nominal_change) or pd.isna(real_change):
            raise ValueError(f"Year {year} has no prior-year GDP observation")
        rows.append(
            NominalVsRealChange(
                year=year,
                nominal_change_pct=float(nominal_change),
                real_change_pct=float(real_change),
            )
        )
    return tuple(rows)


def _country_named_series(gdp_annual: pd.DataFrame, country_name: str) -> pd.Series:
    countries = country_gdp(gdp_annual)
    subset = countries.loc[countries["country_name"] == country_name].sort_values("year")
    if subset.empty:
        raise ValueError(f"gdp_annual has no country named {country_name}")
    return pd.Series(
        subset["nominal_gdp_usd"].to_numpy(dtype=float),
        index=subset["year"].astype(int).to_numpy(),
        name="nominal_gdp_usd",
    )


def nominal_gdp_story(gdp_annual: pd.DataFrame) -> NominalGdpStory:
    """Build World GDP headlines from a canonical table."""

    world = world_gdp_series(gdp_annual)
    start_year = int(world.index.min())
    end_year = int(world.index.max())
    start_usd = float(world.loc[start_year])
    end_usd = float(world.loc[end_year])
    yoy = world.pct_change() * 100
    sharpest = tuple(
        (int(year), float(change))
        for year, change in yoy.dropna().nsmallest(3).items()
    )
    china = _country_named_series(gdp_annual, "China")
    united_states = _country_named_series(gdp_annual, "United States")
    japan = _country_named_series(gdp_annual, "Japan")
    if CHINA_SHARE_START_YEAR not in china.index or CHINA_SHARE_START_YEAR not in united_states.index:
        raise ValueError("China or United States GDP is missing 1990")
    latest_year = int(min(china.index.max(), united_states.index.max(), end_year))
    overlap = china.index.intersection(japan.index)
    overlap = overlap[overlap > CHINA_JAPAN_CROSSING_AFTER_YEAR]
    passed = [int(year) for year in sorted(overlap) if china.loc[year] > japan.loc[year]]
    if not passed:
        raise ValueError("China never exceeds Japan after 1980")
    return NominalGdpStory(
        start_year=start_year,
        end_year=end_year,
        start_usd=start_usd,
        end_usd=end_usd,
        growth_multiple=end_usd / start_usd,
        sharpest_declines=sharpest,
        china_share_1990_pct=float(
            china.loc[CHINA_SHARE_START_YEAR] / united_states.loc[CHINA_SHARE_START_YEAR] * 100
        ),
        china_share_latest_pct=float(
            china.loc[latest_year] / united_states.loc[latest_year] * 100
        ),
        latest_year=latest_year,
        china_passes_japan_year=passed[0],
    )


@contextmanager
def _quiet_statsmodels():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.filterwarnings(
            "ignore",
            message="Setting the shape on a NumPy array has been deprecated",
            category=DeprecationWarning,
        )
        yield


def expanding_arima_backtest(
    series: pd.Series,
    *,
    origin_year: int = ARIMA_ORIGIN_YEAR,
    max_p: int = ARIMA_MAX_LAG,
    max_q: int = ARIMA_MAX_LAG,
    difference: int = ARIMA_DIFFERENCE,
) -> ExpandingArimaBacktest:
    """Score log ARIMA(p,d,q) models with expanding one-step forecasts against a naive lag."""

    ordered = series.sort_index()
    training = ordered.loc[ordered.index < origin_year]
    test = ordered.loc[ordered.index >= origin_year]
    if training.empty or test.empty:
        raise ValueError("ARIMA backtest needs training years before origin_year and test years after")

    candidate_results: list[tuple[tuple[int, int, int], float, float, tuple[float, ...]]] = []
    actual_levels = test.to_numpy(dtype=float)
    for p in range(max_p + 1):
        for q in range(max_q + 1):
            order = (p, difference, q)
            history = list(np.log(training.to_numpy(dtype=float)))
            predictions: list[float] = []
            converged = True
            for actual in np.log(actual_levels):
                with _quiet_statsmodels():
                    fitted = ARIMA(history, order=order).fit()
                    retvals = getattr(fitted, "mle_retvals", None) or {}
                    if not retvals.get("converged", True):
                        converged = False
                        break
                    predictions.append(float(np.exp(fitted.forecast(1)[0])))
                history.append(float(actual))
            if not converged:
                continue
            predicted = np.array(predictions, dtype=float)
            mape = float(np.mean(np.abs((actual_levels - predicted) / actual_levels)) * 100)
            rmse = float(np.sqrt(np.mean((actual_levels - predicted) ** 2)))
            candidate_results.append((order, mape, rmse, tuple(float(value) for value in predicted)))

    if not candidate_results:
        raise ValueError("No ARIMA specification converged")

    candidate_results.sort(key=lambda item: (item[1], item[2], item[0]))
    order, arima_mape, arima_rmse, arima_one_step = candidate_results[0]
    naive = ordered.shift(1).loc[test.index].to_numpy(dtype=float)
    naive_mape = float(np.mean(np.abs((actual_levels - naive) / actual_levels)) * 100)
    naive_rmse = float(np.sqrt(np.mean((actual_levels - naive) ** 2)))
    return ExpandingArimaBacktest(
        order=order,
        arima_mape=arima_mape,
        naive_mape=naive_mape,
        arima_rmse=arima_rmse,
        naive_rmse=naive_rmse,
        years=tuple(int(year) for year in test.index),
        observed=tuple(float(value) for value in actual_levels),
        arima_one_step=arima_one_step,
        naive_one_step=tuple(float(value) for value in naive),
    )


def expanding_arima_projection(
    series: pd.Series,
    order: tuple[int, int, int],
    *,
    steps: int = ARIMA_FORECAST_STEPS,
) -> ExpandingArimaProjection:
    """Forecast log nominal GDP with a fitted ARIMA order and return levels."""

    ordered = series.sort_index()
    if ordered.empty:
        raise ValueError("ARIMA projection needs a non-empty series")
    origin_year = int(ordered.index.max())
    history = list(np.log(ordered.to_numpy(dtype=float)))
    with _quiet_statsmodels():
        fitted = ARIMA(history, order=order).fit(method_kwargs={"maxiter": 1000})
        forecast = fitted.get_forecast(steps=steps)
    median = np.exp(np.asarray(forecast.predicted_mean, dtype=float))
    interval = np.asarray(forecast.conf_int(), dtype=float)
    lower = np.exp(interval[:, 0])
    upper = np.exp(interval[:, 1])
    years = tuple(origin_year + offset for offset in range(1, steps + 1))
    return ExpandingArimaProjection(
        order=order,
        origin_year=origin_year,
        years=years,
        median=tuple(float(value) for value in median),
        lower=tuple(float(value) for value in lower),
        upper=tuple(float(value) for value in upper),
    )


def projection_decision_text(backtest: ExpandingArimaBacktest) -> str:
    if backtest.publishes_projection:
        return "ARIMA beat the naive baseline. A ten-year projection is published."
    return (
        "A future projection is not published. ARIMA did not beat the naive baseline."
    )
