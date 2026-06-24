from __future__ import annotations

import argparse

from backend.app.services.sobreposicao_uc_service import SobreposicaoUcService


def main() -> None:
    parser = argparse.ArgumentParser(description="Implanta motivo 91 para sobreposição temporal por UC.")
    parser.add_argument("--anomes", required=True, help="Competência de apuração, exemplo 202605.")
    parser.add_argument("--usuario", default="terminal", help="Usuário responsável pela implantação.")
    parser.add_argument("--perfil", default="admin", help="Perfil do usuário responsável.")
    parser.add_argument(
        "--justificativa",
        default="Implantação governada de motivo 91 por sobreposição temporal de UC.",
        help="Justificativa registrada no log.",
    )
    parser.add_argument(
        "--sem-recalculo",
        action="store_true",
        help="Implanta motivo 91 sem recalcular pendências, tratamento, indicadores e ressarcimento.",
    )
    args = parser.parse_args()

    print("[Sobreposição UC] Implantando motivo 91...")
    result = SobreposicaoUcService().implantar(
        anomes=args.anomes,
        usuario=args.usuario,
        perfil=args.perfil,
        justificativa=args.justificativa,
        ip="terminal",
        pc="terminal",
        recalcular=not args.sem_recalculo,
    )
    print("[Sobreposição UC] Implantação concluída.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem atualizada: {result.origem}")
    print(f"Backup: {result.backup}")
    print(f"Log: {result.log}")
    print(f"Registros atualizados: {result.registros_atualizados}")
    print(f"UCs afetadas: {result.ucs_afetadas}")
    print(f"Interrupções afetadas: {result.interrupcoes_afetadas}")
    print(f"CHI reduzido estimado: {result.chi_reduzido_estimado:.6f}")
    print(f"Recálculos: {result.recalculos}")


if __name__ == "__main__":
    main()

