from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"


@dataclass(frozen=True)
class SobreposicaoInterrupcaoResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    total_interrupcoes: int
    manter: int
    excluir: int


class SobreposicaoInterrupcaoService:
    def __init__(self, apuracao_dir: Path = APURACAO_DIR) -> None:
        self.apuracao_dir = apuracao_dir

    def materializar(self, anomes: str) -> SobreposicaoInterrupcaoResult:
        origem = self.apuracao_dir / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        if not origem.exists():
            raise FileNotFoundError(
                f"Apuração não encontrada: {origem}. "
                "Gere a apuração mensal antes da análise de sobreposição."
            )

        destino = self.apuracao_dir / f"analise_sobreposicao_interrupcao_APURACAO_{anomes}.parquet"
        destino_atual = self.apuracao_dir / "analise_sobreposicao_interrupcao_APURACAO_ATUAL.parquet"
        temp_destino = destino.with_suffix(".tmp.parquet")

        with duckdb.connect(database=":memory:") as connection:
            connection.execute(
                """
                CREATE TEMP TABLE analise_sobreposicao AS
                WITH origem AS (
                    SELECT
                        *,
                        COALESCE(
                            try_strptime(CAST(DATA_HORA_INIC_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S'),
                            try_strptime(CAST(DATA_HORA_INIC_INTRP AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                            try_cast(DATA_HORA_INIC_INTRP AS TIMESTAMP)
                        ) AS data_inicio_ts,
                        COALESCE(
                            try_strptime(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%d/%m/%Y %H:%M:%S'),
                            try_strptime(CAST(DATA_HORA_FIM_INTRP AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
                            try_cast(DATA_HORA_FIM_INTRP AS TIMESTAMP)
                        ) AS data_fim_ts
                    FROM read_parquet(?)
                ),
                interrupcoes_filtradas AS (
                    SELECT
                        ? AS anomes,
                        COALESCE(CAST(NUM_OCORRENCIA_ADMS AS VARCHAR), CAST(PID_INTRP_CONJTO_PIN AS VARCHAR)) AS ocorrencia,
                        CAST(NUM_SEQ_INTRP AS VARCHAR) AS interrupcao,
                        CAST(TIPO_CHV_INTRP AS VARCHAR) AS tipo_chave,
                        CAST(NUM_OPER_CHV_INTRP AS VARCHAR) AS numero_operacional,
                        MIN(data_inicio_ts) AS data_inicio,
                        MAX(data_fim_ts) AS data_fim,
                        MAX(CAST(COD_CAUSA_INTRP AS VARCHAR)) AS cod_causa_intrp,
                        MAX(CAST(COD_COMP_INTRP AS VARCHAR)) AS cod_comp_intrp,
                        MAX(CAST(COD_TIPO_INTRP AS VARCHAR)) AS cod_tipo_intrp,
                        MAX(CAST(TIPO_PROTOC_JUSTIF_INTRP AS VARCHAR)) AS tipo_protoc_justif_intrp,
                        MAX(CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR)) AS tipo_protocolo_uci,
                        MAX(CAST(REGIONAL_ORIGEM AS VARCHAR)) AS regional_origem,
                        COUNT(DISTINCT COALESCE(CAST(NUM_POSTO_UCI AS VARCHAR), '') || '|' || COALESCE(CAST(NUM_UC_UCI AS VARCHAR), '')) AS uc_afetadas
                    FROM origem
                    WHERE CAST(TIPO_EQP_INTRP AS VARCHAR) = 'C'
                      AND CAST(ESTADO_INTRP AS VARCHAR) = '4'
                      AND (
                            NUM_MOTIVO_TRAT_DIF_UCI IS NULL
                         OR NULLIF(TRIM(CAST(NUM_MOTIVO_TRAT_DIF_UCI AS VARCHAR)), '') IS NULL
                      )
                      AND NUM_OPER_CHV_INTRP IS NOT NULL
                      AND TRIM(CAST(NUM_OPER_CHV_INTRP AS VARCHAR)) <> ''
                      AND NUM_SEQ_INTRP IS NOT NULL
                      AND data_inicio_ts IS NOT NULL
                      AND data_fim_ts IS NOT NULL
                    GROUP BY
                        COALESCE(CAST(NUM_OCORRENCIA_ADMS AS VARCHAR), CAST(PID_INTRP_CONJTO_PIN AS VARCHAR)),
                        CAST(NUM_SEQ_INTRP AS VARCHAR),
                        CAST(TIPO_CHV_INTRP AS VARCHAR),
                        CAST(NUM_OPER_CHV_INTRP AS VARCHAR)
                ),
                mapeamento_sobreposicao AS (
                    SELECT
                        a.*,
                        CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM interrupcoes_filtradas b
                                WHERE a.numero_operacional = b.numero_operacional
                                  AND a.interrupcao <> b.interrupcao
                                  AND b.data_inicio <= a.data_inicio
                                  AND b.data_fim >= a.data_fim
                                  AND (
                                      b.data_inicio < a.data_inicio
                                      OR b.data_fim > a.data_fim
                                      OR COALESCE(TRY_CAST(b.interrupcao AS BIGINT), 0) < COALESCE(TRY_CAST(a.interrupcao AS BIGINT), 0)
                                  )
                            )
                            THEN 'EXCLUIR'
                            ELSE 'MANTER'
                        END AS acao_sugerida
                    FROM interrupcoes_filtradas a
                )
                SELECT
                    anomes,
                    numero_operacional AS NUMERO_OPERACIONAL,
                    ocorrencia,
                    interrupcao,
                    tipo_chave,
                    data_inicio AS DATA_INICIO,
                    data_fim AS DATA_FIM,
                    CASE
                        WHEN acao_sugerida = 'EXCLUIR' THEN 'EXCLUIR (Contido em outra)'
                        ELSE 'MANTER (OK)'
                    END AS SITUACAO,
                    acao_sugerida,
                    CASE WHEN acao_sugerida = 'EXCLUIR' THEN '7' ELSE NULL END AS ESTADO_INTRP_SUGERIDO,
                    CASE WHEN acao_sugerida = 'EXCLUIR' THEN '91' ELSE NULL END AS NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO,
                    cod_causa_intrp AS COD_CAUSA_INTRP,
                    cod_comp_intrp AS COD_COMP_INTRP,
                    cod_tipo_intrp AS COD_TIPO_INTRP,
                    tipo_protoc_justif_intrp AS TIPO_PROTOC_JUSTIF_INTRP,
                    tipo_protocolo_uci AS TIPO_PROTOC_JUSTIF_UCI,
                    regional_origem AS REGIONAL_ORIGEM,
                    uc_afetadas AS UC_AFETADAS,
                    CASE
                        WHEN acao_sugerida = 'EXCLUIR'
                        THEN 'Interrupção contida temporalmente em outra do mesmo NUM_OPER_CHV_INTRP; sugerir ESTADO_INTRP=7 e NUM_MOTIVO_TRAT_DIF_UCI=91.'
                        ELSE 'Interrupção não contida por outra do mesmo NUM_OPER_CHV_INTRP.'
                    END AS JUSTIFICATIVA_SISTEMA
                FROM mapeamento_sobreposicao
                ORDER BY numero_operacional, data_inicio, SITUACAO DESC
                """,
                [str(origem), anomes],
            )

            summary = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_interrupcoes,
                    SUM(CASE WHEN acao_sugerida = 'MANTER' THEN 1 ELSE 0 END) AS manter,
                    SUM(CASE WHEN acao_sugerida = 'EXCLUIR' THEN 1 ELSE 0 END) AS excluir
                FROM analise_sobreposicao
                """
            ).fetchone()

            connection.execute("COPY analise_sobreposicao TO ? (FORMAT PARQUET)", [str(temp_destino)])

        temp_destino.replace(destino)
        shutil.copyfile(destino, destino_atual)

        return SobreposicaoInterrupcaoResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=destino_atual,
            total_interrupcoes=int(summary[0] or 0),
            manter=int(summary[1] or 0),
            excluir=int(summary[2] or 0),
        )
