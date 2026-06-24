# Indicadores de Continuidade — DEC, FEC, DIC, FIC e DMIC

## Objetivo

Adicionar ao ADMStoIQS uma camada de apuração de impacto regulatório para apoiar a tomada de decisão do gestor antes da geração final dos CSVs para o IQS.

O dashboard executivo deve mostrar o efeito do tratamento nos indicadores:

- antes do tratamento;
- depois do tratamento massivo;
- diferença absoluta;
- diferença percentual;
- visão por regional;
- visão Copel;
- visão por UC quando aplicável.

## Conceitos Operacionais

### DIC

Duração de interrupção individual por unidade consumidora.

No contexto do arquivo OMS/UCI:

```text
DIC_UC = soma das durações das interrupções da UC no período
```

Unidade recomendada para apresentação:

```text
horas
```

### FIC

Frequência de interrupção individual por unidade consumidora.

```text
FIC_UC = quantidade de interrupções distintas da UC no período
```

### DMIC

Duração máxima de interrupção contínua individual por unidade consumidora.

```text
DMIC_UC = maior duração individual de interrupção da UC no período
```

### DEC

Duração equivalente de interrupção por conjunto/agregado.

```text
DEC = soma(DIC_UC) / quantidade_de_UCs
```

### FEC

Frequência equivalente de interrupção por conjunto/agregado.

```text
FEC = soma(FIC_UC) / quantidade_de_UCs
```

## Base de Cálculo

### Antes do tratamento

Arquivo:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

### Depois do tratamento

Arquivo:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet
```

### Denominadores

Para DEC/FEC, a quantidade de UCs deve vir preferencialmente das fontes IQS materializadas:

```text
data/external/iqs/mart/mart_consumidor_faturado_regional_[anomes].parquet
data/external/iqs/mart/mart_consumidores_regional_[anomes].parquet
```

Quando não houver denominador IQS disponível, usar fallback documentado:

```text
COUNT(DISTINCT NUM_UC_UCI)
```

Esse fallback deve ser sinalizado no mart para evitar interpretação regulatória indevida.

### Mudança de denominador

Durante o desenvolvimento, o indicador podia usar como fallback:

```text
COUNT(DISTINCT NUM_UC_UCI)
```

Com a materialização IQS disponível, o denominador preferencial passou a ser:

```text
IQS_CONSUMIDOR_FATURADO_REGIONAL
```

Isso pode alterar o valor de DEC/FEC. Exemplo: se o divisor IQS for menor que o total de UCs distintas presentes no OMS, o DEC/FEC aumenta. Portanto, diferenças como `DEC antes` sair de aproximadamente `0,76` para `1,00` são esperadas quando a fonte do denominador muda.

## Filtro de UC Faturada

Para cálculo dos indicadores individuais e agregados, considerar a situação de faturamento da UC no IQS/HCAI.

Fonte IQS proposta:

```sql
SELECT DISTINCT
    NUM_UC_HCAI AS uc,
    INDIC_FAT_HCAI AS faturado,
    CASE
        WHEN INDIC_REG_ORIG_INTRP_HCAI = 'P' THEN 'CSL'
        WHEN INDIC_REG_ORIG_INTRP_HCAI = 'L' THEN 'NRT'
        WHEN INDIC_REG_ORIG_INTRP_HCAI = 'M' THEN 'NRO'
        WHEN INDIC_REG_ORIG_INTRP_HCAI = 'C' THEN 'LES'
        WHEN INDIC_REG_ORIG_INTRP_HCAI = 'V' THEN 'OES'
        ELSE 'COPEL'
    END AS regional
FROM iqs.HIST_CONS_AFETADO_INTERRUPCAO hcai
WHERE to_char(hcai.DATA_INTRP_HCAI, 'yyyymm') = :anomes
  AND INDIC_UC_ACESS_HCAI = 'N'
```

Regra para numerador:

- quando a fonte `uc_faturada_hcai_[anomes].parquet` estiver disponível, manter no cálculo apenas UCs com `faturado = 'S'`;
- essa fonte define se a interrupção da UC entra ou não entra na apuração individual;
- quando a fonte não estiver disponível, calcular com fallback e sinalizar `filtro_faturamento = NAO_APLICADO`;
- manter o campo `filtro_faturamento` nos marts de indicadores.

Regra para denominador de DEC/FEC:

- usar preferencialmente `IQS_COnsumidor_faturado_regional.sql`, materializado como `mart_consumidor_faturado_regional_[anomes].parquet`;
- nessa consulta, a regional vem de `REGIONAL_TOTAL` e o divisor vem de `UC_faturada`;
- se essa fonte não existir, usar `mart_consumidores_regional_[anomes].parquet`;
- se nenhuma fonte IQS existir, usar fallback `COUNT(DISTINCT NUM_UC_UCI)`;
- registrar a origem em `fonte_denominador`.

## Campos OMS Necessários

Campos mínimos:

```text
ANOMES_PROCESSAMENTO
REGIONAL_ORIGEM
COD_CONJTO_ELET_ANEEL_INTRP
NUM_SEQ_INTRP
NUM_INTRP_UCI
NUM_POSTO_UCI
NUM_UC_UCI
DTHR_INICIO_INTRP_UC
DATA_HORA_INIC_INTRP
DATA_HORA_FIM_INTRP
ESTADO_INTRP
NUM_MOTIVO_TRAT_DIF_UCI
```

## Cálculo da Duração por UC

A duração individual deve priorizar o início da interrupção na UC:

```text
inicio_uc = DTHR_INICIO_INTRP_UC
fim = DATA_HORA_FIM_INTRP
duracao_minutos_uc = fim - inicio_uc
```

Fallback quando `DTHR_INICIO_INTRP_UC` estiver ausente:

```text
inicio_uc = DATA_HORA_INIC_INTRP
```

Registros com duração negativa ou datas inválidas devem ser classificados como inconsistência e não devem compor a visão regulatória final sem decisão governada.

## Critério de Interrupção Líquida

Para entrar no cálculo de `DIC`, `FIC`, `DMIC`, `DEC` e `FEC`, a interrupção da UC deve ser considerada líquida.

Critério aplicado:

```text
duracao_minutos_uc >= 3
AND ESTADO_INTRP = '4'
AND TIPO_PROTOC_JUSTIF_UCI = '0'
AND NUM_MOTIVO_TRAT_DIF_UCI IS NULL
AND UC faturada
```

Onde:

- `duracao_minutos_uc` é calculada entre `DTHR_INICIO_INTRP_UC` e `DATA_HORA_FIM_INTRP`;
- `ESTADO_INTRP = '4'` restringe a apuração aos registros válidos para indicador;
- `TIPO_PROTOC_JUSTIF_UCI = '0'` deve ser aplicado de forma estrita;
- `NUM_MOTIVO_TRAT_DIF_UCI` deve estar nulo ou vazio;
- `UC faturada` vem da fonte IQS/HCAI `uc_faturada_hcai_[anomes].parquet`.

O mart deve registrar:

```text
regra_liquido = ESTADO_4_DURACAO_MAIOR_IGUAL_3_PROTOCOLO_0_MOTIVO_NULO_FATURADA
```

Quando o frontend ainda exibir o rótulo antigo `DURACAO_MAIOR_IGUAL_3_PROTOCOLO_0_FATURADA`, os indicadores devem ser rematerializados para atualizar o metadado da regra.

## Marts Propostos

### Mart UC

Arquivo:

```text
data/mart/indicadores/indicadores_uc_[anomes].parquet
```

Grão:

```text
cenario | anomes | regional | conjunto | NUM_POSTO_UCI | NUM_UC_UCI
```

Colunas:

```text
cenario
anomes
regional_origem
cod_conjunto_aneel
num_posto_uci
num_uc_uci
dic_horas
fic
dmic_horas
interrupcoes_distintas
fonte_denominador
gerado_em
```

### Mart Agregado

Arquivo:

```text
data/mart/indicadores/indicadores_agregado_[anomes].parquet
```

Grão:

```text
cenario | anomes | nivel | regional | conjunto
```

Níveis:

- `COPEL`;
- `REGIONAL`;
- `CONJUNTO`.

Colunas:

```text
cenario
anomes
nivel
regional_origem
cod_conjunto_aneel
quantidade_ucs
soma_dic_horas
soma_fic
dec_horas
fec
dmic_max_horas
fonte_denominador
gerado_em
```

### Mart Comparativo

Arquivo:

```text
data/mart/indicadores/indicadores_comparativo_[anomes].parquet
```

Colunas:

```text
anomes
nivel
regional_origem
cod_conjunto_aneel
quantidade_ucs
dec_antes
dec_depois
dec_delta
dec_delta_percentual
fec_antes
fec_depois
fec_delta
fec_delta_percentual
dmic_max_antes
dmic_max_depois
dmic_delta
gerado_em
```

## Regras de Cenário

### Cenário antes

Ler a base original de apuração.

Classificar, mas não remover:

- horário negativo;
- causa/componente ausente;
- sobreposição;
- canceladas.

### Cenário depois

Ler a base tratada.

Esta base já deve refletir:

- remoção de duração negativa;
- remoção de causa/componente ausente;
- remoção de sobreposição classificada como `EXCLUIR`;
- remoção de canceladas quando regra estiver habilitada.

## Dashboard Executivo

O dashboard do gestor deve incluir:

- DEC antes/depois;
- FEC antes/depois;
- DMIC máximo antes/depois;
- DIC médio por UC antes/depois;
- FIC médio por UC antes/depois;
- impacto por regional;
- ranking dos maiores ganhos;
- ranking dos maiores riscos;
- indicador de fonte do denominador.

## Critérios de Aceite

- Gerar marts de indicadores para `202605`.
- Calcular indicadores para os cenários `antes` e `depois`.
- Materializar comparativo antes/depois.
- Expor endpoint de resumo para o frontend.
- Mostrar cards no dashboard executivo.
- Informar quando o denominador for fallback por `COUNT(DISTINCT NUM_UC_UCI)`.

## Scripts Propostos

```cmd
python -m backend.scripts.materializar_indicadores_continuidade --anomes 202605
```

## Implementação Inicial

Foram adicionados:

- serviço `backend/app/services/indicadores_continuidade_service.py`;
- script `backend/scripts/materializar_indicadores_continuidade.py`;
- endpoint `POST /indicadores/continuidade/{anomes}/materializar`;
- endpoint `GET /indicadores/continuidade/{anomes}/resumo`;
- endpoint `GET /indicadores/continuidade/{anomes}/comparativo`;
- página `Indicadores` no portal gestor.

## Comando de Teste

Extrair a fonte IQS de UC faturada:

```cmd
python -m backend.scripts.extrair_iqs --anomes 202605 --consulta uc_faturada_hcai
```

Se a extração já tiver sido feita sem `DISTINCT`, compactar localmente sem consultar novamente o Oracle:

```cmd
python -m backend.scripts.compactar_uc_faturada_hcai --anomes 202605
```

Referência validada para `202605`:

```text
uc_faturada_hcai distinct esperado: aproximadamente 3.863.918 registros
```

Depois materializar os indicadores:

```cmd
python -m backend.scripts.materializar_indicadores_continuidade --anomes 202605
```

Depois subir a API:

```cmd
python -m backend.scripts.run_api
```

Validar:

```text
http://127.0.0.1:8000/indicadores/continuidade/202605/resumo
```

## Endpoints Propostos

```text
POST /indicadores/continuidade/{anomes}/materializar
GET  /indicadores/continuidade/{anomes}/resumo
GET  /indicadores/continuidade/{anomes}/comparativo
```

## Mart Derivado de Ressarcimento

Após materializar os indicadores de continuidade, gerar:

```cmd
python -m backend.scripts.materializar_ressarcimento --anomes 202605
```

Saída:

```text
data/mart/indicadores/indicadores_ressarcimento_202605.parquet
```

Detalhes em:

```text
docs/32_indicadores_ressarcimento.md
```

## Observação Regulatória

As fórmulas de cálculo devem ser validadas contra a versão vigente do PRODIST Módulo 8 e contra a regra interna de apuração do IQS antes de serem usadas como valor oficial. Nesta etapa, o objetivo é apoiar decisão de tratamento e evidenciar impacto antes/depois.
## Regra líquida vigente

Para DEC/FEC/DIC/FIC/DMIC, a base líquida considerada pelo portal gestor deve seguir a regra:

`ESTADO_4_DURACAO_MAIOR_IGUAL_3_PROTOCOLO_0_MOTIVO_NULO_FATURADA`

Critérios aplicados:

- `ESTADO_INTRP = '4'`;
- duração válida e maior ou igual a 3 minutos;
- `TIPO_PROTOC_JUSTIF_UCI = '0'`;
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou vazio;
- UC faturada conforme `uc_faturada_hcai_[anomes].parquet`.
