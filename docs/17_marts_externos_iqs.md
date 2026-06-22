# Marts externos e complementação IQS

## 1. Decisão de arquitetura

A extração OMS/ADMS atual está adequada e deve ser considerada estabilizada neste momento.

O próximo ajuste do ETL deve concentrar-se em:

1. materializar os marts necessários para o projeto;
2. enriquecer a apuração com dados do IQS;
3. manter tudo local em Parquet;
4. evitar gravação em banco;
5. usar `.env` para credenciais IQS.

## 2. Configuração IQS

O acesso ao IQS deve usar variáveis de ambiente:

```env
IQS_UID=admiqs
IQS_PWD=
IQS_DB=MIRA.world
IQS_CONFIG_DIR=C:\APL\Oracle12_32\12CR2\network\admin
```

Arquivo versionado:

```text
.env.example
```

Arquivo local não versionado:

```text
.env
```

O arquivo `.env` deve conter a senha real apenas na máquina local.

## 3. Validação da configuração

Comando:

```cmd
python -m backend.scripts.validar_iqs_env
```

Saída esperada:

```text
Configuração IQS:
IQS_UID: admiqs
IQS_PWD: ***
IQS_DB: MIRA.world
IQS_CONFIG_DIR: C:\APL\Oracle12_32\12CR2\network\admin
Configurado: True
```

Se `Configurado: False`, preencher `IQS_PWD` e `IQS_CONFIG_DIR` no `.env`.

O diretório `IQS_CONFIG_DIR` deve conter a configuração Oracle Client/TNS, especialmente o arquivo:

```text
tnsnames.ora
```

O alias `IQS_DB=MIRA.world` deve existir no `tnsnames.ora`.

## 3.1 Teste de conexão Oracle

Após validar o `.env` e o `tnsnames.ora`, testar a conexão:

```cmd
python -m backend.scripts.testar_conexao_iqs
```

O script tenta os drivers nesta ordem:

1. `oracledb`
2. `cx_Oracle`

Saída esperada:

```text
Teste de conexão IQS Oracle
Usuário: admiqs
Senha: ***
DSN: MIRA.world
TNS_ADMIN: C:\APL\Oracle12_32\12CR2\network\admin
Tentando driver: oracledb
Conexão IQS OK usando oracledb. SELECT 1 retornou: 1
```

Se nenhum driver estiver instalado, instalar o driver compatível com o Oracle Client local antes de implementar as extrações.

Status validado localmente:

```text
Driver: oracledb
DSN: MIRA.world
TNS_ADMIN: C:\APL\Oracle12_32\12CR2\network\admin
SELECT 1 FROM DUAL: OK
Duração observada: 0,39s
```

## 4. Camadas de dados propostas

### 4.1 OMS/ADMS

Já existente:

```text
data/processed/agrupamento_oms_[anomes].parquet
data/mart/agrupamento_oms_UNION.parquet
data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet
```

### 4.2 IQS bruto local

Nova camada sugerida:

```text
data/external/iqs/raw/
```

Arquivos:

```text
iqs_uc_regional_[anomes].parquet
iqs_consumidores_regional_[anomes].parquet
iqs_consumidor_faturado_regional_[anomes].parquet
iqs_metas_uc_[anomes].parquet
iqs_componentes_[anomes].parquet
```

### 4.3 IQS marts tratados

Nova camada sugerida:

```text
data/external/iqs/mart/
```

Arquivos:

```text
mart_iqs_uc_regional_[anomes].parquet
mart_iqs_consumidores_[anomes].parquet
mart_iqs_componentes_[anomes].parquet
mart_iqs_metas_uc_[anomes].parquet
```

### 4.4 Marts combinados ADMStoIQS

Nova camada sugerida:

```text
data/mart/enriquecido/
```

Arquivos:

```text
apuracao_iqs_enriquecida_[anomes].parquet
indicadores_regulatorios_[anomes].parquet
ressarcimento_estimado_[anomes].parquet
pendencias_APURACAO_[anomes].parquet
```

## 5. Fontes IQS mapeadas pelos exemplos

Arquivos de referência:

```text
exemplo/17_extract_consistencia_iqs_uc_regional.sql
exemplo/IQS_METAS UC 2026.sql
exemplo/IQS_Consumidores_regional.sql
exemplo/IQS_COnsumidor_faturado_regional.sql
exemplo/extrair_componente_iqshml.py
```

Uso esperado:

| Fonte | Uso no ADMStoIQS |
|---|---|
| UC regional | validar regional correta da UC |
| consumidores regional | apoio a DEC/FEC e cobertura regional |
| consumidor faturado regional | apoio a DIC/FIC/DMIC e exposição regulatória |
| metas UC | apoiar limites/regulatórios por UC |
| componentes IQS | sugerir causa/componente ausente |

## 6. Fluxo ETL proposto

```text
CSV ADMS
  -> Parquet mensal OMS
  -> UNION OMS
  -> APURAÇÃO OMS
  -> IQS external raw
  -> IQS external mart
  -> APURAÇÃO enriquecida
  -> Pendências materializadas
  -> Resumo executivo/regulatório
  -> CSV IQS final
```

## 7. Scripts propostos

### 7.0 Teste de extração IQS

Antes das consultas reais, executar uma extração mínima em `DUAL`:

```cmd
python -m backend.scripts.extrair_iqs --anomes 202605 --consulta teste_dual
```

Entrada:

```text
backend/app/sql/iqs/teste_dual.sql
```

Saída:

```text
data/external/iqs/raw/teste_dual_202605.parquet
data/logs/log_extracao_iqs.parquet
```

Esse teste valida o fluxo completo:

```text
.env -> Oracle/TNS -> SQL -> Parquet -> log
```

### 7.1 Extrair IQS

```cmd
python -m backend.scripts.extrair_iqs --anomes 202605
```

Responsável por:

- ler `.env`;
- conectar no IQS;
- executar SQLs de extração;
- salvar Parquet bruto local.

Também é possível executar um SQL externo informando o caminho completo:

```cmd
python -m backend.scripts.extrair_iqs --anomes 202605 --sql-path "D:\ADMStoIQS\exemplo\IQS_Consumidores_regional.sql"
```

Ou usar o atalho para consultas mapeadas da pasta `exemplo`:

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidores_regional
```

Consultas mapeadas:

```text
consistencia_uc_regional
sobreposicao_hcai
consumidores_regional
consumidor_faturado_regional
metas_uc
```

Observação:

```text
metas_uc
```

é uma fonte anual pesada, baseada em `IQS_METAS UC 2026.sql`, com milhões de registros. Ela não deve entrar na rotina mensal automática nem no botão geral de atualização dos marts IQS.

Ela deve ser executada somente sob demanda:

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 2026 --consulta metas_uc
```

E materializada somente sob demanda:

```text
POST /iqs/materializar-fonte/metas_uc/2026
```

O extrator disponibiliza os seguintes binds para os SQLs:

```text
:anomes / :ANOMES
:ano / :ANO
:mes / :MES
:P_ANO
:P_MES
:P_YYYY
:P_MM
:P_MES_2D
:data_inicio / :DATA_INICIO
:data_fim / :DATA_FIM
:dt_inicio / :DT_INICIO
:dt_fim / :DT_FIM
```

Se algum SQL da pasta `exemplo` usar nomes de parâmetros diferentes, será necessário adaptar o SQL ou adicionar novos binds no serviço.

Também é possível informar binds extras pelo terminal:

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consistencia_uc_regional --bind P_ANO=2026 --bind P_MES=05
```

Use essa opção quando uma query antiga usar nomes de parâmetros específicos.

### 7.2 Materializar marts IQS

```cmd
python -m backend.scripts.materializar_marts_iqs --anomes 202605
```

Responsável por:

- padronizar nomes de colunas;
- deduplicar dimensões;
- validar regional;
- preparar lookup de consumidor;
- preparar lookup de componente.

### 7.3 Enriquecer apuração

```cmd
python -m backend.scripts.enriquecer_apuracao_iqs --anomes 202605
```

Responsável por:

- juntar apuração OMS com marts IQS;
- criar campos auxiliares para indicadores;
- salvar apuração enriquecida.

### 7.4 Rotina diária completa

```cmd
python -m backend.scripts.rotina_diaria --anomes 202605 --com-iqs
```

Responsável por:

1. verificar CSV pendente;
2. processar CSV pendente;
3. atualizar UNION;
4. gerar apuração;
5. extrair IQS;
6. materializar marts IQS;
7. enriquecer apuração;
8. materializar pendências;
9. materializar resumo;
10. gerar relatório operacional.

## 8. Regras de segurança

- Nunca versionar `.env`.
- Nunca imprimir `IQS_PWD`.
- Nunca salvar senha em log.
- Nunca subir `data/external/iqs/` para GitHub.
- Registrar apenas metadados da extração:
  - data/hora;
  - anomes;
  - consulta executada;
  - linhas extraídas;
  - status;
  - erro resumido.

## 9. Log de extração IQS

Arquivo sugerido:

```text
data/logs/log_extracao_iqs.parquet
```

Colunas:

```text
anomes
fonte
consulta_nome
arquivo_saida
linhas_extraidas
executado_em
status
erro
duracao_segundos
```

## 10. Próxima decisão

Antes de codificar a extração IQS, validar:

1. se será usado `oracledb` ou `cx_Oracle`;
2. se o Oracle Client 32-bit em `C:\APL\Oracle12_32\12CR2` está operacional;
3. se `IQS_CONFIG_DIR` contém `tnsnames.ora`;
4. se o alias `MIRA.world` resolve corretamente;
5. se os SQLs dos exemplos podem rodar diretamente;
6. se há limite de acesso ou janela operacional;
7. quais tabelas IQS são oficialmente fonte para DEC/FEC/DIC/FIC/DMIC.
