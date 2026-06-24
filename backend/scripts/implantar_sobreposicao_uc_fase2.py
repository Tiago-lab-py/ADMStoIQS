from __future__ import annotations

import argparse
import socket

from backend.app.services.sobreposicao_uc_fase2_service import SobreposicaoUcFase2Service


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Implanta ajustes da Fase 2 de sobreposição UC e recalcula marts dependentes."
    )
    parser.add_argument("--anomes", required=True, help="Competência no formato AAAAMM, exemplo 202605.")
    parser.add_argument("--usuario", default="terminal")
    parser.add_argument("--perfil", default="admin")
    parser.add_argument("--ip", default="")
    parser.add_argument("--pc", default=socket.gethostname())
    parser.add_argument(
        "--sem-recalculo",
        action="store_true",
        help="Implanta sem recalcular pendências, tratado, indicadores e ressarcimento.",
    )
    parser.add_argument(
        "--justificativa",
        default="Implantação governada da Fase 2 de sobreposição UC.",
    )
    args = parser.parse_args()

    print("[Sobreposição UC Fase 2] Implantando ajustes de início/manobra...")
    result = SobreposicaoUcFase2Service().implantar(
        anomes=args.anomes,
        usuario=args.usuario,
        perfil=args.perfil,
        ip=args.ip,
        pc=args.pc,
        justificativa=args.justificativa,
        recalcular=not args.sem_recalculo,
    )
    if result.sem_alteracoes:
        print("[Sobreposição UC Fase 2] Nenhum ajuste pendente. Apuração, tratado e indicadores não foram recalculados.")
        print(f"Anomes: {result.anomes}")
        print(f"Análise: {result.analise}")
        print(f"Registros atualizados: {result.registros_atualizados}")
        print(f"Recálculos: {result.recalculos}")
        return

    print("[Sobreposição UC Fase 2] Implantação concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem atualizada: {result.origem}")
    print(f"Backup: {result.backup}")
    print(f"Análise: {result.analise}")
    print(f"Log: {result.log}")
    print(f"Log atual: {result.log_atual}")
    print(f"Registros atualizados: {result.registros_atualizados}")
    print(f"UCs afetadas: {result.ucs_afetadas}")
    print(f"Interrupções ajustadas: {result.interrupcoes_ajustadas}")
    print(f"Minutos de interseção: {result.minutos_interseccao:.2f}")
    if result.recalculos:
        print("Recalculos:")
        for etapa, status in result.recalculos.items():
            print(f"- {etapa}: {status}")


if __name__ == "__main__":
    main()
