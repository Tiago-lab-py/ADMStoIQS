from __future__ import annotations

import argparse

from backend.app.services.tratamento_massivo_service import TratamentoMassivoService


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera base de apuração tratada para envio ao IQS.")
    parser.add_argument("--anomes", required=True, help="Competência da apuração, exemplo 202605.")
    args = parser.parse_args()

    print("[Tratamento] Iniciando geração da base tratada...")
    result = TratamentoMassivoService().gerar_apuracao_tratada(args.anomes)

    print("[Tratamento] Base tratada gerada com sucesso.")
    print(f"Anomes: {result.anomes}")
    print(f"Origem: {result.origem}")
    print(f"Sobreposição: {result.sobreposicao}")
    print(f"Parquet tratado: {result.parquet}")
    print(f"Atual: {result.parquet_atual}")
    print(f"Log: {result.log}")
    print(f"Total original: {result.total_original}")
    print(f"Removido horário negativo: {result.removido_horario_negativo}")
    print(f"Removido sem causa/componente: {result.removido_sem_causa_componente}")
    print(f"Removido sobreposição interrupção: {result.removido_sobreposicao_interrupcao}")
    print(f"Total final: {result.total_final}")


if __name__ == "__main__":
    main()

