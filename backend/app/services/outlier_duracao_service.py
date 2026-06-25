from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"


COLS_INTERRUPCAO = [
    "PID_INTRP_CONJTO_PIN",
    "INDIC_AREA_REDE_POSTO_PIN",
    "ALIM_INTRP_PIN",
    "ESTADO_INTRP",
    "ALIM_INTRP",
    "CAR_SE",
    "INDIC_INTRP_SE_ALIM",
    "NUM_OCORRENCIA_ADMS",
    "INDIC_INTRP_AT",
    "CONS_INTRP",
    "KVA_INTRP",
    "NUM_OPER_CHV_INTRP",
    "NUM_FUNCAO_ELET_HCAI",
    "DESC_INTRP",
    "VALID_POS_OPERACAO",
    "DATA_HORA_INIC_INTRP",
    "DATA_HORA_FIM_INTRP",
    "TIPO_EQP_INTRP",
    "COORD_X_INTRP",
    "COORD_Y_INTRP",
    "NUM_SEQ_INTRP",
    "COD_CAUSA_INTRP",
    "COD_COMP_INTRP",
    "COD_AREA_ELET_INTRP",
    "COD_GRUPO_COMP_INTRP",
    "COD_COND_CLIMA_INTRP",
    "COD_TIPO_INTRP",
    "INDIC_JUMP_INTRP",
    "NUM_PROTOC_JUSTIF_RESP_INTRP",
    "TIPO_PROTOC_JUSTIF_INTRP",
    "COD_CONJTO_ELET_ANEEL_INTRP",
    "INDIC_CALC_DMIC_INTRP",
    "INDIC_PONTO_CONEX_INTRP",
    "NUM_GEO_CHV_INTRP",
    "TIPO_REDE_CHV_INTRP",
    "TIPO_CHV_INTRP",
    "INDIC_PROPR_POSTO_INTRP",
    "TENSAO_OPER_ALIM_INTRP",
    "INDIC_DESLIG_ENT_SERV_INTRP",
    "INDIC_PROPR_CHVP_INTRP",
    "INDIC_CHVP_INIC_ALIM_INTRP",
    "PID",
]


@dataclass(frozen=True)
class OutlierDuracaoResult:
    anomes: str
    origem: Path
    parquet: Path
    parquet_atual: Path
    limite_horas: float
    total_outliers: int
    total_ucs_afetadas: int
    duracao_max_horas: float
    chi_estimado_horas_uc: float


def _timestamp_expr(column: str) -> str:
    return f"""
        COALESCE(
            TRY_CAST({column} AS TIMESTAMP),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%Y-%m-%d %H:%M:%S'),
            TRY_STRPTIME(CAST({column} AS VARCHAR), '%d/%m/%Y %H:%M:%S')
        )
    """


class OutlierDuracaoService:
    def materializar(
        self,
        anomes: str,
        *,
        limite_horas: float = 48.0,
        usar_tratado: bool = True,
    ) -> OutlierDuracaoResult:
        APURACAO_DIR.mkdir(parents=True, exist_ok=True)
        origem = self._resolve_origem(anomes, usar_tratado=usar_tratado)
        if not origem.exists():
            raise FileNotFoundError(f"Base de apuração não encontrada: {origem}")

        destino = APURACAO_DIR / f"analise_outlier_duracao_APURACAO_{anomes}.parquet"
        destino_atual = APURACAO_DIR / "analise_outlier_duracao_APURACAO_ATUAL.parquet"
        gerado_em = datetime.now().isoformat(timespec="seconds")

        with duckdb.connect(database=":memory:") as connection:
            columns = self._columns(connection, origem)
            select_cols = self._select_interrupcao_columns(columns)
            inicio = _timestamp_expr("DATA_HORA_INIC_INTRP")
            fim = _timestamp_expr("DATA_HORA_FIM_INTRP")
            inicio_uc = _timestamp_expr("DTHR_INICIO_INTRP_UC")

            connection.execute(
                f"""
                CREATE OR REPLACE TEMP TABLE outliers AS
                WITH base AS (
                    SELECT
                        {select_cols},
                        CAST(NUM_UC_UCI AS VARCHAR) AS NUM_UC_UCI_ANALISE,
                        {inicio} AS inicio_ts,
                        {fim} AS fim_ts,
                        {inicio_uc} AS inicio_uc_ts
                    FROM read_parquet(?)
                    WHERE NUM_SEQ_INTRP IS NOT NULL
                ),
                interrupcao AS (
                    SELECT
                        {self._aggregate_interrupcao_columns(columns)},
                        MIN(inicio_ts) AS inicio_interrupcao_ts,
                        MAX(fim_ts) AS fim_interrupcao_ts,
                        COUNT(DISTINCT NULLIF(TRIM(NUM_UC_UCI_ANALISE), '')) AS qtd_ucs_afetadas,
                        COUNT(*) AS qtd_registros_uci
                    FROM base
                    WHERE inicio_ts IS NOT NULL
                      AND fim_ts IS NOT NULL
                      AND fim_ts >= inicio_ts
                    GROUP BY CAST(NUM_SEQ_INTRP AS VARCHAR)
                )
                SELECT
                    *,
                    ROUND(date_diff('minute', inicio_interrupcao_ts, fim_interrupcao_ts) / 60.0, 6)
                        AS duracao_horas,
                    ROUND(
                        (date_diff('minute', inicio_interrupcao_ts, fim_interrupcao_ts) / 60.0)
                        * qtd_ucs_afetadas,
                        6
                    ) AS chi_estimado_horas_uc,
                    'outlier_duracao_interrupcao' AS regra,
                    'analise_manual' AS acao_sugerida,
                    'Interrupção com duração acima de '
                        || CAST(? AS VARCHAR)
                        || ' horas. Não alterar automaticamente; avaliar causa, componente, horários e protocolo.'
                        AS justificativa_sistema,
                    ? AS status_pendencia,
                    ? AS gerado_em
                FROM interrupcao
                WHERE date_diff('minute', inicio_interrupcao_ts, fim_interrupcao_ts) >= ?
                ORDER BY duracao_horas DESC, qtd_ucs_afetadas DESC, NUM_SEQ_INTRP
                """,
                [str(origem), limite_horas, "pendente", gerado_em, int(limite_horas * 60)],
            )
            connection.execute("COPY outliers TO ? (FORMAT PARQUET)", [str(destino)])

            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_outliers,
                    COALESCE(SUM(qtd_ucs_afetadas), 0) AS total_ucs_afetadas,
                    COALESCE(MAX(duracao_horas), 0) AS duracao_max_horas,
                    COALESCE(SUM(chi_estimado_horas_uc), 0) AS chi_estimado_horas_uc
                FROM outliers
                """
            ).fetchone()

        shutil.copy2(destino, destino_atual)
        return OutlierDuracaoResult(
            anomes=anomes,
            origem=origem,
            parquet=destino,
            parquet_atual=destino_atual,
            limite_horas=limite_horas,
            total_outliers=int(row[0] or 0),
            total_ucs_afetadas=int(row[1] or 0),
            duracao_max_horas=float(row[2] or 0),
            chi_estimado_horas_uc=float(row[3] or 0),
        )

    def _resolve_origem(self, anomes: str, *, usar_tratado: bool) -> Path:
        if usar_tratado:
            mensal = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet"
            atual = APURACAO_DIR / "agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet"
        else:
            mensal = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
            atual = APURACAO_DIR / "agrupamento_oms_APURACAO_ATUAL.parquet"
        return mensal if mensal.exists() else atual

    def _columns(self, connection: duckdb.DuckDBPyConnection, origem: Path) -> set[str]:
        rows = connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(origem)],
        ).fetchall()
        return {str(row[0]) for row in rows}

    def _select_interrupcao_columns(self, columns: set[str]) -> str:
        expressions = []
        for column in COLS_INTERRUPCAO:
            if column in columns:
                expressions.append(f'CAST("{column}" AS VARCHAR) AS "{column}"')
            else:
                expressions.append(f'CAST(NULL AS VARCHAR) AS "{column}"')
        return ",\n                        ".join(expressions)

    def _aggregate_interrupcao_columns(self, columns: set[str]) -> str:
        expressions = []
        for column in COLS_INTERRUPCAO:
            if column == "NUM_SEQ_INTRP":
                expressions.append('CAST(NUM_SEQ_INTRP AS VARCHAR) AS "NUM_SEQ_INTRP"')
            elif column in columns:
                expressions.append(f'MAX(CAST("{column}" AS VARCHAR)) AS "{column}"')
            else:
                expressions.append(f'CAST(NULL AS VARCHAR) AS "{column}"')
        return ",\n                        ".join(expressions)
