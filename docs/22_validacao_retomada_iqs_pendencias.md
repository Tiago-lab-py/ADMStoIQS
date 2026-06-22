# 22 - Validação de Retomada: IQS e Pendências Materializadas

## Objetivo

Validar a rota de resumo IQS com atualização forçada e, somente depois de sucesso, materializar as pendências da apuração.

Fluxo alvo:

1. API local ativa.
2. `/iqs/resumo?refresh=true&anomes=202605` sem fontes com `status=erro`.
3. Pendências materializadas para a apuração.
4. Resumo de pendências disponível para o frontend executivo.

## Pré-requisitos

Em um terminal:

```bat
d:\ADMStoIQS\.venv\Scripts\activate.bat
cd /d D:\ADMStoIQS
python -m backend.scripts.run_api
```

Em outro terminal:

```bat
d:\ADMStoIQS\.venv\Scripts\activate.bat
cd /d D:\ADMStoIQS
```

## Validação IQS

Executar:

```bat
python -m backend.scripts.validar_retomada_iqs --anomes 202605
```

Critério de aceite:

- Deve retornar `IQS OK: resumo atualizado sem erro`.
- Deve ter pelo menos uma fonte com `status=processado`.
- Não pode haver fonte com `status=erro`.
- Fontes sem raw ainda permitido: `pendente_raw`, desde que sejam fontes planejadas para fase futura.

## Fechar pendências materializadas

Depois do IQS OK:

```bat
python -m backend.scripts.validar_retomada_iqs --anomes 202605 --materializar-pendencias
```

Critério de aceite:

- Materialização de pendências conclui sem HTTP 500.
- `/apuracao/pendencias/resumo` retorna JSON válido.
- O frontend consegue ler os cards e listas materializadas sem recalcular tudo na abertura.

## Rotas equivalentes

Para validar direto no navegador ou Swagger:

- `GET http://127.0.0.1:8000/iqs/resumo?refresh=true&anomes=202605`
- `POST http://127.0.0.1:8000/apuracao/pendencias/materializar/202605`
- `GET http://127.0.0.1:8000/apuracao/pendencias/resumo`

## Observação sobre metas UC

`metas_uc` é anual e pesado. Não deve entrar no refresh mensal automático.

Extração sob demanda:

```bat
python -m backend.scripts.extrair_iqs_exemplo --anomes 2026 --consulta metas_uc
```

Materialização sob demanda:

```http
POST /iqs/materializar-fonte/metas_uc/2026
```

## Se der erro

Copiar:

- JSON retornado pela rota.
- Traceback do terminal da API.
- Nome da fonte IQS com `status=erro`.
- Caminho do arquivo raw/mart envolvido.

## Resultado validado em 2026-06-22

Competência testada: `202605`.

### IQS

- `consumidores_regional`: `processado`, 7 linhas.
- `consumidor_faturado_regional`: `processado`, 6 linhas.
- `consistencia_uc_regional`: `processado`, 18 linhas.
- `sobreposicao_hcai`: `pendente_raw`, mantido como fonte futura.
- Fontes com erro: 0.
- Resumo: `data/external/iqs/mart/resumo_iqs_202605.parquet`.
- Resumo atual: `data/external/iqs/mart/resumo_iqs_ATUAL.parquet`.

### Pendências de apuração

- Origem: `data/mart/apuracao/agrupamento_oms_APURACAO_202605.parquet`.
- Saída: `data/mart/apuracao/pendencias_APURACAO_202605.parquet`.
- Saída atual: `data/mart/apuracao/pendencias_APURACAO_ATUAL.parquet`.
- Total de pendências: 15.660.
- `horario_negativo`: 5.
- `sobreposicao_interrupcao`: 15.647.
- `sem_causa_componente`: 8.

Status da retomada: validada.
