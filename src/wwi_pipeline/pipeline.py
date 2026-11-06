"""Orchestration: the end-to-end pipeline as plain Python functions.

Each task is a function ``fn(ctx) -> dict | None`` with explicit upstream
dependencies.  The runner executes tasks in dependency order, logs every task to
``audit.step_log`` and the run log file, and on failure marks downstream tasks
SKIPPED.  The final task (record the pipeline result) always runs.

    download_raw_files
        -> validate_source_files
            -> prepare_oltp_database
                -> ingest_csv_to_bronze          (CSV -> staging)
                    -> load_oltp_silver          (staging -> typed OLTP)
                        -> validate_oltp         (DQ gate 1)
                            -> prepare_olap      (gold DDL + OLAP staging)
                                -> load_dimensions   (SCD1 / SCD2)
                                    -> load_facts
                                        -> final_quality_checks (DQ gate 2)
    record_pipeline_result (always)
"""

from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import duckdb

from . import bronze, gold, quality, silver
from .config import Settings
from .db import connect, ensure_audit_schema, log_metric, log_step, row_count
from .download import download_raw_files
from .logging_utils import get_logger, setup_logging
from .sources import missing_required, resolve_sources

log = get_logger()


class PipelineError(RuntimeError):
    pass


@dataclass
class Context:
    settings: Settings
    run_id: str
    run_ts: str
    con: duckdb.DuckDBPyConnection
    files: dict[str, Path] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    name: str
    fn: Callable[[Context], Any]
    upstream: tuple[str, ...] = ()
    description: str = ""


# --------------------------------------------------------------------------- tasks
def t_download(ctx: Context) -> dict:
    files = download_raw_files(ctx.settings)
    return {"raw_files": len(files)}


def t_validate_sources(ctx: Context) -> dict:
    files = resolve_sources(ctx.settings.raw_dir, ctx.settings.batch_dir)
    missing = missing_required(files)
    if missing:
        raise PipelineError(f"Required source files missing: {', '.join(missing)}")
    for table, path in files.items():
        origin = "batch" if ctx.settings.batch_dir and path.parent == ctx.settings.batch_dir.resolve() else "raw"
        log.info("  %-34s %-6s %10.1f KB  %s", table, origin, path.stat().st_size / 1024, path)
    ctx.files = files
    return {"source_files": len(files)}


def t_prepare_oltp(ctx: Context) -> dict:
    return {"oltp_tables": silver.prepare_oltp(ctx.con)}


def t_ingest_bronze(ctx: Context) -> dict:
    counts = bronze.load_bronze(ctx.con, ctx.files, ctx.run_id)
    for table, n in counts.items():
        log_metric(ctx.con, ctx.run_id, "ingest_csv_to_bronze", f"bronze.{table}.rows", n)
    return {"bronze_rows": sum(counts.values())}


def t_load_oltp(ctx: Context) -> dict:
    stats = silver.load_oltp(ctx.con, ctx.run_id)
    return {
        "silver_rows": sum(s.get("loaded_rows", 0) for s in stats.values()),
        "quarantined_rows": sum(s.get("quarantined_rows", 0) for s in stats.values()),
    }


def t_validate_oltp(ctx: Context) -> dict:
    res = quality.run_checks(ctx.con, ctx.run_id, "oltp", quality.OLTP_CHECKS)
    return {"checks": len(res), "warnings": sum(not r["passed"] for r in res)}


def t_prepare_olap(ctx: Context) -> dict:
    return gold.prepare_olap(ctx.con)


def t_load_dimensions(ctx: Context) -> dict:
    stats = gold.load_dimensions(ctx.con, ctx.run_id, ctx.run_ts)
    for dim in ("dim_date", "dim_city", "dim_customer", "dim_employee", "dim_stock_item", "dim_delivery_method"):
        log_metric(ctx.con, ctx.run_id, "load_dimensions", f"gold.{dim}.rows", row_count(ctx.con, "gold", dim))
    return {d: s for d, s in stats.items()}


def t_load_facts(ctx: Context) -> dict:
    stats = gold.load_facts(ctx.con, ctx.run_id)
    for fact, s in stats.items():
        log_metric(ctx.con, ctx.run_id, "load_facts", f"gold.{fact}.rows", s["total_rows"])
    return stats


def t_final_checks(ctx: Context) -> dict:
    res = quality.run_checks(ctx.con, ctx.run_id, "final", quality.FINAL_CHECKS)
    return {"checks": len(res), "warnings": sum(not r["passed"] for r in res)}


TASKS: list[Task] = [
    Task("download_raw_files", t_download, (), "Download the Kaggle CSV export if not present"),
    Task("validate_source_files", t_validate_sources, ("download_raw_files",), "Check required files exist"),
    Task("prepare_oltp_database", t_prepare_oltp, ("validate_source_files",), "Create OLTP (silver) schema"),
    Task("ingest_csv_to_bronze", t_ingest_bronze, ("prepare_oltp_database",), "CSV -> bronze staging"),
    Task("load_oltp_silver", t_load_oltp, ("ingest_csv_to_bronze",), "bronze -> typed OLTP + quarantine"),
    Task("validate_oltp", t_validate_oltp, ("load_oltp_silver",), "OLTP data-quality gate"),
    Task("prepare_olap", t_prepare_olap, ("validate_oltp",), "Gold schema + OLAP staging tables"),
    Task("load_dimensions", t_load_dimensions, ("prepare_olap",), "dim_date + SCD1/SCD2 dimensions"),
    Task("load_facts", t_load_facts, ("load_dimensions",), "fact_order, fact_sale"),
    Task("final_quality_checks", t_final_checks, ("load_facts",), "Final data-quality gate"),
]


def _topological(tasks: list[Task]) -> list[Task]:
    by_name, ordered, seen = {t.name: t for t in tasks}, [], set()

    def visit(task: Task, stack: tuple[str, ...] = ()) -> None:
        if task.name in seen:
            return
        if task.name in stack:
            raise PipelineError(f"Cycle in task graph at {task.name}")
        for up in task.upstream:
            visit(by_name[up], stack + (task.name,))
        seen.add(task.name)
        ordered.append(task)

    for t in tasks:
        visit(t)
    return ordered


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:6]


def run_pipeline(settings: Settings, tasks: list[Task] | None = None) -> Context:
    """Execute the full pipeline.  Raises PipelineError if any task failed."""
    run_id = new_run_id()
    log_file = setup_logging(settings.log_dir, run_id)
    started = datetime.now()
    log.info("=" * 100)
    log.info("WWI pipeline run %s | batch=%s | db=%s", run_id, settings.batch_label, settings.db_path)
    log.info("raw_dir=%s batch_dir=%s", settings.raw_dir, settings.batch_dir)
    log.info("=" * 100)

    con = connect(settings)
    ensure_audit_schema(con)
    con.execute(
        "INSERT INTO audit.pipeline_runs VALUES (?, ?, ?, ?, ?, NULL, 'RUNNING', NULL)",
        [run_id, settings.batch_label, str(settings.raw_dir), str(settings.batch_dir or ""), started],
    )
    ctx = Context(settings, run_id, started.strftime("%Y-%m-%d %H:%M:%S"), con)

    status: dict[str, str] = {}
    error: str | None = None
    for task in _topological(tasks or TASKS):
        t0 = datetime.now()
        if any(status.get(up) != "SUCCEEDED" for up in task.upstream):
            status[task.name] = "SKIPPED"
            log.warning("[SKIPPED] %s (upstream did not succeed)", task.name)
            log_step(con, run_id, task.name, "SKIPPED", t0, t0, "upstream did not succeed")
            continue
        log.info("[START] %s - %s", task.name, task.description)
        try:
            result = task.fn(ctx)
            ctx.results[task.name] = result
            status[task.name] = "SUCCEEDED"
            t1 = datetime.now()
            log.info("[DONE ] %s in %.1fs", task.name, (t1 - t0).total_seconds())
            log_step(con, run_id, task.name, "SUCCEEDED", t0, t1, None)
        except Exception as exc:  # noqa: BLE001 - every failure is recorded
            status[task.name] = "FAILED"
            error = f"{task.name}: {exc}"
            t1 = datetime.now()
            log.error("[FAIL ] %s: %s", task.name, exc)
            log.error(traceback.format_exc())
            log_step(con, run_id, task.name, "FAILED", t0, t1, str(exc)[:2000])

    # ---- record the pipeline result (always runs) --------------------------------
    final = "SUCCEEDED" if error is None else "FAILED"
    finished = datetime.now()
    con.execute(
        "UPDATE audit.pipeline_runs SET finished_at = ?, status = ?, error_message = ? WHERE run_id = ?",
        [finished, final, error, run_id],
    )
    log_step(con, run_id, "record_pipeline_result", "SUCCEEDED", finished, finished, final)
    log.info("=" * 100)
    log.info("Pipeline run %s %s in %.1fs  (log: %s)", run_id, final, (finished - started).total_seconds(), log_file)
    log.info("=" * 100)
    con.execute("CHECKPOINT")
    con.close()
    if error:
        raise PipelineError(error)
    return ctx
