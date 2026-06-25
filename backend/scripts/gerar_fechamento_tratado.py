from __future__ import annotations

import argparse

from backend.app.services.fechamento_tratamento_service import FechamentoTratamentoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera uma base tratada isolada para o fechamento mensal."
    )
    parser.add_argument("--anomes", required=True, help="Competência no formato YYYYMM.")
    args = parser.parse_args()

    print("[Fechamento] Gerando base tratada isolada...", flush=True)
    result = FechamentoTratamentoService().gerar(args.anomes)

    print("[Fechamento] Base tratada gerada.", flush=True)
    print(f"Anomes: {result.anomes}", flush=True)
    print(f"Origem: {result.origem}", flush=True)
    print(f"Parquet tratado: {result.parquet}", flush=True)
    print(f"Atual: {result.parquet_atual}", flush=True)
    print(f"Total original: {result.total_original}", flush=True)
    print(f"Removido horário negativo: {result.removido_horario_negativo}", flush=True)
    print(f"Removido sem causa/componente: {result.removido_sem_causa_componente}", flush=True)
    print(f"Total final: {result.total_final}", flush=True)


if __name__ == "__main__":
    main()
