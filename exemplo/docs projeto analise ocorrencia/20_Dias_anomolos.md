# Dias Anômalos: Reclamações sob Demanda

## Objetivo

Reduzir a lentidão da página `Dias Anômalos` quando o analista precisa consultar reclamações
por conjunto, sem perder rastreabilidade do vínculo entre:

- `reclamacao.uc`
- `topologia_uc.uc`
- `topologia_uc.conjunto`

## Problema atual

- A abertura da página fica lenta quando a trilha de reclamações é carregada junto com o restante da análise.
- Mesmo quando há reclamações no conjunto, a cobertura da topologia pode ser insuficiente e gerar tela vazia.
- O resumo de reclamações e o detalhe acabam competindo com a mesma consulta pesada.

## Diretriz de solução

### 1. Reclamações em área própria

As reclamações devem ficar em uma área própria da página, separadas das demais evidências operacionais.

### 2. Carga sob demanda

A consulta de reclamações não deve disparar automaticamente ao abrir a página.

Fluxo desejado:

1. Analista seleciona:
   - competência
   - exatamente 1 conjunto
   - intervalo de datas
2. A tela mostra o contexto da consulta
3. O analista clica em `Carregar reclamações`
4. Só então a consulta pesada é executada

### 3. Resumo separado do detalhe

- `Resumo Reclamação`: visão agregada do recorte
- `Detalhe Reclamação`: visão paginada

A paginação deve existir apenas no detalhe.

### 4. Transparência da cobertura

A tela deve deixar claro quando o problema é de vínculo e não ausência de reclamação.

Mensagem operacional esperada:

- `Sem dados de reclamação/topologia`
- `Baixa cobertura do vínculo reclamacao.uc -> topologia_uc.uc -> conjunto`

## Próxima evolução

Depois da carga sob demanda, o próximo passo é materializar a base de reclamações de dias anômalos em background.

### Marts sugeridos

- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_resumo`
- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_detalhe`
- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_cobertura`

### Status

DDL criada:

- `sql/32_create_table_dbguo_aap_ao_mart_dias_anomalos_reclamacoes_resumo.sql`
- `sql/33_create_table_dbguo_aap_ao_mart_dias_anomalos_reclamacoes_detalhe.sql`
- `sql/34_create_table_dbguo_aap_ao_mart_dias_anomalos_reclamacoes_cobertura.sql`

### Benefícios

- abertura imediata da página
- estabilidade multiusuário
- diagnóstico de cobertura pronto
- menos carga no banco

## Etapa iniciada

Primeira entrega:

- carga sob demanda de reclamações
- contexto visível antes da consulta
- resumo e detalhe preservados
- preparação para separar a trilha de reclamações em aba própria

## Materialização implementada

ETL criado:

- `etl/14_mart_dias_anomalos_reclamacoes.py`
- `etl/15_mart_dias_anomalos_reclamacoes_sql.py`

Saídas geradas:

- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_resumo`
- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_detalhe`
- `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_cobertura`

Enriquecimento do resumo:

- `qtd_uc_com_2_reclamacoes`
- `qtd_uc_com_3_reclamacoes`
- `qtd_uc_com_mais_de_3_reclamacoes`

Essas colunas medem, no mesmo dia e no mesmo agrupamento do resumo, quantas UCs reclamaram:

- exatamente 2 vezes
- exatamente 3 vezes
- mais de 3 vezes

Snapshots locais:

- `dados/mart/mart_dias_anomalos_reclamacoes_resumo.parquet`
- `dados/mart/mart_dias_anomalos_reclamacoes_detalhe.parquet`
- `dados/mart/mart_dias_anomalos_reclamacoes_cobertura.parquet`

## Como rodar

Competência específica:

```bat
cd /d D:\analise_ocorrencia
python etl\14_mart_dias_anomalos_reclamacoes.py --competencia 2026-05
```

Todas as competências disponíveis:

```bat
cd /d D:\analise_ocorrencia
python etl\14_mart_dias_anomalos_reclamacoes.py
```

## Ajuste de schema para base já criada

Se a tabela `ddcq.aap_ao_mart_dias_anomalos_reclamacoes_resumo` já existir no banco, rode também:

```sql
\i sql/35_alter_table_dbguo_aap_ao_mart_dias_anomalos_reclamacoes_resumo_add_recorrencia.sql
```

Se o ETL acusar conflito no resumo durante a persistência, ajuste também o índice único:

```sql
\i sql/36_fix_unique_index_dbguo_aap_ao_mart_dias_anomalos_reclamacoes_resumo.sql
```

Motivo:

- o agrupamento do resumo é por:
  - competência
  - conjunto
  - data
  - `nome_se`
  - `nome_alim`
  - `num_oper_alim`
  - `posto`
- então o índice único precisa refletir essa mesma granularidade

## Regra atual da materialização

- normaliza `uc` de reclamação e topologia
- usa `topologia_uc_raw` como fonte de conjunto
- cria `topo_latest` por `uc`
- grava:
  - detalhe completo
  - resumo agregado
  - cobertura por competência/conjunto

## Próximo passo

Trocar a página `Dias Anômalos` para consumir primeiro os marts materializados de reclamação,
deixando a consulta em tempo real apenas como contingência.

## Materialização SQL-first

Para reduzir o custo de baixar `reclamacoes_raw` e `topologia_uc_raw` para pandas,
foi criada uma trilha SQL-first.

Arquivos:

- `sql/37_mart_dias_anomalos_reclamacoes_detalhe.sql`
- `sql/38_mart_dias_anomalos_reclamacoes_resumo.sql`
- `sql/39_mart_dias_anomalos_reclamacoes_cobertura.sql`
- `etl/15_mart_dias_anomalos_reclamacoes_sql.py`

Fluxo:

1. materializa `detalhe`
2. materializa `resumo` a partir do detalhe
3. materializa `cobertura` a partir do detalhe

Observação técnica:

- os SQLs usam `cast(:competencia as varchar)` para compatibilidade com `sqlalchemy.text(...)`
- evitar a forma `:competencia::varchar`, que pode falhar na interpolação do parâmetro

Como rodar:

```bat
cd /d D:\analise_ocorrencia
python etl\15_mart_dias_anomalos_reclamacoes_sql.py --competencia 2026-05
```

Ou para todas as competências:

```bat
cd /d D:\analise_ocorrencia
python etl\15_mart_dias_anomalos_reclamacoes_sql.py
```

Diretriz:

- preferir a trilha SQL-first para performance
- manter o ETL pandas como contingência operacional
## Otimizacao da topologia para reclamacoes
- A topologia bruta (`aap_ao_topologia_uc_raw`) tem alto volume e custo excessivo quando o `detalhe` recalcula `row_number()` por `uc` em toda execucao.
- Foi adotada a estrategia de base auxiliar:
  - `ddcq.aap_ao_topologia_uc_latest`
- Essa tabela guarda apenas 1 linha por `uc`, com os atributos necessarios para o vinculo com reclamacoes:
  - `uc`
  - `competencia`
  - `cod_conjunto`
  - `sigla_se`
  - `nome_se`
  - `nome_alim`
  - `num_oper_alim`
  - `posto`
  - `vrc`
  - `eusd`
- O SQL de criacao esta em:
  - `sql/40_create_table_dbguo_aap_ao_topologia_uc_latest.sql`
- O SQL de refresh desta base esta em:
  - `sql/41_refresh_topologia_uc_latest.sql`
- O refresh foi simplificado para usar `distinct on (uc)` em vez de `row_number() over (partition by uc)` em toda a tabela bruta.
- Foi adicionado um indice de apoio para esta selecao:
  - `sql/42_create_index_dbguo_aap_ao_topologia_uc_raw_latest_support.sql`
- O SQL do mart de detalhe (`sql/37_mart_dias_anomalos_reclamacoes_detalhe.sql`) foi simplificado para usar `join` direto:
  - `reclamacoes_raw.uc = topologia_uc_latest.uc`
- Com isso:
  - eliminamos o `row_number()` em 6M+ linhas em toda execucao
  - melhoramos a chance de uso de indice
  - reduzimos drasticamente a pressao no servidor para a carga diaria de reclamacoes
