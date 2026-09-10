# Global economic impact analysis

[![Verify](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml/badge.svg)](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml)

World nominal GDP rose from $1.37 trillion in 1960 to $118.35 trillion in 2025, an 86.5× increase. The sharpest current-dollar year-over-year declines are 2015 at -5.5%, 2009 at -5.2%, and 2020 at -2.7%.

2009: current -5.2%, constant 2015 -1.3%.
2015: current -5.5%, constant 2015 3.1%.
2020: current -2.7%, constant 2015 -2.9%.
2015 is a dollar year. 2009 and 2020 are real contractions.

China was 6.1% of U.S. GDP in 1990 and 63.4% in 2025. China passed Japan in 2010.

An expanding one-step ARIMA(1, 1, 1) backtest on log World GDP for 2013 to 2025 recorded 3.804% MAPE. The previous-year baseline recorded 4.574% MAPE. ARIMA beat the naive baseline. A ten-year projection is published. The 2035 median is $172.50 trillion. Observed 2025 GDP was $118.35 trillion. The 95% interval is wide.

The notebook has six Plotly charts. They use World Bank GDP in current US dollars and constant 2015 US dollars, license CC BY 4.0. [Open the executed notebook on GitHub](Global%20Economic%20Impact%20Analysis.ipynb) without installing Python.

## Preview

![World nominal GDP in current US dollars, 1960 to 2025](docs/previews/world-gdp-trend.png)

Current-dollar World GDP. 2015 is the largest drop and is marked FX.

![World GDP annual percent change, current US dollars vs constant 2015 dollars](docs/previews/gdp-nominal-vs-real.png)

2015: current -5.5%, constant 2015 3.1%. 2009 and 2020 fall in both series.

![Nominal GDP for the United States, China, Japan, Germany, and India, log scale](docs/previews/selected-gdp-trajectories.png)

China passes Japan in 2010. The 1960 China-above-Japan reading is a current-dollar artifact.

![Largest current-dollar GDP in 2025, countries only](docs/previews/gdp-latest-ranking.png)

United States, China, Germany, Japan, United Kingdom. World Bank aggregates are excluded.

![ARIMA(1, 1, 1) one-step backtest vs last year's World GDP, 2013 to 2025](docs/previews/gdp-arima-backtest.png)

ARIMA MAPE 3.804%. Previous-year baseline 4.574%.

![Ten-year World GDP projection, ARIMA(1, 1, 1) median and 95% interval](docs/previews/gdp-arima-projection.png)

Median $172.50 trillion in 2035. The 95% interval runs from $75 trillion to $398 trillion.

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The lockfile pins Python 3.13.

```bash
uv sync --locked --dev
```

## Build

```bash
make verify
```

`make verify` regenerates `data/profiles/public-demo`, executes the notebook, runs tests, and scans the public release. `make` runs the same target.

Rebuild the notebook without tests:

```bash
make notebook
```

Rebuild the README images after a chart change. `make previews` needs Chrome.

```bash
make previews
```

Download the latest World Bank GDP, then rebuild the notebook:

```bash
make fetch
make notebook
```

## Run the notebook

Open `Global Economic Impact Analysis.ipynb` in Cursor or VS Code and select the `.venv` kernel.

Open the notebook in a browser:

```bash
uv run --with jupyterlab jupyter lab "Global Economic Impact Analysis.ipynb"
```

The lockfile does not include Jupyter.

## Data

`load_analysis_bundle()` reads `data/profiles/public-demo` unless you set `GEIA_DATA_DIR`.

The public profile has two World Bank GDP tables and seven unused synthetic CSVs. The loader requires all nine tables. Put a licensed local profile in `data/local/` and include `gdp_real_annual.csv`. Git ignores `data/local/`, `data/raw/`, and `data/processed/`. If the chosen directory fails checks, the loader reports the errors. It does not fall back to `public-demo`.

See [`data/README.md`](data/README.md) for the table contract.

## Source

The public extracts are `data/open/world-bank/gdp.csv` and `data/open/world-bank/gdp-real.csv`.

`gdp_annual.csv` is World Bank [GDP (current US$), code NY.GDP.MKTP.CD](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD). `gdp_real_annual.csv` is [GDP (constant 2015 US$), code NY.GDP.MKTP.KD](https://data.worldbank.org/indicator/NY.GDP.MKTP.KD). Both are [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses#cc-by). Normalization dropped invalid and nonpositive rows and flagged aggregates.

Code is [MIT](LICENSE). The GDP files stay CC BY 4.0.
