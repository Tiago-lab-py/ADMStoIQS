from __future__ import annotations

import argparse

from backend.app.services.outlier_duracao_service import OutlierDuracaoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa análise de interrupções com duração acima do limite informado."
    )
    parser.add_argument("--anomes", required=True, help="Competência de apuração. Exemplo: 202605.")
    parser.add_argument(
        "--limite-horas",
        type=float,
        default=48.0,
        help="Limite mínimo em horas para sinalizar outlier. Padrão: 48.",
    )
    parser.add_argument(
        "--base-original",
        action="store_true",
        help="Usa a apuração original em vez da base tratada.",
    )
    args = parser.parse_args()

    print("[Outlier duração] Iniciando análise de interrupções longas...")
    result = OutlierDuracaoService().materializar(
        args.anomes,
        limite_horas=args.limite_horas,
        usar_tratado=not args.base_original,
    )

    print("[Outlier duração] Análise concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Limite horas: {result.limite_horas}")
    print(f"Total outliers: {result.total_outliers}")
    print(f"UCs afetadas estimadas: {result.total_ucs_afetadas}")
    print(f"Duração máxima horas: {result.duracao_max_horas:.6f}")
    print(f"CHI estimado horas-UC: {result.chi_estimado_horas_uc:.6f}")


if __name__ == "__main__":
    main()
