PYTHON ?= python3

.PHONY: generate notebook test verify

generate:
	$(PYTHON) scripts/generate_public_profile.py

notebook: generate
	$(PYTHON) scripts/build_notebook.py --execute

test:
	$(PYTHON) -m pytest -q

verify: notebook test
	$(PYTHON) scripts/verify_public_release.py
