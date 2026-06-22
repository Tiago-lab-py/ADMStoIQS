from __future__ import annotations

import argparse

from backend.app.services.processed_data_service import ProcessedDataService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta CSVs regionais usando preferencialmente OMS_union_corrigido.parquet.",
    )
    parser.add_argument(
        "--anomes",
        help="Competência no formato YYYYMM. Quando omitida, exporta todas as competências disponíveis.",
    )
    args = parser.parse_args()

    if args.anomes and (len(args.anomes) != 6 or not args.anomes.isdigit()):
        raise SystemExit("--anomes deve estar no formato YYYYMM.")

    service = ProcessedDataService()
    competencias = (
        [competencia for competencia in service.list_competencias() if competencia.anomes == args.anomes]
        if args.anomes
        else service.list_competencias()
    )

    if not competencias:
        raise SystemExit("Nenhuma competência encontrada para exportação.")

    total_files = 0
    total_rows = 0

    for competencia in competencias:
        print(f"[export] Competência {competencia.anomes} | fonte={competencia.arquivo}", flush=True)
        results = service.export_all_regionais(competencia.anomes)
        for result in results:
            total_files += 1
            total_rows += result.total_rows
            print(
                " | ".join(
                    [
                        f"[export] OK",
                        f"anomes={result.anomes}",
                        f"regional={result.regional_origem}",
                        f"linhas={result.total_rows}",
                        f"arquivo={result.path}",
                    ]
                ),
                flush=True,
            )

    print("Exportação regional concluída.", flush=True)
    print(f"Arquivos gerados: {total_files}", flush=True)
    print(f"Linhas exportadas: {total_rows}", flush=True)


if __name__ == "__main__":
    main()

