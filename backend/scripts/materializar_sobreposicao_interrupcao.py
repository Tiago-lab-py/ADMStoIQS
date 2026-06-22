from __future__ import annotations

import argparse

from backend.app.services.sobreposicao_interrupcao_service import SobreposicaoInterrupcaoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa análise de sobreposição temporal por interrupção/equipamento."
    )
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[Sobreposição] Iniciando análise por interrupção/equipamento...")
    result = SobreposicaoInterrupcaoService().materializar(args.anomes)

    print("[Sobreposição] Análise concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Total interrupções: {result.total_interrupcoes}")
    print(f"Manter: {result.manter}")
    print(f"Excluir: {result.excluir}")


if __name__ == "__main__":
    main()

