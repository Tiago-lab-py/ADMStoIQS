# Horário negativo: seleção e log

## Seleção em tela

A fila de **Horário negativo** deve permitir seleção por checkbox:

- selecionar um registro individual;
- selecionar todos os registros visíveis na tabela;
- limpar a seleção;
- aplicar decisão ao registro ativo quando não houver seleção;
- aplicar decisão em lote quando houver registros selecionados.

## Filtro por duração

A tela possui filtros de duração mínima e máxima para priorizar a tratativa:

- o filtro usa `duracao_minutos`;
- registros fora da faixa deixam de aparecer na tabela;
- a ação **Selecionar todos visíveis** seleciona apenas os registros filtrados;
- a tratativa em massa atua somente nos registros selecionados.

Ao abrir a fila, o filtro deve iniciar vazio para exibir todas as
`NUM_SEQ_INTRP` negativas retornadas pelo backend. Os presets são apenas
atalhos de análise:

- `0 a -3h`;
- `-3h a -24h`;
- `< -24h`.

O card **Horário negativo** mostra o total da fila materializada; o card
**Registros visíveis** mostra o total após filtro de duração.

## Correção de início e fim

A fila deve apresentar os horários originais e sugeridos:

- `DATA_HORA_INIC_INTRP`;
- `DATA_HORA_FIM_INTRP`;
- `DATA_HORA_INIC_INTRP_SUGERIDA`;
- `DATA_HORA_FIM_INTRP_SUGERIDA`.

Para diferenças negativas de até 3 horas, a sugestão é manter o início e
acrescentar 3 horas ao fim por hipótese de fuso horário. Diferenças maiores
devem seguir para revisão manual.

## Detalhe da NUM_SEQ_INTRP

Para manter a tabela principal mais objetiva, `NUM_POSTO_UCI` e `NUM_UC_UCI`
ficam ocultos na lista de horário negativo.

A tabela principal também remove duplicidade visual por `NUM_SEQ_INTRP`.
Assim, uma interrupção que afeta várias UCs aparece uma única vez na fila.
O endpoint da fila também deve devolver os registros já consolidados por
`NUM_SEQ_INTRP`, para evitar que os primeiros 100 registros sejam todos da
mesma interrupção.

Ao selecionar um registro, a tela apresenta uma tabela complementar da
`NUM_SEQ_INTRP` selecionada contendo:

- `NUM_SEQ_INTRP`;
- `NUM_POSTO_UCI`;
- `NUM_UC_UCI`;
- `NUM_INTRP_UCI`;
- `DTHR_INICIO_INTRP_UC`;
- `duracao_minutos`.

Quando uma linha deduplicada é selecionada, a seleção representa todas as UCs
vinculadas àquela `NUM_SEQ_INTRP` para fins de tratativa em massa.

O card **Horário negativo** deve contar `NUM_SEQ_INTRP` distintas com duração
negativa, e não a quantidade de UCs impactadas.

## Log de alteração

Cada decisão enviada pela tela inclui:

- `chave_registro`: `NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI`;
- `NUM_INTRP_UCI`: interrupção alterada;
- `num_intrp_uci`: alias técnico para compatibilidade com o backend;
- `justificativa`: texto obrigatório informado pelo analista.

O painel lateral de decisão exibe a `NUM_INTRP_UCI` do registro selecionado
para dar rastreabilidade antes da gravação.
