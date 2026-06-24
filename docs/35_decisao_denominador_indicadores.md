# Decisão Técnica — Denominador DEC/FEC

## Contexto

Na fase inicial, os indicadores DEC/FEC podiam ser calculados usando o fallback:

```text
COUNT(DISTINCT NUM_UC_UCI)
```

Esse fallback conta as UCs distintas presentes na base OMS/UCI da apuração.

## Decisão

Para a visão executiva e regulatória, o denominador preferencial passa a ser a fonte IQS materializada:

```text
data/external/iqs/mart/mart_consumidor_faturado_regional_[anomes].parquet
```

No mart, essa escolha aparece como:

```text
fonte_denominador = IQS_CONSUMIDOR_FATURADO_REGIONAL
```

## Efeito Esperado

Como:

```text
DEC = soma(DIC em horas) / quantidade_de_UCs
FEC = soma(FIC) / quantidade_de_UCs
```

qualquer alteração no denominador muda diretamente DEC e FEC.


## Critério Líquido Atual

Para compor o numerador dos indicadores, a interrupção da UC deve atender:

```text
duracao_minutos_uc >= 3
ESTADO_INTRP = '4'
TIPO_PROTOC_JUSTIF_UCI = '0'
NUM_MOTIVO_TRAT_DIF_UCI IS NULL
UC faturada no HCAI/IQS
```

## Reprocessamento

Após mudanças no denominador ou no critério líquido, executar:

```powershell
python -m backend.scripts.materializar_indicadores_continuidade --anomes 202605
python -m backend.scripts.materializar_ressarcimento --anomes 202605
```

## Validação Recomendada

Conferir no frontend ou endpoint:

```text
fonte_denominador
regra_liquido
dec_antes
dec_depois
fec_antes
fec_depois
```

O rótulo esperado da regra líquida é:

```text
ESTADO_4_DURACAO_MAIOR_IGUAL_3_PROTOCOLO_0_MOTIVO_NULO_FATURADA
```
