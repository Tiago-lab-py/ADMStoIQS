# Especificacao Consolidada V4

Projeto Técnico UnificadoPlataforma de Pós-Operação, Auditoria e Anomalias de Interrupções

Streamlit multipágina com ETL diário, data quality, validação operacional, gestão de alterações e trilha de auditoria

Versão consolidada V4 - 23/05/2026

1. Visão geral

Este documento consolida a especificação funcional e técnica de uma aplicação corporativa para técnicos de pós-operação, voltada ao controle de dias anômalos, análise de ISE, auditoria de interrupções, avaliação de data quality e gestão de validações operacionais. A solução separa o motor de dados da interface: scripts Python agendados fazem extração, snapshot, processamento e geração de marts; o Streamlit lê apenas dados processados e permite que o técnico analise, valide, altere ou cancele registros para fins de relatório, comparador e efetivação controlada.

2. Objetivos do projeto

Controlar dias anômalos por conjunto elétrico com base no histórico de 2024 e 2025.

Avaliar ocorrências com TIPO_PROTOCOLO = 0 (Normal) em dias nos quais o mesmo conjunto possui TIPO_PROTOCOLO = 1 (dia crítico) ou TIPO_PROTOCOLO = 6 (ISE) que são consideradas Ocorrências expurgadas.

Agrupar interrupções por EQUIPAMENTO para evitar dupla contagem operacional.

Calcular pré-análise de dia crítico por CONJUNTO com média histórica mais três desvios padrão dos serviços, desconsiderando dias de ISE e contando apenas um serviço por ocorrência.

Comparar o comportamento de ISE por conjunto, causa, componente, tipo de equipamento e duração contra o histórico 2024/2025.

Sinalizar interrupções em dia de ISE fora do comportamento normal para apoio à fiscalização.

Detectar anomalias de CI, CHI e duração por conjunto, causa, componente, tipo de equipamento e número operacional do equipamento.

Permitir interação de pós-operação no registro: validar, solicitar alteração, cancelar, ajustar campos e acompanhar efetivação.

Registrar todas as decisões em trilha de auditoria e gerar relatórios comparativos antes/depois.

3. Arquitetura proposta

Fluxo recomendado:

DIS.INTERRUPCAO e DIS.SERVICOS

ETL Python agendado

Camada RAW

Camada PROCESSED

Camada MART

Streamlit multipágina

Usuários técnicos, administradores, gestores e fiscalização

A aplicação Streamlit não deve consultar a base operacional pesada durante o uso normal. Ela deve consumir arquivos Parquet ou tabelas corporativas já processadas, versionadas e auditáveis.

4. Estrutura de pastas sugerida

analise_ocorrencia/├── app/│   ├── Home.py│   ├── pages/│   │   ├── 1_Data_Quality.py│   │   ├── 2_Dias_Anomalos.py│   │   ├── 3_Analise_ISE.py│   │   ├── 4_Interrupcoes_Agrupadas.py│   │   ├── 5_Auditoria_Alteracoes.py│   │   ├── 6_Validacao_Pos_Operacao.py│   │   ├── 7_Comparador_Efetivacao.py│   │   └── 8_Admin.py├── etl/│   ├── 01_extract_interrupcao.py│   ├── 02_extract_servicos.py│   ├── 03_snapshot_diario.py│   ├── 04_processar_ocorrencias.py│   ├── 05_calcular_dias_anomalos.py│   ├── 06_analisar_ise.py│   ├── 07_detectar_anomalias.py│   ├── 08_gerar_mart.py│   └── 09_comparar_efetivacao.py├── biblioteca/│   ├── conexao.py│   ├── carga.py│   ├── regras_dia_critico.py│   ├── regras_ise.py│   ├── anomalias.py│   ├── auditoria.py│   ├── qualidade.py│   ├── validacao_pos.py│   └── utils.py└── docs/│   ├── 01_CONFIGURACAO_GERAL.md│   ├── 02_BIBLIOTECAS.md│   ├── 03_ARQUITETURA_E_FLUXO_DADOS.md│   ├── 04_DICIONARIO_DE_DADOS.md│   ├── 05_REGRAS_DE_DATA_QUALITY.md│   ├── 06_MOTOR_DE_ETL_E_SNAPSHOTS.md│   ├── 07_REGRAS_ANALITICAS_E_ESTATISTICA.md│   ├── 08_INTERFACE_STREAMLIT.md

│   ├── 09_GOVERNANCA_E_AUDITORIA.md│   └── 10_CRITERIOS_DE_ACEITACAO_E_TESTES.md

├── sql/├── config/├── dados/│   ├── raw/│   ├── processed/│   ├── mart/│   ├── snapshots/│   └── validacoes/├── logs/└── run_etl_diario.py

5. Dicionário mínimo de dados

Campo

Uso no projeto

NUM_INTERRUPCAO

Identificador da interrupção. Confirmar grafia oficial no banco; no documento inicial apareceu como NUM_INTRPUPCAO.

NUMERO_OCORRENCIA

Identificador operacional da ocorrência. Chave principal para agrupamento.

LOCAL

Identifica ocorreu em área Urbana (U) ou área Rural (R)

DT_INI

Data e hora de início da interrupção.

DT_FIM

Data e hora de fim da interrupção.

COD_CONJUNTO

Código do conjunto elétrico regulatório.

NAME_CONJUNTO

Nome do conjunto elétrico.

TIPO_PROTOCOLO

Classificação do protocolo: 0 normal, 1 dia crítico, 6 ISE, conforme regra interna.

NUM_PROTOCOLO

Número do protocolo ou justificativa associado ao evento.

TIPO_EQUIPAMENTO

Tipo de equipamento associado à interrupção.

NUM_OPERACIONAL_EQUIPAMENTO

Número operacional do equipamento, necessário para assinatura histórica do ativo.

Alim_intrp

Numero do alimentador interrompido.

COD_CAUSA / CAUSA

Código e descrição da causa.

COD_COMPONENTE / COMPONENTE

Código e descrição do componente.

CI_URBANO / CI_RURAL

Consumidores interrompidos urbanos e rurais.

CHI_URBANO / CHI_RURAL

Consumidor-hora interrompido urbano e rural.

CI_EXP_URBANO / CI_EXP_RURAL

Consumidores expurgados urbanos e rurais.

CHI_EXP_URBANO / CHI_EXP_RURAL

Consumidor-hora expurgado urbano e rural.

DESCRICAO_SERVICO

Texto livre do serviço, usado para sugerir causa provável por regras ou modelo textual.

6. Dados necessários além dos campos listados

Fonte/Dado

Necessidade

DIS.SERVICOS

NUMERO_OCORRENCIA, data do serviço, descrição do serviço, equipe, tipo de serviço, status e vínculo com interrupção.

Calendário operacional

Dias úteis, fins de semana, feriados, eventos climáticos relevantes e janelas de fiscalização.

Cadastro de conjuntos

COD_CONJUNTO, nome, regional, área, quantidade de consumidores, rural/urbano e atributos regulatórios.

Tabela de protocolos

Domínio oficial dos valores de TIPO_PROTOCOLO e regras de expurgo.

Parâmetros de anomalia

Janelas históricas, limites, severidade, exceções e responsáveis por validação.

Usuários/perfis

E-mail corporativo, perfil, ativo, área, permissões e trilha de auditoria.

Tabela de efetivação

Controle de registros alterados no sistema de origem ou na camada corporativa de revisão.

## 6.1 Hierarquia e cardinalidade operacional (regra obrigatória)

Árvore de informação oficial da aplicação:

- Conjunto
- Alimentador
- Ocorrência
- Interrupção
- Serviço
- Reclamações

Cardinalidades:

- 1 conjunto pode ter N alimentadores;
- 1 alimentador pode ter N ocorrências;
- 1 ocorrência pode ter N interrupções;
- 1 interrupção pode ter N serviços;
- 1 serviço pode ter N reclamações.

Regra de vínculo para análise operacional:

- o vínculo entre serviços e reclamações deve ser realizado por **alimentador** (e janela de data da análise), sem exigir chave direta serviço→reclamação.

7. Regras analíticas propostas

## 7.1 Filtro mínimo de interrupções

Registros com duração negativa ou DT_FIM menor que DT_INI devem ser tratados como erro crítico de Data Quality e enviados para revisão.

Registros menor que 3 minutos que tiver coincidentes com registros maior ou igual que 3 minutos sinalizar o registro de curta duração para eliminação desde que o tipo_protocolo seja o mesmo.

## 7.2 Dia crítico preliminar

Por COD_CONJUNTO e data, calcular a quantidade de serviços distintos, contando apenas um serviço por OCORRENCIA. O histórico base será 2024 e 2025. Dias de ISE devem ser desconsiderados. A regra sinaliza quando a quantidade diária observada for superior à média histórica acrescida de três desvios padrão.

## 7.3 Mistura suspeita de protocolos

Sinalizar quando houver interrupções com TIPO_PROTOCOLO = 0 , TIPO_EQUIPAMENTO e NUM_OPERACIONAL_EQUIPAMENTO com sobreposição temporal na interrupção em que existam interrupções com TIPO_PROTOCOLO = 1 ou TIPO_PROTOCOLO = 6. Sugerir a alteração do protocolo normal para expurgo.

## 7.4 Tipo protocolo 1 - Dia crítico

Quando TIPO_PROTOCOLO = 1, a regra esperada é que o impacto esteja concentrado em CI/CHI expurgado. Caso haja CI/CHI líquido incompatível, o registro deve ser sinalizado para validação.

## 7.5 Tipo protocolo 6 - ISE

Quando TIPO_PROTOCOLO = 6, a aderência ao expurgo depende da causa e do comportamento histórico. A aplicação deve comparar causa, componente, equipamento, duração, CI e CHI contra o histórico 2024/2025.

## 7.6 Distância euclidiana por Z-Score

Para cada evento, calcular variáveis padronizadas por z-score e medir distância euclidiana em relação ao comportamento histórico do conjunto, tipo de equipamento e número operacional do equipamento. Variáveis mínimas: CI líquido, CHI líquido, CI expurgado, CHI expurgado, duração e frequência.

## 7.7 Assinatura histórica do equipamento

Utilizar o número operacional do equipamento e tipo de equipamento para construir perfil de comportamento: causas recorrentes, componentes associados, duração típica, CI/CHI típico e taxa de reincidência.

## 7.8 Sugestão automática de causa

Usar a descrição do serviço para sugerir causa provável. A primeira versão pode usar dicionário de palavras-chave e expressões regulares; versões futuras podem usar classificação textual supervisionada.

## 7.9 Sobreposição temporal

Verificar se a mesma interrupção possui registros diferentes com horários sobrepostos. Condição: DT_INI_A < DT_FIM_B AND DT_INI_B < DT_FIM_A. Também avaliar sobreposição por mesma UC/equipamento quando houver dados disponíveis.

## 7.10 Auditoria diária de alterações

A cada carga diária, gravar snapshot da base extraída e comparar contra o snapshot anterior. Registrar inclusão, exclusão e alteração de campos críticos: DT_INI, DT_FIM, TIPO_PROTOCOLO, causa, componente, CI, CHI, CI_EXP e CHI_EXP.

## 7.11 Assinatura histórica família de equipamento

Utilizar o conjunto e local do tipo de equipamento para construir perfil de comportamento: causas recorrentes, componentes associados, duração típica, CI/CHI típico e taxa de reincidência.

## 7.12 Perfil de reclamação

O sistema deverá verificar as reclamações por UC por data e reincidência período de análise. Quando na mesma data para dia normais ou número protocolo ISE ou protocolo Dia Crítico.

As UC deverão ser vinculadas ao Conjunto da Interrupção e ao alimentador interrompido, as reclamações deverão ser listadas com sua descrição para facilitar a análise pela pós.

8. Interação da pós-operação no registro

A tela de pós-operação deve permitir que o técnico analise cada anomalia ou interrupção agrupada e registre a decisão operacional, sem alterar diretamente a base bruta. A alteração deve ser gravada em tabela de revisão e posteriormente comparada com a efetivação no sistema de origem através da base corporativa. Pois ao cancelar a interrupção no OMS o mesmo não transmitirá para o banco DENODO. O Registro será excluído da base de dados ficará apenas na base de dados comparativo da aplicação.

Ação

Descrição

Registro esperado

Validar

Confirma que o registro está correto e não requer ajuste.

status_validacao = VALIDO

Alterar

Permite propor ajuste de DT_INI, DT_FIM, causa, componente, tipo protocolo e observação.

status_validacao = ALTERAR

Cancelar

Indica que o registro não deve compor a análise, mediante justificativa.

status_validacao = CANCELAR

Pendente

Mantém o item para revisão futura.

status_validacao = PENDENTE

Efetivado

Confirma que a alteração proposta foi aplicada no sistema de origem .

status_efetivacao = EFETIVADO

Não efetivado

Indica que a alteração foi recusada, vencida ou ainda não aplicada.

status_efetivacao = NAO_EFETIVADO

## 8.1 Campos ajustáveis na tela

DT_INI ajustada

DT_FIM ajustada

COD_CAUSA / CAUSA ajustada

COD_COMPONENTE / COMPONENTE ajustado

TIPO_PROTOCOLO ajustado

NUM_PROTOCOLO ajustado ou informado

Comentário técnico obrigatório para alteração ou cancelamento

Usuário, data/hora e perfil do responsável pela decisão

## 8.2 Tabela de validação e revisão

Campo

Finalidade

id_validacao

Identificador único da validação.

chave_evento

Chave técnica do registro: interrupção, ocorrência, conjunto e data.

num_interrupcao / numero_ocorrencia

Identificadores principais.

status_validacao

PENDENTE, VALIDO, ALTERAR ou CANCELAR.

status_efetivacao

PENDENTE, EFETIVADO, NAO_EFETIVADO ou PARCIAL.

campos_originais_json

Valores originais antes da decisão.

campos_propostos_json

Valores propostos pelo técnico.

comentario

Justificativa da decisão.

usuario_validacao / data_validacao

Responsável e data/hora da validação.

usuario_efetivacao / data_efetivacao

Responsável e data/hora da efetivação, quando aplicável.

## 8.3 Comparador antes/depois

A aplicação deve gerar um comparador entre o registro original, a proposta de alteração e o estado efetivado. O objetivo é comprovar se a revisão foi aplicada e manter evidência para relatório, auditoria e fiscalização.

Camada

Descrição

Original

Valor extraído do snapshot ou mart antes da validação.

Proposto

Valor ajustado pelo técnico na tela de pós-operação.

Efetivado

Valor encontrado posteriormente no sistema de origem ou na base corporativa definitiva.

Resultado

Igual, divergente, parcialmente efetivado ou não encontrado.

## 8.4 Modelo de validação por campo com tripla visão (obrigatório)

Para cada campo ajustável na Validação Pós-Operação, a interface deve exibir três visões simultâneas:

- **Original**: valor vindo dos dados analíticos (`dados/mart`).
- **Sugerido**: valor calculado pelo sistema com base na tendência da ocorrência (ex.: aderência de causa/componente frente ao histórico e contexto operacional).
- **Editado**: valor final informado/confirmado pelo analista.

A regra de persistência é:

- `Original` nunca pode ser sobrescrito;
- `Sugerido` deve ficar registrado como recomendação de sistema;
- `Editado` deve representar a decisão operacional do analista.

## 8.5 Regra de contexto da validação por alimentador e data

Na validação de uma ocorrência, a aplicação deve usar obrigatoriamente:

- `alimentador`;
- `data` (data operacional da ocorrência/interrupção);

para filtrar e apresentar ao usuário, no mesmo contexto:

- reclamações do alimentador na data;
- ocorrências do alimentador na data;
- interrupções do alimentador na data.

Esses dados compõem o painel de apoio da decisão e não substituem a decisão técnica do analista.

9. Marts de saída

Mart

Campos sugeridos

mart_dias_anomalos

data, cod_conjunto, name_conjunto, qtd_servicos, media_hist, desvio_hist, limite_3sigma, flag_anomalia

mart_ocorrencias_agrupadas

numero_ocorrencia, data, cod_conjunto, qtd_interrupcoes, tipos_protocolo, causas, componentes, ci_total, chi_total, duracao

mart_ise

data, cod_conjunto, numero_ocorrencia, perfil_historico, causa, componente, tipo_equipamento, score_anomalia

mart_anomalias

tipo_anomalia, severidade, motivo, status_validacao, usuario_validacao, comentario

mart_auditoria_alteracoes

data_snapshot, chave_evento, campo, valor_anterior, valor_atual, tipo_alteracao

mart_validacoes_pos_operacao

registro das decisões: validar, alterar, cancelar, status de efetivação e comparador antes/depois

10. Streamlit multipágina

Página

Função

Home

Resumo da última carga, quantidade de anomalias, pendências e status geral.

Data Quality

Nulos, duplicidades, inconsistências temporais, campos inválidos e falhas de carga.

Dias Anômalos

Ranking por conjunto/data, limite histórico, serviços observados e detalhes.

Análise ISE

Comparação de ISE atual vs histórico por causa, componente e equipamento.

Interrupções Agrupadas

Consulta por ocorrência, interrupções vinculadas, protocolo e métricas CI/CHI.

Validação Pós-Operação

Tela de interação no registro: validar, alterar, cancelar, comentar e enviar para efetivação.

Comparador Efetivação

Verificação se alteração proposta foi aplicada, com antes/depois e divergências.

Auditoria

Alterações entre snapshots, campos modificados e trilha de revisão.

Admin

Parâmetros, usuários, perfis, regras e liberação de competência.

11. Perfis de acesso

Perfil

Permissões

Usuário

Consultar, filtrar, validar anomalias, propor alteração, cancelar com justificativa, comentar e exportar resultados.

Administrador

Gerenciar usuários, parâmetros, regras, reprocessamento, auditoria completa, liberação de competência, efetivação e Fechar o mês para alterações.

Gestor/Auditor

Visualizar indicadores, auditoria, histórico de validações e relatórios, sem alterar parâmetros técnicos, Fechar o mês para alterações.

12. Regras de Data Quality

Regra

Descrição

DQ_CRIT_001

Interrupção com mais de 1000 CHI

DQ_CRIT_002

DT_FIM menor que DT_INI.

DQ_CRIT_003

CHI/CI incompatível com protocolo.

DQ_CRIT_004

Interrupção sem conjunto.

DQ_CRIT_005

Equipamento sem componente.

DQ_CRIT_006

Protocolo incompatível com causa.

DQ_CRIT_007

Sobreposição temporal de interrupções da mesma ocorrência.

DQ_CRIT_008

Sobreposição temporal para mesma UC/equipamento.

DQ_CRIT_009

Controle de Alteração, armazenar usuário que registrou a mudança de status.

DQ_CRIT_010

Cancelamento sem justificativa.

DQ_CRIT_011

Automatismos de data Quality, quando o sistema altera o registro

13. Automatismo pelo sistema

O sistema deverá permitir pelo ADM fechar alteração do mês assim os registros não poderão ser mais alterados pelos usuários. Porém o sistema deverá ter o status PEDENTE DE ALTERAÇÃO e o usuário será “POSAUDIT”.Haverá a necessidade de relatórios após o fechamento do sistema. A quantidade de alterações feito pela equipe, sistema. Produtividade por usuário. Efetividade das alterações, quantas alterações foram mapeadas e quantas foram efetivadas. Eficiência das alterações mensuração de ganhos de CHI, CI, DEC e FEC por CONJUNTO e Global (COPEL).Regras:

Quantidade de consumidores por conjunto por mês e o soma dos conjunto é Copel.

O DEC é a soma de CHI dividido pela média de consumidores do período de apuração.

O FEC é a soma de CI dividido pela média de consumidores do período de apuração.

Deverá calcular o DEC e FEC por REGIONAL, BASE OPERACIONAL, MANUTEÇÃO este organograma será relativo ao desempenho do CONJUNTO. O cálculo REAL de DEC e FEC será a extração do banco original e comparar com as alterações efetivadas, não efetivadas e não realizadas. Não realizadas é que o sistema sugeriu e equipe não validou. O objetivo é medir a eficiência da ferramenta e equipe.

Discriminar os cálculos de eficiência e efetividade Regras de Data Quality.

15. Requisitos técnicos

Python 3.11 ou superior.

Streamlit multipage.

Pandas/Polars para processamento.

Parquet para arquivos analíticos ou PostgreSQL/PostGIS para persistência corporativa.

Agendador Windows, Airflow ou scheduler corporativo para execução diária.

Controle de credenciais por variável de ambiente, cofre ou conta de serviço.

Logs estruturados e snapshots com retenção definida.

Autenticação corporativa preferencialmente por Microsoft Entra ID/OIDC ou integração equivalente.

Controle de perfil por RBAC: admin, usuário, gestor/auditor.

Trilha de auditoria imutável para decisões de pós-operação.

## Anexo A - Prompt para Codex

Crie uma aplicação corporativa em Python para pós-operação de interrupções de energia elétrica, com ETL separado da interface e Streamlit multipage para análise, validação, alteração controlada e auditoria.Contexto:A aplicação deve analisar registros das tabelas DIS.INTERRUPCAO e DIS.SERVICOS. O objetivo é controlar dias anômalos, identificar mistura suspeita de protocolos, analisar ISE fora do comportamento histórico, auditar alterações diárias nos registros de interrupção e permitir que técnicos de pós-operação validem, alterem ou cancelem registros em uma camada de revisão.Campos mínimos em DIS.INTERRUPCAO:- NUM_INTERRUPCAO- NUMERO_OCORRENCIA- DT_INI- DT_FIM- COD_CONJUNTO- NAME_CONJUNTO- TIPO_PROTOCOLO- NUM_PROTOCOLO- TIPO_EQUIPAMENTO- NUM_OPERACIONAL_EQUIPAMENTO- COD_CAUSA- CAUSA- COD_COMPONENTE- COMPONENTE- CI_URBANO- CI_RURAL- CHI_URBANO- CHI_RURAL- CI_EXP_URBANO- CI_EXP_RURAL- CHI_EXP_URBANO- CHI_EXP_RURALCampos adicionais desejáveis em DIS.SERVICOS:- NUMERO_OCORRENCIA- DATA_SERVICO- DESCRICAO_SERVICO- EQUIPE- TIPO_SERVICO- STATUS_SERVICORegras de negócio:1. Considerar somente interrupções com duração maior ou igual a 3 minutos.2. Tratar duração negativa e DT_FIM menor que DT_INI como Data Quality crítico.3. Agrupar interrupções por NUMERO_OCORRENCIA.4. Para serviços, considerar apenas 1 serviço por ocorrência.5. Calcular dias críticos preliminares por COD_CONJUNTO e data usando histórico 2024 e 2025.6. O limite de pré-análise de dia crítico deve ser média histórica + 3 desvios padrão.7. No cálculo histórico dos dias críticos preliminares, desconsiderar dias de ISE, considerando TIPO_PROTOCOLO = 6.8. Sinalizar ocorrências com TIPO_PROTOCOLO = 0 em dias nos quais o mesmo COD_CONJUNTO possui TIPO_PROTOCOLO = 1 ou TIPO_PROTOCOLO = 6.9. Para TIPO_PROTOCOLO = 1, validar se o evento possui apenas CI/CHI expurgado e se o CI/CHI líquido é procedente ou anômalo.10. Para TIPO_PROTOCOLO = 6, comparar o comportamento histórico por COD_CONJUNTO, COD_CAUSA, COD_COMPONENTE, TIPO_EQUIPAMENTO, NUM_OPERACIONAL_EQUIPAMENTO, CI, CHI e duração.11. Usar z-score por coluna e distância euclidiana para detectar comportamento fora do padrão.12. Detectar anomalia de duração por conjunto, causa, componente, tipo de equipamento e equipamento operacional.13. Verificar sobreposição temporal da mesma interrupção em registros diferentes usando: DT_INI_A < DT_FIM_B AND DT_INI_B < DT_FIM_A.14. Pela DESCRICAO_SERVICO, sugerir causa provável usando dicionário de palavras-chave e preparar módulo para modelo textual futuro.15. Executar snapshot diário da DIS.INTERRUPCAO e comparar com o snapshot do dia anterior para detectar alterações retroativas.Funcionalidades da interface:- filtros por competência, data, conjunto, protocolo, causa, componente, tipo de equipamento e número operacional;- painel de data quality;- ranking de dias anômalos;- consulta de ocorrências agrupadas;- painel de ISE fora do padrão;- painel de auditoria de alterações;- tela de validação de pós-operação para cada registro;- ações: validar, alterar, cancelar e manter pendente;- se alterar, permitir ajustar DT_INI, DT_FIM, causa, componente, tipo protocolo e número do protocolo;- comentário obrigatório para alteração e cancelamento;- armazenar validações em tabela ou parquet próprio;- gerar relatório de alterações propostas;- comparar registro original, proposto e efetivado;- indicar status de efetivação: pendente, efetivado, não efetivado ou parcial;- exportação para CSV/Excel;- cache com st.cache_data;- controle simples de perfil admin/usuario/gestor via config/usuarios.yml.Arquitetura desejada:- ETL separado da interface.- Camadas: dados/raw, dados/processed, dados/mart, dados/snapshots e dados/validacoes.- Streamlit deve apenas ler dados processados/mart durante o uso do técnico.- Criar scripts ETL e módulos reutilizáveis.- Persistência inicial em Parquet, preparando futura troca por PostgreSQL/PostGIS.- Código modular, com docstrings, logs, tratamento de erros, .env para credenciais e YAML para configuração.

## Anexo B - Observações de implantação

Validar a grafia real do campo NUM_INTERRUPCAO no banco antes de codificar.

Definir se a data de análise será derivada de DT_INI, DT_FIM ou data operacional da ocorrência.

Definir retenção dos snapshots, por exemplo 180 dias ou 24 meses.

Definir se a validação do técnico terá efeito apenas analítico ou se gerará tabela corporativa de revisão com processo de efetivação.

Evitar execução de consultas pesadas pelo Streamlit durante o uso normal.

A alteração proposta pelo usuário não deve sobrescrever o raw; deve ser armazenada como proposta com usuário, data/hora, justificativa e status.

O comparador deve indicar se a alteração foi efetivada posteriormente no sistema de origem ou no mart definitivo.

## Anexo C - Documentos consolidados

Este documento consolida e amplia os dois documentos fornecidos: a versão técnica preliminar de 8 páginas e a versão complementar com regras adicionais de anomalias, z-score, distância euclidiana e sobreposição temporal.

14. Regras adicionais de ISE, efetivação e priorização operacional

## 14.1 Regra mínima de CHI para protocolo ISENa janela de análise de ISE, eventos com o mesmo NUM_PROTOCOLO devem possuir soma mínima de 700.000 CHI expurgado (CHI_EXP_URBANO + CHI_EXP_RURAL). Caso o protocolo não atinja esse valor mínimo, a aplicação deverá identificar e rankear interrupções candidatas à inclusão no protocolo ISE.

Critérios sugeridos para ranking de inclusão:

Maior CHI líquido associado ao evento.

Maior aderência estatística ao perfil histórico do ISE.

Mesma causa e componente predominantes no protocolo.

Mesma região/conjunto e proximidade temporal.

Maior distância euclidiana em relação ao comportamento normal líquido.

Ocorrências vinculadas ao mesmo evento climático ou operacional.

## 14.2 Verificação obrigatória para CHI elevadoToda interrupção com CHI total maior ou igual a 2.000 deverá ser automaticamente encaminhada para revisão obrigatória pela pós-operação.

Status sugeridos do workflow:

PENDENTE_VERIFICACAO

EM_ANALISE

VALIDO

ALTERAR

CANCELAR

CONFIRMADO

EFETIVADO

NAO_EFETIVADO

## 14.3 Confirmação de efetivaçãoQuando a alteração proposta pelo técnico for implementada no sistema de origem ou no mart corporativo definitivo, o registro deverá assumir status CONFIRMADO e posteriormente EFETIVADO, mantendo trilha completa de auditoria.

A aplicação deverá comparar automaticamente o estado ORIGINAL, PROPOSTO e EFETIVADO.

## 14.4 Melhorias futuras recomendadas

Modelo de severidade automática por impacto regulatório.

Classificação automática de anomalias usando Isolation Forest e LOF.

Integração com eventos climáticos externos e radares meteorológicos.

Mapa geoespacial de anomalias e protocolos ISE.

Motor de recomendação de protocolo provável.

Classificação textual inteligente da DESCRICAO_SERVICO utilizando NLP.

Workflow de aprovação multinível entre técnico, gestor e auditoria.

Painel executivo de impacto DEC/FEC antes e depois das alterações.

Assinatura histórica de comportamento por equipamento operacional.

Indicador de reincidência operacional por equipamento e conjunto.

Controle de SLA de revisão das anomalias críticas.

Dashboard de efetivação pendente e divergências operacionais.

## Documento atualizado em 23/05/2026 03:00

15. Governança da Informação, Segurança e Auditoria Corporativa

## 15.1 Controle de acesso e autenticação

A aplicação deverá possuir autenticação corporativa integrada preferencialmente ao Microsoft Entra ID, Active Directory ou LDAP corporativo.O acesso deverá ser segregado por RBAC (Role Based Access Control), permitindo perfis distintos:- Usuário Operacional- Administrador- Gestor- Auditor- FiscalizaçãoA aplicação deverá registrar:- usuário autenticado- data/hora de login- IP ou hostname de origem- sessão ativa- tentativas inválidas de acessoA aplicação deverá permitir:- bloqueio automático por múltiplas tentativas inválidas- expiração automática de sessão- fechamento mensal das competências- segregação entre homologação e produção

## 15.2 Governança da informação

A solução deverá possuir governança completa dos dados operacionais garantindo:- rastreabilidade- versionamento- imutabilidade da camada RAW- trilha de auditoria- segregação entre dado original e dado proposto- retenção históricaCamadas:RAW = dados originaisPROCESSED = dados tratadosMART = dados analíticosVALIDACOES = propostas operacionaisSNAPSHOTS = fotografia histórica

## 15.3 Controle de alterações

Nenhum dado da camada RAW poderá ser alterado diretamente.Toda alteração deverá possuir:- usuário responsável- data/hora- justificativa- valor original- valor proposto- valor efetivado- status- motivo técnicoA aplicação deverá permitir:- comparação antes/depois- rastreabilidade- reversão controlada- histórico completo das versões

## 15.4 Logs e trilha de auditoria

A aplicação deverá possuir logs estruturados para:- autenticação- alteração de registros- efetivação- exportação de relatórios- reprocessamentos- alterações automáticas- falhas ETLOs logs deverão conter:- timestamp- usuário- ação- módulo- chave do evento- valores alterados- status- hostname/IP- severidadeSeveridades sugeridas:INFOWARNINGERRORCRITICALAUDIT

## 15.5 Auditoria operacional

O auditor deverá conseguir:- visualizar quem alterou- quando alterou- motivo da alteração- impacto regulatório- situação da efetivação- histórico do registroA aplicação deverá gerar relatórios:- produtividade por usuário- efetividade das alterações- eficiência operacional- impacto em DEC/FEC- impacto em CHI/CI- alterações não efetivadas

## 15.6 Segurança e boas práticas

A solução deverá seguir boas práticas de segurança:- variáveis de ambiente para credenciais- .env fora do repositório- criptografia de conexões- segregação de permissões- backup dos snapshots- retenção histórica- trilha imutável de auditoria- logs protegidos contra exclusão indevidaRecomenda-se:- PostgreSQL/PostGIS- Git corporativo- pipeline CI/CD- homologação separada da produção

16. Requisitos não funcionais

Alta disponibilidade da aplicação.

Capacidade multiusuário simultâneo.

Escalabilidade histórica.

Recuperação automática de falhas ETL.

Versionamento de regras operacionais.

Persistência auditável das decisões.

Execução automática via scheduler corporativo.

Compatibilidade com ambiente Windows corporativo.

17. Considerações finais

A plataforma proposta caracteriza-se como um sistema corporativo de pós-operação, auditoria regulatória e governança operacional, permitindo rastreabilidade completa das decisões técnicas, controle de anomalias, apoio à fiscalização e mensuração de impacto regulatório.

Versão V3 atualizada em 23/05/2026 15:42

18. Complemento V4 - Controle de Acesso, Monitoramento, Notificações e Segredos

Objetivo do complemento V4. Este complemento adiciona requisitos específicos de controle de acesso, monitoramento de login/logout, trilha de sessão, alerta por e-mail, armazenamento corporativo no dbGUO/ddcq, gestão segura de credenciais Denodo e documentação de desenvolvimento assistido por IA na pasta docs/.

## 18.1 Controle de acesso com rastreabilidade de sessão

A aplicação deverá monitorar todo ciclo de acesso do usuário, incluindo login, logout, expiração de sessão e tentativas inválidas. O objetivo é garantir rastreabilidade, auditoria e identificação de uso indevido.

Item

Descrição

Login

Registrar usuário, perfil, data/hora, IP, hostname, user agent, origem da autenticação e status da autenticação.

Logout

Registrar data/hora de saída, duração da sessão e motivo de encerramento: voluntário, timeout, bloqueio ou erro.

Sessão

Gerar identificador único de sessão para correlacionar ações, alterações, exportações e consultas.

Tentativa inválida

Registrar tentativas de acesso negadas, usuário informado, IP, horário e motivo.

Bloqueio

Permitir bloqueio por excesso de tentativas inválidas, conforme parâmetro definido pelo administrador.

Expiração

Encerrar sessão por inatividade, registrando timeout na trilha de auditoria.

Tabela sugerida: app_sessoes_acesso

Campo

Finalidade

id_sessao

Identificador único da sessão.

usuario

Login ou e-mail corporativo autenticado.

perfil

Perfil RBAC no momento do acesso.

ip_origem

Endereço IP da conexão.

hostname_origem

Nome da estação quando disponível.

user_agent

Navegador ou cliente utilizado.

dt_login

Data e hora do login.

dt_logout

Data e hora do logout ou encerramento.

motivo_logout

Manual, timeout, erro, bloqueio ou encerramento administrativo.

status_login

Sucesso, negado, bloqueado ou falha de autenticação.

## 18.2 Monitoramento de ETL e alertas por e-mail

O ETL deverá rodar em backend de forma independente do Streamlit. O Streamlit apenas cadastra parâmetros e consulta o status das execuções. Em caso de falha, o sistema deverá disparar e-mail automático para os usuários com perfil Administrador.

Situação

Ação automática

Início do ETL

Registrar início da execução, competência, parâmetros ativos e usuário/sistema responsável.

Sucesso do ETL

Registrar término, quantidade de registros extraídos, processados, rejeitados e tempo total.

Falha do ETL

Registrar erro técnico, stack trace resumido, etapa com falha e disparar e-mail para administradores.

Falha parcial

Gerar alerta quando alguma etapa concluir com ressalvas ou perda de registros.

Reprocessamento

Registrar usuário solicitante, motivo, competência, parâmetros e resultado.

Tabela sugerida: app_etl_execucao

Campo

Finalidade

id_execucao

Identificador da execução.

competencia

Competência processada.

dt_inicio / dt_fim

Controle temporal da execução.

status_execucao

INICIADO, SUCESSO, FALHA, FALHA_PARCIAL ou CANCELADO.

etapa_atual

Extração, snapshot, processamento, mart, data quality ou comparação.

qtd_extraida / qtd_processada / qtd_rejeitada

Métricas de execução.

mensagem_erro

Resumo do erro quando houver falha.

parametros_json

Parâmetros ativos utilizados na execução.

notificacao_enviada

Indica se o alerta por e-mail foi enviado.

## 18.3 Notificações no fechamento mensal

Quando uma competência for fechada para alterações, a aplicação deverá enviar e-mail automático para usuários de pós-operação, gestores e administradores informando o fechamento, a data/hora, o responsável e o resumo dos indicadores da competência.

Evento

Destinatários

Conteúdo mínimo

Fechamento mensal

Pós-operação, gestores e administradores

Competência, responsável, data/hora, quantidade de registros validados, alterados, cancelados, pendentes e efetivados.

Reabertura excepcional

Gestores e administradores

Motivo, responsável, janela de reabertura e registros afetados.

Fechamento com pendências

Gestores, administradores e responsáveis operacionais

Lista de pendências críticas, anomalias não tratadas e impacto estimado.

## 18.4 Armazenamento corporativo da aplicação

O armazenamento oficial dos dados da aplicação deverá ocorrer no banco dbGUO/ddcq, utilizando o perfil de aplicação ddcq_user. Esse usuário representa uma chave de produto da aplicação, devendo possuir permissões mínimas necessárias para leitura e escrita nas tabelas próprias do sistema.

Objeto

Uso recomendado

dbGUO/ddcq

Banco e base corporativa da aplicação.

ddcq_user

Perfil técnico/produto utilizado pela aplicação para persistência dos dados próprios.

Tabelas app_*

Parâmetros, usuários, sessões, logs, validações, notificações e execuções ETL.

Tabelas mart_*

Resultados analíticos e camadas de consulta.

Tabelas snapshot_*

Histórico de fotografia diária para comparação.

Tabelas audit_*

Trilha imutável de auditoria.

O perfil ddcq_user não deve ser utilizado para consulta direta aos dados sensíveis do Denodo quando essa consulta exigir credenciais individuais ou credenciais administrativas específicas. O acesso Denodo deverá ser tratado em camada própria de conexão e segredos.

## 18.5 Gestão segura de credenciais Denodo

Para acesso ao Denodo, a aplicação deverá permitir que o usuário administrador informe chave e senha de acesso. A senha não poderá ser armazenada em texto claro. A solução deverá ocultar a senha na interface e armazená-la de forma criptografada ou preferencialmente em cofre corporativo.

Requisito

Descrição

Entrada da senha

Campo do tipo password, sem exibição em tela, sem log e sem armazenamento em cache de sessão.

Armazenamento

Preferencialmente cofre corporativo. Alternativamente, criptografia forte com chave fora do banco.

Criptografia

Senha Denodo armazenada cifrada. A chave de criptografia não deve ficar no mesmo banco da senha.

Rotação

Permitir troca periódica de senha e invalidação de credenciais antigas.

Teste de conexão

Permitir teste controlado pelo administrador, registrando sucesso/falha sem expor senha.

Auditoria

Registrar quem cadastrou, alterou, testou ou removeu uma credencial, sem gravar o valor da senha.

Menor privilégio

Credencial deve ter apenas permissões necessárias para extração definida no projeto.

Tabela sugerida: app_credenciais_denodo

Campo

Finalidade

id_credencial

Identificador da credencial.

usuario_denodo

Chave/usuário Denodo autorizado.

senha_criptografada

Senha cifrada, nunca em texto claro.

metodo_criptografia

Identificação do mecanismo usado: cofre, keyring, KMS ou criptografia local governada.

ativo

Indica credencial ativa.

dt_criacao / dt_alteracao

Controle temporal.

usuario_responsavel

Administrador responsável pelo cadastro ou alteração.

ultimo_teste_conexao

Data/hora do último teste.

status_ultimo_teste

Sucesso ou falha, sem expor senha.

## 18.6 Pasta docs/ para acompanhamento do desenvolvimento por IA

A pasta docs/ deverá ser usada como camada de governança do desenvolvimento, especialmente quando houver geração ou alteração de código por IA. O objetivo é permitir acompanhamento pelo desenvolvedor, rastreabilidade das decisões, pontos de controle, recuperação em caso de erro e continuidade do projeto.

Arquivo

Finalidade

docs/00_INDICE.md

Mapa dos documentos técnicos e orientação de leitura.

docs/01_CONFIGURACAO_GERAL.md

Variáveis de ambiente, conexões, parâmetros e execução local.

docs/02_ARQUITETURA_E_FLUXO_DADOS.md

Fluxo RAW, PROCESSED, MART, SNAPSHOTS e VALIDACOES.

docs/03_DECISOES_TECNICAS.md

Registro de decisões de arquitetura e justificativas.

docs/04_PROMPTS_IA.md

Prompts usados no Codex/IA e objetivo de cada geração.

docs/05_LOG_DESENVOLVIMENTO_IA.md

Histórico de alterações feitas pela IA, arquivos modificados e riscos.

docs/06_PONTOS_DE_CONTROLE.md

Checkpoints antes/depois de mudanças críticas.

docs/07_PLANO_DE_TESTES.md

Testes funcionais, ETL, data quality, segurança e interface.

docs/08_GUIA_DE_RECUPERACAO.md

Como retornar a um estado estável em caso de travamento ou erro.

docs/09_SEGURANCA_E_SEGREDOS.md

Política de credenciais, .env, cofre, Denodo e mascaramento.

docs/10_CRITERIOS_DE_ACEITACAO.md

Critérios para validar entrega técnica e funcional.

## 18.7 Modelo de notificações por e-mail

As notificações deverão ser parametrizáveis por evento, perfil e competência. A aplicação deve permitir manutenção dos destinatários na aba Admin, respeitando os perfis de acesso.

Tabela

Uso

app_grupos_notificacao

Cadastro de grupos: ADM, POS_OPERACAO, GESTORES, AUDITORIA.

app_usuarios_notificacao

Vínculo entre usuários, e-mails, grupos e situação ativa.

app_notificacoes_eventos

Eventos que disparam e-mail: FALHA_ETL, FECHAMENTO_MES, REABERTURA_MES, PENDENCIA_CRITICA.

app_notificacoes_log

Histórico de e-mails enviados, status, destinatários e erro de envio.

## 18.8 Complemento para o Prompt do Codex - V4

Adicionar à aplicação os seguintes requisitos V4:1. Controle de acesso:- registrar login, logout, IP, hostname, user agent, id_sessao, perfil e tentativas inválidas;- expirar sessão por inatividade;- registrar ações do usuário com correlação à sessão.2. Banco da aplicação:- persistir dados da aplicação no dbGUO/ddcq usando perfil ddcq_user;- criar tabelas app_sessoes_acesso, app_etl_execucao, app_logs_auditoria, app_parametros, app_notificacoes, app_credenciais_denodo e app_validacoes.3. ETL independente:- ETL deve rodar em backend por scheduler, sem depender do Streamlit estar ativo;- Streamlit apenas altera parâmetros e consulta status;- em caso de falha de ETL, enviar e-mail aos usuários administradores.4. Fechamento mensal:- quando o mês for fechado, enviar e-mail aos usuários de pós-operação e gestores;- registrar responsável, data/hora, competência e resumo de pendências.5. Credenciais Denodo:- permitir que administrador cadastre chave e senha Denodo;- nunca salvar senha em texto claro;- armazenar senha criptografada ou usar cofre corporativo;- mascarar senha na interface e nunca registrar em log;- registrar auditoria de criação, alteração, teste e remoção da credencial.6. Pasta docs/:- criar documentação de desenvolvimento gerado por IA;- manter prompts, decisões técnicas, pontos de controle, plano de testes e guia de recuperação.

Versão V4 atualizada em 23/05/2026 16:30

19. Diretriz oficial de filtros por página (atualização 2026-05-27)

Esta diretriz substitui qualquer interpretação anterior de filtros globais em todas as páginas.

## 19.1 Filtros obrigatórios em todas as páginas analíticas

Todas as páginas analíticas da aplicação devem possuir, no mínimo, os filtros:

- competência/mês de análise;
- data;
- conjunto.

## 19.2 Filtros adicionais exclusivos

Os filtros abaixo são obrigatórios apenas nas páginas:

- Data Quality
- Validação Pós-Operação

Filtros adicionais:

- alimentador;
- ocorrência;
- interrupção;
- protocolo;
- causa;
- componente;
- tipo de equipamento;
- equipamento operacional;
- status de validação;
- status de efetivação.

## 19.3 Diretriz de implementação

- Os filtros base (competência, data, conjunto) devem ter comportamento consistente entre páginas.
- Os filtros adicionais devem aparecer apenas nas duas páginas citadas para evitar sobrecarga visual nas demais análises.
- A nomenclatura dos filtros deve seguir PT-BR na interface.
