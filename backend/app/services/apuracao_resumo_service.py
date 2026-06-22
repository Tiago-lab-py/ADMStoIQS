from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

try:
    from backend.app.core.contracts import MART_DIR
except Exception:
    MART_DIR = Path(__file__).resolve().parents[3] / "data" / "mart"


APURACAO_DIR = MART_DIR / "apuracao"
APURACAO_ATUAL_PATH = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"
RESUMO_APURACAO_ATUAL_PATH = APURACAO_DIR / "resumo_APURACAO_ATUAL.parquet"


def _timestamp_expr(column: str) -> str:
    return f"""
        COALESCE(
            TRY_CAST({column} AS TIMESTAMP),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%d/%m/%Y %H:%M:%S')
        )
    """


def _num_seq_expr() -> str:
    return """
        COALESCE(
            NULLIF(TRIM(CAST(NUM_SEQ_INTRP AS VARCHAR)), ''),
            NULLIF(TRIM(CAST(PID_INTRP_CONJTO_PIN AS VARCHAR)), ''),
            NULLIF(TRIM(CAST(NUM_INTRP_UCI AS VARCHAR)), '')
        )
    """


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


@dataclass(frozen=True)
class ResumoApuracaoResult:
    anomes: str
    total_registros: int
    pendencias_totais: int
    horario_negativo: int
    sobreposicao_interrupcao: int
    sobreposicao_uc: int
    sem_causa_componente: int
    rejeitados: int
    validado: int
    parquet: Path
    parquet_atual: Path


class ApuracaoResumoService:
    def materializar(self, anomes: str | None = None, origem: Path | None = None) -> ResumoApuracaoResult:
        APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        origem = origem or APURACAO_ATUAL_PATH
        if not origem.exists():
            raise FileNotFoundError(f"Parquet de apuração não encontrado: {origem}")

        anomes_detectado = anomes or self._detectar_anomes(origem)
        destino = APURACAO_DIR / f"resumo_APURACAO_{anomes_detectado}.parquet"

        with duckdb.connect(database=":memory:") as connection:
            total = self._count_total(connection, origem)
            horario = self._count_horario_negativo(connection, origem)
            sobreposicao = self._count_sobreposicao_equipamento(connection, origem)
            sobreposicao_uc = self._count_sobreposicao_uc(connection, origem)
            sem_causa = self._count_sem_causa_componente(connection, origem)
            rejeitados = self._count_status(connection, origem, "rejeitado")
            validado = self._count_status(connection, origem, "validado")
            rejeitados_por_atividade = self._rejeitados_por_atividade(connection, origem)

            pendencias = max(total - rejeitados - validado, 0)
            self._write_single_row_parquet(
                connection,
                destino,
                {
                    "anomes": anomes_detectado,
                    "gerado_em": datetime.now().isoformat(timespec="seconds"),
                    "fonte": str(origem),
                    "total_registros": total,
                    "pendencias_totais": pendencias,
                    "horario_negativo": horario,
                    "sobreposicao_interrupcao": sobreposicao,
                    "sobreposicao_uc": sobreposicao_uc,
                    "sem_causa_componente": sem_causa,
                    "rejeitados": rejeitados,
                    "validado": validado,
                    "rejeitados_por_atividade_json": json.dumps(rejeitados_por_atividade, ensure_ascii=False),
                },
            )

        shutil.copy2(destino, RESUMO_APURACAO_ATUAL_PATH)
        return ResumoApuracaoResult(
            anomes=anomes_detectado,
            total_registros=total,
            pendencias_totais=pendencias,
            horario_negativo=horario,
            sobreposicao_interrupcao=sobreposicao,
            sobreposicao_uc=sobreposicao_uc,
            sem_causa_componente=sem_causa,
            rejeitados=rejeitados,
            validado=validado,
            parquet=destino,
            parquet_atual=RESUMO_APURACAO_ATUAL_PATH,
        )

    def ler_atual(self) -> dict[str, Any] | None:
        if not RESUMO_APURACAO_ATUAL_PATH.exists():
            return None

        with duckdb.connect(database=":memory:") as connection:
            result = connection.execute(
                "SELECT * FROM read_parquet(?) LIMIT 1",
                [str(RESUMO_APURACAO_ATUAL_PATH)],
            )
            columns = [column[0] for column in result.description]
            row = result.fetchone()

        if not row:
            return None

        resumo = dict(zip(columns, row))
        raw_rejeitados = resumo.pop("rejeitados_por_atividade_json", None)
        try:
            resumo["rejeitados_por_atividade"] = json.loads(raw_rejeitados or "{}")
        except Exception:
            resumo["rejeitados_por_atividade"] = {}

        resumo["pendentes"] = resumo.get("pendencias_totais", 0)
        resumo["sobreposicoes"] = resumo.get("sobreposicao_interrupcao", 0)
        return resumo

    def _detectar_anomes(self, path: Path) -> str:
        with duckdb.connect(database=":memory:") as connection:
            try:
                value = connection.execute(
                    """
                    SELECT max(CAST(ANOMES_PROCESSAMENTO AS VARCHAR))
                    FROM read_parquet(?)
                    WHERE ANOMES_PROCESSAMENTO IS NOT NULL
                    """,
                    [str(path)],
                ).fetchone()[0]
                if value:
                    return str(value)
            except Exception:
                pass
        return "ATUAL"

    def _count_total(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        return int(connection.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0] or 0)

    def _count_horario_negativo(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()
        query = f"""
            WITH base AS (
                SELECT
                    {inicio} AS inicio,
                    {fim} AS fim,
                    {num_seq} AS num_seq
                FROM read_parquet(?)
            )
            SELECT count(DISTINCT num_seq)
            FROM base
            WHERE inicio IS NOT NULL
              AND fim IS NOT NULL
              AND fim < inicio
              AND num_seq IS NOT NULL
        """
        return int(connection.execute(query, [str(path)]).fetchone()[0] or 0)

    def _count_sobreposicao_equipamento(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()
        query = f"""
            WITH base AS (
                SELECT
                    NUM_OPER_CHV_INTRP,
                    {num_seq} AS num_seq,
                    {inicio} AS inicio,
                    {fim} AS fim
                FROM read_parquet(?)
                WHERE NULLIF(TRIM(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)), '') IS NOT NULL
            ),
            intrp AS (
                SELECT NUM_OPER_CHV_INTRP, num_seq, min(inicio) AS inicio, max(fim) AS fim
                FROM base
                WHERE inicio IS NOT NULL AND fim IS NOT NULL AND num_seq IS NOT NULL
                GROUP BY NUM_OPER_CHV_INTRP, num_seq
            ),
            marcadas AS (
                SELECT DISTINCT a.num_seq
                FROM intrp a
                JOIN intrp b
                  ON a.NUM_OPER_CHV_INTRP = b.NUM_OPER_CHV_INTRP
                 AND a.num_seq <> b.num_seq
                 AND a.inicio < b.fim
                 AND b.inicio < a.fim
            )
            SELECT count(*) FROM marcadas
        """
        return int(connection.execute(query, [str(path)]).fetchone()[0] or 0)

    def _count_sobreposicao_uc(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        return 0

    def _count_sem_causa_componente(self, connection: duckdb.DuckDBPyConnection, path: Path) -> int:
        try:
            return int(
                connection.execute(
                    """
                    SELECT count(*)
                    FROM read_parquet(?)
                    WHERE NULLIF(TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)), '') IS NULL
                       OR NULLIF(TRIM(CAST(COD_COMP_INTRP AS VARCHAR)), '') IS NULL
                    """,
                    [str(path)],
                ).fetchone()[0]
                or 0
            )
        except Exception:
            return 0

    def _count_status(self, connection: duckdb.DuckDBPyConnection, path: Path, status: str) -> int:
        try:
            return int(
                connection.execute(
                    """
                    SELECT count(*)
                    FROM read_parquet(?)
                    WHERE lower(trim(CAST(status_validacao AS VARCHAR))) = lower(?)
                       OR lower(trim(CAST(STATUS_VALIDACAO AS VARCHAR))) = lower(?)
                    """,
                    [str(path), status, status],
                ).fetchone()[0]
                or 0
            )
        except Exception:
            return 0

    def _rejeitados_por_atividade(self, connection: duckdb.DuckDBPyConnection, path: Path) -> dict[str, int]:
        try:
            rows = connection.execute(
                """
                SELECT
                    COALESCE(NULLIF(TRIM(CAST(atividade_validacao AS VARCHAR)), ''), 'Sem atividade') AS atividade,
                    count(*) AS total
                FROM read_parquet(?)
                WHERE lower(trim(CAST(status_validacao AS VARCHAR))) = 'rejeitado'
                   OR lower(trim(CAST(STATUS_VALIDACAO AS VARCHAR))) = 'rejeitado'
                GROUP BY 1
                ORDER BY 2 DESC
                """,
                [str(path)],
            ).fetchall()
            return {str(atividade): int(total) for atividade, total in rows}
        except Exception:
            return {}

    def _write_single_row_parquet(
        self,
        connection: duckdb.DuckDBPyConnection,
        path: Path,
        values: dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        select_sql = ", ".join(
            f"{_sql_literal(value)} AS {column}"
            for column, value in values.items()
        )
        connection.execute(
            f"COPY (SELECT {select_sql}) TO ? (FORMAT PARQUET)",
            [str(path)],
        )
