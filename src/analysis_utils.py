from __future__ import annotations

import pandas as pd

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
