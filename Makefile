PY ?= python3

.PHONY: install download pipeline scd-batch pipeline-batch2 report demo clean

install:            ## install dependencies (DuckDB only)
	$(PY) -m pip install -r requirements.txt

download:           ## download the raw CSV files from Kaggle (or mirror)
	$(PY) run_pipeline.py download

pipeline:           ## run the complete pipeline (single entry point)
	$(PY) run_pipeline.py run

scd-batch:          ## create the second input batch with attribute changes
	$(PY) run_pipeline.py make-scd-batch

pipeline-batch2:    ## run the pipeline with the change batch overlaid on the raw files
	$(PY) run_pipeline.py run --batch-dir data/batches/batch_002 --batch-label batch_002

report:             ## run the business queries and write docs/evidence/business_queries.md
	$(PY) run_pipeline.py report

demo:               ## reproduce all evidence from scratch (4 runs + report)
	$(PY) run_pipeline.py demo --fresh

clean:              ## remove the warehouse database, batches and logs (raw files are kept)
	rm -rf data/warehouse data/batches logs
