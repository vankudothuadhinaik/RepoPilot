from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    raw = os.getenv("REP PILOT_DATA_DIR") or os.getenv("REP_PILOT_DATA_DIR") or ".repopilot"
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "repopilot.sqlite3"
