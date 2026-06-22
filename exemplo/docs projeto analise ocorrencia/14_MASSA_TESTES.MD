# Massa de Testes

## Objetivo
Definir a massa minima e os cenarios essenciais para validar a plataforma de pos-operacao de ponta a ponta (ETL, regras, dashboards e fluxo operacional).

## Fontes obrigatorias
1. Interrupcoes (`DIS.INTERRUPCAO` ou equivalente)
2. Servicos (`DIS.SERVICOS` ou equivalente)

## Fontes recomendadas
1. Cadastro de conjuntos
2. Tabela de protocolos (0, 1, 6 e regras)
3. Reclamacoes por UC
4. Topologia (UC/conjunto/alimentador)
5. Base de efetivacao (comparador)

## Campos minimos obrigatorios
### Interrupcoes
- `NUM_INTERRUPCAO`
- `NUMERO_OCORRENCIA`
- `DT_INI`
- `DT_FIM`
- `COD_CONJUNTO`
- `NAME_CONJUNTO`
- `TIPO_PROTOCOLO`
- `NUM_PROTOCOLO`
- `TIPO_EQUIPAMENTO`
- `NUM_OPERACIONAL_EQUIPAMENTO`
- `COD_CAUSA`, `CAUSA`
- `COD_COMPONENTE`, `COMPONENTE`
- `CI_URBANO`, `CI_RURAL`
- `CHI_URBANO`, `CHI_RURAL`
- `CI_EXP_URBANO`, `CI_EXP_RURAL`
- `CHI_EXP_URBANO`, `CHI_EXP_RURAL`

### Servicos
- `NUMERO_OCORRENCIA`
- `DATA_SERVICO`
- `DESCRICAO_SERVICO`
- `EQUIPE`
- `TIPO_SERVICO`
- `STATUS_SERVICO`

## Volume minimo sugerido
1. 3 meses de dados correntes (ex.: 2026-03 a 2026-05)
2. Historico 2024 e 2025 para baseline estatistico
3. Pelo menos:
   - 50.000 interrupcoes
   - 30.000 ocorrencias
   - 20.000 servicos

## Cenarios criticos que a massa deve conter
1. Protocolo `0` com coexistencia de `1` e/ou `6` na mesma ocorrencia/conjunto
2. Registros com `DT_FIM < DT_INI` (erro critico DQ)
3. Duracao menor que 3 minutos em eventos sobrepostos
4. Casos de CHI elevado (>= 2.000) para revisao obrigatoria
5. Ocorrencias com sobreposicao temporal real
6. Casos ISE (`TIPO_PROTOCOLO = 6`) com variabilidade de causa/componente/equipamento
7. Casos de alteracao/cancelamento para validar trilha de auditoria

## Checklist de validacao da massa
- [ ] Chaves tecnicas sem null: `NUM_INTERRUPCAO`, `NUMERO_OCORRENCIA`
- [ ] Datas validas em `DT_INI` e `DT_FIM`
- [ ] Protocolos dentro do dominio esperado
- [ ] Campos numericos de CI/CHI parseando corretamente
- [ ] Servicos vinculando com ocorrencias existentes
- [ ] Distribuicao suficiente de conjuntos e regionais
- [ ] Casos de excecao presentes (DQ, ISE, sobreposicao)

## Criterio de pronto da massa
1. ETL executa sem erro no periodo alvo
2. Marts principais gerados com volumetria consistente
3. Dashboard executivo e paginas operacionais carregam sem falha
4. Regras criticas (DQ/protocolo/ISE) aparecem com evidencia nos dados
5. Exportacoes CSV/Parquet funcionam com dados reais

## Evidencias recomendadas
1. Print/registro da execucao ETL
2. Contagem de linhas por camada (`raw`, `processed`, `mart`)
3. Lista de casos criticos encontrados (amostra)
4. Print das telas com classificacoes e legendas ativas
