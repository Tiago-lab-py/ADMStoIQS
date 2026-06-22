from __future__ import annotations

import pandas as pd

from backend.app.core.contracts import LOG_LEITURA_CSV_PATH
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.log_leitura_csv import LOG_LEITURA_CSV_COLUMNS


def main() -> None:
    repository = ParquetLogRepository(
        path=LOG_LEITURA_CSV_PATH,
        columns=LOG_LEITURA_CSV_COLUMNS,
    )
    dataframe = repository.read()

    if dataframe.empty:
        print("Log de leitura vazio. Nada a compactar.")
        return

    before = len(dataframe)
    dataframe["processado_em"] = pd.to_datetime(dataframe["processado_em"])
    compacted = (
        dataframe.sort_values("processado_em")
        .drop_duplicates(
            subset=[
                "arquivo_path",
                "arquivo_tamanho_bytes",
                "arquivo_modificado_em",
                "status",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    repository.overwrite(compacted)
    after = len(compacted)

    print(f"Log compactado: {before} -> {after} registros.")
    print(f"Arquivo: {LOG_LEITURA_CSV_PATH}")


if __name__ == "__main__":
    main()
