from __future__ import annotations

import argparse

from backend.app.services.sobreposicao_uc_service import SobreposicaoUcService


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa análise de sobreposição temporal por UC.")
    parser.add_argument("--anomes", required=True, help="Competência de apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[Sobreposição UC] Iniciando análise por UC/protocolo...")
    result = SobreposicaoUcService().materializar(args.anomes)
    print("[Sobreposição UC] Análise concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Registros a classificar 91: {result.registros_classificar_91}")
    print(f"UCs afetadas: {result.ucs_afetadas}")
    print(f"Interrupções afetadas: {result.interrupcoes_afetadas}")
    print(f"Horas-UC reduzidas: {result.horas_uc_reduzidas:.6f}")
    print(f"CHI reduzido estimado: {result.chi_reduzido_estimado:.6f}")


if __name__ == "__main__":
    main()

