# Data profiles

The notebook loads one profile directory. That directory has `profile.json` and nine CSV files. `load_analysis_bundle()` reads `data/profiles/public-demo` unless you set `GEIA_DATA_DIR`. If the directory fails checks, the loader reports every error and does not fall back to `public-demo`.

`DATASET_SPECS` in `src/data_loader.py` is the contract. Column names and order must match exactly. Each CSV must match the SHA-256 in `profile.json`. Tables cannot be empty.

Git ignores `data/local/`, `data/raw/`, and `data/processed/`.

## What the notebook plots

The charts use World Bank GDP only.

| Table | File | Ordered columns | Unique key |
| --- | --- | --- | --- |
| `gdp_annual` | `gdp_annual.csv` | `country_name`, `country_code`, `year`, `nominal_gdp_usd`, `is_aggregate` | `country_code`, `year` |
| `gdp_real_annual` | `gdp_real_annual.csv` | `country_name`, `country_code`, `year`, `real_gdp_2015_usd`, `is_aggregate` | `country_code`, `year` |

`is_aggregate` is `true` or `false`. GDP values are nonnegative.

Public `gdp_annual` is World Bank GDP in current US dollars, series `NY.GDP.MKTP.CD`, from `data/open/world-bank/gdp.csv`. Public `gdp_real_annual` is GDP in constant 2015 US dollars, series `NY.GDP.MKTP.KD`, from `data/open/world-bank/gdp-real.csv`. Both are CC BY 4.0. Normalization dropped invalid and nonpositive rows and flagged aggregates. `profile.json` records the year coverage and those changes.

## Unused tables the loader still requires

These seven CSVs are fictional. The notebook does not plot them. A complete profile must still include them.

| Table | Ordered columns | Unique key |
| --- | --- | --- |
| `arms_by_category_annual` | `direction`, `category`, `year`, `activity_value` | `direction`, `category`, `year` |
| `arms_by_entity_annual` | `direction`, `source_entity`, `country_name`, `country_code`, `mapping_status`, `exclusion_reason`, `year`, `activity_value` | `direction`, `source_entity`, `year` |
| `aircraft_orders_monthly` | `date`, `manufacturer`, `net_orders` | `date`, `manufacturer` |
| `defense_budget_annual` | `request_year`, `category`, `nominal_usd_bn` | `request_year`, `category` |
| `cyber_fund_flows_monthly` | `date`, `fund`, `net_flow_usd_m` | `date`, `fund` |
| `airline_cds_monthly` | `date`, `region`, `spread_bps` | `date`, `region` |
| `homebuilder_confidence_annual` | `year`, `index_value` | `year` |

`country_name`, `country_code`, and `exclusion_reason` may be empty only in `arms_by_entity_annual`. Mapped rows need a country name and code. Excluded rows need a reason. `direction` is `inbound` or `outbound`. `mapping_status` is `mapped` or `excluded`. Dates use `YYYY-MM-DD`. Activity, budget, and spread values are nonnegative.

## profile.json

`schema_version` is `1.0`. Each dataset entry has `filename`, `classification` (`open`, `synthetic`, or `licensed`), `sha256` (64 lowercase hex digits), and provenance:

- `open` or `licensed` tables have a `source` object
- `synthetic` tables have a `generator` object

On `public-demo`, the two GDP tables are `open` and must name World Bank with license CC BY 4.0. The other seven are `synthetic` and must use this disclosure: `Synthetic demonstration data. Values are fictional and are not observed measurements.`

A licensed local profile belongs in `data/local/`. It must include every table, including `gdp_real_annual.csv`. Copy that public file if the local profile has no separate real-GDP extract.

## Rebuild the public profile

```bash
make notebook
```

`make notebook` writes the tracked tables from the committed World Bank extracts, then executes the notebook.

Download the latest World Bank GDP and rebuild both public tables:

```bash
make fetch
```

`make fetch` writes `data/open/world-bank/gdp.csv` and `data/open/world-bank/gdp-real.csv`, then updates `data/profiles/public-demo`. Those files are public and tracked. Run the generator twice and the output bytes match.
