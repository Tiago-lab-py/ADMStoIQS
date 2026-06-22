# Backend ADMStoIQS

Backend Python para ingestão, deduplicação, auditoria e exportação dos dados IQS/ADMS.

## Sprint 0

Esta etapa codifica os contratos mínimos do projeto:

- Diretórios oficiais de entrada, temporários, processados, logs e exports.
- Chave inicial de deduplicação.
- Nome dos artefatos Parquet.
- Schema do `log_leitura_csv.parquet`.
- Schema do `log_alteracoes.parquet`.
- Cabeçalho oficial do CSV exportado.

## Processamento CSV

Processar arquivos pendentes:

```text
python -m backend.scripts.processar_csv
```

Processar uma competência:

```text
python -m backend.scripts.processar_csv --anomes 202604
```

## API Local

Subir a API:

```text
python -m backend.scripts.run_api
```

URL padrão:

```text
http://127.0.0.1:8000
```

Documentação interativa:

```text
http://127.0.0.1:8000/docs
```
