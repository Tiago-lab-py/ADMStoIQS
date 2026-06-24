# Sprint 12 — Sobreposição UC Fase 2

## Meta

Entregar análise e implantação governada para interseções parciais de horário na mesma UC.

## Entregáveis

- Serviço `SobreposicaoUcFase2Service`.
- Script de materialização.
- Script de implantação.
- Endpoints REST para análise, consulta e implantação.
- Documentação técnica da regra.
- Integração com recálculo de pendências, tratamento massivo, indicadores e ressarcimento.

## Regra de negócio

Quando duas interrupções da mesma UC e mesmo protocolo se sobrepõem parcialmente, o segundo registro deve iniciar no fim do primeiro registro.

Também deve ser preenchido:

```text
NUM_INTRP_INIC_MANOBRA_UCI = NUM_SEQ_INTRP do registro anterior
```

## Filtros

- `ESTADO_INTRP = '4'`
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou branco
- mesma `NUM_UC_UCI`
- mesmo `TIPO_PROTOC_JUSTIF_UCI`

## Checklist técnico

- [x] Criar documentação da regra.
- [x] Criar serviço de análise.
- [x] Criar script de materialização.
- [x] Criar script de implantação.
- [x] Criar log de implantação.
- [x] Criar endpoints.
- [x] Integrar cards e ações na página operacional.
- [ ] Validar com `python -m backend.scripts.materializar_sobreposicao_uc_fase2 --anomes 202605`.
- [ ] Validar implantação em base de teste ou backup.

## Critérios de aceite

- A análise não altera dados.
- A implantação cria backup antes de gravar.
- A implantação registra usuário, perfil, PC, IP e justificativa.
- A implantação recalcula marts dependentes.
- O usuário consegue explicar por que o início foi ajustado e de qual interrupção veio a manobra inicial.
