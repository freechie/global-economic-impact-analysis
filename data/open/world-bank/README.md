# World Bank GDP source

`gdp.csv` is the World Bank indicator GDP in current US dollars, series `NY.GDP.MKTP.CD`, license CC BY 4.0. Rows are country-year observations from the public API.

Refresh it with `make fetch-gdp`. The notebook charts read the normalized copy at `data/profiles/public-demo/gdp_annual.csv`.
