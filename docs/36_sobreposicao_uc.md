# Sobreposição temporal por UC

## Objetivo

Detectar registros de UC (`NUM_UC_UCI`) em que uma interrupção está totalmente contida em outra interrupção da mesma UC, usando:

- início da UC: `DTHR_INICIO_INTRP_UC`;
- fim da interrupção: `DATA_HORA_FIM_INTRP`;
- mesma UC: `NUM_UC_UCI`;
- mesmo protocolo: `TIPO_PROTOC_JUSTIF_UCI`;
- apenas registros elegíveis: `ESTADO_INTRP = '4'` e `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou vazio.

## Regra de classificação

Para cada registro candidato `A`, procurar outro registro `B` da mesma UC e mesmo protocolo onde:

- `B.DTHR_INICIO_INTRP_UC <= A.DTHR_INICIO_INTRP_UC`;
- `B.DATA_HORA_FIM_INTRP >= A.DATA_HORA_FIM_INTRP`;
- `B.NUM_SEQ_INTRP <> A.NUM_SEQ_INTRP`;
- a janela de `B` contém totalmente a janela de `A`.

Quando a condição for verdadeira, o registro `A` deve ser sugerido para classificação:

- campo sugerido: `NUM_MOTIVO_TRAT_DIF_UCI`;
- valor sugerido: `91`;
- ação sugerida: `CLASSIFICAR_91`;
- justificativa: sobreposição temporal da UC contida em outra interrupção.

## Impacto operacional

A análise materializada deve apresentar:

- quantidade de registros de UC que receberiam motivo `91`;
- quantidade de UCs distintas afetadas;
- quantidade de interrupções distintas afetadas;
- horas-UC reduzidas;
- CHI estimado reduzido.

O CHI estimado é calculado como:

```text
CHI_ESTIMADO = duração_em_horas_da_janela_contida * KVA_INTRP
```

Quando `KVA_INTRP` estiver ausente ou inválido, o impacto financeiro/energético fica como `0`, mas a quantidade de registros e horas-UC continuam sendo apuradas.

## Implantação governada

A implantação não é automática na materialização. O fluxo é:

1. gestor executa a análise na tela operacional;
2. tela exibe cards de quantidade e impacto;
3. gestor clica em `Implantar motivo 91`;
4. sistema cria backup do parquet de apuração;
5. sistema atualiza `NUM_MOTIVO_TRAT_DIF_UCI = '91'` nos registros classificados;
6. sistema grava log nominal com usuário, perfil, IP, PC, quantidade, CHI e justificativa;
7. sistema rematerializa pendências, tratamento massivo, indicadores e ressarcimento.

## Arquivos

- análise mensal: `data/mart/apuracao/analise_sobreposicao_uc_APURACAO_[anomes].parquet`;
- análise atual: `data/mart/apuracao/analise_sobreposicao_uc_APURACAO_ATUAL.parquet`;
- backup da apuração: `data/mart/apuracao/backups/agrupamento_oms_APURACAO_[anomes]_antes_sobreposicao_uc_[timestamp].parquet`;
- log mensal: `data/logs/log_implantacao_sobreposicao_uc_[anomes].parquet`;
- log atual: `data/logs/log_implantacao_sobreposicao_uc_ATUAL.parquet`.

## Validação

Comandos sugeridos:

```powershell
python -m backend.scripts.materializar_sobreposicao_uc --anomes 202605
python -m backend.scripts.implantar_sobreposicao_uc --anomes 202605 --usuario admin --perfil admin
python -m backend.scripts.gerar_apuracao_tratada --anomes 202605
python -m backend.scripts.materializar_indicadores_continuidade --anomes 202605
python -m backend.scripts.materializar_ressarcimento --anomes 202605
```
