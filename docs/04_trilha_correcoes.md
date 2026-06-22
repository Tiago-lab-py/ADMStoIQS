# Trilha de Correções OMS

## Objetivo

Criar um fluxo guiado no frontend para revisar, sugerir, aprovar e aplicar correções nos dados OMS/IQS/ADMS, mantendo governança nominal e rastreabilidade das decisões.

A trilha deve usar como fonte principal:

```text
data/mart/OMS_union.parquet
```

Quando existir, a trilha deve usar preferencialmente:

```text
data/mart/OMS_union_corrigido.parquet
```

E registrar ações em:

```text
data/logs/log_alteracoes.parquet
```

## Princípios

- Nenhuma alteração deve ser aplicada sem usuário autenticado.
- Toda sugestão deve ter justificativa ou regra de origem.
- Toda decisão deve ser rastreável por usuário, perfil, data/hora, IP e user-agent.
- O usuário comum solicita correções.
- Gestor e admin podem aprovar/aplicar correções.
- A exportação final deve acontecer apenas depois da revisão das etapas obrigatórias.
- A base original `OMS_union.parquet` não deve ser sobrescrita por correções.
- Correções aprovadas/aplicadas devem gerar `OMS_union_corrigido.parquet`.

## Sequência da Trilha

Ordem sugerida:

1. Dashboard
2. Horário negativo
3. Sobreposição de interrupção
4. Sobreposição de UC
5. Sem causa ou componente
6. Revisão final
7. Exportação regional

## Por Que Esta Ordem

### 1. Dashboard

Primeiro ponto de orientação.

Mostra:

- Competência selecionada.
- Total de registros.
- Total por regional.
- Quantidade de pendências por tipo.
- Status geral da trilha.

### 2. Horário Negativo

Deve vir antes das sobreposições, porque horários inconsistentes afetam duração e análise temporal.

Regra principal:

- `erro_duracao = true`.
- Se diferença negativa absoluta for até 3 horas, sugerir ajuste de fuso.

### 3. Sobreposição de Interrupção

Deve vir depois de corrigir horários negativos.

Agrupamento:

```text
ALIM_INTRP_PIN
NUM_OPER_CHV_INTRP
```

Intervalo:

```text
DATA_HORA_INIC_INTRP
DATA_HORA_FIM_INTRP
```

### 4. Sobreposição de UC

Deve vir depois da sobreposição no nível da interrupção.

Agrupamento:

```text
NUM_UC_UCI
NUM_POSTO_UCI
```

Intervalo:

```text
DTHR_INICIO_INTRP_UC
DATA_HORA_FIM_INTRP
```

### 5. Sem Causa ou Componente

Etapa de qualidade cadastral/operacional.

Campos:

```text
COD_CAUSA_INTRP
COD_COMP_INTRP
```

### 6. Revisão Final

Consolida:

- Correções aprovadas.
- Correções rejeitadas.
- Correções ignoradas.
- Pendências restantes.
- Impacto esperado antes da exportação.

### 7. Exportação Regional

Gera os CSVs finais por:

```text
REGIONAL_ORIGEM
```

## Estados de uma Correção

Cada sugestão/correção deve passar por estados controlados.

| Estado | Descrição |
|---|---|
| `pendente` | Sugestão identificada, ainda sem decisão |
| `em_revisao` | Usuário abriu ou editou a sugestão |
| `solicitado` | Usuário comum enviou solicitação |
| `aprovado` | Gestor/admin aprovou a correção |
| `rejeitado` | Gestor/admin rejeitou a correção |
| `ignorado` | Item marcado como não aplicável |
| `aplicado` | Correção aplicada ao conjunto de saída |
| `erro` | Falha ao aplicar ou registrar correção |

## Perfis e Permissões

| Ação | Usuário | Gestor | Admin |
|---|---:|---:|---:|
| Consultar dashboard | Sim | Sim | Sim |
| Ver pendências | Sim | Sim | Sim |
| Editar sugestão | Sim | Sim | Sim |
| Solicitar correção | Sim | Sim | Sim |
| Aprovar correção | Não | Sim | Sim |
| Rejeitar correção | Não | Sim | Sim |
| Ignorar pendência | Não | Sim | Sim |
| Aplicar correção | Não | Sim | Sim |
| Exportar CSV | Não | Sim | Sim |
| Gerenciar perfis | Não | Não | Sim |

## Tipos de Correção

### Horário Negativo

Tipo:

```text
horario_negativo
```

Campo principal:

```text
DATA_HORA_FIM_INTRP
```

Sugestão automática:

```text
DATA_HORA_FIM_INTRP + 3 horas
```

Condição:

```text
erro_duracao = true
0 < abs(duracao) <= 180 minutos
```

Se a diferença negativa for maior que 3 horas:

```text
revisao_manual
```

### Sobreposição de Interrupção

Tipo:

```text
sobreposicao_interrupcao
```

Regra:

- Manter como primeira interrupção a de menor `NUM_SEQ_INTRP`.
- Se a segunda interrupção for longa (`duracao_longa = true`), deslocar início da segunda para o fim da primeira.
- Se a segunda interrupção for curta (`duracao_longa = false`), sugerir tratamento diferenciado.

Campos sugeridos:

```text
DATA_HORA_INIC_INTRP
NUM_INTRP_INIC_MANOBRA_UCI
NUM_MOTIVO_TRAT_DIF_UCI
```

Valor para tratamento diferenciado:

```text
NUM_MOTIVO_TRAT_DIF_UCI = 91
```

### Sobreposição de UC

Tipo:

```text
sobreposicao_uc
```

Regra:

- Avaliar mesma `NUM_UC_UCI` e `NUM_POSTO_UCI`.
- Usar intervalo `DTHR_INICIO_INTRP_UC` até `DATA_HORA_FIM_INTRP`.
- Para evento longo, deslocar início da segunda interrupção.
- Para evento curto, sugerir `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

Campos sugeridos:

```text
DTHR_INICIO_INTRP_UC
NUM_INTRP_INIC_MANOBRA_UCI
NUM_MOTIVO_TRAT_DIF_UCI
```

### Sem Causa ou Componente

Tipo:

```text
sem_causa_componente
```

Campos avaliados:

```text
COD_CAUSA_INTRP
COD_COMP_INTRP
```

Nesta etapa, a sugestão pode ser:

- Manual.
- Baseada em histórico de ocorrências similares.
- Baseada em `DESC_INTRP`.
- Baseada em `TIPO_EQP_INTRP`.
- Baseada em `NUM_OPER_CHV_INTRP`.

## Estrutura Visual do Frontend

### Layout

Proposta:

- Barra lateral com etapas.
- Área principal com lista de pendências.
- Painel lateral ou modal com detalhe da correção.
- Cards de métricas no dashboard.
- Foco de atuação com total de pendências.
- Administração visível apenas para perfil `admin`.

Exemplo:

```text
┌──────────────────────────┬─────────────────────────────────────┐
│ Trilha                   │ Conteúdo                             │
│                          │                                     │
│ 1 Dashboard              │ Tabela de pendências                 │
│ 2 Horário negativo       │ Filtros / ações / detalhe            │
│ 3 Sobreposição interrup. │                                     │
│ 4 Sobreposição UC        │                                     │
│ 5 Causa/componente       │                                     │
│ 6 Revisão final          │                                     │
│ 7 Exportação             │                                     │
└──────────────────────────┴─────────────────────────────────────┘
```

### Cada Etapa Deve Ter

- Contador de pendências.
- Filtro por regional.
- Filtro por status.
- Tabela com registros.
- Detalhe da sugestão.
- Botões de ação conforme perfil.

## Ações na Interface

### Ações Básicas

- `Ver detalhe`
- `Aceitar sugestão`
- `Editar sugestão`
- `Solicitar correção`
- `Aprovar`
- `Rejeitar`
- `Ignorar`
- `Aplicar`

### Ações por Perfil

Usuário:

- Ver detalhe.
- Editar sugestão.
- Solicitar correção.

Gestor:

- Ver detalhe.
- Editar sugestão.
- Solicitar correção.
- Aprovar.
- Rejeitar.
- Ignorar.
- Aplicar.
- Exportar.

Admin:

- Todas as ações do gestor.
- Gerenciar perfis e configurações futuras.

## Modelo de Registro de Correção

Campos sugeridos para evolução do `log_alteracoes.parquet`:

| Campo | Descrição |
|---|---|
| `id_alteracao` | Identificador único |
| `id_sugestao` | Identificador da sugestão |
| `tipo_correcao` | Tipo da fila |
| `status` | Estado da correção |
| `usuario` | Usuário autenticado |
| `perfil_usuario` | Perfil no momento da ação |
| `ip_origem` | IP capturado pelo backend |
| `hostname_origem` | Hostname quando disponível |
| `user_agent` | User-agent |
| `anomes` | Competência |
| `regional_origem` | Regional |
| `chave_registro` | Chave lógica do registro |
| `campo` | Campo alterado |
| `valor_anterior` | Valor anterior |
| `valor_sugerido` | Valor sugerido |
| `valor_novo` | Valor aprovado/aplicado |
| `justificativa` | Justificativa |
| `regra_origem` | Regra que gerou a sugestão |
| `criado_em` | Data/hora |

## Endpoints Necessários

### Já Existentes

```text
GET /tratamentos/horario-negativo
GET /tratamentos/sobreposicao-interrupcao
GET /tratamentos/sobreposicao-uc
GET /tratamentos/sem-causa-componente
POST /alteracoes
POST /competencias/{anomes}/exportar-csv-regionais
POST /mart/oms-corrigido
```

### Próximos Endpoints Sugeridos

```text
GET /trilha/{anomes}/resumo
GET /trilha/{anomes}/pendencias
POST /trilha/{anomes}/sugestoes/{id_sugestao}/solicitar
POST /trilha/{anomes}/sugestoes/{id_sugestao}/aprovar
POST /trilha/{anomes}/sugestoes/{id_sugestao}/rejeitar
POST /trilha/{anomes}/sugestoes/{id_sugestao}/ignorar
POST /trilha/{anomes}/aplicar
```

## Critérios de Aceite

- Usuário navega pela sequência da trilha.
- Cada etapa mostra quantidade de pendências.
- Usuário visualiza detalhe e sugestão da correção.
- Usuário comum solicita correção, mas não aplica.
- Gestor/admin aprova, rejeita, ignora ou aplica.
- Toda decisão registra auditoria.
- Exportação regional só fica disponível para gestor/admin.
- Revisão final mostra pendências restantes antes da exportação.

## Próximos Passos

1. Criar resumo da trilha por competência.
2. Criar identificador estável para cada sugestão.
3. Persistir status das sugestões.
4. Ajustar frontend para layout com stepper lateral. **Implementado como primeira versão em `frontend/src/App.tsx`.**
5. Implementar ações de aprovar/rejeitar/ignorar.
6. Implementar aplicação controlada das correções.
7. Gerar `OMS_union_corrigido.parquet` a partir das alterações aprovadas/aplicadas.
# Trilha de Correções OMS

## Objetivo

Construir uma jornada de tratamento governada sobre o mart único:

```text
data/mart/agrupamento_oms_UNION_corrigido.parquet
```

A ferramenta deve reduzir o volume de análise manual com regras robustas, mas preservar a decisão humana quando a correção não for automática ou segura.

## Fonte de Dados

- Base consolidada original: `data/mart/agrupamento_oms_UNION.parquet`
- Base de trabalho: `data/mart/agrupamento_oms_UNION_corrigido.parquet`
- Log de decisões: `data/logs/log_alteracoes.parquet`

O frontend deve tratar `UNION` como competência lógica única.

## Estados do Registro

Cada registro da base corrigida deve conter:

- `validado`
- `status_validacao`
- `motivo_status`
- `usuario_validacao`
- `data_hora_validacao`

Estados permitidos inicialmente:

- `pendente`: ainda não analisado.
- `em_analise`: aberto por usuário ou em fila de decisão.
- `validado`: aceito sem alteração.
- `rejeitado`: descartado para exportação ou tratamento.
- `ignorado`: regra automática não aplicada.
- `aplicado`: correção aplicada ao parquet corrigido.

## Perfis

- `admin`: gerencia usuários, perfis, reset de senha, parâmetros e auditoria.
- `gestor`: aprova/rejeita alterações e executa exportações oficiais.
- `usuario`: analisa filas, solicita alterações e marca decisões permitidas.

## Páginas da Trilha

### 1. Dashboard

Visão geral do mart:

- Total de registros carregados.
- Total pendente.
- Total com horário negativo.
- Total com sobreposição.
- Total rejeitado.
- Total validado.

### 2. Horário Negativo

Critério:

- `erro_duracao = true`

Regra sugerida:

- Se o desvio negativo estiver entre 0 e 3 horas, sugerir ajuste de fuso adicionando 3 horas ao horário fim.

Decisão do analista:

- aplicar sugestão;
- rejeitar registro;
- ignorar regra;
- deixar pendente para análise futura.

### 3. Sobreposição de Interrupção

Critério:

- Mesmo `ALIM_INTRP_PIN`.
- Mesmo `NUM_OPER_CHV_INTRP`.
- Intervalos sobrepostos usando `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`.

Regra sugerida:

- Manter menor `NUM_SEQ_INTRP` como interrupção principal.
- Se a segunda interrupção for longa (`duracao_longa = true`), deslocar início da segunda para o fim da primeira.
- Popular `NUM_INTRP_INIC_MANOBRA_UCI` com o número da primeira interrupção.
- Se a segunda for curta, sugerir exclusão/tratamento com `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

### 4. Sobreposição de UC

Critério:

- Mesmo `NUM_UC_UCI`.
- Mesmo `NUM_POSTO_UCI`.
- Intervalos sobrepostos usando `DTHR_INICIO_INTRP_UC` e `DATA_HORA_FIM_INTRP`.

Decisão:

- aplicar ajuste;
- rejeitar;
- ignorar;
- manter pendente.

### 5. Causa/Componente

Critério:

- `COD_CAUSA_INTRP` ausente.
- `COD_COMP_INTRP` ausente.

Objetivo:

- sugerir causa ou componente com base na ocorrência, descrição, regional e padrões históricos.
- não aplicar sem decisão explícita.

### 6. Revisão Final

Tela de conferência antes da exportação:

- alterações aplicadas;
- registros rejeitados;
- registros pendentes;
- registros validados;
- inconsistências restantes.

### 7. Exportação

Exportação deve usar a base corrigida:

```text
data/mart/agrupamento_oms_UNION_corrigido.parquet
```

Regras:

- Exportar por `REGIONAL_ORIGEM`.
- Não exportar registros com `status_validacao = rejeitado`.
- Permitir exportação apenas para `gestor` e `admin`.

## Auditoria

Toda decisão deve registrar:

- usuário autenticado;
- perfil;
- host/PC quando disponível;
- IP;
- timestamp;
- chave do registro;
- campo alterado;
- valor original;
- valor novo;
- justificativa;
- status da decisão.
