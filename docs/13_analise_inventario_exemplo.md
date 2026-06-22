# Análise inicial da pasta `exemplo`

## 1. Contexto

A pasta `exemplo` reúne scripts SQL, scripts Python, CSVs de apoio e documentação de projetos anteriores. Mesmo antes da leitura detalhada do conteúdo, o inventário indica que há material útil para amadurecer o ADMStoIQS em três frentes:

1. Regras técnicas de consistência.
2. Estratégia de apuração e análise temporal.
3. Governança, documentação, testes e operação.

Como o objetivo macro do ADMStoIQS é ser um middleware local entre ADMS e IQS, os arquivos de exemplo devem ser usados como base de conhecimento, não copiados diretamente sem adaptação.

## 2. Inventário recebido

Arquivos principais:

```text
exemplo/17_extract_consistencia_iqs_uc_regional.sql
exemplo/21_extract_meta_dia_critico.sql
exemplo/apurador_polars_full.py
exemplo/consumidores.csv
exemplo/extrair_componente_iqshml.py
exemplo/IQS_Analise_sobreposição_HCAI_V3.sql
exemplo/IQS_Consumidores_regional.sql
exemplo/IQS_COnsumidor_faturado_regional.sql
```

Documentação de projeto anterior:

```text
exemplo/docs projeto analise ocorrencia/00_OBJETIVO_PROGRAMA.MD
exemplo/docs projeto analise ocorrencia/01_INDICE.MD
exemplo/docs projeto analise ocorrencia/02_CONFIGURACAO_GERAL.MD
exemplo/docs projeto analise ocorrencia/03_ARQUITETURA_E_FLUXO_DADOS.MD
exemplo/docs projeto analise ocorrencia/04_DECISOES_TECNICAS.MD
exemplo/docs projeto analise ocorrencia/05_PROMPTS_IA.MD
exemplo/docs projeto analise ocorrencia/06_LOG_DESENVOLVIMENTO_IA.MD
exemplo/docs projeto analise ocorrencia/07_PONTOS_DE_CONTROLE.MD
exemplo/docs projeto analise ocorrencia/08_PLANO_DE_TESTES.MD
exemplo/docs projeto analise ocorrencia/09_GUIA_DE_RECUPERACAO.MD
exemplo/docs projeto analise ocorrencia/10_SEGURANCA_E_SEGREDOS.MD
exemplo/docs projeto analise ocorrencia/11_ATUALIZACAO_2026-05-26.md
exemplo/docs projeto analise ocorrencia/11_CRITERIOS_DE_ACEITACAO.MD
exemplo/docs projeto analise ocorrencia/12_ESTILO_PAGINAS_ATRIBUTOS.MD
exemplo/docs projeto analise ocorrencia/13_LOGIN_SENHAS.MD
exemplo/docs projeto analise ocorrencia/14_MASSA_TESTES.MD
exemplo/docs projeto analise ocorrencia/15_VALIDACAO+POS_OPERACAO.md
exemplo/docs projeto analise ocorrencia/16_Consistencia_IQS.md
exemplo/docs projeto analise ocorrencia/17_Regras_dia_critico.MD
exemplo/docs projeto analise ocorrencia/18_API_FASTAPI_FASE1.MD
exemplo/docs projeto analise ocorrencia/19_Analise_temporal.MD
exemplo/docs projeto analise ocorrencia/20_Dias_anomolos.md
exemplo/docs projeto analise ocorrencia/especificacao.md
```

## 3. Classificação preliminar

### 3.1 Reaproveitar com alta prioridade

| Arquivo | Uso provável no ADMStoIQS | Classificação |
|---|---|---|
| `apurador_polars_full.py` | Pode conter uma lógica de apuração completa, provavelmente útil para comparar com o ETL atual DuckDB/Parquet. | Adaptar |
| `IQS_Analise_sobreposição_HCAI_V3.sql` | Deve conter critérios de sobreposição temporal já usados ou validados no contexto IQS/HCAI. | Reaproveitar regra |
| `17_extract_consistencia_iqs_uc_regional.sql` | Pode apoiar validação de UC por regional e consistência de cobertura. | Adaptar |
| `extrair_componente_iqshml.py` | Pode ajudar na regra de causa/componente ausente. | Adaptar |
| `16_Consistencia_IQS.md` | Deve conter regras de consistência já consolidadas. | Reaproveitar documentação |
| `19_Analise_temporal.MD` | Provável base para regras de duração, sobreposição e janelas temporais. | Reaproveitar conceito |
| `15_VALIDACAO+POS_OPERACAO.md` | Pode conter critério de validação pós-operação, alinhado às telas de tratamento. | Reaproveitar regra |

### 3.2 Adaptar para governança e produto

| Arquivo | Uso provável no ADMStoIQS | Classificação |
|---|---|---|
| `03_ARQUITETURA_E_FLUXO_DADOS.MD` | Comparar arquitetura anterior com a esteira local atual. | Adaptar |
| `04_DECISOES_TECNICAS.MD` | Evitar repetir decisões que geraram problemas em banco. | Reaproveitar lições |
| `07_PONTOS_DE_CONTROLE.MD` | Transformar em checklist operacional diário. | Adaptar |
| `08_PLANO_DE_TESTES.MD` | Virar plano de testes do pipeline CSV → Parquet → IQS. | Adaptar |
| `09_GUIA_DE_RECUPERACAO.MD` | Definir recuperação após falha de processamento. | Adaptar |
| `10_SEGURANCA_E_SEGREDOS.MD` | Base para login, senha, perfis e auditoria. | Adaptar |
| `11_CRITERIOS_DE_ACEITACAO.MD` | Transformar em critérios de aceite por sprint. | Adaptar |
| `13_LOGIN_SENHAS.MD` | Apoiar reset de senha e perfis `admin`, `gestor`, `usuario`. | Reaproveitar governança |
| `18_API_FASTAPI_FASE1.MD` | Comparar com a API atual e padronizar contratos. | Adaptar |

### 3.3 Regras futuras ou apoio analítico

| Arquivo | Uso provável no ADMStoIQS | Classificação |
|---|---|---|
| `21_extract_meta_dia_critico.sql` | Pode apoiar regras de exceção por dia crítico. | Inspirar regra futura |
| `17_Regras_dia_critico.MD` | Pode definir flexibilizações de validação em dias críticos. | Inspirar regra futura |
| `20_Dias_anomolos.md` | Apoiar detecção de dias anômalos e alertas. | Inspirar regra futura |
| `IQS_Consumidores_regional.sql` | Referência para cobertura de consumidores por regional. | Adaptar |
| `IQS_COnsumidor_faturado_regional.sql` | Comparar consumidores faturados vs afetados. | Inspirar indicador |
| `consumidores.csv` | Massa auxiliar ou referência de consumidores. | Apoio/teste |

### 3.4 Documentos de contexto

| Arquivo | Uso provável no ADMStoIQS | Classificação |
|---|---|---|
| `00_OBJETIVO_PROGRAMA.MD` | Comparar objetivo anterior com middleware atual. | Contexto |
| `01_INDICE.MD` | Apoio para reorganizar documentação. | Contexto |
| `02_CONFIGURACAO_GERAL.MD` | Pode conter padrões de caminhos/config. | Adaptar |
| `05_PROMPTS_IA.MD` | Histórico de construção, menos crítico para execução. | Referência |
| `06_LOG_DESENVOLVIMENTO_IA.MD` | Histórico, útil para decisões. | Referência |
| `11_ATUALIZACAO_2026-05-26.md` | Pode conter mudanças recentes relevantes. | Avaliar |
| `12_ESTILO_PAGINAS_ATRIBUTOS.MD` | Apoio ao frontend atual. | Adaptar |
| `14_MASSA_TESTES.MD` | Apoio aos testes e massa mínima. | Adaptar |
| `especificacao.md` | Pode ter regras consolidadas do projeto anterior. | Avaliar com prioridade |

## 4. Como isso muda a visão do ADMStoIQS

O inventário reforça que o ADMStoIQS não deve ser apenas um conversor CSV → Parquet → CSV. Ele deve se tornar uma esteira de preparação IQS com três camadas:

### 4.1 Camada operacional

Responsável por:

- ingestão incremental;
- deduplicação;
- UNION;
- apuração mensal;
- geração de CSV final.

Arquivos de exemplo relacionados:

- `apurador_polars_full.py`
- `03_ARQUITETURA_E_FLUXO_DADOS.MD`
- `04_DECISOES_TECNICAS.MD`

### 4.2 Camada de consistência

Responsável por:

- horário negativo;
- sobreposição por equipamento;
- sobreposição por UC;
- causa/componente ausentes;
- consistência regional;
- consumidores inconsistentes;
- dias críticos/anômalos.

Arquivos de exemplo relacionados:

- `IQS_Analise_sobreposição_HCAI_V3.sql`
- `17_extract_consistencia_iqs_uc_regional.sql`
- `16_Consistencia_IQS.md`
- `19_Analise_temporal.MD`
- `21_extract_meta_dia_critico.sql`
- `17_Regras_dia_critico.MD`

### 4.3 Camada de governança

Responsável por:

- login;
- perfil;
- reset de senha;
- aprovação;
- rejeição;
- auditoria;
- justificativa;
- recuperação após falha.

Arquivos de exemplo relacionados:

- `07_PONTOS_DE_CONTROLE.MD`
- `08_PLANO_DE_TESTES.MD`
- `09_GUIA_DE_RECUPERACAO.MD`
- `10_SEGURANCA_E_SEGREDOS.MD`
- `11_CRITERIOS_DE_ACEITACAO.MD`
- `13_LOGIN_SENHAS.MD`

## 5. Proposta de incorporação no projeto atual

### Fase 1 — Ler e extrair regras dos exemplos

Criar um documento de extração:

```text
docs/14_regras_extraidas_exemplos.md
```

Cada regra deve ser descrita assim:

```text
Nome da regra:
Fonte:
Campos usados:
Grão da análise:
Critério:
Ação sugerida:
Risco:
Pode automatizar:
Precisa aprovação:
Impacto no CSV IQS:
```

### Fase 2 — Separar regras em serviços

Criar estrutura:

```text
backend/app/rules/
  horario_negativo.py
  sobreposicao_equipamento.py
  sobreposicao_uc.py
  causa_componente.py
  consistencia_regional.py
  dia_critico.py
```

Cada regra deve ter:

- consulta de pendências;
- contagem para card;
- sugestão de alteração;
- payload de auditoria;
- aplicação controlada.

### Fase 3 — Criar mart de pendências

Para desempenho, em vez de recalcular todas as regras na abertura da tela:

```text
data/mart/apuracao/pendencias_APURACAO_[anomes].parquet
```

Colunas sugeridas:

```text
anomes
regra
gravidade
chave_evento
chave_registro
num_seq_intrp
num_intrp_uci
num_oper_chv_intrp
regional_origem
campo_sugerido
valor_original
valor_sugerido
acao_sugerida
status_pendencia
justificativa_sistema
```

Isso deixaria o frontend muito mais leve.

### Fase 4 — Aplicar decisões de forma governada

As decisões dos usuários não devem alterar diretamente o arquivo original. O fluxo recomendado:

```text
APURACAO original
  + log_alteracoes
  -> APURACAO corrigida
  -> CSV final IQS
```

Arquivos:

```text
agrupamento_oms_APURACAO_202605.parquet
log_alteracoes.parquet
agrupamento_oms_APURACAO_202605_CORRIGIDO.parquet
```

### Fase 5 — Rotina diária única

Criar comando operacional:

```cmd
python -m backend.scripts.rotina_diaria --anomes 202605
```

Etapas:

1. verificar CSV pendente;
2. processar CSV pendente;
3. atualizar UNION;
4. gerar apuração mensal;
5. materializar pendências;
6. materializar resumo;
7. gerar relatório operacional.

## 6. Prioridade sugerida de leitura detalhada

Quando for possível analisar o conteúdo dos arquivos, a ordem recomendada é:

1. `exemplo/apurador_polars_full.py`
2. `exemplo/IQS_Analise_sobreposição_HCAI_V3.sql`
3. `exemplo/docs projeto analise ocorrencia/19_Analise_temporal.MD`
4. `exemplo/docs projeto analise ocorrencia/16_Consistencia_IQS.md`
5. `exemplo/docs projeto analise ocorrencia/15_VALIDACAO+POS_OPERACAO.md`
6. `exemplo/extrair_componente_iqshml.py`
7. `exemplo/17_extract_consistencia_iqs_uc_regional.sql`
8. `exemplo/docs projeto analise ocorrencia/13_LOGIN_SENHAS.MD`
9. `exemplo/docs projeto analise ocorrencia/08_PLANO_DE_TESTES.MD`
10. `exemplo/docs projeto analise ocorrencia/09_GUIA_DE_RECUPERACAO.MD`

## 7. Risco principal identificado

O maior risco atual é misturar grãos de análise:

- UC;
- interrupção;
- equipamento;
- ocorrência;
- apuração mensal;
- arquivo regional.

Esse risco já apareceu na regra de horário negativo, onde havia milhares de UCs, mas poucas interrupções distintas. A arquitetura deve assumir explicitamente o grão de cada regra.

## 8. Decisão recomendada

Antes de continuar criando novas telas, recomenda-se introduzir uma camada de pendências materializadas por regra.

Essa camada resolve três problemas:

1. O dashboard fica rápido.
2. As páginas mostram a quantidade certa.
3. A governança fica mais simples, porque cada pendência tem chave, regra, sugestão e status.

## 9. Próximo passo recomendado

Ler detalhadamente os três arquivos de maior impacto:

```text
apurador_polars_full.py
IQS_Analise_sobreposição_HCAI_V3.sql
19_Analise_temporal.MD
```

Depois disso, revisar a modelagem das pendências antes de implementar novas regras no frontend.

