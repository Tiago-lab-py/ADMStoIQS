# Plano técnico — serviços IQS

## 1. Objetivo

Definir a implementação backend para complementar o ADMStoIQS com dados do IQS, mantendo execução local e materialização em Parquet.

## 2. Premissa

A extração OMS/ADMS está adequada. O foco passa a ser enriquecer a apuração e preparar indicadores regulatórios.

## 3. Serviços propostos

### 3.1 `IqsConnectionService`

Responsabilidade:

- ler `IQS_UID`, `IQS_PWD`, `IQS_DB`;
- ler `IQS_CONFIG_DIR`;
- criar conexão com IQS;
- configurar diretório Oracle/TNS;
- mascarar senha em logs;
- validar disponibilidade.

Pendente:

- confirmar uso de `oracledb` ou `cx_Oracle`;
- validar `tnsnames.ora` em `IQS_CONFIG_DIR`;
- confirmar se `MIRA.world` resolve via Oracle Client.

### 3.2 `IqsExtractionService`

Responsabilidade:

- executar SQLs de extração;
- salvar Parquet bruto;
- registrar `log_extracao_iqs.parquet`.

Entradas:

- `anomes`;
- nome da consulta;
- arquivo SQL;
- caminho de saída.

Saídas:

- `data/external/iqs/raw/*.parquet`

### 3.3 `IqsMartService`

Responsabilidade:

- padronizar colunas;
- deduplicar dimensões;
- criar marts IQS tratados.

Saídas:

- `data/external/iqs/mart/*.parquet`

### 3.4 `ApuracaoEnrichmentService`

Responsabilidade:

- juntar apuração OMS com marts IQS;
- criar campos auxiliares para indicadores;
- salvar apuração enriquecida.

Saída:

```text
data/mart/enriquecido/apuracao_iqs_enriquecida_[anomes].parquet
```

### 3.5 `IndicadoresRegulatoriosService`

Responsabilidade:

- calcular DEC/FEC antes e depois;
- preparar base para DIC/FIC/DMIC;
- calcular estimativa de ressarcimento quando fórmula estiver validada.

Saída:

```text
data/mart/enriquecido/indicadores_regulatorios_[anomes].parquet
data/mart/enriquecido/ressarcimento_estimado_[anomes].parquet
```

## 4. Ordem de implementação

1. Validar `.env`.
2. Confirmar driver Oracle IQS.
3. Validar `IQS_CONFIG_DIR` e `tnsnames.ora`.
4. Criar conexão.
5. Extrair uma consulta simples.
6. Salvar Parquet bruto.
7. Criar log de extração.
8. Materializar mart de UC regional.
9. Enriquecer apuração.
10. Expandir para consumidores/componentes/dia crítico.
11. Conectar dashboard.

## 5. Contrato de log IQS

Arquivo:

```text
data/logs/log_extracao_iqs.parquet
```

Campos:

```text
anomes
fonte
consulta_nome
sql_path
arquivo_saida
linhas_extraidas
executado_em
status
erro
duracao_segundos
usuario_iqs
database_iqs
```

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Driver IQS indisponível localmente | Confirmar antes de codificar conexão |
| Senha exposta em log | Mascarar sempre `IQS_PWD` |
| Extração pesada no banco IQS | Materializar local e usar janela operacional |
| SQLs antigos incompatíveis | Validar uma consulta por vez |
| Dados IQS versionados por engano | `.gitignore` e checklist pré-commit |

## 7. Critério para começar código

Antes da implementação real da conexão, confirmar:

```text
driver/conector Oracle
IQS_CONFIG_DIR
tnsnames.ora
string de conexão
SQL inicial
volume esperado
janela de execução
permissão do usuário admiqs
```
