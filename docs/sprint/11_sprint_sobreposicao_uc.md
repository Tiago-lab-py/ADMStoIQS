# Sprint 11 — Sobreposição temporal por UC

## Meta

Entregar uma análise governada para classificar com motivo `91` registros de UC contidos em outra interrupção da mesma UC, com impacto em CHI, indicadores e ressarcimento.

## Escopo

1. Materializar análise de sobreposição por `NUM_UC_UCI`.
2. Exibir cards na tela operacional de sobreposição.
3. Implantar motivo `91` com backup e log nominal.
4. Rematerializar pendências, tratamento massivo, indicadores DEC/FEC/DIC/FIC/DMIC e ressarcimento.
5. Manter dashboard somente leitura.

## Critérios de aceite

- A análise usa apenas `ESTADO_INTRP = '4'`.
- A análise usa apenas `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou vazio.
- A análise exige mesmo `TIPO_PROTOC_JUSTIF_UCI`.
- A tela exibe quantidade a classificar e CHI estimado reduzido.
- A implantação popula `NUM_MOTIVO_TRAT_DIF_UCI = '91'`.
- A implantação gera backup e log nominal.
- Após implantação, os marts de pendências, tratamento, indicadores e ressarcimento são recalculados.

## Fora do escopo desta sprint

- Alteração manual de início/fim por UC.
- Sugestão automática de causa/componente.
- Exportação final IQS recalculada diretamente no mesmo botão.

