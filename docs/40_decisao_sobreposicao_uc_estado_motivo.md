# Decisão de Governança — Sobreposição UC

Data da decisão: 2026-06-24

## Regra aprovada

Para tratamento de sobreposição temporal em UC:

- `ESTADO_INTRP` deve permanecer `4`.
- A classificação da UC sobreposta deve ocorrer somente em `NUM_MOTIVO_TRAT_DIF_UCI = 91`.
- A alteração deve ser registrada em log com usuário, perfil, horário, regra aplicada e justificativa.
- Quando executada por rotina automática, o executor deve ser `SISTEMA_AI`.

## Interpretação operacional

A sobreposição UC não cancela a interrupção inteira. Ela classifica a participação da UC na interrupção como tratada/diferenciada.

Portanto:

- Não usar `ESTADO_INTRP = 7` para sobreposição UC.
- Usar `ESTADO_INTRP = 7` apenas quando a decisão governada for cancelar a interrupção inteira.
- Para sobreposição UC contida ou interseccionada, aplicar `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

## Efeito nos indicadores

Os indicadores líquidos devem considerar somente registros com:

- `ESTADO_INTRP = '4'`;
- duração maior ou igual a 3 minutos;
- `TIPO_PROTOC_JUSTIF_UCI = '0'`;
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo;
- UC faturada.

Assim, registros de UC marcados com motivo `91` permanecem auditáveis na base, mas são expurgados do cálculo líquido.

## Sequência operacional recomendada

Para resolver sobreposição e recalcular indicadores:

1. Materializar sobreposição de interrupção por equipamento.
2. Materializar sobreposição UC fase 1.
3. Implantar sobreposição UC fase 1 somente quando houver registros, mantendo `ESTADO_INTRP = 4` e populando `NUM_MOTIVO_TRAT_DIF_UCI = 91`.
4. Materializar sobreposição UC fase 2.
5. Implantar sobreposição UC fase 2 somente quando houver ajustes, alterando `DTHR_INICIO_INTRP_UC` e `NUM_INTRP_INIC_MANOBRA_UCI`.
6. Gerar base tratada.
7. Recalcular indicadores de continuidade.
8. Recalcular ressarcimento.

Execuções automáticas devem usar:

- `usuario = SISTEMA_AI`;
- `perfil = sistema`;
- justificativa operacional informando a regra aplicada.

