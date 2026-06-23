from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INDICADORES_DIR = PROJECT_ROOT / "data" / "mart" / "indicadores"
IQS_MART_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "mart"
IQS_RAW_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "raw"


@dataclass(frozen=True)
class RessarcimentoResult:
    anomes: str
    origem_indicadores: Path
    origem_metas: Path
    origem_vrc: Path | None
    parquet: Path
    parquet_atual: Path
    total_registros: int
    total_ucs: int
    violacoes_antes: int
    violacoes_depois: int
    valor_estimado_antes: float | None
    valor_estimado_depois: float | None
    status_formula: str


class RessarcimentoService:
    def materializar(self, anomes: str) -> RessarcimentoResult:
        indicadores_uc = INDICADORES_DIR / f"indicadores_uc_{anomes}.parquet"
        if not indicadores_uc.exists():
            raise FileNotFoundError(
                f"Indicadores UC não encontrados: {indicadores_uc}. "
                f"Execute `python -m backend.scripts.materializar_indicadores_continuidade --anomes {anomes}`."
            )

        metas_uc = self._localizar_metas_uc(anomes)
        if metas_uc is None:
            raise FileNotFoundError(
                "Metas UC não encontradas. Esperado em data/external/iqs/raw ou mart com nomes como "
                f"metas_uc_{anomes}.parquet, metas_uc_{anomes[:4]}.parquet ou mart_metas_uc_{anomes}.parquet."
            )
        vrc_uc = self._localizar_vrc(anomes)

        INDICADORES_DIR.mkdir(parents=True, exist_ok=True)
        parquet = INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
        parquet_atual = INDICADORES_DIR / "indicadores_ressarcimento_ATUAL.parquet"

        with duckdb.connect(database=":memory:") as connection:
            meta_columns = self._columns(connection, metas_uc)
            mapping = self._mapear_colunas_metas(meta_columns)
            self._criar_metas_normalizadas(connection, metas_uc, mapping)
            self._criar_vrc_normalizado(connection, vrc_uc)
            self._criar_ressarcimento(connection, indicadores_uc, parquet, mapping)

            total_registros = connection.execute("SELECT COUNT(*) FROM ressarcimento").fetchone()[0]
            total_ucs = connection.execute(
                "SELECT COUNT(DISTINCT num_uc_uci) FROM ressarcimento"
            ).fetchone()[0]
            violacoes_antes = connection.execute(
                """
                SELECT COUNT(*)
                FROM ressarcimento
                WHERE cenario = 'antes'
                  AND possui_violacao
                """
            ).fetchone()[0]
            violacoes_depois = connection.execute(
                """
                SELECT COUNT(*)
                FROM ressarcimento
                WHERE cenario = 'depois'
                  AND possui_violacao
                """
            ).fetchone()[0]
            valores = connection.execute(
                """
                SELECT
                    SUM(CASE WHEN cenario = 'antes' THEN valor_ressarcimento_estimado ELSE 0 END),
                    SUM(CASE WHEN cenario = 'depois' THEN valor_ressarcimento_estimado ELSE 0 END)
                FROM ressarcimento
                """
            ).fetchone()
            valor_estimado_antes = valores[0]
            valor_estimado_depois = valores[1]
            status_formula = connection.execute(
                "SELECT MAX(status_formula_ressarcimento) FROM ressarcimento"
            ).fetchone()[0]

            connection.execute(
                "COPY (SELECT * FROM ressarcimento) TO ? (FORMAT PARQUET)",
                [str(parquet_atual)],
            )

        return RessarcimentoResult(
            anomes=anomes,
            origem_indicadores=indicadores_uc,
            origem_metas=metas_uc,
            origem_vrc=vrc_uc,
            parquet=parquet,
            parquet_atual=parquet_atual,
            total_registros=total_registros,
            total_ucs=total_ucs,
            violacoes_antes=violacoes_antes,
            violacoes_depois=violacoes_depois,
            valor_estimado_antes=valor_estimado_antes,
            valor_estimado_depois=valor_estimado_depois,
            status_formula=status_formula,
        )

    def resumo(self, anomes: str) -> dict[str, Any]:
        parquet = INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
        if not parquet.exists():
            return {
                "anomes": anomes,
                "arquivo": str(parquet),
                "status": "pendente",
                "total_registros": 0,
                "total_ucs": 0,
                "por_cenario": [],
                "por_regional": [],
            }

        with duckdb.connect(database=":memory:") as connection:
            total_registros = connection.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(parquet)],
            ).fetchone()[0]
            total_ucs = connection.execute(
                "SELECT COUNT(DISTINCT num_uc_uci) FROM read_parquet(?)",
                [str(parquet)],
            ).fetchone()[0]
            por_cenario = self._rows_to_dicts(
                ["cenario", "ucs_com_violacao", "valor_estimado", "excedente_dic_horas", "excedente_fic", "excedente_dmic_horas"],
                connection.execute(
                    """
                    SELECT
                        cenario,
                        COUNT(DISTINCT CASE WHEN possui_violacao THEN num_uc_uci END) AS ucs_com_violacao,
                        SUM(valor_ressarcimento_estimado) AS valor_estimado,
                        SUM(excedente_dic_horas) AS excedente_dic_horas,
                        SUM(excedente_fic) AS excedente_fic,
                        SUM(excedente_dmic_horas) AS excedente_dmic_horas
                    FROM read_parquet(?)
                    GROUP BY cenario
                    ORDER BY cenario
                    """,
                    [str(parquet)],
                ).fetchall(),
            )
            por_regional = self._rows_to_dicts(
                ["cenario", "regional_origem", "ucs_com_violacao", "valor_estimado"],
                connection.execute(
                    """
                    SELECT
                        cenario,
                        regional_origem,
                        COUNT(DISTINCT CASE WHEN possui_violacao THEN num_uc_uci END) AS ucs_com_violacao,
                        SUM(valor_ressarcimento_estimado) AS valor_estimado
                    FROM read_parquet(?)
                    GROUP BY cenario, regional_origem
                    ORDER BY cenario, regional_origem
                    """,
                    [str(parquet)],
                ).fetchall(),
            )
            status_formula = connection.execute(
                "SELECT MAX(status_formula_ressarcimento) FROM read_parquet(?)",
                [str(parquet)],
            ).fetchone()[0]

        return {
            "anomes": anomes,
            "arquivo": str(parquet),
            "status": "processado",
            "total_registros": total_registros,
            "total_ucs": total_ucs,
            "status_formula": status_formula,
            "por_cenario": por_cenario,
            "por_regional": por_regional,
        }

    def dados(
        self,
        anomes: str,
        limit: int = 100,
        offset: int = 0,
        apenas_violacao: bool = True,
    ) -> dict[str, Any]:
        parquet = INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
        if not parquet.exists():
            raise FileNotFoundError(f"Ressarcimento não materializado: {parquet}")

        where_sql = "WHERE possui_violacao" if apenas_violacao else ""
        with duckdb.connect(database=":memory:") as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM read_parquet(?) {where_sql}",
                [str(parquet)],
            ).fetchone()[0]
            result = connection.execute(
                f"""
                SELECT *
                FROM read_parquet(?)
                {where_sql}
                ORDER BY cenario, regional_origem, valor_ressarcimento_estimado DESC NULLS LAST, num_uc_uci
                LIMIT ? OFFSET ?
                """,
                [str(parquet), limit, offset],
            )
            columns = [column[0] for column in result.description]
            rows = result.fetchall()

        return {
            "anomes": anomes,
            "arquivo": str(parquet),
            "limit": limit,
            "offset": offset,
            "total": total,
            "registros": self._rows_to_dicts(columns, rows),
        }

    def _localizar_metas_uc(self, anomes: str) -> Path | None:
        ano = anomes[:4]
        candidates = [
            IQS_MART_DIR / f"mart_metas_uc_{anomes}.parquet",
            IQS_MART_DIR / f"mart_metas_uc_{ano}.parquet",
            IQS_RAW_DIR / f"metas_uc_{anomes}.parquet",
            IQS_RAW_DIR / f"metas_uc_{ano}.parquet",
            IQS_RAW_DIR / f"IQS_METAS_UC_{ano}.parquet",
            IQS_RAW_DIR / f"iqs_metas_uc_{ano}.parquet",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _localizar_vrc(self, anomes: str) -> Path | None:
        candidates = [
            IQS_MART_DIR / f"mart_vrc_{anomes}.parquet",
            IQS_RAW_DIR / f"vrc_{anomes}.parquet",
            IQS_MART_DIR / "mart_vrc.parquet",
            IQS_RAW_DIR / "vrc.parquet",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _columns(self, connection: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
        return [
            row[0]
            for row in connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(path)],
            ).fetchall()
        ]

    def _mapear_colunas_metas(self, columns: list[str]) -> dict[str, str | None]:
        return {
            "uc": self._first_existing(
                columns,
                [
                    "UC",
                    "NUM_UC",
                    "NUM_UC_UCI",
                    "NUM_UC_HCAI",
                    "NUM_CONTA_CONTRATO",
                    "CONTA_CONTRATO",
                    "ISN_UC",
                    "COD_UC",
                    "ID_UC",
                    "U_C",
                ],
            ),
            "dic": self._first_existing(columns, ["META_DIC", "DIC_MENSAL", "LIMITE_DIC", "DIC_LIMITE", "DIC_META", "DIC"]),
            "fic": self._first_existing(columns, ["META_FIC", "FIC_MENSAL", "LIMITE_FIC", "FIC_LIMITE", "FIC_META", "FIC"]),
            "dmic": self._first_existing(columns, ["META_DMIC", "DMIC_MENSAL", "LIMITE_DMIC", "DMIC_LIMITE", "DMIC_META", "DMIC"]),
            "conjunto": self._first_existing(columns, ["COD_CONJUNTO_ANEEL", "COD_CONJTO_ELET_ANEEL_INTRP", "CONJUNTO"]),
            "ano": self._first_existing(columns, ["ANO_REF", "ANO", "ANO_REFERENCIA"]),
            "valor": self._first_existing(
                columns,
                ["VRC", "EUSD_MEDIO", "EUSD_MEDIA", "VALOR_EUSD", "VL_EUSD", "VALOR_REFERENCIA", "VL_REFERENCIA"],
            ),
        }

    def _criar_metas_normalizadas(
        self,
        connection: duckdb.DuckDBPyConnection,
        metas_uc: Path,
        mapping: dict[str, str | None],
    ) -> None:
        if not mapping["uc"]:
            raise ValueError("Não foi possível identificar a coluna de UC na base de metas.")

        dic_expr = self._numeric_expr(mapping["dic"])
        fic_expr = self._numeric_expr(mapping["fic"])
        dmic_expr = self._numeric_expr(mapping["dmic"])
        valor_expr = self._numeric_expr(mapping["valor"])
        conjunto_expr = f"MAX(CAST({mapping['conjunto']} AS VARCHAR))" if mapping["conjunto"] else "NULL::VARCHAR"
        ano_expr = f"MAX(CAST({mapping['ano']} AS VARCHAR))" if mapping["ano"] else "NULL::VARCHAR"

        connection.execute(
            f"""
            CREATE TEMP TABLE metas_uc AS
            SELECT
                CAST({mapping["uc"]} AS VARCHAR) AS num_uc_uci,
                {conjunto_expr} AS cod_conjunto_aneel_meta,
                {ano_expr} AS ano_ref_meta,
                MAX({dic_expr}) AS limite_dic_horas,
                MAX({fic_expr}) AS limite_fic,
                MAX({dmic_expr}) AS limite_dmic_horas,
                MAX({valor_expr}) AS valor_referencia_ressarcimento
            FROM read_parquet(?)
            GROUP BY CAST({mapping["uc"]} AS VARCHAR)
            """,
            [str(metas_uc)],
        )

    def _criar_vrc_normalizado(
        self,
        connection: duckdb.DuckDBPyConnection,
        vrc_uc: Path | None,
    ) -> None:
        if vrc_uc is None:
            connection.execute(
                """
                CREATE TEMP TABLE vrc_uc AS
                SELECT
                    NULL::VARCHAR AS num_uc_uci,
                    NULL::DOUBLE AS vrc
                WHERE FALSE
                """
            )
            return

        columns = self._columns(connection, vrc_uc)
        uc_col = self._first_existing(columns, ["ISN_UC", "UC", "NUM_UC", "NUM_UC_UCI", "NUM_UC_HCAI"])
        vrc_col = self._first_existing(columns, ["VRC", "VAL_BASE_CALC_COMPEN_UC", "VALOR_VRC"])
        cea_col = self._first_existing(columns, ["CEA", "NUM_CONJTO_ANEEL_FIXO_UC", "COD_CONJUNTO_ANEEL"])
        urb_rur_col = self._first_existing(columns, ["URB_RUR", "INDIC_LOCAL_TEC_UC"])
        grupo_tensao_col = self._first_existing(columns, ["COD_GRUPO_NIVEL_TENSAO_UC", "GRUPO_TENSAO"])
        nivel_tensao_col = self._first_existing(columns, ["COD_NIVEL_TENSAO_UC", "NIVEL_TENSAO"])
        if not uc_col or not vrc_col:
            connection.execute(
                """
                CREATE TEMP TABLE vrc_uc AS
                SELECT
                    NULL::VARCHAR AS num_uc_uci,
                    NULL::VARCHAR AS cea_vrc,
                    NULL::VARCHAR AS urb_rur,
                    NULL::VARCHAR AS cod_grupo_nivel_tensao_uc,
                    NULL::VARCHAR AS cod_nivel_tensao_uc,
                    NULL::DOUBLE AS vrc
                WHERE FALSE
                """
            )
            return

        cea_expr = f"MAX(CAST({cea_col} AS VARCHAR))" if cea_col else "NULL::VARCHAR"
        urb_rur_expr = f"MAX(CAST({urb_rur_col} AS VARCHAR))" if urb_rur_col else "NULL::VARCHAR"
        grupo_expr = f"MAX(CAST({grupo_tensao_col} AS VARCHAR))" if grupo_tensao_col else "NULL::VARCHAR"
        nivel_expr = f"MAX(CAST({nivel_tensao_col} AS VARCHAR))" if nivel_tensao_col else "NULL::VARCHAR"
        connection.execute(
            f"""
            CREATE TEMP TABLE vrc_uc AS
            SELECT
                CAST({uc_col} AS VARCHAR) AS num_uc_uci,
                {cea_expr} AS cea_vrc,
                {urb_rur_expr} AS urb_rur,
                {grupo_expr} AS cod_grupo_nivel_tensao_uc,
                {nivel_expr} AS cod_nivel_tensao_uc,
                MAX(TRY_CAST(REPLACE(CAST({vrc_col} AS VARCHAR), ',', '.') AS DOUBLE)) AS vrc
            FROM read_parquet(?)
            GROUP BY CAST({uc_col} AS VARCHAR)
            """,
            [str(vrc_uc)],
        )

    def _criar_ressarcimento(
        self,
        connection: duckdb.DuckDBPyConnection,
        indicadores_uc: Path,
        parquet: Path,
        mapping: dict[str, str | None],
    ) -> None:
        gerado_em = datetime.now().isoformat(timespec="seconds")
        possui_vrc = bool(connection.execute("SELECT COUNT(*) > 0 FROM vrc_uc").fetchone()[0])
        status_formula = (
            "ESTIMATIVA_OPERACIONAL_EXCEDENTE_X_VRC"
            if possui_vrc
            else (
                "ESTIMATIVA_OPERACIONAL_EXCEDENTE_X_VALOR_REFERENCIA"
                if mapping["valor"]
                else "SEM_VALOR_REFERENCIA_FORMULA_OFICIAL_PENDENTE"
            )
        )
        connection.execute(
            """
            CREATE TEMP TABLE indicadores_uc AS
            SELECT *
            FROM read_parquet(?)
            """,
            [str(indicadores_uc)],
        )
        connection.execute(
            """
            CREATE TEMP TABLE ressarcimento AS
            WITH base AS (
                SELECT
                    ind.cenario,
                    ind.anomes,
                    ind.regional_origem,
                    ind.cod_conjunto_aneel,
                    ind.num_posto_uci,
                    ind.num_uc_uci,
                    ind.dic_horas,
                    ind.fic,
                    ind.dmic_horas,
                    meta.limite_dic_horas,
                    meta.limite_fic,
                    meta.limite_dmic_horas,
                    meta.cod_conjunto_aneel_meta,
                    meta.ano_ref_meta,
                    vrc.cea_vrc,
                    vrc.urb_rur,
                    vrc.cod_grupo_nivel_tensao_uc,
                    vrc.cod_nivel_tensao_uc,
                    COALESCE(vrc.vrc, meta.valor_referencia_ressarcimento) AS valor_referencia_ressarcimento,
                    GREATEST(ind.dic_horas - meta.limite_dic_horas, 0) AS excedente_dic_horas,
                    GREATEST(ind.fic - meta.limite_fic, 0) AS excedente_fic,
                    GREATEST(ind.dmic_horas - meta.limite_dmic_horas, 0) AS excedente_dmic_horas,
                    CASE
                        WHEN vrc.cod_grupo_nivel_tensao_uc = 'A'
                         AND vrc.cod_nivel_tensao_uc IN ('1', '2', '3') THEN 108
                        WHEN vrc.cod_grupo_nivel_tensao_uc = 'A'
                         AND vrc.cod_nivel_tensao_uc IN ('3a', '3A', '4', 'S') THEN 40
                        WHEN vrc.cod_grupo_nivel_tensao_uc = 'B' THEN 34
                        ELSE 0
                    END AS kei,
                    ind.fonte_denominador,
                    ind.filtro_faturamento,
                    ind.regra_liquido
                FROM indicadores_uc AS ind
                LEFT JOIN metas_uc AS meta
                  ON ind.num_uc_uci = meta.num_uc_uci
                LEFT JOIN vrc_uc AS vrc
                  ON ind.num_uc_uci = vrc.num_uc_uci
            )
            SELECT
                *,
                COALESCE(excedente_dic_horas, 0) > 0 AS violou_dic,
                COALESCE(excedente_fic, 0) > 0 AS violou_fic,
                COALESCE(excedente_dmic_horas, 0) > 0 AS violou_dmic,
                COALESCE(excedente_dic_horas, 0) > 0
                    OR COALESCE(excedente_fic, 0) > 0
                    OR COALESCE(excedente_dmic_horas, 0) > 0 AS possui_violacao,
                CASE
                    WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                    WHEN COALESCE(limite_dic_horas, 0) <= 0 THEN 0
                    WHEN dic_horas > limite_dic_horas THEN valor_referencia_ressarcimento * (dic_horas / 730.0) * kei
                    ELSE 0
                END AS compensacao_dic,
                CASE
                    WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                    WHEN COALESCE(limite_fic, 0) <= 0 THEN 0
                    WHEN fic > limite_fic THEN valor_referencia_ressarcimento * (fic / 730.0) * kei
                    ELSE 0
                END AS compensacao_fic,
                CASE
                    WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                    WHEN COALESCE(limite_dmic_horas, 0) <= 0 THEN 0
                    WHEN dmic_horas > limite_dmic_horas THEN valor_referencia_ressarcimento * (dmic_horas / 730.0) * kei
                    ELSE 0
                END AS compensacao_dmic,
                GREATEST(
                    COALESCE(
                        CASE
                            WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                            WHEN COALESCE(limite_dic_horas, 0) <= 0 THEN 0
                            WHEN dic_horas > limite_dic_horas THEN valor_referencia_ressarcimento * (dic_horas / 730.0) * kei
                            ELSE 0
                        END,
                        0
                    ),
                    COALESCE(
                        CASE
                            WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                            WHEN COALESCE(limite_fic, 0) <= 0 THEN 0
                            WHEN fic > limite_fic THEN valor_referencia_ressarcimento * (fic / 730.0) * kei
                            ELSE 0
                        END,
                        0
                    ),
                    COALESCE(
                        CASE
                            WHEN valor_referencia_ressarcimento IS NULL THEN NULL
                            WHEN COALESCE(limite_dmic_horas, 0) <= 0 THEN 0
                            WHEN dmic_horas > limite_dmic_horas THEN valor_referencia_ressarcimento * (dmic_horas / 730.0) * kei
                            ELSE 0
                        END,
                        0
                    )
                ) AS valor_ressarcimento_estimado,
                ? AS status_formula_ressarcimento,
                ? AS gerado_em
            FROM base
            """,
            [status_formula, gerado_em],
        )
        connection.execute(
            "COPY ressarcimento TO ? (FORMAT PARQUET)",
            [str(parquet)],
        )

    def _numeric_expr(self, column: str | None) -> str:
        if not column:
            return "NULL::DOUBLE"
        return f"TRY_CAST(REPLACE(CAST({column} AS VARCHAR), ',', '.') AS DOUBLE)"

    def _first_existing(self, columns: list[str], candidates: list[str]) -> str | None:
        normalized = {column.upper(): column for column in columns}
        for candidate in candidates:
            if candidate.upper() in normalized:
                return normalized[candidate.upper()]
        return None

    def _rows_to_dicts(self, columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        return [dict(zip(columns, row, strict=False)) for row in rows]
