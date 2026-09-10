# Global economic impact analysis

[![Verify](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml/badge.svg)](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml)

World nominal GDP rose from $1.37 trillion in 1960 to $118.35 trillion in 2025, an 86.5× increase. The sharpest current-dollar year-over-year declines are 2015 at -5.5%, 2009 at -5.2%, and 2020 at -2.7%. The 2015 drop is mostly a strong dollar, not a collapse in world output.

China was 6.1% of U.S. GDP in 1990 and 63.4% in 2025. China passed Japan in 2010.

An expanding one-step ARIMA(1, 1, 1) backtest on log World GDP for 2013 to 2025 recorded 3.804% MAPE. The previous-year baseline recorded 4.574% MAPE. ARIMA beat the naive baseline. A ten-year projection is published. The median path goes from $118.35 trillion in 2025 to $172.50 trillion in 2035. The 95% interval is wide.

The notebook has six Plotly charts from World Bank GDP in current US dollars, license CC BY 4.0. [Open the executed notebook on GitHub](Global%20Economic%20Impact%20Analysis.ipynb) without installing Python.

## Preview

![World nominal GDP over time](docs/previews/world-gdp-trend.png)

![Selected nominal GDP trajectories](docs/previews/selected-gdp-trajectories.png)

![World GDP ARIMA backtest](docs/previews/gdp-arima-backtest.png)

![World GDP ten-year ARIMA projection](docs/previews/gdp-arima-projection.png)

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The lockfile pins Python 3.13.

```bash
uv sync --locked --dev
```

## Build

Rebuild the executed notebook from `scripts/build_notebook.py`:

```bash
make notebook
```

That regenerates `data/profiles/public-demo`, then executes every cell and writes `Global Economic Impact Analysis.ipynb`. `make verify` does the same, then runs tests and the public-release scan:

```bash
make verify
```

After you change a chart, rebuild the README images. That step needs Chrome.

```bash
make previews
```

Those images come from `data/profiles/public-demo/gdp_annual.csv`. The public World Bank extract that feeds that table is `data/open/world-bank/gdp.csv`. To refresh through the latest published year:

```bash
make fetch-gdp
make notebook
```

## Run the notebook

Open `Global Economic Impact Analysis.ipynb` in Cursor or VS Code and select the `.venv` kernel.

To open it in a browser without adding Jupyter to the lockfile:

```bash
uv run --with jupyterlab jupyter lab "Global Economic Impact Analysis.ipynb"
```

## Data

`load_analysis_bundle()` reads `data/profiles/public-demo` unless you set `GEIA_DATA_DIR`. The public profile is one World Bank GDP table plus seven unused synthetic CSVs. Those extra files keep the eight-table loader working. Licensed local profiles belong in `data/local/`. Git ignores that directory, plus `data/raw/` and `data/processed/`. If the chosen directory fails checks, the loader reports the errors and does not fall back to `public-demo`.

See [`data/README.md`](data/README.md) for the table contract.

## Source

`gdp_annual.csv` is the World Bank indicator [GDP (current US$), code NY.GDP.MKTP.CD](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD), [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses#cc-by). Normalization dropped invalid and nonpositive rows and flagged aggregates.

Code is [MIT](LICENSE). The GDP file stays CC BY 4.0.
