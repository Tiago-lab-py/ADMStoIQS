# Sprint 13 — Frontend governado, login e administração de usuários

## Objetivo

Transformar o frontend em uma experiência definitiva e governada, mantendo estabilidade do código atual.

Prioridade:

1. `gestor.html` como tela inicial;
2. login obrigatório;
3. navegação para `operacional.html`;
4. administração de usuários;
5. agrupamento das abas de sobreposição;
6. módulos futuros visíveis com status `Em desenvolvimento`.

## Escopo

### Frontend

- Criar fluxo único de autenticação.
- Proteger `gestor.html`.
- Proteger `operacional.html`.
- Transformar `gestor.html` na página inicial.
- Adicionar botão/link para tela operacional.
- Agrupar:
  - `Sobreposição interrupção`;
  - `Sobreposição UC`;
  - `Sobreposição UC Fase 2`;
  em uma aba única chamada `Sobreposição`.
- Exibir módulos ainda não prontos com flag `Em desenvolvimento`.

### Backend

- Criar serviço de usuários local com parquet.
- Criar cadastro por e-mail.
- Criar aprovação de cadastro por admin.
- Criar senha inicial `inicio123`.
- Criar troca obrigatória de senha no primeiro acesso.
- Criar segunda autenticação por código de 4 dígitos.
- Registrar logs de autenticação.

## Fora do escopo desta sprint

Não implementar regra de negócio nova para:

- alteração de causa/componente;
- janela ISE;
- dia crítico;
- cálculo regulatório novo;
- novas regras de tratamento OMS.

Esses módulos devem apenas aparecer como `Em desenvolvimento`.

## Plano de implantação seguro

### Etapa 1 — Documentação e contratos

- [x] Documentar visão de login, navegação e perfis.
- [x] Definir estrutura dos parquets de segurança.
- [x] Definir critérios de aceite.

### Etapa 2 — Backend de usuários

- [ ] Criar `data/security/.gitkeep`.
- [ ] Criar serviço `UserSecurityService`.
- [ ] Criar `usuarios.parquet`.
- [ ] Criar `solicitacoes_usuarios.parquet`.
- [ ] Criar `log_autenticacao.parquet`.
- [ ] Implementar hash de senha.
- [ ] Implementar usuário admin inicial se arquivo não existir.
- [ ] Implementar aprovação/rejeição de cadastro.
- [ ] Implementar reset de senha.
- [ ] Implementar troca obrigatória no primeiro acesso.
- [ ] Implementar código de 4 dígitos para segunda autenticação.

### Etapa 3 — API de autenticação

- [ ] Ajustar `/auth/login` para e-mail e senha.
- [ ] Ajustar `/auth/me`.
- [ ] Criar `/auth/solicitar-cadastro`.
- [ ] Criar `/auth/trocar-senha`.
- [ ] Criar `/auth/mfa/validar`.
- [ ] Criar `/admin/usuarios`.
- [ ] Criar `/admin/usuarios/{id}/aprovar`.
- [ ] Criar `/admin/usuarios/{id}/rejeitar`.
- [ ] Criar `/admin/usuarios/{id}/resetar-senha`.
- [ ] Criar `/admin/usuarios/{id}/perfil`.

### Etapa 4 — Frontend de login

- [ ] Ajustar tela de login para e-mail.
- [ ] Adicionar link `Solicitar cadastro`.
- [ ] Criar modal/tela de solicitação de cadastro.
- [ ] Criar tela de troca de senha.
- [ ] Criar tela de código de 4 dígitos.
- [ ] Gravar token após autenticação completa.
- [ ] Redirecionar para `gestor.html`.

### Etapa 5 — Portal gestor como inicial

- [ ] Criar redirect de `/` para `gestor.html`.
- [ ] Garantir que `gestor.html` exige login.
- [ ] Adicionar botão `Abrir operacional`.
- [ ] Validar que usuários sem sessão voltam para login.

### Etapa 6 — Tela operacional

- [ ] Garantir que `operacional.html` exige login.
- [ ] Exibir usuário e perfil no layout.
- [ ] Respeitar permissões por perfil.
- [ ] Bloquear implantação para perfil sem permissão.

### Etapa 7 — Aba Sobreposição

- [ ] Criar aba única `Sobreposição`.
- [ ] Criar subtab `Interrupção/equipamento`.
- [ ] Criar subtab `UC — motivo 91`.
- [ ] Criar subtab `UC — Fase 2 interseção`.
- [ ] Remover duplicidade visual no menu lateral.
- [ ] Manter endpoints atuais sem alteração.

### Etapa 8 — Módulos em desenvolvimento

- [ ] Exibir `Causa/componente` como `Em desenvolvimento`.
- [ ] Exibir `Janela ISE` como `Em desenvolvimento`.
- [ ] Exibir `Dia crítico` como `Em desenvolvimento`.
- [ ] Bloquear chamadas de API inexistentes.
- [ ] Registrar mensagem amigável em tela.

### Etapa 9 — Validação

- [ ] Login admin.
- [ ] Login gestor.
- [ ] Login analista.
- [ ] Solicitação de novo cadastro.
- [ ] Aprovação por admin.
- [ ] Primeiro login com `inicio123`.
- [ ] Troca obrigatória de senha.
- [ ] Validação de código 4 dígitos.
- [ ] Acesso ao portal gestor.
- [ ] Navegação para operacional.
- [ ] Bloqueio de ações por perfil.
- [ ] Logs gravados em parquet.

## Permissões propostas

| Ação | admin | gestor | analista |
|---|---:|---:|---:|
| Ver dashboard gestor | Sim | Sim | Sim |
| Abrir operacional | Sim | Sim | Sim |
| Executar ETL | Sim | Não | Sim |
| Materializar pendências | Sim | Não | Sim |
| Implantar tratamento massivo | Sim | Sim | Não |
| Aprovar decisão | Sim | Sim | Não |
| Solicitar ajuste | Sim | Sim | Sim |
| Administrar usuários | Sim | Não | Não |
| Resetar senha | Sim | Não | Não |

## Arquivos esperados

Backend:

```text
backend/app/services/user_security_service.py
backend/app/api/auth_routes.py
backend/app/api/admin_user_routes.py
```

Frontend:

```text
frontend/src/auth.ts
frontend/src/pages/LoginPage.tsx
frontend/src/pages/SolicitarCadastroPage.tsx
frontend/src/pages/TrocarSenhaPage.tsx
frontend/src/pages/AdminUsuariosPage.tsx
frontend/src/components/AppShell.tsx
frontend/src/components/FeatureFlagCard.tsx
frontend/src/components/SobreposicaoTabs.tsx
```

Dados:

```text
data/security/usuarios.parquet
data/security/solicitacoes_usuarios.parquet
data/security/log_autenticacao.parquet
data/security/log_eventos_usuario.parquet
```

## Riscos

### Risco 1 — quebrar login atual

Mitigação:

- manter compatibilidade temporária com `admin/admin123`;
- migrar para e-mail/senha em etapa controlada.

### Risco 2 — quebrar navegação atual

Mitigação:

- manter `gestor.html` e `operacional.html`;
- não trocar tudo para SPA única imediatamente.

### Risco 3 — senha salva incorretamente

Mitigação:

- nunca salvar senha pura;
- usar hash com `bcrypt`;
- validar criação do parquet em teste isolado.

### Risco 4 — módulos em desenvolvimento gerarem erro

Mitigação:

- feature flags no frontend;
- não chamar endpoints inexistentes.

## Critérios de aceite

- Login obrigatório em todas as telas.
- `gestor.html` é a tela inicial para todos.
- Existe botão claro para `operacional.html`.
- Aba `Sobreposição` agrupa os três tratamentos.
- Administração permite criar/aprovar usuário.
- Senha inicial aprovada é `inicio123`.
- Primeiro login obriga troca de senha.
- Segunda autenticação de 4 dígitos registra log.
- Senhas são criptografadas.
- Logs são gravados em parquet.
- Módulos futuros aparecem como `Em desenvolvimento`.
- Nenhuma regra OMS/indicador é alterada nesta sprint.

## Sugestão de ordem de implementação

1. Backend de usuários e parquet.
2. Login por e-mail mantendo compatibilidade.
3. Admin de usuários.
4. Redirect para `gestor.html`.
5. Navegação para `operacional.html`.
6. Agrupamento da aba `Sobreposição`.
7. Feature flags para módulos futuros.

Essa ordem reduz o risco de quebrar o fluxo operacional já usado no projeto.
