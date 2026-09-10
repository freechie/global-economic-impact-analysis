PYTHON ?= uv run python

.PHONY: fetch notebook previews verify

verify: notebook
	$(PYTHON) -m pytest -q
	$(PYTHON) scripts/verify_public_release.py

notebook:
	$(PYTHON) scripts/build_notebook.py --execute

previews: notebook
	$(PYTHON) scripts/generate_previews.py

fetch:
	$(PYTHON) scripts/fetch_world_bank_gdp.py
