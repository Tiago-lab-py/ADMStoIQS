# Mart OMS Union

## Objetivo

Unificar os Parquets mensais processados em um único Parquet analítico, removendo duplicidades por UC e criando colunas derivadas de duração.

Arquivo final:

```text
data/mart/OMS_union.parquet
```

Arquivo corrigido após aplicação de alterações governadas:

```text
data/mart/OMS_union_corrigido.parquet
```

## Entradas

Arquivos mensais em:

```text
data/processed/
```

Padrão:

```text
agrupamento_oms_[anomes].parquet
```

Exemplos:

```text
agrupamento_oms_202604.parquet
agrupamento_oms_202605.parquet
agrupamento_oms_202606.parquet
```

## Saída

```text
data/mart/OMS_union.parquet
```

## Mart Corrigido

O arquivo `OMS_union.parquet` deve ser tratado como a base consolidada original.

As alterações aprovadas ou aplicadas a partir da governança devem gerar um novo arquivo:

```text
data/mart/OMS_union_corrigido.parquet
```

Esse arquivo é produzido a partir de:

- `data/mart/OMS_union.parquet`
- `data/logs/log_alteracoes.parquet`

Somente alterações com status:

- `aprovado`
- `aplicado`

são consideradas no mart corrigido.

Comando:

```powershell
python -m backend.scripts.gerar_oms_corrigido
```

Endpoint:

```text
POST /mart/oms-corrigido
```

Permissão:

- `gestor`
- `admin`

Quando `OMS_union_corrigido.parquet` existir, a API deve preferir este arquivo para consulta, filas de tratamento e exportação.

Exportar os CSVs regionais atualizados de uma competência:

```powershell
python -m backend.scripts.exportar_csv_regionais --anomes 202604
```

Exportar os CSVs regionais atualizados de todas as competências disponíveis:

```powershell
python -m backend.scripts.exportar_csv_regionais
```

## Deduplicação

A remoção de duplicidades usa a chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

Colunas:

- `NUM_INTRP_UCI`
- `NUM_POSTO_UCI`
- `NUM_UC_UCI`

## Colunas Derivadas

### `ANOMES_PROCESSAMENTO`

Competência de origem do registro, extraída do nome do Parquet mensal.

Exemplo:

```text
agrupamento_oms_202604.parquet -> 202604
```

Esta coluna permite que a API e o frontend usem o `OMS_union.parquet` como fonte principal, mantendo filtros por competência.

### `duracao`

Duração da interrupção em minutos.

Origem:

- `DATA_HORA_INIC_INTRP`
- `DATA_HORA_FIM_INTRP`

Formatos aceitos:

- `DD/MM/YYYY HH:MM:SS`
- `YYYY-MM-DD HH:MM:SS`

Quando alguma data não puder ser interpretada, `duracao` fica nula.

### `erro_duracao`

Coluna booleana.

Regra:

```text
duracao < 0
```

Indica registros em que a data/hora final é menor que a data/hora inicial.

### `duracao_longa`

Coluna booleana.

Regra:

```text
duracao >= 3
```

Indica interrupções com duração maior ou igual a 3 minutos.

## Comando Operacional

Executar na raiz do projeto:

```powershell
python -m backend.scripts.gerar_oms_union
```

Exemplo de saída:

```text
Mart OMS union gerado com sucesso.
Arquivos origem: 3
Linhas origem: 7500000
Linhas saída: 7200000
Parquet: D:\ADMStoIQS\data\mart\OMS_union.parquet
```

## Acompanhamento no Terminal

O processamento exibe etapas no terminal para indicar progresso:

```text
[OMS_union] inicio | inicio | Iniciando geração do mart OMS_union.
[OMS_union] descobrir_arquivos | processando | Buscando Parquets mensais em D:\ADMStoIQS\data\processed.
[OMS_union] descobrir_arquivos | sucesso | Encontrados 3 arquivo(s), 12.345.678 bytes.
[OMS_union] Arquivo origem 1 de 3 | agrupamento_oms_202604.parquet | 123.456 bytes
[OMS_union] Criando view com os Parquets mensais...
[OMS_union] Validando colunas obrigatórias...
[OMS_union] Contando linhas de origem...
[OMS_union] Deduplicando e gravando Parquet temporário...
[OMS_union] Contando linhas de saída...
[OMS_union] Publicando Parquet final...
[OMS_union] fim | sucesso | Mart OMS_union gerado com sucesso.
```

Durante a etapa `Deduplicando e gravando Parquet temporário`, o DuckDB executa uma operação única de escrita. Esta etapa pode demorar em bases grandes, mas o início e o fim são registrados no terminal e no log.

## Log do Processamento

Arquivo:

```text
data/logs/log_oms_union.parquet
```

Campos:

| Campo | Descrição |
|---|---|
| `run_id` | Identificador único da execução |
| `etapa` | Etapa do processamento |
| `status` | `inicio`, `processando`, `sucesso` ou `erro` |
| `mensagem` | Mensagem operacional |
| `arquivos_origem` | Quantidade de Parquets mensais usados |
| `linhas_origem` | Total de linhas antes da deduplicação |
| `linhas_saida` | Total de linhas no mart final |
| `parquet_path` | Caminho do Parquet relacionado |
| `criado_em` | Data/hora do registro |

Consultar últimas etapas:

```powershell
python -m backend.scripts.listar_log_oms_union
```

Consultar uma quantidade específica:

```powershell
python -m backend.scripts.listar_log_oms_union --limit 50
```

## Validação

Validar contratos:

```powershell
python -m backend.scripts.validate_contracts
```

Conferir arquivo final:

```text
data/mart/OMS_union.parquet
```

## Observações

- O processo usa DuckDB.
- A união lê todos os Parquets mensais em `data/processed/`.
- O arquivo final é escrito primeiro em `data/raw_temp/` e substitui `data/mart/OMS_union.parquet` apenas no sucesso.
- As etapas são exibidas no terminal e gravadas em `data/logs/log_oms_union.parquet`.
- A coluna `REGIONAL_ORIGEM` é preservada quando existir nos Parquets mensais.
- A coluna `ANOMES_PROCESSAMENTO` é criada a partir do nome dos Parquets mensais.
- O arquivo `OMS_union_corrigido.parquet` é derivado do `OMS_union.parquet` e não substitui a base original.
- A última coluna solicitada após “criar a colu...” ainda precisa ser confirmada.
# Mart OMS Union

## Objetivo

Consolidar todos os parquets mensais de `data/processed` em uma base única de trabalho para consulta, tratamento, validação e exportação OMS.

O mart não é mensal. Ele representa o universo consolidado disponível para análise.

## Arquivos

- Fonte consolidada: `data/mart/agrupamento_oms_UNION.parquet`
- Base de trabalho corrigida: `data/mart/agrupamento_oms_UNION_corrigido.parquet`
- Compatibilidade legada:
  - `data/mart/OMS_union.parquet`
  - `data/mart/OMS_union_corrigido.parquet`

## Competência Lógica

Para reaproveitar telas e endpoints que esperavam uma competência mensal, o mart único usa a competência lógica:

- `UNION`

A coluna `ANOMES_PROCESSAMENTO` permanece no parquet apenas para rastreabilidade e filtros internos. Ela não representa arquivos separados no frontend.

## Deduplicação

A união remove duplicados pela chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

## Colunas Derivadas

O mart deve conter:

- `ANOMES_PROCESSAMENTO`: competência de origem do parquet mensal.
- `duracao`: duração em minutos.
- `erro_duracao`: booleano para duração negativa.
- `duracao_longa`: booleano para duração maior ou igual a 3 minutos.

## Base de Apuração Corrigida

O `UNION` é fonte consolidada e não deve ser corrigido diretamente.

A base de trabalho do analista é a apuração mensal:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

Após decisões, deve ser gerada a versão corrigida:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_corrigido.parquet
```

Além dos dados da apuração, ela deve conter colunas de governança:

- `validado`: booleano indicando se o registro foi analisado e validado.
- `status_validacao`: estado do registro na trilha.
- `motivo_status`: justificativa operacional.
- `usuario_validacao`: usuário responsável pela última decisão.
- `data_hora_validacao`: data e hora da última decisão.

Estados sugeridos para `status_validacao`:

- `pendente`
- `em_analise`
- `validado`
- `rejeitado`
- `ignorado`
- `aplicado`

## Princípio Operacional

As regras automáticas devem reduzir o volume de análise, mas não forçar correções quando o caso exigir julgamento humano.

Exemplo:

- Horário negativo pode ser sugerido pela aplicação.
- O analista pode aceitar, rejeitar ou deixar pendente para tratar futuramente.
- Toda decisão deve ser registrada em `log_alteracoes.parquet`.

## Endpoints Preferenciais

As telas devem usar os endpoints de mart:

- `GET /competencias`
- `GET /mart/dados`
- `GET /mart/amostra`
- `POST /mart/exportar-csv`
- `POST /mart/exportar-csv-regionais`
- `POST /mart/oms-corrigido`

Os endpoints com `{anomes}` permanecem apenas para compatibilidade.

## Situação Atual

- `agrupamento_oms_UNION.parquet` é o consolidado bruto.
- Endpoints de governança disponíveis no Swagger.
- Próximo passo: gerar apuração mensal e materializar corrigido por apuração.

## Apuração Mensal

Antes do dashboard, a aplicação deve executar um ETL de apuração para criar uma base mensal de trabalho:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

O alias ativo para consulta é:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_ATUAL.parquet
```

Quando esse arquivo existe, os endpoints `/mart/dados`, `/mart/resumo` e exportações passam a trabalhar sobre ele.

Após decisões, `POST /mart/oms-corrigido` materializa:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_corrigido.parquet
```

e atualiza:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_CORRIGIDO_ATUAL.parquet
```

Detalhes:

- `docs/06_etl_apuracao.md`
