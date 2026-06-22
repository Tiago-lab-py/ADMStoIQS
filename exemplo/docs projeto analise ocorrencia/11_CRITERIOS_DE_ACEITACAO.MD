# Criterios de Aceitacao

## 1. Funcionais
- ETL executa em `sample` sem banco local.
- ETL gera camadas `raw`, `processed`, `mart`, `snapshots` e `validacoes`.
- Dashboard executivo apresenta indicadores e classificacao por protocolo.
- Paginas operacionais exibem dados e permitem exportacao.
- Admin permite gerenciar configuracoes, usuarios, perfis e operacao ETL.

## 2. Seguranca e acesso
- Usuario sem login nao acessa paginas.
- Usuario sem funcionalidade nao acessa recurso restrito.
- Perfis `admin` e `desenvolvedor` possuem acesso total por padrao.

## 3. Qualidade de dados
- Regras DQ criticas calculadas e persistidas.
- Anomalias e scores ISE gerados sem erro.
- Auditoria de snapshot criada quando houver base anterior.

## 4. Usabilidade
- Layout wide padrao em todas as paginas.
- Tema escuro funcional e legivel.
- Navegacao multipagina consistente.

## 5. Operabilidade
- Execucao manual de ETL via Admin com retorno de log.
- Importacao de base legada funcional.
- Configuracoes persistidas em `config/*.yml`.

## 6. Critérios de pronto para homologacao
- Testes do `07_PLANO_DE_TESTES.md` executados.
- Nao haver erro de compilacao Python.
- Evidencia de execucao ETL e carregamento no app.
