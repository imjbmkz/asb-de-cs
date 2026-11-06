-- Audit / observability schema.  Persistent across runs (never dropped).
CREATE SCHEMA IF NOT EXISTS audit;

-- One row per pipeline execution.
CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id          VARCHAR PRIMARY KEY,
    batch_label     VARCHAR,
    source_dir      VARCHAR,
    batch_dir       VARCHAR,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    status          VARCHAR NOT NULL,          -- RUNNING / SUCCEEDED / FAILED
    error_message   VARCHAR
);

-- One row per orchestrated task.
CREATE TABLE IF NOT EXISTS audit.step_log (
    run_id          VARCHAR NOT NULL,
    step_name       VARCHAR NOT NULL,
    status          VARCHAR NOT NULL,          -- SUCCEEDED / FAILED / SKIPPED
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    duration_sec    DOUBLE,
    message         VARCHAR
);

-- One row per CSV file ingested into bronze.
CREATE TABLE IF NOT EXISTS audit.ingestion_log (
    run_id          VARCHAR NOT NULL,
    table_name      VARCHAR NOT NULL,
    source_file     VARCHAR NOT NULL,
    file_size_bytes BIGINT,
    file_sha256     VARCHAR,
    rows_loaded     BIGINT,
    ingested_at     TIMESTAMP NOT NULL
);

-- Row-level outcome of the bronze -> silver (OLTP) load per table.
CREATE TABLE IF NOT EXISTS audit.silver_load_log (
    run_id               VARCHAR NOT NULL,
    table_name           VARCHAR NOT NULL,
    bronze_rows          BIGINT,
    exact_duplicates     BIGINT,
    archived_versions    BIGINT,
    quarantined_rows     BIGINT,
    loaded_rows          BIGINT,
    invalid_casts        BIGINT,
    loaded_at            TIMESTAMP NOT NULL
);

-- Outcome of every SCD merge.
CREATE TABLE IF NOT EXISTS audit.scd_log (
    run_id           VARCHAR NOT NULL,
    dimension        VARCHAR NOT NULL,
    scd_type         VARCHAR NOT NULL,
    new_members      BIGINT,
    new_versions     BIGINT,   -- type 2 changes (old row closed + new row inserted)
    type1_updates    BIGINT,
    unchanged        BIGINT,
    loaded_at        TIMESTAMP NOT NULL
);

-- Outcome of every fact merge.
CREATE TABLE IF NOT EXISTS audit.fact_load_log (
    run_id           VARCHAR NOT NULL,
    fact_table       VARCHAR NOT NULL,
    staged_rows      BIGINT,
    inserted_rows    BIGINT,
    updated_rows     BIGINT,
    deleted_rows     BIGINT,
    total_rows       BIGINT,
    loaded_at        TIMESTAMP NOT NULL
);

-- Data quality results.
CREATE TABLE IF NOT EXISTS audit.dq_results (
    run_id           VARCHAR NOT NULL,
    stage            VARCHAR NOT NULL,          -- oltp / final
    check_name       VARCHAR NOT NULL,
    severity         VARCHAR NOT NULL,          -- critical / warning
    failed_rows      BIGINT NOT NULL,
    passed           BOOLEAN NOT NULL,
    description      VARCHAR,
    checked_at       TIMESTAMP NOT NULL
);

-- Free-form numeric metrics (row counts, etc.).
CREATE TABLE IF NOT EXISTS audit.run_metrics (
    run_id           VARCHAR NOT NULL,
    step_name        VARCHAR NOT NULL,
    metric_name      VARCHAR NOT NULL,
    metric_value     DOUBLE,
    detail           VARCHAR,
    recorded_at      TIMESTAMP NOT NULL
);

-- Quarantine for records rejected by the silver (OLTP) load.
CREATE SCHEMA IF NOT EXISTS quarantine;
CREATE TABLE IF NOT EXISTS quarantine.rejected_records (
    run_id           VARCHAR NOT NULL,
    table_name       VARCHAR NOT NULL,
    reason           VARCHAR NOT NULL,
    record           JSON,
    rejected_at      TIMESTAMP NOT NULL
);
