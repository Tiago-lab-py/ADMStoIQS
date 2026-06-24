from __future__ import annotations

import argparse

from backend.app.services.orquestrador_apuracao_service import OrquestradorApuracaoService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa a trilha operacional completa da apuração ADMStoIQS."
    )
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo: 202605.")
    parser.add_argument("--usuario", default="SISTEMA_AI", help="Usuário responsável pelo log.")
    parser.add_argument("--perfil", default="sistema", help="Perfil responsável pelo log.")
    parser.add_argument("--sem-csv", action="store_true", help="Não processa CSVs pendentes.")
    parser.add_argument("--sem-union", action="store_true", help="Não atualiza o OMS UNION.")
    parser.add_argument("--sem-apuracao", action="store_true", help="Não gera a apuração mensal.")
    parser.add_argument("--sem-pendencias", action="store_true", help="Não materializa pendências.")
    parser.add_argument(
        "--sem-sobreposicao-interrupcao",
        action="store_true",
        help="Não materializa a análise de sobreposição por interrupção/equipamento.",
    )
    parser.add_argument("--sem-tratado", action="store_true", help="Não gera a base tratada.")
    parser.add_argument("--sem-indicadores", action="store_true", help="Não materializa indicadores.")
    parser.add_argument("--sem-ressarcimento", action="store_true", help="Não materializa ressarcimento.")
    parser.add_argument(
        "--manter-canceladas",
        action="store_true",
        help="Mantém ESTADO_INTRP=7 na apuração mensal.",
    )
    args = parser.parse_args()

    print("[Orquestrador] Iniciando trilha ADMStoIQS...")
    result = OrquestradorApuracaoService().executar(
        anomes=args.anomes,
        usuario=args.usuario,
        perfil=args.perfil,
        processar_csv=not args.sem_csv,
        atualizar_union=not args.sem_union,
        gerar_apuracao=not args.sem_apuracao,
        materializar_pendencias=not args.sem_pendencias,
        materializar_sobreposicao_interrupcao=not args.sem_sobreposicao_interrupcao,
        gerar_tratado=not args.sem_tratado,
        materializar_indicadores=not args.sem_indicadores,
        materializar_ressarcimento=not args.sem_ressarcimento,
        remover_canceladas=not args.manter_canceladas,
    )

    print(f"[Orquestrador] Status: {result.status}")
    print(f"[Orquestrador] Competência: {result.anomes}")
    print(f"[Orquestrador] Início: {result.iniciado_em}")
    print(f"[Orquestrador] Fim: {result.finalizado_em}")
    for index, etapa in enumerate(result.etapas, start=1):
        print(
            f"[Orquestrador] {index}/{len(result.etapas)} "
            f"{etapa.etapa} | {etapa.status} | {etapa.mensagem}"
        )


if __name__ == "__main__":
    main()
