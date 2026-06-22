# CSVs pendentes na tela de ETL

## Objetivo

A janela **CSVs pendentes** da tela de ETL deve funcionar como fila operacional.
Ela não deve listar os arquivos já processados no `log_leitura_csv.parquet`.

## Regra de exibição

- A API compara a pasta `P:\Common\IQS\ADMS\Backup` com `data/logs/log_leitura_csv.parquet`.
- A comparação considera o caminho completo normalizado e o nome do arquivo.
- Arquivos com `status = processado` no log são usados apenas para contagem interna.
- A lista visual `arquivos` retorna somente arquivos ainda acionáveis, ou seja, pendentes de processamento/reprocessamento.

## Indicadores

- `arquivos_encontrados`: total de CSVs encontrados na pasta.
- `arquivos_processados`: total já marcado como `processado` no log.
- `arquivos_pendentes`: quantidade que aparece na tabela operacional.
- `arquivos_com_erro`: quantidade registrada com erro no log e ainda sujeita a revisão/reprocessamento.

## Resultado esperado

Quando todos os CSVs da pasta já estiverem registrados como `processado` no log:

- a tabela de pendentes deve ficar vazia;
- os arquivos processados continuam disponíveis no parquet de log para auditoria;
- a tela não deve exibir o histórico completo do log.
