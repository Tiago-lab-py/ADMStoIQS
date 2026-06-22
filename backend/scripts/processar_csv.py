from __future__ import annotations

import argparse

from backend.app.services.csv_ingestion_service import CsvIngestionService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processa CSVs IQS/ADMS pendentes e gera Parquets mensais.",
    )
    parser.add_argument(
        "--anomes",
        help="Processa apenas uma competência no formato YYYYMM.",
    )
    parser.add_argument(
        "--todos-pendentes",
        action="store_true",
        help="Processa todos os arquivos pendentes. É o comportamento padrão.",
    )
    parser.add_argument(
        "--manter-temp",
        action="store_true",
        help="Não limpa data/raw_temp ao final. Usar apenas para diagnóstico.",
    )
    args = parser.parse_args()

    if args.anomes and (len(args.anomes) != 6 or not args.anomes.isdigit()):
        raise SystemExit("--anomes deve estar no formato YYYYMM.")

    service = CsvIngestionService()
    summary = service.process_pending(
        anomes=args.anomes,
        clean_temp=not args.manter_temp,
    )

    print("Processamento incremental concluído.")
    print(f"Arquivos encontrados: {summary.arquivos_encontrados}")
    print(f"Arquivos pendentes: {summary.arquivos_pendentes}")
    print(f"Meses processados: {summary.meses_processados}")

    for result in summary.resultados:
        print(
            " | ".join(
                [
                    f"anomes={result.anomes}",
                    f"arquivos={result.arquivos_processados}",
                    f"erros={result.arquivos_com_erro}",
                    f"linhas_lidas={result.linhas_lidas}",
                    f"linhas_processadas={result.linhas_processadas}",
                    f"parquet={result.parquet_path}",
                ]
            )
        )


if __name__ == "__main__":
    main()
