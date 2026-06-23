from __future__ import annotations

import argparse

import duckdb

from backend.app.services.ressarcimento_service import RessarcimentoService


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista colunas e amostra do arquivo de metas UC localizado.")
    parser.add_argument("--anomes", required=True, help="Competência, exemplo 202605.")
    args = parser.parse_args()

    service = RessarcimentoService()
    metas_path = service._localizar_metas_uc(args.anomes)
    if metas_path is None:
        print("Metas UC não encontradas.")
        return

    print(f"Metas UC: {metas_path}")
    with duckdb.connect(database=":memory:") as connection:
        columns = connection.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(metas_path)],
        ).fetchall()
        print("Colunas:")
        for name, data_type, *_ in columns:
            print(f"- {name} ({data_type})")

        print("Amostra:")
        result = connection.execute(
            "SELECT * FROM read_parquet(?) LIMIT 5",
            [str(metas_path)],
        )
        names = [column[0] for column in result.description]
        for row in result.fetchall():
            print(dict(zip(names, row, strict=False)))


if __name__ == "__main__":
    main()
