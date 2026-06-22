from __future__ import annotations

import argparse

from backend.app.services.apuracao_resumo_service import ApuracaoResumoService


def main() -> None:
    parser = argparse.ArgumentParser(description="Materializa o resumo dos cards da apuração atual.")
    parser.add_argument("--anomes", default=None, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    result = ApuracaoResumoService().materializar(anomes=args.anomes)

    print("Resumo de apuração materializado com sucesso.")
    print(f"Anomes: {result.anomes}")
    print(f"Total registros: {result.total_registros}")
    print(f"Pendências: {result.pendencias_totais}")
    print(f"Horário negativo: {result.horario_negativo}")
    print(f"Sobreposição interrupção: {result.sobreposicao_interrupcao}")
    print(f"Rejeitados: {result.rejeitados}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")


if __name__ == "__main__":
    main()
