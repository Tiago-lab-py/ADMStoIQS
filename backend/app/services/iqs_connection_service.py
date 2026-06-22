from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import oracledb

from backend.app.core.iqs_settings import IqsSettings, get_iqs_settings


class IqsConnectionService:
    def __init__(self, settings: IqsSettings | None = None) -> None:
        self.settings = settings or get_iqs_settings()

    @contextmanager
    def connect(self) -> Iterator[oracledb.Connection]:
        if not self.settings.configured:
            raise RuntimeError("Configuração IQS incompleta. Verifique .env.")

        os.environ["TNS_ADMIN"] = self.settings.config_dir

        connection = oracledb.connect(
            user=self.settings.uid,
            password=self.settings.pwd,
            dsn=self.settings.db,
            config_dir=self.settings.config_dir,
        )

        try:
            yield connection
        finally:
            connection.close()

