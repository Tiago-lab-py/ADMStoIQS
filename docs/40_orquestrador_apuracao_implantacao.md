# Orquestrador de apuração ADMStoIQS

## Objetivo

Centralizar a implantação operacional diária/mensal em uma trilha única, com log nominal e possibilidade de execução:

- automática, por agendador local;
- manual, por administrador no portal;
- técnica, por terminal.

O objetivo é reduzir passos soltos e evitar geração desnecessária de arquivos fora do fluxo governado.

## Fluxo oficial

1. Verificar e processar CSVs pendentes em `P:\Common\IQS\ADMS\Backup`.
2. Atualizar `data/mart/agrupamento_oms_UNION.parquet`.
3. Gerar `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`.
4. Materializar `pendencias_APURACAO_[anomes].parquet` e `pendencias_APURACAO_ATUAL.parquet`.
5. Materializar análise de sobreposição por interrupção/equipamento.
6. Gerar `agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet`.
7. Materializar indicadores de continuidade.
8. Materializar ressarcimento estimado.

## Comando terminal

```bat
python -m backend.scripts.orquestrar_apuracao --anomes 202605
```

Execução parcial:

```bat
python -m backend.scripts.orquestrar_apuracao --anomes 202605 --sem-csv --sem-union
```

## Endpoint

`POST /etl/orquestrar-apuracao`

Uso esperado pelo portal:

```json
{
  "anomes": "202605",
  "processar_csv": true,
  "atualizar_union": true,
  "gerar_apuracao": true,
  "materializar_pendencias": true,
  "materializar_sobreposicao_interrupcao": true,
  "gerar_tratado": true,
  "materializar_indicadores": true,
  "materializar_ressarcimento": true,
  "remover_canceladas": true
}
```

Permissão: apenas perfil `admin`.

## Logs

O orquestrador grava:

- `data/logs/log_orquestrador_apuracao.parquet`;
- etapa executada;
- usuário/perfil;
- horário de início e fim;
- status;
- mensagem;
- detalhes técnicos serializados.

Para execução automática via agendador, usar:

- `usuario = SISTEMA_AI`;
- `perfil = sistema`.

Para execução manual via portal, usar o usuário autenticado.

## Governança

Processamento diário automático pode gerar materializações e classificações sistêmicas, mas alterações pontuais de registros devem seguir trilha governada com:

- usuário;
- perfil;
- horário;
- IP/PC quando disponível;
- justificativa;
- autorização quando houver alteração de `NUM_MOTIVO_TRAT_DIF_UCI = 91` ou `ESTADO_INTRP = 7`.

## Próximas melhorias

- Mostrar progresso incremental por etapa no frontend.
- Adicionar histórico visual do último `log_orquestrador_apuracao.parquet`.
- Permitir agendamento via `schtasks` com arquivo `.cmd`.
- Separar execução diária leve da execução mensal completa.
