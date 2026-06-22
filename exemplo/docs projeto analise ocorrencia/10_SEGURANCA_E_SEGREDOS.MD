# Seguranca e Segredos

## Princípios
- Menor privilegio
- Segregacao de responsabilidades
- Rastreabilidade de acesso
- Nao exposicao de segredo em codigo

## Credenciais
- Nunca versionar credenciais reais.
- Usar `.env` local (fora de compartilhamento publico).
- Preferir cofre corporativo para producao.

## Autenticacao atual
- Login local baseado em `config/usuarios.yml`.
- Senha armazenada em `senha_hash` (SHA-256).
- Eventos de login/logout registrados em `logs/auth_sessions.jsonl`.

## Autorizacao
- Modelo por funcionalidade em `config/perfis.yml`.
- Paginas validam permissao via `require_feature(...)`.

## Controles recomendados para evolucao
- Integracao SSO (Entra ID/LDAP).
- Politica de expiracao e complexidade de senha.
- Trava por tentativas invalidas.
- Auditoria de alteracoes administrativas em storage imutavel.

## Dados e exportacao
- Exportacoes devem ser usadas conforme perfil e necessidade operacional.
- Evitar compartilhamento externo de datasets com dados sensiveis.
- Padronizar mascaramento em campos pessoais quando aplicavel.
