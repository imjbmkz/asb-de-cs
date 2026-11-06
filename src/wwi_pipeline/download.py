"""Step 0: download the raw Wide World Importers CSV files.

Primary source: the Kaggle dataset ``pauloviniciusornelas/wwimporters`` through the
Kaggle REST API (credentials from KAGGLE_USERNAME/KAGGLE_KEY, ``.env`` or
``~/.kaggle/kaggle.json``).  If Kaggle cannot be reached, an optional mirror of the
same CSV export is used file by file.

Raw files are written once and never modified by the pipeline.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .config import KAGGLE_DOWNLOAD_URL, Settings
from .logging_utils import get_logger
from .sources import SOURCES, missing_required, resolve_sources

log = get_logger()
CHUNK = 1024 * 1024


class DownloadError(RuntimeError):
    pass


def _kaggle_credentials() -> tuple[str, str] | None:
    user, key = os.environ.get("KAGGLE_USERNAME"), os.environ.get("KAGGLE_KEY")
    if user and key:
        return user, key
    cfg = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    if cfg.exists():
        data = json.loads(cfg.read_text())
        return data.get("username"), data.get("key")
    return None


def _stream(url: str, target: Path, headers: dict[str, str] | None = None, timeout: int = 600) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "wwi-pipeline/1.0", **(headers or {})})
    tmp = target.with_suffix(target.suffix + ".part")
    size = 0
    with urllib.request.urlopen(request, timeout=timeout) as response, open(tmp, "wb") as fh:
        while chunk := response.read(CHUNK):
            fh.write(chunk)
            size += len(chunk)
    tmp.replace(target)
    return size


def _safe_extract(zip_path: Path, target_dir: Path) -> int:
    """Extract CSV members only, flattening folders and refusing path traversal."""
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            name = Path(member.filename).name
            if member.is_dir() or not name.lower().endswith(".csv") or name in ("", ".", ".."):
                continue
            with archive.open(member) as src, open(target_dir / name, "wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK)
            count += 1
    return count


def download_from_kaggle(settings: Settings) -> bool:
    creds = _kaggle_credentials()
    if not creds:
        log.warning("Kaggle credentials not found (KAGGLE_USERNAME / KAGGLE_KEY or ~/.kaggle/kaggle.json)")
        return False
    token = base64.b64encode(f"{creds[0]}:{creds[1]}".encode()).decode()
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    zip_path = settings.download_dir / "wwimporters.zip"
    try:
        log.info("Downloading Kaggle dataset from %s", KAGGLE_DOWNLOAD_URL)
        size = _stream(KAGGLE_DOWNLOAD_URL, zip_path, {"Authorization": f"Basic {token}"})
        log.info("Downloaded %.1f MB", size / CHUNK)
        n = _safe_extract(zip_path, settings.raw_dir)
        log.info("Extracted %d CSV files into %s", n, settings.raw_dir)
        return True
    except (urllib.error.URLError, OSError, zipfile.BadZipFile) as exc:
        log.warning("Kaggle download failed: %s", exc)
        return False


def download_from_mirror(settings: Settings) -> bool:
    if not settings.mirror_url:
        return False
    log.info("Downloading CSV files from mirror %s", settings.mirror_url)
    ok = True
    for source in SOURCES:
        target = settings.raw_dir / source.filename
        if target.exists() and target.stat().st_size > 0:
            continue
        url = f"{settings.mirror_url.rstrip('/')}/{source.filename}"
        try:
            size = _stream(url, target)
            log.info("  %-40s %10.1f MB", source.filename, size / CHUNK)
        except (urllib.error.URLError, OSError) as exc:
            level = log.error if source.required else log.warning
            level("  %-40s FAILED (%s)", source.filename, exc)
            ok = ok and not source.required
    return ok


def download_raw_files(settings: Settings) -> dict[str, Path]:
    """Ensure every required raw file exists locally; download only what is missing."""
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    resolved = resolve_sources(settings.raw_dir)
    if not settings.force_download and not missing_required(resolved):
        log.info("All required raw files already present in %s - download skipped", settings.raw_dir)
        return resolved
    if not settings.download:
        raise DownloadError(f"Missing raw files and downloads are disabled: {missing_required(resolved)}")

    if not download_from_kaggle(settings):
        download_from_mirror(settings)

    resolved = resolve_sources(settings.raw_dir)
    missing = missing_required(resolved)
    if missing:
        raise DownloadError(
            "Required raw files are missing after download: "
            + ", ".join(missing)
            + ".  Download the Kaggle dataset manually and unzip it into "
            + str(settings.raw_dir)
        )
    return resolved
