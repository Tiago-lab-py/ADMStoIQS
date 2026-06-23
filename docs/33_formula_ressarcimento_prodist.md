# Fórmula Operacional de Ressarcimento DIC/FIC/DMIC

## Objetivo

Materializar uma estimativa operacional de ressarcimento por UC para apoiar a decisão do gestor, comparando o cenário antes e depois do tratamento massivo da apuração.

## Entradas

- `data/mart/indicadores/indicadores_uc_[anomes].parquet`
  - Deve conter os realizados líquidos por UC.
  - O cálculo líquido considera somente interrupções faturadas, com duração maior ou igual a 3 minutos e protocolo regulatório considerado.
- `data/external/iqs/raw/metas_uc_[anomes].parquet`
  - Contém as metas mensais por UC: `META_DIC`, `META_FIC` e `META_DMIC`.
- `data/external/iqs/raw/vrc_[anomes].parquet`
  - Contém `VRC`, grupo de tensão, nível de tensão, localização urbana/rural e conjunto ANEEL.

## Critério líquido

O ressarcimento não recalcula a elegibilidade de cada interrupção linha a linha. Ele usa o mart `indicadores_uc_[anomes].parquet`, que deve ter sido gerado com:

- UC faturada conforme HCAI/IQS;
- duração da interrupção maior ou igual a 3 minutos;
- `TIPO_PROTOC_JUSTIF_UCI = '0'`;
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou vazio;
- realizados mensais por UC:
  - `DIC`: soma das durações em horas;
  - `FIC`: contagem de interrupções;
  - `DMIC`: maior duração em horas.

## KEI

O fator `KEI` é definido por grupo e nível de tensão:

- Grupo `A`, níveis `1`, `2` ou `3`: `108`;
- Grupo `A`, níveis `3a`, `4` ou `S`: `40`;
- Grupo `B`: `34`;
- demais casos: `0`.

## Fórmula por UC

Para cada UC e cenário (`antes` e `depois`) são calculadas três compensações:

```text
COMP_DIC  = VRC * (DIC_REALIZADO  / 730) * KEI, se DIC_REALIZADO  > META_DIC
COMP_FIC  = VRC * (FIC_REALIZADO  / 730) * KEI, se FIC_REALIZADO  > META_FIC
COMP_DMIC = VRC * (DMIC_REALIZADO / 730) * KEI, se DMIC_REALIZADO > META_DMIC
```

O valor estimado final da UC é o maior entre os três:

```text
VALOR_RESSARCIMENTO_UC = maior(COMP_DIC, COMP_FIC, COMP_DMIC)
```

## Consolidação

O total financeiro é a soma do maior valor individual de cada UC, e não a soma direta de DIC + FIC + DMIC. Isso evita compensar a mesma UC múltiplas vezes no mesmo mês.

## Saídas

- `data/mart/indicadores/indicadores_ressarcimento_[anomes].parquet`
- `data/mart/indicadores/indicadores_ressarcimento_ATUAL.parquet`

Status da fórmula:

- `ESTIMATIVA_PRODIST_VRC_KEI_MAIOR_COMPENSACAO_UC`

## Observação

Esta materialização é uma estimativa operacional para apoio à gestão. A validação regulatória final deve confrontar os critérios oficiais completos do PRODIST e regras internas do IQS.
