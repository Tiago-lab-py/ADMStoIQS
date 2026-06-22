# Pendências materializadas da apuração

## 1. Objetivo

Materializar as pendências da apuração mensal em Parquet para reduzir recálculo nas telas e estabilizar os indicadores do dashboard executivo.

## 2. Arquivos gerados

```text
data/mart/apuracao/pendencias_APURACAO_[anomes].parquet
data/mart/apuracao/pendencias_APURACAO_ATUAL.parquet
```

## 3. Regras iniciais materializadas

### 3.1 Horário negativo

Grão:

```text
NUM_SEQ_INTRP
```

Regra:

- identifica interrupções com `DATA_HORA_FIM_INTRP < DATA_HORA_INIC_INTRP`;
- conta interrupções distintas;
- registra quantidade de UCs afetadas na justificativa;
- sugere ajuste de fuso quando diferença for até 3 horas;
- caso contrário envia para revisão manual.

### 3.2 Sobreposição interrupção

Grão:

```text
NUM_OPER_CHV_INTRP|NUM_SEQ_INTRP
```

Regra:

- identifica interrupções sobrepostas no mesmo equipamento;
- mantém menor `NUM_SEQ_INTRP`;
- sugere rejeitar demais interrupções sobrepostas;
- sugere `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

### 3.3 Sem causa/componente

Grão:

```text
NUM_SEQ_INTRP
```

Regra:

- identifica interrupções sem `COD_CAUSA_INTRP` ou `COD_COMP_INTRP`;
- envia para sugestão futura por histórico IQS.

## 4. Script

```cmd
python -m backend.scripts.materializar_pendencias_apuracao --anomes 202605
```

## 5. Endpoints

Resumo:

```text
GET /apuracao/pendencias/resumo
```

Listagem:

```text
GET /apuracao/pendencias?limit=100&offset=0
```

Filtro por regra:

```text
GET /apuracao/pendencias?regra=horario_negativo
GET /apuracao/pendencias?regra=sobreposicao_interrupcao
GET /apuracao/pendencias?regra=sem_causa_componente
```

Materialização:

```text
POST /apuracao/pendencias/materializar/202605
```

## 6. Prévia gestor

A página:

```text
http://127.0.0.1:5173/gestor-preview.html
```

agora possui o botão:

```text
Atualizar pendências
```

Ele chama:

```text
POST /apuracao/pendencias/materializar/{anomes}
```

e atualiza os cards executivos.

## 7. Próximos ajustes

- Criar endpoint de detalhe por pendência.
- Separar tabela de IQS e tabela de pendências na prévia.
- Integrar pendências ao dashboard principal.
- Aplicar decisões do `log_alteracoes.parquet` sobre as pendências.
- Criar `APURACAO_CORRIGIDA_[anomes].parquet`.

