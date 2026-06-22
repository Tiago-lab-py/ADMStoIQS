from __future__ import annotations

import argparse

from backend.app.services.csv_discovery import discover_csv_files
from backend.app.services.csv_ingestion_service import CsvIngestionService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lista CSVs IQS/ADMS descobertos por competência.",
    )
    parser.add_argument(
        "--anomes",
        help="Lista apenas uma competência no formato YYYYMM.",
    )
    args = parser.parse_args()

    if args.anomes and (len(args.anomes) != 6 or not args.anomes.isdigit()):
        raise SystemExit("--anomes deve estar no formato YYYYMM.")

    service = CsvIngestionService()
    processed_keys = service.processed_keys()

    csv_files = discover_csv_files()
    if args.anomes:
        csv_files = [
            csv_file
            for csv_file in csv_files
            if csv_file.anomes == args.anomes
        ]

    total_size = sum(csv_file.size_bytes for csv_file in csv_files)
    pending_count = sum(
        1
        for csv_file in csv_files
        if csv_file.processing_key not in processed_keys
    )

    print(f"Arquivos encontrados: {len(csv_files)}")
    print(f"Arquivos pendentes: {pending_count}")
    print(f"Tamanho total: {total_size:,} bytes".replace(",", "."))

    for csv_file in csv_files:
        status = (
            "processado"
            if csv_file.processing_key in processed_keys
            else "pendente"
        )
        print(
            " | ".join(
                [
                    f"anomes={csv_file.anomes}",
                    f"regional={csv_file.regional_origem}",
                    f"status={status}",
                    f"tamanho={csv_file.size_bytes}",
                    f"arquivo={csv_file.name}",
                ]
            )
        )


if __name__ == "__main__":
    main()
