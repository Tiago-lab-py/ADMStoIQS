from __future__ import annotations

import shutil
from pathlib import Path

from backend.app.core.contracts import RAW_TEMP_DIR


def clean_raw_temp(raw_temp_dir: Path = RAW_TEMP_DIR) -> None:
    raw_temp_dir.mkdir(parents=True, exist_ok=True)

    for path in raw_temp_dir.iterdir():
        if path.name == ".gitkeep":
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

