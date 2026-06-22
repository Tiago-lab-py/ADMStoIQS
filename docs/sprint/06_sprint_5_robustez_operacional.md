# Sprint 5 — Robustez Operacional, Testes e Observabilidade

## Objetivo

Fortalecer a solução para operação recorrente com grandes volumes, retomada segura, testes automatizados e logs compreensíveis.

## Escopo

- Adicionar testes de backend.
- Validar schema dos CSVs.
- Melhorar tratamento de erro.
- Criar comandos operacionais.
- Criar métricas de processamento.
- Documentar rotina de execução.

## Comandos Operacionais Sugeridos

```text
python -m backend.scripts.processar_csv --todos-pendentes
python -m backend.scripts.processar_csv --anomes 202604
python -m backend.scripts.reprocessar_competencia --anomes 202604
python -m backend.scripts.validar_parquet --anomes 202604
```

## Testes Mínimos

- Deduplicação por `NUM_INTRP_UCI`, `NUM_POSTO_UCI`, `NUM_UC_UCI`.
- Processamento incremental ignorando arquivo já lido.
- Reprocessamento de competência.
- Geração de CSV com cabeçalho oficial.
- Erro funcional para coluna obrigatória ausente.
- Limpeza de `data/raw_temp/` após sucesso.
- Limpeza de `data/raw_temp/` após erro controlado.

## Observabilidade

Registrar em logs técnicos:

- Início e fim do processamento.
- Arquivos encontrados.
- Arquivos ignorados.
- Arquivos processados.
- Tempo por arquivo.
- Total de linhas lidas.
- Total de linhas deduplicadas.
- Caminho do Parquet gerado.
- Caminho dos Parquets de staging, quando aplicável.
- Erros técnicos com stack trace no backend.

## Validações de Segurança

- Não registrar senha em log.
- Não expor token no frontend.
- Não permitir download sem autenticação.
- Não permitir alteração sem usuário autenticado.
- Validar parâmetros de competência no backend.
- Restringir acesso aos arquivos gerados.

## Critérios de Aceite

- Testes mínimos executam com sucesso.
- Processo consegue retomar após interrupção.
- Erros são registrados de forma compreensível.
- Operador consegue processar todos os arquivos pendentes.
- Operador consegue reprocessar uma competência específica.
- Sistema evita acúmulo indevido em `data/raw_temp/`.
