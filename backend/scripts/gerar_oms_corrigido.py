from __future__ import annotations

from backend.app.services.oms_correcoes_service import OmsCorrecoesService


def main() -> None:
    print("[OMS_corrigido] Gerando base corrigida com governança...")
    result = OmsCorrecoesService().gerar_corrigido()
    print("[OMS_corrigido] Mart OMS corrigido gerado com sucesso.")
    print(f"[OMS_corrigido] Alterações/decisões aplicáveis: {result.alteracoes_aplicaveis}")
    print(f"[OMS_corrigido] Linhas saída: {result.linhas_saida}")
    print(f"[OMS_corrigido] Parquet: {result.caminho}")


if __name__ == "__main__":
    main()
