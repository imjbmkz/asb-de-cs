#!/usr/bin/env python3
"""Single entry point for the whole pipeline (no installation required).

    python run_pipeline.py run      # download (if needed) -> bronze -> silver -> gold -> DQ
    python run_pipeline.py demo     # full evidence run incl. SCD2 second batch
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from wwi_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["run"]))
