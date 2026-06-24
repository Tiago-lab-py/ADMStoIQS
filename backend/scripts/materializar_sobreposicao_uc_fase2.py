from __future__ import annotations

import argparse

from backend.app.services.sobreposicao_uc_fase2_service import SobreposicaoUcFase2Service


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa a análise Fase 2 de sobreposição temporal por UC."
    )
    parser.add_argument("--anomes", required=True, help="Competência no formato AAAAMM, exemplo 202605.")
    args = parser.parse_args()

    print("[Sobreposição UC Fase 2] Iniciando análise de interseção por UC/protocolo...")
    result = SobreposicaoUcFase2Service().materializar(args.anomes)
    print("[Sobreposição UC Fase 2] Análise concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Total ajustes: {result.total_ajustes}")
    print(f"UCs afetadas: {result.ucs_afetadas}")
    print(f"Interrupções ajustadas: {result.interrupcoes_ajustadas}")
    print(f"Minutos de interseção: {result.minutos_interseccao:.2f}")


if __name__ == "__main__":
    main()
