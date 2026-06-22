# Sprint 5 — Pendências materializadas e dashboard regulatório

## 1. Objetivo

Criar uma camada materializada de pendências por regra e evoluir o dashboard para visão executiva, regulatória e financeira.

Essa sprint reduz custo de processamento na abertura das telas e prepara o sistema para cálculo de impacto antes/depois do tratamento.

## 2. Problema atual

Algumas telas ainda dependem de consultas diretas sobre a apuração ou sobre o mart. Com dezenas de milhões de registros, isso pode gerar:

- lentidão;
- cards divergentes;
- contagem por grão errado;
- recálculo desnecessário;
- dificuldade de auditar decisões.

## 3. Solução proposta

Criar arquivos materializados:

```text
data/mart/apuracao/pendencias_APURACAO_[anomes].parquet
data/mart/apuracao/pendencias_APURACAO_ATUAL.parquet
data/mart/apuracao/resumo_APURACAO_[anomes].parquet
data/mart/apuracao/resumo_APURACAO_ATUAL.parquet
```

## 4. Modelo de pendências

Colunas sugeridas:

```text
anomes
regra
gravidade
grao
chave_evento
chave_registro
num_seq_intrp
num_intrp_uci
num_oper_chv_intrp
num_posto_uci
num_uc_uci
regional_origem
campo_sugerido
valor_original
valor_sugerido
acao_sugerida
status_pendencia
justificativa_sistema
criado_em
```

## 5. Regras iniciais

### 5.1 Horário negativo

Grão:

```text
NUM_SEQ_INTRP
```

Detalhe:

```text
NUM_POSTO_UCI
NUM_UC_UCI
NUM_INTRP_UCI
```

### 5.2 Sobreposição por equipamento

Grão:

```text
NUM_OPER_CHV_INTRP + NUM_SEQ_INTRP
```

Regra:

- identificar interrupções sobrepostas no mesmo equipamento;
- manter menor `NUM_SEQ_INTRP`;
- sugerir rejeição dos demais eventos;
- sugerir `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

### 5.3 Sobreposição UC

Grão:

```text
NUM_UC_UCI + NUM_POSTO_UCI
```

### 5.4 Causa/componente ausentes

Campos:

```text
COD_CAUSA_INTRP
COD_COMP_INTRP
```

## 6. Dashboard regulatório

Adicionar indicadores:

- DEC antes;
- DEC depois;
- variação DEC;
- FEC antes;
- FEC depois;
- variação FEC;
- DIC antes/depois;
- FIC antes/depois;
- DMIC antes/depois;
- ressarcimento estimado antes;
- ressarcimento estimado depois;
- diferença estimada.

## 7. Cuidados regulatórios

O cálculo de ressarcimento deve seguir a metodologia vigente do PRODIST Módulo 8 da ANEEL.

Enquanto a fórmula não estiver validada formalmente:

- apresentar como estimativa;
- registrar versão da regra;
- separar cálculo técnico de valor oficial;
- exigir aprovação de gestor para uso regulatório.

## 8. Entregáveis backend

- Serviço `PendenciasApuracaoService`.
- Script `materializar_pendencias_apuracao.py`.
- Atualização do `ApuracaoResumoService`.
- Endpoints:

```text
POST /apuracao/pendencias/materializar
GET  /apuracao/pendencias
GET  /apuracao/pendencias/{regra}
GET  /apuracao/resumo
```

Implementação inicial:

```text
backend/app/services/pendencias_apuracao_service.py
backend/scripts/materializar_pendencias_apuracao.py
backend/app/api/pendencias_routes.py
```

Endpoints implementados:

```text
GET  /apuracao/pendencias/resumo
GET  /apuracao/pendencias
POST /apuracao/pendencias/materializar/{anomes}
```

## 9. Entregáveis frontend

- Dashboard lendo resumo materializado.
- Cards regulatórios.
- Páginas de tratamento lendo `pendencias_APURACAO_ATUAL.parquet`.
- Detalhe da pendência por evento.

## 10. Critérios de aceite

- Dashboard abre sem varrer todo o parquet da apuração.
- Cards batem com os arquivos materializados.
- Horário negativo conta `NUM_SEQ_INTRP` distintas.
- Detalhe mostra UCs vinculadas.
- Sobreposição por equipamento trabalha em interrupções únicas.
- Rejeitados por atividade aparecem no dashboard.
- Cálculos regulatórios aparecem marcados como estimativa.
