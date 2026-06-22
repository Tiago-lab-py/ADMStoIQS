# 26 - Frontend Versão Definitiva

## Decisão

O portal gestor React foi promovido para a entrada principal do frontend.

Antes:

```text
http://127.0.0.1:5173/gestor.html
```

Agora:

```text
http://127.0.0.1:5173/
```

## Alteração realizada

Arquivo alterado:

- `frontend/index.html`

A raiz do Vite passou a carregar:

```html
<script type="module" src="/src/gestor-main.tsx"></script>
```

## Páginas mantidas

As páginas de apoio continuam disponíveis:

- `http://127.0.0.1:5173/operacional.html`
- `http://127.0.0.1:5173/gestor.html`
- `http://127.0.0.1:5173/filas.html?anomes=202605`
- `http://127.0.0.1:5173/decisoes.html?anomes=202605`
- `http://127.0.0.1:5173/gestor-filas.html`

## ETL operacional

A tela de ETL não deve ficar misturada ao dashboard executivo.

Ela fica disponível em:

```text
http://127.0.0.1:5173/operacional.html
```

No portal definitivo há o menu `ETL operacional`, com link para abrir a tela completa.

Responsabilidades da tela operacional:

- verificar CSVs pendentes;
- processar CSVs pendentes;
- atualizar `agrupamento_oms_UNION.parquet`;
- gerar `agrupamento_oms_APURACAO_[anomes].parquet`;
- preparar pendências materializadas.

## Estado da versão definitiva

Inclui:

- dashboard executivo somente leitura;
- acesso ao ETL operacional;
- filtro de competência;
- resumo de pendências materializadas;
- acesso à decisão governada;
- link para filas de correção;
- fontes IQS materializadas;
- visão de governança.

## Próximos passos

1. Implementar decisão governada oficial.
2. Integrar login/perfis no portal definitivo.
3. Materializar indicadores DEC/FEC antes/depois.
4. Materializar ressarcimento DIC/FIC/DMIC antes/depois.
5. Criar exportação final IQS com trilha de auditoria.
