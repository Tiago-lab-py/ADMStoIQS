from __future__ import annotations

import argparse

import pandas as pd

from backend.app.core.contracts import LOG_OMS_UNION_PATH
from backend.app.repositories.parquet_log_repository import ParquetLogRepository
from backend.app.schemas.log_oms_union import LOG_OMS_UNION_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lista as últimas etapas registradas do processamento OMS_union.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Quantidade de registros finais a exibir.",
    )
    args = parser.parse_args()

    repository = ParquetLogRepository(
        path=LOG_OMS_UNION_PATH,
        columns=LOG_OMS_UNION_COLUMNS,
    )
    dataframe = repository.read()

    if dataframe.empty:
        print("Log OMS_union vazio.")
        return

    dataframe["criado_em"] = pd.to_datetime(dataframe["criado_em"])
    tail = dataframe.sort_values("criado_em").tail(max(args.limit, 1))

    for row in tail.itertuples(index=False):
        print(
            " | ".join(
                [
                    f"criado_em={row.criado_em}",
                    f"run_id={row.run_id}",
                    f"etapa={row.etapa}",
                    f"status={row.status}",
                    f"arquivos={row.arquivos_origem}",
                    f"linhas_origem={row.linhas_origem}",
                    f"linhas_saida={row.linhas_saida}",
                    f"mensagem={row.mensagem}",
                ]
            )
        )


if __name__ == "__main__":
    main()
