# Data profiles

The notebook reads one profile directory. That directory has `profile.json` and eight CSV files. The manifest records the schema version, profile ID, each table's classification, source or generator metadata, and SHA-256 hash.

## Public classifications

The tracked `public-demo` profile uses these classifications:

| Table | Classification | Meaning |
| --- | --- | --- |
| `gdp_annual` | Open | World Bank Open Data, GDP in current US dollars, CC BY 4.0. `profile.json` records the year coverage and the changes made during normalization. |
| Other seven tables | Synthetic | Fictional values from `scripts/generate_public_profile.py`. The notebook does not plot them. They keep the eight-table loader working for a local profile. |

## Canonical table contract

`DATASET_SPECS` in `src/data_loader.py` fixes these column orders:

| Table | Ordered columns |
| --- | --- |
| `gdp_annual` | `country_name`, `country_code`, `year`, `nominal_gdp_usd`, `is_aggregate` |
| `arms_by_category_annual` | `direction`, `category`, `year`, `activity_value` |
| `arms_by_entity_annual` | `direction`, `source_entity`, `country_name`, `country_code`, `mapping_status`, `exclusion_reason`, `year`, `activity_value` |
| `aircraft_orders_monthly` | `date`, `manufacturer`, `net_orders` |
| `defense_budget_annual` | `request_year`, `category`, `nominal_usd_bn` |
| `cyber_fund_flows_monthly` | `date`, `fund`, `net_flow_usd_m` |
| `airline_cds_monthly` | `date`, `region`, `spread_bps` |
| `homebuilder_confidence_annual` | `year`, `index_value` |

`country_name`, `country_code`, and `exclusion_reason` are nullable only in `arms_by_entity_annual`. An excluded entity records a reason. A mapped entity records its geographic scenario.

## Regenerate the public profile

```bash
python3 scripts/generate_public_profile.py
```

A fresh clone regenerates from the tracked `gdp_annual.csv`. To load a new World Bank download, keep that file outside local licensed profiles and run:

```bash
python3 scripts/generate_public_profile.py --gdp-source data/open/world-bank/gdp.csv
```

The generator uses closed formulas, stable sorting, fixed rounding, and stable JSON. Running it twice writes the same bytes.
