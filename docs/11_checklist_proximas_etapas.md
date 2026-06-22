# Checklist de continuidade

## ETL e apuração

- [ ] Verificar CSVs pendentes contra `log_leitura_csv.parquet`.
- [ ] Processar apenas CSVs pendentes.
- [ ] Atualizar `agrupamento_oms_UNION.parquet`.
- [ ] Gerar apuração mensal em `agrupamento_oms_APURACAO_[anomes].parquet`.
- [ ] Aplicar opção `remover_canceladas` para `ESTADO_INTRP = 7`, quando marcada.
- [ ] Materializar indicadores da apuração.
- [ ] Salvar `resumo_APURACAO_[anomes].parquet`.
- [ ] Atualizar `resumo_APURACAO_ATUAL.parquet`.

## Dashboard

- [ ] Ler cards somente de `resumo_APURACAO_ATUAL.parquet`.
- [ ] Ao clicar em Atualizar, materializar novamente os arquivos de resumo dos cards.
- [ ] Exibir pendências totais.
- [ ] Exibir horário negativo.
- [ ] Exibir sobreposição por equipamento.
- [ ] Exibir rejeitados.
- [ ] Exibir rejeitados por atividade quando existir log.

## Correções

- [ ] Horário negativo com seleção por checkbox.
- [ ] Sobreposição interrupção por `NUM_OPER_CHV_INTRP`.
- [ ] Manter menor `NUM_SEQ_INTRP`.
- [ ] Sugerir rejeição dos demais com `NUM_MOTIVO_TRAT_DIF_UCI = 91`.
- [ ] Registrar `NUM_INTRP_UCI` no log de alteração.
