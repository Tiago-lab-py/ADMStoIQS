# Sprint 3 — Frontend React

## Objetivo

Criar uma interface React autenticada para consulta dos Parquets processados, visualização de amostra, solicitação de alterações e geração do CSV oficial.

Nesta fase, a governança de alteração passa a ser obrigatória. Toda ação operacional relevante deve estar associada a um usuário autenticado e a um perfil de acesso.

## Escopo

- Tela de login.
- Controle de sessão.
- Tela inicial com competências disponíveis.
- Tela de consulta dos dados processados.
- Tela ou aba de amostra das 100 maiores durações por `PID_INTRP_CONJTO_PIN`.
- Telas ou filas de tratamento operacional.
- Ação para solicitar alteração.
- Ação para gerar e baixar CSV.

As consultas do frontend devem consumir a API, que passa a usar preferencialmente `data/mart/OMS_union.parquet` quando disponível. Assim, as telas exibem colunas de verificação como `duracao`, `erro_duracao` e `duracao_longa`.

O seletor de competência deve ser alimentado pelo mart ativo (`OMS_union_corrigido.parquet` quando válido, senão `OMS_union.parquet`) e não pelos arquivos mensais em `data/processed/`.

## Runtime Local

O frontend deve utilizar o Node.js disponível no próprio projeto:

```text
tools/nodejs
```

Os comandos de desenvolvimento e build devem ser executados a partir da pasta `frontend`, usando preferencialmente:

```text
install.cmd
dev.cmd
build.cmd
```

Esses scripts adicionam `tools/nodejs` ao `PATH` antes de executar `npm`, evitando falhas de dependências que chamam `node` diretamente durante o install.

## Perfis de Acesso

Perfis iniciais:

| Perfil | Permissões |
|---|---|
| `admin` | Consulta dados, exporta CSV, registra alteração aplicada e visualiza painel administrativo |
| `gestor` | Consulta dados, exporta CSV e registra alteração aplicada |
| `usuario` | Consulta dados e solicita alteração |

Credenciais locais de desenvolvimento:

| Usuário | Senha | Perfil |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `gestor` | `gestor123` | `gestor` |
| `usuario` | `usuario123` | `usuario` |

Estas credenciais são apenas para desenvolvimento local. Em produção, devem ser substituídas por integração corporativa ou mecanismo seguro equivalente.

## Telas

### Login

Campos:

- Usuário.
- Senha.

Comportamentos:

- Autenticar no backend.
- Guardar token de sessão de forma segura.
- Bloquear acesso às telas internas sem autenticação.
- Carregar perfil do usuário autenticado.

### Competências

Funcionalidades:

- Listar meses processados.
- Exibir caminho/nome do Parquet.
- Exibir data de processamento, quando disponível.
- Permitir selecionar uma competência.

### Consulta

Funcionalidades:

- Consultar dados paginados.
- Filtrar por campos principais.
- Visualizar detalhes de um registro.
- Solicitar alteração de campos permitidos.

### Amostra

Funcionalidades:

- Exibir os 100 maiores `CHI` por `PID_INTRP_CONJTO_PIN`.
- Permitir download da amostra, se aprovado.
- Exibir mensagem funcional quando `CHI` não estiver disponível.

### Exportação

Funcionalidades:

- Gerar CSV oficial.
- Mostrar status da geração.
- Permitir download do arquivo final.
- Bloquear exportação para perfil `usuario`.
- Permitir exportação por regional.
- Permitir exportação de todas as regionais da competência.

### Governança de Alteração

Funcionalidades:

- Registrar solicitação de alteração vinculada ao usuário autenticado.
- Registrar competência, chave do registro, campo, valor anterior, valor novo e justificativa.
- Enviar IP e user-agent pelo backend para `log_alteracoes.parquet`.
- Para perfil `usuario`, registrar alteração com status `solicitado`.
- Para perfis `gestor` e `admin`, registrar alteração com status `aplicado` nesta fase inicial.

Campos mínimos:

- `anomes`
- `chave_registro`
- `campo`
- `valor_anterior`
- `valor_novo`
- `justificativa`

### Filas de Tratamento

As filas de tratamento devem ser carregadas a partir do `OMS_union.parquet`.

Filas iniciais:

| Página/Fila | Regra |
|---|---|
| Horário negativo | `erro_duracao = true`; se diferença negativa for até 3 horas, sugerir `DATA_HORA_FIM_INTRP + 3 horas` |
| Sobreposição interrupção | Mesmo `ALIM_INTRP_PIN` e `NUM_OPER_CHV_INTRP`, avaliando `DATA_HORA_INIC_INTRP` e `DATA_HORA_FIM_INTRP` |
| Sobreposição UC | Mesma `NUM_UC_UCI` e `NUM_POSTO_UCI`, avaliando `DTHR_INICIO_INTRP_UC` e `DATA_HORA_FIM_INTRP` |
| Sem causa/componente | Registros sem `COD_CAUSA_INTRP` ou `COD_COMP_INTRP` |

Regras de sugestão:

- Em sobreposição parcial, manter como primeira interrupção a de menor `NUM_SEQ_INTRP`.
- Para segunda interrupção longa (`duracao_longa = true`), sugerir deslocar o início para o fim da primeira.
- Quando houver deslocamento, sugerir preencher `NUM_INTRP_INIC_MANOBRA_UCI` com o número da primeira interrupção.
- Para segunda interrupção curta (`duracao_longa = false`), sugerir exclusão/tratamento diferenciado com `NUM_MOTIVO_TRAT_DIF_UCI = 91`.
- Para causa/componente ausentes, exibir registro para revisão e sugestão futura baseada em descrição, tipo de equipamento e histórico.

## Backend de Suporte

Endpoints criados para suporte ao frontend:

| Método | Rota | Permissão |
|---|---|---|
| `POST` | `/auth/login` | Público |
| `GET` | `/auth/me` | Autenticado |
| `GET` | `/competencias` | Autenticado |
| `GET` | `/competencias/{anomes}/dados` | Autenticado |
| `GET` | `/competencias/{anomes}/amostra` | Autenticado |
| `POST` | `/competencias/{anomes}/exportar-csv` | `admin`, `gestor` |
| `POST` | `/competencias/{anomes}/exportar-csv-regionais` | `admin`, `gestor` |
| `GET` | `/exports/{arquivo}` | Autenticado |
| `POST` | `/alteracoes` | Autenticado |
| `GET` | `/tratamentos/horario-negativo` | Autenticado |
| `GET` | `/tratamentos/sobreposicao-interrupcao` | Autenticado |
| `GET` | `/tratamentos/sobreposicao-uc` | Autenticado |
| `GET` | `/tratamentos/sem-causa-componente` | Autenticado |
| `POST` | `/mart/oms-corrigido` | `admin`, `gestor` |

## Implementação

Arquivos frontend criados:

- `frontend/package.json`: scripts e dependências React/Vite.
- `frontend/index.html`: entrada da aplicação.
- `frontend/vite.config.ts`: configuração Vite.
- `frontend/tsconfig.json`: configuração TypeScript.
- `frontend/src/main.tsx`: bootstrap React.
- `frontend/src/App.tsx`: trilha de correções com sidebar, dashboard, filas, revisão, exportação e administração.
- `frontend/src/api.ts`: cliente HTTP para backend.
- `frontend/src/auth.tsx`: contexto de autenticação.
- `frontend/src/styles.css`: estilos da interface.

Arquivos backend de suporte:

- `backend/app/core/auth.py`: autenticação local, token e dependências de permissão.
- `backend/app/services/alteracao_service.py`: gravação auditada de alterações.
- `backend/app/services/tratamento_service.py`: filas de tratamento e sugestões sobre o `OMS_union.parquet`.
- `backend/app/api/routes.py`: rotas protegidas, login e solicitação de alteração.
- `backend/app/schemas/api_models.py`: modelos de autenticação e alteração.

## Comandos

Instalar dependências do frontend, a partir da pasta `frontend`:

```text
install.cmd
```

Subir frontend:

```text
dev.cmd
```

Subir backend, a partir da raiz do projeto:

```text
python -m backend.scripts.run_api
```

URLs:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
```

## Boas Práticas

- Não expor caminho físico completo da rede para usuários sem necessidade.
- Não permitir exportação sem autenticação.
- Não permitir alteração sem justificativa.
- Exibir avisos claros para erros funcionais.
- Evitar carregar grandes volumes de dados no navegador.

## Critérios de Aceite

- Usuário autentica antes de acessar dados.
- Usuário visualiza competências disponíveis.
- Usuário consulta amostra das maiores durações.
- Usuário solicita geração do CSV.
- Usuário baixa CSV gerado.
- Ações relevantes enviam dados suficientes para auditoria.
- Perfil `usuario` não consegue exportar CSV.
- Perfis `gestor` e `admin` conseguem exportar CSV.
- Solicitações de alteração são registradas em `log_alteracoes.parquet`.
- Usuário consulta filas de horário negativo, sobreposição e causa/componente.
# Sprint 3 - Frontend React e Trilha Governada

## Objetivo

Construir o frontend React para operar a trilha de correções OMS sobre o mart único:

```text
data/mart/agrupamento_oms_UNION_corrigido.parquet
```

O frontend deve tratar `UNION` como competência lógica única, evitando apresentar o mart como se fosse um arquivo mensal.

## Estado Atual

- API FastAPI disponível em `http://127.0.0.1:8000`.
- Frontend Vite disponível em `http://127.0.0.1:5173`.
- Login local funcional:
  - `admin/admin123`
  - `gestor/gestor123`
  - `usuario/usuario123`
- Dropdown do frontend aponta para `UNION`.
- Dashboard consulta o mart e carrega registros.

## Rotas Preferenciais

O frontend deve usar:

- `GET /competencias`
- `GET /mart/dados`
- `GET /mart/amostra`
- `POST /mart/exportar-csv`
- `POST /mart/exportar-csv-regionais`
- `POST /mart/oms-corrigido`

Rotas com `{anomes}` ficam apenas para compatibilidade.

## Páginas

### Dashboard

- Apresentar fonte ativa do mart.
- Exibir registros carregados.
- Exibir contadores por fila.
- Exibir ações rápidas.

### Horário Negativo

- Listar registros com `erro_duracao = true`.
- Mostrar sugestão de ajuste quando aplicável.
- Permitir aplicar, rejeitar, ignorar ou manter pendente.

### Sobreposição Interrupção

- Listar sobreposições por alimentador e chave.
- Apresentar interrupção principal e interrupção ajustável.
- Sugerir deslocamento ou tratamento diferenciado.

### Sobreposição UC

- Listar conflitos por UC e posto.
- Apresentar intervalo conflitante.
- Permitir decisão auditável.

### Causa/Componente

- Listar registros sem causa ou componente.
- Apresentar sugestão quando houver base histórica.
- Exigir decisão explícita.

### Revisão Final

- Mostrar pendentes, validados, rejeitados e aplicados.
- Gerar `agrupamento_oms_UNION_corrigido.parquet`.

### Exportação

- Exportar CSV por regional.
- Exportar todas as regionais.
- Usar apenas a base corrigida.
- Excluir registros rejeitados.

### Administração

- Cadastro de usuários.
- Perfil `admin`, `gestor`, `usuario`.
- Reset de senha no primeiro acesso.
- Auditoria de acesso e alteração.

## Governança

Cada alteração deve registrar:

- usuário;
- perfil;
- IP;
- estação/PC quando disponível;
- data/hora;
- chave do registro;
- campo;
- valor original;
- valor novo;
- justificativa;
- status.

## Critérios de Aceite

- Login funcional.
- `UNION` apresentado como única fonte lógica.
- Dashboard carrega registros do mart corrigido.
- Filas de tratamento consultam o mart.
- Decisões geram log.
- Exportação respeita `REGIONAL_ORIGEM`.
- Registros rejeitados não entram no CSV final.
