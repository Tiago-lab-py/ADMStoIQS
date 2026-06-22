# Regras ajustadas: apuração e sobreposição

## Dashboard

O Dashboard é somente consultivo.

- Não exibe painel de alteração.
- Não grava decisões.
- Serve para visão geral e navegação para as filas de tratamento.

## Apuração mensal

Na **Janela 3** da preparação de apuração existe a opção:

- `Remover canceladas (ESTADO_INTRP = 7)`.

Quando marcada, o ETL mensal remove registros cancelados antes de salvar:

- `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`;
- `data/mart/apuracao/agrupamento_oms_APURACAO_ATUAL.parquet`.

## Sobreposição de interrupção

A análise de sobreposição de interrupção deve ser sinalizada por equipamento:

- campo principal: `NUM_OPER_CHV_INTRP`;
- apoio: `ALIM_INTRP_PIN`;
- comparação temporal: `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`;
- identificação da ocorrência: `NUM_SEQ_INTRP` e chave da UC.

A tela deve priorizar a exibição de `NUM_OPER_CHV_INTRP` para mostrar quais
equipamentos estão associados a interrupções sobrepostas.

### Critério de sugestão

Antes da comparação temporal, as linhas devem ser consolidadas em
**interrupções únicas**, porque uma mesma interrupção pode afetar várias UCs.

A unidade de análise passa a ser:

- `NUM_OPER_CHV_INTRP`;
- `NUM_SEQ_INTRP`.

Para cada interrupção única:

- `DATA_HORA_INIC_INTRP` considerada = menor início das linhas da interrupção;
- `DATA_HORA_FIM_INTRP` considerada = maior fim das linhas da interrupção;
- `qtd_ucs_afetadas` = quantidade de linhas/UCs vinculadas à interrupção.

Quando houver mais de uma interrupção única temporalmente sobreposta na mesma
`NUM_OPER_CHV_INTRP`:

- manter a interrupção com menor `NUM_SEQ_INTRP`;
- sugerir para o registro mantido a menor `DATA_HORA_INIC_INTRP` do grupo;
- sugerir para o registro mantido a maior `DATA_HORA_FIM_INTRP` do grupo;
- para os demais registros do grupo, sugerir rejeição por sobreposição;
- preencher a sugestão `NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO = 91`.

O Dashboard deve considerar a quantidade calculada no parquet ativo completo,
não apenas os 100 registros visíveis na tabela. A contagem do card deve ser
feita por interrupções únicas sobrepostas, não por UCs afetadas.

### Rejeições por atividade

O Dashboard exibe também a quantidade de registros rejeitados por atividade,
consolidada a partir do `log_alteracoes.parquet`.
