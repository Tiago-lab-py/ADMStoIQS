# 29 - Roteiro Produto Hoje: CSV Tratado para Envio ao IQS

## Objetivo do Dia

Entregar uma versão funcional do produto que:

1. lê a apuração OMS em parquet;
2. aplica limpezas massivas governadas;
3. gera uma base tratada;
4. exporta CSV no layout IQS;
5. permite ao gestor visualizar antes/depois;
6. prepara o caminho para ajustes manuais por analista.

## Produto Mínimo de Hoje

### Entrada

Fonte principal:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

Exemplo:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_202605.parquet
```

### Saídas

Base tratada:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet
```

Base tratada atual:

```text
data/mart/apuracao/agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet
```

CSV final para IQS:

```text
data/exports/iqs/agrupamento_oms_IQS_[regional]_[anomes]_[timestamp].csv
```

Log de execução:

```text
data/logs/log_tratamento_massivo_[anomes].parquet
```

## Regras Massivas para o Gestor

Estas regras são aplicadas em massa, com rastreabilidade, antes do analista atuar manualmente.

### 1. Horário negativo

Identificação:

```text
DATA_HORA_FIM_INTRP < DATA_HORA_INIC_INTRP
```

Tratamento de hoje:

- remover do CSV final;
- registrar no log como `removido_horario_negativo`;
- manter disponível para análise manual futura.

Motivo:

- horário negativo não deve seguir para IQS sem validação;
- ainda teremos tela específica para ajustar início/fim.

### 2. Causa ou componente nulo

Identificação:

```text
COD_CAUSA_INTRP IS NULL OR vazio
COD_COMP_INTRP IS NULL OR vazio
```

Tratamento de hoje:

- remover do CSV final;
- registrar no log como `removido_sem_causa_componente`;
- manter disponível para tela futura de sugestão/correção.

Motivo:

- IQS tende a rejeitar ou gerar inconsistência;
- correção depende de regra técnica ou decisão do analista.

### 3. Sobreposição por interrupção/equipamento

Fonte da análise:

```text
data/mart/apuracao/analise_sobreposicao_interrupcao_APURACAO_[anomes].parquet
```

Regra:

- para `acao_sugerida = EXCLUIR`, remover a interrupção do CSV final;
- a chave principal da exclusão é `NUM_SEQ_INTRP`;
- registrar no log como `removido_sobreposicao_interrupcao`;
- sugestão técnica:
  - `ESTADO_INTRP = 7`;
  - `NUM_MOTIVO_TRAT_DIF_UCI = 91`.

Tratamento de hoje:

- remover do CSV final;
- não sobrescrever o parquet original;
- registrar decisão automática como tratamento massivo.

## Visão para o Gestor

Criar página no portal:

```text
Tratamento massivo
```

Deve apresentar:

- competência selecionada;
- total original;
- removidos por horário negativo;
- removidos por causa/componente;
- removidos por sobreposição;
- total final para IQS;
- quantidade por regional;
- botão `Gerar base tratada`;
- botão `Exportar CSV IQS`;
- link para baixar CSVs.

## Fluxo Operacional de Hoje

### Passo 1 - Garantir apuração

```bat
python -m backend.scripts.validar_retomada_iqs --anomes 202605 --materializar-pendencias
```

### Passo 2 - Materializar sobreposição por interrupção

```bat
python -m backend.scripts.materializar_sobreposicao_interrupcao --anomes 202605
```

### Passo 3 - Gerar base tratada

Novo script a criar:
Implementado:

```bat
python -m backend.scripts.gerar_apuracao_tratada --anomes 202605
```

Responsabilidade:

- ler `agrupamento_oms_APURACAO_202605.parquet`;
- excluir registros com horário negativo;
- excluir registros com causa/componente nulos;
- excluir registros com `NUM_SEQ_INTRP` sugeridas como `EXCLUIR`;
- gravar parquet tratado;
- gravar log massivo.

### Passo 4 - Exportar CSV IQS

Novo script/endpoint a criar:
Implementado:

```bat
python -m backend.scripts.exportar_iqs_tratado --anomes 202605
```

Responsabilidade:

- ler base tratada;
- aplicar layout oficial do CSV;
- separar por `REGIONAL_ORIGEM`;
- exportar com delimitador `|`;
- preservar cabeçalho definido na especificação.

## APIs Necessárias

### Gerar base tratada

```http
POST /tratamento-massivo/{anomes}/gerar
```

Retorno esperado:

```json
{
  "anomes": "202605",
  "total_original": 20925470,
  "removido_horario_negativo": 5,
  "removido_sem_causa_componente": 8,
  "removido_sobreposicao_interrupcao": 15647,
  "total_final": 20909810,
  "parquet": "data/mart/apuracao/agrupamento_oms_APURACAO_202605_TRATADO.parquet",
  "status": "processado"
}
```

### Resumo da base tratada

```http
GET /tratamento-massivo/{anomes}/resumo
```

### Exportar CSV IQS

```http
POST /tratamento-massivo/{anomes}/exportar-csv
```

### Baixar CSV

```http
GET /exports/iqs/{arquivo}
```

## Frontend Necessário Hoje

Adicionar no portal gestor:

```text
Tratamento massivo
```

Componentes:

- card `Total original`;
- card `Removidos`;
- card `Total final`;
- card `Regionais exportadas`;
- tabela `Remoções por regra`;
- tabela `Remoções por regional`;
- botão `Gerar base tratada`;
- botão `Exportar CSV IQS`;
- mensagens:
  - vermelho: `Aguarde processamento...`;
  - verde: `Processamento concluído`.

## Próxima Fase: Analista

Depois da entrega massiva para gestor, evoluir telas por analista.

### Ajuste de horário

Permitir alterar:

- `DATA_HORA_INIC_INTRP`;
- `DATA_HORA_FIM_INTRP`.

Com validações:

- fim maior que início;
- duração longa;
- fuso horário até 3 horas;
- justificativa obrigatória.

### Ajuste causa/componente

Permitir alterar:

- `COD_CAUSA_INTRP`;
- `COD_COMP_INTRP`.

Com sugestão baseada em:

- descrição da ocorrência;
- equipamento;
- regional;
- histórico IQS;
- padrões anteriores.

### Anomalias sucessivas

Validar registros sucessivos:

- mesma UC:
  - `NUM_UC_UCI`;
  - `NUM_POSTO_UCI`;
  - intervalo temporal.
- mesmo equipamento:
  - `NUM_OPER_CHV_INTRP`;
  - `NUM_SEQ_INTRP`;
  - início/fim.

### Governança

Toda alteração manual deve gravar:

- usuário;
- perfil;
- PC;
- IP;
- data/hora;
- campo alterado;
- valor anterior;
- valor novo;
- justificativa;
- regra de origem.

## Prioridade de Implementação Hoje

### P0 - Obrigatório

1. Criar `gerar_apuracao_tratada`.
2. Criar `exportar_iqs_tratado`.
3. Criar endpoints de tratamento massivo.
4. Criar tela `Tratamento massivo`.
5. Gerar CSV por regional.

### P1 - Se houver tempo

1. Mostrar preview de 100 registros removidos por regra.
2. Baixar log massivo.
3. Integrar decisões governadas já registradas.

### P2 - Próximo ciclo

1. Ajuste manual de horário.
2. Ajuste manual causa/componente.
3. Análise sucessiva UC/equipamento.
4. DEC/FEC antes/depois.
5. Ressarcimento DIC/FIC/DMIC.

## Critério de Sucesso do Dia

O dia termina bem se for possível:

1. selecionar competência no portal;
2. gerar base tratada;
3. visualizar resumo das remoções;
4. exportar CSV IQS por regional;
5. localizar os arquivos exportados;
6. explicar claramente ao gestor o que foi removido e por quê.
