from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from backend.app.core.contracts import (
    DEDUP_KEY_COLUMNS,
    LOG_OMS_UNION_PATH,
    MART_DIR,
    OMS_UNION_PARQUET_PATH,
    PROCESSED_DIR,
    RAW_TEMP_DIR,
    ensure_data_directories,
)
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.log_oms_union import LOG_OMS_UNION_COLUMNS, LogOmsUnion


@dataclass(frozen=True)
class OmsUnionResult:
    arquivos_origem: int
    linhas_origem: int
    linhas_saida: int
    parquet_path: Path


class OmsUnionService:
    def __init__(
        self,
        processed_dir: Path = PROCESSED_DIR,
        mart_dir: Path = MART_DIR,
        output_path: Path = OMS_UNION_PARQUET_PATH,
        raw_temp_dir: Path = RAW_TEMP_DIR,
        log_path: Path = LOG_OMS_UNION_PATH,
    ) -> None:
        self.processed_dir = processed_dir
        self.mart_dir = mart_dir
        self.output_path = output_path
        self.raw_temp_dir = raw_temp_dir
        self.log_repository = ParquetLogRepository(
            path=log_path,
            columns=LOG_OMS_UNION_COLUMNS,
        )

    def build(self) -> OmsUnionResult:
        run_id = uuid4().hex
        linhas_origem = 0
        linhas_saida = 0
        source_paths: list[Path] = []

        ensure_data_directories()
        self.mart_dir.mkdir(parents=True, exist_ok=True)
        self.raw_temp_dir.mkdir(parents=True, exist_ok=True)
        self._log(
            run_id=run_id,
            etapa="inicio",
            status="inicio",
            mensagem="Iniciando geração do mart OMS_union.",
        )

        try:
            self._log(
                run_id=run_id,
                etapa="descobrir_arquivos",
                status="processando",
                mensagem=f"Buscando Parquets mensais em {self.processed_dir}.",
            )
            source_paths = self._source_paths()
            total_size = sum(path.stat().st_size for path in source_paths)
            self._log(
                run_id=run_id,
                etapa="descobrir_arquivos",
                status="sucesso",
                mensagem=(
                    f"Encontrados {len(source_paths)} arquivo(s), "
                    f"{total_size:,} bytes.".replace(",", ".")
                ),
                arquivos_origem=len(source_paths),
            )

            if not source_paths:
                raise FileNotFoundError(
                    f"Nenhum Parquet mensal encontrado em {self.processed_dir}."
                )

            for index, path in enumerate(source_paths, start=1):
                size = f"{path.stat().st_size:,}".replace(",", ".")
                self._print(
                    f"[OMS_union] Arquivo origem {index} de {len(source_paths)} | "
                    f"{path.name} | {size} bytes"
                )

            temp_path = self.raw_temp_dir / f"{self.output_path.stem}.tmp.parquet"
            if temp_path.exists():
                temp_path.unlink()

            connection = duckdb.connect(":memory:")
            try:
                self._log(
                    run_id=run_id,
                    etapa="criar_view_origem",
                    status="processando",
                    mensagem="Criando view DuckDB com os Parquets mensais.",
                    arquivos_origem=len(source_paths),
                )
                self._print("[OMS_union] Criando view com os Parquets mensais...")
                source_list = _duckdb_path_list(source_paths)
                connection.execute(
                    f"""
                    CREATE OR REPLACE TEMP VIEW oms_source AS
                    SELECT
                        * EXCLUDE (filename),
                        REGEXP_EXTRACT(filename, 'agrupamento_oms_([0-9]{{6}})\\.parquet', 1)
                            AS ANOMES_PROCESSAMENTO
                    FROM read_parquet({source_list}, union_by_name = true, filename = true)
                    """
                )
                self._log(
                    run_id=run_id,
                    etapa="criar_view_origem",
                    status="sucesso",
                    mensagem="View DuckDB criada com sucesso.",
                    arquivos_origem=len(source_paths),
                )

                self._log(
                    run_id=run_id,
                    etapa="validar_colunas",
                    status="processando",
                    mensagem="Validando colunas obrigatórias.",
                    arquivos_origem=len(source_paths),
                )
                self._print("[OMS_union] Validando colunas obrigatórias...")
                self._validate_required_columns(connection)
                self._log(
                    run_id=run_id,
                    etapa="validar_colunas",
                    status="sucesso",
                    mensagem="Colunas obrigatórias presentes.",
                    arquivos_origem=len(source_paths),
                )

                self._log(
                    run_id=run_id,
                    etapa="contar_origem",
                    status="processando",
                    mensagem="Contando linhas de origem.",
                    arquivos_origem=len(source_paths),
                )
                self._print("[OMS_union] Contando linhas de origem...")
                linhas_origem = self._count_rows(connection, "oms_source")
                self._log(
                    run_id=run_id,
                    etapa="contar_origem",
                    status="sucesso",
                    mensagem=f"Linhas de origem: {linhas_origem}.",
                    arquivos_origem=len(source_paths),
                    linhas_origem=linhas_origem,
                )

                self._log(
                    run_id=run_id,
                    etapa="gravar_parquet",
                    status="processando",
                    mensagem="Deduplicando, criando colunas derivadas e gravando Parquet temporário.",
                    arquivos_origem=len(source_paths),
                    linhas_origem=linhas_origem,
                )
                self._print(
                    "[OMS_union] Deduplicando e gravando Parquet temporário..."
                )
                self._write_union(connection, temp_path)
                self._log(
                    run_id=run_id,
                    etapa="gravar_parquet",
                    status="sucesso",
                    mensagem=f"Parquet temporário gravado em {temp_path}.",
                    arquivos_origem=len(source_paths),
                    linhas_origem=linhas_origem,
                    parquet_path=str(temp_path),
                )

                self._log(
                    run_id=run_id,
                    etapa="contar_saida",
                    status="processando",
                    mensagem="Contando linhas do Parquet final temporário.",
                    arquivos_origem=len(source_paths),
                    linhas_origem=linhas_origem,
                )
                self._print("[OMS_union] Contando linhas de saída...")
                linhas_saida = self._count_parquet_rows(connection, temp_path)
                self._log(
                    run_id=run_id,
                    etapa="contar_saida",
                    status="sucesso",
                    mensagem=f"Linhas de saída: {linhas_saida}.",
                    arquivos_origem=len(source_paths),
                    linhas_origem=linhas_origem,
                    linhas_saida=linhas_saida,
                )
            finally:
                connection.close()

            self._log(
                run_id=run_id,
                etapa="publicar_parquet",
                status="processando",
                mensagem=f"Publicando Parquet final em {self.output_path}.",
                arquivos_origem=len(source_paths),
                linhas_origem=linhas_origem,
                linhas_saida=linhas_saida,
            )
            self._print("[OMS_union] Publicando Parquet final...")
            os.replace(temp_path, self.output_path)

            self._log(
                run_id=run_id,
                etapa="fim",
                status="sucesso",
                mensagem="Mart OMS_union gerado com sucesso.",
                arquivos_origem=len(source_paths),
                linhas_origem=linhas_origem,
                linhas_saida=linhas_saida,
                parquet_path=str(self.output_path),
            )

            return OmsUnionResult(
                arquivos_origem=len(source_paths),
                linhas_origem=linhas_origem,
                linhas_saida=linhas_saida,
                parquet_path=self.output_path,
            )
        except Exception as exc:
            self._log(
                run_id=run_id,
                etapa="erro",
                status="erro",
                mensagem=str(exc),
                arquivos_origem=len(source_paths) if source_paths else None,
                linhas_origem=linhas_origem or None,
                linhas_saida=linhas_saida or None,
                parquet_path=str(self.output_path),
            )
            self._print(f"[OMS_union] ERRO | {exc}")
            raise

    def _source_paths(self) -> list[Path]:
        return sorted(self.processed_dir.glob("agrupamento_oms_*.parquet"))

    def _log(
        self,
        run_id: str,
        etapa: str,
        status: str,
        mensagem: str,
        arquivos_origem: int | None = None,
        linhas_origem: int | None = None,
        linhas_saida: int | None = None,
        parquet_path: str | None = None,
    ) -> None:
        self._print(f"[OMS_union] {etapa} | {status} | {mensagem}")
        record = LogOmsUnion(
            run_id=run_id,
            etapa=etapa,
            status=status,  # type: ignore[arg-type]
            mensagem=mensagem,
            arquivos_origem=arquivos_origem,
            linhas_origem=linhas_origem,
            linhas_saida=linhas_saida,
            parquet_path=parquet_path,
            criado_em=datetime.now(),
        )
        self.log_repository.append([record.to_record()])

    @staticmethod
    def _print(message: str) -> None:
        print(message, flush=True)

    def _validate_required_columns(self, connection: duckdb.DuckDBPyConnection) -> None:
        available_columns = {
            row[0]
            for row in connection.execute("DESCRIBE oms_source").fetchall()
        }
        required_columns = set(DEDUP_KEY_COLUMNS) | {
            "DATA_HORA_INIC_INTRP",
            "DATA_HORA_FIM_INTRP",
        }
        missing_columns = sorted(required_columns - available_columns)
        if missing_columns:
            raise ValueError(
                "Colunas obrigatórias ausentes para união OMS: "
                + ", ".join(missing_columns)
            )

    def _write_union(
        self,
        connection: duckdb.DuckDBPyConnection,
        output_path: Path,
    ) -> None:
        partition_columns = ", ".join(DEDUP_KEY_COLUMNS)
        output = _duckdb_string(output_path)

        connection.execute(
            f"""
            COPY (
                WITH typed AS (
                    SELECT
                        *,
                        COALESCE(
                            TRY_STRPTIME(DATA_HORA_INIC_INTRP, '%d/%m/%Y %H:%M:%S'),
                            TRY_STRPTIME(DATA_HORA_INIC_INTRP, '%Y-%m-%d %H:%M:%S')
                        ) AS __inicio_ts,
                        COALESCE(
                            TRY_STRPTIME(DATA_HORA_FIM_INTRP, '%d/%m/%Y %H:%M:%S'),
                            TRY_STRPTIME(DATA_HORA_FIM_INTRP, '%Y-%m-%d %H:%M:%S')
                        ) AS __fim_ts
                    FROM oms_source
                ),
                enriched AS (
                    SELECT
                        *,
                        CASE
                            WHEN __inicio_ts IS NULL OR __fim_ts IS NULL THEN NULL
                            ELSE DATE_DIFF('second', __inicio_ts, __fim_ts) / 60.0
                        END AS duracao
                    FROM typed
                ),
                ranked AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY {partition_columns}
                            ORDER BY DATA_HORA_INIC_INTRP, DATA_HORA_FIM_INTRP
                        ) AS __rn
                    FROM enriched
                )
                SELECT
                    * EXCLUDE (__inicio_ts, __fim_ts, __rn),
                    COALESCE(duracao < 0, false) AS erro_duracao,
                    COALESCE(duracao >= 3, false) AS duracao_longa
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

    @staticmethod
    def _count_rows(connection: duckdb.DuckDBPyConnection, table_name: str) -> int:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])

    @staticmethod
    def _count_parquet_rows(
        connection: duckdb.DuckDBPyConnection,
        parquet_path: Path,
    ) -> int:
        path = _duckdb_string(parquet_path)
        return int(
            connection.execute(f"SELECT COUNT(*) FROM read_parquet({path})").fetchone()[0]
        )


def _duckdb_path_list(paths: list[Path]) -> str:
    return "[" + ", ".join(_duckdb_string(path) for path in paths) + "]"


def _duckdb_string(path: Path) -> str:
    value = str(path).replace("'", "''")
    return f"'{value}'"
