# Visão Geral das Sprints

## Objetivo

Construir uma solução local para ingestão, deduplicação, consulta, auditoria e geração de CSV a partir dos arquivos de interrupções IQS/ADMS disponíveis em:

```text
P:\Common\IQS\ADMS\Backup
```

A solução deve processar arquivos CSV a partir de abril de 2026, gerar Parquets mensais em área processada e permitir posterior consulta/exportação via frontend React com autenticação.

## Componentes

- **Backend Python**: responsável por leitura dos CSVs, processamento com DuckDB, deduplicação, logs e APIs.
- **DuckDB**: motor local para leitura, transformação e consulta dos dados.
- **Parquet Processado**: artefato mensal oficial para consulta e exportação.
- **Frontend React**: interface autenticada para consulta, amostra, alteração e geração de CSV.
- **Logs Parquet**: trilhas técnicas e de auditoria de negócio.

## Estrutura Sugerida

```text
backend/
  app/
    api/
    core/
    services/
    repositories/
    schemas/
  scripts/
  tests/

frontend/
  src/

data/
  raw_temp/
  processed/
  mart/
  logs/
  exports/
  duckdb/
    staging/
```

## Áreas de Dados

- `data/raw_temp/`: área temporária usada apenas durante o processamento.
- `data/processed/`: saída oficial dos Parquets mensais.
- `data/mart/`: marts analíticos derivados, como `OMS_union.parquet`.
- `data/logs/`: logs técnicos e de auditoria.
- `data/exports/`: CSVs gerados pelo usuário.
- `data/duckdb/`: banco DuckDB local opcional para staging, controle e consultas.
- `data/duckdb/staging/`: Parquets intermediários por arquivo, reaproveitáveis em caso de interrupção e apagados após sucesso.

## Artefatos Principais

- `data/processed/agrupamento_oms_[anomes].parquet`
- `data/mart/OMS_union.parquet`
- `data/logs/log_leitura_csv.parquet`
- `data/logs/log_alteracoes.parquet`
- `data/logs/log_oms_union.parquet`
- `data/exports/agrupamento_oms_[anomes]_[timestamp].csv`

## Ordem das Sprints

1. Sprint 0: contratos, governança e desenho técnico.
2. Sprint 1: backend de ingestão CSV para Parquet.
3. Sprint 2: API de consulta, amostra e exportação CSV.
4. Sprint 3: frontend React com login e fluxo operacional.
5. Sprint 4: auditoria nominal e governança de alterações.
6. Sprint 5: robustez, testes, operação e observabilidade.
