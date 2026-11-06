"""Step 0: download the raw Wide World Importers CSV files with ``kagglehub``.

The whole dataset ``pauloviniciusornelas/wwimporters`` is downloaded with
``kagglehub.dataset_download`` straight into ``data/raw`` (the files are then
ingested by DuckDB - pandas is not used in the pipeline).  Credentials, when
needed, are read by kagglehub from KAGGLE_USERNAME / KAGGLE_KEY (also via the
project's ``.env``) or ``~/.kaggle/kaggle.json``.

``preview_file`` is the kagglehub pandas-adapter snippet, kept for quickly
inspecting a single file (``python run_pipeline.py preview <file>``).

Raw files are written once and never modified by the pipeline.
"""

from __future__ import annotations

from pathlib import Path

from .config import KAGGLE_DATASET, Settings
from .logging_utils import get_logger
from .sources import missing_required, resolve_sources

log = get_logger()


class DownloadError(RuntimeError):
    pass


def download_from_kaggle(settings: Settings) -> Path:
    try:
        import kagglehub
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise DownloadError("kagglehub is not installed: pip install -r requirements.txt") from exc

    log.info("Downloading Kaggle dataset %s with kagglehub into %s", KAGGLE_DATASET, settings.raw_dir)
    try:
        path = kagglehub.dataset_download(
            KAGGLE_DATASET,
            force_download=settings.force_download,
            output_dir=str(settings.raw_dir),
        )
    except Exception as exc:  # network / auth / API errors
        raise DownloadError(
            f"kagglehub download of {KAGGLE_DATASET} failed: {exc}. Check KAGGLE_USERNAME/KAGGLE_KEY "
            f"or download the dataset manually and unzip the CSV files into {settings.raw_dir}"
        ) from exc
    log.info("kagglehub finished: %s", path)
    return Path(path)


def download_raw_files(settings: Settings) -> dict[str, Path]:
    """Ensure every required raw file exists locally; download the dataset if any is missing."""
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    resolved = resolve_sources(settings.raw_dir)
    if not settings.force_download and not missing_required(resolved):
        log.info("All required raw files already present in %s - download skipped", settings.raw_dir)
        return resolved
    if not settings.download:
        raise DownloadError(f"Missing raw files and downloads are disabled: {missing_required(resolved)}")

    download_from_kaggle(settings)

    resolved = resolve_sources(settings.raw_dir)
    missing = missing_required(resolved)
    if missing:
        raise DownloadError(f"Required raw files are missing after download: {', '.join(missing)}")
    log.info("%d source files available in %s", len(resolved), settings.raw_dir)
    return resolved


def preview_file(file_path: str, rows: int = 5) -> None:
    """Load one file of the dataset with the kagglehub pandas adapter and print the first rows.

    Exploration only (requires ``kagglehub[pandas-datasets]``); the pipeline ingests with DuckDB.
    """
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    df = kagglehub.load_dataset(KaggleDatasetAdapter.PANDAS, KAGGLE_DATASET, file_path)
    print(f"First {rows} records:", df.head(rows))
