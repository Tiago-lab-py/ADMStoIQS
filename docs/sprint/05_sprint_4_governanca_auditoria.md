# Sprint 4 — Governança e Auditoria

## Objetivo

Garantir rastreabilidade nominal das ações realizadas no sistema, especialmente solicitações de alteração e geração de arquivos.

## Log de Alterações

Arquivo:

```text
data/logs/log_alteracoes.parquet
```

## Campos Mínimos

| Campo | Descrição |
|---|---|
| `id_alteracao` | Identificador único da alteração |
| `usuario` | Usuário autenticado |
| `nome_usuario` | Nome completo, quando disponível |
| `ip_origem` | IP capturado pelo backend |
| `hostname_origem` | Nome do computador, quando disponível por fonte confiável |
| `user_agent` | User-agent do navegador |
| `acao` | Tipo de ação executada |
| `anomes` | Competência afetada |
| `chave_registro` | Chave lógica do registro afetado |
| `campo` | Campo alterado |
| `valor_anterior` | Valor anterior |
| `valor_novo` | Valor novo |
| `justificativa` | Justificativa informada pelo usuário |
| `criado_em` | Data/hora do registro de auditoria |
| `status` | `solicitado`, `aprovado`, `rejeitado`, `aplicado` ou `erro` |

## Ações Auditáveis

- Login com sucesso.
- Falha de login.
- Consulta de competência.
- Geração de amostra.
- Solicitação de alteração.
- Aprovação ou rejeição de alteração, quando existir fluxo de aprovação.
- Geração de CSV.
- Download de CSV.

## Identificação de Usuário, PC e IP

O backend deve registrar de forma obrigatória:

- Usuário autenticado.
- IP de origem.
- User-agent.
- Data e hora.

O hostname do computador deve ser registrado quando houver mecanismo confiável disponível, como:

- Autenticação integrada Windows/AD.
- Proxy corporativo adicionando header confiável.
- Integração local controlada.
- Inventário corporativo associado ao usuário/IP.

Não se deve depender apenas do navegador para obter nome do computador, pois essa informação não é exposta de forma confiável por segurança.

## Alterações nos Dados

Nesta fase inicial, alterações devem ser registradas no log antes de alterar qualquer artefato final.

Regra recomendada:

1. Usuário solicita alteração.
2. Backend registra solicitação em `log_alteracoes.parquet`.
3. Alteração fica pendente ou aplicada conforme regra de negócio definida.
4. CSV gerado considera o estado aprovado/aplicado.

## Critérios de Aceite

- Toda alteração possui usuário nominal.
- Toda alteração possui IP e timestamp.
- Toda alteração registra campo, valor anterior e valor novo.
- Toda geração de CSV é auditável.
- O sistema não depende de informação insegura do navegador para identificar o PC.
# Sprint 4 - Governança, Validação e Auditoria

## Objetivo

Transformar `agrupamento_oms_UNION_corrigido.parquet` em uma base de trabalho governada, permitindo validar, rejeitar, ignorar ou aplicar correções com rastreabilidade nominal.

## Fonte

- Entrada: `data/mart/agrupamento_oms_UNION.parquet`
- Trabalho: `data/mart/agrupamento_oms_UNION_corrigido.parquet`
- Auditoria: `data/logs/log_alteracoes.parquet`

## Colunas de Governança

Adicionar ao parquet corrigido:

- `validado`: booleano.
- `status_validacao`: texto.
- `motivo_status`: texto.
- `usuario_validacao`: texto.
- `data_hora_validacao`: timestamp.

## Estados

- `pendente`
- `em_analise`
- `validado`
- `rejeitado`
- `ignorado`
- `aplicado`

## Regras

- Registro novo inicia como `validado = false` e `status_validacao = pendente`.
- Correção automática gera sugestão, não obrigação.
- Usuário pode deixar registro pendente para tratamento futuro.
- Registro rejeitado não deve ser exportado.
- Registro aplicado deve preservar log de alteração.

## Backend

Implementar endpoints:

- `POST /alteracoes`: solicitar alteração.
- `POST /alteracoes/{id}/aprovar`: aprovar alteração.
- `POST /alteracoes/{id}/rejeitar`: rejeitar alteração.
- `POST /registros/{chave}/validar`: validar registro sem alteração.
- `POST /registros/{chave}/rejeitar`: rejeitar registro.
- `POST /registros/{chave}/ignorar-regra`: ignorar sugestão automática.

## Frontend

Cada fila deve permitir:

- ver detalhe do registro;
- ver sugestão;
- aplicar sugestão;
- validar sem alterar;
- rejeitar registro;
- ignorar regra;
- registrar justificativa.

## Auditoria

Registrar sempre:

- usuário autenticado;
- perfil;
- IP;
- PC/host quando possível;
- timestamp;
- ação;
- chave;
- campo;
- valor original;
- valor novo;
- justificativa.

## Critérios de Aceite

- Parquet corrigido contém colunas de governança.
- Log de alteração registra decisões nominais.
- Rejeição remove registro da exportação.
- Validação sem alteração fica registrada.
- Usuário comum solicita; gestor/admin aprova ou aplica.

## Implementação Atual

Serviços e scripts:

- `backend/app/services/governance_service.py`
- `backend/app/services/oms_correcoes_service.py`
- `backend/scripts/gerar_oms_corrigido.py`

Endpoints adicionados:

- `GET /mart/resumo`
- `POST /registros/{chave}/validar`
- `POST /registros/{chave}/rejeitar`
- `POST /registros/{chave}/ignorar-regra`
- `POST /alteracoes/{id}/aprovar`
- `POST /alteracoes/{id}/rejeitar`

Comando para materializar o parquet corrigido após decisões:

```cmd
python -m backend.scripts.gerar_oms_corrigido
```

Exportação:

- A exportação usa o mart corrigido quando disponível.
- Registros com `status_validacao = rejeitado` não entram no CSV final.
- Frontend possui painel inicial de decisão com justificativa obrigatória.

## Fechamento do Dia

Concluído:

- Mart corrigido gerado com colunas de governança.
- Endpoints de decisão visíveis no Swagger.
- Frontend voltou a autenticar e consultar o mart.
- `UNION` consolidado como competência lógica.
- Exportação preparada para ignorar registros rejeitados.

Pendente para amanhã:

- Testar decisão real usando uma chave do mart.
- Regenerar o corrigido após decisão pela interface.
- Conferir materialização de `status_validacao`.
- Refinar layout das filas específicas.
- Adicionar contador pesado de sobreposições em rotina separada.

Checklist operacional:

- Ver `docs/05_checklist_amanha.md`.
