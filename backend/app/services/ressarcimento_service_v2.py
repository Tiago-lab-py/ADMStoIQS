from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INDICADORES_DIR = PROJECT_ROOT / "data" / "mart" / "indicadores"
IQS_RAW_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "raw"
IQS_MART_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "mart"


@dataclass(frozen=True)
class RessarcimentoResult:
    anomes: str
    indicadores_uc: Path
    metas_uc: Path
    vrc: Path | None
    parquet: Path
    parquet_atual: Path
    total_registros: int
    total_ucs: int
    violacoes_antes: int
    violacoes_depois: int
    valor_estimado_antes: float
    valor_estimado_depois: float
    status_formula: str

    @property
    def origem_indicadores(self) -> Path:
        return self.indicadores_uc

    @property
    def origem_metas(self) -> Path:
        return self.metas_uc

    @property
    def origem_vrc(self) -> Path | None:
        return self.vrc

    @property
    def total_uc(self) -> int:
        return self.total_ucs

    @property
    def valor_total_antes(self) -> float:
        return self.valor_estimado_antes

    @property
    def valor_total_depois(self) -> float:
        return self.valor_estimado_depois


class RessarcimentoService:
    """Materializa compensação DIC/FIC/DMIC por UC.

    O realizado vem de `indicadores_uc_[anomes].parquet`, que já deve estar
    líquido: UC faturada, interrupção >= 3 minutos e protocolo regulatório.
    """

    def materializar(self, anomes: str) -> RessarcimentoResult:
        anomes = str(anomes)
        indicadores_uc = INDICADORES_DIR / f"indicadores_uc_{anomes}.parquet"
        metas_uc = self._localizar_metas_uc(anomes)
        vrc = self._localizar_vrc(anomes)
        parquet = INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
        parquet_atual = INDICADORES_DIR / "indicadores_ressarcimento_ATUAL.parquet"

        if not indicadores_uc.exists():
            raise FileNotFoundError(f"Indicadores UC não encontrado: {indicadores_uc}")
        if not metas_uc.exists():
            raise FileNotFoundError(f"Metas UC não encontrado: {metas_uc}")

        INDICADORES_DIR.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(database=":memory:") as connection:
            indicadores_cols = self._columns(connection, indicadores_uc)
            metas_cols = self._columns(connection, metas_uc)
            vrc_cols = self._columns(connection, vrc) if vrc and vrc.exists() else []

            self._criar_indicadores(connection, indicadores_uc, indicadores_cols)
            self._criar_metas(connection, metas_uc, metas_cols)
            self._criar_vrc(connection, vrc, vrc_cols)
            self._criar_saida(connection, parquet, anomes)
            self._copy_parquet(connection, parquet, parquet_atual)

            total = connection.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT uc),
                    SUM(CASE WHEN cenario = 'antes' AND possui_violacao THEN 1 ELSE 0 END),
                    SUM(CASE WHEN cenario = 'depois' AND possui_violacao THEN 1 ELSE 0 END),
                    SUM(CASE WHEN cenario = 'antes' THEN COALESCE(valor_ressarcimento_estimado, 0) ELSE 0 END),
                    SUM(CASE WHEN cenario = 'depois' THEN COALESCE(valor_ressarcimento_estimado, 0) ELSE 0 END)
                FROM read_parquet(?)
                """,
                [str(parquet)],
            ).fetchone()

        return RessarcimentoResult(
            anomes=anomes,
            indicadores_uc=indicadores_uc,
            metas_uc=metas_uc,
            vrc=vrc,
            parquet=parquet,
            parquet_atual=parquet_atual,
            total_registros=int(total[0] or 0),
            total_ucs=int(total[1] or 0),
            violacoes_antes=int(total[2] or 0),
            violacoes_depois=int(total[3] or 0),
            valor_estimado_antes=float(total[4] or 0),
            valor_estimado_depois=float(total[5] or 0),
            status_formula=(
                "ESTIMATIVA_PRODIST_VRC_KEI_MAIOR_COMPENSACAO_UC"
                if vrc and vrc.exists()
                else "SEM_VRC_FORMULA_FINANCEIRA_INCOMPLETA"
            ),
        )

    def resumo(self, anomes: str | None = None) -> dict[str, object]:
        parquet = (
            INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
            if anomes
            else INDICADORES_DIR / "indicadores_ressarcimento_ATUAL.parquet"
        )
        if not parquet.exists():
            return {"status": "pendente", "arquivo": str(parquet)}

        with duckdb.connect(database=":memory:") as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(DISTINCT uc),
                    SUM(CASE WHEN cenario = 'antes' AND possui_violacao THEN 1 ELSE 0 END),
                    SUM(CASE WHEN cenario = 'depois' AND possui_violacao THEN 1 ELSE 0 END),
                    SUM(CASE WHEN cenario = 'antes' THEN COALESCE(valor_ressarcimento_estimado, 0) ELSE 0 END),
                    SUM(CASE WHEN cenario = 'depois' THEN COALESCE(valor_ressarcimento_estimado, 0) ELSE 0 END)
                FROM read_parquet(?)
                """,
                [str(parquet)],
            ).fetchone()

        return {
            "status": "processado",
            "arquivo": str(parquet),
            "total_registros": int(row[0] or 0),
            "total_ucs": int(row[1] or 0),
            "violacoes_antes": int(row[2] or 0),
            "violacoes_depois": int(row[3] or 0),
            "valor_estimado_antes": float(row[4] or 0),
            "valor_estimado_depois": float(row[5] or 0),
            "status_formula": "ESTIMATIVA_PRODIST_VRC_KEI_MAIOR_COMPENSACAO_UC",
        }

    def dados(self, anomes: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, object]:
        parquet = (
            INDICADORES_DIR / f"indicadores_ressarcimento_{anomes}.parquet"
            if anomes
            else INDICADORES_DIR / "indicadores_ressarcimento_ATUAL.parquet"
        )
        if not parquet.exists():
            return {"arquivo": str(parquet), "total_retorno": 0, "registros": []}

        with duckdb.connect(database=":memory:") as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM read_parquet(?)
                ORDER BY valor_ressarcimento_estimado DESC NULLS LAST, uc
                LIMIT ? OFFSET ?
                """,
                [str(parquet), int(limit), int(offset)],
            ).fetchall()
            columns = [column[0] for column in connection.description]

        return {
            "arquivo": str(parquet),
            "total_retorno": len(rows),
            "registros": [dict(zip(columns, row, strict=False)) for row in rows],
        }

    def _criar_indicadores(self, connection: duckdb.DuckDBPyConnection, path: Path, columns: list[str]) -> None:
        uc = self._expr_first(columns, ["uc", "num_uc_uci", "NUM_UC_UCI", "isn_uc", "ISN_UC"])
        regional = self._expr_first(columns, ["regional", "regional_origem", "REGIONAL_ORIGEM"], default="'COPEL'")
        cenario = self._expr_first(columns, ["cenario", "fonte", "base"], default="'apuracao'")
        dic = self._number_expr(columns, ["dic_horas", "realizado_dic", "DIC_HORAS", "REALIZADO_DIC"])
        fic = self._number_expr(columns, ["fic", "fic_qtd", "realizado_fic", "FIC", "REALIZADO_FIC"])
        dmic = self._number_expr(columns, ["dmic_horas", "realizado_dmic", "DMIC_HORAS", "REALIZADO_DMIC"])

        if uc == "NULL":
            raise ValueError("Não foi possível identificar a coluna de UC nos indicadores.")

        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE indicadores_norm AS
            SELECT
                CAST({uc} AS VARCHAR) AS uc,
                CASE
                    WHEN lower(CAST({cenario} AS VARCHAR)) LIKE '%antes%' THEN 'antes'
                    WHEN lower(CAST({cenario} AS VARCHAR)) LIKE '%depois%' THEN 'depois'
                    WHEN lower(CAST({cenario} AS VARCHAR)) LIKE '%trat%' THEN 'depois'
                    ELSE lower(CAST({cenario} AS VARCHAR))
                END AS cenario,
                CAST({regional} AS VARCHAR) AS regional,
                COALESCE({dic}, 0)::DOUBLE AS dic_horas,
                COALESCE({fic}, 0)::DOUBLE AS fic,
                COALESCE({dmic}, 0)::DOUBLE AS dmic_horas
            FROM read_parquet({self._sql_literal(path)})
            """
        )

    def _criar_metas(self, connection: duckdb.DuckDBPyConnection, path: Path, columns: list[str]) -> None:
        uc = self._expr_first(columns, ["uc", "ISN_UC", "isn_uc", "NUM_UC"])
        meta_dic = self._number_expr(columns, ["META_DIC", "meta_dic", "limite_dic_horas"])
        meta_fic = self._number_expr(columns, ["META_FIC", "meta_fic", "limite_fic"])
        meta_dmic = self._number_expr(columns, ["META_DMIC", "meta_dmic", "limite_dmic_horas"])
        conjunto = self._expr_first(columns, ["COD_CONJUNTO_ANEEL", "cea", "CEA"], default="NULL")
        ano = self._expr_first(columns, ["ANO_REF", "ano_ref"], default="NULL")
        urb_rur = self._expr_first(columns, ["URB_RUR", "urb_rur"], default="NULL")
        grupo = self._expr_first(columns, ["COD_GRUPO_NTFN", "COD_GRUPO_NIVEL_TENSAO_UC", "grupo_tensao"], default="NULL")
        nivel = self._expr_first(columns, ["COD_NTFN", "COD_NIVEL_TENSAO_UC", "nivel_tensao"], default="NULL")

        if uc == "NULL":
            raise ValueError("Não foi possível identificar a coluna de UC na base de metas.")

        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE metas_norm AS
            SELECT
                CAST({uc} AS VARCHAR) AS uc,
                CAST({conjunto} AS VARCHAR) AS conjunto_aneel,
                CAST({ano} AS VARCHAR) AS ano_ref,
                CAST({urb_rur} AS VARCHAR) AS urb_rur_meta,
                CAST({grupo} AS VARCHAR) AS grupo_tensao_meta,
                CAST({nivel} AS VARCHAR) AS nivel_tensao_meta,
                {meta_dic}::DOUBLE AS limite_dic_horas,
                {meta_fic}::DOUBLE AS limite_fic,
                {meta_dmic}::DOUBLE AS limite_dmic_horas
            FROM read_parquet({self._sql_literal(path)})
            """
        )

    def _criar_vrc(self, connection: duckdb.DuckDBPyConnection, path: Path | None, columns: list[str]) -> None:
        if not path or not path.exists():
            connection.execute(
                """
                CREATE OR REPLACE TEMP TABLE vrc_norm AS
                SELECT
                    NULL::VARCHAR AS uc,
                    NULL::VARCHAR AS cea_vrc,
                    NULL::VARCHAR AS urb_rur,
                    NULL::VARCHAR AS grupo_tensao_vrc,
                    NULL::VARCHAR AS nivel_tensao_vrc,
                    NULL::DOUBLE AS vrc
                WHERE FALSE
                """
            )
            return

        uc = self._expr_first(columns, ["ISN_UC", "isn_uc", "uc", "NUM_UC"])
        cea = self._expr_first(columns, ["cea", "CEA", "NUM_CONJTO_ANEEL_FIXO_UC"], default="NULL")
        urb_rur = self._expr_first(columns, ["urb_rur", "URB_RUR", "INDIC_LOCAL_TEC_UC"], default="NULL")
        grupo = self._expr_first(columns, ["COD_GRUPO_NIVEL_TENSAO_UC", "grupo_tensao"], default="NULL")
        nivel = self._expr_first(columns, ["COD_NIVEL_TENSAO_UC", "nivel_tensao"], default="NULL")
        vrc = self._number_expr(columns, ["VRC", "vrc", "VAL_BASE_CALC_COMPEN_UC"])

        if uc == "NULL":
            raise ValueError("Não foi possível identificar a coluna de UC na base VRC.")

        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE vrc_norm AS
            SELECT
                CAST({uc} AS VARCHAR) AS uc,
                CAST({cea} AS VARCHAR) AS cea_vrc,
                CAST({urb_rur} AS VARCHAR) AS urb_rur,
                CAST({grupo} AS VARCHAR) AS grupo_tensao_vrc,
                CAST({nivel} AS VARCHAR) AS nivel_tensao_vrc,
                {vrc}::DOUBLE AS vrc
            FROM read_parquet({self._sql_literal(path)})
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY CAST({uc} AS VARCHAR)
                ORDER BY {vrc} DESC NULLS LAST
            ) = 1
            """
        )

    def _criar_saida(self, connection: duckdb.DuckDBPyConnection, parquet: Path, anomes: str) -> None:
        materializado_em = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            f"""
            COPY (
                WITH base AS (
                    SELECT
                        {self._sql_literal(anomes)} AS anomes,
                        ind.uc,
                        ind.cenario,
                        ind.regional,
                        COALESCE(vrc.cea_vrc, meta.conjunto_aneel) AS conjunto_aneel,
                        COALESCE(vrc.urb_rur, meta.urb_rur_meta) AS urb_rur,
                        COALESCE(vrc.grupo_tensao_vrc, meta.grupo_tensao_meta) AS grupo_tensao,
                        COALESCE(vrc.nivel_tensao_vrc, meta.nivel_tensao_meta) AS nivel_tensao,
                        COALESCE(vrc.vrc, 0) AS vrc,
                        meta.ano_ref,
                        ind.dic_horas,
                        ind.fic,
                        ind.dmic_horas,
                        meta.limite_dic_horas,
                        meta.limite_fic,
                        meta.limite_dmic_horas,
                        CASE
                            WHEN COALESCE(vrc.grupo_tensao_vrc, meta.grupo_tensao_meta) = 'A'
                             AND COALESCE(vrc.nivel_tensao_vrc, meta.nivel_tensao_meta) IN ('1', '2', '3')
                                THEN 108
                            WHEN COALESCE(vrc.grupo_tensao_vrc, meta.grupo_tensao_meta) = 'A'
                             AND COALESCE(vrc.nivel_tensao_vrc, meta.nivel_tensao_meta) IN ('3a', '3A', '4', 'S')
                                THEN 40
                            WHEN COALESCE(vrc.grupo_tensao_vrc, meta.grupo_tensao_meta) = 'B'
                                THEN 34
                            ELSE 0
                        END AS kei
                    FROM indicadores_norm ind
                    LEFT JOIN metas_norm meta ON meta.uc = ind.uc
                    LEFT JOIN vrc_norm vrc ON vrc.uc = ind.uc
                ),
                calculo AS (
                    SELECT
                        *,
                        dic_horas > COALESCE(limite_dic_horas, 999999999) AS viola_dic,
                        fic > COALESCE(limite_fic, 999999999) AS viola_fic,
                        dmic_horas > COALESCE(limite_dmic_horas, 999999999) AS viola_dmic,
                        CASE
                            WHEN dic_horas > COALESCE(limite_dic_horas, 999999999)
                                THEN vrc * (dic_horas / 730.0) * kei
                            ELSE 0
                        END AS compensacao_dic,
                        CASE
                            WHEN fic > COALESCE(limite_fic, 999999999)
                                THEN vrc * (fic / 730.0) * kei
                            ELSE 0
                        END AS compensacao_fic,
                        CASE
                            WHEN dmic_horas > COALESCE(limite_dmic_horas, 999999999)
                                THEN vrc * (dmic_horas / 730.0) * kei
                            ELSE 0
                        END AS compensacao_dmic
                    FROM base
                )
                SELECT
                    *,
                    viola_dic OR viola_fic OR viola_dmic AS possui_violacao,
                    GREATEST(compensacao_dic, compensacao_fic, compensacao_dmic) AS valor_ressarcimento_estimado,
                    {self._sql_literal("ESTIMATIVA_PRODIST_VRC_KEI_MAIOR_COMPENSACAO_UC")} AS status_formula,
                    {self._sql_literal("LIQUIDO_PRE_CALCULADO_EM_INDICADORES_UC")} AS criterio_liquido,
                    {self._sql_literal(materializado_em)} AS materializado_em
                FROM calculo
            ) TO {self._sql_literal(parquet)} (FORMAT PARQUET)
            """
        )

    def _localizar_metas_uc(self, anomes: str) -> Path:
        candidates = [
            IQS_RAW_DIR / f"metas_uc_{anomes}.parquet",
            IQS_MART_DIR / f"mart_metas_uc_{anomes}.parquet",
            IQS_RAW_DIR / "metas_uc.parquet",
            IQS_MART_DIR / "mart_metas_uc.parquet",
        ]
        return next((path for path in candidates if path.exists()), candidates[0])

    def _localizar_vrc(self, anomes: str) -> Path | None:
        candidates = [
            IQS_RAW_DIR / f"vrc_{anomes}.parquet",
            IQS_MART_DIR / f"mart_vrc_{anomes}.parquet",
            IQS_RAW_DIR / "vrc.parquet",
            IQS_MART_DIR / "mart_vrc.parquet",
        ]
        return next((path for path in candidates if path.exists()), candidates[0])

    def _columns(self, connection: duckdb.DuckDBPyConnection, path: Path | None) -> list[str]:
        if not path or not path.exists():
            return []
        rows = connection.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()
        return [str(row[0]) for row in rows]

    def _expr_first(self, columns: list[str], candidates: list[str], default: str = "NULL") -> str:
        lookup = {column.lower(): column for column in columns}
        for candidate in candidates:
            column = lookup.get(candidate.lower())
            if column:
                return f'"{column}"'
        return default

    def _number_expr(self, columns: list[str], candidates: list[str]) -> str:
        expr = self._expr_first(columns, candidates)
        if expr == "NULL":
            return "NULL"
        return f"try_cast(replace(CAST({expr} AS VARCHAR), ',', '.') AS DOUBLE)"

    def _copy_parquet(self, connection: duckdb.DuckDBPyConnection, source: Path, target: Path) -> None:
        connection.execute(
            f"""
            COPY (
                SELECT *
                FROM read_parquet({self._sql_literal(source)})
            ) TO {self._sql_literal(target)} (FORMAT PARQUET)
            """
        )

    def _sql_literal(self, value: str | Path) -> str:
        return "'" + str(value).replace("'", "''").replace("\\", "\\\\") + "'"
