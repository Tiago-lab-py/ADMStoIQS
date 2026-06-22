# Arquitetura e Fluxo de Dados

## Visao geral
A plataforma segue arquitetura desacoplada:
- ETL executa em background e produz camadas de dados
- Streamlit consome apenas dados processados/marts
- Admin controla parametros, perfis e execucoes manuais

## Camadas de dados
- `dados/raw`: fonte original extraida (csv/parquet)
- `dados/processed`: tratamento, qualidade e enriquecimento
- `dados/mart`: visoes analiticas para UI
- `dados/snapshots`: historico para comparacao temporal
- `dados/validacoes`: decisoes operacionais de pos-operacao

## Fluxo oficial
1. Extracao (`sample` ou `db`)
2. Persistencia em `raw`
3. Snapshot diario
4. Tratamento de tipos e regras DQ
5. Deteccao de anomalias e regras ISE/DC
6. Geracao de marts
7. Consumo via Streamlit

## Scripts ETL
- `etl/01_extract_interrupcao.py`
- `etl/02_extract_servicos.py`
- `etl/03_snapshot_diario.py`
- `etl/04_processar_ocorrencias.py`
- `etl/05_calcular_dias_anomalos.py`
- `etl/06_analisar_ise.py`
- `etl/07_detectar_anomalias.py`
- `etl/08_gerar_mart.py`
- `etl/09_comparar_efetivacao.py`
- orquestrador: `run_etl_diario.py`

## Marts principais
- `mart_dias_anomalos.parquet`
- `mart_ocorrencias_agrupadas.parquet`
- `mart_ise.parquet`
- `mart_anomalias.parquet`
- `mart_auditoria_alteracoes.parquet`
- `mart_validacoes_pos_operacao.parquet`

## Governanca de acesso
- Controle de autenticacao via `biblioteca/auth.py`
- Autorizacao por funcionalidade (`config/perfis.yml`)
- Logs de sessao em `logs/auth_sessions.jsonl`
