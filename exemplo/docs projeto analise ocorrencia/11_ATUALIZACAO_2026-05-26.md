# Atualizacao Tecnica - 2026-05-26

## Escopo
Registro consolidado das alteracoes realizadas em ETL, banco, baseline historica ISE, interface e seguranca operacional.

## ETL e Banco
- Ajustada extracao de interrupcao em `sql/01_extract_interrupcao.sql` com campos:
  - `NUMERO_OCORRENCIA`
  - `TIPO_CHV_INTRP`
  - `NUMERO_PROTOCOLO` / `NUM_PROTOCOLO`
- Aplicada migration de granularidade historica ISE:
  - `sql/13_alter_table_dbguo_aap_ao_ise_resumo_historico_granularidade.sql`
- Aplicada migration de protocolo em interrupcao:
  - `sql/14_alter_tables_dbguo_aap_ao_numero_protocolo.sql`
- Incluida tabela de componente no dbguo:
  - `ddcq.aap_ao_componente_raw`

## Baseline ISE 2024-2025
- Script dedicado: `etl/carga_unica_ise_resumo_historico.py`.
- Carga unica executada para `competencia=2025-12` com granularidade por:
  - `mes_referencia`
  - `cod_conjunto`
  - `tipo_chv_intrp`
  - `cod_causa_intrp`
  - `cod_comp_intrp`
- Persistencia da baseline em `ddcq.aap_ao_ise_resumo_historico` sem duplicidade de chave de granularidade.

## Regras de CI/CHI
- Reforcada regra de calculo para evitar inconsistencias entre campos liquidos e expurgados:
  - `CI_LIQUIDO = CI_URBANO + CI_RURAL`
  - `CHI_LIQUIDO = CHI_URBANO + CHI_RURAL`
  - `CI_EXP_TOTAL = CI_EXP_URBANO + CI_EXP_RURAL`
  - `CHI_EXP_TOTAL = CHI_EXP_URBANO + CHI_EXP_RURAL`

## Interface (em validacao funcional)
- Solicitada revisao para Home e Dashboard Executivo:
  - reduzir nulos em `numero_ocorrencia` e `componente`
  - exibir `name_conjunto` na tabela executiva de anomalias recentes
  - incluir coluna de duracao em horas
  - padronizar textos em PT-BR

## Seguranca e notificacoes
- SMTP validado em ambiente operacional com envio registrado em log.
- Fluxo de troca obrigatoria de senha no primeiro acesso validado.

## Observacoes operacionais
- Reprocessamento de maio/2026 permanece no plano, com execucao sem topologia UC quando necessario para reduzir tempo de carga.
- Confirmar reconciliacao final de marts apos rerun completo da competencia.