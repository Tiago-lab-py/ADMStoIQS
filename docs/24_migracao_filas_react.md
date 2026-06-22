# 24 - Migração das Filas Materializadas para React

## Objetivo

Migrar a prévia estática `gestor-filas.html` para uma tela React oficial, mantendo a tela antiga como fallback até estabilizar a navegação principal.

## Arquivos criados

- `frontend/src/filasApi.ts`
- `frontend/src/FilasMaterializadasApp.tsx`
- `frontend/src/filasMaterializadas.css`
- `frontend/src/filas-main.tsx`
- `frontend/filas.html`

## URL de validação

Com Vite ativo:

```text
http://127.0.0.1:5173/filas.html
```

Também é possível abrir já com competência:

```text
http://127.0.0.1:5173/filas.html?anomes=202605
```

A página estática antiga ganhou um botão:

```text
http://127.0.0.1:5173/gestor-filas.html
```

Botão: `Abrir versão React`.

## APIs consumidas

- `GET /apuracao/filas/resumo?anomes=202605`
- `GET /apuracao/filas/{regra}?anomes=202605&limit=100&offset=0`

Se `anomes` não for informado, a API usa `pendencias_APURACAO_ATUAL.parquet`.

## Comportamento esperado

- Cards carregam a partir de `pendencias_APURACAO_ATUAL.parquet`.
- O campo `Competência` permite alternar o parquet `pendencias_APURACAO_[anomes].parquet`.
- Menu lateral mostra:
  - `sobreposicao_interrupcao`
  - `horario_negativo`
  - `sem_causa_componente`
- Ao clicar em uma regra, a tabela carrega até 100 registros.
- Mensagem vermelha aparece durante carregamento.
- Mensagem verde aparece ao concluir.

## Critérios de aceite

- API ativa em `http://127.0.0.1:8000`.
- Vite ativo em `http://127.0.0.1:5173`.
- `http://127.0.0.1:5173/filas.html` abre sem erro no console.
- Cards batem com `/apuracao/filas/resumo`.
- Tabelas batem com `/apuracao/filas/{regra}`.

## Próximo passo

Depois de validado:

1. Integrar `FilasMaterializadasApp` ao `App.tsx` principal.
2. Substituir a navegação antiga de filas por componentes React.
3. Manter dashboard executivo somente leitura.
4. Deixar ações governadas em páginas específicas por regra.
