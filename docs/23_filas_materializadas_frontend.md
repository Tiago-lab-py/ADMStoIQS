# 23 - Filas Materializadas no Frontend

## Objetivo

Usar `pendencias_APURACAO_ATUAL.parquet` como fonte principal das filas de correção, evitando recalcular regras pesadas na abertura das telas.

## Arquivos criados

- API: `backend/app/api/filas_routes.py`
- Prévia: `frontend/public/gestor-filas.html`

## Rotas novas

### Resumo das filas

```http
GET /apuracao/filas/resumo
```

Retorna:

- total de pendências;
- pendências por regra;
- pendências por status;
- caminho do parquet atual.

### Consulta por regra

```http
GET /apuracao/filas/{regra}?limit=100&offset=0
```

Regras iniciais:

- `sobreposicao_interrupcao`
- `horario_negativo`
- `sem_causa_componente`

## Prévia para gestor

Com a API e o Vite ativos:

```text
http://127.0.0.1:5173/gestor-filas.html
```

Esta página é somente leitura e apresenta:

- cards das pendências materializadas;
- lista de regras;
- tabela de registros da regra selecionada;
- mensagens visuais de processamento em vermelho e conclusão em verde.

## Critérios de aceite

- `/apuracao/filas/resumo` deve retornar `status=processado`.
- A prévia deve carregar os cards sem recalcular regras.
- Ao clicar em cada regra, a tabela deve listar até 100 registros.
- Se `pendencias_APURACAO_ATUAL.parquet` não existir, a API deve orientar a executar a materialização.

## Próximo passo

Migrar a tela React principal para consumir estas rotas:

- Dashboard executivo: `GET /apuracao/filas/resumo`.
- Página por regra: `GET /apuracao/filas/{regra}`.
- Ações governadas: continuam usando os endpoints de alteração/validação já existentes.

