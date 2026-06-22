# Sprint 0 — Contratos, Governança e Desenho Técnico

## Objetivo

Fechar os contratos mínimos do projeto antes da implementação: estrutura de pastas, formatos de entrada/saída, campos obrigatórios, logs, autenticação e regras de auditoria.

## Entregas

- Definição da estrutura de diretórios do backend, frontend e dados.
- Definição do esquema dos logs `log_leitura_csv.parquet` e `log_alteracoes.parquet`.
- Definição do cabeçalho oficial do CSV exportado.
- Confirmação das colunas críticas dos CSVs de origem.
- Definição do mecanismo de login e identificação nominal do usuário.

## Decisões Técnicas

- O backend será implementado em Python.
- O processamento analítico será feito com DuckDB.
- Os dados finais serão salvos em Parquet.
- A área `raw_temp` será usada apenas durante processamento e apagada ao final.
- A deduplicação inicial será por UC, usando a chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

## Pontos de Atenção

- Confirmar se a coluna `CHI` existe nos CSVs de origem, pois será usada para amostra.
- Confirmar se `PID_INTRP_CONJTO_PIN` existe e está preenchido nos arquivos processados.
- Confirmar encoding e separador real dos CSVs de origem.
- Confirmar se todos os campos do cabeçalho de exportação existem no dado processado.

## Governança

Toda alteração solicitada pelo frontend deve registrar:

- Usuário autenticado.
- Data e hora da ação.
- IP de origem.
- User-agent.
- Ação executada.
- Competência afetada.
- Identificadores dos registros afetados.
- Valor anterior e valor novo, quando aplicável.

O nome do computador deve ser registrado quando disponível por autenticação corporativa, proxy, header confiável ou integração local. Navegadores comuns não expõem o hostname do computador de forma confiável por padrão.

## Critérios de Aceite

- Estrutura de pastas aprovada.
- Campos dos logs documentados.
- Cabeçalho CSV oficial documentado.
- Estratégia de autenticação definida.
- Critério inicial de deduplicação definido.

## Implementação

Arquivos criados para codificar os contratos desta sprint:

- `backend/app/core/contracts.py`: caminhos oficiais, competência inicial, padrão amplo dos CSVs, nomes de artefatos e chave de deduplicação.
- `backend/app/schemas/log_leitura_csv.py`: contrato do `log_leitura_csv.parquet`.
- `backend/app/schemas/log_alteracoes.py`: contrato do `log_alteracoes.parquet`.
- `backend/app/schemas/audit_context.py`: contexto mínimo de auditoria para usuário, IP, hostname e user-agent.
- `backend/app/schemas/export_layout.py`: cabeçalho oficial e separador do CSV de saída.
- `backend/scripts/validate_contracts.py`: validação leve dos contratos configurados.
- `backend/requirements.txt`: dependências iniciais previstas para backend, DuckDB, Parquet e API.

## Validação Manual

Quando o ambiente Python estiver configurado, executar:

```text
python -m backend.scripts.validate_contracts
```

O comando valida:

- Formato da competência inicial.
- Criação dos diretórios locais de dados.
- Duplicidade no layout oficial de exportação.
- Presença da chave de deduplicação no layout final.
- Quantidade de campos dos contratos de log e exportação.
