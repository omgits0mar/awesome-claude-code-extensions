.PHONY: build refresh-snapshots validate test check-links all

all: test build validate

refresh-snapshots:
	python3 scripts/fetch_sources.py

build:
	python3 scripts/build_catalog.py

validate:
	python3 scripts/validate_catalog.py

test:
	python3 -m unittest discover -s tests -p 'test_*.py'

check-links:
	python3 scripts/check_links.py --limit 250
