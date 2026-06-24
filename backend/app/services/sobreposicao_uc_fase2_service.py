from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from backend.app.services.indicadores_continuidade_service import IndicadoresContinuidadeService
from backend.app.services.pendencias_apuracao_service import PendenciasApuracaoService
from backend.app.services.ressarcimento_service import RessarcimentoService
from backend.app.services.tratamento_massivo_service import TratamentoMassivoService


ROOT_DIR = Path(__file__).resolve().parents[3]
APURACAO_DIR = ROOT_DIR / "data" / "mart" / "apuracao"
LOG_DIR = ROOT_DIR / "data" / "logs"


@dataclass(slots=True)
class SobreposicaoUcFase2Result:
    anomes: str
    origem: str
    parquet: str
    parquet_atual: str
    total_ajustes: int
    ucs_afetadas: int
    interrupcoes_ajustadas: int
    minutos_interseccao: float


@dataclass(slots=True)
class ImplantacaoSobreposicaoUcFase2Result:
    anomes: str
    origem: str
    backup: str
    analise: str
    log: str
    log_atual: str
    registros_atualizados: int
    ucs_afetadas: int
    interrupcoes_ajustadas: int
    minutos_interseccao: float
    recalculos: dict[str, str]


class SobreposicaoUcFase2Service:
    """Analisa e implanta ajuste de interseção temporal por UC.

    Regra Fase 2:
    - considera somente registros com `ESTADO_INTRP = 4`;
    - considera somente `NUM_MOTIVO_TRAT_DIF_UCI` nulo/branco;
    - compara eventos da mesma `NUM_UC_UCI` e mesmo protocolo UCI;
    - quando o registro B inicia dentro do intervalo do registro A e termina depois
      dele, sugere deslocar o início de B para o fim de A;
    - popula `NUM_INTRP_INIC_MANOBRA_UCI` com o `NUM_SEQ_INTRP` do registro A.
    """

    def materializar(self, anomes: str) -> SobreposicaoUcFase2Result:
        origem = self._apuracao_path(anomes)
        destino = self._analise_path(anomes)
        destino_atual = self._analise_atual_path()

        if not origem.exists():
            raise FileNotFoundError(f"Apuração não encontrada: {origem}")

        destino.parent.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                COPY (
                    WITH base AS (
                        SELECT
                            *,
                            CAST(NUM_INTRP_UCI AS VARCHAR) || '|' ||
                            CAST(NUM_POSTO_UCI AS VARCHAR) || '|' ||
                            CAST(NUM_UC_UCI AS VARCHAR) AS chave_registro,
                            NULLIF(TRIM(CAST(NUM_SEQ_INTRP AS VARCHAR)), '') AS num_seq_intrp_txt,
                            NULLIF(TRIM(CAST(NUM_INTRP_UCI AS VARCHAR)), '') AS num_intrp_uci_txt,
                            NULLIF(TRIM(CAST(NUM_UC_UCI AS VARCHAR)), '') AS num_uc_uci_txt,
                            COALESCE(
                                NULLIF(TRIM(CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR)), ''),
                                'SEM_PROTOCOLO'
                            ) AS protocolo_uc,
                            COALESCE(
                                TRY_CAST(DTHR_INICIO_INTRP_UC AS TIMESTAMP),
                                TRY_STRPTIME(CAST(DTHR_INICIO_INTRP_UC AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                                TRY_STRPTIME(CAST(DTHR_INICIO_INTRP_UC AS VARCHAR), '%d/%m/%Y %H:%M:%S')
                            ) AS inicio_uc,
                            COALESCE(
                                TRY_CAST(DATA_HORA_FIM_INTRP AS TIMESTAMP),
                                TRY_STRPTIME(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                                TRY_STRPTIME(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S')
                            ) AS fim_uc
                        FROM read_parquet(?)
                        WHERE CAST(ESTADO_INTRP AS VARCHAR) = '4'
                          AND (
                              NUM_MOTIVO_TRAT_DIF_UCI IS NULL
                              OR TRIM(CAST(NUM_MOTIVO_TRAT_DIF_UCI AS VARCHAR)) = ''
                          )
                          AND NUM_UC_UCI IS NOT NULL
                    ),
                    elegiveis AS (
                        SELECT *
                        FROM base
                        WHERE inicio_uc IS NOT NULL
                          AND fim_uc IS NOT NULL
                          AND fim_uc > inicio_uc
                          AND num_uc_uci_txt IS NOT NULL
                    ),
                    pares AS (
                        SELECT
                            b.chave_registro,
                            b.num_intrp_uci_txt AS num_intrp_uci_alvo,
                            b.num_seq_intrp_txt AS num_seq_intrp_alvo,
                            b.num_uc_uci_txt AS num_uc_uci,
                            CAST(b.NUM_POSTO_UCI AS VARCHAR) AS num_posto_uci,
                            b.protocolo_uc,
                            b.inicio_uc AS inicio_original,
                            b.fim_uc AS fim_alvo,
                            a.num_seq_intrp_txt AS num_seq_intrp_origem,
                            a.num_intrp_uci_txt AS num_intrp_uci_origem,
                            a.inicio_uc AS inicio_origem,
                            a.fim_uc AS fim_origem,
                            date_diff('minute', b.inicio_uc, a.fim_uc) AS minutos_interseccao,
                            ROW_NUMBER() OVER (
                                PARTITION BY b.chave_registro
                                ORDER BY
                                    a.fim_uc DESC,
                                    a.inicio_uc,
                                    TRY_CAST(a.num_seq_intrp_txt AS BIGINT) NULLS LAST,
                                    a.num_seq_intrp_txt
                            ) AS rn
                        FROM elegiveis b
                        JOIN elegiveis a
                          ON a.num_uc_uci_txt = b.num_uc_uci_txt
                         AND a.protocolo_uc = b.protocolo_uc
                         AND a.chave_registro <> b.chave_registro
                         AND a.inicio_uc < b.inicio_uc
                         AND a.fim_uc > b.inicio_uc
                         AND a.fim_uc < b.fim_uc
                    )
                    SELECT
                        'sobreposicao_uc_fase2_interseccao' AS regra,
                        chave_registro,
                        num_intrp_uci_alvo,
                        num_seq_intrp_alvo,
                        num_uc_uci,
                        num_posto_uci,
                        protocolo_uc,
                        strftime(inicio_original, '%Y-%m-%d %H:%M:%S') AS inicio_original,
                        strftime(fim_alvo, '%Y-%m-%d %H:%M:%S') AS fim_alvo,
                        num_intrp_uci_origem,
                        num_seq_intrp_origem,
                        strftime(inicio_origem, '%Y-%m-%d %H:%M:%S') AS inicio_origem,
                        strftime(fim_origem, '%Y-%m-%d %H:%M:%S') AS inicio_sugerido,
                        strftime(fim_origem, '%Y-%m-%d %H:%M:%S') AS fim_origem,
                        minutos_interseccao,
                        'DTHR_INICIO_INTRP_UC' AS campo_sugerido,
                        strftime(fim_origem, '%Y-%m-%d %H:%M:%S') AS valor_sugerido,
                        'NUM_INTRP_INIC_MANOBRA_UCI' AS campo_manobra_sugerido,
                        num_seq_intrp_origem AS valor_manobra_sugerido,
                        'AJUSTAR_INICIO_MANOBRA_UC' AS acao_sugerida,
                        'Interseção temporal parcial na mesma UC e mesmo protocolo; ajustar início do registro alvo para fim da interrupção anterior.' AS justificativa_sistema,
                        'pendente' AS status_pendencia,
                        current_timestamp AS criado_em
                    FROM pares
                    WHERE rn = 1
                      AND minutos_interseccao > 0
                ) TO ? (FORMAT PARQUET)
                """,
                [str(origem), str(destino)],
            )

            self._copy_parquet(destino, destino_atual)

            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_ajustes,
                    COUNT(DISTINCT num_uc_uci) AS ucs_afetadas,
                    COUNT(DISTINCT num_seq_intrp_alvo) AS interrupcoes_ajustadas,
                    COALESCE(SUM(minutos_interseccao), 0) AS minutos_interseccao
                FROM read_parquet(?)
                """,
                [str(destino)],
            ).fetchone()

        return SobreposicaoUcFase2Result(
            anomes=anomes,
            origem=str(origem),
            parquet=str(destino),
            parquet_atual=str(destino_atual),
            total_ajustes=int(row[0] or 0),
            ucs_afetadas=int(row[1] or 0),
            interrupcoes_ajustadas=int(row[2] or 0),
            minutos_interseccao=float(row[3] or 0),
        )

    def listar(self, anomes: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        path = self._analise_path(anomes) if anomes else self._analise_atual_path()
        if not path.exists():
            return {
                "arquivo": str(path),
                "total": 0,
                "registros": [],
                "status": "sem_analise",
            }

        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(path)],
            ).fetchone()[0]
            rows = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                ORDER BY num_uc_uci, inicio_original, chave_registro
                LIMIT ? OFFSET ?
                """,
                [str(path), limit, offset],
            )
            columns = [column[0] for column in rows.description]
            registros = [dict(zip(columns, row)) for row in rows.fetchall()]

        return {
            "arquivo": str(path),
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "registros": registros,
            "status": "processado",
        }

    def implantar(
        self,
        anomes: str,
        usuario: str,
        perfil: str,
        ip: str | None = None,
        pc: str | None = None,
        justificativa: str | None = None,
        recalcular: bool = True,
    ) -> ImplantacaoSobreposicaoUcFase2Result:
        origem = self._apuracao_path(anomes)
        analise = self._analise_path(anomes)

        if not origem.exists():
            raise FileNotFoundError(f"Apuração não encontrada: {origem}")
        if not analise.exists():
            self.materializar(anomes)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = APURACAO_DIR / "backups" / f"agrupamento_oms_APURACAO_{anomes}_antes_sobreposicao_uc_fase2_{timestamp}.parquet"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, backup)

        temp = origem.with_suffix(".sobreposicao_uc_fase2.tmp.parquet")
        log = LOG_DIR / f"log_implantacao_sobreposicao_uc_fase2_{anomes}.parquet"
        log_atual = LOG_DIR / "log_implantacao_sobreposicao_uc_fase2_ATUAL.parquet"
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE TEMP TABLE ajustes AS
                SELECT DISTINCT
                    chave_registro,
                    inicio_sugerido,
                    num_seq_intrp_origem
                FROM read_parquet(?)
                WHERE status_pendencia = 'pendente'
                """,
                [str(analise)],
            )

            metrics = connection.execute(
                """
                SELECT
                    COUNT(*) AS registros_atualizados,
                    COUNT(DISTINCT num_uc_uci) AS ucs_afetadas,
                    COUNT(DISTINCT num_seq_intrp_alvo) AS interrupcoes_ajustadas,
                    COALESCE(SUM(minutos_interseccao), 0) AS minutos_interseccao
                FROM read_parquet(?)
                WHERE status_pendencia = 'pendente'
                """,
                [str(analise)],
            ).fetchone()

            connection.execute(
                """
                CREATE TEMP TABLE apuracao_fase2 AS
                WITH src AS (
                    SELECT
                        *,
                        CAST(NUM_INTRP_UCI AS VARCHAR) || '|' ||
                        CAST(NUM_POSTO_UCI AS VARCHAR) || '|' ||
                        CAST(NUM_UC_UCI AS VARCHAR) AS chave_fase2
                    FROM read_parquet(?)
                )
                SELECT src.* EXCLUDE (chave_fase2) REPLACE (
                    COALESCE(aj.inicio_sugerido, CAST(src.DTHR_INICIO_INTRP_UC AS VARCHAR))
                        AS DTHR_INICIO_INTRP_UC,
                    COALESCE(
                        aj.num_seq_intrp_origem,
                        CAST(src.NUM_INTRP_INIC_MANOBRA_UCI AS VARCHAR)
                    ) AS NUM_INTRP_INIC_MANOBRA_UCI
                )
                FROM src
                LEFT JOIN ajustes aj
                  ON src.chave_fase2 = aj.chave_registro
                """,
                [str(origem)],
            )
            connection.execute("COPY apuracao_fase2 TO ? (FORMAT PARQUET)", [str(temp)])

            connection.execute(
                """
                COPY (
                    SELECT
                        ? AS anomes,
                        regra,
                        chave_registro,
                        num_intrp_uci_alvo,
                        num_seq_intrp_alvo,
                        num_uc_uci,
                        protocolo_uc,
                        inicio_original,
                        inicio_sugerido,
                        fim_alvo,
                        num_intrp_uci_origem,
                        num_seq_intrp_origem,
                        minutos_interseccao,
                        'DTHR_INICIO_INTRP_UC' AS campo_alterado,
                        inicio_original AS valor_original,
                        inicio_sugerido AS valor_novo,
                        'NUM_INTRP_INIC_MANOBRA_UCI' AS campo_alterado_2,
                        NULL AS valor_original_2,
                        num_seq_intrp_origem AS valor_novo_2,
                        ? AS usuario,
                        ? AS perfil,
                        ? AS ip,
                        ? AS pc,
                        ? AS justificativa,
                        current_timestamp AS implantado_em
                    FROM read_parquet(?)
                    WHERE status_pendencia = 'pendente'
                ) TO ? (FORMAT PARQUET)
                """,
                [
                    anomes,
                    usuario,
                    perfil,
                    ip or "",
                    pc or "",
                    justificativa
                    or "Implantação governada da Fase 2 de sobreposição UC: ajuste de início e manobra inicial.",
                    str(analise),
                    str(log),
                ],
            )
            self._copy_parquet(log, log_atual)

        temp.replace(origem)
        shutil.copy2(origem, APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet")

        recalculos: dict[str, str] = {}
        if recalcular:
            recalculos = self._recalcular(anomes)

        return ImplantacaoSobreposicaoUcFase2Result(
            anomes=anomes,
            origem=str(origem),
            backup=str(backup),
            analise=str(analise),
            log=str(log),
            log_atual=str(log_atual),
            registros_atualizados=int(metrics[0] or 0),
            ucs_afetadas=int(metrics[1] or 0),
            interrupcoes_ajustadas=int(metrics[2] or 0),
            minutos_interseccao=float(metrics[3] or 0),
            recalculos=recalculos,
        )

    def _recalcular(self, anomes: str) -> dict[str, str]:
        stages: dict[str, str] = {}
        for name, action in (
            ("pendencias", lambda: PendenciasApuracaoService().materializar(anomes)),
            ("tratamento_massivo", lambda: TratamentoMassivoService().gerar_apuracao_tratada(anomes)),
            ("indicadores", lambda: IndicadoresContinuidadeService().materializar(anomes)),
            ("ressarcimento", lambda: RessarcimentoService().materializar(anomes)),
        ):
            try:
                action()
                stages[name] = "processado"
            except Exception as exc:  # pragma: no cover - retorno operacional
                stages[name] = f"erro: {type(exc).__name__}: {exc}"
        return stages

    def _apuracao_path(self, anomes: str) -> Path:
        return APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"

    def _analise_path(self, anomes: str) -> Path:
        return APURACAO_DIR / f"analise_sobreposicao_uc_fase2_APURACAO_{anomes}.parquet"

    def _analise_atual_path(self) -> Path:
        return APURACAO_DIR / "analise_sobreposicao_uc_fase2_APURACAO_ATUAL.parquet"

    def _copy_parquet(self, origem: Path, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if origem.resolve() != destino.resolve():
            shutil.copy2(origem, destino)
