from __future__ import annotations

from backend.app.services.oms_union_service import OmsUnionService


def main() -> None:
    service = OmsUnionService()
    result = service.build()

    print("Mart OMS union gerado com sucesso.")
    print(f"Arquivos origem: {result.arquivos_origem}")
    print(f"Linhas origem: {result.linhas_origem}")
    print(f"Linhas saída: {result.linhas_saida}")
    print(f"Parquet: {result.parquet_path}")


if __name__ == "__main__":
    main()

