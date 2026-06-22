# Login e Senhas - Desenvolvimento Implementado

## Objetivo
Documentar a implementacao de autenticacao, controle de senha e fluxo de seguranca de primeiro acesso na aplicacao.

## Escopo implementado
- Login por e-mail e senha com hash.
- Controle de perfil e autorizacao por funcionalidade.
- Troca obrigatoria de senha no primeiro acesso.
- Confirmacao de troca com codigo de 4 digitos enviado por e-mail.
- Exibicao de contato dos administradores na tela de login.

## Arquivos envolvidos
- `biblioteca/auth.py`
- `biblioteca/email_utils.py`
- `config/usuarios.yml`
- `app/pages/8_Admin.py`
- `.env.example`

## Modelo atual de autenticacao
1. Usuario informa e-mail e senha.
2. Sistema compara hash da senha com `senha_hash` em `config/usuarios.yml`.
3. Se valido e usuario ativo, cria sessao (`auth_ok`, `auth_email`, `auth_perfil`, `auth_session_id`).
4. Se `trocar_senha_obrigatoria = true`, bloqueia navegacao e exige troca antes de continuar.

## Primeiro acesso com troca obrigatoria
### Fluxo
1. Usuario loga com credencial inicial.
2. Sistema informa obrigatoriedade de troca.
3. Usuario solicita codigo de 4 digitos.
4. Codigo e enviado para o e-mail cadastrado do proprio usuario.
5. Usuario informa codigo + nova senha + confirmacao.
6. Sistema valida:
   - codigo correto,
   - codigo nao expirado,
   - senha com tamanho minimo,
   - confirmacao igual.
7. Sistema salva nova senha (hash) e remove obrigatoriedade.

### Regras
- Codigo com 4 digitos.
- Validade do codigo: 10 minutos.
- Codigo associado ao e-mail logado na sessao.
- Troca nao conclui sem codigo valido.

## Envio de e-mail
### Modulo
`biblioteca/email_utils.py`

### Funcoes principais
- `obter_emails_admin(root_dir)`: lista admins/desenvolvedores ativos.
- `enviar_email(root_dir, destinatarios, assunto, corpo_texto, remetente=None)`: envio SMTP.

### Remetente
- Usa e-mail de administrador da ferramenta como remetente padrao.

### Logs
- Registro em `logs/email.log` com status de envio, erro e destinatarios.

## Administracao de usuarios (Admin)
- Ao criar usuario com senha, marca `trocar_senha_obrigatoria = true`.
- Ao resetar senha, marca `trocar_senha_obrigatoria = true`.
- Usuario somente normaliza acesso apos concluir troca com codigo.

## Configuracao SMTP
Variaveis previstas em `.env`:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_TLS`

Se SMTP nao estiver configurado, o sistema registra tentativa e informa falha de envio.

## Estado atual e recomendacoes
### Ja implementado
- Fluxo minimo seguro para primeiro acesso.
- Confirmacao por codigo por e-mail.
- Notificacao administrativa de troca concluida.

### Proximas melhorias sugeridas
- Limite de tentativas de codigo.
- Politica de complexidade de senha (maiuscula/minuscula/numero/simbolo).
- Expiracao periodica de senha.
- Integracao com SSO corporativo (Entra ID/LDAP).
- Auditoria administrativa imutavel para alteracoes de usuario/senha/perfil.

