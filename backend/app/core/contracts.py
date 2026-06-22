from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SOURCE_DIR = Path(r"P:\Common\IQS\ADMS\Backup")
SOURCE_CSV_PATTERN = "Interrupcoes_IQS_*.CSV"
SOURCE_CSV_ENCODINGS = ("utf-8", "cp1252", "latin-1")
MIN_ANOMES = "202604"
CSV_DELIMITER = "|"
PARQUET_COMPRESSION = "zstd"

DATA_DIR = PROJECT_ROOT / "data"
RAW_TEMP_DIR = DATA_DIR / "raw_temp"
RAW_TEMP_CONVERTED_DIR = RAW_TEMP_DIR / "converted_utf8"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = DATA_DIR / "logs"
EXPORTS_DIR = DATA_DIR / "exports"
DUCKDB_DIR = DATA_DIR / "duckdb"
DUCKDB_PATH = DUCKDB_DIR / "admstoiqs.duckdb"
DUCKDB_STAGING_DIR = DUCKDB_DIR / "staging"
MART_DIR = DATA_DIR / "mart"

LOG_LEITURA_CSV_PATH = LOGS_DIR / "log_leitura_csv.parquet"
LOG_ALTERACOES_PATH = LOGS_DIR / "log_alteracoes.parquet"
LOG_OMS_UNION_PATH = LOGS_DIR / "log_oms_union.parquet"

OMS_UNION_LEGACY_PARQUET_PATH = MART_DIR / "OMS_union.parquet"
OMS_UNION_CORRIGIDO_LEGACY_PARQUET_PATH = MART_DIR / "OMS_union_corrigido.parquet"
OMS_UNION_PARQUET_PATH = MART_DIR / "agrupamento_oms_UNION.parquet"
OMS_UNION_CORRIGIDO_PARQUET_PATH = MART_DIR / "agrupamento_oms_UNION_corrigido.parquet"

DEDUP_KEY_COLUMNS = ("NUM_INTRP_UCI", "NUM_POSTO_UCI", "NUM_UC_UCI")
UNION_ANOMES = "UNION"


def processed_parquet_path(anomes: str) -> Path:
    return PROCESSED_DIR / f"agrupamento_oms_{anomes}.parquet"


def export_csv_path(regional_origem: str, anomes: str, timestamp: str) -> Path:
    regional = regional_origem.upper().strip()
    return EXPORTS_DIR / f"agrupamento_oms_{regional}_{anomes}_{timestamp}.csv"


def ensure_data_directories() -> None:
    for path in (
        DATA_DIR,
        RAW_TEMP_DIR,
        RAW_TEMP_CONVERTED_DIR,
        PROCESSED_DIR,
        LOGS_DIR,
        EXPORTS_DIR,
        DUCKDB_DIR,
        DUCKDB_STAGING_DIR,
        MART_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
