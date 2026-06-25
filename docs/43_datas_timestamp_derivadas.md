# Datas no fluxo CSV -> Parquet

## Decisão

Os campos de data/hora vindos do CSV ADMS/IQS são preservados no formato original para garantir compatibilidade com o layout de exportação do IQS.

Além disso, o mart `agrupamento_oms_UNION.parquet` passa a publicar colunas derivadas em tipo `TIMESTAMP` para cálculos internos:

- `DATA_HORA_INIC_INTRP_TS`
- `DATA_HORA_FIM_INTRP_TS`
- `DTHR_INICIO_INTRP_UC_TS`

## Formatos aceitos

A conversão tenta, nesta ordem:

1. `dd/MM/yyyy HH:mm:ss`
2. `yyyy-MM-dd HH:mm:ss`
3. conversão nativa DuckDB para `TIMESTAMP`

## Uso esperado

- Exportação IQS: usa as colunas originais, sem sufixo `_TS`.
- Indicadores, ressarcimento, sobreposição e outliers: devem preferir as colunas `_TS` quando disponíveis.
- Reprocessamentos antigos continuam possíveis porque os serviços ainda podem parsear as colunas originais quando necessário.

## Regeneração

Após alterar esse contrato, regenere o UNION e a apuração:

```bat
python -m backend.scripts.gerar_oms_union
python -m backend.scripts.orquestrar_apuracao --anomes 202605
```

Se não quiser rodar a trilha completa, gere a apuração pelo botão de ETL operacional no portal.

## Ajuste único dos Parquets já processados

Para evitar reler todos os CSVs da pasta `P:\Common\IQS\ADMS\Backup`, existe uma rotina de normalização dos Parquets já gerados em `data/processed`.

Ela adiciona as colunas `_TS` somente quando faltarem:

```bat
python -m backend.scripts.normalizar_datas_processados
```

Para ajustar uma competência específica:

```bat
python -m backend.scripts.normalizar_datas_processados --anomes 202605
```

Por padrão a rotina não cria backup completo, porque os arquivos são grandes e a substituição usa arquivo temporário. Se desejar backup explícito:

```bat
python -m backend.scripts.normalizar_datas_processados --backup
```

Depois rode:

```bat
python -m backend.scripts.gerar_oms_union
```
