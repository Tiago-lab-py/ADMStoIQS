# Frontend — governança, login e navegação definitiva

## Objetivo

Consolidar o frontend do ADMStoIQS em uma experiência única, governada e segura para:

- acesso autenticado;
- navegação por perfil;
- visão inicial executiva para todos os usuários;
- trilha operacional controlada;
- administração de usuários e perfis;
- módulos futuros visíveis, mas bloqueados como `em desenvolvimento`.

O objetivo principal é evitar mudanças fragmentadas no React e preservar o que já está funcionando.

## Página inicial

A página inicial do sistema deve ser:

```text
http://127.0.0.1:5173/gestor.html
```

Essa página passa a ser o portal inicial para todos os perfis.

### Comportamento esperado

Ao acessar qualquer rota do frontend:

- se não houver sessão válida, exibir tela de login;
- após login bem-sucedido, redirecionar para `gestor.html`;
- o portal gestor deve permitir navegação para a tela operacional:

```text
http://127.0.0.1:5173/operacional.html
```

### Sugestão

Manter `gestor.html` como **Portal Executivo** e `operacional.html` como **Área Técnica/Operacional**.

Isso deixa claro para o usuário:

- onde ele enxerga impacto;
- onde ele executa rotinas;
- onde ele aprova decisões;
- onde ele apenas consulta.

## Perfis de acesso

Perfis oficiais:

| Perfil | Descrição | Acessos |
|---|---|---|
| `admin` | Administrador do sistema | usuários, perfis, reset, aprovação de cadastro, todas as telas |
| `gestor` | Gestor da apuração | dashboard executivo, indicadores, ressarcimento, filas, aprovação |
| `analista` | Analista operacional | ETL, filas de correção, análises e propostas de ajuste |

### Sugestão de nomenclatura

Evitar `usuario` como perfil final. Usar:

- `admin`;
- `gestor`;
- `analista`.

Se necessário, manter `usuario` apenas como compatibilidade interna temporária.

## Login

Todas as telas devem exigir login.

### Campos

- e-mail;
- senha.

### Fluxo

1. Usuário informa e-mail e senha.
2. Backend valida credenciais.
3. Frontend recebe token.
4. Frontend carrega perfil.
5. Frontend direciona para `gestor.html`.

## Cadastro de usuário

O cadastro deve ser solicitado pelo próprio usuário, mas não deve liberar acesso automaticamente.

### Fluxo de solicitação

1. Usuário acessa tela de login.
2. Clica em `Solicitar cadastro`.
3. Informa:
   - nome;
   - e-mail corporativo;
   - justificativa de acesso;
   - área/equipe;
   - perfil solicitado.
4. Registro é salvo com status:

```text
pendente_aprovacao
```

5. Um admin aprova ou rejeita.

### Senha inicial

Quando aprovado, o usuário recebe senha inicial:

```text
inicio123
```

Ao primeiro login, deve ser obrigado a trocar a senha.

## Primeiro acesso

No primeiro login:

1. usuário autentica com `inicio123`;
2. sistema detecta `troca_senha_obrigatoria = true`;
3. abre tela de troca de senha;
4. após troca, abre segunda autenticação com código numérico de 4 dígitos;
5. valida o código;
6. registra evento de primeiro acesso;
7. libera navegação.

## Segunda autenticação por código de 4 dígitos

### Objetivo

Registrar uma confirmação adicional em ações sensíveis e no primeiro acesso.

### Código

- numérico;
- 4 dígitos;
- validade curta;
- uso único.

### Sugestão

Para MVP local, gerar e exibir o código na própria tela apenas em ambiente de desenvolvimento.

Para versão produtiva, enviar por e-mail corporativo.

## Parquet de usuários

Criar armazenamento local governado em parquet.

Diretório sugerido:

```text
data/security/
```

Arquivos:

```text
data/security/usuarios.parquet
data/security/solicitacoes_usuarios.parquet
data/security/log_autenticacao.parquet
data/security/log_eventos_usuario.parquet
```

## Estrutura de `usuarios.parquet`

Campos sugeridos:

| Campo | Descrição |
|---|---|
| `id_usuario` | UUID |
| `email` | login principal |
| `nome` | nome completo |
| `perfil` | `admin`, `gestor`, `analista` |
| `senha_hash` | senha criptografada |
| `salt` | salt da senha, se aplicável |
| `status` | `ativo`, `bloqueado`, `pendente_aprovacao`, `rejeitado` |
| `troca_senha_obrigatoria` | boolean |
| `mfa_obrigatorio` | boolean |
| `criado_em` | timestamp |
| `criado_por` | admin responsável |
| `aprovado_em` | timestamp |
| `aprovado_por` | admin responsável |
| `ultimo_login_em` | timestamp |
| `tentativas_invalidas` | inteiro |

## Criptografia de senha

Não salvar senha em texto puro.

### Recomendação

Usar hash seguro com:

- `bcrypt`; ou
- `argon2`.

### Sugestão para o projeto

Usar `bcrypt` pela simplicidade de implantação local.

Adicionar dependência apenas quando a sprint de backend de usuários for implementada.

## Log de autenticação

Arquivo:

```text
data/security/log_autenticacao.parquet
```

Campos:

| Campo | Descrição |
|---|---|
| `id_evento` | UUID |
| `email` | usuário |
| `evento` | `login_ok`, `login_erro`, `logout`, `troca_senha`, `mfa_ok`, `mfa_erro` |
| `ip` | IP de origem |
| `pc` | nome do computador, quando informado |
| `user_agent` | navegador |
| `criado_em` | timestamp |
| `detalhe` | mensagem técnica |

## Administração

A aba `Administração` deve permitir:

- listar usuários;
- aprovar cadastro;
- rejeitar cadastro;
- criar usuário manualmente;
- alterar perfil;
- bloquear usuário;
- desbloquear usuário;
- resetar senha para `inicio123`;
- exigir troca de senha no próximo login;
- consultar logs de autenticação.

## Navegação

### Portal gestor

Arquivo:

```text
frontend/src/GestorPortalApp.tsx
```

Deve ser a experiência inicial.

Abas sugeridas:

- `Dashboard executivo`;
- `ETL operacional`;
- `Produto IQS`;
- `Indicadores`;
- `Sobreposição`;
- `Filas de correção`;
- `Fontes IQS`;
- `Governança`;
- `Administração`.

### Operacional

Arquivo:

```text
frontend/src/App.tsx
```

Deve ser acessível por botão/link a partir do portal gestor.

Uso:

- execução de ETL;
- análise técnica;
- filas operacionais;
- implantação de regras.

## Ajuste das abas de sobreposição

Atualmente existem abas separadas:

- `Sobreposição interrupção`;
- `Sobreposição UC`.

Nova proposta:

```text
Sobreposição
```

Dentro da aba `Sobreposição`, criar subtabs:

- `Interrupção/equipamento`;
- `UC — motivo 91`;
- `UC — Fase 2 interseção`;

### Vantagem

Reduz ruído no menu lateral e organiza as regras por domínio.

## Módulos em desenvolvimento

Os módulos ainda não finalizados devem aparecer no menu, mas bloqueados com flag:

```text
em_desenvolvimento = true
```

Módulos:

- alteração de causa/componente;
- implantação de janela ISE;
- implantação de dia crítico;
- simulação de impacto regulatório avançada.

### Comportamento visual

Quando usuário clicar:

- mostrar card explicativo;
- exibir status `Em desenvolvimento`;
- não chamar endpoint inexistente;
- não gerar erro no console.

## Controle de autorização por perfil

### Admin

Pode:

- acessar todas as telas;
- aprovar usuários;
- alterar perfis;
- resetar senhas;
- executar implantação;
- consultar logs.

### Gestor

Pode:

- acessar portal executivo;
- ver indicadores;
- ver ressarcimento;
- aprovar decisões;
- abrir tela operacional em modo consulta ou aprovação.

### Analista

Pode:

- executar ETL;
- consultar filas;
- propor ajustes;
- registrar justificativas;
- não pode aprovar cadastro de usuário.

## Boas práticas de implementação

1. Não remover telas antigas imediatamente.
2. Criar camada de autenticação reutilizável.
3. Criar componente comum de layout.
4. Migrar abas aos poucos.
5. Manter compatibilidade com endpoints atuais.
6. Evitar alterar regras de negócio junto com layout.
7. Cada sprint deve alterar uma camada por vez.

## Sugestões

### 1. Criar shell único do frontend

Criar um componente base:

```text
AppShell
```

Responsável por:

- menu lateral;
- usuário logado;
- botão de sair;
- controle de perfil;
- mensagens de erro/sucesso;
- layout visual.

### 2. Separar páginas por domínio

Estrutura sugerida:

```text
frontend/src/pages/
  LoginPage.tsx
  GestorPage.tsx
  OperacionalPage.tsx
  AdminUsuariosPage.tsx
  SobreposicaoPage.tsx
```

### 3. Criar serviço de auth no frontend

```text
frontend/src/auth.ts
```

Responsável por:

- token;
- usuário atual;
- login;
- logout;
- checagem de perfil.

### 4. Não quebrar o código atual

Manter `gestor.html` e `operacional.html`, mas compartilhar componentes internos.

Assim a implantação é progressiva e reversível.

## Critério de aceite

- Todo acesso exige login.
- `gestor.html` é a página inicial.
- Existe navegação clara para `operacional.html`.
- Admin consegue aprovar cadastro de usuário.
- Senha inicial é `inicio123`.
- Primeiro login exige troca de senha.
- Segundo fator de 4 dígitos registra evento.
- Senha é salva criptografada.
- Logs de autenticação são gravados em parquet.
- Abas de sobreposição ficam agrupadas em `Sobreposição`.
- Módulos incompletos aparecem como `Em desenvolvimento`, sem erro.
