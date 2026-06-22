from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.services.iqs_extraction_service import IQS_RAW_DIR, SQL_DIR, IqsExtractionService


def _parse_binds(raw_binds: list[str]) -> dict[str, str]:
    binds: dict[str, str] = {}
    for raw_bind in raw_binds:
        if "=" not in raw_bind:
            raise ValueError(f"Bind inválido: {raw_bind}. Use NOME=VALOR.")
        key, value = raw_bind.split("=", 1)
        binds[key.strip()] = value.strip()
    return binds


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai dados do IQS para Parquet local.")
    parser.add_argument("--anomes", required=True, help="Competência no formato AAAAMM, exemplo 202605.")
    parser.add_argument(
        "--consulta",
        default="teste_dual",
        help="Nome do arquivo SQL em backend/app/sql/iqs sem extensão. Padrão: teste_dual.",
    )
    parser.add_argument(
        "--sql-path",
        default=None,
        help="Caminho completo opcional para um arquivo SQL externo, por exemplo da pasta exemplo.",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Caminho opcional do Parquet de saída.",
    )
    parser.add_argument(
        "--bind",
        action="append",
        default=[],
        help="Bind extra no formato NOME=VALOR. Pode ser usado mais de uma vez.",
    )
    args = parser.parse_args()

    sql_path = Path(args.sql_path) if args.sql_path else SQL_DIR / f"{args.consulta}.sql"
    consulta_nome = args.consulta
    if args.sql_path and args.consulta == "teste_dual":
        consulta_nome = sql_path.stem

    output_path = Path(args.saida) if args.saida else IQS_RAW_DIR / f"{consulta_nome}_{args.anomes}.parquet"

    print("[IQS] Iniciando extração...")
    print(f"[IQS] Consulta: {consulta_nome}")
    print(f"[IQS] SQL: {sql_path}")
    print(f"[IQS] Saída: {output_path}")

    result = IqsExtractionService().extract_sql_file(
        anomes=args.anomes,
        consulta_nome=consulta_nome,
        sql_path=sql_path,
        output_path=output_path,
        extra_binds=_parse_binds(args.bind),
    )

    print("[IQS] Extração concluída.")
    print(f"[IQS] Status: {result.status}")
    print(f"[IQS] Linhas: {result.linhas_extraidas}")
    print(f"[IQS] Duração: {result.duracao_segundos}s")
    print(f"[IQS] Parquet: {result.arquivo_saida}")


if __name__ == "__main__":
    main()
