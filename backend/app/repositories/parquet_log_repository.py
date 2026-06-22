from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd


class ParquetLogRepository:
    def __init__(self, path: Path, columns: list[str]) -> None:
        self.path = path
        self.columns = columns

    def exists(self) -> bool:
        return self.path.exists()

    def read(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame(columns=self.columns)

        dataframe = pd.read_parquet(self.path)
        return self._normalize_columns(dataframe)

    def append(self, records: Iterable[dict[str, object]]) -> None:
        records_list = list(records)
        if not records_list:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)

        current = self.read()
        incoming = self._normalize_columns(pd.DataFrame.from_records(records_list))
        updated = pd.concat([current, incoming], ignore_index=True)
        self._write_atomic(updated)

    def overwrite(self, dataframe: pd.DataFrame) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_atomic(self._normalize_columns(dataframe))

    def _normalize_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        normalized = dataframe.copy()

        for column in self.columns:
            if column not in normalized.columns:
                normalized[column] = None

        return normalized[self.columns]

    def _write_atomic(self, dataframe: pd.DataFrame) -> None:
        with NamedTemporaryFile(
            suffix=".parquet",
            delete=False,
            dir=self.path.parent,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        try:
            dataframe.to_parquet(temporary_path, index=False)
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
