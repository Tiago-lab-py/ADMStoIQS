# Fechamento mensal consolidado OMS

## Objetivo

Processar os 5 arquivos consolidados mensais por regional sem alterar a trilha diária já existente.

Essa trilha cria arquivos isolados com prefixo `FECHAMENTO`, permitindo comparar o fechamento oficial do OMS com a apuração diária acumulada.

## Entrada

Copiar os CSVs consolidados para:

```text
data/input/fechamento/{anomes}/
```

Exemplo:

```text
data/input/fechamento/202605/
```

Os arquivos devem conter a competência `YYYYMM` no nome e a regional `CSL`, `LES`, `NRO`, `NRT` ou `OES`.

## Saídas

Processamento bruto consolidado:

```text
data/processed/fechamento/agrupamento_oms_FECHAMENTO_{anomes}.parquet
```

Apuração mensal isolada:

```text
data/mart/apuracao/fechamento/agrupamento_oms_FECHAMENTO_APURACAO_{anomes}.parquet
data/mart/apuracao/fechamento/agrupamento_oms_FECHAMENTO_APURACAO_ATUAL.parquet
```

Base tratada isolada:

```text
data/mart/apuracao/fechamento/agrupamento_oms_FECHAMENTO_APURACAO_{anomes}_TRATADO.parquet
data/mart/apuracao/fechamento/agrupamento_oms_FECHAMENTO_APURACAO_TRATADO_ATUAL.parquet
```

Log de leitura:

```text
data/logs/log_fechamento_csv.parquet
```

## Comandos

Processar os CSVs consolidados:

```bat
python -m backend.scripts.processar_fechamento_mensal --anomes 202605
```

Gerar a apuração mensal isolada:

```bat
python -m backend.scripts.gerar_apuracao_fechamento --anomes 202605
```

Gerar a base tratada isolada:

```bat
python -m backend.scripts.gerar_fechamento_tratado --anomes 202605
```

## Regras da versão inicial

O fechamento mensal:

- não altera `data/processed/agrupamento_oms_YYYYMM.parquet`;
- não altera `data/mart/apuracao/agrupamento_oms_APURACAO_YYYYMM.parquet`;
- não altera `agrupamento_oms_UNION.parquet`;
- preserva as datas originais e cria colunas `_TS` na apuração;
- deduplica pelas mesmas chaves da ingestão diária;
- trata inicialmente:
  - horário negativo;
  - causa/componente ausente.

## Próximas fases

As regras abaixo devem ser adicionadas depois da conferência inicial:

- sobreposição de interrupção em modo fechamento;
- sobreposição UC fase 1 e fase 2 em modo fechamento;
- indicadores DEC/FEC/DIC/FIC/DMIC comparando diário acumulado vs fechamento;
- exportação IQS final a partir do fechamento tratado.
