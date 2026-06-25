from __future__ import annotations

import argparse

from backend.app.services.fechamento_apuracao_service import FechamentoApuracaoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera a apuração mensal a partir do parquet isolado de fechamento."
    )
    parser.add_argument("--anomes", required=True, help="Competência no formato YYYYMM.")
    args = parser.parse_args()

    print("[Fechamento] Gerando apuração mensal isolada...", flush=True)
    result = FechamentoApuracaoService().gerar(args.anomes)

    print("[Fechamento] Apuração gerada.", flush=True)
    print(f"Anomes: {result.anomes}", flush=True)
    print(f"Origem: {result.origem}", flush=True)
    print(f"Parquet: {result.parquet}", flush=True)
    print(f"Atual: {result.parquet_atual}", flush=True)
    print(f"Linhas origem: {result.linhas_origem}", flush=True)
    print(f"Linhas apuração: {result.linhas_apuracao}", flush=True)


if __name__ == "__main__":
    main()
