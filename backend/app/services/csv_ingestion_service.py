from __future__ import annotations

import os
import re
import shutil
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from backend.app.core.contracts import (
    DEDUP_KEY_COLUMNS,
    DUCKDB_PATH,
    DUCKDB_STAGING_DIR,
    LOG_LEITURA_CSV_PATH,
    PROCESSED_DIR,
    RAW_TEMP_DIR,
    SOURCE_CSV_ENCODINGS,
    ensure_data_directories,
    processed_parquet_path,
)
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.log_leitura_csv import LOG_LEITURA_CSV_COLUMNS, LogLeituraCsv
from backend.app.services.csv_discovery import CsvFile, discover_csv_files
from backend.app.services.raw_temp import clean_raw_temp


@dataclass(frozen=True)
class MonthlyIngestionResult:
    anomes: str
    arquivos_processados: int
    arquivos_com_erro: int
    linhas_lidas: int
    linhas_processadas: int
    parquet_path: Path


@dataclass(frozen=True)
class IngestionSummary:
    arquivos_encontrados: int
    arquivos_pendentes: int
    meses_processados: int
    resultados: list[MonthlyIngestionResult]


class CsvIngestionService:
    def __init__(
        self,
        duckdb_path: Path = DUCKDB_PATH,
        log_leitura_path: Path = LOG_LEITURA_CSV_PATH,
        raw_temp_dir: Path = RAW_TEMP_DIR,
        staging_dir: Path = DUCKDB_STAGING_DIR,
    ) -> None:
        self.duckdb_path = duckdb_path
        self.log_repository = ParquetLogRepository(
            path=log_leitura_path,
            columns=LOG_LEITURA_CSV_COLUMNS,
        )
        self.raw_temp_dir = raw_temp_dir
        self.staging_dir = staging_dir

    def process_pending(
        self,
        anomes: str | None = None,
        clean_temp: bool = True,
    ) -> IngestionSummary:
        ensure_data_directories()

        discovered_files = discover_csv_files()
        if anomes is not None:
            discovered_files = [
                csv_file
                for csv_file in discovered_files
                if csv_file.anomes == anomes
            ]

        processed_keys = self._processed_keys()
        pending_files = [
            csv_file
            for csv_file in discovered_files
            if csv_file.processing_key not in processed_keys
        ]

        files_by_month: dict[str, list[CsvFile]] = defaultdict(list)
        for csv_file in pending_files:
            files_by_month[csv_file.anomes].append(csv_file)

        results: list[MonthlyIngestionResult] = []
        try:
            for month, files in sorted(files_by_month.items()):
                results.append(self._process_month(month, files))
        finally:
            if clean_temp:
                clean_raw_temp(self.raw_temp_dir)

        return IngestionSummary(
            arquivos_encontrados=len(discovered_files),
            arquivos_pendentes=len(pending_files),
            meses_processados=len(results),
            resultados=results,
        )

    def processed_keys(self) -> set[tuple[str, int, datetime]]:
        return self._processed_keys()

    def _process_month(
        self,
        anomes: str,
        csv_files: list[CsvFile],
    ) -> MonthlyIngestionResult:
        if not csv_files:
            raise ValueError("csv_files não pode ser vazio.")

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        self.raw_temp_dir.mkdir(parents=True, exist_ok=True)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

        final_path = processed_parquet_path(anomes)
        temp_path = self.raw_temp_dir / f"{final_path.stem}.tmp.parquet"
        month_staging_dir = self.staging_dir / anomes
        month_staging_dir.mkdir(parents=True, exist_ok=True)
        processed_at = datetime.now()

        file_row_counts: dict[Path, int] = {}
        staged_paths: list[Path] = []
        staged_files: list[CsvFile] = []
        failed_files: list[CsvFile] = []
        connection: duckdb.DuckDBPyConnection | None = None

        try:
            connection = duckdb.connect(str(self.duckdb_path))

            total_files = len(csv_files)
            for index, csv_file in enumerate(csv_files, start=1):
                print(
                    f"[{anomes}] Arquivo {index} de {total_files} | "
                    f"{csv_file.regional_origem} | {csv_file.name}"
                )
                try:
                    stage_path = self._stage_csv_file(
                        connection=connection,
                        csv_file=csv_file,
                        month_staging_dir=month_staging_dir,
                    )
                    staged_paths.append(stage_path)
                    staged_files.append(csv_file)
                    file_row_counts[csv_file.path] = self._count_parquet_rows(
                        connection,
                        stage_path,
                    )
                    print(
                        f"[{anomes}] OK {index} de {total_files} | "
                        f"linhas={file_row_counts[csv_file.path]}"
                    )
                except Exception as exc:
                    failed_files.append(csv_file)
                    self._append_error_logs(
                        csv_files=[csv_file],
                        anomes=anomes,
                        processed_at=processed_at,
                        message=str(exc),
                    )
                    print(
                        f"[{anomes}] ERRO {index} de {total_files} | "
                        f"{csv_file.name} | {exc}"
                    )

            if not staged_paths:
                raise RuntimeError(
                    f"Nenhum CSV de {anomes} foi convertido para staging com sucesso."
                )

            self._create_month_views(
                connection=connection,
                staged_paths=staged_paths,
                current_parquet_path=final_path,
            )
            self._validate_required_columns(connection)

            linhas_lidas = sum(file_row_counts.values())
            print(
                f"[{anomes}] Consolidando {len(staged_paths)} arquivo(s) "
                f"de staging com deduplicação..."
            )
            linhas_processadas = self._write_deduplicated_parquet(
                connection=connection,
                output_path=temp_path,
            )
            connection.close()
            connection = None

            os.replace(temp_path, final_path)
            print(f"[{anomes}] Parquet final gravado: {final_path}")

            self._append_success_logs(
                csv_files=staged_files,
                anomes=anomes,
                processed_at=processed_at,
                file_row_counts=file_row_counts,
                linhas_processadas=linhas_processadas,
            )
            if not failed_files:
                shutil.rmtree(month_staging_dir, ignore_errors=True)

            return MonthlyIngestionResult(
                anomes=anomes,
                arquivos_processados=len(staged_files),
                arquivos_com_erro=len(failed_files),
                linhas_lidas=linhas_lidas,
                linhas_processadas=linhas_processadas,
                parquet_path=final_path,
            )
        except Exception as exc:
            unlogged_files = [
                csv_file
                for csv_file in csv_files
                if csv_file not in failed_files and csv_file not in staged_files
            ]
            if unlogged_files:
                self._append_error_logs(
                    csv_files=unlogged_files,
                    anomes=anomes,
                    processed_at=processed_at,
                    message=str(exc),
                )
            raise
        finally:
            if connection is not None:
                connection.close()
            if temp_path.exists():
                temp_path.unlink()

    def _stage_csv_file(
        self,
        connection: duckdb.DuckDBPyConnection,
        csv_file: CsvFile,
        month_staging_dir: Path,
    ) -> Path:
        stage_path = self._stage_path(csv_file, month_staging_dir)

        if stage_path.exists():
            try:
                self._count_parquet_rows(connection, stage_path)
                return stage_path
            except Exception:
                stage_path.unlink()

        temp_stage_path = stage_path.with_suffix(".tmp.parquet")
        if temp_stage_path.exists():
            temp_stage_path.unlink()

        output = _duckdb_string(temp_stage_path)
        converted_path: Path | None = None
        try:
            converted_path = self._convert_csv_to_utf8(csv_file)
            self._copy_csv_to_parquet(
                connection=connection,
                input_path=converted_path,
                output_sql=output,
                regional_origem=csv_file.regional_origem,
            )
            os.replace(temp_stage_path, stage_path)
            return stage_path
        except Exception as exc:
            raise ValueError(
                f"Não foi possível converter e ler {csv_file.path}: {exc}"
            ) from exc
        finally:
            if converted_path is not None and converted_path.exists():
                converted_path.unlink()
            if temp_stage_path.exists():
                temp_stage_path.unlink()

    def _copy_csv_to_parquet(
        self,
        connection: duckdb.DuckDBPyConnection,
        input_path: Path,
        output_sql: str,
        regional_origem: str,
    ) -> None:
        csv_path = _duckdb_string(input_path)
        connection.execute(
            f"""
            COPY (
                SELECT *
                    ,{_duckdb_literal(regional_origem)} AS REGIONAL_ORIGEM
                FROM read_csv_auto(
                    {csv_path},
                    delim = '|',
                    header = true,
                    union_by_name = true,
                    all_varchar = true,
                    nullstr = ['', ' '],
                    encoding = 'utf-8'
                )
            )
            TO {output_sql}
            (
                FORMAT PARQUET,
                COMPRESSION ZSTD
            )
            """
        )

    def _convert_csv_to_utf8(self, csv_file: CsvFile) -> Path:
        converted_dir = self.raw_temp_dir / "converted_utf8"
        converted_dir.mkdir(parents=True, exist_ok=True)

        converted_path = converted_dir / f"{csv_file.name}.utf8.tmp"
        if converted_path.exists():
            converted_path.unlink()

        errors: list[str] = []
        for encoding in SOURCE_CSV_ENCODINGS:
            try:
                with (
                    csv_file.path.open("r", encoding=encoding, errors="strict", newline="") as source,
                    converted_path.open("w", encoding="utf-8", newline="") as target,
                ):
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                return converted_path
            except UnicodeError as exc:
                errors.append(f"{encoding}: {exc}")
                if converted_path.exists():
                    converted_path.unlink()

        raise ValueError(
            f"Não foi possível converter {csv_file.path} para UTF-8 usando "
            f"{', '.join(SOURCE_CSV_ENCODINGS)}. Erros: {'; '.join(errors)}"
        )

    def _stage_path(self, csv_file: CsvFile, month_staging_dir: Path) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", csv_file.name)
        modified_key = csv_file.modified_at.strftime("%Y%m%d%H%M%S")
        file_name = f"{safe_name}.{csv_file.size_bytes}.{modified_key}.parquet"
        return month_staging_dir / file_name

    def _create_month_views(
        self,
        connection: duckdb.DuckDBPyConnection,
        staged_paths: list[Path],
        current_parquet_path: Path,
    ) -> None:
        staged_list = _duckdb_path_list(staged_paths)
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW source_staged AS
            SELECT *
            FROM read_parquet({staged_list}, union_by_name = true)
            """
        )

        if current_parquet_path.exists():
            parquet_path = _duckdb_string(current_parquet_path)
            connection.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW source_existing AS
                SELECT *
                FROM read_parquet({parquet_path})
                """
            )
            connection.execute(
                """
                CREATE OR REPLACE TEMP VIEW source_all AS
                SELECT *, 0 AS __source_priority
                FROM source_existing
                UNION ALL BY NAME
                SELECT *, 1 AS __source_priority
                FROM source_staged
                """
            )
            return

        connection.execute(
            """
            CREATE OR REPLACE TEMP VIEW source_all AS
            SELECT *, 1 AS __source_priority
            FROM source_staged
            """
        )

    def _validate_required_columns(self, connection: duckdb.DuckDBPyConnection) -> None:
        available_columns = {
            row[0]
            for row in connection.execute("DESCRIBE source_all").fetchall()
        }
        missing_columns = [
            column
            for column in DEDUP_KEY_COLUMNS
            if column not in available_columns
        ]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"Colunas obrigatórias ausentes para deduplicação: {missing}")

    def _write_deduplicated_parquet(
        self,
        connection: duckdb.DuckDBPyConnection,
        output_path: Path,
    ) -> int:
        output = _duckdb_string(output_path)
        partition_columns = ", ".join(DEDUP_KEY_COLUMNS)

        connection.execute(
            f"""
            COPY (
                WITH ranked AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY {partition_columns}
                            ORDER BY __source_priority
                        ) AS __rn
                    FROM source_all
                )
                SELECT * EXCLUDE (__source_priority, __rn)
                FROM ranked
                WHERE __rn = 1
            )
            TO {output}
            (
                FORMAT PARQUET,
                COMPRESSION ZSTD
            )
            """
        )

        return self._count_parquet_rows(connection, output_path)

    def _append_success_logs(
        self,
        csv_files: list[CsvFile],
        anomes: str,
        processed_at: datetime,
        file_row_counts: dict[Path, int],
        linhas_processadas: int,
    ) -> None:
        records = [
            LogLeituraCsv(
                arquivo_path=str(csv_file.path),
                arquivo_nome=csv_file.name,
                arquivo_tamanho_bytes=csv_file.size_bytes,
                arquivo_modificado_em=csv_file.modified_at,
                arquivo_hash=None,
                anomes=anomes,
                processado_em=processed_at,
                status="processado",
                linhas_lidas=file_row_counts.get(csv_file.path, 0),
                linhas_processadas=linhas_processadas,
                mensagem_erro=None,
            ).to_record()
            for csv_file in csv_files
        ]
        self.log_repository.append(records)

    def _append_error_logs(
        self,
        csv_files: list[CsvFile],
        anomes: str,
        processed_at: datetime,
        message: str,
    ) -> None:
        records = [
            LogLeituraCsv(
                arquivo_path=str(csv_file.path),
                arquivo_nome=csv_file.name,
                arquivo_tamanho_bytes=csv_file.size_bytes,
                arquivo_modificado_em=csv_file.modified_at,
                arquivo_hash=None,
                anomes=anomes,
                processado_em=processed_at,
                status="erro",
                linhas_lidas=0,
                linhas_processadas=0,
                mensagem_erro=message,
            ).to_record()
            for csv_file in csv_files
        ]
        self.log_repository.append(records)

    def _processed_keys(self) -> set[tuple[str, int, datetime]]:
        dataframe = self.log_repository.read()
        if dataframe.empty:
            return set()

        processed = dataframe[dataframe["status"] == "processado"]
        keys: set[tuple[str, int, datetime]] = set()

        for row in processed.itertuples(index=False):
            modified_at = _to_datetime(row.arquivo_modificado_em)
            if modified_at is None:
                continue

            keys.add(
                (
                    str(row.arquivo_path),
                    int(row.arquivo_tamanho_bytes),
                    modified_at.replace(microsecond=0),
                )
            )

        return keys

    @staticmethod
    def _count_parquet_rows(
        connection: duckdb.DuckDBPyConnection,
        parquet_path: Path,
    ) -> int:
        path = _duckdb_string(parquet_path)
        return int(
            connection.execute(f"SELECT COUNT(*) FROM read_parquet({path})").fetchone()[0]
        )


def _to_datetime(value: object) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return pd.to_datetime(value).to_pydatetime()


def _duckdb_path_list(paths: Iterable[Path]) -> str:
    return "[" + ", ".join(_duckdb_string(path) for path in paths) + "]"


def _duckdb_string(path: Path) -> str:
    value = str(path).replace("'", "''")
    return f"'{value}'"


def _duckdb_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
