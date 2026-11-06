"""Central configuration: paths, environment variables and dataset locations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]
SQL_DIR = PACKAGE_DIR / "sql"

KAGGLE_DATASET = "pauloviniciusornelas/wwimporters"
KAGGLE_DOWNLOAD_URL = f"https://www.kaggle.com/api/v1/datasets/download/{KAGGLE_DATASET}"

# Optional fallback used only when Kaggle is unreachable / no credentials are set.
# This is an unofficial public mirror of the same CSV export (Git LFS).  The base
# URL can be overridden with WWI_MIRROR_URL; set it to an empty string to disable.
DEFAULT_MIRROR_URL = "https://media.githubusercontent.com/media/whitevshadow/DataProfiler/HEAD/data"


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader (KEY=VALUE lines) so no extra dependency is needed.

    Existing environment variables always win over values in the file.
    """
    path = path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key, value)


def _path_from_env(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


@dataclass
class Settings:
    """Runtime settings for one pipeline execution."""

    raw_dir: Path = field(default_factory=lambda: _path_from_env("WWI_RAW_DIR", PROJECT_ROOT / "data" / "raw"))
    db_path: Path = field(
        default_factory=lambda: _path_from_env("WWI_DB_PATH", PROJECT_ROOT / "data" / "warehouse" / "wwi.duckdb")
    )
    log_dir: Path = field(default_factory=lambda: _path_from_env("WWI_LOG_DIR", PROJECT_ROOT / "logs"))
    download_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "downloads")
    # Optional directory whose CSV files override the files in raw_dir (incremental /
    # change batch, used to demonstrate SCD Type 2 with a second load).
    batch_dir: Path | None = None
    batch_label: str = "batch_001"
    download: bool = True
    force_download: bool = False
    mirror_url: str = field(default_factory=lambda: os.environ.get("WWI_MIRROR_URL", DEFAULT_MIRROR_URL))
    threads: int | None = None
    memory_limit: str | None = field(default_factory=lambda: os.environ.get("WWI_MEMORY_LIMIT"))
