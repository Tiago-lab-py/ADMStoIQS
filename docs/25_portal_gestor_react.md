# 25 - Portal Gestor React

## Objetivo

Criar uma experiência React oficial para apresentação ao gestor, centralizando:

- dashboard executivo somente leitura;
- resumo das filas materializadas;
- fontes IQS materializadas;
- visão de governança e próximas decisões.

## Arquivos criados

- `frontend/src/gestorApi.ts`
- `frontend/src/GestorPortalApp.tsx`
- `frontend/src/gestorPortal.css`
- `frontend/src/gestor-main.tsx`
- `frontend/gestor.html`

## URL de validação

Com API e Vite ativos:

```text
http://127.0.0.1:5173/gestor.html
```

O portal inicia em `202605` e possui campo `Competência` para alternar o mês de trabalho.

## APIs consumidas

- `GET /apuracao/filas/resumo?anomes=202605`
- `GET /iqs/resumo?anomes=202605`
- `GET /mart/resumo`

O portal usa `Promise.allSettled`, então uma fonte indisponível não derruba a tela inteira. A mensagem superior informa se houve carregamento parcial.

## Estrutura da tela

### Dashboard executivo

Somente leitura.

Cards:

- pendências totais;
- sobreposição;
- horário negativo;
- sem causa/componente;
- fontes IQS processadas.

### Filas de correção

Resumo por regra e link para:

```text
http://127.0.0.1:5173/filas.html
```

### Fontes IQS

Tabela com:

- fonte;
- status;
- linhas raw;
- linhas mart;
- erro.

### Governança

Roadmap conceitual:

1. dashboard somente leitura;
2. filas por regra;
3. decisão governada;
4. exportação IQS.

## Critérios de aceite

- `gestor.html` abre sem erro no console.
- Ao alterar `Competência`, o portal recarrega filas e IQS para o `anomes` informado.
- Cards carregam mesmo que `/mart/resumo` esteja indisponível.
- Menu lateral alterna entre Dashboard, Filas, IQS e Governança.
- Link para `filas.html?anomes=[competencia]` funciona.
- Visual mantém o design system escuro/ciano/violeta já validado.

## Próximos passos

1. Parametrizar competência no portal.
2. Integrar login/perfil.
3. Criar tela oficial de decisão governada por regra.
4. Conectar ações a `log_alteracoes.parquet`.
5. Evoluir dashboard para DEC/FEC e ressarcimento antes/depois.
