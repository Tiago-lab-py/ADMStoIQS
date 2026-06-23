from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IQS_RAW_DIR = PROJECT_ROOT / "data" / "external" / "iqs" / "raw"


def sql_literal(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compacta uc_faturada_hcai para a granularidade DISTINCT uc/faturado/regional."
    )
    parser.add_argument("--anomes", required=True, help="Competência da extração, exemplo 202605.")
    args = parser.parse_args()

    raw_path = IQS_RAW_DIR / f"uc_faturada_hcai_{args.anomes}.parquet"
    temp_path = IQS_RAW_DIR / f"uc_faturada_hcai_{args.anomes}.compactado.tmp.parquet"

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw não encontrado: {raw_path}")

    print("[IQS] Compactando UC faturada HCAI...")
    print(f"[IQS] Origem: {raw_path}")

    with duckdb.connect(database=":memory:") as connection:
        total_original = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(raw_path)],
        ).fetchone()[0]
        connection.execute(
            f"""
            COPY (
                SELECT DISTINCT
                    CAST(uc AS VARCHAR) AS uc,
                    CAST(faturado AS VARCHAR) AS faturado,
                    CAST(regional AS VARCHAR) AS regional
                FROM read_parquet({sql_literal(raw_path)})
            )
            TO {sql_literal(temp_path)} (FORMAT PARQUET)
            """
        )
        total_compactado = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(temp_path)],
        ).fetchone()[0]

    temp_path.replace(raw_path)

    print("[IQS] Compactação concluída.")
    print(f"[IQS] Linhas originais: {total_original}")
    print(f"[IQS] Linhas compactadas: {total_compactado}")
    print(f"[IQS] Arquivo atualizado: {raw_path}")


if __name__ == "__main__":
    main()
