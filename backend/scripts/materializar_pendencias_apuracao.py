from __future__ import annotations

import argparse

from backend.app.services.pendencias_apuracao_service import PendenciasApuracaoService


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa pendências da apuração atual.")
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[PENDÊNCIAS] Materializando pendências da apuração...")
    result = PendenciasApuracaoService().materializar(args.anomes)

    print("[PENDÊNCIAS] Materialização concluída.")
    print(f"[PENDÊNCIAS] Competência: {result.anomes}")
    print(f"[PENDÊNCIAS] Origem: {result.origem}")
    print(f"[PENDÊNCIAS] Parquet: {result.parquet}")
    print(f"[PENDÊNCIAS] Atual: {result.parquet_atual}")
    print(f"[PENDÊNCIAS] Total: {result.total_pendencias}")
    print(f"[PENDÊNCIAS] Horário negativo: {result.horario_negativo}")
    print(f"[PENDÊNCIAS] Sobreposição interrupção: {result.sobreposicao_interrupcao}")
    print(f"[PENDÊNCIAS] Sem causa/componente: {result.sem_causa_componente}")


if __name__ == "__main__":
    main()

