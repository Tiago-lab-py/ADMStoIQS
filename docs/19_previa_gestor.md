# Prévia para gestor — ADMStoIQS

## 1. Objetivo

Disponibilizar uma visão executiva para apresentação do projeto ADMStoIQS, demonstrando:

- objetivo do middleware;
- esteira operacional ADMS → IQS;
- status dos marts IQS;
- governança de alteração;
- visão futura regulatória com DEC/FEC e ressarcimento.

## 2. Página criada

Arquivo:

```text
frontend/public/gestor-preview.html
```

URL local com Vite:

```text
http://127.0.0.1:5173/gestor-preview.html
```

## 3. Preparar dados para a prévia

### 3.1 Validar IQS

```cmd
python -m backend.scripts.validar_iqs_env
python -m backend.scripts.testar_conexao_iqs
```

### 3.2 Extrair fontes IQS iniciais

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidores_regional
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidor_faturado_regional
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consistencia_uc_regional
```

Fonte anual sob demanda:

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 2026 --consulta metas_uc
```

Essa fonte não deve ser executada no botão geral por ser uma dimensão anual pesada.

### 3.3 Materializar marts IQS

```cmd
python -m backend.scripts.materializar_marts_iqs --anomes 202605
```

Saídas:

```text
data/external/iqs/mart/mart_consumidores_regional_202605.parquet
data/external/iqs/mart/mart_consumidor_faturado_regional_202605.parquet
data/external/iqs/mart/mart_consistencia_uc_regional_202605.parquet
data/external/iqs/mart/resumo_iqs_202605.parquet
data/external/iqs/mart/resumo_iqs_ATUAL.parquet
```

## 4. Rodar aplicação

API:

```cmd
python -m backend.scripts.run_api
```

Frontend:

```cmd
cd D:\ADMStoIQS\frontend
dev.cmd
```

Abrir:

```text
http://127.0.0.1:5173/gestor-preview.html
```

## 5. Mensagem sugerida para apresentação

O ADMStoIQS cria uma camada local de saneamento e governança entre o ADMS e o IQS.

O sistema:

- processa diariamente os CSVs do ADMS;
- converte para Parquet local;
- consolida e deduplica;
- prepara apuração mensal;
- complementa com dados IQS via Oracle;
- materializa marts externos;
- aplica regras de qualidade;
- registra decisões com governança;
- gera CSVs finais para o IQS com menor número de falhas.

## 6. Pontos para decisão do gestor

- Aprovar continuidade da camada local Parquet/DuckDB.
- Aprovar uso de `.env` para credenciais IQS sem versionamento.
- Aprovar design system estável.
- Aprovar próxima sprint de pendências materializadas.
- Validar necessidade de visão regulatória DEC/FEC e ressarcimento estimado.

## 7. Próximo desenvolvimento após a prévia

1. Criar `pendencias_APURACAO_[anomes].parquet`.
2. Refatorar frontend principal usando o design system.
3. Criar dashboard executivo integrado.
4. Implementar comparação antes/depois do tratamento.
5. Implementar indicadores regulatórios DEC/FEC/DIC/FIC/DMIC.

## 8. Endpoints usados pela prévia

Resumo operacional:

```text
GET /mart/resumo
```

Resumo IQS:

```text
GET /iqs/resumo
```

Arquivos raw IQS vistos pela API:

```text
GET /iqs/raw
```

Materialização IQS:

```text
POST /iqs/materializar/{anomes}
```

Materialização de fonte anual sob demanda:

```text
POST /iqs/materializar-fonte/metas_uc/2026
```

Diagnóstico de configuração IQS:

```text
GET /iqs/config
```

## 9. Validação rápida da API

Com a API ligada, acessar:

```text
http://127.0.0.1:8000/iqs/resumo
http://127.0.0.1:8000/iqs/config
http://127.0.0.1:8000/iqs/raw
```

Na prévia:

```text
http://127.0.0.1:5173/gestor-preview.html
```

Clicar em:

```text
Atualizar marts IQS
```

Resultado esperado:

- mensagem vermelha enquanto processa;
- mensagem verde ao concluir;
- tabela de marts IQS atualizada.
