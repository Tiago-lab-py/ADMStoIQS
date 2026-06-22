# Sprint 10 — Produto IQS Massivo

## Objetivo

Entregar uma versão operacional do ADMStoIQS capaz de gerar, ainda no fluxo local, os CSVs tratados para envio ao IQS a partir da apuração mensal.

O foco desta sprint é transformar o pipeline já validado em uma experiência executável pelo gestor, com rastreabilidade e segurança mínima.

## Estado Atual

- Extração OMS diária e incremental está estruturada.
- Mart consolidado `agrupamento_oms_UNION.parquet` está funcionando.
- Apuração mensal gera `agrupamento_oms_APURACAO_[anomes].parquet`.
- Análise de sobreposição por interrupção/equipamento materializa:
  - `analise_sobreposicao_interrupcao_APURACAO_[anomes].parquet`
  - `analise_sobreposicao_interrupcao_APURACAO_ATUAL.parquet`
- Tratamento massivo já gerou:
  - `agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet`
  - `agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet`
  - `log_tratamento_massivo_[anomes].parquet`
- Portal gestor e telas React já estão disponíveis.

## Escopo da Sprint

### 1. Validar exportação tratada

Executar e corrigir, se necessário:

```cmd
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
```

Resultado esperado:

- CSVs regionais gerados em `data/exports/iqs`.
- Separador `|`.
- Cabeçalho no layout esperado pelo IQS.
- Arquivos separados por `REGIONAL_ORIGEM`.

### 2. Criar experiência do gestor

Adicionar no frontend definitivo uma seção de tratamento massivo com:

- competência de apuração;
- botão para gerar base tratada;
- botão para exportar CSVs tratados;
- cards com:
  - total original;
  - removidos por horário negativo;
  - removidos por causa/componente ausente;
  - removidos por sobreposição;
  - total final;
- link ou lista dos CSVs gerados.

### 3. Governança mínima

Registrar em parquet:

- competência;
- usuário;
- perfil;
- ação executada;
- data/hora;
- origem;
- destino;
- totais removidos;
- status;
- erro, quando houver.

### 4. Revisão técnica da regra massiva

A regra massiva para produto do dia deve:

- remover registros com duração negativa;
- remover registros sem causa ou componente;
- remover interrupções classificadas como `EXCLUIR` na análise de sobreposição;
- marcar tratamento no log;
- preservar a base original de apuração.

## Fora do Escopo Desta Sprint

- Tratamento manual individual de registros.
- Edição linha a linha de causa/componente.
- Recálculo oficial definitivo de DEC/FEC.
- Integração automática diária via agendador.
- Envio automático para pasta final do IQS.

## Critérios de Aceite

- `gerar_apuracao_tratada` executa com sucesso para `202605`.
- `exportar_iqs_tratado` gera pelo menos um CSV regional.
- API expõe resumo do tratamento massivo.
- Frontend permite executar ou acompanhar as etapas principais.
- Logs ficam gravados em `data/logs`.
- Nenhum dado original é sobrescrito.

## Comandos de Validação

```cmd
python -m backend.scripts.materializar_sobreposicao_interrupcao --anomes 202605
python -m backend.scripts.gerar_apuracao_tratada --anomes 202605
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
python -m backend.scripts.run_api
```

Endpoints úteis:

```text
GET  http://127.0.0.1:8000/tratamento-massivo/202605/resumo
POST http://127.0.0.1:8000/tratamento-massivo/202605/gerar
POST http://127.0.0.1:8000/tratamento-massivo/202605/exportar-csv
```

## Próximo Passo Imediato

Validar a exportação dos CSVs tratados. Se o comando falhar, corrigir primeiro o backend antes de avançar no frontend.

## Validação Realizada

Em 2026-06-22, a exportação tratada foi validada com sucesso para `202605`:

```cmd
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
```

Resultado:

- total de arquivos: `6`;
- total de linhas: `19.022.187`;
- destino: `data/exports/iqs`;
- regionais exportadas:
  - `CSL`: `1.768.202`;
  - `LES`: `3.118.827`;
  - `NRO`: `3.113.390`;
  - `NRT`: `2.295.655`;
  - `OES`: `4.385.102`;
  - `SEM_REGIONAL`: `4.341.011`.

## Atualização do Frontend

Foi adicionada ao portal gestor a página `Produto IQS`, com:

- cards do tratamento massivo;
- botão `Gerar base tratada`;
- botão `Exportar CSV IQS`;
- mensagem de processamento em andamento;
- mensagem de processamento concluído;
- tabela dos CSVs exportados na sessão.

Próxima validação:

```cmd
cd D:\ADMStoIQS\frontend
dev.cmd
```

Abrir:

```text
http://127.0.0.1:5173/
```

E acessar `Produto IQS`.
