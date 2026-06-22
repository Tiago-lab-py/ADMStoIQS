from __future__ import annotations

import argparse

from backend.app.services.iqs_mart_service import IqsMartService


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa marts IQS a partir dos Parquets raw.")
    parser.add_argument("--anomes", required=True, help="Competência no formato AAAAMM, exemplo 202605.")
    args = parser.parse_args()

    print("[IQS MART] Materializando marts IQS...")
    result = IqsMartService().materializar(args.anomes)

    print(f"[IQS MART] Competência: {result.anomes}")
    for arquivo in result.arquivos:
        print(
            "[IQS MART] "
            f"fonte={arquivo.fonte} | "
            f"status={arquivo.status} | "
            f"raw={arquivo.linhas_raw} | "
            f"mart={arquivo.linhas_mart} | "
            f"arquivo={arquivo.mart_path}"
        )
        if arquivo.erro:
            print(f"[IQS MART] erro={arquivo.erro}")

    print(f"[IQS MART] Resumo: {result.resumo_path}")
    print(f"[IQS MART] Resumo atual: {result.resumo_atual_path}")


if __name__ == "__main__":
    main()

