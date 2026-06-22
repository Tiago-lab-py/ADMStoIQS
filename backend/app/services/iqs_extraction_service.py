from __future__ import annotations

import calendar
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import duckdb

from backend.app.core.iqs_settings import get_iqs_settings
from backend.app.services.iqs_connection_service import IqsConnectionService


ROOT_DIR = Path(__file__).resolve().parents[3]
SQL_DIR = ROOT_DIR / "backend" / "app" / "sql" / "iqs"
IQS_RAW_DIR = ROOT_DIR / "data" / "external" / "iqs" / "raw"
IQS_TMP_DIR = ROOT_DIR / "data" / "external" / "iqs" / "tmp"
LOGS_DIR = ROOT_DIR / "data" / "logs"
LOG_EXTRACAO_IQS = LOGS_DIR / "log_extracao_iqs.parquet"


@dataclass(frozen=True)
class IqsExtractionResult:
    anomes: str
    consulta_nome: str
    arquivo_saida: Path
    linhas_extraidas: int
    status: str
    erro: str
    duracao_segundos: float


def build_iqs_binds(anomes: str) -> dict[str, Any]:
    ano = int(anomes[:4])
    mes = int(anomes[4:6])
    ano_txt = str(ano)
    mes_txt = f"{mes:02d}"
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_inicio = date(ano, mes, 1)
    data_fim = date(ano, mes, ultimo_dia)

    return {
        "anomes": anomes,
        "ANOMES": anomes,
        "p_yyyymm": anomes,
        "P_YYYYMM": anomes,
        "p_anomes": anomes,
        "P_ANOMES": anomes,
        "ano": ano,
        "ANO": ano,
        "ano_txt": ano_txt,
        "ANO_TXT": ano_txt,
        "yyyy": ano_txt,
        "YYYY": ano_txt,
        "p_yyyy": ano_txt,
        "P_YYYY": ano_txt,
        "p_ano": ano,
        "P_ANO": ano,
        "p_ano_txt": ano_txt,
        "P_ANO_TXT": ano_txt,
        "mes": mes,
        "MES": mes,
        "mes_txt": mes_txt,
        "MES_TXT": mes_txt,
        "mm": mes_txt,
        "MM": mes_txt,
        "p_mm": mes_txt,
        "P_MM": mes_txt,
        "p_mes": mes,
        "P_MES": mes,
        "p_mes_txt": mes_txt,
        "P_MES_TXT": mes_txt,
        "p_mes_2d": mes_txt,
        "P_MES_2D": mes_txt,
        "data_inicio": data_inicio,
        "DATA_INICIO": data_inicio,
        "p_data_inicio": data_inicio,
        "P_DATA_INICIO": data_inicio,
        "data_fim": data_fim,
        "DATA_FIM": data_fim,
        "p_data_fim": data_fim,
        "P_DATA_FIM": data_fim,
        "dt_inicio": data_inicio,
        "DT_INICIO": data_inicio,
        "p_dt_inicio": data_inicio,
        "P_DT_INICIO": data_inicio,
        "dt_fim": data_fim,
        "DT_FIM": data_fim,
        "p_dt_fim": data_fim,
        "P_DT_FIM": data_fim,
    }


def filter_binds_for_sql(sql: str, binds: dict[str, Any]) -> dict[str, Any]:
    sql_to_scan = re.sub(r"'([^']|'')*'", "''", sql)
    sql_to_scan = re.sub(r"--.*?$", "", sql_to_scan, flags=re.MULTILINE)
    sql_to_scan = re.sub(r"/\*.*?\*/", "", sql_to_scan, flags=re.DOTALL)
    placeholders = {
        match.group(1)
        for match in re.finditer(r":([A-Za-z_][A-Za-z0-9_]*)", sql_to_scan)
    }
    if not placeholders:
        return {}
    return {key: value for key, value in binds.items() if key in placeholders}


def normalize_oracle_sql(sql: str) -> str:
    cleaned_lines: list[str] = []
    skip_prefixes = (
        "SET ",
        "SPOOL ",
        "PROMPT ",
        "WHENEVER ",
        "COLUMN ",
        "DEFINE ",
        "UNDEFINE ",
        "ALTER SESSION SET CURRENT_SCHEMA",
    )

    for raw_line in sql.replace("\ufeff", "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        upper = stripped.upper()

        if not stripped:
            cleaned_lines.append(line)
            continue

        if stripped == "/":
            continue

        if any(upper.startswith(prefix) for prefix in skip_prefixes):
            continue

        cleaned_lines.append(line)

    normalized = "\n".join(cleaned_lines).strip()

    while normalized.endswith(";") or normalized.endswith("/"):
        normalized = normalized[:-1].rstrip()

    return normalized


class IqsExtractionService:
    def __init__(self, connection_service: IqsConnectionService | None = None) -> None:
        self.connection_service = connection_service or IqsConnectionService()
        self.settings = get_iqs_settings()

    def extract_sql_file(
        self,
        *,
        anomes: str,
        consulta_nome: str,
        sql_path: Path,
        output_path: Path | None = None,
        arraysize: int = 10000,
        extra_binds: dict[str, Any] | None = None,
    ) -> IqsExtractionResult:
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL não encontrado: {sql_path}")

        sql = normalize_oracle_sql(sql_path.read_text(encoding="utf-8"))
        return self.extract_sql(
            anomes=anomes,
            consulta_nome=consulta_nome,
            sql=sql,
            sql_path=sql_path,
            output_path=output_path,
            arraysize=arraysize,
            extra_binds=extra_binds,
        )

    def extract_sql(
        self,
        *,
        anomes: str,
        consulta_nome: str,
        sql: str,
        sql_path: Path | None = None,
        output_path: Path | None = None,
        arraysize: int = 10000,
        extra_binds: dict[str, Any] | None = None,
    ) -> IqsExtractionResult:
        started = perf_counter()
        IQS_RAW_DIR.mkdir(parents=True, exist_ok=True)
        IQS_TMP_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        output_path = output_path or IQS_RAW_DIR / f"{consulta_nome}_{anomes}.parquet"
        tmp_db = IQS_TMP_DIR / f"{consulta_nome}_{anomes}_{datetime.now().strftime('%Y%m%d%H%M%S')}.duckdb"
        status = "processado"
        erro = ""
        linhas = 0

        try:
            sql = normalize_oracle_sql(sql)
            all_binds = build_iqs_binds(anomes)
            if extra_binds:
                all_binds.update(extra_binds)
            binds = filter_binds_for_sql(sql, all_binds)
            with duckdb.connect(database=str(tmp_db)) as duck_connection:
                with self.connection_service.connect() as oracle_connection:
                    with oracle_connection.cursor() as cursor:
                        cursor.arraysize = arraysize
                        if binds:
                            cursor.execute(sql, binds)
                        else:
                            cursor.execute(sql)
                        columns = [description[0] for description in cursor.description]
                        safe_columns = [self._safe_column(column, index) for index, column in enumerate(columns)]

                        self._create_duck_table(duck_connection, safe_columns)

                        while True:
                            batch = cursor.fetchmany(arraysize)
                            if not batch:
                                break

                            self._insert_batch(duck_connection, safe_columns, batch)
                            linhas += len(batch)
                            print(f"[IQS] {consulta_nome}: {linhas} linha(s) extraída(s)...")

                output_path.parent.mkdir(parents=True, exist_ok=True)
                duck_connection.execute("COPY extracted TO ? (FORMAT PARQUET)", [str(output_path)])

        except Exception as exc:
            status = "erro"
            erro = f"{type(exc).__name__}: {exc}"
            print(f"[IQS] ERRO na consulta {consulta_nome}: {erro}")
            if sql_path:
                print(f"[IQS] SQL origem: {sql_path}")
            raise
        finally:
            duracao = perf_counter() - started
            self._append_log(
                {
                    "anomes": anomes,
                    "fonte": "IQS",
                    "consulta_nome": consulta_nome,
                    "sql_path": str(sql_path or ""),
                    "arquivo_saida": str(output_path),
                    "linhas_extraidas": linhas,
                    "executado_em": datetime.now().isoformat(timespec="seconds"),
                    "status": status,
                    "erro": erro,
                    "duracao_segundos": round(duracao, 3),
                    "usuario_iqs": self.settings.uid,
                    "database_iqs": self.settings.db,
                }
            )
            if tmp_db.exists():
                try:
                    tmp_db.unlink()
                except Exception:
                    shutil.rmtree(tmp_db, ignore_errors=True)

        return IqsExtractionResult(
            anomes=anomes,
            consulta_nome=consulta_nome,
            arquivo_saida=output_path,
            linhas_extraidas=linhas,
            status=status,
            erro=erro,
            duracao_segundos=round(perf_counter() - started, 3),
        )

    def _create_duck_table(self, connection: duckdb.DuckDBPyConnection, columns: list[str]) -> None:
        if not columns:
            connection.execute("CREATE TABLE extracted (AVISO VARCHAR)")
            return

        column_defs = ", ".join([f'"{column}" VARCHAR' for column in columns])
        connection.execute(f"CREATE TABLE extracted ({column_defs})")

    def _insert_batch(
        self,
        connection: duckdb.DuckDBPyConnection,
        columns: list[str],
        rows: list[tuple[Any, ...]],
    ) -> None:
        if not rows:
            return

        placeholders = ", ".join(["?"] * len(columns))
        connection.executemany(
            f"INSERT INTO extracted VALUES ({placeholders})",
            [[None if value is None else str(value) for value in row] for row in rows],
        )

    def _append_log(self, record: dict[str, Any]) -> None:
        select_values = []
        for key, value in record.items():
            escaped = str(value).replace("'", "''")
            select_values.append(f"'{escaped}' AS {key}")
        values = ", ".join(select_values)

        temp_log = LOG_EXTRACAO_IQS.with_suffix(".tmp.parquet")

        with duckdb.connect(database=":memory:") as connection:
            if LOG_EXTRACAO_IQS.exists():
                connection.execute(
                    "CREATE TEMP TABLE log_atual AS SELECT * FROM read_parquet(?)",
                    [str(LOG_EXTRACAO_IQS)],
                )
                connection.execute(f"CREATE TEMP TABLE log_novo AS SELECT {values}")
                connection.execute(
                    """
                    COPY (
                        SELECT * FROM log_atual
                        UNION ALL
                        SELECT * FROM log_novo
                    ) TO ? (FORMAT PARQUET)
                    """,
                    [str(temp_log)],
                )
                temp_log.replace(LOG_EXTRACAO_IQS)
            else:
                connection.execute(
                    f"COPY (SELECT {values}) TO ? (FORMAT PARQUET)",
                    [str(LOG_EXTRACAO_IQS)],
                )

    def _safe_column(self, column: str, index: int) -> str:
        value = str(column or "").strip().upper()
        if not value:
            value = f"COLUNA_{index + 1}"
        return value.replace('"', "")
