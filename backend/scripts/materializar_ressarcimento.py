from __future__ import annotations

import argparse

from backend.app.services.ressarcimento_service_v2 import RessarcimentoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materializa indicadores de ressarcimento estimado por UC."
    )
    parser.add_argument("--anomes", required=True, help="Competência, exemplo 202605.")
    args = parser.parse_args()

    print("[Ressarcimento] Iniciando materialização...")
    result = RessarcimentoService().materializar(args.anomes)
    print("[Ressarcimento] Materialização concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Indicadores UC: {result.origem_indicadores}")
    print(f"Metas UC: {result.origem_metas}")
    print(f"VRC: {result.origem_vrc}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Total registros: {result.total_registros}")
    print(f"Total UCs: {result.total_ucs}")
    print(f"Violações antes: {result.violacoes_antes}")
    print(f"Violações depois: {result.violacoes_depois}")
    print(f"Valor estimado antes: {result.valor_estimado_antes}")
    print(f"Valor estimado depois: {result.valor_estimado_depois}")
    print(f"Status fórmula: {result.status_formula}")


if __name__ == "__main__":
    main()
