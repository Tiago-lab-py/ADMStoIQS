import argparse
import glob
import os
import re
import shutil
from datetime import datetime
from time import perf_counter
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


AREA_SUFFIXES = ("CSL", "LES", "NRO", "NRT", "OES")
DT_FORMAT = "%d/%m/%Y %H:%M:%S"
FILE_RE = re.compile(r"^Interrupcoes_IQS_(\d{14})_(CSL|LES|NRO|NRT|OES)\.CSV$", re.IGNORECASE)

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

COLS_HCAI = [
    "PID_INTRP_UCI",
    "NUM_INTRP_UCI",
    "NUM_POSTO_UCI",
    "NUM_UC_UCI",
    "TIPO_SIT_UC_UCI",
    "DTHR_INICIO_INTRP_UC",
    "NUM_INTRP_INIC_MANOBRA_UCI",
    "NUM_MOTIVO_TRAT_DIF_UCI",
    "UC_ACESSANTE",
    "SIGLA_REGIONAL",
    "NUM_PROTOC_JUSTIF_RESP_UCI",
    "TIPO_PROTOC_JUSTIF_UCI",
    "PID_PIN",
    "INDIC_PROCES_IND_PIN",
    "INDIC_SIT_PROCES_INDIC_UCI",
    "DATA_HORA_FIM_INTRP",
    "PID_POSTO_PIN",
    "COD_AREA_ELET_INTRP",
]

EXTRA_REQUIRED = ["TIPO_PROTOC_JUSTIF_INTRP"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consolida arquivos Interrupcoes_IQS do backup, "
            "copia os mais recentes para data/raw e grava parquets em data/processed."
        )
    )
    parser.add_argument("--year", type=int, required=True, help="Ano de apuracao (ex: 2026)")
    parser.add_argument("--month", type=int, required=True, choices=range(1, 13), help="Mes de apuracao (1-12)")
    parser.add_argument(
        "--source-dir",
        default=r"P:\Common\IQS\ADMS\Backup",
        help="Pasta de origem dos CSVs historicos",
    )
    parser.add_argument(
        "--data-root",
        default="data",
        help="Raiz de dados local (sera criado data/raw, data/processed, data/output)",
    )
    parser.add_argument(
        "--use-local-raw",
        action="store_true",
        help="Nao copia do source-dir; usa os CSVs ja existentes em data/raw/YYYY-MM",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduz mensagens de progresso",
    )
    return parser.parse_args()


def log(msg: str, quiet: bool = False) -> None:
    if quiet:
        return
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def parse_file_info(path: str) -> Optional[Tuple[str, str]]:
    name = os.path.basename(path)
    m = FILE_RE.match(name)
    if not m:
        return None
    ts_txt, area = m.groups()
    # Alguns arquivos podem vir com segundo fora de 0..59 no nome.
    # Para escolha do "mais recente", a ordenacao lexicografica do carimbo
    # YYYYMMDDHHMMSS funciona e evita erro de parse.
    return ts_txt, area.upper()


def ensure_dirs(data_root: str, year: int, month: int) -> Tuple[str, str, str]:
    month_tag = f"{year}-{month:02d}"
    raw_dir = os.path.join(data_root, "raw", month_tag)
    processed_dir = os.path.join(data_root, "processed")
    output_dir = os.path.join(data_root, "output")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    return raw_dir, processed_dir, output_dir


def list_month_files(source_dir: str, year: int, month: int) -> List[Tuple[str, str, str]]:
    pattern = os.path.join(source_dir, "Interrupcoes_IQS_*_*.CSV")
    ym = f"{year:04d}{month:02d}"
    rows: List[Tuple[str, str, str]] = []
    for path in glob.glob(pattern):
        info = parse_file_info(path)
        if info is None:
            continue
        ts_txt, area = info
        if ts_txt.startswith(ym):
            rows.append((ts_txt, area, path))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    return rows


def sync_month_to_raw(source_dir: str, raw_dir: str, year: int, month: int) -> List[Tuple[str, str, str]]:
    chosen = list_month_files(source_dir, year, month)
    copied: List[Tuple[str, str, str]] = []
    for ts_txt, area, src in chosen:
        dst = os.path.join(raw_dir, os.path.basename(src))
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copy2(src, dst)
        copied.append((ts_txt, area, dst))
    return copied


def month_files_from_raw(raw_dir: str, year: int, month: int) -> List[Tuple[str, str, str]]:
    pattern = os.path.join(raw_dir, "Interrupcoes_IQS_*_*.CSV")
    ym = f"{year:04d}{month:02d}"
    rows: List[Tuple[str, str, str]] = []
    for path in glob.glob(pattern):
        info = parse_file_info(path)
        if info is None:
            continue
        ts_txt, area = info
        if ts_txt.startswith(ym):
            rows.append((ts_txt, area, path))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    return rows


def read_area_raw(path: str, area: str, ts_txt: str, needed_cols: List[str]) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="|",
        encoding="latin-1",
        dtype=str,
        usecols=lambda c: c in needed_cols,
        low_memory=False,
    )
    df["arquivo_origem"] = area
    df["snapshot_ts"] = ts_txt
    df["arquivo_csv"] = os.path.basename(path)
    return df


def dedupe_hcai_latest(df: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["NUM_INTRP_UCI", "NUM_POSTO_UCI", "NUM_UC_UCI"]
    if df.empty or not all(c in df.columns for c in key_cols):
        return df

    out = df.copy()
    out["_seq"] = np.arange(len(out))
    out = out.sort_values(["snapshot_ts", "_seq"])

    valid_key = pd.Series(True, index=out.index)
    for c in key_cols:
        valid_key &= out[c].astype(str).str.strip().ne("")
        valid_key &= out[c].notna()

    base_valid = out[valid_key]
    base_other = out[~valid_key]
    base_valid = base_valid.drop_duplicates(subset=key_cols, keep="last")

    out = pd.concat([base_other, base_valid], ignore_index=True)
    out = out.sort_values(["snapshot_ts", "_seq"]).drop(columns=["_seq"])
    return out


def dedupe_interrupcao_latest(df: pd.DataFrame) -> pd.DataFrame:
    key_col = "PID"
    if df.empty or key_col not in df.columns:
        return df

    out = df.copy()
    out["_seq"] = np.arange(len(out))
    out = out.sort_values(["snapshot_ts", "_seq"])

    valid_key = out[key_col].astype(str).str.strip().ne("") & out[key_col].notna()
    base_valid = out[valid_key].drop_duplicates(subset=[key_col], keep="last")
    base_other = out[~valid_key]

    out = pd.concat([base_other, base_valid], ignore_index=True)
    out = out.sort_values(["snapshot_ts", "_seq"]).drop(columns=["_seq"])
    return out


def build_dataframes(
    file_rows: List[Tuple[str, str, str]],
    progress_cb=None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    needed_union = sorted(set(COLS_INTERRUPCAO + COLS_HCAI + EXTRA_REQUIRED))
    inter_frames: List[pd.DataFrame] = []
    hcai_frames: List[pd.DataFrame] = []

    total = len(file_rows)
    for idx, (ts_txt, area, path) in enumerate(file_rows, start=1):
        if progress_cb is not None:
            progress_cb(idx, total, ts_txt, area, path)
        raw = read_area_raw(path, area, ts_txt, needed_union)
        cols_inter = [c for c in COLS_INTERRUPCAO if c in raw.columns]
        cols_hcai = [c for c in COLS_HCAI if c in raw.columns]

        inter_frames.append(raw[cols_inter + ["arquivo_origem", "snapshot_ts", "arquivo_csv"]].copy())

        hcai_keep = cols_hcai + ["arquivo_origem", "snapshot_ts", "arquivo_csv"]
        if "TIPO_PROTOC_JUSTIF_INTRP" in raw.columns and "TIPO_PROTOC_JUSTIF_INTRP" not in hcai_keep:
            hcai_keep.append("TIPO_PROTOC_JUSTIF_INTRP")
        hcai_frames.append(raw[hcai_keep].copy())

    df_interrupcao = pd.concat(inter_frames, ignore_index=True) if inter_frames else pd.DataFrame()
    df_hcai = pd.concat(hcai_frames, ignore_index=True) if hcai_frames else pd.DataFrame()
    df_interrupcao = dedupe_interrupcao_latest(df_interrupcao)
    df_hcai = dedupe_hcai_latest(df_hcai)
    return df_interrupcao, df_hcai


def to_number(series: pd.Series) -> pd.Series:
    s = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .replace({"": None, "nan": None, "None": None})
    )
    return pd.to_numeric(s, errors="coerce")


def process_df_interrupcao(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    out["DATA_HORA_INIC_INTRP"] = pd.to_datetime(
        out["DATA_HORA_INIC_INTRP"].astype(str).str.strip(),
        format=DT_FORMAT,
        errors="coerce",
    )
    out["DATA_HORA_FIM_INTRP"] = pd.to_datetime(
        out["DATA_HORA_FIM_INTRP"].astype(str).str.strip(),
        format=DT_FORMAT,
        errors="coerce",
    )
    out["CONS_INTRP"] = to_number(out["CONS_INTRP"])
    out["duracao_horas"] = (
        out["DATA_HORA_FIM_INTRP"] - out["DATA_HORA_INIC_INTRP"]
    ).dt.total_seconds() / 3600.0
    out["CHI"] = out["CONS_INTRP"] * out["duracao_horas"]
    out["NUM_OCORRENCIA_ADMS"] = out["NUM_OCORRENCIA_ADMS"].astype(str).str.strip().replace({"": np.nan})
    out["PID"] = out["PID"].astype(str).str.strip().replace({"": np.nan})

    valid = (
        out["DATA_HORA_INIC_INTRP"].notna()
        & out["DATA_HORA_FIM_INTRP"].notna()
        & (out["DATA_HORA_FIM_INTRP"] >= out["DATA_HORA_INIC_INTRP"])
        & out["CONS_INTRP"].notna()
        & (out["CONS_INTRP"] >= 0)
    )
    valid &= out["DATA_HORA_INIC_INTRP"].dt.year.eq(year)
    valid &= out["DATA_HORA_INIC_INTRP"].dt.month.eq(month)
    return out[valid].copy()


def process_df_hcai(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    if "COD_AREA_ELET_INTRP" not in out.columns:
        out["COD_AREA_ELET_INTRP"] = np.nan
    out["NUM_UC_UCI"] = out["NUM_UC_UCI"].astype(str).str.strip()
    out["DTHR_INICIO_INTRP_UC"] = pd.to_datetime(
        out["DTHR_INICIO_INTRP_UC"].astype(str).str.strip(),
        format=DT_FORMAT,
        errors="coerce",
    )
    out["DATA_HORA_FIM_INTRP"] = pd.to_datetime(
        out["DATA_HORA_FIM_INTRP"].astype(str).str.strip(),
        format=DT_FORMAT,
        errors="coerce",
    )

    valid = (
        out["NUM_UC_UCI"].ne("")
        & out["DTHR_INICIO_INTRP_UC"].notna()
        & out["DATA_HORA_FIM_INTRP"].notna()
        & (out["DATA_HORA_FIM_INTRP"] >= out["DTHR_INICIO_INTRP_UC"])
    )
    valid &= out["DTHR_INICIO_INTRP_UC"].dt.year.eq(year)
    valid &= out["DTHR_INICIO_INTRP_UC"].dt.month.eq(month)
    return out[valid].copy()


def save_parquet(df: pd.DataFrame, path: str) -> None:
    try:
        df.to_parquet(path, index=False)
    except Exception as exc:
        raise RuntimeError(
            f"Falha ao gravar parquet em {path}. Instale 'pyarrow' (ou 'fastparquet'). Erro: {exc}"
        ) from exc


def write_manifest(path: str, file_rows: List[Tuple[str, str, str]], year: int, month: int) -> None:
    rows = []
    for ts_raw, area, csv_path in file_rows:
        ts_txt = (
            f"{ts_raw[0:4]}-{ts_raw[4:6]}-{ts_raw[6:8]} "
            f"{ts_raw[8:10]}:{ts_raw[10:12]}:{ts_raw[12:14]}"
        )
        rows.append(
            {
                "ano": year,
                "mes": month,
                "regional": area,
                "arquivo_csv": csv_path,
                "timestamp_arquivo": ts_txt,
                "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()
    t0 = perf_counter()

    raw_dir, processed_dir, output_dir = ensure_dirs(args.data_root, args.year, args.month)
    log(
        f"Iniciando consolidacao {args.year}-{args.month:02d} | data-root: {args.data_root}",
        quiet=args.quiet,
    )

    if args.use_local_raw:
        log(f"Lendo CSVs ja existentes em: {raw_dir}", quiet=args.quiet)
        file_rows = month_files_from_raw(raw_dir, args.year, args.month)
    else:
        log(f"Procurando arquivos no backup: {args.source_dir}", quiet=args.quiet)
        file_rows = sync_month_to_raw(args.source_dir, raw_dir, args.year, args.month)
        log(f"Sincronizacao para raw concluida: {len(file_rows)} arquivo(s)", quiet=args.quiet)

    if not file_rows:
        print("Nenhum arquivo Interrupcoes_IQS encontrado para consolidar.")
        return

    log(f"Leitura dos CSVs iniciada: {len(file_rows)} arquivo(s) do mes", quiet=args.quiet)

    def _progress(idx: int, total: int, ts_txt: str, area: str, path: str) -> None:
        # Mostra cada 5 arquivos (e sempre no primeiro/ultimo) para nao poluir muito.
        if args.quiet:
            return
        if idx == 1 or idx == total or idx % 5 == 0:
            nome = os.path.basename(path)
            log(f"Lendo {idx}/{total} | {area} | {ts_txt} | {nome}", quiet=False)

    df_interrupcao_raw, df_hcai_raw = build_dataframes(file_rows, progress_cb=_progress)
    log(
        f"Leitura concluida | interrupcao_raw={len(df_interrupcao_raw)} | hcai_raw={len(df_hcai_raw)}",
        quiet=args.quiet,
    )

    df_interrupcao = process_df_interrupcao(df_interrupcao_raw, args.year, args.month)
    df_hcai = process_df_hcai(df_hcai_raw, args.year, args.month)
    log(
        f"Filtro {args.year}-{args.month:02d} concluido | interrupcao={len(df_interrupcao)} | hcai={len(df_hcai)}",
        quiet=args.quiet,
    )

    inter_path = os.path.join(processed_dir, f"df_interrupcao_{args.year}_{args.month:02d}.parquet")
    hcai_path = os.path.join(processed_dir, f"df_hcai_{args.year}_{args.month:02d}.parquet")
    log("Gravando parquets...", quiet=args.quiet)
    save_parquet(df_interrupcao, inter_path)
    save_parquet(df_hcai, hcai_path)

    manifest_path = os.path.join(output_dir, f"manifest_consolidacao_{args.year}_{args.month:02d}.csv")
    write_manifest(manifest_path, file_rows, args.year, args.month)
    log("Manifesto gerado.", quiet=args.quiet)

    latest_by_area: Dict[str, str] = {}
    for ts_txt, area, path in file_rows:
        latest_by_area[area] = f"{os.path.basename(path)} ({ts_txt})"

    print(f"Arquivos do mes lidos: {len(file_rows)}")
    print(f"Regionais consolidadas: {', '.join(sorted(latest_by_area.keys()))}")
    for area in AREA_SUFFIXES:
        if area in latest_by_area:
            print(f"- {area}: {latest_by_area[area]}")
    print(f"CSV local (raw): {raw_dir}")
    print(f"Parquet interrupcao: {inter_path}")
    print(f"Parquet hcai: {hcai_path}")
    print(f"Manifesto: {manifest_path}")
    log(f"Consolidacao finalizada em {perf_counter() - t0:.1f}s", quiet=args.quiet)


if __name__ == "__main__":
    main()
