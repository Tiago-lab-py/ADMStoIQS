from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"
LOGS_DIR = PROJECT_ROOT / "data" / "logs"
BACKUP_DIR = APURACAO_DIR / "backups"


def _timestamp_expr(column: str) -> str:
    return f"""
        COALESCE(
            TRY_CAST({column} AS TIMESTAMP),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%d/%m/%Y %H:%M:%S')
        )
    """


def _str(column: str) -> str:
    return f"CAST({column} AS VARCHAR)"


def _blank_or_null(column: str) -> str:
    return f"({column} IS NULL OR NULLIF(TRIM(CAST({column} AS VARCHAR)), '') IS NULL)"


@dataclass(frozen=True)
class SobreposicaoUcResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    registros_classificar_91: int
    ucs_afetadas: int
    interrupcoes_afetadas: int
    horas_uc_reduzidas: float
    chi_reduzido_estimado: float


@dataclass(frozen=True)
class SobreposicaoUcImplantacaoResult:
    anomes: str
    origem: Path
    backup: Path
    analise: Path
    log: Path
    log_atual: Path
    registros_atualizados: int
    ucs_afetadas: int
    interrupcoes_afetadas: int
    chi_reduzido_estimado: float
    recalculos: dict[str, Any]


class SobreposicaoUcService:
    def materializar(self, anomes: str) -> SobreposicaoUcResult:
        anomes = str(anomes)
        origem = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        destino = APURACAO_DIR / f"analise_sobreposicao_uc_APURACAO_{anomes}.parquet"
        destino_atual = APURACAO_DIR / "analise_sobreposicao_uc_APURACAO_ATUAL.parquet"

        if not origem.exists():
            raise FileNotFoundError(f"Apuração não encontrada: {origem}")

        APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        criado_em = datetime.now().isoformat(timespec="seconds")

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(self._sql_materializacao(), [anomes, str(origem), criado_em])
            connection.execute("COPY analise_sobreposicao_uc TO ? (FORMAT PARQUET)", [str(destino)])
            self._copy_parquet(connection, destino, destino_atual)
            resumo = self._resumo(connection, "analise_sobreposicao_uc")

        return SobreposicaoUcResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=destino_atual,
            registros_classificar_91=resumo["registros_classificar_91"],
            ucs_afetadas=resumo["ucs_afetadas"],
            interrupcoes_afetadas=resumo["interrupcoes_afetadas"],
            horas_uc_reduzidas=resumo["horas_uc_reduzidas"],
            chi_reduzido_estimado=resumo["chi_reduzido_estimado"],
        )

    def consultar(self, anomes: str, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        parquet = APURACAO_DIR / f"analise_sobreposicao_uc_APURACAO_{anomes}.parquet"
        if not parquet.exists():
            raise FileNotFoundError(f"Análise de sobreposição UC não encontrada: {parquet}")

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute("SELECT COUNT(*) FROM read_parquet(?)", [str(parquet)]).fetchone()[0]
            resumo = self._resumo_from_path(connection, parquet)
            result = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                ORDER BY chi_reduzido_estimado DESC, num_uc_uci, data_inicio_uc
                LIMIT ? OFFSET ?
                """,
                [str(parquet), limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(parquet),
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "resumo": resumo,
            "registros": [dict(zip(columns, row, strict=False)) for row in rows],
        }

    def implantar(
        self,
        anomes: str,
        *,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str,
        pc: str,
        recalcular: bool = True,
    ) -> SobreposicaoUcImplantacaoResult:
        anomes = str(anomes)
        origem = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        analise = APURACAO_DIR / f"analise_sobreposicao_uc_APURACAO_{anomes}.parquet"
        atual = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"

        if not origem.exists():
            raise FileNotFoundError(f"Apuração não encontrada: {origem}")
        if not analise.exists():
            self.materializar(anomes)

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = BACKUP_DIR / f"agrupamento_oms_APURACAO_{anomes}_antes_sobreposicao_uc_{timestamp}.parquet"
        temp = origem.with_suffix(".sobreposicao_uc.tmp.parquet")
        log = LOGS_DIR / f"log_implantacao_sobreposicao_uc_{anomes}.parquet"
        log_atual = LOGS_DIR / "log_implantacao_sobreposicao_uc_ATUAL.parquet"
        implantado_em = datetime.now().isoformat(timespec="seconds")

        shutil.copy2(origem, backup)

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE TEMP TABLE chaves_uc91 AS
                SELECT DISTINCT chave_registro
                FROM read_parquet(?)
                WHERE acao_sugerida = 'CLASSIFICAR_91'
                """,
                [str(analise)],
            )
            connection.execute(
                """
                CREATE OR REPLACE TEMP TABLE apuracao_uc91 AS
                SELECT
                    * REPLACE (
                        CASE
                            WHEN (
                                CAST(NUM_INTRP_UCI AS VARCHAR) || '|' ||
                                CAST(NUM_POSTO_UCI AS VARCHAR) || '|' ||
                                CAST(NUM_UC_UCI AS VARCHAR)
                            ) IN (SELECT chave_registro FROM chaves_uc91)
                            THEN '91'
                            ELSE CAST(NUM_MOTIVO_TRAT_DIF_UCI AS VARCHAR)
                        END AS NUM_MOTIVO_TRAT_DIF_UCI
                    )
                FROM read_parquet(?)
                """,
                [str(origem)],
            )
            connection.execute(
                "COPY apuracao_uc91 TO ? (FORMAT PARQUET)",
                [str(temp)],
            )
            temp.replace(origem)
            self._copy_parquet(connection, origem, atual)
            resumo = self._resumo_from_path(connection, analise)
            registros_atualizados = int(
                connection.execute("SELECT COUNT(*) FROM chaves_uc91").fetchone()[0] or 0
            )
            self._gravar_log_implantacao(
                connection=connection,
                analise=analise,
                log=log,
                log_atual=log_atual,
                anomes=anomes,
                usuario=usuario,
                perfil=perfil,
                justificativa=justificativa,
                ip=ip,
                pc=pc,
                implantado_em=implantado_em,
            )

        recalculos = self._recalcular(anomes) if recalcular else {"status": "nao_executado"}

        return SobreposicaoUcImplantacaoResult(
            anomes=anomes,
            origem=origem,
            backup=backup,
            analise=analise,
            log=log,
            log_atual=log_atual,
            registros_atualizados=registros_atualizados,
            ucs_afetadas=int(resumo["ucs_afetadas"]),
            interrupcoes_afetadas=int(resumo["interrupcoes_afetadas"]),
            chi_reduzido_estimado=float(resumo["chi_reduzido_estimado"]),
            recalculos=recalculos,
        )

    def _sql_materializacao(self) -> str:
        inicio = _timestamp_expr("DTHR_INICIO_INTRP_UC")
        fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
        kva = "TRY_CAST(REPLACE(CAST(KVA_INTRP AS VARCHAR), ',', '.') AS DOUBLE)"
        protocolo = "COALESCE(NULLIF(TRIM(CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR)), ''), 'SEM_PROTOCOLO')"
        chave = (
            "CAST(NUM_INTRP_UCI AS VARCHAR) || '|' || "
            "CAST(NUM_POSTO_UCI AS VARCHAR) || '|' || "
            "CAST(NUM_UC_UCI AS VARCHAR)"
        )
        return f"""
            CREATE OR REPLACE TEMP TABLE analise_sobreposicao_uc AS
            WITH base AS (
                SELECT
                    ? AS anomes,
                    {chave} AS chave_registro,
                    {_str("NUM_SEQ_INTRP")} AS num_seq_intrp,
                    {_str("NUM_INTRP_UCI")} AS num_intrp_uci,
                    {_str("NUM_POSTO_UCI")} AS num_posto_uci,
                    {_str("NUM_UC_UCI")} AS num_uc_uci,
                    {protocolo} AS protocolo,
                    {inicio} AS inicio_uc,
                    {fim} AS fim_uc,
                    {_str("REGIONAL_ORIGEM")} AS regional_origem,
                    {kva} AS kva_intrp,
                    TRY_CAST(NUM_SEQ_INTRP AS BIGINT) AS ordem_seq
                FROM read_parquet(?)
                WHERE CAST(ESTADO_INTRP AS VARCHAR) = '4'
                  AND {_blank_or_null("NUM_MOTIVO_TRAT_DIF_UCI")}
                  AND NULLIF(TRIM(CAST(NUM_UC_UCI AS VARCHAR)), '') IS NOT NULL
                  AND {inicio} IS NOT NULL
                  AND {fim} IS NOT NULL
                  AND {fim} >= {inicio}
            ),
            pares AS (
                SELECT
                    a.*,
                    b.num_seq_intrp AS num_seq_contem,
                    b.inicio_uc AS inicio_contem,
                    b.fim_uc AS fim_contem,
                    ROW_NUMBER() OVER (
                        PARTITION BY a.chave_registro
                        ORDER BY b.inicio_uc, b.fim_uc DESC, COALESCE(b.ordem_seq, 9223372036854775807)
                    ) AS prioridade
                FROM base a
                JOIN base b
                  ON a.num_uc_uci = b.num_uc_uci
                 AND a.protocolo = b.protocolo
                 AND a.num_seq_intrp <> b.num_seq_intrp
                 AND b.inicio_uc <= a.inicio_uc
                 AND b.fim_uc >= a.fim_uc
                 AND (
                    b.inicio_uc < a.inicio_uc
                    OR b.fim_uc > a.fim_uc
                    OR COALESCE(b.ordem_seq, 9223372036854775807) < COALESCE(a.ordem_seq, 9223372036854775807)
                 )
            )
            SELECT
                anomes,
                chave_registro,
                num_seq_intrp,
                num_seq_contem,
                num_intrp_uci,
                num_posto_uci,
                num_uc_uci,
                protocolo,
                regional_origem,
                strftime(inicio_uc, '%Y-%m-%d %H:%M:%S') AS data_inicio_uc,
                strftime(fim_uc, '%Y-%m-%d %H:%M:%S') AS data_fim_uc,
                strftime(inicio_contem, '%Y-%m-%d %H:%M:%S') AS data_inicio_contem,
                strftime(fim_contem, '%Y-%m-%d %H:%M:%S') AS data_fim_contem,
                date_diff('minute', inicio_uc, fim_uc) AS duracao_minutos,
                ROUND(date_diff('minute', inicio_uc, fim_uc) / 60.0, 6) AS horas_uc_reduzidas,
                COALESCE(kva_intrp, 0) AS kva_intrp,
                ROUND((date_diff('minute', inicio_uc, fim_uc) / 60.0) * COALESCE(kva_intrp, 0), 6) AS chi_reduzido_estimado,
                'NUM_MOTIVO_TRAT_DIF_UCI' AS campo_sugerido,
                '91' AS valor_sugerido,
                'CLASSIFICAR_91' AS acao_sugerida,
                'pendente' AS status_pendencia,
                'UC com janela de interrupção contida em outra interrupção da mesma UC e mesmo protocolo.' AS justificativa_sistema,
                ? AS criado_em
            FROM pares
            WHERE prioridade = 1
        """

    def _resumo(self, connection: duckdb.DuckDBPyConnection, table_name: str) -> dict[str, Any]:
        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS registros_classificar_91,
                COUNT(DISTINCT num_uc_uci) AS ucs_afetadas,
                COUNT(DISTINCT num_seq_intrp) AS interrupcoes_afetadas,
                SUM(COALESCE(horas_uc_reduzidas, 0)) AS horas_uc_reduzidas,
                SUM(COALESCE(chi_reduzido_estimado, 0)) AS chi_reduzido_estimado
            FROM {table_name}
            """
        ).fetchone()
        return {
            "registros_classificar_91": int(row[0] or 0),
            "ucs_afetadas": int(row[1] or 0),
            "interrupcoes_afetadas": int(row[2] or 0),
            "horas_uc_reduzidas": float(row[3] or 0),
            "chi_reduzido_estimado": float(row[4] or 0),
        }

    def _resumo_from_path(self, connection: duckdb.DuckDBPyConnection, parquet: Path) -> dict[str, Any]:
        connection.execute(
            "CREATE OR REPLACE TEMP TABLE resumo_sobreposicao_uc AS SELECT * FROM read_parquet(?)",
            [str(parquet)],
        )
        return self._resumo(connection, "resumo_sobreposicao_uc")

    def _copy_parquet(self, connection: duckdb.DuckDBPyConnection, origem: Path, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)

    def _gravar_log_implantacao(
        self,
        *,
        connection: duckdb.DuckDBPyConnection,
        analise: Path,
        log: Path,
        log_atual: Path,
        anomes: str,
        usuario: str,
        perfil: str,
        justificativa: str,
        ip: str,
        pc: str,
        implantado_em: str,
    ) -> None:
        temp_log = log.with_suffix(".tmp.parquet")
        connection.execute(
            """
            CREATE OR REPLACE TEMP TABLE novas_implantacoes AS
            SELECT
                ? AS anomes,
                ? AS implantado_em,
                ? AS usuario,
                ? AS perfil,
                ? AS ip,
                ? AS pc,
                ? AS justificativa,
                'sobreposicao_uc' AS regra,
                'popular_motivo_91' AS acao,
                chave_registro,
                num_seq_intrp,
                num_seq_contem,
                num_uc_uci,
                num_posto_uci,
                num_intrp_uci,
                protocolo,
                horas_uc_reduzidas,
                chi_reduzido_estimado
            FROM read_parquet(?)
            WHERE acao_sugerida = 'CLASSIFICAR_91'
            """,
            [anomes, implantado_em, usuario, perfil, ip, pc, justificativa, str(analise)],
        )
        if log.exists():
            connection.execute(
                """
                CREATE OR REPLACE TEMP TABLE log_implantacao AS
                SELECT * FROM read_parquet(?)
                UNION ALL
                SELECT * FROM novas_implantacoes
                """,
                [str(log)],
            )
        else:
            connection.execute("CREATE OR REPLACE TEMP TABLE log_implantacao AS SELECT * FROM novas_implantacoes")
        connection.execute("COPY log_implantacao TO ? (FORMAT PARQUET)", [str(temp_log)])
        temp_log.replace(log)
        self._copy_parquet(connection, log, log_atual)

    def _recalcular(self, anomes: str) -> dict[str, Any]:
        etapas: dict[str, Any] = {}
        try:
            from backend.app.services.pendencias_apuracao_service import PendenciasApuracaoService

            result = PendenciasApuracaoService().materializar(anomes)
            etapas["pendencias"] = {"status": "ok", "total": result.total_pendencias}
        except Exception as error:  # pragma: no cover - retorno operacional
            etapas["pendencias"] = {"status": "erro", "erro": str(error)}

        try:
            from backend.app.services.sobreposicao_interrupcao_service import SobreposicaoInterrupcaoService

            result = SobreposicaoInterrupcaoService().materializar(anomes)
            etapas["sobreposicao_interrupcao"] = {"status": "ok", "excluir": result.excluir}
        except Exception as error:  # pragma: no cover - retorno operacional
            etapas["sobreposicao_interrupcao"] = {"status": "erro", "erro": str(error)}

        try:
            from backend.app.services.tratamento_massivo_service import TratamentoMassivoService

            result = TratamentoMassivoService().gerar_apuracao_tratada(anomes)
            etapas["tratamento_massivo"] = {"status": "ok", "total_final": result.total_final}
        except Exception as error:  # pragma: no cover - retorno operacional
            etapas["tratamento_massivo"] = {"status": "erro", "erro": str(error)}

        try:
            from backend.app.services.indicadores_continuidade_service import IndicadoresContinuidadeService

            result = IndicadoresContinuidadeService().materializar(anomes)
            etapas["indicadores"] = {"status": "ok", "total_comparativo": result.total_comparativo}
        except Exception as error:  # pragma: no cover - retorno operacional
            etapas["indicadores"] = {"status": "erro", "erro": str(error)}

        try:
            from backend.app.services.ressarcimento_service_v2 import RessarcimentoService

            result = RessarcimentoService().materializar(anomes)
            etapas["ressarcimento"] = {
                "status": "ok",
                "valor_estimado_depois": result.valor_estimado_depois,
            }
        except Exception as error:  # pragma: no cover - retorno operacional
            etapas["ressarcimento"] = {"status": "erro", "erro": str(error)}

        return etapas
