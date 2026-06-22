# CSV OMS para Parquet

## Objetivo

Converter os arquivos CSV de interrupções OMS/IQS/ADMS em Parquets mensais deduplicados, mantendo rastreabilidade dos arquivos lidos e preservando a regional de origem.

O artefato final mensal é:

```text
data/processed/agrupamento_oms_[anomes].parquet
```

Exemplo:

```text
data/processed/agrupamento_oms_202604.parquet
```

## Origem

Diretório de entrada:

```text
P:\Common\IQS\ADMS\Backup
```

Padrão de arquivos aceito:

```text
Interrupcoes_IQS_YYYYMMDDHHMMSS_[REGIONAL].CSV
```

Exemplos:

```text
Interrupcoes_IQS_20260430033012_CSL.CSV
Interrupcoes_IQS_20260430033539_LES.CSV
Interrupcoes_IQS_20260430034122_NRO.CSV
Interrupcoes_IQS_20260430034640_NRT.CSV
Interrupcoes_IQS_20260430035353_OES.CSV
```

São processados arquivos a partir da competência:

```text
202604
```

## Regional de Origem

O sufixo do nome do arquivo é preservado no Parquet final na coluna técnica:

```text
REGIONAL_ORIGEM
```

Exemplos de valores:

- `CSL`
- `LES`
- `NRO`
- `NRT`
- `OES`

Esta coluna é usada posteriormente para reconstruir os CSVs finais por regional.

## Estratégia de Processamento

O processamento é incremental e feito por competência.

Fluxo:

1. Descobrir arquivos CSV na pasta de origem.
2. Filtrar arquivos da competência solicitada.
3. Consultar `log_leitura_csv.parquet`.
4. Ignorar arquivos já processados com sucesso.
5. Converter cada CSV pendente para UTF-8 temporário.
6. Converter cada CSV UTF-8 temporário para Parquet de staging.
7. Consolidar os Parquets de staging com o Parquet mensal existente, se houver.
8. Remover duplicidades.
9. Gravar o Parquet mensal final.
10. Registrar sucesso ou erro no log de leitura.
11. Limpar arquivos temporários.

## Áreas de Dados

### Temporários

```text
data/raw_temp/
```

Usada para arquivos temporários durante o processamento.

Subpasta usada para conversão de encoding:

```text
data/raw_temp/converted_utf8/
```

Esta área é limpa ao final do processamento.

### Staging Incremental

```text
data/duckdb/staging/[anomes]/
```

Cada CSV pendente é convertido individualmente para um Parquet de staging.

Se o processamento for interrompido, os Parquets de staging já criados podem ser reaproveitados na próxima execução.

Após sucesso completo de uma competência, o staging mensal é removido.

### Processados

```text
data/processed/
```

Contém o Parquet mensal deduplicado:

```text
agrupamento_oms_[anomes].parquet
```

### Logs

```text
data/logs/log_leitura_csv.parquet
```

Controla arquivos lidos, pendentes, processados e com erro.

## Deduplicação

Critério inicial de remoção de duplicidades:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

Colunas:

- `NUM_INTRP_UCI`
- `NUM_POSTO_UCI`
- `NUM_UC_UCI`

Regra atual:

- Mantém uma ocorrência por chave.
- Quando já existe Parquet mensal, os dados existentes têm prioridade sobre os novos durante a consolidação.
- Critérios mais detalhados por UC serão incluídos em sprint posterior.

## Encoding dos CSVs

Os CSVs podem conter caracteres legados e nem sempre estão em UTF-8.

Antes da leitura pelo DuckDB, o backend converte cada arquivo em streaming para UTF-8 tentando os encodings:

1. `utf-8`
2. `cp1252`
3. `latin-1`

O processo não usa `ignore_errors`, portanto linhas não são descartadas silenciosamente.

## Leitura com DuckDB

Os CSVs são lidos com:

- Separador `|`
- Cabeçalho na primeira linha
- `all_varchar = true`
- `union_by_name = true`
- `nullstr = ['', ' ']`

A decisão de ler tudo como texto evita falhas de inferência automática, por exemplo quando uma coluna parece numérica no início do arquivo e depois contém espaço em branco ou texto.

## Log de Leitura

Arquivo:

```text
data/logs/log_leitura_csv.parquet
```

Campos principais:

| Campo | Descrição |
|---|---|
| `arquivo_path` | Caminho completo do CSV |
| `arquivo_nome` | Nome do arquivo |
| `arquivo_tamanho_bytes` | Tamanho do arquivo |
| `arquivo_modificado_em` | Data/hora de modificação |
| `arquivo_hash` | Reservado para hash futuro |
| `anomes` | Competência processada |
| `processado_em` | Data/hora do processamento |
| `status` | `processado`, `erro` ou `ignorado` |
| `linhas_lidas` | Linhas lidas do arquivo |
| `linhas_processadas` | Linhas no Parquet final consolidado |
| `mensagem_erro` | Erro técnico, quando existir |

Um arquivo é considerado já processado somente quando existe log com:

```text
status = processado
```

Erros não bloqueiam nova tentativa.

## Comandos Operacionais

Todos os comandos devem ser executados na raiz do projeto:

```text
D:\ADMStoIQS
```

Ativar ambiente virtual:

```powershell
d:\ADMStoIQS\.venv\Scripts\activate.bat
```

Validar contratos:

```powershell
python -m backend.scripts.validate_contracts
```

Listar arquivos de uma competência:

```powershell
python -m backend.scripts.listar_csv --anomes 202604
```

Processar uma competência:

```powershell
python -m backend.scripts.processar_csv --anomes 202604
```

Processar todos os arquivos pendentes:

```powershell
python -m backend.scripts.processar_csv --todos-pendentes
```

Compactar logs repetidos:

```powershell
python -m backend.scripts.compactar_log_leitura
```

Resetar uma competência para reprocessar do zero:

```powershell
python -m backend.scripts.resetar_competencia --anomes 202604 --remover-parquet --remover-staging
```

## Acompanhamento no Terminal

Durante o processamento, o terminal mostra progresso por arquivo:

```text
[202604] Arquivo 1 de 10 | CSL | Interrupcoes_IQS_20260430033012_CSL.CSV
[202604] OK 1 de 10 | linhas=96421
[202604] Arquivo 2 de 10 | LES | Interrupcoes_IQS_20260430033539_LES.CSV
```

Ao final, mostra resumo da competência:

```text
Processamento incremental concluído.
Arquivos encontrados: 10
Arquivos pendentes: 10
Meses processados: 1
anomes=202604 | arquivos=10 | erros=0 | linhas_lidas=3409800 | linhas_processadas=2543306 | parquet=D:\ADMStoIQS\data\processed\agrupamento_oms_202604.parquet
```

## Reprocessamento Seguro

Para reprocessar uma competência do zero:

```powershell
python -m backend.scripts.resetar_competencia --anomes 202604 --remover-parquet --remover-staging
python -m backend.scripts.processar_csv --anomes 202604
```

Este comando remove:

- Registros da competência em `log_leitura_csv.parquet`.
- Parquet final mensal, se existir.
- Staging da competência, se existir.

## Validação do Resultado

Após processar uma competência, validar:

1. Existência do Parquet final:

```text
data/processed/agrupamento_oms_[anomes].parquet
```

2. Presença da coluna:

```text
REGIONAL_ORIGEM
```

3. Existência de registros `status = processado` no log:

```text
data/logs/log_leitura_csv.parquet
```

4. Ausência de excesso de arquivos em:

```text
data/raw_temp/
```

## Problemas Conhecidos e Tratamento

### Erro de conversão numérica

Exemplo:

```text
Could not convert string " " to BIGINT
```

Tratamento:

- Ler todas as colunas como texto com `all_varchar = true`.

### Erro de Unicode

Exemplo:

```text
Invalid unicode (byte sequence mismatch) detected.
```

Tratamento:

- Converter o CSV para UTF-8 temporário usando `utf-8`, `cp1252` ou `latin-1`.

### Arquivo com erro

Tratamento:

- O erro é registrado por arquivo.
- Arquivos válidos da mesma competência continuam sendo processados.
- Arquivos com `status = erro` podem ser tentados novamente em execução futura.

### Muitos registros repetidos no log

Tratamento:

```powershell
python -m backend.scripts.compactar_log_leitura
```

## Relação com Exportação CSV

Este processo gera o Parquet mensal base.

A exportação final para CSV oficial é feita pela API da Sprint 2, usando:

```text
POST /competencias/{anomes}/exportar-csv
POST /competencias/{anomes}/exportar-csv-regionais
```

A reconstrução por regional depende da coluna:

```text
REGIONAL_ORIGEM
```

