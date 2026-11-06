"""Command-line entry point.

    python -m wwi_pipeline run                 # full pipeline (single entry point)
    python -m wwi_pipeline demo                # run + idempotent re-run + SCD batch + report
    python -m wwi_pipeline download            # only fetch the raw CSV files
    python -m wwi_pipeline make-scd-batch      # build the 2nd (change) batch
    python -m wwi_pipeline report              # business queries -> Markdown
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

from .config import PROJECT_ROOT, Settings, load_dotenv
from .download import download_raw_files
from .logging_utils import setup_logging
from .pipeline import PipelineError, run_pipeline
from .report import write_business_report, write_run_summary
from .scd_batch import make_scd_batch

DEFAULT_BATCH_DIR = PROJECT_ROOT / "data" / "batches" / "batch_002"
DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence"


def _settings(args: argparse.Namespace) -> Settings:
    s = Settings()
    if getattr(args, "raw_dir", None):
        s.raw_dir = Path(args.raw_dir).resolve()
    if getattr(args, "db", None):
        s.db_path = Path(args.db).resolve()
    if getattr(args, "batch_dir", None):
        s.batch_dir = Path(args.batch_dir).resolve()
    if getattr(args, "batch_label", None):
        s.batch_label = args.batch_label
    if getattr(args, "no_download", False):
        s.download = False
    if getattr(args, "force_download", False):
        s.force_download = True
    if getattr(args, "threads", None):
        s.threads = args.threads
    return s


def _run(settings: Settings, summary_dir: Path | None = None) -> str:
    ctx = run_pipeline(settings)
    target_dir = summary_dir or settings.log_dir
    stem = f"run_{settings.batch_label}"
    out = write_run_summary(settings.db_path, ctx.run_id, target_dir / f"{stem}.md")
    if summary_dir:  # evidence mode: keep a copy of the plain-text run log too
        shutil.copy(settings.log_dir / f"pipeline_{ctx.run_id}.log", summary_dir / f"{stem}.log")
    print(f"Run summary written to {out}")
    return ctx.run_id


def cmd_run(args: argparse.Namespace) -> int:
    _run(_settings(args))
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    s = _settings(args)
    setup_logging(s.log_dir, "download")
    files = download_raw_files(s)
    print(f"{len(files)} source files available in {s.raw_dir}")
    return 0


def cmd_make_batch(args: argparse.Namespace) -> int:
    s = _settings(args)
    setup_logging(s.log_dir, "make_scd_batch")
    out = make_scd_batch(s.raw_dir, Path(args.out).resolve(), date.fromisoformat(args.effective_date))
    print(f"SCD change batch written to {out}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    s = _settings(args)
    out = write_business_report(s.db_path, Path(args.out).resolve())
    print(f"Business query results written to {out}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Reproduce all evidence: initial load, idempotent re-run, SCD2 change batch, queries."""
    s = _settings(args)
    evidence = Path(args.evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    if args.fresh and s.db_path.exists():
        s.db_path.unlink()
        Path(str(s.db_path) + ".wal").unlink(missing_ok=True)

    s.batch_label, s.batch_dir = "batch_001", None
    _run(s, evidence)
    s.batch_label = "batch_001_rerun"
    _run(s, evidence)

    batch_dir = Path(args.batch_dir).resolve() if args.batch_dir else DEFAULT_BATCH_DIR
    setup_logging(s.log_dir, "make_scd_batch")
    make_scd_batch(s.raw_dir, batch_dir)
    shutil.copy(batch_dir / "manifest.json", evidence / "batch_002_manifest.json")
    s.batch_label, s.batch_dir = "batch_002", batch_dir
    _run(s, evidence)
    s.batch_label = "batch_002_rerun"
    _run(s, evidence)

    write_business_report(s.db_path, evidence / "business_queries.md")
    print(f"Evidence written to {evidence}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wwi_pipeline", description="Wide World Importers DuckDB pipeline")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--raw-dir", help="directory with the raw CSV files (default data/raw)")
    common.add_argument("--db", help="DuckDB database file (default data/warehouse/wwi.duckdb)")
    common.add_argument("--threads", type=int, help="DuckDB worker threads")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", parents=[common], help="run the end-to-end pipeline")
    p.add_argument("--batch-dir", help="directory whose CSV files override the raw files (change batch)")
    p.add_argument("--batch-label", default="batch_001", help="label recorded in audit.pipeline_runs")
    p.add_argument("--no-download", action="store_true", help="fail instead of downloading missing files")
    p.add_argument("--force-download", action="store_true", help="download even if files are present")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("download", parents=[common], help="download the raw CSV files")
    p.add_argument("--force-download", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("make-scd-batch", parents=[common], help="create the second (SCD change) batch")
    p.add_argument("--out", default=str(DEFAULT_BATCH_DIR))
    p.add_argument("--effective-date", default="2016-07-15")
    p.set_defaults(func=cmd_make_batch)

    p = sub.add_parser("report", parents=[common], help="run the business queries")
    p.add_argument("--out", default=str(DEFAULT_EVIDENCE_DIR / "business_queries.md"))
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("demo", parents=[common], help="initial load, re-run, SCD batch, re-run, report")
    p.add_argument("--batch-dir", help="where to write the change batch (default data/batches/batch_002)")
    p.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    p.add_argument("--fresh", action="store_true", help="delete the warehouse database first")
    p.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PipelineError as exc:
        print(f"Pipeline FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
