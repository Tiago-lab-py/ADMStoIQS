# 16) Consistência IQS (Expurgo/Líquido por UC Afetada)

Atualizado em: 2026-05-28

## Objetivo
Garantir a consistência do cálculo de expurgo/líquido usado no IQS, respeitando a regional responsável da **UC afetada** e não apenas o conjunto da interrupção.

## Regra de ouro
1. A regional deve ser derivada da UC afetada (`HIST_CONS_AFETADO_INTERRUPCAO` -> `UC_ENERGIA` -> `LOCALIDADE` -> `SECCIONAL` -> `REGIONAL_DISTRIBUICAO`).
2. O conjunto da interrupção é contexto operacional, mas não substitui a regional da UC para a consistência regulatória.
3. A classificação expurgo/líquido segue protocolo + tratamento diferenciado.
4. Deve haver deduplicação temporal por `num_intrp_key + num_posto + num_uc`.

## Artefatos implementados
1. SQL de consistência:
   - `sql/17_extract_consistencia_iqs_uc_regional.sql`
2. Execução ETL dedicada (não embutida no ETL diário):
   - `etl/10_consistencia_iqs.py`
3. Saída parquet:
   - `dados/mart/mart_consistencia_iqs_YYYYMM.parquet`
4. Persistência opcional no dbGUO:
   - tabela esperada: `ddcq.aap_ao_mart_consistencia_iqs`

## Como executar
1. Gerar somente parquet:
```bash
python etl/10_consistencia_iqs.py --yyyymm 202605
```
2. Gerar e persistir no dbGUO (se tabela existir):
```bash
python etl/10_consistencia_iqs.py --yyyymm 202605 --persist-db
```

## Colunas de resultado (resumo)
1. `yyyymm`
2. `arquivo_origem` (regional + COPEL)
3. `classificacao` (`Liquido`, `Expurgo`, `Bruto`)
4. `ci`, `chi`, `ci_longa`, `chi_longa_s`
5. `mercado_faturado`
6. `fec`, `dec`

## Checks mínimos pós-execução
1. Validar existência do parquet mensal em `dados/mart`.
2. Confirmar presença das três classificações por regional (`Liquido`, `Expurgo`, `Bruto`).
3. Verificar se `mercado_faturado > 0` para regionais válidas.
4. Conferir ordem e cobertura regional (`CSL`, `LES`, `NRO`, `NRT`, `OES`, `COPEL`).

## Riscos e observações
1. Carga pesada: usar job dedicado (fora do ETL diário), pois a base HCAI pode passar de 20 milhões/mês.
2. Divergências de DEC/FEC entre plataforma e IQS tendem a ocorrer quando regional é inferida por conjunto da interrupção em vez de UC afetada.
3. Próximo passo recomendado: painel no app com comparação mensal `IQS oficial x plataforma` e desvio percentual por regional/classificação.
