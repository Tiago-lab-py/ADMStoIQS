# Jornada de usuário e governança operacional

## 1. Objetivo

Definir a jornada operacional do ADMStoIQS para transformar o uso da ferramenta em um fluxo seguro, auditável e simples:

- ingestão diária dos CSVs ADMS;
- preparação da apuração mensal;
- aplicação de tratamentos automáticos;
- análise pontual por analistas;
- aprovação/implantação governada;
- geração dos CSVs finais para o IQS.

O objetivo é reduzir falhas no IQS sem transformar o processo em uma sequência manual de scripts.

## 2. Perfis de usuário

### 2.1 Admin

Responsável por operação técnica e governança do ambiente.

Pode:

- cadastrar usuários;
- resetar senha;
- alterar perfis;
- acessar ETL operacional;
- forçar atualização de marts;
- implantar tratamentos;
- gerar CSV final;
- consultar governança e logs.

### 2.2 Gestor

Responsável pela decisão operacional e acompanhamento da qualidade.

Pode:

- acessar dashboard executivo;
- consultar indicadores;
- consultar pendências;
- consultar governança;
- autorizar implantação de alterações;
- gerar CSV final para IQS.

Não deve acessar:

- ETL técnico;
- administração de usuários.

### 2.3 Analista

Responsável por análise e tratamento pontual das pendências.

Pode:

- acessar dashboard;
- consultar filas de correção;
- propor alterações pontuais;
- justificar correções.

Não deve acessar:

- ETL;
- administração;
- governança executiva;
- geração final sem autorização.

## 3. Jornada de acesso

### 3.1 Cadastro

O usuário solicita acesso ao sistema.

O admin cadastra:

- e-mail;
- nome;
- perfil;
- status ativo;
- senha inicial padrão `inicio123`;
- flag `troca_senha_obrigatoria = true`;
- flag `segundo_fator_obrigatorio = true`.

O cadastro deve gravar log em parquet contendo:

- usuário criado;
- perfil;
- admin responsável;
- data/hora;
- IP;
- estação/PC quando disponível.

### 3.2 Primeiro login

Quando o usuário acessa com `inicio123`, o sistema não deve carregar dashboard nem dados.

Fluxo esperado:

1. usuário informa e-mail e senha inicial;
2. backend identifica `troca_senha_obrigatoria = true`;
3. frontend redireciona para troca de senha;
4. usuário define nova senha;
5. sistema grava log de alteração de senha;
6. usuário deve fazer login novamente com a nova senha.

Essa regra evita que tokens antigos ou senha padrão liberem navegação operacional.

## 4. Jornada diária de dados

### 4.1 Processamento agendado

O processamento diário deve ser executado preferencialmente pelo backend/agendador.

Etapas recomendadas:

1. verificar CSVs novos na pasta `P:\Common\IQS\ADMS\Backup`;
2. comparar com `log_leitura_csv.parquet`;
3. processar apenas arquivos pendentes;
4. gerar/atualizar parquets mensais em `data/processed`;
5. atualizar `agrupamento_oms_UNION.parquet`;
6. gerar apuração mensal;
7. materializar pendências;
8. materializar e aplicar sobreposição de interrupção;
9. materializar e aplicar sobreposição UC fase 1, quando houver registros elegíveis;
10. materializar e aplicar sobreposição UC fase 2, quando houver interseção temporal elegível;
11. gerar tratado automático;
12. materializar indicadores e ressarcimento;
13. atualizar arquivos `*_ATUAL.parquet`.

As etapas automáticas de sobreposição devem rodar com executor sistêmico:

- `usuario = SISTEMA_AI`;
- `perfil = sistema`;
- `origem = orquestrador_apuracao`;
- `justificativa = tratamento sistêmico automático aprovado na regra operacional`.

### 4.2 Processamento manual pelo admin

O admin deve poder forçar a execução pela interface em casos de exceção.

Exemplos:

- CSV chegou fora do horário;
- processamento diário falhou;
- nova regra foi implantada;
- gestor solicitou nova prévia.

O botão manual deve disparar o mesmo orquestrador usado no agendamento, evitando divergência entre terminal e frontend.

## 5. Separação entre tratamento automático e alteração pontual

### 5.1 Tratamento automático sistêmico

Tratamento automático é aplicado pelo backend para reduzir ruído e preparar a visão executiva.

Exemplos:

- desconsiderar horário negativo do cálculo de indicadores;
- desconsiderar registros sem causa/componente dos indicadores;
- aplicar regra automática de sobreposição de interrupção;
- aplicar regra automática de sobreposição UC fase 1;
- aplicar regra automática de sobreposição UC fase 2;
- gerar base tratada para cálculo e exportação.

Nesses casos, o alterador deve ser registrado como:

- `usuario = SISTEMA_AI`;
- `perfil = sistema`;
- `origem = processamento_backend`;
- `justificativa = regra automática aplicada pelo orquestrador`.

O log deve registrar a regra, a quantidade de registros afetados e os arquivos gerados, mesmo quando não houver usuário humano tomando a decisão.

### 5.3 Expurgos para indicadores de continuidade

Para DEC, FEC, DIC, FIC e DMIC, a base líquida deve considerar apenas registros que atendam simultaneamente:

- `ESTADO_INTRP = '4'`;
- duração válida e maior ou igual a 3 minutos;
- `TIPO_PROTOC_JUSTIF_UCI = '0'`;
- `NUM_MOTIVO_TRAT_DIF_UCI` nulo ou vazio;
- UC faturada conforme HCAI/IQS;
- UC não acessante quando a fonte externa estiver disponível.

Além disso, o FIC deve contar apenas interrupções em que:

- `NUM_INTRP_INIC_MANOBRA_UCI` esteja nulo ou vazio.

Essa regra evita contar como nova frequência uma UC cujo início foi deslocado por manobra/sobreposição já representada por outra interrupção.

Resumo prático:

- **DIC**: soma duração líquida em horas.
- **FIC**: conta interrupções líquidas distintas, mas expurga registros com `NUM_INTRP_INIC_MANOBRA_UCI` preenchido.
- **DMIC**: maior duração líquida individual.
- **DEC/FEC**: agregações de DIC/FIC sobre o denominador de consumidores faturados.

### 5.2 Alteração pontual governada

Alteração pontual é aquela feita caso a caso ou em lote selecionado por analista, gestor ou admin.

Exemplos:

- alterar `DATA_HORA_INIC_INTRP`;
- alterar `DATA_HORA_FIM_INTRP`;
- alterar causa;
- alterar componente;
- marcar registro como rejeitado;
- definir `NUM_MOTIVO_TRAT_DIF_UCI = 91`;
- definir `ESTADO_INTRP = 7`.

Essas alterações devem exigir:

- usuário autenticado;
- perfil permitido;
- justificativa obrigatória;
- log nominal;
- data/hora;
- IP;
- PC;
- chave do registro;
- campo alterado;
- valor anterior;
- valor novo;
- regra relacionada.

## 6. Decisão sobre `NUM_MOTIVO_TRAT_DIF_UCI = 91` e `ESTADO_INTRP = 7`

### 6.1 Quando usar `NUM_MOTIVO_TRAT_DIF_UCI = 91`

Usar quando a UC afetada deve ser desconsiderada/tratada por motivo técnico específico, preservando a interrupção principal.

Exemplos:

- sobreposição de UC;
- manobra já representada por outra interrupção;
- ajuste pontual no nível UCI/HCAI.

### 6.2 Quando usar `ESTADO_INTRP = 7`

Usar quando a interrupção inteira deve ser cancelada/desconsiderada.

Exemplos:

- evento duplicado integral;
- interrupção inválida;
- ocorrência que não deve entrar no produto final IQS.

### 6.3 Governança da implantação

Para alteração pontual, a implantação deve ter um usuário autorizador.

Modelo recomendado:

- analista propõe;
- gestor ou admin autoriza;
- sistema aplica;
- log grava proponente, autorizador e executor sistêmico.

Quando o processamento for automático, o autorizador pode ser uma decisão previamente aprovada da regra, e o executor será `SISTEMA_AI`.

Para sobreposição automática, a recomendação é separar a decisão em dois níveis:

1. **Regra aprovada**: gestor/admin aprova a regra técnica uma vez, documentada em sprint/doc.
2. **Execução diária**: orquestrador aplica a regra com `SISTEMA_AI`, gravando log com quantidade, CHI/horas-UC estimado, arquivos de entrada e saída.

Se uma sobreposição for tratada manualmente pelo analista, volta a valer o fluxo nominal:

- analista propõe;
- gestor/admin autoriza;
- sistema aplica;
- log grava proponente, autorizador, executor e justificativa.

## 7. Materializações e performance

Para navegação fluida, os principais resultados devem ser materializados em parquet.

Arquivos principais:

- `agrupamento_oms_UNION.parquet`;
- `agrupamento_oms_APURACAO_[anomes].parquet`;
- `pendencias_APURACAO_[anomes].parquet`;
- `agrupamento_oms_APURACAO_[anomes]_TRATADO.parquet`;
- `indicadores_comparativo_[anomes].parquet`;
- `indicadores_ressarcimento_[anomes].parquet`.

Também devem existir ponteiros:

- `*_ATUAL.parquet`;
- logs operacionais;
- logs de decisão;
- logs de alteração.

Temporários devem ser gravados em pasta `tmp` e apagados ao final do processamento bem-sucedido.

## 8. Páginas recomendadas

### 8.1 Dashboard executivo

Somente leitura.

Deve mostrar:

- última atualização;
- competência atual;
- arquivos usados;
- status das fontes;
- DEC/FEC antes e depois;
- DIC/FIC/DMIC;
- ressarcimento estimado;
- pendências por regra;
- rejeitados por atividade.

### 8.2 ETL operacional

Acesso admin.

Deve mostrar:

- CSVs pendentes;
- execução de ingestão;
- atualização do UNION;
- geração da apuração;
- materialização de pendências;
- geração de tratado;
- materialização de indicadores.

### 8.3 Filas de correção

Acesso analista e admin.

Deve mostrar:

- horário negativo;
- sem causa/componente;
- sobreposição interrupção;
- sobreposição UC;
- módulos futuros com flag “em desenvolvimento”.

### 8.4 Governança

Acesso gestor e admin.

Deve mostrar:

- alterações propostas;
- alterações aprovadas;
- alterações rejeitadas;
- implantações sistêmicas;
- logs por usuário;
- impacto nos indicadores.

### 8.5 Administração

Acesso admin.

Deve permitir:

- cadastrar usuário;
- resetar senha;
- alterar perfil;
- desativar usuário;
- visualizar logs de acesso.

## 9. Sugestão de arquitetura operacional

Criar um orquestrador único de apuração.

Exemplo:

```text
Executar apuração diária
├── verificar CSVs pendentes
├── processar CSVs
├── atualizar UNION
├── gerar apuração mensal
├── materializar pendências
├── materializar sobreposição interrupção
├── implantar sobreposição interrupção com SISTEMA_AI
├── materializar sobreposição UC fase 1
├── implantar sobreposição UC fase 1 com SISTEMA_AI
├── materializar sobreposição UC fase 2
├── implantar sobreposição UC fase 2 com SISTEMA_AI
├── aplicar tratamento automático sistêmico
├── materializar indicadores
├── materializar ressarcimento
└── registrar resumo executivo
```

Esse orquestrador deve poder ser chamado:

- por agendador;
- por script;
- pelo frontend admin.

## 10. Decisão recomendada

Minha sugestão é:

1. **Backend agendado executa o processo diário automaticamente.**
2. **Admin pode forçar o mesmo processo pela tela ETL.**
3. **Tratamentos sistêmicos automáticos usam `SISTEMA_AI` como executor.**
4. **Alterações pontuais exigem usuário, justificativa e autorização.**
5. **Gestor/admin autorizam alterações que impactam geração final do CSV.**
6. **Analista propõe e justifica, mas não gera produto final sozinho.**
7. **Dashboard deve sempre ler materializações prontas, nunca recalcular pesado em tempo real.**

Essa separação reduz risco, melhora performance e deixa clara a responsabilidade de cada decisão.
