from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APURACAO_DIR = PROJECT_ROOT / "data" / "mart" / "apuracao"
INDICADORES_DIR = PROJECT_ROOT / "data" / "mart" / "indicadores"
IQS_MART_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "mart"
IQS_RAW_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "raw"


@dataclass(frozen=True)
class IndicadoresContinuidadeResult:
    anomes: str
    origem_antes: Path
    origem_depois: Path
    mart_uc: Path
    mart_agregado: Path
    mart_comparativo: Path
    total_uc: int
    total_agregado: int
    total_comparativo: int
    fonte_denominador: str
    filtro_faturamento: str


class IndicadoresContinuidadeService:
    def materializar(self, anomes: str) -> IndicadoresContinuidadeResult:
        origem_antes = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}.parquet"
        origem_depois = APURACAO_DIR / f"agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet"
        if not origem_antes.exists():
            raise FileNotFoundError(f"Apuração original não encontrada: {origem_antes}")
        if not origem_depois.exists():
            raise FileNotFoundError(f"Apuração tratada não encontrada: {origem_depois}")

        INDICADORES_DIR.mkdir(parents=True, exist_ok=True)
        mart_uc = INDICADORES_DIR / f"indicadores_uc_{anomes}.parquet"
        mart_agregado = INDICADORES_DIR / f"indicadores_agregado_{anomes}.parquet"
        mart_comparativo = INDICADORES_DIR / f"indicadores_comparativo_{anomes}.parquet"
        mart_uc_atual = INDICADORES_DIR / "indicadores_uc_ATUAL.parquet"
        mart_agregado_atual = INDICADORES_DIR / "indicadores_agregado_ATUAL.parquet"
        mart_comparativo_atual = INDICADORES_DIR / "indicadores_comparativo_ATUAL.parquet"

        consumidores_regional = self._primeiro_arquivo_existente(
            [
                IQS_MART_DIR / f"mart_consumidores_regional_{anomes}.parquet",
                IQS_RAW_DIR / f"consumidores_regional_{anomes}.parquet",
            ]
        )
        consumidor_faturado = self._primeiro_arquivo_existente(
            [
                IQS_MART_DIR / f"mart_consumidor_faturado_regional_{anomes}.parquet",
                IQS_RAW_DIR / f"consumidor_faturado_regional_{anomes}.parquet",
            ]
        )
        uc_faturada_mart = IQS_MART_DIR / f"mart_uc_faturada_hcai_{anomes}.parquet"
        uc_faturada_raw = IQS_RAW_DIR / f"uc_faturada_hcai_{anomes}.parquet"
        fonte_denominador = "COUNT_DISTINCT_NUM_UC_UCI"
        filtro_faturamento = "NAO_APLICADO"

        with duckdb.connect(database=":memory:") as connection:
            self._criar_base(connection, origem_antes, origem_depois, anomes)
            self._aplicar_filtro_faturamento(connection, uc_faturada_mart, uc_faturada_raw)
            filtro_faturamento = connection.execute("SELECT filtro_faturamento FROM filtro_faturamento_info").fetchone()[0]
            self._criar_denominadores(connection, consumidores_regional, consumidor_faturado)
            fonte_denominador = connection.execute("SELECT fonte_denominador FROM denominador_info").fetchone()[0]
            self._materializar_uc(connection, mart_uc)
            self._materializar_agregado(connection, mart_agregado)
            self._materializar_comparativo(connection, mart_comparativo)

            total_uc = connection.execute("SELECT COUNT(*) FROM indicadores_uc").fetchone()[0]
            total_agregado = connection.execute("SELECT COUNT(*) FROM indicadores_agregado").fetchone()[0]
            total_comparativo = connection.execute("SELECT COUNT(*) FROM indicadores_comparativo").fetchone()[0]

            connection.execute(
                "COPY (SELECT * FROM indicadores_uc) TO ? (FORMAT PARQUET)",
                [str(mart_uc_atual)],
            )
            connection.execute(
                "COPY (SELECT * FROM indicadores_agregado) TO ? (FORMAT PARQUET)",
                [str(mart_agregado_atual)],
            )
            connection.execute(
                "COPY (SELECT * FROM indicadores_comparativo) TO ? (FORMAT PARQUET)",
                [str(mart_comparativo_atual)],
            )

        return IndicadoresContinuidadeResult(
            anomes=anomes,
            origem_antes=origem_antes,
            origem_depois=origem_depois,
            mart_uc=mart_uc,
            mart_agregado=mart_agregado,
            mart_comparativo=mart_comparativo,
            total_uc=total_uc,
            total_agregado=total_agregado,
            total_comparativo=total_comparativo,
            fonte_denominador=fonte_denominador,
            filtro_faturamento=filtro_faturamento,
        )

    def _criar_base(
        self,
        connection: duckdb.DuckDBPyConnection,
        origem_antes: Path,
        origem_depois: Path,
        anomes: str,
    ) -> None:
        connection.execute(
            """
            CREATE TEMP TABLE base_raw AS
            SELECT 'antes' AS cenario, * FROM read_parquet(?)
            UNION ALL
            SELECT 'depois' AS cenario, * FROM read_parquet(?)
            """,
            [str(origem_antes), str(origem_depois)],
        )
        connection.execute(
            """
            CREATE TEMP TABLE base_indicadores AS
            WITH parse AS (
                SELECT
                    cenario,
                    ? AS anomes,
                    CASE
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) = 'P' THEN 'CSL'
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) = 'L' THEN 'NRT'
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) = 'M' THEN 'NRO'
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) = 'C' THEN 'LES'
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) = 'V' THEN 'OES'
                        WHEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, '')))) IN ('CSL', 'NRT', 'NRO', 'LES', 'OES')
                            THEN UPPER(TRIM(COALESCE(NULLIF(SIGLA_REGIONAL, ''), NULLIF(REGIONAL_ORIGEM, ''))))
                        ELSE 'COPEL'
                    END AS regional_origem,
                    COALESCE(NULLIF(COD_CONJTO_ELET_ANEEL_INTRP, ''), 'SEM_CONJUNTO') AS cod_conjunto_aneel,
                    CAST(NUM_POSTO_UCI AS VARCHAR) AS num_posto_uci,
                    CAST(NUM_UC_UCI AS VARCHAR) AS num_uc_uci,
                    CAST(NUM_SEQ_INTRP AS VARCHAR) AS num_seq_intrp,
                    CAST(NUM_INTRP_UCI AS VARCHAR) AS num_intrp_uci,
                    COALESCE(
                        try_strptime(NULLIF(DTHR_INICIO_INTRP_UC, ''), '%Y-%m-%d %H:%M:%S'),
                        try_strptime(NULLIF(DTHR_INICIO_INTRP_UC, ''), '%d/%m/%Y %H:%M:%S'),
                        try_strptime(NULLIF(DATA_HORA_INIC_INTRP, ''), '%Y-%m-%d %H:%M:%S'),
                        try_strptime(NULLIF(DATA_HORA_INIC_INTRP, ''), '%d/%m/%Y %H:%M:%S')
                    ) AS inicio_uc,
                    COALESCE(
                        try_strptime(NULLIF(DATA_HORA_FIM_INTRP, ''), '%Y-%m-%d %H:%M:%S'),
                        try_strptime(NULLIF(DATA_HORA_FIM_INTRP, ''), '%d/%m/%Y %H:%M:%S')
                    ) AS fim_uc,
                    CAST(ESTADO_INTRP AS VARCHAR) AS estado_intrp,
                    CAST(NUM_MOTIVO_TRAT_DIF_UCI AS VARCHAR) AS motivo_tratamento,
                    CAST(TIPO_PROTOC_JUSTIF_UCI AS VARCHAR) AS tipo_protocolo_uci,
                    CAST(TIPO_PROTOC_JUSTIF_INTRP AS VARCHAR) AS tipo_protocolo_interrupcao
                FROM base_raw
                WHERE NUM_UC_UCI IS NOT NULL
                  AND NULLIF(CAST(NUM_UC_UCI AS VARCHAR), '') IS NOT NULL
            )
            SELECT
                *,
                date_diff('minute', inicio_uc, fim_uc) AS duracao_minutos_uc,
                inicio_uc IS NOT NULL
                AND fim_uc IS NOT NULL
                AND date_diff('minute', inicio_uc, fim_uc) >= 0 AS duracao_valida,
                date_diff('minute', inicio_uc, fim_uc) >= 3 AS duracao_longa_liquida,
                NULLIF(TRIM(tipo_protocolo_uci), '') = '0'
                    AS protocolo_liquido
            FROM parse
            """,
            [anomes],
        )

    def _aplicar_filtro_faturamento(
        self,
        connection: duckdb.DuckDBPyConnection,
        uc_faturada_mart: Path,
        uc_faturada_raw: Path,
    ) -> None:
        fonte = uc_faturada_mart if uc_faturada_mart.exists() else uc_faturada_raw
        if not fonte.exists():
            connection.execute(
                """
                CREATE TEMP TABLE filtro_faturamento_info AS
                SELECT 'NAO_APLICADO' AS filtro_faturamento
                """
            )
            connection.execute(
                """
                CREATE TEMP TABLE base_indicadores_filtrada AS
                SELECT
                    *,
                    'NAO_APLICADO' AS filtro_faturamento
                FROM base_indicadores
                """
            )
            connection.execute("DROP TABLE base_indicadores")
            connection.execute("ALTER TABLE base_indicadores_filtrada RENAME TO base_indicadores")
            return

        columns = [
            row[0]
            for row in connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(fonte)],
            ).fetchall()
        ]
        uc_col = self._first_existing(columns, ["uc", "NUM_UC_HCAI", "NUM_UC_UCI", "NUM_UC"])
        faturado_col = self._first_existing(columns, ["faturado", "INDIC_FAT_HCAI", "INDIC_FAT"])
        regional_col = self._first_existing(columns, ["regional", "REGIONAL", "REGIONAL_ORIGEM"])

        if not uc_col or not faturado_col:
            connection.execute(
                """
                CREATE TEMP TABLE filtro_faturamento_info AS
                SELECT 'NAO_APLICADO_COLUNAS_INVALIDAS' AS filtro_faturamento
                """
            )
            connection.execute(
                """
                CREATE TEMP TABLE base_indicadores_filtrada AS
                SELECT
                    *,
                    'NAO_APLICADO_COLUNAS_INVALIDAS' AS filtro_faturamento
                FROM base_indicadores
                """
            )
            connection.execute("DROP TABLE base_indicadores")
            connection.execute("ALTER TABLE base_indicadores_filtrada RENAME TO base_indicadores")
            return

        regional_expression = (
            f"COALESCE(NULLIF(CAST({regional_col} AS VARCHAR), ''), 'COPEL')"
            if regional_col
            else "'COPEL'"
        )
        connection.execute(
            f"""
            CREATE TEMP TABLE ucs_faturadas_hcai AS
            SELECT DISTINCT
                CAST({uc_col} AS VARCHAR) AS num_uc_uci,
                UPPER(TRIM(CAST({faturado_col} AS VARCHAR))) AS faturado,
                {regional_expression} AS regional_hcai
            FROM read_parquet(?)
            """,
            [str(fonte)],
        )
        connection.execute(
            """
            CREATE TEMP TABLE filtro_faturamento_info AS
            SELECT 'APLICADO_UC_FATURADA_HCAI' AS filtro_faturamento
            """
        )
        connection.execute(
            """
            CREATE TEMP TABLE base_indicadores_filtrada AS
            SELECT
                base.*,
                'APLICADO_UC_FATURADA_HCAI' AS filtro_faturamento
            FROM base_indicadores AS base
            INNER JOIN ucs_faturadas_hcai AS fat
              ON base.num_uc_uci = fat.num_uc_uci
             AND fat.faturado = 'S'
            """
        )
        connection.execute("DROP TABLE base_indicadores")
        connection.execute("ALTER TABLE base_indicadores_filtrada RENAME TO base_indicadores")

    def _criar_denominadores(
        self,
        connection: duckdb.DuckDBPyConnection,
        consumidores_regional: Path,
        consumidor_faturado: Path,
    ) -> None:
        connection.execute(
            """
            CREATE TEMP TABLE denominadores_fallback AS
            SELECT
                cenario,
                regional_origem,
                COUNT(DISTINCT num_uc_uci) AS quantidade_ucs
            FROM base_indicadores
            GROUP BY cenario, regional_origem
            """
        )

        if consumidor_faturado is not None:
            connection.execute(
                """
                CREATE TEMP TABLE denominador_info AS
                SELECT 'IQS_CONSUMIDOR_FATURADO_REGIONAL' AS fonte_denominador
                """
            )
            self._criar_denominadores_iqs(connection, consumidor_faturado)
            return

        if consumidores_regional is not None:
            connection.execute(
                """
                CREATE TEMP TABLE denominador_info AS
                SELECT 'IQS_CONSUMIDORES_REGIONAL' AS fonte_denominador
                """
            )
            self._criar_denominadores_iqs(connection, consumidores_regional)
            return

        connection.execute(
            """
            CREATE TEMP TABLE denominador_info AS
            SELECT 'COUNT_DISTINCT_NUM_UC_UCI' AS fonte_denominador
            """
        )
        connection.execute(
            """
            CREATE TEMP TABLE denominadores AS
            SELECT * FROM denominadores_fallback
            """
        )

    def _criar_denominadores_iqs(self, connection: duckdb.DuckDBPyConnection, fonte: Path) -> None:
        columns = [
            row[0]
            for row in connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(fonte)],
        ).fetchall()
        ]
        regional_col = self._first_existing(
            columns,
            [
                "REGIONAL_TOTAL",
                "REGIONAL_ORIGEM",
                "SIGLA_REGIONAL",
                "REGIONAL",
                "DSC_REGIONAL",
                "NOME_REGIONAL",
            ],
        )
        quantidade_col = self._first_existing(
            columns,
            [
                "UC_faturada",
                "UC_FATURADA",
                "QTD_UC",
                "QTD_UCS",
                "QUANTIDADE_UCS",
                "CONSUMIDORES",
                "TOTAL",
                "QTDE",
            ],
        )
        if not regional_col or not quantidade_col:
            connection.execute(
                """
                CREATE TEMP TABLE denominadores AS
                SELECT * FROM denominadores_fallback
                """
            )
            connection.execute(
                """
                DROP TABLE denominador_info
                """
            )
            connection.execute(
                """
                CREATE TEMP TABLE denominador_info AS
                SELECT 'COUNT_DISTINCT_NUM_UC_UCI' AS fonte_denominador
                """
            )
            return

        connection.execute(
            f"""
            CREATE TEMP TABLE denominadores_iqs_regional AS
            SELECT
                COALESCE(NULLIF(CAST({regional_col} AS VARCHAR), ''), 'SEM_REGIONAL') AS regional_origem,
                SUM(TRY_CAST({quantidade_col} AS DOUBLE)) AS quantidade_ucs
            FROM read_parquet(?)
            GROUP BY COALESCE(NULLIF(CAST({regional_col} AS VARCHAR), ''), 'SEM_REGIONAL')
            """,
            [str(fonte)],
        )
        connection.execute(
            """
            CREATE TEMP TABLE denominadores AS
            SELECT
                fallback.cenario,
                fallback.regional_origem,
                COALESCE(iqs.quantidade_ucs, fallback.quantidade_ucs) AS quantidade_ucs
            FROM denominadores_fallback AS fallback
            LEFT JOIN denominadores_iqs_regional AS iqs
              ON fallback.regional_origem = iqs.regional_origem
            """
        )

    def _materializar_uc(self, connection: duckdb.DuckDBPyConnection, mart_uc: Path) -> None:
        gerado_em = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            CREATE TEMP TABLE indicadores_uc AS
            SELECT
                cenario,
                anomes,
                regional_origem,
                cod_conjunto_aneel,
                num_posto_uci,
                num_uc_uci,
                SUM(duracao_minutos_uc) / 60.0 AS dic_horas,
                COUNT(DISTINCT num_seq_intrp) AS fic,
                MAX(duracao_minutos_uc) / 60.0 AS dmic_horas,
                COUNT(DISTINCT num_seq_intrp) AS interrupcoes_distintas,
                (SELECT fonte_denominador FROM denominador_info) AS fonte_denominador,
                MAX(filtro_faturamento) AS filtro_faturamento,
                'ESTADO_4_DURACAO_MAIOR_IGUAL_3_PROTOCOLO_0_MOTIVO_NULO_FATURADA' AS regra_liquido,
                ? AS gerado_em
            FROM base_indicadores
            WHERE duracao_valida
              AND estado_intrp = '4'
              AND duracao_longa_liquida
              AND protocolo_liquido
              AND (
                    motivo_tratamento IS NULL
                 OR NULLIF(TRIM(motivo_tratamento), '') IS NULL
              )
            GROUP BY
                cenario,
                anomes,
                regional_origem,
                cod_conjunto_aneel,
                num_posto_uci,
                num_uc_uci
            """,
            [gerado_em],
        )
        connection.execute(
            "COPY indicadores_uc TO ? (FORMAT PARQUET)",
            [str(mart_uc)],
        )

    def _materializar_agregado(self, connection: duckdb.DuckDBPyConnection, mart_agregado: Path) -> None:
        gerado_em = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            CREATE TEMP TABLE indicadores_agregado AS
            WITH regional AS (
                SELECT
                    uc.cenario,
                    uc.anomes,
                    'REGIONAL' AS nivel,
                    uc.regional_origem,
                    'TODOS' AS cod_conjunto_aneel,
                    MAX(den.quantidade_ucs) AS quantidade_ucs,
                    SUM(uc.dic_horas) AS soma_dic_horas,
                    SUM(uc.fic) AS soma_fic,
                    SUM(uc.dic_horas) / NULLIF(MAX(den.quantidade_ucs), 0) AS dec_horas,
                    SUM(uc.fic) / NULLIF(MAX(den.quantidade_ucs), 0) AS fec,
                    MAX(uc.dmic_horas) AS dmic_max_horas,
                    MAX(uc.fonte_denominador) AS fonte_denominador
                    ,MAX(uc.filtro_faturamento) AS filtro_faturamento
                    ,MAX(uc.regra_liquido) AS regra_liquido
                FROM indicadores_uc AS uc
                LEFT JOIN denominadores AS den
                  ON uc.cenario = den.cenario
                 AND uc.regional_origem = den.regional_origem
                GROUP BY uc.cenario, uc.anomes, uc.regional_origem
            ),
            copel AS (
                SELECT
                    cenario,
                    anomes,
                    'COPEL' AS nivel,
                    'COPEL' AS regional_origem,
                    'TODOS' AS cod_conjunto_aneel,
                    SUM(quantidade_ucs) AS quantidade_ucs,
                    SUM(soma_dic_horas) AS soma_dic_horas,
                    SUM(soma_fic) AS soma_fic,
                    SUM(soma_dic_horas) / NULLIF(SUM(quantidade_ucs), 0) AS dec_horas,
                    SUM(soma_fic) / NULLIF(SUM(quantidade_ucs), 0) AS fec,
                    MAX(dmic_max_horas) AS dmic_max_horas,
                    MAX(fonte_denominador) AS fonte_denominador
                    ,MAX(filtro_faturamento) AS filtro_faturamento
                    ,MAX(regra_liquido) AS regra_liquido
                FROM regional
                GROUP BY cenario, anomes
            ),
            conjunto AS (
                SELECT
                    cenario,
                    anomes,
                    'CONJUNTO' AS nivel,
                    regional_origem,
                    cod_conjunto_aneel,
                    COUNT(DISTINCT num_uc_uci) AS quantidade_ucs,
                    SUM(dic_horas) AS soma_dic_horas,
                    SUM(fic) AS soma_fic,
                    SUM(dic_horas) / NULLIF(COUNT(DISTINCT num_uc_uci), 0) AS dec_horas,
                    SUM(fic) / NULLIF(COUNT(DISTINCT num_uc_uci), 0) AS fec,
                    MAX(dmic_horas) AS dmic_max_horas,
                    MAX(fonte_denominador) AS fonte_denominador
                    ,MAX(filtro_faturamento) AS filtro_faturamento
                    ,MAX(regra_liquido) AS regra_liquido
                FROM indicadores_uc
                GROUP BY cenario, anomes, regional_origem, cod_conjunto_aneel
            )
            SELECT *, ? AS gerado_em FROM copel
            UNION ALL
            SELECT *, ? AS gerado_em FROM regional
            UNION ALL
            SELECT *, ? AS gerado_em FROM conjunto
            """,
            [gerado_em, gerado_em, gerado_em],
        )
        connection.execute(
            "COPY indicadores_agregado TO ? (FORMAT PARQUET)",
            [str(mart_agregado)],
        )

    def _materializar_comparativo(
        self,
        connection: duckdb.DuckDBPyConnection,
        mart_comparativo: Path,
    ) -> None:
        gerado_em = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            CREATE TEMP TABLE indicadores_comparativo AS
            SELECT
                COALESCE(antes.anomes, depois.anomes) AS anomes,
                COALESCE(antes.nivel, depois.nivel) AS nivel,
                COALESCE(antes.regional_origem, depois.regional_origem) AS regional_origem,
                COALESCE(antes.cod_conjunto_aneel, depois.cod_conjunto_aneel) AS cod_conjunto_aneel,
                COALESCE(depois.quantidade_ucs, antes.quantidade_ucs) AS quantidade_ucs,
                antes.dec_horas AS dec_antes,
                depois.dec_horas AS dec_depois,
                depois.dec_horas - antes.dec_horas AS dec_delta,
                CASE
                    WHEN antes.dec_horas IS NULL OR antes.dec_horas = 0 THEN NULL
                    ELSE ((depois.dec_horas - antes.dec_horas) / antes.dec_horas) * 100
                END AS dec_delta_percentual,
                antes.fec AS fec_antes,
                depois.fec AS fec_depois,
                depois.fec - antes.fec AS fec_delta,
                CASE
                    WHEN antes.fec IS NULL OR antes.fec = 0 THEN NULL
                    ELSE ((depois.fec - antes.fec) / antes.fec) * 100
                END AS fec_delta_percentual,
                antes.dmic_max_horas AS dmic_max_antes,
                depois.dmic_max_horas AS dmic_max_depois,
                depois.dmic_max_horas - antes.dmic_max_horas AS dmic_delta,
                COALESCE(depois.fonte_denominador, antes.fonte_denominador) AS fonte_denominador,
                COALESCE(depois.filtro_faturamento, antes.filtro_faturamento) AS filtro_faturamento,
                COALESCE(depois.regra_liquido, antes.regra_liquido) AS regra_liquido,
                ? AS gerado_em
            FROM indicadores_agregado AS antes
            FULL OUTER JOIN indicadores_agregado AS depois
              ON antes.nivel = depois.nivel
             AND antes.regional_origem = depois.regional_origem
             AND antes.cod_conjunto_aneel = depois.cod_conjunto_aneel
             AND antes.anomes = depois.anomes
             AND antes.cenario = 'antes'
             AND depois.cenario = 'depois'
            WHERE COALESCE(antes.cenario, 'antes') = 'antes'
              AND COALESCE(depois.cenario, 'depois') = 'depois'
            """,
            [gerado_em],
        )
        connection.execute(
            "COPY indicadores_comparativo TO ? (FORMAT PARQUET)",
            [str(mart_comparativo)],
        )

    def _first_existing(self, columns: list[str], candidates: list[str]) -> str | None:
        normalized = {column.upper(): column for column in columns}
        for candidate in candidates:
            if candidate.upper() in normalized:
                return normalized[candidate.upper()]
        return None

    def _primeiro_arquivo_existente(self, paths: list[Path]) -> Path | None:
        for path in paths:
            if path.exists():
                return path
        return None
