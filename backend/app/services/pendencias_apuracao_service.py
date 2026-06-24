from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


ROOT_DIR = Path(__file__).resolve().parents[3]
APURACAO_DIR = ROOT_DIR / "data" / "mart" / "apuracao"
PENDENCIAS_ATUAL_PATH = APURACAO_DIR / "pendencias_APURACAO_ATUAL.parquet"


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


@dataclass(frozen=True)
class PendenciasApuracaoResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    total_pendencias: int
    horario_negativo: int
    sobreposicao_interrupcao: int
    sobreposicao_uc: int
    sem_causa_componente: int


class PendenciasApuracaoService:
    def materializar(self, anomes: str, origem: Path | None = None) -> PendenciasApuracaoResult:
        APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        origem = origem or self._resolve_origem(anomes)
        if not origem.exists():
            raise FileNotFoundError(f"Parquet de apuração não encontrado: {origem}")

        destino = APURACAO_DIR / f"pendencias_APURACAO_{anomes}.parquet"
        criado_em = datetime.now().isoformat(timespec="seconds")

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                self._create_pendencias_sql(),
                [
                    str(origem),
                    criado_em,
                    str(origem),
                    criado_em,
                    str(origem),
                    criado_em,
                    str(origem),
                    criado_em,
                ],
            )
            connection.execute("COPY pendencias TO ? (FORMAT PARQUET)", [str(destino)])
            total = self._count(connection, "SELECT count(*) FROM pendencias")
            horario = self._count(connection, "SELECT count(*) FROM pendencias WHERE regra = 'horario_negativo'")
            sobreposicao = self._count(
                connection,
                "SELECT count(*) FROM pendencias WHERE regra = 'sobreposicao_interrupcao'",
            )
            sobreposicao_uc = self._count(
                connection,
                "SELECT count(*) FROM pendencias WHERE regra = 'sobreposicao_uc'",
            )
            sem_causa = self._count(
                connection,
                "SELECT count(*) FROM pendencias WHERE regra = 'sem_causa_componente'",
            )

        shutil.copy2(destino, PENDENCIAS_ATUAL_PATH)
        return PendenciasApuracaoResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=PENDENCIAS_ATUAL_PATH,
            total_pendencias=total,
            horario_negativo=horario,
            sobreposicao_interrupcao=sobreposicao,
            sobreposicao_uc=sobreposicao_uc,
            sem_causa_componente=sem_causa,
        )

    def listar(
        self,
        *,
        regra: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        if not PENDENCIAS_ATUAL_PATH.exists():
            return {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "registros": [],
                "status": "sem_pendencias_materializadas",
            }

        where = ""
        params: list[Any] = [str(PENDENCIAS_ATUAL_PATH)]
        if regra:
            where = "WHERE regra = ?"
            params.append(regra)

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                f"SELECT count(*) FROM read_parquet(?) {where}",
                params,
            ).fetchone()[0]
            result = connection.execute(
                f"""
                SELECT *
                FROM read_parquet(?)
                {where}
                ORDER BY gravidade DESC, regra, chave_evento
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "regra": regra,
            "registros": [dict(zip(columns, row)) for row in rows],
            "status": "processado",
        }

    def resumo(self) -> dict[str, Any]:
        if not PENDENCIAS_ATUAL_PATH.exists():
            return {
                "total_pendencias": 0,
                "por_regra": {},
                "status": "sem_pendencias_materializadas",
            }

        with duckdb.connect(database=":memory:") as connection:
            rows = connection.execute(
                """
                SELECT regra, count(*) AS total
                FROM read_parquet(?)
                GROUP BY regra
                ORDER BY total DESC
                """,
                [str(PENDENCIAS_ATUAL_PATH)],
            ).fetchall()
            total = connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(PENDENCIAS_ATUAL_PATH)],
            ).fetchone()[0]

        return {
            "total_pendencias": int(total or 0),
            "por_regra": {str(regra): int(valor) for regra, valor in rows},
            "arquivo": str(PENDENCIAS_ATUAL_PATH),
            "status": "processado",
        }

    def _resolve_origem(self, anomes: str) -> Path:
        atual = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"
        mensal = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        if mensal.exists():
            return mensal
        return atual

    def _count(self, connection: duckdb.DuckDBPyConnection, sql: str) -> int:
        return int(connection.execute(sql).fetchone()[0] or 0)

    def _create_pendencias_sql(self) -> str:
        inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        num_seq = _num_seq_expr()

        return f"""
            CREATE OR REPLACE TEMP TABLE pendencias AS
            WITH
            horario_base AS (
                SELECT
                    {num_seq} AS num_seq_intrp,
                    min({inicio}) AS inicio_intrp,
                    min({fim}) AS fim_intrp,
                    min(date_diff('minute', {inicio}, {fim})) AS duracao_minutos,
                    max(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)) AS num_oper_chv_intrp,
                    max(CAST(REGIONAL_ORIGEM AS VARCHAR)) AS regional_origem,
                    count(*) AS qtd_ucs_afetadas
                FROM read_parquet(?)
                WHERE {inicio} IS NOT NULL
                  AND {fim} IS NOT NULL
                  AND {fim} < {inicio}
                  AND {num_seq} IS NOT NULL
                GROUP BY {num_seq}
            ),
            horario AS (
                SELECT
                    'horario_negativo' AS regra,
                    'alta' AS gravidade,
                    'NUM_SEQ_INTRP' AS grao,
                    CAST(num_seq_intrp AS VARCHAR) AS chave_evento,
                    CAST(num_seq_intrp AS VARCHAR) AS chave_registro,
                    CAST(num_seq_intrp AS VARCHAR) AS num_seq_intrp,
                    CAST(NULL AS VARCHAR) AS num_intrp_uci,
                    CAST(num_oper_chv_intrp AS VARCHAR) AS num_oper_chv_intrp,
                    CAST(NULL AS VARCHAR) AS num_posto_uci,
                    CAST(NULL AS VARCHAR) AS num_uc_uci,
                    CAST(regional_origem AS VARCHAR) AS regional_origem,
                    'DATA_HORA_FIM_INTRP' AS campo_sugerido,
                    strftime(fim_intrp, '%d/%m/%Y %H:%M:%S') AS valor_original,
                    CASE
                        WHEN duracao_minutos >= -180
                        THEN strftime(inicio_intrp + INTERVAL 3 HOUR, '%d/%m/%Y %H:%M:%S')
                        ELSE NULL
                    END AS valor_sugerido,
                    CASE
                        WHEN duracao_minutos >= -180 THEN 'corrigir_fuso'
                        ELSE 'revisao_manual'
                    END AS acao_sugerida,
                    'pendente' AS status_pendencia,
                    'Duração negativa em interrupção distinta. UCs afetadas: ' || CAST(qtd_ucs_afetadas AS VARCHAR) AS justificativa_sistema,
                    ? AS criado_em
                FROM horario_base
            ),
            equipamento_base AS (
                SELECT
                    CAST(NUM_OPER_CHV_INTRP AS VARCHAR) AS num_oper_chv_intrp,
                    {num_seq} AS num_seq_intrp,
                    min({inicio}) AS inicio_intrp,
                    max({fim}) AS fim_intrp,
                    min(TRY_CAST(NUM_SEQ_INTRP AS BIGINT)) AS ordem_seq,
                    max(CAST(REGIONAL_ORIGEM AS VARCHAR)) AS regional_origem,
                    count(*) AS qtd_ucs_afetadas
                FROM read_parquet(?)
                WHERE NULLIF(TRIM(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)), '') IS NOT NULL
                  AND {inicio} IS NOT NULL
                  AND {fim} IS NOT NULL
                  AND {num_seq} IS NOT NULL
                GROUP BY CAST(NUM_OPER_CHV_INTRP AS VARCHAR), {num_seq}
            ),
            equipamento_pares AS (
                SELECT DISTINCT
                    a.num_oper_chv_intrp,
                    a.num_seq_intrp,
                    b.num_seq_intrp AS num_seq_sobreposta,
                    a.regional_origem,
                    a.qtd_ucs_afetadas,
                    CASE
                        WHEN COALESCE(a.ordem_seq, 9223372036854775807) <= COALESCE(b.ordem_seq, 9223372036854775807)
                        THEN 'manter'
                        ELSE 'sugerir_rejeitar'
                    END AS acao
                FROM equipamento_base a
                JOIN equipamento_base b
                  ON a.num_oper_chv_intrp = b.num_oper_chv_intrp
                 AND a.num_seq_intrp <> b.num_seq_intrp
                 AND a.inicio_intrp < b.fim_intrp
                 AND b.inicio_intrp < a.fim_intrp
            ),
            equipamento AS (
                SELECT
                    'sobreposicao_interrupcao' AS regra,
                    'alta' AS gravidade,
                    'NUM_OPER_CHV_INTRP|NUM_SEQ_INTRP' AS grao,
                    num_oper_chv_intrp || '|' || CAST(num_seq_intrp AS VARCHAR) AS chave_evento,
                    num_oper_chv_intrp || '|' || CAST(num_seq_intrp AS VARCHAR) AS chave_registro,
                    CAST(num_seq_intrp AS VARCHAR) AS num_seq_intrp,
                    CAST(NULL AS VARCHAR) AS num_intrp_uci,
                    CAST(num_oper_chv_intrp AS VARCHAR) AS num_oper_chv_intrp,
                    CAST(NULL AS VARCHAR) AS num_posto_uci,
                    CAST(NULL AS VARCHAR) AS num_uc_uci,
                    CAST(regional_origem AS VARCHAR) AS regional_origem,
                    'NUM_MOTIVO_TRAT_DIF_UCI' AS campo_sugerido,
                    CAST(NULL AS VARCHAR) AS valor_original,
                    '91' AS valor_sugerido,
                    'sugerir_rejeitar' AS acao_sugerida,
                    'pendente' AS status_pendencia,
                    'Sobreposição temporal no mesmo equipamento. Manter menor NUM_SEQ_INTRP. UCs afetadas: ' || CAST(qtd_ucs_afetadas AS VARCHAR) AS justificativa_sistema,
                    ? AS criado_em
                FROM equipamento_pares
                WHERE acao = 'sugerir_rejeitar'
            ),
            uc_base AS (
                SELECT
                    CAST(NUM_INTRP_UCI AS VARCHAR) || '|' ||
                    CAST(NUM_POSTO_UCI AS VARCHAR) || '|' ||
                    CAST(NUM_UC_UCI AS VARCHAR) AS chave_registro_uc,
                    CAST(NUM_INTRP_UCI AS VARCHAR) AS num_intrp_uci,
                    CAST(NUM_POSTO_UCI AS VARCHAR) AS num_posto_uci,
                    CAST(NUM_UC_UCI AS VARCHAR) AS num_uc_uci,
                    {num_seq} AS num_seq_intrp,
                    COALESCE(NULLIF(TRIM(CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR)), ''), 'SEM_PROTOCOLO') AS protocolo,
                    min({_timestamp_expr("DTHR_INICIO_INTRP_UC")}) AS inicio_uc,
                    max({fim}) AS fim_uc,
                    max(CAST(REGIONAL_ORIGEM AS VARCHAR)) AS regional_origem,
                    count(*) AS qtd_registros
                FROM read_parquet(?)
                WHERE CAST(ESTADO_INTRP AS VARCHAR) = '4'
                  AND (
                    NUM_MOTIVO_TRAT_DIF_UCI IS NULL
                    OR NULLIF(TRIM(CAST(NUM_MOTIVO_TRAT_DIF_UCI AS VARCHAR)), '') IS NULL
                  )
                  AND NULLIF(TRIM(CAST(NUM_UC_UCI AS VARCHAR)), '') IS NOT NULL
                  AND {_timestamp_expr("DTHR_INICIO_INTRP_UC")} IS NOT NULL
                  AND {fim} IS NOT NULL
                  AND {fim} >= {_timestamp_expr("DTHR_INICIO_INTRP_UC")}
                  AND {num_seq} IS NOT NULL
                GROUP BY
                    CAST(NUM_INTRP_UCI AS VARCHAR),
                    CAST(NUM_POSTO_UCI AS VARCHAR),
                    CAST(NUM_UC_UCI AS VARCHAR),
                    {num_seq},
                    COALESCE(NULLIF(TRIM(CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR)), ''), 'SEM_PROTOCOLO')
            ),
            uc_pares AS (
                SELECT
                    a.*,
                    b.num_seq_intrp AS num_seq_contem,
                    ROW_NUMBER() OVER (
                        PARTITION BY a.chave_registro_uc
                        ORDER BY b.inicio_uc, b.fim_uc DESC, COALESCE(TRY_CAST(b.num_seq_intrp AS BIGINT), 9223372036854775807)
                    ) AS prioridade
                FROM uc_base a
                JOIN uc_base b
                  ON a.num_uc_uci = b.num_uc_uci
                 AND a.protocolo = b.protocolo
                 AND a.num_seq_intrp <> b.num_seq_intrp
                 AND b.inicio_uc <= a.inicio_uc
                 AND b.fim_uc >= a.fim_uc
                 AND (
                    b.inicio_uc < a.inicio_uc
                    OR b.fim_uc > a.fim_uc
                    OR COALESCE(TRY_CAST(b.num_seq_intrp AS BIGINT), 9223372036854775807)
                       < COALESCE(TRY_CAST(a.num_seq_intrp AS BIGINT), 9223372036854775807)
                 )
            ),
            uc AS (
                SELECT
                    'sobreposicao_uc' AS regra,
                    'alta' AS gravidade,
                    'NUM_UC_UCI|NUM_SEQ_INTRP' AS grao,
                    CAST(num_uc_uci AS VARCHAR) || '|' || CAST(num_seq_intrp AS VARCHAR) AS chave_evento,
                    CAST(chave_registro_uc AS VARCHAR) AS chave_registro,
                    CAST(num_seq_intrp AS VARCHAR) AS num_seq_intrp,
                    CAST(num_intrp_uci AS VARCHAR) AS num_intrp_uci,
                    CAST(NULL AS VARCHAR) AS num_oper_chv_intrp,
                    CAST(num_posto_uci AS VARCHAR) AS num_posto_uci,
                    CAST(num_uc_uci AS VARCHAR) AS num_uc_uci,
                    CAST(regional_origem AS VARCHAR) AS regional_origem,
                    'NUM_MOTIVO_TRAT_DIF_UCI' AS campo_sugerido,
                    CAST(NULL AS VARCHAR) AS valor_original,
                    '91' AS valor_sugerido,
                    'classificar_91' AS acao_sugerida,
                    'pendente' AS status_pendencia,
                    'UC com interrupção contida em outra interrupção da mesma UC e mesmo protocolo. NUM_SEQ que contém: '
                        || CAST(num_seq_contem AS VARCHAR) AS justificativa_sistema,
                    ? AS criado_em
                FROM uc_pares
                WHERE prioridade = 1
            ),
            causa_base AS (
                SELECT
                    {num_seq} AS num_seq_intrp,
                    max(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)) AS num_oper_chv_intrp,
                    max(CAST(REGIONAL_ORIGEM AS VARCHAR)) AS regional_origem,
                    max(CAST(COD_CAUSA_INTRP AS VARCHAR)) AS cod_causa,
                    max(CAST(COD_COMP_INTRP AS VARCHAR)) AS cod_comp,
                    count(*) AS qtd_ucs_afetadas
                FROM read_parquet(?)
                WHERE (
                    NULLIF(TRIM(CAST(COD_CAUSA_INTRP AS VARCHAR)), '') IS NULL
                    OR NULLIF(TRIM(CAST(COD_COMP_INTRP AS VARCHAR)), '') IS NULL
                )
                AND {num_seq} IS NOT NULL
                GROUP BY {num_seq}
            ),
            causa AS (
                SELECT
                    'sem_causa_componente' AS regra,
                    'media' AS gravidade,
                    'NUM_SEQ_INTRP' AS grao,
                    CAST(num_seq_intrp AS VARCHAR) AS chave_evento,
                    CAST(num_seq_intrp AS VARCHAR) AS chave_registro,
                    CAST(num_seq_intrp AS VARCHAR) AS num_seq_intrp,
                    CAST(NULL AS VARCHAR) AS num_intrp_uci,
                    CAST(num_oper_chv_intrp AS VARCHAR) AS num_oper_chv_intrp,
                    CAST(NULL AS VARCHAR) AS num_posto_uci,
                    CAST(NULL AS VARCHAR) AS num_uc_uci,
                    CAST(regional_origem AS VARCHAR) AS regional_origem,
                    CASE
                        WHEN NULLIF(TRIM(CAST(cod_causa AS VARCHAR)), '') IS NULL THEN 'COD_CAUSA_INTRP'
                        ELSE 'COD_COMP_INTRP'
                    END AS campo_sugerido,
                    CAST(NULL AS VARCHAR) AS valor_original,
                    CAST(NULL AS VARCHAR) AS valor_sugerido,
                    'sugerir_por_historico_iqs' AS acao_sugerida,
                    'pendente' AS status_pendencia,
                    'Interrupção sem causa ou componente. UCs afetadas: ' || CAST(qtd_ucs_afetadas AS VARCHAR) AS justificativa_sistema,
                    ? AS criado_em
                FROM causa_base
            )
            SELECT * FROM horario
            UNION ALL
            SELECT * FROM equipamento
            UNION ALL
            SELECT * FROM uc
            UNION ALL
            SELECT * FROM causa
        """
