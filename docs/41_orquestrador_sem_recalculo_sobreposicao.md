# Orquestrador — Regra de Recálculo das Sobreposições

Data: 2026-06-24

## Decisão

No orquestrador diário, as etapas de sobreposição não devem recalcular pendências, base tratada, indicadores ou ressarcimento individualmente.

O recálculo deve ocorrer uma única vez, ao final da trilha, depois de todas as alterações automáticas terem sido implantadas.

## Sequência correta

1. Processar CSVs pendentes.
2. Atualizar `agrupamento_oms_UNION.parquet`.
3. Gerar `agrupamento_oms_APURACAO_[anomes].parquet`.
4. Materializar sobreposição de interrupção.
5. Materializar sobreposição UC fase 1.
6. Implantar sobreposição UC fase 1 com `recalcular=False`.
7. Materializar sobreposição UC fase 2 após a fase 1.
8. Implantar sobreposição UC fase 2 com `recalcular=False`.
9. Gerar `agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet`.
10. Materializar pendências.
11. Materializar indicadores de continuidade.
12. Materializar ressarcimento.
13. Registrar log do orquestrador.

## Parâmetros esperados

Quando o orquestrador chamar os serviços diretamente:

- `SobreposicaoUcService().implantar(..., recalcular=False)`
- `SobreposicaoUcFase2Service().implantar(..., recalcular=False)`

Quando o orquestrador chamar scripts via subprocess:

- `python -m backend.scripts.implantar_sobreposicao_uc --anomes [AAAAMM] --usuario SISTEMA_AI --perfil sistema --sem-recalculo`
- `python -m backend.scripts.implantar_sobreposicao_uc_fase2 --anomes [AAAAMM] --usuario SISTEMA_AI --perfil sistema --sem-recalculo`

## Motivo

Evita processamento duplicado em arquivos grandes:

- não regrava base tratada várias vezes;
- não recalcula indicadores antes da base final;
- não recalcula ressarcimento com estado intermediário;
- reduz tempo total da trilha;
- reduz risco de inconsistência entre ponteiros `ATUAL`.

## Governança

As implantações automáticas devem registrar:

- `usuario = SISTEMA_AI`;
- `perfil = sistema`;
- justificativa operacional da regra;
- log por regra aplicada;
- horário de implantação.

