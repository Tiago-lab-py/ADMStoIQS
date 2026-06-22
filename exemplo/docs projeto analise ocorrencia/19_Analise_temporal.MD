# 19. Analise Temporal das Interrupcoes

## Objetivo
Esta etapa da aplicacao existe para **identificar sobreposicoes temporais** entre interrupcoes que, do ponto de vista operacional, representam o mesmo evento e podem gerar **duplicidade indevida** no tratamento e no envio ao IQS.

A proposta desta analise e:
- detectar blocos temporais equivalentes;
- definir uma **interrupcao lider**;
- consolidar a janela temporal do bloco;
- marcar as demais interrupcoes como derivadas/duplicadas;
- preservar a **trilha de auditoria** antes de qualquer efetivacao.

## Posicionamento na jornada
Esta pagina fica entre:
- **Implantacao de Protocolo**: tratamento operacional por conjunto/regiao;
- **Validacao Pos-Operacao**: ajuste fino, confirmacao final e fechamento do pendente.

Ela funciona como uma camada de **limpeza e consolidacao operacional** antes da validacao final.

## Regras de deteccao do bloco temporal
Um bloco temporal candidato e formado quando duas ou mais interrupcoes compartilham o mesmo contexto:

- `competencia`
- `cod_conjunto`
- `alim_intrp`
- `tipo_protocolo`
- `cod_causa`
- `cod_componente`
- `tipo_equipamento`
- `num_operacional_equipamento`

e, alem disso, possuem **sobreposicao temporal**:

- `dt_ini_b <= dt_fim_a`

No primeiro ciclo, a regra usa **sobreposicao real**. Em etapa futura, pode ser adicionada tolerancia configuravel em minutos.

## Interrupcao lider
Dentro de cada bloco temporal:

- a interrupcao lider e a de **menor `num_interrupcao`**
- `dt_ini_consolidado` = menor `dt_ini` do bloco
- `dt_fim_consolidado` = maior `dt_fim` do bloco

Essa interrupcao lider passa a ser a **representante canonica** do bloco.

## Tratamento das demais interrupcoes
As demais interrupcoes do bloco **nao devem ser apagadas**.

Elas devem ser mantidas para rastreabilidade com status de consolidacao, por exemplo:

- `LIDER_TEMPORAL`
- `DUPLICADA_TEMPORAL`

Campos de governanca recomendados:

- `bloco_temporal_id`
- `status_consolidacao`
- `num_interrupcao_lider`
- `motivo_consolidacao`
- `dt_ini_original`
- `dt_fim_original`
- `dt_ini_consolidado`
- `dt_fim_consolidado`

## Regra de envio ao IQS
Para evitar duplicidade regulatoria, o envio ao IQS deve considerar somente:

- registros sem consolidacao temporal; ou
- registros marcados como `LIDER_TEMPORAL`

Nao devem seguir para o envio:

- `DUPLICADA_TEMPORAL`
- `CANCELADA`
- outros status bloqueados pela regra de negocio

## Trilha de auditoria
Cada consolidacao deve registrar:

- `bloco_temporal_id`
- interrupcao lider
- lista de interrupcoes absorvidas
- janela original de cada interrupcao
- janela consolidada final
- usuario
- data/hora
- regra aplicada
- justificativa do analista (quando necessario)

## O que a pagina deve entregar
### 1. Blocos Temporais Detectados
Visao resumida do bloco:

- conjunto
- alimentador
- ocorrencia lider
- interrupcao lider
- qtd de interrupcoes no bloco
- tipo protocolo
- componente
- causa
- tipo equipamento
- numero operacional do equipamento
- data/hora inicial consolidada
- data/hora final consolidada
- CI total do bloco
- CHI total do bloco
- acao sugerida

### 2. Detalhe do Bloco
Lista de todas as interrupcoes do bloco com:

- identificacao da lider
- janela original
- janela consolidada
- CI e CHI individual
- status sugerido

### 3. Proposta de Consolidacao
Saida preparada para posterior efetivacao:

- lider mantida
- demais marcadas como `DUPLICADA_TEMPORAL`
- consolidacao documentada para auditoria

## Principios de seguranca da implementacao
- nao alterar silenciosamente a base operacional
- separar claramente:
  - deteccao
  - proposta
  - efetivacao
- manter compatibilidade com revisao humana antes da acao em massa

## Proximos passos tecnicos
1. Persistir proposta de consolidacao em tabela/app de governanca
2. Integrar efetivacao com trilha de auditoria
3. Bloquear envio ao IQS de interrupcoes marcadas como duplicadas temporais
4. Adicionar tolerancia temporal configuravel
5. Incluir indicador de impacto regulatorio estimado por bloco

## Estrutura de persistencia recomendada
A implementacao da fase atual utiliza a tabela:

- `ddcq.aap_ao_app_consolidacao_temporal`

Script de criacao:

- `sql/28_create_table_dbguo_aap_ao_app_consolidacao_temporal.sql`

Ela armazena uma linha por interrupcao participante do bloco, incluindo:
- bloco temporal
- interrupcao lider
- status sugerido (`LIDER_TEMPORAL` ou `DUPLICADA_TEMPORAL`)
- janela original
- janela consolidada
- usuario/perfil/sessao

## Regra pratica de saida para IQS
Na fase atual da aplicacao, a base recomendada para IQS deve considerar apenas:

- `Status Consolidacao Sugerido = LIDER_TEMPORAL`

Isso garante que o mesmo evento temporal nao seja enviado duplicado por fragmentacao operacional.

## Materializacao recomendada para consumo da UI
Para estabilizar performance da pagina e reduzir carga no dbGUO, a analise temporal deve evoluir para consumo de tabelas materializadas:

- `ddcq.aap_ao_mart_analise_temporal_blocos`
- `ddcq.aap_ao_mart_analise_temporal_detalhe`
- `ddcq.aap_ao_mart_analise_temporal_ganho_conjunto`

Scripts de criacao:

- `sql/29_create_table_dbguo_aap_ao_mart_analise_temporal_blocos.sql`
- `sql/30_create_table_dbguo_aap_ao_mart_analise_temporal_detalhe.sql`
- `sql/31_create_table_dbguo_aap_ao_mart_analise_temporal_ganho_conjunto.sql`

### Papel de cada tabela
#### 1. Blocos
Tabela executiva com 1 linha por bloco temporal detectado.

Uso principal:
- aba executiva
- proposta de consolidacao
- consolidacao lider x duplicadas

#### 2. Detalhe
Tabela analitica com 1 linha por interrupcao participante do bloco.

Uso principal:
- aba tabular
- timeline
- base elegivel ao IQS

#### 3. Ganho por conjunto
Tabela executiva agregada por conjunto.

Uso principal:
- ganhos estimados de CI/CHI
- priorizacao operacional
- dashboard executivo
