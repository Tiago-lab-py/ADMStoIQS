from __future__ import annotations

import argparse

from backend.app.services.fechamento_mensal_service import (
    FECHAMENTO_INPUT_DIR,
    FechamentoMensalService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Processa CSVs consolidados regionais do fechamento mensal em trilha isolada."
    )
    parser.add_argument("--anomes", required=True, help="Competência da pasta de fechamento, exemplo 202605.")
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Pasta alternativa dos CSVs. Padrão: data/input/fechamento/{anomes}.",
    )
    args = parser.parse_args()

    entrada = args.input_dir or (FECHAMENTO_INPUT_DIR / args.anomes)
    print("[Fechamento] Iniciando processamento mensal consolidado...")
    print(f"[Fechamento] Entrada esperada: {entrada}")
    print("[Fechamento] Observação: a competência vem da pasta; o timestamp do nome do CSV pode ser posterior.")

    result = FechamentoMensalService().processar(
        anomes=args.anomes,
        input_dir=args.input_dir,
    )

    print("[Fechamento] Processamento concluído.")
    print(f"Anomes: {result.anomes}")
    print(f"Entrada: {result.entrada}")
    print(f"Arquivos encontrados: {result.arquivos_encontrados}")
    print(f"Linhas lidas: {result.linhas_lidas}")
    print(f"Linhas saída deduplicada: {result.linhas_saida}")
    print(f"Parquet: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    for item in result.regionais:
        print(f"regional={item.regional} | linhas={item.linhas} | arquivo={item.arquivo}")


if __name__ == "__main__":
    main()
