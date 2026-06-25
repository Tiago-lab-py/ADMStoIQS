from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
FECHAMENTO_INPUT_DIR = DATA_DIR / "input" / "fechamento"
FECHAMENTO_PROCESSED_DIR = DATA_DIR / "processed" / "fechamento"
RAW_TEMP_DIR = DATA_DIR / "raw_temp"

REGIONAIS = {"CSL", "LES", "NRO", "NRT", "OES"}


@dataclass(frozen=True)
class FechamentoRegionalResumo:
    regional: str
    arquivo: str
    linhas: int


@dataclass(frozen=True)
class FechamentoMensalResult:
    anomes: str
    entrada: Path
    arquivos_encontrados: int
    linhas_lidas: int
    linhas_saida: int
    parquet: Path
    parquet_atual: Path
    regionais: list[FechamentoRegionalResumo]


def _sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("\\", "/").replace("'", "''") + "'"


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _regional_from_name(path: Path) -> str:
    stem = path.stem.upper()
    regional = stem.rsplit("_", 1)[-1] if "_" in stem else ""
    return regional if regional in REGIONAIS else "SEM_REGIONAL"


def _list_csv_files(input_dir: Path) -> list[Path]:
    files = [*input_dir.glob("*.CSV"), *input_dir.glob("*.csv")]
    return sorted({file.resolve() for file in files})


def _duckdb_file_list(files: Iterable[Path]) -> str:
    return "[" + ", ".join(_sql_literal(file) for file in files) + "]"


class FechamentoMensalService:
    """Processa os CSVs consolidados de fechamento mensal em trilha isolada.

    O fechamento mensal usa a pasta `data/input/fechamento/{anomes}` como
    delimitador da competência. O timestamp no nome do arquivo pode ser de outro
    mês, pois normalmente os consolidados são gerados após o encerramento.
    """

    def processar(self, anomes: str, input_dir: str | Path | None = None) -> FechamentoMensalResult:
        entrada = Path(input_dir) if input_dir else FECHAMENTO_INPUT_DIR / anomes
        entrada = entrada.resolve()

        if not entrada.exists():
            raise FileNotFoundError(f"Pasta de fechamento não encontrada: {entrada}")

        csv_files = _list_csv_files(entrada)
        if not csv_files:
            raise FileNotFoundError(
                f"Nenhum CSV de fechamento encontrado em {entrada}. "
                "Copie os consolidados regionais para essa pasta."
            )

        FECHAMENTO_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        RAW_TEMP_DIR.mkdir(parents=True, exist_ok=True)

        destino = FECHAMENTO_PROCESSED_DIR / f"agrupamento_oms_FECHAMENTO_{anomes}.parquet"
        destino_atual = FECHAMENTO_PROCESSED_DIR / "agrupamento_oms_FECHAMENTO_ATUAL.parquet"
        tmp = RAW_TEMP_DIR / f"agrupamento_oms_FECHAMENTO_{anomes}.tmp.parquet"

        file_list_sql = _duckdb_file_list(csv_files)

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                f"""
                CREATE OR REPLACE TEMP VIEW fechamento_raw AS
                SELECT *
                FROM read_csv_auto(
                    {file_list_sql},
                    delim='|',
                    header=true,
                    all_varchar=true,
                    filename=true,
                    ignore_errors=false
                )
                """
            )

            columns = [row[0] for row in connection.execute("DESCRIBE fechamento_raw").fetchall()]
            select_exprs = self._build_select_exprs(columns, anomes)
            partition_expr = self._build_partition_expr(columns)

            connection.execute(
                f"""
                COPY (
                    WITH enriched AS (
                        SELECT
                            {", ".join(select_exprs)}
                        FROM fechamento_raw
                    )
                    SELECT *
                    FROM enriched
                    QUALIFY ROW_NUMBER() OVER (
                        PARTITION BY {partition_expr}
                        ORDER BY arquivo_origem
                    ) = 1
                )
                TO {_sql_literal(tmp)}
                (FORMAT PARQUET)
                """
            )

            linhas_lidas = int(connection.execute("SELECT COUNT(*) FROM fechamento_raw").fetchone()[0])
            linhas_saida = int(
                connection.execute(
                    "SELECT COUNT(*) FROM read_parquet(?)",
                    [str(tmp)],
                ).fetchone()[0]
            )

            regionais_rows = connection.execute(
                """
                SELECT
                    REGIONAL_ORIGEM,
                    COUNT(*) AS linhas
                FROM read_parquet(?)
                GROUP BY REGIONAL_ORIGEM
                ORDER BY REGIONAL_ORIGEM
                """,
                [str(tmp)],
            ).fetchall()

            connection.execute(
                f"COPY (SELECT * FROM read_parquet({_sql_literal(tmp)})) TO {_sql_literal(destino)} (FORMAT PARQUET)"
            )
            connection.execute(
                f"COPY (SELECT * FROM read_parquet({_sql_literal(tmp)})) TO {_sql_literal(destino_atual)} (FORMAT PARQUET)"
            )

        tmp.unlink(missing_ok=True)

        regionais = [
            FechamentoRegionalResumo(
                regional=str(regional),
                arquivo=self._arquivo_regional(csv_files, str(regional)),
                linhas=int(linhas),
            )
            for regional, linhas in regionais_rows
        ]

        return FechamentoMensalResult(
            anomes=anomes,
            entrada=entrada,
            arquivos_encontrados=len(csv_files),
            linhas_lidas=linhas_lidas,
            linhas_saida=linhas_saida,
            parquet=destino,
            parquet_atual=destino_atual,
            regionais=regionais,
        )

    def _build_select_exprs(self, columns: list[str], anomes: str) -> list[str]:
        ignored = {
            "ANOMES_PROCESSAMENTO",
            "REGIONAL_ORIGEM",
            "arquivo_origem",
            "duracao_minutos",
            "erro_duracao",
            "duracao_longa",
        }
        expressions = [
            f"{_quote_identifier(column)} AS {_quote_identifier(column)}"
            for column in columns
            if column not in ignored
        ]

        expressions.extend(
            [
                f"{_sql_literal(anomes)} AS ANOMES_PROCESSAMENTO",
                """
                CASE
                    WHEN UPPER(regexp_extract(filename, '_([A-Z]{3})\\.CSV$', 1)) IN ('CSL','LES','NRO','NRT','OES')
                    THEN UPPER(regexp_extract(filename, '_([A-Z]{3})\\.CSV$', 1))
                    ELSE 'SEM_REGIONAL'
                END AS REGIONAL_ORIGEM
                """,
                "filename AS arquivo_origem",
            ]
        )

        if {"DATA_HORA_INIC_INTRP", "DATA_HORA_FIM_INTRP"}.issubset(columns):
            inicio = self._timestamp_expr("DATA_HORA_INIC_INTRP")
            fim = self._timestamp_expr("DATA_HORA_FIM_INTRP")
            expressions.extend(
                [
                    f"date_diff('minute', {inicio}, {fim}) AS duracao_minutos",
                    f"date_diff('minute', {inicio}, {fim}) < 0 AS erro_duracao",
                    f"date_diff('minute', {inicio}, {fim}) >= 3 AS duracao_longa",
                ]
            )
        else:
            expressions.extend(
                [
                    "NULL::BIGINT AS duracao_minutos",
                    "false AS erro_duracao",
                    "false AS duracao_longa",
                ]
            )

        return expressions

    def _timestamp_expr(self, column: str) -> str:
        quoted = _quote_identifier(column)
        return (
            f"COALESCE("
            f"try_strptime({quoted}, '%d/%m/%Y %H:%M:%S'), "
            f"try_strptime({quoted}, '%Y-%m-%d %H:%M:%S'), "
            f"try_strptime({quoted}, '%d/%m/%Y %H:%M'), "
            f"try_strptime({quoted}, '%Y-%m-%d %H:%M')"
            f")"
        )

    def _build_partition_expr(self, columns: list[str]) -> str:
        keys = [column for column in ["NUM_INTRP_UCI", "NUM_POSTO_UCI", "NUM_UC_UCI"] if column in columns]
        if keys:
            return " || '|' || ".join(f"COALESCE({_quote_identifier(key)}, '')" for key in keys)
        return "row_number() OVER ()"

    def _arquivo_regional(self, files: list[Path], regional: str) -> str:
        for file in files:
            if _regional_from_name(file) == regional:
                return str(file)
        return ""
