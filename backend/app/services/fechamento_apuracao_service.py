from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FECHAMENTO_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "fechamento"
FECHAMENTO_APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao" / "fechamento"
RAW_TEMP_DIR = PROJECT_ROOT / "data" / "raw_temp"


@dataclass(frozen=True)
class FechamentoApuracaoResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    linhas_origem: int
    linhas_apuracao: int


class FechamentoApuracaoService:
    def gerar(self, anomes: str) -> FechamentoApuracaoResult:
        origem = FECHAMENTO_PROCESSED_DIR / f"agrupamento_oms_FECHAMENTO_{anomes}.parquet"
        if not origem.exists():
            raise FileNotFoundError(
                f"Parquet de fechamento não encontrado: {origem}. "
                "Rode primeiro python -m backend.scripts.processar_fechamento_mensal."
            )

        FECHAMENTO_APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        RAW_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        destino = FECHAMENTO_APURACAO_DIR / f"agrupamento_oms_FECHAMENTO_APURACAO_{anomes}.parquet"
        destino_atual = FECHAMENTO_APURACAO_DIR / "agrupamento_oms_FECHAMENTO_APURACAO_ATUAL.parquet"
        temp_path = RAW_TEMP_DIR / f"{destino.stem}.tmp.parquet"

        inicio_mes = datetime.strptime(anomes + "01", "%Y%m%d").date()
        if inicio_mes.month == 12:
            proximo_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            proximo_mes = inicio_mes.replace(month=inicio_mes.month + 1)

        with duckdb.connect(database=":memory:") as connection:
            colunas = _colunas_parquet(connection, origem)
            select_base = _select_com_timestamps(colunas)
            connection.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW fechamento_base AS
                SELECT
                    {select_base}
                FROM read_parquet({_sql_literal(origem)})
                """
            )

            linhas_origem = int(connection.execute("SELECT COUNT(*) FROM fechamento_base").fetchone()[0])
            if temp_path.exists():
                temp_path.unlink()

            connection.execute(
                f"""
                COPY (
                    SELECT *
                    FROM fechamento_base
                    WHERE DATA_HORA_INIC_INTRP_TS >= {_sql_literal(str(inicio_mes))}::TIMESTAMP
                      AND DATA_HORA_FIM_INTRP_TS < {_sql_literal(str(proximo_mes))}::TIMESTAMP
                )
                TO {_sql_literal(temp_path)} (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """
            )
            linhas_apuracao = int(
                connection.execute(
                    "SELECT COUNT(*) FROM read_parquet(?)",
                    [str(temp_path)],
                ).fetchone()[0]
            )

        os.replace(temp_path, destino)
        _copiar_parquet(destino, destino_atual)

        return FechamentoApuracaoResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=destino_atual,
            linhas_origem=linhas_origem,
            linhas_apuracao=linhas_apuracao,
        )


def _select_com_timestamps(colunas: list[str]) -> str:
    partes = [_quote_identifier(coluna) for coluna in colunas]
    if "DATA_HORA_INIC_INTRP_TS" not in colunas:
        partes.append(f"{_timestamp_expr('DATA_HORA_INIC_INTRP')} AS DATA_HORA_INIC_INTRP_TS")
    if "DATA_HORA_FIM_INTRP_TS" not in colunas:
        partes.append(f"{_timestamp_expr('DATA_HORA_FIM_INTRP')} AS DATA_HORA_FIM_INTRP_TS")
    if "DTHR_INICIO_INTRP_UC_TS" not in colunas and "DTHR_INICIO_INTRP_UC" in colunas:
        partes.append(f"{_timestamp_expr('DTHR_INICIO_INTRP_UC')} AS DTHR_INICIO_INTRP_UC_TS")
    return ",\n                    ".join(partes)


def _timestamp_expr(coluna: str) -> str:
    quoted = _quote_identifier(coluna)
    return f"""
        COALESCE(
            TRY_STRPTIME(NULLIF(CAST({quoted} AS VARCHAR), ''), '%d/%m/%Y %H:%M:%S'),
            TRY_STRPTIME(NULLIF(CAST({quoted} AS VARCHAR), ''), '%Y-%m-%d %H:%M:%S'),
            TRY_CAST(NULLIF(CAST({quoted} AS VARCHAR), '') AS TIMESTAMP)
        )
    """.strip()


def _colunas_parquet(connection: duckdb.DuckDBPyConnection, parquet: Path) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(parquet)})",
        ).fetchall()
    ]


def _copiar_parquet(origem: Path, destino: Path) -> None:
    with duckdb.connect(database=":memory:") as connection:
        connection.execute(
            f"COPY (SELECT * FROM read_parquet({_sql_literal(origem)})) TO {_sql_literal(destino)} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("\\", "/").replace("'", "''") + "'"
