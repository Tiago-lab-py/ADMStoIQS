# ETL de Apuração Mensal

## Objetivo

Organizar a preparação dos dados em três etapas independentes:

1. Verificação e processamento de CSVs pendentes.
2. Atualização do mart consolidado `UNION`.
3. Geração da apuração mensal por datas reais.

Essa separação é necessária porque arquivos CSV pendentes podem estar no mês corrente, mas conter registros que atualizam dados do mês de apuração.

## Etapa 1 - CSVs Pendentes

Fonte:

```text
P:\Common\IQS\ADMS\Backup
```

Controle:

```text
data/logs/log_leitura_csv.parquet
```

A aplicação deve:

- listar arquivos encontrados na pasta;
- identificar arquivos pendentes;
- identificar arquivos processados;
- identificar arquivos com erro;
- permitir processamento incremental dos pendentes;
- apresentar resumo após processamento.

Campos desejados na listagem:

- arquivo;
- caminho;
- competência do nome;
- regional;
- tamanho;
- modificado em;
- status;
- mensagem de erro, quando houver.

Resumo esperado após processamento:

- arquivos encontrados;
- arquivos pendentes;
- arquivos processados;
- arquivos com erro;
- linhas lidas;
- linhas deduplicadas/processadas;
- parquets mensais atualizados.

Importante:

- A verificação de CSV não deve depender do mês de apuração.
- O filtro por mês ocorre somente na etapa de apuração mensal.

## Etapa 2 - Atualização do UNION

Após processar CSVs pendentes, atualizar o mart consolidado:

```text
data/mart/agrupamento_oms_UNION.parquet
```

Esse arquivo é a união deduplicada dos parquets mensais de `data/processed`.

O processo deve apresentar:

- parquets mensais encontrados;
- linhas lidas;
- linhas deduplicadas;
- competências incluídas;
- caminho do arquivo gerado;
- log em `data/logs/log_oms_union.parquet`.

## Etapa 3 - Apuração Mensal

A apuração mensal lê o `UNION` e cria uma base de trabalho filtrada por datas reais:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

## Critério Inicial

Para um mês de apuração `AAAAMM`, manter apenas interrupções em que:

- `DATA_HORA_INIC_INTRP` esteja dentro do mês;
- `DATA_HORA_FIM_INTRP` esteja dentro do mês.

Exemplo para maio de 2026:

```text
2026-05-01 00:00:00 <= DATA_HORA_INIC_INTRP < 2026-06-01 00:00:00
2026-05-01 00:00:00 <= DATA_HORA_FIM_INTRP  < 2026-06-01 00:00:00
```

## Saídas

Arquivo mensal:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

Alias operacional usado pelo dashboard:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_ATUAL.parquet
```

## Colunas Adicionadas

- `MES_APURACAO`
- `DATA_HORA_ETL_APURACAO`

## Correções

O arquivo `agrupamento_oms_UNION_corrigido.parquet` deixa de ser a base principal.

O fluxo correto passa a ser:

1. Gerar `agrupamento_oms_UNION.parquet`.
2. Gerar `agrupamento_oms_APURACAO_[anomes].parquet`.
3. Realizar análises e decisões sobre a apuração.
4. Materializar:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_corrigido.parquet
```

Alias operacional:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_CORRIGIDO_ATUAL.parquet
```

## Endpoint

Atualizar o mart UNION pela aplicação:

```text
POST /etl/oms-union
```

Gerar apuração mensal:

```text
POST /etl/apuracao
```

Body:

```json
{
  "anomes": "202605",
  "remover_rejeitados": false
}
```

## Frontend

A primeira página da aplicação passa a ser:

```text
Preparar apuração
```

Fluxo:

1. Abrir a janela `CSVs pendentes`.
2. Verificar arquivos pendentes na pasta.
3. Processar pendentes, se houver.
4. Abrir a janela `Atualizar UNION`.
5. Gerar/atualizar `agrupamento_oms_UNION.parquet`.
6. Abrir a janela `Apuração mensal`.
7. Informar mês de apuração.
8. Gerar `agrupamento_oms_APURACAO_[anomes].parquet`.
9. Dashboard passa a ler `agrupamento_oms_APURACAO_ATUAL.parquet`.
10. Após decisões, gerar versão corrigida da apuração.

## Verificação de CSV

Endpoints:

```text
GET /etl/csv/verificar?anomes=202605
POST /etl/csv/processar
```

O endpoint de verificação compara:

- CSVs encontrados na pasta de origem;
- registros de `data/logs/log_leitura_csv.parquet`;
- status `processado`;
- status `erro`.

A comparação deve considerar:

- caminho completo normalizado;
- nome do arquivo, para cobrir logs gravados com caminho diferente.

A lista da tela deve priorizar:

1. pendentes;
2. erros;
3. processados.

O processamento chama a mesma rotina incremental do terminal:

```cmd
python -m backend.scripts.processar_csv --anomes 202605
```

## Próximas Regras de Limpeza

Depois do filtro mensal, a etapa pode incluir:

- remover registros rejeitados;
- padronizar campos vazios;
- sinalizar datas inválidas;
- separar interrupções iniciadas no mês anterior e finalizadas no mês atual;
- separar interrupções iniciadas no mês atual e finalizadas no mês seguinte;
- gerar relatório de exclusões e pendências do ETL.
