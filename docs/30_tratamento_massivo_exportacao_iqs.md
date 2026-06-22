# 30 - Tratamento Massivo e Exportação IQS

## Objetivo

Gerar uma base tratada para envio ao IQS, removendo em massa registros que hoje têm alta probabilidade de falha:

- horário negativo;
- causa/componente ausente;
- sobreposição por interrupção/equipamento.

## Scripts

### Gerar apuração tratada

```bat
python -m backend.scripts.gerar_apuracao_tratada --anomes 202605
```

### Exportar CSV IQS

```bat
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
```

## APIs

### Gerar tratamento

```http
POST /tratamento-massivo/202605/gerar
```

### Consultar resumo

```http
GET /tratamento-massivo/202605/resumo
```

### Exportar CSV

```http
POST /tratamento-massivo/202605/exportar-csv
```

## Entradas

```text
data/mart/apuracao/agrupamento_oms_APURACAO_202605.parquet
data/mart/apuracao/analise_sobreposicao_interrupcao_APURACAO_202605.parquet
```

## Saídas

```text
data/mart/apuracao/agrupamento_oms_APURACAO_202605_TRATADO.parquet
data/mart/apuracao/agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet
data/logs/log_tratamento_massivo_202605.parquet
data/exports/iqs/agrupamento_oms_IQS_[regional]_202605_[timestamp].csv
```

## Observação

O tratamento massivo não altera a base original.

Ele cria uma visão tratada para envio ao IQS e registra os removidos em log, permitindo auditoria e revisão posterior pelo analista.

