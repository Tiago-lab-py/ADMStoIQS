from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import oracledb
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

SQL_COMPONENTE = """
SELECT
    COD_COMP,
    DESC_COMP
FROM SOD.COMPONENTE
"""


def _carregar_env_local() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _first_env(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return default


def _init_oracle_client() -> None:
    lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", r"C:\instantclient_23_9")
    config_dir = os.getenv("ORACLE_CLIENT_CONFIG_DIR", r"C:\APL\Oracle12_32\12CR2\network\admin")
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir, config_dir=config_dir)
    except Exception:
        # Cliente pode ja estar inicializado no processo.
        pass


def criar_engine_oracle() -> Engine:
    _carregar_env_local()

    user = _first_env("IQSHML_USER", "IQSHML_UID", "ORACLE_USER", "ORACLE_UID")
    password = _first_env("IQSHML_PASSWORD", "IQSHML_PWD", "ORACLE_PASSWORD", "ORACLE_PWD")
    dsn = _first_env("IQSHML_DSN", "IQSHML_DB", "ORACLE_DSN", "ORACLE_DB", default="mira")

    if not user or not password:
        raise RuntimeError(
            "Credenciais ausentes. Defina no .env ou ambiente: "
            "IQSHML_USER/IQSHML_PASSWORD (ou aliases IQSHML_UID/IQSHML_PWD)."
        )
    return create_engine(f"oracle+oracledb://{user}:{password}@{dsn}")


def extrair_componentes(engine: Engine) -> pd.DataFrame:
    df = pd.read_sql(SQL_COMPONENTE, engine)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _salvar_saida(df: pd.DataFrame, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if suffix == ".parquet":
        try:
            df.to_parquet(path, index=False)
        except Exception as exc:
            raise RuntimeError(
                "Falha ao salvar parquet. Verifique se o engine (ex.: pyarrow) esta instalado."
            ) from exc
    elif suffix == ".csv":
        df.to_csv(path, index=False, encoding="utf-8")
    else:
        raise ValueError(f"Formato de saida nao suportado: {suffix}. Use .parquet ou .csv")

    return str(path)


def executar(output_path: Optional[str] = None) -> pd.DataFrame:
    _init_oracle_client()
    engine = criar_engine_oracle()
    df = extrair_componentes(engine)
    if output_path:
        _salvar_saida(df, output_path)
    return df


if __name__ == "__main__":
    out = os.getenv(
        "COMPONENTE_OUTPUT_PATH",
        os.getenv("COMPONENTE_OUTPUT_CSV", r"dados/raw/componentes_iqshml.parquet"),
    )
    df_componentes = executar(output_path=out)
    print(f"Extracao concluida | linhas={len(df_componentes)} | arquivo={out}")
