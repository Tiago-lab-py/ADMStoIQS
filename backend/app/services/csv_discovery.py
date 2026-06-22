from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.app.core.contracts import MIN_ANOMES, SOURCE_CSV_PATTERN, SOURCE_DIR


CSV_NAME_PATTERN = re.compile(
    r"^Interrupcoes_IQS_(?P<timestamp>\d{14})_(?P<tipo>[A-Z0-9]+)\.CSV$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CsvFile:
    path: Path
    name: str
    size_bytes: int
    modified_at: datetime
    anomes: str
    regional_origem: str

    @property
    def processing_key(self) -> tuple[str, int, datetime]:
        return (
            str(self.path),
            self.size_bytes,
            self.modified_at.replace(microsecond=0),
        )


def extract_anomes_from_name(file_name: str) -> str | None:
    match = CSV_NAME_PATTERN.match(file_name)
    if match is None:
        return None

    return match.group("timestamp")[:6]


def extract_regional_from_name(file_name: str) -> str | None:
    match = CSV_NAME_PATTERN.match(file_name)
    if match is None:
        return None

    return match.group("tipo").upper()


def discover_csv_files(
    source_dir: Path = SOURCE_DIR,
    min_anomes: str = MIN_ANOMES,
    pattern: str = SOURCE_CSV_PATTERN,
) -> list[CsvFile]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Diretório de origem não encontrado: {source_dir}")

    csv_files: list[CsvFile] = []

    for path in source_dir.glob(pattern):
        if not path.is_file():
            continue

        anomes = extract_anomes_from_name(path.name)
        regional_origem = extract_regional_from_name(path.name)
        if anomes is None or regional_origem is None or anomes < min_anomes:
            continue

        stat = path.stat()
        csv_files.append(
            CsvFile(
                path=path,
                name=path.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime).replace(microsecond=0),
                anomes=anomes,
                regional_origem=regional_origem,
            )
        )

    return sorted(csv_files, key=lambda item: (item.anomes, item.name))
