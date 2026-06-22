# Sprint 2 — API de Consulta, Amostra e Exportação CSV

## Objetivo

Criar APIs no backend para leitura dos Parquets processados, geração de amostras e exportação de CSV no layout oficial.

A partir da criação do mart `OMS_union.parquet`, a API deve preferir este arquivo para consulta, amostra e exportação, pois ele contém colunas de verificação como `duracao`, `erro_duracao` e `duracao_longa`.

Quando `data/mart/OMS_union_corrigido.parquet` existir, a API deve preferir o mart corrigido para consulta, amostra, filas de tratamento e exportação, preservando `OMS_union.parquet` como base original.

## Escopo

- Listar competências disponíveis.
- Consultar dados processados por competência usando preferencialmente `data/mart/OMS_union.parquet`.
- Gerar amostra dos 100 maiores valores de `duracao` por `PID_INTRP_CONJTO_PIN`.
- Gerar CSV oficial com separador `|`.
- Registrar eventos relevantes para auditoria posterior.

## Endpoints Sugeridos

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/health` | Verificar saúde da API |
| `GET` | `/competencias` | Listar Parquets disponíveis |
| `GET` | `/competencias/{anomes}/amostra` | Retornar amostra operacional por duração |
| `GET` | `/competencias/{anomes}/dados` | Consultar dados paginados |
| `POST` | `/competencias/{anomes}/exportar-csv` | Gerar CSV oficial |
| `GET` | `/exports/{arquivo}` | Baixar CSV gerado |

## Regra da Amostra

Gerar amostra com os 100 registros de maior `duracao` por `PID_INTRP_CONJTO_PIN`.

Quando a coluna `duracao` existir no Parquet, ela deve ser usada diretamente.

Quando a coluna `duracao` ainda não existir, a API deve calcular a duração em minutos a partir de:

- `DATA_HORA_INIC_INTRP`
- `DATA_HORA_FIM_INTRP`

Se `duracao` não existir e alguma das colunas de data/hora também não existir, a API deve retornar erro funcional claro informando as colunas obrigatórias ausentes.

## Cabeçalho Oficial do CSV

O CSV exportado deve usar separador `|` e conter exatamente o cabeçalho:

```text
PID_INTRP_CONJTO_PIN|PID_POSTO_PIN|INDIC_AREA_REDE_POSTO_PIN|ALIM_INTRP_PIN|ESTADO_INTRP|ALIM_INTRP|CAR_SE|INDIC_INTRP_SE_ALIM|NUM_OCORRENCIA_ADMS|INDIC_INTRP_AT|CONS_INTRP|KVA_INTRP|NUM_OPER_CHV_INTRP|NUM_FUNCAO_ELET_HCAI|DESC_INTRP|VALID_POS_OPERACAO|DATA_HORA_INIC_INTRP|DATA_HORA_FIM_INTRP|TIPO_EQP_INTRP|COORD_X_INTRP|COORD_Y_INTRP|NUM_SEQ_INTRP|COD_CAUSA_INTRP|COD_COMP_INTRP|COD_AREA_ELET_INTRP|COD_GRUPO_COMP_INTRP|COD_COND_CLIMA_INTRP|COD_TIPO_INTRP|INDIC_JUMP_INTRP|NUM_PROTOC_JUSTIF_RESP_INTRP|TIPO_PROTOC_JUSTIF_INTRP|COD_CONJTO_ELET_ANEEL_INTRP|INDIC_CALC_DMIC_INTRP|INDIC_PONTO_CONEX_INTRP|NUM_GEO_CHV_INTRP|TIPO_REDE_CHV_INTRP|TIPO_CHV_INTRP|INDIC_PROPR_POSTO_INTRP|TENSAO_OPER_ALIM_INTRP|INDIC_DESLIG_ENT_SERV_INTRP|INDIC_PROPR_CHVP_INTRP|INDIC_CHVP_INIC_ALIM_INTRP|PID|PID_INTRP_UCI|NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI|TIPO_SIT_UC_UCI|DTHR_INICIO_INTRP_UC|NUM_INTRP_INIC_MANOBRA_UCI|NUM_MOTIVO_TRAT_DIF_UCI|UC_ACESSANTE|SIGLA_REGIONAL|NUM_PROTOC_JUSTIF_RESP_UCI|TIPO_PROTOC_JUSTIF_UCI|PID_PIN|INDIC_PROCES_IND_PIN|INDIC_SIT_PROCES_INDIC_UCI
```

## Regras de Exportação

- O CSV deve ser gerado em `data/exports/`.
- O nome deve conter competência e timestamp.
- O separador deve ser `|`.
- A ordem das colunas deve seguir o cabeçalho oficial.
- Colunas ausentes devem ser tratadas como erro funcional, salvo decisão posterior de preenchimento com vazio.

## Critérios de Aceite

- API lista competências processadas.
- API retorna amostra por competência.
- API gera CSV com cabeçalho e separador corretos.
- API informa erro claro quando coluna obrigatória não existir.
- Exportação não altera os Parquets processados.

## Implementação

Arquivos criados para a Sprint 2:

- `backend/app/services/processed_data_service.py`: leitura de Parquets processados, amostra por `duracao` e exportação CSV.
- `backend/app/api/routes.py`: endpoints FastAPI da Sprint 2.
- `backend/app/main.py`: aplicação FastAPI com CORS local para o frontend.
- `backend/app/schemas/api_models.py`: modelos de resposta e request da API.
- `backend/scripts/run_api.py`: CLI para subir a API local.

## Comandos

Subir a API:

```text
python -m backend.scripts.run_api
```

Abrir documentação interativa:

```text
http://127.0.0.1:8000/docs
```

## Endpoints Implementados

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/health` | Verificar saúde da API |
| `GET` | `/competencias` | Listar Parquets processados |
| `GET` | `/competencias/{anomes}/dados` | Consultar dados paginados |
| `GET` | `/competencias/{anomes}/amostra` | Retornar maiores durações por conjunto |
| `POST` | `/competencias/{anomes}/exportar-csv` | Gerar CSV oficial |
| `POST` | `/competencias/{anomes}/exportar-csv-regionais` | Gerar um CSV para cada regional de origem |
| `GET` | `/exports/{arquivo}` | Baixar CSV gerado |

## Consulta Paginada

Exemplo:

```text
GET /competencias/202604/dados?limit=100&offset=0
```

Quando `data/mart/OMS_union.parquet` existir, a consulta usa este mart e filtra por:

```text
ANOMES_PROCESSAMENTO = 202604
```

O endpoint `/competencias` deve listar competências a partir do mart ativo, não de `data/processed/`. Se o mart não existir ou não possuir `ANOMES_PROCESSAMENTO`, a API deve retornar erro funcional solicitando a regeneração do mart.

## Amostra

Exemplo:

```text
GET /competencias/202604/amostra?por_grupo=100
```

A amostra retorna os maiores valores de `duracao` por `PID_INTRP_CONJTO_PIN`. Se `duracao` não existir, a API calcula a duração pelas colunas `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP`. Se as colunas necessárias não existirem no Parquet, a API retorna erro funcional `400`.

## Exportação

Exemplo:

```text
POST /competencias/202604/exportar-csv
```

Exportar apenas uma regional de origem:

```json
{
  "regional_origem": "CSL",
  "usuario": "usuario.rede",
  "justificativa": "Reconstrução do arquivo regional"
}
```

O arquivo é salvo em:

```text
data/exports/
```

O CSV usa:

- Cabeçalho oficial da Sprint 2.
- Separador `|`.
- Ordem de colunas definida em `backend/app/schemas/export_layout.py`.
- Filtro opcional por `REGIONAL_ORIGEM` para reconstruir arquivos por `CSL`, `LES`, `NRO`, `NRT` ou `OES`.
- Filtro por `ANOMES_PROCESSAMENTO` quando a fonte for `OMS_union.parquet`.

Para que a API use as colunas de verificação, gerar ou regenerar o mart:

```text
python -m backend.scripts.gerar_oms_union
```

Para gerar os CSVs regionais atualizados via terminal, usando preferencialmente `OMS_union_corrigido.parquet`:

```text
python -m backend.scripts.exportar_csv_regionais --anomes 202604
```

## Exportação de Todas as Regionais

Exemplo:

```text
POST /competencias/202604/exportar-csv-regionais
```

O endpoint identifica os valores distintos de `REGIONAL_ORIGEM` no Parquet da competência e gera um CSV separado para cada regional encontrada.

Resposta esperada:

```json
{
  "anomes": "202604",
  "total_regionais": 5,
  "exports": [
    {
      "anomes": "202604",
      "regional_origem": "CSL",
      "arquivo": "agrupamento_oms_CSL_202604_20260616170000.csv",
      "caminho": "data/exports/agrupamento_oms_CSL_202604_20260616170000.csv",
      "tamanho_bytes": 123,
      "total_linhas": 100,
      "colunas": 58
    }
  ]
}
```
