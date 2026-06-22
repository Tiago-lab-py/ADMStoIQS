import argparse
import os
import unicodedata
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd


try:
    import polars as pl
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Polars nao esta disponivel. Instale com: py -m pip install polars") from exc


AREA_SUFFIXES = ("CSL", "LES", "NRO", "NRT", "OES")

DEFAULT_CONSUMIDORES = [
    {"regional": "CSL", "consumidores": 607891, "mes": 4},
    {"regional": "LES", "consumidores": 17781002, "mes": 4},
    {"regional": "NRO", "consumidores": 926116, "mes": 4},
    {"regional": "NRT", "consumidores": 950494, "mes": 4},
    {"regional": "OES", "consumidores": 1019621, "mes": 4},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apurador Polars FULL: le parquet em FULL e gera resumo Excel em FULL/output."
        )
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True, choices=range(1, 13))
    parser.add_argument("--full-root", default="FULL", help="Diretorio com arquivos parquet FULL.")
    parser.add_argument("--output-dir", default=None, help="Diretorio de saida. Padrao: FULL/output.")
    parser.add_argument("--consumidores-csv", default="consumidores.csv")
    parser.add_argument(
        "--uc-faturadas-path",
        default=os.path.join("data", "processed", "uc_faturadas.csv"),
        help="Arquivo CSV/Parquet com UCs faturadas (coluna UC_FATURADAS ou equivalente).",
    )
    return parser.parse_args()


def protocol_is_expurgo_expr(col_name: str) -> pl.Expr:
    return (
        pl.col(col_name)
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .is_in(["", "0"])
        .not_()
    )


def non_empty_expr(col_name: str) -> pl.Expr:
    return (
        pl.col(col_name)
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .ne("")
    )


def ensure_datetime(df: pl.DataFrame, col: str) -> pl.DataFrame:
    if col not in df.columns:
        return df.with_columns(pl.lit(None, dtype=pl.Datetime).alias(col))
    if df.schema[col] == pl.Datetime:
        return df
    s = pl.col(col).cast(pl.Utf8, strict=False).fill_null("").str.strip_chars()
    return df.with_columns(
        pl.coalesce(
            [
                s.str.strptime(pl.Datetime, format="%d/%m/%Y %H:%M:%S", strict=False),
                s.str.strptime(pl.Datetime, format="%Y-%m-%d %H:%M:%S", strict=False),
                s.str.strptime(pl.Datetime, strict=False),
            ]
        ).alias(col)
    )


def load_parquets(full_root: str, year: int, month: int) -> Tuple[pl.DataFrame, pl.DataFrame]:
    inter_path = os.path.join(full_root, f"df_interrupcao_{year}_{month:02d}.parquet")
    hcai_path = os.path.join(full_root, f"df_hcai_{year}_{month:02d}.parquet")

    if not os.path.exists(inter_path):
        raise FileNotFoundError(f"Arquivo nao encontrado: {inter_path}")
    if not os.path.exists(hcai_path):
        raise FileNotFoundError(f"Arquivo nao encontrado: {hcai_path}")

    return pl.read_parquet(inter_path), pl.read_parquet(hcai_path)


def ensure_origem_column(df: pl.DataFrame, fallback_cols: List[str]) -> pl.DataFrame:
    if "arquivo_origem" in df.columns:
        return df.with_columns(
            pl.col("arquivo_origem")
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .str.strip_chars()
            .alias("arquivo_origem")
        )

    expr = None
    for c in fallback_cols:
        if c in df.columns:
            candidate = pl.col(c).cast(pl.Utf8, strict=False).fill_null("").str.strip_chars()
            expr = candidate if expr is None else pl.coalesce([expr, candidate])
    if expr is None:
        expr = pl.lit("Copel")
    return df.with_columns(
        pl.when(expr.ne("")).then(expr).otherwise(pl.lit("Copel")).alias("arquivo_origem")
    )


def normalize_classification(df_interrupcao: pl.DataFrame, df_hcai: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame]:
    di = df_interrupcao
    if "classificacao" not in di.columns:
        if "TIPO_PROTOC_JUSTIF_INTRP" in di.columns:
            di = di.with_columns(
                pl.when(protocol_is_expurgo_expr("TIPO_PROTOC_JUSTIF_INTRP"))
                .then(pl.lit("Expurgo"))
                .otherwise(pl.lit("Liquido"))
                .alias("classificacao")
            )
        else:
            di = di.with_columns(pl.lit("Liquido").alias("classificacao"))

    dh = df_hcai
    if "is_expurgo" not in dh.columns:
        exp_uci = protocol_is_expurgo_expr("TIPO_PROTOC_JUSTIF_UCI") if "TIPO_PROTOC_JUSTIF_UCI" in dh.columns else pl.lit(False)
        exp_intrp = (
            protocol_is_expurgo_expr("TIPO_PROTOC_JUSTIF_INTRP")
            if "TIPO_PROTOC_JUSTIF_INTRP" in dh.columns
            else pl.lit(False)
        )
        dh = dh.with_columns((exp_uci | exp_intrp).alias("is_expurgo"))
    if "classificacao" not in dh.columns:
        dh = dh.with_columns(
            pl.when(pl.col("is_expurgo")).then(pl.lit("Expurgo")).otherwise(pl.lit("Liquido")).alias("classificacao")
        )

    if "is_area_i" not in dh.columns:
        if "COD_AREA_ELET_INTRP" in dh.columns:
            dh = dh.with_columns(
                pl.col("COD_AREA_ELET_INTRP")
                .cast(pl.Float64, strict=False)
                .le(6)
                .fill_null(False)
                .alias("is_area_i")
            )
        else:
            dh = dh.with_columns(pl.lit(False).alias("is_area_i"))

    if "NUM_MOTIVO_TRAT_DIF_UCI" in dh.columns:
        dh = dh.filter(
            ~(
                (pl.col("classificacao") == "Liquido")
                & non_empty_expr("NUM_MOTIVO_TRAT_DIF_UCI")
            )
        )

    return di, dh


def dedupe_hcai_key(df: pl.DataFrame) -> pl.DataFrame:
    key_cols = ["NUM_INTRP_UCI", "NUM_POSTO_UCI", "NUM_UC_UCI"]
    if not all(c in df.columns for c in key_cols):
        return df

    x = df
    if "NUM_INTRP_INIC_MANOBRA_UCI" in x.columns:
        x = x.with_columns(
            pl.col("NUM_INTRP_INIC_MANOBRA_UCI")
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .str.strip_chars()
            .alias("NUM_INTRP_INIC_MANOBRA_UCI")
        ).with_columns(
            pl.when(pl.col("NUM_INTRP_INIC_MANOBRA_UCI").ne(""))
            .then(pl.col("NUM_INTRP_INIC_MANOBRA_UCI"))
            .otherwise(
                pl.col("NUM_INTRP_UCI").cast(pl.Utf8, strict=False).fill_null("").str.strip_chars()
            )
            .alias("NUM_INTRP_UCI")
        )

    x = x.with_columns([pl.col(c).cast(pl.Utf8, strict=False).fill_null("").str.strip_chars().alias(c) for c in key_cols])
    valid = (
        pl.col("NUM_INTRP_UCI").ne("")
        & pl.col("NUM_POSTO_UCI").ne("")
        & pl.col("NUM_UC_UCI").ne("")
    )
    sort_cols: List[str] = []
    if "snapshot_ts" in x.columns:
        x = x.with_columns(pl.col("snapshot_ts").cast(pl.Utf8, strict=False).fill_null("").alias("snapshot_ts"))
        sort_cols.append("snapshot_ts")
    sort_cols.append("DATA_HORA_FIM_INTRP")
    if "arquivo_csv" in x.columns:
        sort_cols.append("arquivo_csv")

    keyed = x.filter(valid).sort(sort_cols).unique(subset=key_cols, keep="last")
    nokey = x.filter(~valid)
    return pl.concat([nokey, keyed], how="vertical_relaxed")


def merge_intervals_hcai(df_hcai: pl.DataFrame, by_origin: bool = True) -> pl.DataFrame:
    if df_hcai.height == 0:
        return df_hcai

    tmp = ensure_datetime(df_hcai, "DTHR_INICIO_INTRP_UC")
    tmp = ensure_datetime(tmp, "DATA_HORA_FIM_INTRP")
    tmp = dedupe_hcai_key(tmp)

    tmp = tmp.filter(
        pl.col("DTHR_INICIO_INTRP_UC").is_not_null()
        & pl.col("DATA_HORA_FIM_INTRP").is_not_null()
        & (pl.col("DATA_HORA_FIM_INTRP") >= pl.col("DTHR_INICIO_INTRP_UC"))
    )
    if tmp.height == 0:
        return tmp

    group_keys = ["NUM_UC_UCI"]
    sort_keys = ["NUM_UC_UCI", "DTHR_INICIO_INTRP_UC"]
    if by_origin:
        group_keys = ["arquivo_origem"] + group_keys
        sort_keys = ["arquivo_origem"] + sort_keys

    tmp = (
        tmp.sort(sort_keys)
        .with_columns(pl.col("DATA_HORA_FIM_INTRP").cum_max().over(group_keys).alias("max_fim_ate_agora"))
        .with_columns(pl.col("max_fim_ate_agora").shift(1).over(group_keys).alias("max_fim_anterior"))
        .with_columns(
            (
                pl.col("max_fim_anterior").is_null()
                | (pl.col("DTHR_INICIO_INTRP_UC") > pl.col("max_fim_anterior"))
            ).alias("is_novo_periodo")
        )
        .with_columns(
            pl.col("is_novo_periodo")
            .cast(pl.Int64)
            .cum_sum()
            .over(group_keys)
            .alias("periodo_id")
        )
    )

    out = (
        tmp.group_by(group_keys + ["periodo_id"])
        .agg(
            pl.col("DTHR_INICIO_INTRP_UC").min().alias("DTHR_INICIO_INTRP_UC"),
            pl.col("DATA_HORA_FIM_INTRP").max().alias("DATA_HORA_FIM_INTRP"),
            pl.col("SIGLA_REGIONAL").first().alias("SIGLA_REGIONAL"),
            pl.col("is_expurgo").max().alias("is_expurgo"),
            pl.col("is_area_i").max().alias("is_area_i"),
        )
    )

    if not by_origin:
        out = out.with_columns(pl.lit("Copel").alias("arquivo_origem"))

    out = out.with_columns(
        (
            (pl.col("DATA_HORA_FIM_INTRP") - pl.col("DTHR_INICIO_INTRP_UC")).dt.total_seconds() / 60.0
        )
        .clip(lower_bound=0.0)
        .alias("duracao_min")
    ).with_columns(
        (pl.col("duracao_min") / 60.0).alias("chi_individual"),
        pl.when(pl.col("duracao_min") >= 3).then(pl.lit("Longa")).otherwise(pl.lit("Curta")).alias("tipo_intrp"),
        pl.when(pl.col("is_expurgo")).then(pl.lit("Expurgo")).otherwise(pl.lit("Liquido")).alias("classificacao"),
    )
    return out


def load_consumidores(path: str, month: int) -> pl.DataFrame:
    def norm_col(name: str) -> str:
        txt = unicodedata.normalize("NFKD", str(name))
        txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
        return txt.strip().lower().replace(" ", "_")

    if path and os.path.exists(path):
        cons = pd.read_csv(path, sep=None, engine="python")
        rename_map: Dict[str, str] = {}
        for c in cons.columns:
            nc = norm_col(c)
            if nc in {"regional", "regiao", "sigla_regional", "arquivo_origem"}:
                rename_map[c] = "regional"
            elif nc in {"consumidores", "consumidor", "qtd_consumidores", "total_consumidores", "uc_total"}:
                rename_map[c] = "consumidores"
            elif nc in {"mes", "mes_referencia", "competencia_mes"}:
                rename_map[c] = "mes"
        cons = cons.rename(columns=rename_map)
        if "mes" not in cons.columns:
            cons["mes"] = month
        missing = [c for c in ["regional", "consumidores"] if c not in cons.columns]
        if missing:
            raise ValueError(
                f"CSV de consumidores invalido. Colunas esperadas: regional, consumidores, mes. Colunas encontradas: {list(cons.columns)}"
            )
    else:
        cons = pd.DataFrame(DEFAULT_CONSUMIDORES)

    cons["regional"] = cons["regional"].astype(str).str.strip().str.upper()
    cons["consumidores"] = pd.to_numeric(cons["consumidores"], errors="coerce")
    cons["mes"] = pd.to_numeric(cons["mes"], errors="coerce")
    cons_mes = cons[cons["mes"] == month].copy()
    if cons_mes.empty:
        cons_mes = cons.copy()
    return pl.from_pandas(cons_mes[["regional", "consumidores", "mes"]])


def load_uc_faturadas(path: str) -> pl.DataFrame:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo de UCs faturadas nao encontrado: {path}")

    lower = path.lower()
    if lower.endswith(".parquet"):
        ucf = pl.read_parquet(path)
    else:
        ucf = pl.read_csv(path, infer_schema_length=10000)

    aliases = {"UC_FATURADAS", "NUM_UC_HCAI", "NUM_UC_UCI", "UC", "NUM_UC"}
    col = next((c for c in ucf.columns if str(c).strip().upper() in aliases), None)
    if col is None:
        raise ValueError(
            f"Arquivo de UCs faturadas invalido: coluna esperada entre {sorted(aliases)}. "
            f"Colunas encontradas: {ucf.columns}"
        )

    return (
        ucf.select(
            pl.col(col)
            .cast(pl.Utf8, strict=False)
            .fill_null("")
            .str.strip_chars()
            .alias("NUM_UC_UCI")
        )
        .filter(pl.col("NUM_UC_UCI").ne(""))
        .unique(subset=["NUM_UC_UCI"])
    )


def filter_hcai_by_uc_faturadas(df_hcai: pl.DataFrame, uc_faturadas: pl.DataFrame) -> pl.DataFrame:
    if df_hcai.height == 0:
        return df_hcai
    if "NUM_UC_UCI" not in df_hcai.columns:
        return df_hcai
    return (
        df_hcai.with_columns(
            pl.col("NUM_UC_UCI").cast(pl.Utf8, strict=False).fill_null("").str.strip_chars().alias("NUM_UC_UCI")
        )
        .join(uc_faturadas, on="NUM_UC_UCI", how="inner")
    )


def aggregate_hcai_metrics(df_clean: pl.DataFrame) -> pl.DataFrame:
    if df_clean.height == 0:
        return pl.DataFrame(
            schema={
                "arquivo_origem": pl.Utf8,
                "classificacao": pl.Utf8,
                "CI": pl.Int64,
                "CHI": pl.Float64,
                "CI_longa": pl.Int64,
                "CHI_longa": pl.Float64,
                "CI_curta": pl.Int64,
                "CHI_curta": pl.Float64,
                "CIi_longa": pl.Int64,
                "CHIi_longa": pl.Float64,
            }
        )

    tmp = df_clean.with_columns(
        pl.lit(1).alias("CI"),
        pl.col("chi_individual").cast(pl.Float64).alias("CHI"),
        pl.when(pl.col("tipo_intrp") == "Longa").then(1).otherwise(0).alias("CI_longa"),
        pl.when(pl.col("tipo_intrp") == "Longa").then(pl.col("chi_individual")).otherwise(0.0).alias("CHI_longa"),
        pl.when(pl.col("tipo_intrp") == "Curta").then(1).otherwise(0).alias("CI_curta"),
        pl.when(pl.col("tipo_intrp") == "Curta").then(pl.col("chi_individual")).otherwise(0.0).alias("CHI_curta"),
        pl.when((pl.col("tipo_intrp") == "Longa") & pl.col("is_area_i")).then(1).otherwise(0).alias("CIi_longa"),
        pl.when((pl.col("tipo_intrp") == "Longa") & pl.col("is_area_i"))
        .then(pl.col("chi_individual"))
        .otherwise(0.0)
        .alias("CHIi_longa"),
    )

    return tmp.group_by(["arquivo_origem", "classificacao"]).agg(
        pl.col("CI").sum().alias("CI"),
        pl.col("CHI").sum().alias("CHI"),
        pl.col("CI_longa").sum().alias("CI_longa"),
        pl.col("CHI_longa").sum().alias("CHI_longa"),
        pl.col("CI_curta").sum().alias("CI_curta"),
        pl.col("CHI_curta").sum().alias("CHI_curta"),
        pl.col("CIi_longa").sum().alias("CIi_longa"),
        pl.col("CHIi_longa").sum().alias("CHIi_longa"),
    )


def build_summary(
    df_hcai_limpo: pl.DataFrame,
    df_hcai_percepcao: pl.DataFrame,
    df_interrupcao: pl.DataFrame,
    consumidores: pl.DataFrame,
) -> Tuple[pl.DataFrame, pl.DataFrame]:
    metrics_all = aggregate_hcai_metrics(df_hcai_limpo)
    metrics_copel = aggregate_hcai_metrics(df_hcai_percepcao)

    if metrics_all.height == 0:
        empty_cols = [
            "arquivo_origem",
            "classificacao",
            "CI",
            "CHI",
            "qtd_intrp_longas",
            "qtd_intrp_curtas",
            "qtd_ocorrencias_distintas",
            "qtd_interrupcoes_distintas",
            "consumidores",
            "mes",
            "FEC",
            "DEC",
            "FM_fec",
            "FM_dec",
            "FECi",
            "DECi",
        ]
        return pl.DataFrame({c: [] for c in empty_cols}), pl.DataFrame({c: [] for c in empty_cols})

    resumo = metrics_all.with_columns(
        pl.col("CI_longa").alias("qtd_intrp_longas"),
        pl.col("CI_curta").alias("qtd_intrp_curtas"),
    )

    if df_interrupcao.height > 0:
        base_intrp = df_interrupcao.group_by(["arquivo_origem", "classificacao"]).agg(
            pl.col("NUM_OCORRENCIA_ADMS").n_unique().alias("qtd_ocorrencias_distintas"),
            pl.col("PID").n_unique().alias("qtd_interrupcoes_distintas"),
        )
    else:
        base_intrp = pl.DataFrame(
            schema={
                "arquivo_origem": pl.Utf8,
                "classificacao": pl.Utf8,
                "qtd_ocorrencias_distintas": pl.Int64,
                "qtd_interrupcoes_distintas": pl.Int64,
            }
        )

    resumo = (
        resumo.join(base_intrp, on=["arquivo_origem", "classificacao"], how="left")
        .with_columns(
            pl.col("qtd_ocorrencias_distintas").fill_null(0),
            pl.col("qtd_interrupcoes_distintas").fill_null(0),
        )
        .join(consumidores.rename({"regional": "arquivo_origem"}), on="arquivo_origem", how="left")
        .with_columns(
            pl.col("consumidores").cast(pl.Float64, strict=False),
            pl.col("mes").cast(pl.Int64, strict=False),
        )
    )

    resumo = resumo.with_columns(
        pl.when(pl.col("consumidores") > 0).then(pl.col("CI_longa") / pl.col("consumidores")).otherwise(0.0).alias("FEC"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHI_longa") / pl.col("consumidores")).otherwise(0.0).alias("DEC"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CI_curta") / pl.col("consumidores")).otherwise(0.0).alias("FM_fec"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHI_curta") / pl.col("consumidores")).otherwise(0.0).alias("FM_dec"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CIi_longa") / pl.col("consumidores")).otherwise(0.0).alias("FECi"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHIi_longa") / pl.col("consumidores")).otherwise(0.0).alias("DECi"),
    )

    total_consumidores = float(consumidores["consumidores"].sum()) if consumidores.height > 0 else 0.0
    mes_total = int(consumidores["mes"].drop_nulls()[0]) if consumidores.height > 0 and consumidores["mes"].drop_nulls().len() > 0 else None

    copel = metrics_copel.with_columns(
        pl.col("CI_longa").alias("qtd_intrp_longas"),
        pl.col("CI_curta").alias("qtd_intrp_curtas"),
        pl.lit(total_consumidores).alias("consumidores"),
        pl.lit(mes_total).alias("mes"),
        pl.lit("Copel").alias("arquivo_origem"),
    )

    if df_interrupcao.height > 0:
        copel_dist = df_interrupcao.group_by("classificacao").agg(
            pl.col("NUM_OCORRENCIA_ADMS").n_unique().alias("qtd_ocorrencias_distintas"),
            pl.col("PID").n_unique().alias("qtd_interrupcoes_distintas"),
        )
        copel = copel.join(copel_dist, on="classificacao", how="left")
    copel = copel.with_columns(
        pl.col("qtd_ocorrencias_distintas").fill_null(0),
        pl.col("qtd_interrupcoes_distintas").fill_null(0),
    )
    copel = copel.with_columns(
        pl.when(pl.col("consumidores") > 0).then(pl.col("CI_longa") / pl.col("consumidores")).otherwise(0.0).alias("FEC"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHI_longa") / pl.col("consumidores")).otherwise(0.0).alias("DEC"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CI_curta") / pl.col("consumidores")).otherwise(0.0).alias("FM_fec"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHI_curta") / pl.col("consumidores")).otherwise(0.0).alias("FM_dec"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CIi_longa") / pl.col("consumidores")).otherwise(0.0).alias("FECi"),
        pl.when(pl.col("consumidores") > 0).then(pl.col("CHIi_longa") / pl.col("consumidores")).otherwise(0.0).alias("DECi"),
    )

    out_cols = [
        "arquivo_origem",
        "classificacao",
        "CI",
        "CHI",
        "qtd_intrp_longas",
        "qtd_intrp_curtas",
        "qtd_ocorrencias_distintas",
        "qtd_interrupcoes_distintas",
        "consumidores",
        "mes",
        "FEC",
        "DEC",
        "FM_fec",
        "FM_dec",
        "FECi",
        "DECi",
    ]
    resumo_std = resumo.select(out_cols)
    copel_std = copel.select(out_cols)
    resumo_final = pl.concat([resumo_std, copel_std], how="vertical_relaxed")
    copel = copel_std

    ordem_area = {a: i for i, a in enumerate(AREA_SUFFIXES)}
    ordem_area["Copel"] = 999
    ordem_class = {"Expurgo": 0, "Liquido": 1}

    resumo_final = resumo_final.with_columns(
        pl.col("arquivo_origem").replace_strict(ordem_area, default=998).alias("_ord_area"),
        pl.col("classificacao").replace_strict(ordem_class, default=9).alias("_ord_cls"),
    ).sort(["_ord_area", "_ord_cls"]).drop(["_ord_area", "_ord_cls"])

    copel = copel.with_columns(
        pl.col("classificacao").replace_strict(ordem_class, default=9).alias("_ord_cls")
    ).sort(["_ord_cls"]).drop(["_ord_cls"])

    return resumo_final, copel


def write_excel(
    xlsx_path: str,
    resumo_origem: pl.DataFrame,
    totais_copel: pl.DataFrame,
    consumidores: pl.DataFrame,
    metadata: Dict[str, Any],
) -> None:
    resumo_pd = resumo_origem.to_pandas()
    copel_pd = totais_copel.to_pandas()
    cons_pd = consumidores.to_pandas()
    meta_pd = pd.DataFrame([metadata])

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        resumo_pd.to_excel(writer, index=False, sheet_name="resumo_origem")
        copel_pd.to_excel(writer, index=False, sheet_name="copel")
        cons_pd.to_excel(writer, index=False, sheet_name="consumidores")
        meta_pd.to_excel(writer, index=False, sheet_name="metadata")
        for origem in sorted(resumo_pd["arquivo_origem"].dropna().unique()):
            aba = resumo_pd[resumo_pd["arquivo_origem"] == origem].copy()
            aba.to_excel(writer, index=False, sheet_name=str(origem)[:31])


def main() -> None:
    args = parse_args()
    full_root = args.full_root
    output_dir = args.output_dir or os.path.join(full_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    df_interrupcao, df_hcai = load_parquets(full_root, args.year, args.month)
    df_interrupcao = ensure_origem_column(df_interrupcao, ["SIGLA_REGIONAL", "regional"])
    df_hcai = ensure_origem_column(df_hcai, ["SIGLA_REGIONAL", "regional"])
    df_interrupcao, df_hcai = normalize_classification(df_interrupcao, df_hcai)
    df_hcai_limpo = merge_intervals_hcai(df_hcai, by_origin=True)
    df_hcai_percepcao = merge_intervals_hcai(df_hcai, by_origin=False)
    uc_faturadas = load_uc_faturadas(args.uc_faturadas_path)
    if uc_faturadas.height == 0:
        raise ValueError(f"Arquivo de UCs faturadas vazio: {args.uc_faturadas_path}")
    df_hcai_limpo = filter_hcai_by_uc_faturadas(df_hcai_limpo, uc_faturadas)
    df_hcai_percepcao = filter_hcai_by_uc_faturadas(df_hcai_percepcao, uc_faturadas)
    consumidores = load_consumidores(args.consumidores_csv, args.month)

    resumo_origem, totais_copel = build_summary(
        df_hcai_limpo=df_hcai_limpo,
        df_hcai_percepcao=df_hcai_percepcao,
        df_interrupcao=df_interrupcao,
        consumidores=consumidores,
    )

    excel_path = os.path.join(output_dir, f"resumo_ci_chi_{args.year}_{args.month:02d}.xlsx")
    metadata = {
        "ano": args.year,
        "mes": args.month,
        "full_root": full_root,
        "parquet_interrupcao": os.path.join(full_root, f"df_interrupcao_{args.year}_{args.month:02d}.parquet"),
        "parquet_hcai": os.path.join(full_root, f"df_hcai_{args.year}_{args.month:02d}.parquet"),
        "consumidores_csv": args.consumidores_csv,
        "uc_faturadas_path": args.uc_faturadas_path,
        "qtd_uc_faturadas": int(uc_faturadas.height),
        "engine": "polars",
    }
    write_excel(excel_path, resumo_origem, totais_copel, consumidores, metadata)

    ci_total = int(totais_copel["CI"].sum()) if totais_copel.height > 0 else 0
    chi_total = float(totais_copel["CHI"].sum()) if totais_copel.height > 0 else 0.0
    cons_total = float(consumidores["consumidores"].sum()) if consumidores.height > 0 else 0.0
    fec_total = (float(totais_copel["qtd_intrp_longas"].sum()) / cons_total) if cons_total > 0 else 0.0
    dec_num = float((totais_copel["DEC"] * totais_copel["consumidores"]).sum()) if totais_copel.height > 0 else 0.0
    dec_total = (dec_num / cons_total) if cons_total > 0 else 0.0

    print(f"Resumo Excel: {excel_path}")
    print(f"CI: {ci_total}")
    print(f"CHI: {chi_total:.6f}")
    print(f"FEC (longas >=3min): {fec_total:.12f}")
    print(f"DEC (longas >=3min): {dec_total:.12f}")
    print(f"UCs faturadas consideradas: {uc_faturadas.height}")


if __name__ == "__main__":
    main()
