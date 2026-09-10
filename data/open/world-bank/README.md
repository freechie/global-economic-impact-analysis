# World Bank GDP source

`gdp.csv` is GDP in current US dollars, series `NY.GDP.MKTP.CD`. `gdp-real.csv` is GDP in constant 2015 US dollars, series `NY.GDP.MKTP.KD`. Both are World Bank Open Data, license CC BY 4.0. Rows are country-year observations from the public API.

Refresh both with `make fetch`. The notebook charts read the normalized copies at `data/profiles/public-demo/gdp_annual.csv` and `data/profiles/public-demo/gdp_real_annual.csv`.
