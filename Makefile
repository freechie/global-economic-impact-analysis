PYTHON ?= uv run python

.PHONY: fetch-gdp generate notebook previews test verify

fetch-gdp:
	$(PYTHON) scripts/fetch_world_bank_gdp.py
	$(PYTHON) scripts/generate_public_profile.py --gdp-source data/open/world-bank/gdp.csv

generate:
	$(PYTHON) scripts/generate_public_profile.py

notebook: generate
	$(PYTHON) scripts/build_notebook.py --execute

previews: notebook
	$(PYTHON) scripts/generate_previews.py

test:
	$(PYTHON) -m pytest -q

verify: notebook test
	$(PYTHON) scripts/verify_public_release.py
