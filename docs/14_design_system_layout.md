# Design system e layout estável — ADMStoIQS

## 1. Objetivo

Este documento define uma proposta estável de layout, estilo e experiência visual para o ADMStoIQS.

A intenção é evitar mudanças constantes de interface durante o desenvolvimento. A partir daqui, o frontend deve evoluir dentro de um mesmo padrão visual, com alterações controladas e documentadas.

## 2. Princípios de interface

O sistema deve transmitir:

- robustez operacional;
- confiança regulatória;
- clareza para tomada de decisão;
- rastreabilidade de alterações;
- leitura rápida em telas com muitos dados;
- separação clara entre operação, análise e aprovação.

## 3. Estrutura geral da aplicação

Layout recomendado:

```text
┌─────────────────────────────────────────────────────────────┐
│ Sidebar fixa │ Conteúdo principal                          │
│              │                                             │
│ Navegação    │ Cabeçalho da página                         │
│ Perfil       │ Alertas / status de processamento           │
│ Logout       │ Cards executivos                            │
│              │ Tabelas / painéis / ações governadas        │
└─────────────────────────────────────────────────────────────┘
```

## 4. Sidebar

A sidebar deve ser fixa e conter:

- logotipo ADMStoIQS;
- subtítulo da aplicação;
- card “Foco de atuação”;
- menu principal;
- usuário logado;
- perfil;
- botão sair.

Menu recomendado:

```text
Preparar apuração
Dashboard
Horário negativo
Sobreposição interrupção
Sobreposição UC
Causa/componente
Revisão final
Exportação
Administração
```

Regras:

- item ativo deve ter destaque visual consistente;
- badges devem mostrar contagens materializadas;
- menu não deve mudar de ordem sem decisão de sprint.

## 5. Cabeçalho de página

Cada página deve ter:

- título;
- descrição curta;
- botão “Atualizar”, quando aplicável;
- mensagem de status de processamento.

Mensagens:

- processamento em andamento: vermelho/alerta;
- processamento concluído: verde/sucesso;
- informação neutra: azul;
- erro: vermelho com texto técnico resumido.

## 6. Cards

Cards devem ter:

- título curto;
- número principal;
- subtítulo explicativo;
- padrão de cor por criticidade.

Tipos:

- operacional;
- regulatório;
- financeiro;
- governança.

Cards do dashboard:

```text
Pendências totais
Horário negativo
Sobreposições
Rejeitados
Validados
Revisão manual
DEC antes
DEC depois
FEC antes
FEC depois
Ressarcimento estimado antes
Ressarcimento estimado depois
```

## 7. Tabelas

Tabelas devem ser densas, mas legíveis.

Regras:

- cabeçalho fixo;
- rolagem horizontal quando necessário;
- altura controlada;
- seleção por checkbox apenas em páginas de tratamento;
- dashboard sem ação de alteração;
- colunas técnicas ordenadas por importância;
- detalhe expandido quando o grão principal for evento/interrupção.

## 8. Grãos visuais

Cada tela deve deixar claro o grão da análise.

Exemplos:

| Página | Grão principal | Detalhe |
|---|---|---|
| Dashboard | Apuração mensal | Indicadores |
| Horário negativo | `NUM_SEQ_INTRP` | UCs afetadas |
| Sobreposição interrupção | `NUM_OPER_CHV_INTRP + NUM_SEQ_INTRP` | interrupções sobrepostas e UCs |
| Sobreposição UC | `NUM_UC_UCI + NUM_POSTO_UCI` | interrupções conflitantes |
| Causa/componente | interrupção/ocorrência | sugestão histórica |
| Exportação | regional | arquivo CSV gerado |

## 9. Painel de decisão governada

Páginas de tratamento devem ter painel de decisão separado da tabela.

Campos:

- regra;
- chave do evento;
- quantidade selecionada;
- usuário;
- perfil;
- justificativa;
- ação: validar, rejeitar, ignorar regra, enviar para revisão.

Regras:

- rejeitar exige justificativa;
- alteração em massa exige confirmação;
- gestor aprova alterações sensíveis;
- dashboard nunca altera dados.

## 10. Paleta visual

Padrão recomendado:

```text
Fundo principal: preto/azul muito escuro
Cards: azul petróleo translúcido
Bordas: azul/ciano com baixa opacidade
Ação principal: ciano
Alerta crítico: vermelho/rosa
Sucesso: verde
Texto principal: branco
Texto secundário: azul acinzentado
```

Evitar:

- mudar paleta entre páginas;
- botões com tamanhos diferentes para a mesma ação;
- tabelas sem altura controlada;
- cores novas sem função definida.

## 11. Componentes padrão

Criar e manter componentes reutilizáveis:

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

A próxima refatoração do frontend deve migrar a tela atual para esses componentes, sem alterar regra de negócio.

## 12. Responsividade

Prioridade:

1. desktop corporativo;
2. notebook;
3. tela wide;
4. tablet apenas para consulta.

Não priorizar celular na fase atual, pois o uso principal envolve tabelas largas e análise técnica.

## 13. Regra de congelamento visual

Após aprovação deste design system:

- mudanças visuais devem ser registradas em sprint;
- não alterar estilo durante correção de regra de negócio;
- novas páginas devem reutilizar componentes existentes;
- mudanças grandes de layout exigem atualização deste documento.

## 14. Próximo passo técnico

Criar uma sprint específica para refatoração visual:

```text
Sprint 4 — Design system e estabilização do frontend
```

Entregas:

- componentes reutilizáveis;
- CSS organizado por tokens;
- dashboard somente leitura;
- telas de tratamento com painel governado;
- documentação visual congelada.

