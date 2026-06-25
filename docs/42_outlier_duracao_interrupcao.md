# Outlier de duração de interrupção

## Objetivo

Identificar interrupções com duração muito alta para análise governada, sem remover automaticamente da base tratada.

O objetivo é evitar que interrupções acima de 48 horas distorçam DEC, DIC, DMIC e ressarcimento sem validação técnica.

## Regra inicial

Uma interrupção é sinalizada como outlier quando:

- possui `DATA_HORA_INIC_INTRP` válida;
- possui `DATA_HORA_FIM_INTRP` válida;
- `DATA_HORA_FIM_INTRP >= DATA_HORA_INIC_INTRP`;
- duração da interrupção é maior ou igual ao limite informado;
- limite padrão: `48` horas.

## Base utilizada

Por padrão, a análise usa a base tratada:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_{anomes}_TRATADO.parquet
```

Também é possível rodar contra a base original com `--base-original`.

## Saídas

O processo materializa:

```text
data/mart/apuracao/analise_outlier_duracao_APURACAO_{anomes}.parquet
data/mart/apuracao/analise_outlier_duracao_APURACAO_ATUAL.parquet
```

## Granularidade

A análise é feita em nível de interrupção, por `NUM_SEQ_INTRP`.

O arquivo mantém as colunas de interrupção:

- `PID_INTRP_CONJTO_PIN`;
- `INDIC_AREA_REDE_POSTO_PIN`;
- `ALIM_INTRP_PIN`;
- `ESTADO_INTRP`;
- `ALIM_INTRP`;
- `CAR_SE`;
- `INDIC_INTRP_SE_ALIM`;
- `NUM_OCORRENCIA_ADMS`;
- `INDIC_INTRP_AT`;
- `CONS_INTRP`;
- `KVA_INTRP`;
- `NUM_OPER_CHV_INTRP`;
- `NUM_FUNCAO_ELET_HCAI`;
- `DESC_INTRP`;
- `VALID_POS_OPERACAO`;
- `DATA_HORA_INIC_INTRP`;
- `DATA_HORA_FIM_INTRP`;
- `TIPO_EQP_INTRP`;
- `COORD_X_INTRP`;
- `COORD_Y_INTRP`;
- `NUM_SEQ_INTRP`;
- `COD_CAUSA_INTRP`;
- `COD_COMP_INTRP`;
- `COD_AREA_ELET_INTRP`;
- `COD_GRUPO_COMP_INTRP`;
- `COD_COND_CLIMA_INTRP`;
- `COD_TIPO_INTRP`;
- `INDIC_JUMP_INTRP`;
- `NUM_PROTOC_JUSTIF_RESP_INTRP`;
- `TIPO_PROTOC_JUSTIF_INTRP`;
- `COD_CONJTO_ELET_ANEEL_INTRP`;
- `INDIC_CALC_DMIC_INTRP`;
- `INDIC_PONTO_CONEX_INTRP`;
- `NUM_GEO_CHV_INTRP`;
- `TIPO_REDE_CHV_INTRP`;
- `TIPO_CHV_INTRP`;
- `INDIC_PROPR_POSTO_INTRP`;
- `TENSAO_OPER_ALIM_INTRP`;
- `INDIC_DESLIG_ENT_SERV_INTRP`;
- `INDIC_PROPR_CHVP_INTRP`;
- `INDIC_CHVP_INIC_ALIM_INTRP`;
- `PID`.

## Campos adicionais

- `inicio_interrupcao_ts`;
- `fim_interrupcao_ts`;
- `qtd_ucs_afetadas`;
- `qtd_registros_uci`;
- `duracao_horas`;
- `chi_estimado_horas_uc`;
- `regra = outlier_duracao_interrupcao`;
- `acao_sugerida = analise_manual`;
- `status_pendencia = pendente`;
- `justificativa_sistema`;
- `gerado_em`.

## Governança

Essa regra não altera:

- `ESTADO_INTRP`;
- `NUM_MOTIVO_TRAT_DIF_UCI`;
- horários;
- causa;
- componente;
- base tratada.

Qualquer decisão sobre o outlier deve ser posterior e auditada:

- validar como correto;
- corrigir horário;
- classificar motivo;
- cancelar interrupção, se tecnicamente justificado;
- manter para cálculo.

## Comandos

Rodar na base tratada:

```bat
python -m backend.scripts.materializar_outlier_duracao --anomes 202605
```

Rodar com outro limite:

```bat
python -m backend.scripts.materializar_outlier_duracao --anomes 202605 --limite-horas 72
```

Rodar na base original:

```bat
python -m backend.scripts.materializar_outlier_duracao --anomes 202605 --base-original
```

## Decisão operacional

Outlier de duração deve ser tratado como fila de análise, não como expurgo automático.

A regra pode apoiar:

- priorização do analista;
- comparação de DEC/DIC antes e depois;
- simulação de impacto;
- justificativa técnica para alteração governada.
