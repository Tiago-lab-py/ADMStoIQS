# Log de Desenvolvimento IA

## 2026-05-23
- Estrutura inicial do projeto criada (app, etl, biblioteca, docs, sql, dados).
- SQL de extracao remota criado para interrupcao e servicos.
- Pipeline ETL funcional implementado com camadas raw/processed/mart/snapshots/validacoes.
- Paginas Streamlit multipage implementadas.
- Dados de amostra sinteticos adicionados.
- Adaptador de legado implementado para reaproveitar dados do programa antigo.
- Importador `etl/00_import_legacy_samples.py` criado.
- Login com perfis implantado.
- Tema escuro ergonomico e exportacao de dados nas tabelas implementados.
- Dashboard executivo criado e evoluido com classificacao por protocolo.
- Page Admin evoluida para painel de configuracoes, usuarios, perfis e operacao ETL.
- Autorizacao por funcionalidade aplicada em todas as paginas.
- Documentacao em `docs/` reestruturada e detalhada.
- Documentos renumerados, padronizados em maiusculo e indice ajustado.
- Criado `00_OBJETIVO_PROGRAMA.MD` com base na especificacao V4.
- Criada pasta de backlog `docs/pedencias_de_desenvolvimento` com trilhas funcionais, dados, seguranca, UX, operacao e QA.
- Layout `wide` aplicado em todas as paginas do Streamlit.
- Dashboard executivo aprimorado com classificacoes por protocolo e paleta semantica de cores.
- Legendas/nota de rodape aplicadas em graficos e tabelas com criterio/classificacao.
- Formatação pt-BR aplicada para exibicao numerica (milhar com ponto e decimal com virgula).
- Fluxo de primeiro acesso com troca obrigatoria de senha implementado.
- Confirmacao por codigo de 4 digitos implementada; envio de e-mail removido por decisao operacional (modo local sem SMTP).

## Estado atual
- Aplicacao executa localmente com dados de amostra/legado.
- Fluxo principal pronto para evolucao de regras de negocio avancadas.
- Base de governanca (configuracao, perfis e controle de acesso) estabelecida.
- Login e senha operando em modo local com OTP em tela no primeiro acesso.
