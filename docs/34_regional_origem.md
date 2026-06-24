# Regional de Origem

## Objetivo

Garantir que o pipeline consiga reconstruir os CSVs finais por regional sem gerar registros indevidos em `SEM_REGIONAL`.

## Coluna final

A coluna operacional usada pelo projeto é:

```text
REGIONAL_ORIGEM
```

Ela deve conter uma das regionais:

```text
CSL, NRT, NRO, LES, OES, COPEL
```

## Regra de prioridade

Na consolidação do `OMS_union` e nos indicadores, a regional passa a ser normalizada a partir de:

1. `SIGLA_REGIONAL`, quando preenchida;
2. `REGIONAL_ORIGEM`, quando `SIGLA_REGIONAL` estiver vazia;
3. `COPEL`, quando não houver valor reconhecido.

## Conversão

```sql
CASE
    WHEN SIGLA_REGIONAL = 'P' THEN 'CSL'
    WHEN SIGLA_REGIONAL = 'L' THEN 'NRT'
    WHEN SIGLA_REGIONAL = 'M' THEN 'NRO'
    WHEN SIGLA_REGIONAL = 'C' THEN 'LES'
    WHEN SIGLA_REGIONAL = 'V' THEN 'OES'
    ELSE 'COPEL'
END
```

Também são aceitos valores já normalizados:

```text
CSL, NRT, NRO, LES, OES
```

## Reprocessamento necessário

Para refletir a nova regra nos arquivos finais, reprocessar:

```powershell
python -m backend.scripts.gerar_oms_union
python -m backend.scripts.executar_etl_apuracao --anomes 202605
python -m backend.scripts.gerar_apuracao_tratada --anomes 202605
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
```

Se o nome do script de ETL mensal estiver diferente no ambiente, usar o endpoint ou comando já utilizado para gerar `agrupamento_oms_APURACAO_[anomes].parquet`.
