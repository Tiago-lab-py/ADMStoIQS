from __future__ import annotations

import argparse
import shutil

from backend.app.core.contracts import (
    DUCKDB_STAGING_DIR,
    LOG_LEITURA_CSV_PATH,
    processed_parquet_path,
)
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.log_leitura_csv import LOG_LEITURA_CSV_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove controles de uma competência para permitir reprocessamento.",
    )
    parser.add_argument(
        "--anomes",
        required=True,
        help="Competência no formato YYYYMM.",
    )
    parser.add_argument(
        "--remover-parquet",
        action="store_true",
        help="Remove também o Parquet processado da competência.",
    )
    parser.add_argument(
        "--remover-staging",
        action="store_true",
        help="Remove também os Parquets de staging da competência.",
    )
    args = parser.parse_args()

    if len(args.anomes) != 6 or not args.anomes.isdigit():
        raise SystemExit("--anomes deve estar no formato YYYYMM.")

    repository = ParquetLogRepository(
        path=LOG_LEITURA_CSV_PATH,
        columns=LOG_LEITURA_CSV_COLUMNS,
    )
    dataframe = repository.read()

    before = len(dataframe)
    filtered = dataframe[dataframe["anomes"].astype(str) != args.anomes].copy()
    repository.overwrite(filtered)
    after = len(filtered)

    print(f"Registros removidos do log: {before - after}")
    print(f"Log atualizado: {LOG_LEITURA_CSV_PATH}")

    if args.remover_parquet:
        parquet_path = processed_parquet_path(args.anomes)
        if parquet_path.exists():
            parquet_path.unlink()
            print(f"Parquet removido: {parquet_path}")
        else:
            print(f"Parquet não encontrado: {parquet_path}")

    if args.remover_staging:
        staging_path = DUCKDB_STAGING_DIR / args.anomes
        if staging_path.exists():
            shutil.rmtree(staging_path)
            print(f"Staging removido: {staging_path}")
        else:
            print(f"Staging não encontrado: {staging_path}")


if __name__ == "__main__":
    main()

