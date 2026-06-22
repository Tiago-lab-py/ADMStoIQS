# Sprint 1 — Backend de Ingestão CSV para Parquet

## Objetivo

Criar o backend Python responsável por ler os CSVs em `P:\Common\IQS\ADMS\Backup`, processar apenas arquivos novos, remover duplicidades e gerar Parquets mensais em `data/processed`.

## Escopo

- Criar estrutura base do backend.
- Implementar leitor incremental de CSV.
- Implementar controle de arquivos processados.
- Implementar deduplicação por UC.
- Gerar Parquet mensal.
- Apagar dados temporários ao final do processamento.

## Fluxo de Processamento

1. Listar arquivos `Interrupcoes_IQS_*.CSV` no diretório de origem.
2. Extrair data do nome do arquivo.
3. Filtrar arquivos com competência `YYYYMM >= 202604`.
4. Consultar `data/logs/log_leitura_csv.parquet`.
5. Processar apenas arquivos ainda não registrados como processados.
6. Converter cada CSV pendente em Parquet de staging usando DuckDB.
7. Consolidar os Parquets de staging com o Parquet mensal existente, se houver.
8. Deduplicar por `NUM_INTRP_UCI`, `NUM_POSTO_UCI`, `NUM_UC_UCI`.
9. Gravar `data/processed/agrupamento_oms_[anomes].parquet`.
10. Registrar arquivos processados em `log_leitura_csv.parquet`.
11. Limpar `data/raw_temp/` e o staging mensal concluído.

## Log de Leitura

Arquivo:

```text
data/logs/log_leitura_csv.parquet
```

Campos mínimos:

| Campo | Descrição |
|---|---|
| `arquivo_path` | Caminho completo do CSV lido |
| `arquivo_nome` | Nome do arquivo |
| `arquivo_tamanho_bytes` | Tamanho do arquivo no momento da leitura |
| `arquivo_modificado_em` | Data/hora de modificação do arquivo |
| `arquivo_hash` | Hash opcional para detectar troca de conteúdo |
| `anomes` | Competência processada |
| `processado_em` | Data/hora do processamento |
| `status` | `processado`, `erro` ou `ignorado` |
| `linhas_lidas` | Total de linhas lidas |
| `linhas_processadas` | Total de linhas após processamento |
| `mensagem_erro` | Erro técnico, quando existir |

## Deduplicação

Critério inicial:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

Regra:

- Manter apenas um registro por chave.
- Se existir coluna confiável de atualização, manter o registro mais recente.
- Se não existir, manter a primeira ocorrência de forma determinística.

## Saída Processada

Padrão:

```text
data/processed/agrupamento_oms_[anomes].parquet
```

Exemplos:

```text
data/processed/agrupamento_oms_202604.parquet
data/processed/agrupamento_oms_202605.parquet
data/processed/agrupamento_oms_202606.parquet
```

## Limpeza de Temporários

A pasta `data/raw_temp/` deve ser limpa ao final do processamento, tanto em sucesso quanto em erro controlado, para evitar excesso de dados locais.

## Critérios de Aceite

- Processa apenas arquivos novos.
- Ignora arquivos já registrados em `log_leitura_csv.parquet`.
- Remove duplicidades pela chave definida.
- Gera Parquet mensal no padrão esperado.
- Preserva a regional de origem na coluna `REGIONAL_ORIGEM`.
- Limpa `data/raw_temp/` ao final.
- Registra métricas mínimas da leitura.

## Implementação

Arquivos criados para a Sprint 1:

- `backend/app/repositories/parquet_log_repository.py`: leitura e escrita atômica dos logs Parquet.
- `backend/app/services/csv_discovery.py`: descoberta dos CSVs na pasta de origem e extração da competência.
- `backend/app/services/raw_temp.py`: limpeza segura da pasta temporária preservando `.gitkeep`.
- `backend/app/services/csv_ingestion_service.py`: staging incremental por arquivo, deduplicação e geração do Parquet mensal.
- `backend/scripts/processar_csv.py`: CLI operacional para processar arquivos pendentes.
- `backend/scripts/listar_csv.py`: CLI para listar arquivos descobertos, processados e pendentes por competência.
- `backend/scripts/compactar_log_leitura.py`: CLI para compactar registros repetidos do log de leitura.
- `backend/scripts/resetar_competencia.py`: CLI para remover controles de uma competência e permitir reprocessamento.

O padrão de descoberta considera todos os sufixos após o timestamp, como:

- `Interrupcoes_IQS_20260430033012_CSL.CSV`
- `Interrupcoes_IQS_20260430033539_LES.CSV`
- `Interrupcoes_IQS_20260430034122_NRO.CSV`
- `Interrupcoes_IQS_20260430034640_NRT.CSV`
- `Interrupcoes_IQS_20260430035353_OES.CSV`

O sufixo do arquivo é preservado na coluna técnica `REGIONAL_ORIGEM`, com valores como `CSL`, `LES`, `NRO`, `NRT` e `OES`. Esta coluna deve ser usada posteriormente para reconstruir os arquivos finais com as UCs na regional correta.

## Comandos

Executar todos os arquivos pendentes:

```text
python -m backend.scripts.processar_csv
```

Executar apenas uma competência:

```text
python -m backend.scripts.processar_csv --anomes 202604
```

Durante o processamento, o terminal exibe progresso por arquivo:

```text
[202605] Arquivo 23 de 333 | CSL | Interrupcoes_IQS_20260513221709_CSL.CSV
[202605] OK 23 de 333 | linhas=148000
```

Listar arquivos de uma competência antes de processar:

```text
python -m backend.scripts.listar_csv --anomes 202605
```

Manter temporários para diagnóstico:

```text
python -m backend.scripts.processar_csv --anomes 202604 --manter-temp
```

## Comportamento Incremental

O processo considera um arquivo já lido somente quando existe registro com `status = processado` em `data/logs/log_leitura_csv.parquet` para a combinação:

- Caminho completo do arquivo.
- Tamanho do arquivo.
- Data/hora de modificação.

Registros com `status = erro` não bloqueiam nova tentativa de processamento.

Falhas de leitura são registradas por arquivo. Um CSV com erro não deve impedir que os demais arquivos válidos da mesma competência sejam convertidos para staging e consolidados.

Compactar registros repetidos do log de leitura:

```text
python -m backend.scripts.compactar_log_leitura
```

Resetar apenas o log de uma competência:

```text
python -m backend.scripts.resetar_competencia --anomes 202604
```

Reprocessar uma competência do zero, removendo log, Parquet final e staging:

```text
python -m backend.scripts.resetar_competencia --anomes 202604 --remover-parquet --remover-staging
python -m backend.scripts.processar_csv --anomes 202604
```

## Staging por Arquivo

Para reduzir risco operacional com meses muito grandes, cada CSV pendente é convertido individualmente para Parquet de staging em:

```text
data/duckdb/staging/[anomes]/
```

O nome do arquivo de staging inclui:

- Nome original do CSV.
- Tamanho do arquivo.
- Data/hora de modificação.

Se o processamento cair no meio, os Parquets de staging já criados podem ser reaproveitados na próxima execução. Se o mês concluir com sucesso, o staging daquele mês é apagado.

Os arquivos só entram em `log_leitura_csv.parquet` com `status = processado` depois que o Parquet mensal final é gravado com sucesso.

## Comportamento do Parquet Mensal

Quando já existe `data/processed/agrupamento_oms_[anomes].parquet`, a consolidação mensal combina:

- Parquet mensal existente.
- Parquets de staging dos CSVs novos ainda não processados.

Depois aplica novamente a deduplicação pela chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

O novo resultado é escrito primeiro em `data/raw_temp/` e substitui o Parquet final apenas ao concluir com sucesso.

## Leitura dos CSVs

Os CSVs são lidos com DuckDB usando:

- Separador `|`.
- Cabeçalho na primeira linha.
- União de colunas por nome.
- `all_varchar = true`.
- `nullstr = ['', ' ']`.
- Conversão temporária em streaming para UTF-8, tentando origem em `utf-8`, `cp1252` e `latin-1`.

Esta decisão evita falhas de inferência automática quando uma coluna parece numérica na amostra inicial, mas depois contém espaços em branco ou outros valores textuais.

Antes de entregar o arquivo ao DuckDB, o backend converte o CSV em streaming para um CSV UTF-8 temporário em `data/raw_temp/converted_utf8/`. Essa conversão tenta `utf-8`, depois `cp1252` e depois `latin-1`. O processo não usa `ignore_errors`, portanto linhas não são descartadas silenciosamente.
