# Data profiles

The notebook reads one profile directory. That directory has `profile.json` and nine CSV files. The manifest records the schema version, profile ID, each table's classification, source or generator metadata, and SHA-256 hash.

## Public classifications

The tracked `public-demo` profile uses these classifications:

| Table | Classification | Meaning |
| --- | --- | --- |
| `gdp_annual` | Open | World Bank Open Data, GDP in current US dollars, CC BY 4.0. `profile.json` records the year coverage and the changes made during normalization. |
| `gdp_real_annual` | Open | World Bank Open Data, GDP in constant 2015 US dollars, CC BY 4.0. Same normalization rules as `gdp_annual`. |
| Other seven tables | Synthetic | Fictional values from `scripts/generate_public_profile.py`. The notebook does not plot them. The loader requires all nine tables. |

## Canonical table contract

`DATASET_SPECS` in `src/data_loader.py` fixes these column orders:

| Table | Ordered columns |
| --- | --- |
| `gdp_annual` | `country_name`, `country_code`, `year`, `nominal_gdp_usd`, `is_aggregate` |
| `gdp_real_annual` | `country_name`, `country_code`, `year`, `real_gdp_2015_usd`, `is_aggregate` |
| `arms_by_category_annual` | `direction`, `category`, `year`, `activity_value` |
| `arms_by_entity_annual` | `direction`, `source_entity`, `country_name`, `country_code`, `mapping_status`, `exclusion_reason`, `year`, `activity_value` |
| `aircraft_orders_monthly` | `date`, `manufacturer`, `net_orders` |
| `defense_budget_annual` | `request_year`, `category`, `nominal_usd_bn` |
| `cyber_fund_flows_monthly` | `date`, `fund`, `net_flow_usd_m` |
| `airline_cds_monthly` | `date`, `region`, `spread_bps` |
| `homebuilder_confidence_annual` | `year`, `index_value` |

`country_name`, `country_code`, and `exclusion_reason` are nullable only in `arms_by_entity_annual`. Excluded rows have a reason. Mapped rows have a geographic scenario.

A licensed local profile must include every table, including `gdp_real_annual.csv`. Copy that public file if the local profile has no separate real-GDP extract.

## Regenerate the public profile

```bash
make notebook
```

`make notebook` writes the tracked tables from the committed World Bank extracts, then executes the notebook.

Download the latest World Bank GDP and rebuild both public tables:

```bash
make fetch
```

`make fetch` writes `data/open/world-bank/gdp.csv` and `data/open/world-bank/gdp-real.csv`, then updates `data/profiles/public-demo`. Those files are public and tracked. Run the generator twice and the output bytes match.
