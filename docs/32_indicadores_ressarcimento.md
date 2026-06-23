# Indicadores de Ressarcimento

## Objetivo

Materializar uma visão por UC para estimar impacto de ressarcimento a partir dos indicadores de continuidade.

Arquivo gerado:

```text
data/mart/indicadores/indicadores_ressarcimento_[anomes].parquet
```

Arquivo atual:

```text
data/mart/indicadores/indicadores_ressarcimento_ATUAL.parquet
```

## Entradas

### Indicadores por UC

```text
data/mart/indicadores/indicadores_uc_[anomes].parquet
```

Gerado por:

```cmd
python -m backend.scripts.materializar_indicadores_continuidade --anomes 202605
```

### Metas UC

O serviço procura automaticamente arquivos em:

```text
data/external/iqs/raw
data/external/iqs/mart
```

Nomes aceitos:

```text
metas_uc_[anomes].parquet
metas_uc_[ano].parquet
mart_metas_uc_[anomes].parquet
mart_metas_uc_[ano].parquet
IQS_METAS_UC_[ano].parquet
iqs_metas_uc_[ano].parquet
```

## Colunas Esperadas em Metas

O serviço detecta nomes alternativos:

| Papel | Colunas aceitas |
|---|---|
| UC | `ISN_UC`, `UC`, `NUM_UC`, `NUM_UC_UCI`, `NUM_UC_HCAI` |
| Limite DIC | `META_DIC`, `DIC_MENSAL`, `LIMITE_DIC`, `DIC_LIMITE`, `DIC_META`, `DIC` |
| Limite FIC | `META_FIC`, `FIC_MENSAL`, `LIMITE_FIC`, `FIC_LIMITE`, `FIC_META`, `FIC` |
| Limite DMIC | `META_DMIC`, `DMIC_MENSAL`, `LIMITE_DMIC`, `DMIC_LIMITE`, `DMIC_META`, `DMIC` |
| Conjunto | `COD_CONJUNTO_ANEEL`, `COD_CONJTO_ELET_ANEEL_INTRP`, `CONJUNTO` |
| Ano referência | `ANO_REF`, `ANO`, `ANO_REFERENCIA` |
| Valor referência | `EUSD_MEDIO`, `EUSD_MEDIA`, `VALOR_EUSD`, `VL_EUSD`, `VALOR_REFERENCIA`, `VL_REFERENCIA` |

Base validada em `202605`:

```text
ISN_UC
COD_CONJUNTO_ANEEL
ANO_REF
META_DIC
META_FIC
META_DMIC
```

## Regras Materializadas

Para cada UC e cenário:

```text
excedente_dic_horas = max(dic_horas - limite_dic_horas, 0)
excedente_fic = max(fic - limite_fic, 0)
excedente_dmic_horas = max(dmic_horas - limite_dmic_horas, 0)
```

Flags:

```text
violou_dic
violou_fic
violou_dmic
possui_violacao
```

## Valor Estimado

Quando existir coluna de valor de referência na base de metas:

```text
valor_ressarcimento_estimado =
  (excedente_dic_horas + excedente_fic + excedente_dmic_horas)
  * valor_referencia_ressarcimento
```

Status:

```text
ESTIMATIVA_OPERACIONAL_EXCEDENTE_X_VALOR_REFERENCIA
```

Quando não existir valor de referência:

```text
valor_ressarcimento_estimado = NULL
status_formula_ressarcimento = SEM_VALOR_REFERENCIA_FORMULA_OFICIAL_PENDENTE
```

## Observação Importante

O mart inicial calcula violações e estrutura a visão para decisão do gestor.

O valor monetário deve ser validado contra a regra oficial de compensação vigente do PRODIST/IQS antes de ser usado como valor regulatório final.

## Comando

```cmd
python -m backend.scripts.materializar_ressarcimento --anomes 202605
```

## Endpoints

```text
POST /indicadores/ressarcimento/{anomes}/materializar
GET  /indicadores/ressarcimento/{anomes}/resumo
GET  /indicadores/ressarcimento/{anomes}/dados
```

## Critério de Aceite

- Gerar `indicadores_ressarcimento_202605.parquet`.
- Gerar `indicadores_ressarcimento_ATUAL.parquet`.
- Informar totais de violações antes/depois.
- Informar status da fórmula de ressarcimento.
- Não sobrescrever indicadores de continuidade.

## Fonte VRC

O valor de referência para cálculo monetário do ressarcimento deve vir da consulta:

```text
backend/app/sql/iqs/vrc.sql
```

Consulta:

```sql
SELECT
    ue.ISN_UC,
    ue.NUM_CONJTO_ANEEL_FIXO_UC AS cea,
    ue.INDIC_LOCAL_TEC_UC AS urb_rur,
    ue.COD_GRUPO_NIVEL_TENSAO_UC,
    ue.COD_NIVEL_TENSAO_UC,
    NVL(ue.VAL_BASE_CALC_COMPEN_UC, 0) AS VRC
FROM CIS.UC_ENERGIA ue
WHERE ue.TIPO_SIT_UC IN ('LG', 'CR')
```

Arquivos aceitos:

```text
data/external/iqs/raw/vrc_[anomes].parquet
data/external/iqs/raw/vrc.parquet
data/external/iqs/mart/mart_vrc_[anomes].parquet
data/external/iqs/mart/mart_vrc.parquet
```

Quando existir VRC, o status da fórmula será:

```text
ESTIMATIVA_OPERACIONAL_EXCEDENTE_X_VRC
```

Comando de extração:

```cmd
python -m backend.scripts.extrair_iqs --consulta vrc --anomes 202605
```

Depois:

```cmd
python -m backend.scripts.materializar_ressarcimento --anomes 202605
```
