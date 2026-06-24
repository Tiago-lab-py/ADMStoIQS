# Sobreposição UC — Fase 2: interseção temporal parcial

## Objetivo

Criar um segundo módulo de tratamento para sobreposição temporal na unidade consumidora (`NUM_UC_UCI`), sem excluir registros inicialmente.

A Fase 2 trata o caso em que uma interrupção da mesma UC e do mesmo protocolo inicia antes de outra terminar:

```text
Registro A: início 00:00 | fim 02:00
Registro B: início 01:00 | fim 03:00
```

Nesse cenário, o Registro B deve ter o início deslocado para o fim do Registro A:

```text
Registro B: início 02:00 | fim 03:00
```

Além disso, o campo `NUM_INTRP_INIC_MANOBRA_UCI` do Registro B deve receber o `NUM_SEQ_INTRP` do Registro A.

## Escopo da regra

Somente entram na análise registros com:

- `ESTADO_INTRP = '4'`;
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou branco;
- mesma `NUM_UC_UCI`;
- mesmo protocolo de justificativa da UC (`TIPO_PROTOC_JUSTIF_UCI`);
- início e fim válidos em `DTHR_INICIO_INTRP_UC` e `DATA_HORA_FIM_INTRP`.

## Critério temporal

Para cada Registro B, a ferramenta procura Registro A quando:

- `A.NUM_UC_UCI = B.NUM_UC_UCI`;
- `A.TIPO_PROTOC_JUSTIF_UCI = B.TIPO_PROTOC_JUSTIF_UCI`;
- `A.DTHR_INICIO_INTRP_UC < B.DTHR_INICIO_INTRP_UC`;
- `A.DATA_HORA_FIM_INTRP > B.DTHR_INICIO_INTRP_UC`;
- `A.DATA_HORA_FIM_INTRP < B.DATA_HORA_FIM_INTRP`.

Ou seja: A cruza parcialmente o início de B, mas B ainda continua depois de A.

## Seleção do registro anterior

Se houver mais de um Registro A candidato, será escolhido:

1. o que tiver o maior `DATA_HORA_FIM_INTRP`;
2. em empate, o menor `DTHR_INICIO_INTRP_UC`;
3. em novo empate, o menor `NUM_SEQ_INTRP`.

## Resultado da análise

Arquivo materializado:

```text
data/mart/apuracao/analise_sobreposicao_uc_fase2_APURACAO_[anomes].parquet
data/mart/apuracao/analise_sobreposicao_uc_fase2_APURACAO_ATUAL.parquet
```

Principais campos:

- `chave_registro`;
- `num_intrp_uci_alvo`;
- `num_seq_intrp_alvo`;
- `num_uc_uci`;
- `protocolo_uc`;
- `inicio_original`;
- `inicio_sugerido`;
- `num_seq_intrp_origem`;
- `minutos_interseccao`;
- `campo_sugerido = DTHR_INICIO_INTRP_UC`;
- `campo_manobra_sugerido = NUM_INTRP_INIC_MANOBRA_UCI`;
- `acao_sugerida = AJUSTAR_INICIO_MANOBRA_UC`.

## Implantação governada

Ao implantar:

- cria backup do parquet de apuração;
- altera `DTHR_INICIO_INTRP_UC` no registro alvo;
- popula `NUM_INTRP_INIC_MANOBRA_UCI` com o `NUM_SEQ_INTRP` da interrupção anterior;
- registra log nominal de implantação;
- atualiza `agrupamento_oms_APURACAO_ATUAL.parquet`;
- recalcula pendências, tratamento massivo, indicadores e ressarcimento.

Logs:

```text
data/logs/log_implantacao_sobreposicao_uc_fase2_[anomes].parquet
data/logs/log_implantacao_sobreposicao_uc_fase2_ATUAL.parquet
```

## Comandos

Materializar análise:

```bash
python -m backend.scripts.materializar_sobreposicao_uc_fase2 --anomes 202605
```

Implantar ajustes:

```bash
python -m backend.scripts.implantar_sobreposicao_uc_fase2 --anomes 202605 --usuario admin --perfil admin
```

Implantar sem recalcular dependências:

```bash
python -m backend.scripts.implantar_sobreposicao_uc_fase2 --anomes 202605 --usuario admin --perfil admin --sem-recalculo
```

## Endpoints

- `POST /apuracao/analises/sobreposicao-uc-fase2/materializar/{anomes}`
- `GET /apuracao/analises/sobreposicao-uc-fase2?anomes=202605&limit=100&offset=0`
- `POST /apuracao/analises/sobreposicao-uc-fase2/implantar/{anomes}`

## Observação importante

Esta fase não classifica registros com motivo `91`. Ela corrige o início parcial da interrupção da UC e mantém rastreabilidade de manobra.

A classificação com `NUM_MOTIVO_TRAT_DIF_UCI = 91` permanece no módulo de sobreposição UC Fase 1, usado para registros contidos/excluídos.
