# Regras de Dia Crítico (DEC/FEC)

## Objetivo
Padronizar a classificação de severidade de dia crítico por conjunto, usando metas anuais e comportamento diário de DEC/FEC.

## Fontes de dados
- `ddcq.aap_ao_cea_historico_media_movel`
- `ddcq.aap_ao_mart_dias_anomalos`
- `ddcq.aap_ao_dis_servicos_raw`
- `ddcq.aap_ao_dis_interrupcao_raw`
- `ddcq.aap_ao_reclamacoes_raw`
- `ddcq.aap_ao_topologia_uc_raw`

## Conceitos
- Meta anual DEC/FEC: `meta_dec`, `meta_fec`
- Acumulado anual DEC/FEC: `dec_acum_anual`, `fec_acum_anual`
- Degrau do dia: variação diária do acumulado mensal (DEC/FEC)
- Meta diária DEC/FEC: meta anual dividida pelos dias do ano

## Cálculos base

### DEC
- `meta_diaria_dec = meta_dec / dias_no_ano`
- `degrau_dia_dec = dec_acum_mensal(dia_atual) - dec_acum_mensal(dia_anterior)`
  - No 1º dia do mês: usa o valor do próprio dia como degrau inicial.
- `razao_dia_meta_dec = degrau_dia_dec / meta_diaria_dec`

### FEC
- `meta_diaria_fec = meta_fec / dias_no_ano`
- `degrau_dia_fec = fec_acum_mensal(dia_atual) - fec_acum_mensal(dia_anterior)`
  - No 1º dia do mês: usa o valor do próprio dia como degrau inicial.
- `razao_dia_meta_fec = degrau_dia_fec / meta_diaria_fec`

## Regra de severidade

### Prioridade ALTA
Critério aplicado quando:
- `razao_dia_meta_dec >= 2` **ou**
- `razao_dia_meta_fec >= 2`

Interpretação:
- O dia teve impacto pelo menos 2x a meta diária.

### Prioridade MÉDIA
Critério aplicado quando:
- Existe estouro diário (`razao_dia_meta_dec > 1` ou `razao_dia_meta_fec > 1`) **e**
- O acumulado anual já excedeu a meta anual correspondente:
  - `dec_acum_anual > meta_dec` para DEC
  - `fec_acum_anual > meta_fec` para FEC

Interpretação:
- Já estourou meta anual e o dia mantém pressão acima da meta diária.

### Sem prioridade
Quando não atende os critérios acima.

## Regras adicionais (serviços)
- Meta de Dia Crítico por conjunto é mantida em decimal.
- Limite operacional de comparação é inteiro arredondado para cima.
- Na carga da meta anual, se houver duplicidade por conjunto, mantém a maior meta.

## Regras críticas de qualidade (CI/CHI líquido)

### Regra 1 - Duração curta com impacto líquido (ERRO GRAVE)
Condição:
- `duracao_min < 3` **e**
- (`ci_liquido > 0` **ou** `chi_liquido > 0`)

Classificação:
- `ERRO_GRAVE_DURACAO_CURTA_COM_IMPACTO`
- Severidade: **P0 (bloqueante)**

Ação recomendada:
- Não permitir validação final como `VALIDO` até correção ou justificativa formal.

### Regra 2 - Protocolo tipo 1 com impacto líquido (ERRO GRAVE)
Condição:
- `tipo_protocolo = 1` **e**
- (`ci_liquido > 0` **ou** `chi_liquido > 0`)

Classificação:
- `ERRO_GRAVE_PROTOCOLO_1_COM_IMPACTO_LIQUIDO`
- Severidade: **P0 (bloqueante)**

Regra esperada:
- Para `tipo_protocolo = 1`, esperado `ci_liquido = 0` e `chi_liquido = 0`.

### Regra 3 - Protocolo tipo 6 com impacto líquido (ALERTA BAIXO)
Condição:
- `tipo_protocolo = 6` **e**
- (`ci_liquido > 0` **ou** `chi_liquido > 0`)

Classificação:
- `ALERTA_PROTOCOLO_6_COM_IMPACTO_LIQUIDO`
- Severidade: **baixa (não bloqueante)**

Ação recomendada:
- Enviar para fila de conferência do analista (revisão assistida).

## Métricas operacionais exibidas
- `limite_dia_critico` (inteiro)
- `delta_servicos_limite`
- `servicos_faltando_para_limite`
- `servicos_acima_do_limite`
- indicadores de prioridade DEC/FEC por conjunto

## Serviços (detalhes)
No detalhamento de serviços:
- CI do serviço:
  - `ci_servico = vl_total_consumidor_afetados` se `status_servico = '14'`
  - caso contrário `0`
- CHI do serviço:
  - `chi_servico = vl_total_consumidor_afetados * horas(dthr_term_srv - dthr_solicitacao_servico)` se `status_servico = '14'`
  - se `status_servico != '14'`, `0`
  - se `dthr_term_srv` nulo para status 14, sinalizar para verificação de término

## Observações de qualidade de dados
- Chaves de conjunto devem ser normalizadas para evitar divergência (`15573` vs `15573.0`).
- Descrição de status de serviço deve estar preenchida (`status_servico_desc`).
- Campos de causa/componente podem ser exibidos como `codigo-descricao`.

## Resultado esperado
- Tela de Dias Anômalos com priorização consistente DEC/FEC.
- Rastreabilidade do impacto diário com base técnica e operacional.
- Apoio claro para decisão analítica de dia crítico por conjunto.
