# Decisoes Tecnicas

## Decisoes estruturais
1. ETL separado da interface
Motivo: evitar consultas pesadas no uso operacional.

2. Persistencia inicial em Parquet
Motivo: simplicidade, desempenho local e portabilidade.

3. SQL versionado em pasta dedicada
Motivo: rastreabilidade de extracao e manutencao por fonte.

4. Modo `sample` como padrao de desenvolvimento
Motivo: equipe evolui funcionalidades sem dependencia de banco.

5. Autenticacao local com hash SHA-256
Motivo: baseline de seguranca em ambiente de desenvolvimento.

6. Autorizacao por matriz de funcionalidades
Motivo: controle fino de acesso sem hardcode por pagina.

## Decisoes de UX
- Tema escuro default para jornadas longas.
- Layout `wide` em todas as paginas.
- Download nativo de dados (`csv` e `parquet`) nas tabelas operacionais.
- Dashboard executivo com indicadores consolidados.

## Divida tecnica reconhecida
- Persistencia de usuarios/perfis em YAML (sem trilha de alteracao detalhada ainda).
- Ausencia de rotacao automatica de senha e politica de expiracao.
- Comparador de efetivacao ainda em nivel inicial.

## Proximas melhorias sugeridas
- Migrar configuracoes e auditoria administrativa para banco `app_*`.
- Implementar trilha de alteracao de perfil/usuario.
- Integrar notificacoes por evento de falha ETL.
