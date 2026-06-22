from __future__ import annotations

import argparse

from backend.app.services.indicadores_continuidade_service import IndicadoresContinuidadeService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa DEC/FEC/DIC/FIC/DMIC antes e depois do tratamento."
    )
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[Indicadores] Iniciando materialização de continuidade...")
    result = IndicadoresContinuidadeService().materializar(args.anomes)

    print("[Indicadores] Materialização concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem antes: {result.origem_antes}")
    print(f"Origem depois: {result.origem_depois}")
    print(f"Mart UC: {result.mart_uc}")
    print(f"Mart agregado: {result.mart_agregado}")
    print(f"Mart comparativo: {result.mart_comparativo}")
    print(f"Linhas UC: {result.total_uc}")
    print(f"Linhas agregado: {result.total_agregado}")
    print(f"Linhas comparativo: {result.total_comparativo}")
    print(f"Fonte denominador: {result.fonte_denominador}")
    print(f"Filtro faturamento: {result.filtro_faturamento}")


if __name__ == "__main__":
    main()
