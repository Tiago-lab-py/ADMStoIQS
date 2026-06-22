# Sprint 4 — Design system e estabilização do frontend

## 1. Objetivo

Estabilizar o layout do ADMStoIQS para evitar mudanças visuais frequentes durante o desenvolvimento das regras de tratamento.

Esta sprint não deve alterar regra de negócio. O foco é organizar componentes, padronizar estilo e deixar a experiência consistente.

## 2. Referência principal

Documento base:

```text
docs/14_design_system_layout.md
```

## 3. Escopo

### 3.1 Componentização

Criar componentes reutilizáveis:

```text
AppShell
Sidebar
PageHeader
StatusMessage
MetricCard
DataTable
DecisionPanel
DetailPanel
Toolbar
ActionButton
RoleBadge
```

### 3.2 Dashboard somente leitura

Garantir que o dashboard não tenha ações de alteração.

O dashboard deve exibir:

- cards operacionais;
- visão executiva;
- tendências;
- pendências por regra;
- rejeitados por atividade;
- DEC/FEC antes e depois;
- estimativa de ressarcimento antes e depois.

### 3.3 Páginas de tratamento

Padronizar:

- tabela principal;
- tabela de detalhe;
- seleção individual;
- seleção em massa;
- painel de decisão;
- justificativa obrigatória quando aplicável.

### 3.4 Mensagens de processamento

Padronizar:

- “Aguarde processamento...” em vermelho;
- “Processamento concluído” em verde;
- erro técnico resumido em vermelho;
- informação neutra em azul.

## 4. Fora de escopo

Não faz parte desta sprint:

- criar novas regras de tratamento;
- alterar cálculo regulatório;
- alterar ingestão CSV;
- alterar exportação IQS;
- alterar autenticação.

## 5. Critérios de aceite

- Todas as páginas usam o mesmo layout base.
- Sidebar mantém ordem fixa.
- Dashboard não possui painel de decisão.
- Botões têm padrão visual único.
- Tabelas têm rolagem controlada.
- Mensagens de processamento seguem as cores definidas.
- CSS passa a ter tokens de cor, espaçamento e sombra.
- Nenhuma regra de negócio é alterada nesta sprint.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Refatoração visual quebrar telas existentes | Fazer em pequenos commits |
| Misturar layout com regra de negócio | Não alterar serviços/API nesta sprint |
| Recriar estilos por página | Usar componentes compartilhados |
| Perder velocidade no desenvolvimento | Congelar padrões e reaproveitar |

## 7. Entregáveis

- `frontend/src/components/`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/layout.css`
- `frontend/src/styles/components.css`
- `frontend/src/styles/tables.css`
- atualização do `App.tsx` para usar componentes.

## 8. Checklist

- [ ] Criar tokens de estilo.
- [ ] Criar `AppShell`.
- [ ] Criar `Sidebar`.
- [ ] Criar `PageHeader`.
- [ ] Criar `StatusMessage`.
- [ ] Criar `MetricCard`.
- [ ] Criar `DataTable`.
- [ ] Criar `DecisionPanel`.
- [ ] Migrar Dashboard.
- [ ] Migrar Preparar apuração.
- [ ] Migrar Horário negativo.
- [ ] Validar tela em 1366px.
- [ ] Validar tela wide.
- [ ] Atualizar documentação.

