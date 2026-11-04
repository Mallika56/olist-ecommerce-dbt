.PHONY: install data build docs analysis all
install:   ## install dbt + DuckDB
	pip install -r requirements.txt
data:      ## download the 9 Olist CSVs and verify checksums
	python scripts/download_data.py
build:     ## run every model, data test and unit test
	dbt build --profiles-dir .
docs:      ## browse the documentation site + lineage graph at localhost:8080
	dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
analysis:  ## query the marts, write docs/results and docs/img
	python scripts/run_analysis.py
all: data build analysis
