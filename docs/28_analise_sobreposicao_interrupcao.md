# 28 - Análise de Sobreposição por Interrupção

## Objetivo

Materializar uma análise local equivalente ao raciocínio usado no IQS/HCAI, adaptada ao mart OMS/ADMS em parquet.

No IQS:

- `SOD.INTERRUPCAO` representa interrupções.
- `IQS.HIST_CONS_AFETADO_INTERRUPCAO` representa consumidores afetados.

No projeto ADMStoIQS:

- colunas de interrupção vêm do agrupamento OMS;
- a camada análoga ao HCAI é a UCI:
  - `NUM_INTRP_UCI`
  - `NUM_POSTO_UCI`
  - `NUM_UC_UCI`
  - `NUM_MOTIVO_TRAT_DIF_UCI`

## Regra

Filtrar interrupções:

- `TIPO_EQP_INTRP = 'C'`
- `NUM_OPER_CHV_INTRP IS NOT NULL`
- datas válidas em `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`

Para cada `NUM_OPER_CHV_INTRP`, uma interrupção é sugerida como `EXCLUIR` quando está temporalmente contida em outra interrupção do mesmo equipamento:

```text
B.DATA_INICIO <= A.DATA_INICIO
B.DATA_FIM >= A.DATA_FIM
A.NUM_SEQ_INTRP <> B.NUM_SEQ_INTRP
```

Critério de desempate:

- se as datas forem iguais, mantém a menor `NUM_SEQ_INTRP`;
- a maior `NUM_SEQ_INTRP` é sugerida para exclusão.

## Sugestão de tratamento

Quando `acao_sugerida = EXCLUIR`:

- `ESTADO_INTRP_SUGERIDO = 7`
- `NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO = 91`

O sistema apenas sugere. A aplicação real deve passar pela decisão governada.

## Saídas

```text
data/mart/apuracao/analise_sobreposicao_interrupcao_APURACAO_[anomes].parquet
data/mart/apuracao/analise_sobreposicao_interrupcao_APURACAO_ATUAL.parquet
```

Campos principais:

- `NUMERO_OPERACIONAL`
- `ocorrencia`
- `interrupcao`
- `tipo_chave`
- `DATA_INICIO`
- `DATA_FIM`
- `SITUACAO`
- `acao_sugerida`
- `ESTADO_INTRP_SUGERIDO`
- `NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO`
- `COD_CAUSA_INTRP`
- `COD_COMP_INTRP`
- `COD_TIPO_INTRP`
- `TIPO_PROTOC_JUSTIF_INTRP`
- `TIPO_PROTOC_JUSTIF_UCI`
- `REGIONAL_ORIGEM`
- `UC_AFETADAS`
- `JUSTIFICATIVA_SISTEMA`

## Como materializar

Via terminal:

```bat
python -m backend.scripts.materializar_sobreposicao_interrupcao --anomes 202605
```

Via API:

```http
POST /apuracao/analises/sobreposicao-interrupcao/materializar/202605
```

## Como consultar

Todos os registros:

```http
GET /apuracao/analises/sobreposicao-interrupcao?anomes=202605
```

Somente sugeridos para exclusão:

```http
GET /apuracao/analises/sobreposicao-interrupcao?anomes=202605&situacao=EXCLUIR
```

Somente manter:

```http
GET /apuracao/analises/sobreposicao-interrupcao?anomes=202605&situacao=MANTER
```

## Próximo passo

Integrar esta análise às filas materializadas:

- regra: `sobreposicao_interrupcao`
- chave de decisão: `interrupcao` ou `NUM_SEQ_INTRP`
- ação sugerida `EXCLUIR` deve alimentar decisão governada;
- após aprovação, aplicar `ESTADO_INTRP = 7` e `NUM_MOTIVO_TRAT_DIF_UCI = 91` na base corrigida.

