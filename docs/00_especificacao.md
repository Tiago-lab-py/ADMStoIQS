# 00 - Apuração com Polars

Este documento descreve como o script de apuração em Polars calcula os indicadores de continuidade a partir dos parquets mensais.

## Objetivo

Ler os dados de interrupção e HCAI em `data/processed`, consolidar eventos por UC, classificar eventos (Líquido/Expurgo), separar curta/longa duração e gerar resumo com métricas operacionais e regulatórias em Excel.

## Entradas

- `df_interrupcao_{ano}_{mes}.parquet`
- `df_hcai_{ano}_{mes}.parquet`
- `consumidores.csv` (opcional; se não existir, usa tabela padrão no código)

## Saídas

- `data/output/resumo_ci_chi_{ano}_{mes}.xlsx` com abas:
- `resumo_origem`
- `copel`
- `consumidores`
- `metadata`
- uma aba por origem/regional

## Regras de classificação

### Expurgo x Líquido

Se existir protocolo justificando expurgo (`TIPO_PROTOC_JUSTIF_*`) e ele não for vazio nem `"0"`, o registro é classificado como `Expurgo`. Caso contrário, `Liquido`.

- Em `df_interrupcao`, usa `TIPO_PROTOC_JUSTIF_INTRP`.
- Em `df_hcai`, usa `TIPO_PROTOC_JUSTIF_UCI` ou `TIPO_PROTOC_JUSTIF_INTRP`.

### Área I

`is_area_i = True` quando `COD_AREA_ELET_INTRP <= 6`.  
Se a coluna não existir, considera `False`.

## Preparação e limpeza do HCAI

## 1) Normalização de datas

As colunas de início/fim são convertidas para `Datetime`, aceitando formatos:

- `%d/%m/%Y %H:%M:%S`
- `%Y-%m-%d %H:%M:%S`
- parse genérico do Polars

## 2) Deduplicação por chave técnica

Quando disponíveis, os campos `NUM_INTRP_UCI`, `NUM_POSTO_UCI` e `NUM_UC_UCI` formam a chave.

- Registros com chave completa são deduplicados mantendo o último (ordenando por `snapshot_ts`, `DATA_HORA_FIM_INTRP` e `arquivo_csv` quando existirem).
- Registros sem chave completa são mantidos.

## 3) Filtro de consistência temporal

Mantém somente linhas com:

- início não nulo
- fim não nulo
- `fim >= início`

## 4) Merge de intervalos sobrepostos (por UC)

O algoritmo ordena por UC (e por origem quando `by_origin=True`) e agrupa períodos que se sobrepõem:

- Calcula `max_fim_ate_agora` (máximo acumulado de fim no grupo).
- Compara início atual com `max_fim_anterior`.
- Se `início > max_fim_anterior`, abre novo período.
- Soma acumulada desses “novos períodos” gera `periodo_id`.
- Agrega por `periodo_id` usando:
- menor início
- maior fim
- primeira regional
- máximo de `is_expurgo` e `is_area_i`

Assim, múltiplas linhas técnicas de uma mesma interrupção contínua viram 1 evento consolidado.

## 5) Duração e tipo da interrupção

Para cada período consolidado:

- `duracao_min = (fim - início) em minutos` (com piso 0)
- `chi_individual = duracao_min / 60`
- `tipo_intrp = "Longa"` se `duracao_min >= 3`, senão `"Curta"`

## Métricas calculadas

Após consolidação, cada linha representa 1 interrupção de UC.

- `CI = 1` por linha
- `CHI = chi_individual`
- `CI_longa`: conta apenas longas
- `CHI_longa`: soma CHI apenas longas
- `CI_curta`: conta apenas curtas
- `CHI_curta`: soma CHI apenas curtas
- `CIi_longa`: conta longas em Área I
- `CHIi_longa`: soma CHI de longas em Área I

Essas métricas são agregadas por:

- `arquivo_origem`
- `classificacao` (`Expurgo`/`Liquido`)

## Distintos de interrupção (base ADMS)

Do `df_interrupcao`, também são calculados:

- `qtd_ocorrencias_distintas = n_unique(NUM_OCORRENCIA_ADMS)`
- `qtd_interrupcoes_distintas = n_unique(PID)`

Também por `arquivo_origem` e `classificacao`.

## Consumidores

O arquivo de consumidores é normalizado para colunas:

- `regional`
- `consumidores`
- `mes`

Se não houver linha para o mês solicitado, usa o conjunto inteiro disponível.  
No join final, `regional` é renomeada para `arquivo_origem`.

## Indicadores finais

Com base nas métricas longas/curtas e no total de consumidores:

- `FEC = CI_longa / consumidores`
- `DEC = CHI_longa / consumidores`
- `FM_fec = CI_curta / consumidores`
- `FM_dec = CHI_curta / consumidores`
- `FECi = CIi_longa / consumidores`
- `DECi = CHIi_longa / consumidores`

Se `consumidores <= 0`, os indicadores ficam `0`.

## Visão por origem e visão Copel

O script monta dois cenários:

- **Por origem/regional**: merge com `by_origin=True`.
- **Percepção Copel**: merge com `by_origin=False`, unificando tudo como `arquivo_origem = "Copel"`.

No cenário Copel:

- consumidores = soma de consumidores de todas regionais
- distintos (`NUM_OCORRENCIA_ADMS`, `PID`) agregados por `classificacao`

## Ordenação final

`resumo_final` é ordenado por origem na sequência:

- `CSL`, `LES`, `NRO`, `NRT`, `OES`, `Copel`

E dentro de cada origem:

- `Expurgo`
- `Liquido`

## Totais impressos no console

No fim da execução:

- `CI` total (soma da aba Copel)
- `CHI` total
- `FEC` total (usando `qtd_intrp_longas / consumidores_totais`)
- `DEC` total ponderado por consumidores:
- numerador: `sum(DEC * consumidores)`
- denominador: `consumidores_totais`

## Resumo conceitual do cálculo

1. Classifica evento em Expurgo/Líquido.
2. Consolida sobreposições de tempo por UC (evita dupla contagem).
3. Separa curta (<3 min) e longa (>=3 min).
4. Soma contagens e horas de interrupção.
5. Divide por consumidores para obter FEC/DEC e métricas associadas.
## Ingestão local das interrupções IQS/ADMS

### Objetivo

Ler os arquivos CSV de interrupções gerados em `P:\Common\IQS\ADMS\Backup`, a partir de abril de 2026, remover registros duplicados e materializar uma base local analítica em Parquet.

O resultado final de cada mês deve ser um arquivo:

```text
agrupamento_oms_[anomes].parquet
```

Exemplo:

```text
agrupamento_oms_202604.parquet
```

### Origem dos dados

- Diretório de entrada: `P:\Common\IQS\ADMS\Backup`
- Padrão esperado de arquivos: `Interrupcoes_IQS_YYYYMMDDHHMMSS_[tipo].CSV`
- Marco inicial de processamento: arquivos referentes a `202604` em diante
- Volume estimado: aproximadamente `40 GB` de CSV por mês
- O sufixo `[tipo]` deve ser preservado como regional de origem na coluna técnica `REGIONAL_ORIGEM`, por exemplo `CSL`, `LES`, `NRO`, `NRT` e `OES`.

### Chave de deduplicação

Os registros devem ser considerados duplicados quando possuírem a mesma combinação dos campos:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

Para cada chave duplicada, o processo deve manter apenas uma ocorrência no resultado mensal. Quando houver coluna de data/hora de atualização, extração ou processamento disponível no CSV, a regra preferencial é manter o registro mais recente. Caso contrário, manter a primeira ocorrência lida de forma determinística.

### Estratégia técnica

Usar `DuckDB` como motor local de leitura, transformação e gravação, evitando carregar os arquivos completos em memória.

Fluxo esperado:

1. Localizar os CSVs em `P:\Common\IQS\ADMS\Backup`.
2. Filtrar somente arquivos com competência `YYYYMM >= 202604`.
3. Agrupar os arquivos por mês de competência.
4. Ler os CSVs do mês com `DuckDB` usando leitura vetorizada.
5. Padronizar nomes e tipos de colunas quando necessário.
6. Remover duplicados pela chave `NUM_INTRP_UCI`, `NUM_POSTO_UCI`, `NUM_UC_UCI`.
7. Gravar o resultado em Parquet local.

Os CSVs devem ser lidos como texto, com separador `|`, convertidos temporariamente para UTF-8 em streaming, aceitando origem em `utf-8`, `cp1252` e `latin-1` para suportar arquivos legados sem descartar linhas.

### Saída

Para cada mês processado, gerar um único arquivo Parquet:

```text
data/parquet/agrupamento_oms_[anomes].parquet
```

Onde `[anomes]` representa a competência no formato `YYYYMM`.

Exemplos:

- `data/parquet/agrupamento_oms_202604.parquet`
- `data/parquet/agrupamento_oms_202605.parquet`
- `data/parquet/agrupamento_oms_202606.parquet`

### Leitor DuckDB

O leitor deve ser implementado para processar um mês por vez, com baixo uso de memória e sem depender de banco externo.

Requisitos mínimos:

- Usar banco DuckDB local temporário ou persistente para staging.
- Ler CSVs diretamente da pasta de origem.
- Aceitar arquivos grandes sem conversão intermediária obrigatória.
- Gerar Parquet comprimido, preferencialmente com `ZSTD` ou `SNAPPY`.
- Permitir reprocessamento seguro de um mês, sobrescrevendo o Parquet final daquele mês.
- Registrar quantidade de linhas lidas, quantidade de linhas após deduplicação e caminho do arquivo gerado.

Exemplo conceitual de transformação:

```sql
COPY (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY NUM_INTRP_UCI, NUM_POSTO_UCI, NUM_UC_UCI
                ORDER BY 1
            ) AS rn
        FROM read_csv_auto($arquivos_csv, union_by_name = true)
    )
    WHERE rn = 1
)
TO $arquivo_saida
(
    FORMAT PARQUET,
    COMPRESSION ZSTD
);
```

Caso seja identificada uma coluna confiável de atualização ou extração, substituir `ORDER BY 1` por ordenação descendente desta coluna para preservar o registro mais recente.

### Banco local opcional

Além do Parquet final, o processo pode manter um arquivo DuckDB local para auditoria e consultas incrementais:

```text
data/duckdb/adms_iqs.duckdb
```

Este banco pode conter tabelas de controle, como:

- `controle_processamento`
- `arquivos_processados`
- `metricas_processamento`

O Parquet mensal continua sendo o artefato oficial de saída.

### Critérios de aceite

- Processa arquivos de `202604` em diante.
- Gera um Parquet por mês no padrão `agrupamento_oms_[anomes].parquet`.
- Remove duplicados pela chave `NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI`.
- Usa `DuckDB` para leitura e transformação.
- Suporta volumes mensais de aproximadamente `40 GB` de CSV.
- Permite reprocessar competências sem acumular duplicidade no resultado final.
# Especificação ADMStoIQS

## Visão Geral

O projeto ADMStoIQS processa arquivos CSV OMS/IQS da pasta:

```text
P:\Common\IQS\ADMS\Backup
```

A partir de abril de 2026, os arquivos são lidos com DuckDB, convertidos para parquet, deduplicados e consolidados em um mart local.

## Fluxo de Dados

1. Verificar CSVs pendentes na pasta de origem.
2. Processar CSVs pendentes de forma incremental.
3. Converter temporariamente para UTF-8 quando necessário.
4. Gravar staging temporário por arquivo.
5. Gerar parquet mensal em `data/processed`.
6. Unificar os parquets mensais em `data/mart/agrupamento_oms_UNION.parquet`.
7. Escolher mês de apuração.
8. Filtrar `UNION` por `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`.
9. Gerar `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`.
10. Aplicar validações, rejeições e correções auditáveis sobre a apuração.
11. Gerar `agrupamento_oms_APURACAO_[anomes]_corrigido.parquet`.
12. Exportar CSVs regionais finais.

## CSV Pendente vs Mês de Apuração

A verificação de CSV pendente não deve depender do mês de apuração.

Um arquivo CSV incluído no mês corrente pode conter registros que atualizam o mês de apuração anterior.

Por isso o fluxo correto é:

1. processar todos os CSVs pendentes;
2. atualizar o `UNION`;
3. selecionar o mês de apuração;
4. filtrar por datas reais de início e fim.

## Deduplicação

A chave de deduplicação é:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

## Parquets

### Mensais

Formato:

```text
data/processed/agrupamento_oms_[anomes].parquet
```

Exemplo:

```text
data/processed/agrupamento_oms_202604.parquet
```

### Mart Único

Formato:

```text
data/mart/agrupamento_oms_UNION.parquet
```

Este arquivo não é mensal. Ele contém todos os registros consolidados.

### Mart Corrigido

Formato:

```text
data/mart/agrupamento_oms_UNION_corrigido.parquet
```

Este é o arquivo usado pelo frontend para análise, validação, rejeição e exportação.

## Competência Lógica

O frontend usa a competência lógica:

```text
UNION
```

Ela representa o mart completo. A coluna `ANOMES_PROCESSAMENTO` permanece apenas para filtro e rastreabilidade.

## Governança

O parquet corrigido deve conter colunas de validação:

- `validado`
- `status_validacao`
- `motivo_status`
- `usuario_validacao`
- `data_hora_validacao`

O log de alterações deve registrar usuário, perfil, IP, PC/host, chave, campo, valor original, valor novo, justificativa e status.

## Princípio de Tratamento

A ferramenta deve aplicar lógicas robustas para reduzir o volume de análise, mas não substituir a decisão do analista em casos ambíguos.

Exemplo:

- Horário negativo pode receber sugestão de ajuste.
- O analista pode aceitar, rejeitar, ignorar ou manter pendente.
