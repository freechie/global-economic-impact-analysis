# Data profiles

The notebook loads one profile directory. That directory has `profile.json` and two CSV files. `load_analysis_bundle()` reads `data/profiles/public-demo` unless you set `GEIA_DATA_DIR`. If the directory fails checks, the loader reports every error and does not fall back to `public-demo`.

`DATASET_SPECS` in `src/data_loader.py` is the contract. Column names and order must match exactly. Each CSV must match the SHA-256 in `profile.json`. Tables cannot be empty.

Git ignores `data/local/`, `data/raw/`, and `data/processed/`.

## Tables

| Table | File | Ordered columns | Unique key |
| --- | --- | --- | --- |
| `gdp_annual` | `gdp_annual.csv` | `country_name`, `country_code`, `year`, `nominal_gdp_usd`, `is_aggregate` | `country_code`, `year` |
| `gdp_real_annual` | `gdp_real_annual.csv` | `country_name`, `country_code`, `year`, `real_gdp_2015_usd`, `is_aggregate` | `country_code`, `year` |

`is_aggregate` is `true` or `false`. GDP values are nonnegative.

Public `gdp_annual` is World Bank GDP in current US dollars, series `NY.GDP.MKTP.CD`, from `data/open/world-bank/gdp.csv`. Public `gdp_real_annual` is GDP in constant 2015 US dollars, series `NY.GDP.MKTP.KD`, from `data/open/world-bank/gdp-real.csv`. Both are CC BY 4.0. Normalization dropped invalid and nonpositive rows and flagged aggregates. `profile.json` records the year coverage and those changes.

## profile.json

`schema_version` is `1.0`. Each dataset entry has `filename`, `classification` (`open`), `sha256` (64 lowercase hex digits), and a `source` object.

On `public-demo`, both tables must name World Bank with license CC BY 4.0.

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
