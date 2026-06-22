from __future__ import annotations

from pathlib import Path

import duckdb

from backend.app.core.contracts import OMS_UNION_CORRIGIDO_PARQUET_PATH, OMS_UNION_PARQUET_PATH


class TratamentoService:
    def __init__(
        self,
        mart_path: Path = OMS_UNION_PARQUET_PATH,
        corrected_mart_path: Path = OMS_UNION_CORRIGIDO_PARQUET_PATH,
    ) -> None:
        self.mart_path = mart_path
        self.corrected_mart_path = corrected_mart_path

    def horario_negativo(
        self,
        anomes: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object | None]]:
        self._require_mart()
        where_anomes = self._where_anomes(anomes, prefix="WHERE")
        and_anomes = self._where_anomes(anomes, prefix="AND")
        query = f"""
            WITH base AS (
                SELECT
                    *,
                    {_timestamp_expr("DATA_HORA_INIC_INTRP")} AS __inicio_ts,
                    {_timestamp_expr("DATA_HORA_FIM_INTRP")} AS __fim_ts
                FROM read_parquet({_sql_string(self.mart_path)})
                {where_anomes}
            ),
            calc AS (
                SELECT
                    *,
                    DATE_DIFF('minute', __inicio_ts, __fim_ts) AS __duracao_min
                FROM base
                WHERE __inicio_ts IS NOT NULL
                  AND __fim_ts IS NOT NULL
                  {and_anomes if where_anomes == "" else ""}
            )
            SELECT
                ANOMES_PROCESSAMENTO,
                REGIONAL_ORIGEM,
                NUM_INTRP_UCI,
                NUM_POSTO_UCI,
                NUM_UC_UCI,
                DATA_HORA_INIC_INTRP,
                DATA_HORA_FIM_INTRP,
                __duracao_min AS duracao_minutos,
                CASE
                    WHEN __duracao_min < 0 AND ABS(__duracao_min) <= 180
                    THEN STRFTIME(__fim_ts + INTERVAL 3 HOUR, '%d/%m/%Y %H:%M:%S')
                    ELSE NULL
                END AS valor_sugerido,
                'DATA_HORA_FIM_INTRP' AS campo_sugerido,
                CASE
                    WHEN __duracao_min < 0 AND ABS(__duracao_min) <= 180
                    THEN 'Sugerir DATA_HORA_FIM_INTRP + 3 horas por provável fuso horário.'
                    ELSE 'Revisão manual: diferença negativa maior que 3 horas.'
                END AS sugestao
            FROM calc
            WHERE __duracao_min < 0
            ORDER BY ABS(__duracao_min) DESC
            LIMIT {self._limit(limit)}
            OFFSET {self._offset(offset)}
        """
        return self._fetch(query)

    def sobreposicao_interrupcao(
        self,
        anomes: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object | None]]:
        self._require_mart()
        where_anomes = self._where_anomes(anomes, prefix="WHERE")
        query = f"""
            WITH base AS (
                SELECT
                    ROW_NUMBER() OVER () AS __rowid,
                    *,
                    {_timestamp_expr("DATA_HORA_INIC_INTRP")} AS __inicio_ts,
                    {_timestamp_expr("DATA_HORA_FIM_INTRP")} AS __fim_ts,
                    TRY_CAST(NUM_SEQ_INTRP AS BIGINT) AS __seq
                FROM read_parquet({_sql_string(self.mart_path)})
                {where_anomes}
            ),
            pares AS (
                SELECT
                    a.ANOMES_PROCESSAMENTO,
                    a.REGIONAL_ORIGEM,
                    a.ALIM_INTRP_PIN,
                    a.NUM_OPER_CHV_INTRP,
                    CASE WHEN a.__seq <= b.__seq THEN a.NUM_SEQ_INTRP ELSE b.NUM_SEQ_INTRP END AS num_seq_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_SEQ_INTRP ELSE a.NUM_SEQ_INTRP END AS num_seq_segunda,
                    CASE WHEN a.__seq <= b.__seq THEN a.NUM_INTRP_UCI ELSE b.NUM_INTRP_UCI END AS num_intrp_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_INTRP_UCI ELSE a.NUM_INTRP_UCI END AS num_intrp_segunda,
                    CASE WHEN a.__seq <= b.__seq THEN a.DATA_HORA_FIM_INTRP ELSE b.DATA_HORA_FIM_INTRP END AS fim_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.DATA_HORA_INIC_INTRP ELSE a.DATA_HORA_INIC_INTRP END AS inicio_segunda_atual,
                    CASE WHEN a.__seq <= b.__seq THEN b.duracao_longa ELSE a.duracao_longa END AS segunda_duracao_longa,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_UC_UCI ELSE a.NUM_UC_UCI END AS num_uc_segunda,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_POSTO_UCI ELSE a.NUM_POSTO_UCI END AS num_posto_segunda
                FROM base a
                JOIN base b
                  ON a.__rowid < b.__rowid
                 AND a.ALIM_INTRP_PIN = b.ALIM_INTRP_PIN
                 AND a.NUM_OPER_CHV_INTRP = b.NUM_OPER_CHV_INTRP
                 AND a.__inicio_ts IS NOT NULL
                 AND a.__fim_ts IS NOT NULL
                 AND b.__inicio_ts IS NOT NULL
                 AND b.__fim_ts IS NOT NULL
                 AND a.__inicio_ts < b.__fim_ts
                 AND b.__inicio_ts < a.__fim_ts
            )
            SELECT
                *,
                CASE
                    WHEN segunda_duracao_longa
                    THEN 'DATA_HORA_INIC_INTRP'
                    ELSE 'NUM_MOTIVO_TRAT_DIF_UCI'
                END AS campo_sugerido,
                CASE
                    WHEN segunda_duracao_longa
                    THEN fim_primeira
                    ELSE '91'
                END AS valor_sugerido,
                CASE
                    WHEN segunda_duracao_longa
                    THEN 'Deslocar início da segunda interrupção para o fim da primeira e preencher NUM_INTRP_INIC_MANOBRA_UCI.'
                    ELSE 'Interrupção curta sobreposta: sugerir exclusão/tratamento diferenciado com motivo 91.'
                END AS sugestao,
                CASE
                    WHEN segunda_duracao_longa
                    THEN num_intrp_primeira
                    ELSE NULL
                END AS NUM_INTRP_INIC_MANOBRA_UCI_sugerido
            FROM pares
            ORDER BY ALIM_INTRP_PIN, NUM_OPER_CHV_INTRP, num_seq_primeira
            LIMIT {self._limit(limit)}
            OFFSET {self._offset(offset)}
        """
        return self._fetch(query)

    def sobreposicao_uc(
        self,
        anomes: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object | None]]:
        self._require_mart()
        where_anomes = self._where_anomes(anomes, prefix="WHERE")
        query = f"""
            WITH base AS (
                SELECT
                    ROW_NUMBER() OVER () AS __rowid,
                    *,
                    {_timestamp_expr("DTHR_INICIO_INTRP_UC")} AS __inicio_uc_ts,
                    {_timestamp_expr("DATA_HORA_FIM_INTRP")} AS __fim_ts,
                    TRY_CAST(NUM_SEQ_INTRP AS BIGINT) AS __seq
                FROM read_parquet({_sql_string(self.mart_path)})
                {where_anomes}
            ),
            pares AS (
                SELECT
                    a.ANOMES_PROCESSAMENTO,
                    a.REGIONAL_ORIGEM,
                    a.NUM_UC_UCI,
                    a.NUM_POSTO_UCI,
                    CASE WHEN a.__seq <= b.__seq THEN a.NUM_SEQ_INTRP ELSE b.NUM_SEQ_INTRP END AS num_seq_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_SEQ_INTRP ELSE a.NUM_SEQ_INTRP END AS num_seq_segunda,
                    CASE WHEN a.__seq <= b.__seq THEN a.NUM_INTRP_UCI ELSE b.NUM_INTRP_UCI END AS num_intrp_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.NUM_INTRP_UCI ELSE a.NUM_INTRP_UCI END AS num_intrp_segunda,
                    CASE WHEN a.__seq <= b.__seq THEN a.DATA_HORA_FIM_INTRP ELSE b.DATA_HORA_FIM_INTRP END AS fim_primeira,
                    CASE WHEN a.__seq <= b.__seq THEN b.DTHR_INICIO_INTRP_UC ELSE a.DTHR_INICIO_INTRP_UC END AS inicio_segunda_atual,
                    CASE WHEN a.__seq <= b.__seq THEN b.duracao_longa ELSE a.duracao_longa END AS segunda_duracao_longa
                FROM base a
                JOIN base b
                  ON a.__rowid < b.__rowid
                 AND a.NUM_UC_UCI = b.NUM_UC_UCI
                 AND a.NUM_POSTO_UCI = b.NUM_POSTO_UCI
                 AND a.__inicio_uc_ts IS NOT NULL
                 AND a.__fim_ts IS NOT NULL
                 AND b.__inicio_uc_ts IS NOT NULL
                 AND b.__fim_ts IS NOT NULL
                 AND a.__inicio_uc_ts < b.__fim_ts
                 AND b.__inicio_uc_ts < a.__fim_ts
            )
            SELECT
                *,
                CASE
                    WHEN segunda_duracao_longa
                    THEN 'DTHR_INICIO_INTRP_UC'
                    ELSE 'NUM_MOTIVO_TRAT_DIF_UCI'
                END AS campo_sugerido,
                CASE
                    WHEN segunda_duracao_longa
                    THEN fim_primeira
                    ELSE '91'
                END AS valor_sugerido,
                CASE
                    WHEN segunda_duracao_longa
                    THEN 'Deslocar início da segunda interrupção da UC para o fim da primeira e preencher NUM_INTRP_INIC_MANOBRA_UCI.'
                    ELSE 'Interrupção curta sobreposta da UC: sugerir exclusão/tratamento diferenciado com motivo 91.'
                END AS sugestao,
                CASE
                    WHEN segunda_duracao_longa
                    THEN num_intrp_primeira
                    ELSE NULL
                END AS NUM_INTRP_INIC_MANOBRA_UCI_sugerido
            FROM pares
            ORDER BY NUM_UC_UCI, NUM_POSTO_UCI, num_seq_primeira
            LIMIT {self._limit(limit)}
            OFFSET {self._offset(offset)}
        """
        return self._fetch(query)

    def sem_causa_componente(
        self,
        anomes: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object | None]]:
        self._require_mart()
        where_anomes = self._where_anomes(anomes, prefix="WHERE")
        connector = "AND" if where_anomes else "WHERE"
        query = f"""
            SELECT
                ANOMES_PROCESSAMENTO,
                REGIONAL_ORIGEM,
                NUM_INTRP_UCI,
                NUM_POSTO_UCI,
                NUM_UC_UCI,
                NUM_OCORRENCIA_ADMS,
                DESC_INTRP,
                TIPO_EQP_INTRP,
                NUM_OPER_CHV_INTRP,
                COD_CAUSA_INTRP,
                COD_COMP_INTRP,
                CASE
                    WHEN NULLIF(TRIM(COALESCE(COD_CAUSA_INTRP, '')), '') IS NULL
                     AND NULLIF(TRIM(COALESCE(COD_COMP_INTRP, '')), '') IS NULL
                    THEN 'COD_CAUSA_INTRP,COD_COMP_INTRP'
                    WHEN NULLIF(TRIM(COALESCE(COD_CAUSA_INTRP, '')), '') IS NULL
                    THEN 'COD_CAUSA_INTRP'
                    ELSE 'COD_COMP_INTRP'
                END AS campo_sugerido,
                'Revisar causa/componente com base em descrição, tipo de equipamento e histórico de ocorrências similares.' AS sugestao
            FROM read_parquet({_sql_string(self.mart_path)})
            {where_anomes}
            {connector} (
                NULLIF(TRIM(COALESCE(COD_CAUSA_INTRP, '')), '') IS NULL
                OR NULLIF(TRIM(COALESCE(COD_COMP_INTRP, '')), '') IS NULL
            )
            ORDER BY ANOMES_PROCESSAMENTO, REGIONAL_ORIGEM, NUM_OCORRENCIA_ADMS
            LIMIT {self._limit(limit)}
            OFFSET {self._offset(offset)}
        """
        return self._fetch(query)

    def _require_mart(self) -> None:
        if self._mart_has_anomes(self.corrected_mart_path):
            self.mart_path = self.corrected_mart_path
            return

        if not self.mart_path.exists():
            raise FileNotFoundError(
                f"OMS_union.parquet não encontrado: {self.mart_path}. "
                "Gere o mart com python -m backend.scripts.gerar_oms_union."
            )

    def _mart_has_anomes(self, parquet_path: Path) -> bool:
        if not parquet_path.exists():
            return False

        connection = duckdb.connect(":memory:")
        try:
            rows = connection.execute(
                f"DESCRIBE SELECT * FROM read_parquet({_sql_string(parquet_path)})"
            ).fetchall()
            return "ANOMES_PROCESSAMENTO" in {row[0] for row in rows}
        except Exception:
            return False
        finally:
            connection.close()

    def _fetch(self, query: str) -> list[dict[str, object | None]]:
        connection = duckdb.connect(":memory:")
        try:
            dataframe = connection.execute(query).fetchdf()
            return dataframe.where(dataframe.notna(), None).to_dict(orient="records")
        finally:
            connection.close()

    def _where_anomes(self, anomes: str | None, prefix: str) -> str:
        if not anomes:
            return ""
        if len(anomes) != 6 or not anomes.isdigit():
            raise ValueError("anomes deve estar no formato YYYYMM.")
        return f"{prefix} ANOMES_PROCESSAMENTO = {_sql_literal(anomes)}"

    @staticmethod
    def _limit(limit: int) -> int:
        return min(max(limit, 1), 5000)

    @staticmethod
    def _offset(offset: int) -> int:
        return max(offset, 0)


def _timestamp_expr(column: str) -> str:
    return f"""
        COALESCE(
            TRY_STRPTIME({column}, '%d/%m/%Y %H:%M:%S'),
            TRY_STRPTIME({column}, '%Y-%m-%d %H:%M:%S')
        )
    """


def _sql_string(path: Path) -> str:
    escaped = str(path).replace("'", "''")
    return f"'{escaped}'"


def _sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
