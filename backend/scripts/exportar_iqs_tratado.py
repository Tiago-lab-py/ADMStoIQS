from __future__ import annotations

import argparse

from backend.app.services.tratamento_massivo_service import TratamentoMassivoService


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta CSV IQS a partir da apuração tratada.")
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[Exportação IQS] Iniciando exportação dos CSVs tratados...")
    result = TratamentoMassivoService().exportar_csv_iqs(args.anomes)

    print("[Exportação IQS] Exportação concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Total arquivos: {result.total_arquivos}")
    print(f"Total linhas: {result.total_linhas}")
    for item in result.arquivos:
        print(
            "regional={regional} | linhas={linhas} | arquivo={caminho}".format(
                regional=item["regional"],
                linhas=item["linhas"],
                caminho=item["caminho"],
            )
        )


if __name__ == "__main__":
    main()

