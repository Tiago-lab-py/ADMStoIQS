from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.services.iqs_extraction_service import IQS_RAW_DIR, IqsExtractionService


ROOT_DIR = Path(__file__).resolve().parents[2]
EXEMPLO_DIR = ROOT_DIR / "exemplo"

CONSULTAS_EXEMPLO = {
    "consistencia_uc_regional": EXEMPLO_DIR / "17_extract_consistencia_iqs_uc_regional.sql",
    "metas_uc": EXEMPLO_DIR / "IQS_METAS UC 2026.sql",
    "sobreposicao_hcai": EXEMPLO_DIR / "IQS_Analise_sobreposição_HCAI_V3.sql",
    "consumidores_regional": EXEMPLO_DIR / "IQS_Consumidores_regional.sql",
    "consumidor_faturado_regional": EXEMPLO_DIR / "IQS_COnsumidor_faturado_regional.sql",
}


def _parse_binds(raw_binds: list[str]) -> dict[str, str]:
    binds: dict[str, str] = {}
    for raw_bind in raw_binds:
        if "=" not in raw_bind:
            raise ValueError(f"Bind inválido: {raw_bind}. Use NOME=VALOR.")
        key, value = raw_bind.split("=", 1)
        binds[key.strip()] = value.strip()
    return binds


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa uma consulta IQS da pasta exemplo.")
    parser.add_argument("--anomes", required=True, help="Competência no formato AAAAMM, exemplo 202605.")
    parser.add_argument(
        "--consulta",
        required=True,
        choices=sorted(CONSULTAS_EXEMPLO),
        help="Consulta da pasta exemplo a executar.",
    )
    parser.add_argument(
        "--bind",
        action="append",
        default=[],
        help="Bind extra no formato NOME=VALOR. Pode ser usado mais de uma vez.",
    )
    args = parser.parse_args()

    sql_path = CONSULTAS_EXEMPLO[args.consulta]
    output_path = IQS_RAW_DIR / f"{args.consulta}_{args.anomes}.parquet"

    print("[IQS] Extração de exemplo")
    print(f"[IQS] Consulta: {args.consulta}")
    print(f"[IQS] SQL: {sql_path}")
    print(f"[IQS] Saída: {output_path}")

    result = IqsExtractionService().extract_sql_file(
        anomes=args.anomes,
        consulta_nome=args.consulta,
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
