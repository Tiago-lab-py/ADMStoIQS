# 15_VALIDACAO+POS_OPERACAO

## Visão geral
A tela **15_VALIDACAO+POS_OPERACAO** é um atalho de navegação para a página principal de validação pós-operação.

- Arquivo de atalho: `app/pages/15_VALIDACAO+POS_OPERACAO.py`
- Implementação da lógica: `app/pages/6_Validacao_Pos_Operacao.py`

Ou seja: a página `15_...` reutiliza integralmente a mesma lógica e interface da página `6_...`.

## Objetivo da tela
Permitir que o usuário:

1. Consulte a base de validações de pós-operação.
2. Selecione um registro para análise.
3. Atualize status de validação, comentário e campos JSON de revisão.
4. Tenha apoio operacional por alimentador + data para decidir validação/alteração/cancelamento.

## Estrutura da interface
A tela é composta por:

1. **Tabela geral de validações**
- Exibe os registros da base `dados/validacoes/app_validacoes.parquet`.
- As colunas de JSON ficam ocultas nessa tabela inicial para facilitar leitura.

2. **Janela de interação para avaliação e atualização**
- Busca por `ID validação`.
- Busca por `NUMERO_OCORRENCIA`.
- Carregamento do registro selecionado para edição.
- Exibição de timeline das interrupções da ocorrência selecionada.

### Regra de filtros da página
Por diretriz oficial do projeto, esta página (Validação Pós-Operação) deve conter:

- Filtros base: competência/mês de análise, data e conjunto.
- Filtros adicionais: alimentador, ocorrência, interrupção, protocolo, causa, componente, tipo de equipamento, equipamento operacional, status de validação e status de efetivação.

3. **Edição do registro (modal ou inline)**
- Quando suportado pelo ambiente Streamlit, a edição abre em **modal**.
- Caso contrário, usa o modo **inline** (alternativo).

## Modelo de validação por campo (tripla visão)
Para cada campo de ajuste, a tela opera com três visões:

- **Original**: valor vindo de `campos_originais_json`.
- **Sugerido**: valor anteriormente proposto (estado anterior do registro).
- **Editado**: valor final salvo pelo analista no momento da atualização.

Regra: o valor original não é sobrescrito; cada alteração é registrada em histórico por campo.

## Persistência e trilha por campo
Ao salvar alterações:

1. A aplicação valida os JSONs informados.
2. Atualiza o registro no `app_validacoes.parquet`.
3. Realiza `upsert` do estado atual em `ddcq.aap_ao_app_validacoes`.
4. Persiste histórico por campo em `ddcq.aap_ao_app_historico_campo` com:
   - `id_validacao`, `chave_evento`, `campo`
   - `valor_original`, `valor_sugerido`, `valor_editado`
   - `usuario`, `perfil`, `sessao_id`, `ip`, `hostname`
   - `motivo`, `status_anterior`, `status_novo`, `competencia`, `dt_evento`
5. Persiste auditoria detalhada em `ddcq.aap_ao_app_logs_auditoria`.

## Regras de bloqueio por fechamento mensal
A atualização respeita bloqueio de competência fechada por duas fontes:

- Configuração global (`config/app_config.yml`)
- Registro formal no dbGUO (`ddcq.aap_ao_app_fechamento_mensal`)

Comportamento:
- Usuário não-admin: bloqueado em competência fechada.
- Admin: pode alterar, e deve usar reabertura formal auditada na página Admin.

## Timeline da ocorrência
Ao selecionar um registro, a tela monta a timeline das interrupções da ocorrência:

1. **Eixo X**: data/hora (`DT_INI` a `DT_FIM`).
2. **Eixo Y**: número da interrupção (`NUM_INTERRUPCAO`).
3. **Cor da barra**: `TIPO_PROTOCOLO`.
4. **Hover (tooltip)**: dados detalhados da interrupção.

## Painel de apoio por alimentador + data
A tela calcula contexto operacional por `alimentador + data` da interrupção de referência, exibindo:

- quantidade de ocorrências relacionadas;
- quantidade de interrupções relacionadas;
- quantidade de serviços relacionados;
- quantidade de reclamações relacionadas.

Também disponibiliza tabelas de apoio para:
- ocorrências relacionadas;
- interrupções relacionadas;
- serviços relacionados;
- reclamações relacionadas.

Para reclamações, quando disponível, a aplicação usa `topologia_uc` para mapear UC -> alimentador.

## Observações operacionais
- Se a base de validações não existir, a tela orienta executar o ETL.
- Se não houver dados suficientes para montar o painel de apoio, a tela informa o motivo sem quebrar o fluxo de validação.
- Em tabelas muito grandes, a visualização pode ser limitada para performance, mas o download mantém os dados completos.