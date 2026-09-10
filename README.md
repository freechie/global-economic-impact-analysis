# Global economic impact analysis

[![Verify](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml/badge.svg)](https://github.com/freechie/global-economic-impact-analysis/actions/workflows/verify.yml)

World nominal GDP rose from $1.38 trillion in 1960 to $100.56 trillion in 2022, a 72.6× increase. The sharpest current-dollar year-over-year declines are 2015 at -5.7%, 2009 at -5.2%, and 2020 at -2.9%. The 2015 drop is mostly a strong dollar, not a collapse in world output.

China was 6.1% of U.S. GDP in 1990 and 70.5% in 2022. China passed Japan in 2010.

An expanding one-step ARIMA(0, 1, 1) backtest on log World GDP for 2013 to 2022 recorded 4.527% MAPE. The previous-year baseline recorded 4.506% MAPE. A future projection is not published because ARIMA did not beat that baseline.

The notebook has six Plotly charts from World Bank GDP in current US dollars, license CC BY 4.0. [Open the executed notebook on GitHub](Global%20Economic%20Impact%20Analysis.ipynb) without installing Python.

## Preview

![World nominal GDP over time](docs/previews/world-gdp-trend.png)

![Selected nominal GDP trajectories](docs/previews/selected-gdp-trajectories.png)

![World GDP ARIMA backtest](docs/previews/gdp-arima-backtest.png)

## Run it

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The lockfile pins Python 3.13.

```bash
uv sync --locked --dev
make verify
```

After you change a chart, rebuild the README images. That step needs Chrome.

```bash
make previews
```

Those images come from the tracked file `data/profiles/public-demo/gdp_annual.csv`. To load a new World Bank download, pass `--gdp-source` to `scripts/generate_public_profile.py`.

## Data

`load_analysis_bundle()` reads `data/profiles/public-demo` unless you set `GEIA_DATA_DIR`. The public profile is one World Bank GDP table plus seven unused synthetic CSVs. Those extra files keep the eight-table loader working. Put a local profile in `data/local/`. Git ignores that directory. If the chosen directory fails checks, the loader reports the errors and does not fall back to `public-demo`.

See [`data/README.md`](data/README.md) for the table contract.

## Source

`gdp_annual.csv` is the World Bank indicator [GDP (current US$), code NY.GDP.MKTP.CD](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD), [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses#cc-by). Normalization dropped invalid and nonpositive rows and flagged aggregates.

Code is [MIT](LICENSE). The GDP file stays CC BY 4.0.
