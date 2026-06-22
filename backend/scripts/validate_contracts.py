from __future__ import annotations

from backend.app.core.contracts import (
    DEDUP_KEY_COLUMNS,
    DUCKDB_STAGING_DIR,
    LOG_ALTERACOES_PATH,
    LOG_LEITURA_CSV_PATH,
    LOG_OMS_UNION_PATH,
    MART_DIR,
    MIN_ANOMES,
    OMS_UNION_CORRIGIDO_PARQUET_PATH,
    OMS_UNION_PARQUET_PATH,
    PROCESSED_DIR,
    RAW_TEMP_DIR,
    SOURCE_CSV_ENCODINGS,
    SOURCE_CSV_PATTERN,
    SOURCE_DIR,
    ensure_data_directories,
    processed_parquet_path,
)
from backend.app.schemas.export_layout import CSV_HEADER_FIELDS
from backend.app.schemas.log_alteracoes import LOG_ALTERACOES_COLUMNS
from backend.app.schemas.log_leitura_csv import LOG_LEITURA_CSV_COLUMNS


def validate_contracts() -> None:
    ensure_data_directories()

    if len(MIN_ANOMES) != 6 or not MIN_ANOMES.isdigit():
        raise ValueError("MIN_ANOMES deve estar no formato YYYYMM.")

    duplicated_export_columns = [
        column
        for column in CSV_HEADER_FIELDS
        if CSV_HEADER_FIELDS.count(column) > 1
    ]
    if duplicated_export_columns:
        duplicated = ", ".join(sorted(set(duplicated_export_columns)))
        raise ValueError(f"Colunas duplicadas no layout de exportação: {duplicated}")

    missing_dedup_columns = [
        column
        for column in DEDUP_KEY_COLUMNS
        if column not in CSV_HEADER_FIELDS
    ]
    if missing_dedup_columns:
        missing = ", ".join(missing_dedup_columns)
        raise ValueError(f"Chave de deduplicação ausente do CSV final: {missing}")

    print("Contratos ADMStoIQS validados com sucesso.")
    print(f"Origem configurada: {SOURCE_DIR}")
    print(f"Padrão CSV: {SOURCE_CSV_PATTERN}")
    print(f"Encodings CSV: {', '.join(SOURCE_CSV_ENCODINGS)}")
    print(f"Competência inicial: {MIN_ANOMES}")
    print(f"Temporários: {RAW_TEMP_DIR}")
    print(f"Processados: {PROCESSED_DIR}")
    print(f"Mart: {MART_DIR}")
    print(f"OMS union: {OMS_UNION_PARQUET_PATH}")
    print(f"OMS union corrigido: {OMS_UNION_CORRIGIDO_PARQUET_PATH}")
    print(
        "Parquet exemplo da competência inicial "
        f"({MIN_ANOMES}): {processed_parquet_path(MIN_ANOMES)}"
    )
    print(f"Log leitura: {LOG_LEITURA_CSV_PATH}")
    print(f"Log alterações: {LOG_ALTERACOES_PATH}")
    print(f"Log OMS union: {LOG_OMS_UNION_PATH}")
    print(f"Staging incremental: {DUCKDB_STAGING_DIR}")
    print(f"Campos log leitura: {len(LOG_LEITURA_CSV_COLUMNS)}")
    print(f"Campos log alterações: {len(LOG_ALTERACOES_COLUMNS)}")
    print(f"Campos CSV exportação: {len(CSV_HEADER_FIELDS)}")


if __name__ == "__main__":
    validate_contracts()
