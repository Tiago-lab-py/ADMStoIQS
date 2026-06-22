# Reflexão e proposta — Middleware ADMStoIQS

## 1. Objetivo macro

O objetivo do projeto é atuar como um middleware local entre ADMS e IQS:

1. Monitorar diariamente a pasta `P:\Common\IQS\ADMS\Backup`.
2. Ler os CSVs gerados pelo ADMS.
3. Converter os dados para estruturas locais em Parquet.
4. Consolidar, deduplicar e preparar uma base governada.
5. Aplicar regras robustas para reduzir falhas antes do processamento pelo IQS.
6. Gerar novos CSVs com a mesma estrutura esperada pelo IQS.
7. Registrar todo processamento e toda decisão de alteração em logs auditáveis.

O projeto deve continuar evitando dependência de banco transacional central, pois já houve problemas em experiências anteriores com gravação em banco. A estratégia local com CSV + Parquet + DuckDB é adequada para volume alto, desde que os arquivos sejam bem particionados, os logs sejam consistentes e as etapas sejam materializadas.

## 2. Princípios técnicos recomendados

### 2.1 Parquet como base operacional

O Parquet deve ser tratado como a camada principal do projeto:

- CSV é apenas entrada e saída.
- Parquet mensal é a camada processada.
- Parquet UNION é a camada consolidada.
- Parquet APURAÇÃO é a camada de trabalho mensal.
- Parquet de resumo é a camada rápida para cards e indicadores.
- Parquet de alterações é a camada de auditoria.

Essa separação reduz leitura repetida de CSV, diminui uso de disco temporário e permite consultas rápidas via DuckDB.

### 2.2 Processamento incremental

O processamento diário deve ser incremental:

- Verificar arquivos existentes na pasta de origem.
- Comparar com `log_leitura_csv.parquet`.
- Processar apenas arquivos pendentes.
- Registrar linhas lidas, linhas deduplicadas, erro, encoding e regional.
- Atualizar o mart UNION somente após concluir a ingestão.

O frontend deve mostrar somente pendências reais, não todos os arquivos da pasta.

### 2.3 Materialização de etapas

Para volume alto, cada etapa importante deve salvar resultado físico:

1. `data/processed/agrupamento_oms_[anomes].parquet`
2. `data/mart/agrupamento_oms_UNION.parquet`
3. `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`
4. `data/mart/apuracao/resumo_APURACAO_[anomes].parquet`
5. CSVs finais por regional.

Isso evita recalcular milhões de registros a cada abertura de tela.

## 3. Fluxo proposto

### Etapa 1 — Verificação de CSV pendente

Entrada:

- Pasta `P:\Common\IQS\ADMS\Backup`
- Log `data/logs/log_leitura_csv.parquet`

Saída:

- Lista apenas de arquivos pendentes.
- Quantidade por mês.
- Quantidade por regional.
- Tamanho total pendente.

Regra:

- O arquivo é considerado já processado se existir no log com `status = processado`.
- Arquivos com `status = erro` devem aparecer em seção separada de reprocessamento.

### Etapa 2 — Ingestão CSV para Parquet mensal

Entrada:

- CSVs pendentes.

Saída:

- `data/processed/agrupamento_oms_[anomes].parquet`
- `log_leitura_csv.parquet` atualizado.

Regras:

- Ler como texto quando houver instabilidade de tipos.
- Preservar `REGIONAL_ORIGEM`.
- Deduplicar pela chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

- Usar staging temporário e remover ao final.

### Etapa 3 — Atualização do UNION

Entrada:

- Parquets mensais em `data/processed`.

Saída:

- `data/mart/agrupamento_oms_UNION.parquet`
- `data/logs/log_oms_union.parquet`

Regras:

- Deduplicar novamente pela chave UC.
- Criar campos derivados:
  - `duracao_minutos`
  - `erro_duracao`
  - `duracao_longa`
  - `status_validacao`
  - `atividade_validacao`
  - `justificativa_validacao`

### Etapa 4 — Apuração mensal

Entrada:

- `data/mart/agrupamento_oms_UNION.parquet`

Saída:

- `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`
- `data/mart/apuracao/agrupamento_oms_APURACAO_ATUAL.parquet`

Regra:

- Filtrar registros com início e fim dentro do mês de apuração.
- Opcionalmente remover canceladas:

```text
ESTADO_INTRP = 7
```

Essa base deve ser a origem das páginas de tratamento.

### Etapa 5 — Materialização de indicadores

Entrada:

- `agrupamento_oms_APURACAO_[anomes].parquet`

Saída:

- `resumo_APURACAO_[anomes].parquet`
- `resumo_APURACAO_ATUAL.parquet`

Indicadores:

- Total de registros.
- Pendências totais.
- Horário negativo por `NUM_SEQ_INTRP` distinta.
- Sobreposição por equipamento.
- Sem causa/componente.
- Rejeitados.
- Validados.
- Rejeitados por atividade.

Os cards do dashboard devem ler esse resumo, não recalcular tudo na abertura.

### Etapa 6 — Tratamentos governados

Cada regra deve trabalhar em dois níveis:

1. Interrupção ou evento técnico.
2. UCs/registros afetados.

Isso é essencial porque uma interrupção pode afetar muitas UCs.

## 4. Regras de tratamento

### 4.1 Horário negativo

Conceito correto:

- Card: contar `NUM_SEQ_INTRP` distintas.
- Detalhe: mostrar todas as UCs vinculadas à `NUM_SEQ_INTRP`.

Regra sugerida:

- Se diferença negativa estiver entre 0 e 3 horas:
  - sugerir ajuste de fuso;
  - `DATA_HORA_FIM_INTRP = DATA_HORA_INIC_INTRP + 3 horas`.
- Se diferença negativa for maior que 3 horas:
  - enviar para revisão manual.

O usuário pode:

- validar sugestão;
- rejeitar registro;
- ignorar regra para tratar futuramente.

### 4.2 Sobreposição por equipamento

Chave técnica:

```text
NUM_OPER_CHV_INTRP
```

Agrupamento de interrupção:

```text
NUM_SEQ_INTRP
```

Regra:

- Identificar interrupções diferentes no mesmo `NUM_OPER_CHV_INTRP` com intervalo temporal sobreposto.
- Para a sobreposição:
  - manter o menor `NUM_SEQ_INTRP`;
  - considerar menor data de início e maior data fim para o evento mantido;
  - sugerir rejeição dos demais eventos sobrepostos;
  - preencher `NUM_MOTIVO_TRAT_DIF_UCI = 91` nos rejeitados.

Importante:

- A análise deve ser por interrupção única, não por UC.
- A tela pode mostrar a interrupção na tabela principal e as UCs em detalhe.

### 4.3 Sobreposição de UC

Chave técnica:

```text
NUM_UC_UCI|NUM_POSTO_UCI
```

Regra:

- Identificar mesma UC/posto com intervalos sobrepostos.
- Se a interrupção sobreposta for longa:
  - sugerir deslocamento do início da segunda para o fim da primeira.
  - preencher `NUM_INTRP_INIC_MANOBRA_UCI` com o número da primeira interrupção.
- Se a interrupção for curta:
  - sugerir rejeição com `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

### 4.4 Causa e componente ausentes

Campos:

```text
COD_CAUSA_INTRP
COD_COMP_INTRP
```

Regra inicial:

- Listar registros sem causa ou componente.
- Sugerir causa/componente por padrões históricos:
  - mesmo alimentador;
  - mesmo equipamento;
  - mesma descrição;
  - mesma regional;
  - ocorrências semelhantes.

Essa regra deve começar como sugestão, não alteração automática.

## 5. Governança

### 5.1 Perfis

Perfis mínimos:

- `admin`: gerencia usuários, perfis e reset de senha.
- `gestor`: aprova/rejeita alterações em massa.
- `usuario`: analisa e propõe alterações.

### 5.2 Auditoria obrigatória

Toda decisão deve gravar:

- usuário;
- perfil;
- nome do computador, quando disponível;
- IP;
- data/hora;
- regra aplicada;
- chave do registro;
- `NUM_SEQ_INTRP`;
- `NUM_INTRP_UCI`, quando aplicável;
- campo alterado;
- valor original;
- valor sugerido;
- valor aplicado;
- justificativa;
- status da decisão.

### 5.3 Estados de validação

Recomenda-se padronizar:

```text
pendente
sugerido
validado
rejeitado
ignorado
revisao_manual
exportado
```

## 6. Frontend recomendado

### 6.1 Tela inicial — Preparar apuração

Janelas:

1. CSVs pendentes.
2. Atualizar UNION.
3. Gerar apuração mensal.
4. Materializar resumo.

Botões devem mostrar:

- “Aguarde processamento...” em vermelho enquanto executa.
- “Processamento concluído” em verde ao terminar.
- Erro técnico com detalhe resumido.

### 6.2 Dashboard

O dashboard deve ser somente leitura:

- cards;
- tendências;
- pendências por regra;
- rejeitados por atividade;
- visão executiva;
- calculo de DEC FEC por Regional e Copel do antes e depois do tratamento;
- Calculo de ressarmineto antes e depois do tratamento. Por DIC, FIC e DMIC verificar no prodist modulo 8  da aneel.

Não deve ter ação de alteração.

### 6.3 Páginas de tratamento

Cada página deve ter:

- tabela principal por evento técnico;
- detalhe das UCs vinculadas;
- seleção individual;
- seleção em massa;
- decisão governada;
- justificativa obrigatória para rejeição/alteração.

## 7. Estratégia de performance

### 7.1 O que calcular sob demanda

Pode ser sob demanda:

- listagem paginada de 100 registros;
- detalhe de uma interrupção selecionada;
- download de CSV final.

### 7.2 O que materializar

Deve ser materializado:

- resumo dos cards;
- contagens por regra;
- lista de pendências pesadas;
- logs de processamento;
- apuração mensal.

Para dezenas de milhões de linhas, abrir tela não pode disparar varredura completa desnecessária.

## 8. Proposta de evolução

### Fase A — Estabilizar pipeline local

- Garantir ingestão incremental diária.
- Garantir UNION confiável.
- Garantir apuração mensal.
- Garantir resumo materializado.
- Garantir logs de CSV e UNION.

### Fase B — Separar evento e UC

- Criar endpoints/tabelas de evento técnico.
- Criar endpoints/tabelas de detalhe de UCs.
- Ajustar horário negativo e sobreposição para operar por evento.

### Fase C — Governança forte

- Consolidar perfis.
- Persistir decisões no `log_alteracoes.parquet`.
- Aplicar decisões para gerar base corrigida da apuração.
- Criar trilha de aprovação para gestor.

### Fase D — Exportação IQS

- Gerar CSVs por regional.
- Manter cabeçalho oficial.
- Validar contagem de linhas.
- Gerar relatório de exportação.
- Registrar exportação no log.

### Fase E — Operação diária

- Criar comando único:

```cmd
python -m backend.scripts.rotina_diaria --anomes 202605
```

Esse comando deve:

1. verificar CSVs pendentes;
2. processar pendentes;
3. atualizar UNION;
4. gerar apuração;
5. materializar resumo;
6. indicar pendências para análise;
7. gerar relatório operacional.

## 9. Análise dos scripts da pasta exemplo

A análise inicial por inventário foi registrada em:

```text
docs/13_analise_inventario_exemplo.md
```

Essa análise classifica os arquivos da pasta `exemplo` por prioridade e por tipo de reaproveitamento.

Ainda é necessário ler o conteúdo dos principais scripts para extrair regras concretas.

Pontos a procurar:

- boas regras de tratamento já existentes;
- validações de data mais maduras;
- critérios de rejeição já usados pelo negócio;
- padrões de log e auditoria;
- estruturas de saída esperadas pelo IQS;
- decisões técnicas que evitaram problemas de banco;
- scripts que possam virar serviços reutilizáveis.

Quando os arquivos forem analisados, classificar cada item como:

```text
reaproveitar
adaptar
descartar
inspirar regra futura
```

Prioridade sugerida:

1. `exemplo/apurador_polars_full.py`
2. `exemplo/IQS_Analise_sobreposição_HCAI_V3.sql`
3. `exemplo/docs projeto analise ocorrencia/19_Analise_temporal.MD`
4. `exemplo/docs projeto analise ocorrencia/16_Consistencia_IQS.md`
5. `exemplo/docs projeto analise ocorrencia/15_VALIDACAO+POS_OPERACAO.md`

## 10. Recomendação principal

A recomendação é tratar o ADMStoIQS como uma esteira local de dados governada:

```text
CSV ADMS
  -> Parquet mensal
  -> UNION
  -> APURAÇÃO mensal
  -> Regras e decisões
  -> CSV IQS
```

O ponto mais importante agora é separar corretamente:

- registro de UC;
- interrupção técnica;
- equipamento;
- apuração mensal;
- decisão de governança.

Essa separação evita as distorções vistas recentemente, como contar milhares de UCs quando o problema real são poucas interrupções distintas.

## 11. Evolução do dashboard executivo

O dashboard deve ser somente leitura e evoluir para uma visão executiva, operacional, regulatória e financeira.

Itens esperados:

- cards operacionais;
- tendências;
- pendências por regra;
- rejeitados por atividade;
- visão executiva;
- cálculo de DEC/FEC por regional e consolidado Copel antes e depois do tratamento;
- cálculo estimado de ressarcimento antes e depois do tratamento;
- avaliação de DIC, FIC e DMIC conforme metodologia vigente do PRODIST Módulo 8 da ANEEL.

### 11.1 Bloco operacional

Indicadores recomendados:

- total de registros da apuração;
- pendências por regra;
- registros validados;
- registros rejeitados;
- registros em revisão manual;
- pendências por regional;
- pendências por tipo de regra.

### 11.2 Bloco regulatório

Indicadores recomendados:

- DEC antes do tratamento;
- DEC depois do tratamento;
- variação absoluta e percentual do DEC;
- FEC antes do tratamento;
- FEC depois do tratamento;
- variação absoluta e percentual do FEC;
- DIC por UC antes e depois;
- FIC por UC antes e depois;
- DMIC por UC antes e depois;
- estimativa de compensação/ressarcimento antes e depois;
- diferença estimada de exposição financeira.

### 11.3 Cuidados de governança

O dashboard não deve executar alteração de dados.

O cálculo de compensação/ressarcimento deve ser tratado como estimativa até validação formal da fórmula vigente no PRODIST Módulo 8 e das regras internas aplicáveis.

O sistema deve diferenciar:

- valor técnico estimado;
- valor regulatório oficial;
- valor aprovado por gestor;
- valor exportado/encaminhado.

Essa separação evita que um cálculo preliminar seja confundido com obrigação regulatória definitiva.
