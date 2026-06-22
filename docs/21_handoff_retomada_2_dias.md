# Handoff — retomada do desenvolvimento em 2 dias

## 1. Estado atual do projeto

O ADMStoIQS está evoluindo para um middleware local entre ADMS e IQS.

Objetivo macro:

```text
CSV ADMS
  -> Parquet OMS mensal
  -> UNION OMS
  -> Apuração mensal
  -> Enriquecimento IQS
  -> Pendências materializadas
  -> Governança de correção
  -> CSV final IQS
```

## 2. Decisões consolidadas

### 2.1 Extração OMS

A extração OMS/ADMS está adequada neste momento.

Não deve ser redesenhada agora.

O foco passa a ser:

- marts externos;
- IQS;
- pendências materializadas;
- dashboard executivo;
- governança de decisão;
- exportação final IQS.

### 2.2 Execução local

O projeto segue local, sem banco central:

- CSV como entrada/saída;
- Parquet como camada operacional;
- DuckDB como motor de consulta;
- logs em Parquet.

### 2.3 IQS

Conexão Oracle validada:

```text
Driver: oracledb
DSN: MIRA.world
TNS_ADMIN: C:\APL\Oracle12_32\12CR2\network\admin
SELECT 1 FROM DUAL: OK
```

Configuração via `.env`:

```env
IQS_UID=admiqs
IQS_PWD=
IQS_DB=MIRA.world
IQS_CONFIG_DIR=C:\APL\Oracle12_32\12CR2\network\admin
```

Não versionar `.env`.

### 2.4 `metas_uc`

A fonte:

```text
exemplo/IQS_METAS UC 2026.sql
```

foi mapeada como:

```text
metas_uc
```

Ela é uma dimensão anual pesada, com aproximadamente 6 milhões de registros.

Decisão:

- não entra na rotina mensal;
- não entra no botão geral de atualização dos marts IQS;
- deve ser extraída/materializada somente sob demanda.

## 3. Arquivos relevantes criados/alterados

### 3.1 IQS

```text
backend/app/core/iqs_settings.py
backend/app/services/iqs_connection_service.py
backend/app/services/iqs_extraction_service.py
backend/app/services/iqs_mart_service.py
backend/app/api/iqs_routes.py
backend/scripts/validar_iqs_env.py
backend/scripts/testar_conexao_iqs.py
backend/scripts/extrair_iqs.py
backend/scripts/extrair_iqs_exemplo.py
backend/scripts/materializar_marts_iqs.py
backend/app/sql/iqs/teste_dual.sql
```

### 3.2 Pendências materializadas

```text
backend/app/services/pendencias_apuracao_service.py
backend/app/api/pendencias_routes.py
backend/scripts/materializar_pendencias_apuracao.py
```

### 3.3 Frontend / prévia gestor

```text
frontend/public/gestor-preview.html
```

### 3.4 Documentação

```text
docs/17_marts_externos_iqs.md
docs/18_plano_tecnico_servicos_iqs.md
docs/19_previa_gestor.md
docs/20_pendencias_materializadas_apuracao.md
docs/21_handoff_retomada_2_dias.md
docs/sprint/08_sprint_7_marts_externos_iqs.md
```

## 4. Comandos úteis

### 4.1 Validar IQS

```cmd
python -m backend.scripts.validar_iqs_env
python -m backend.scripts.testar_conexao_iqs
```

### 4.2 Teste mínimo IQS

```cmd
python -m backend.scripts.extrair_iqs --anomes 202605 --consulta teste_dual
```

### 4.3 Extrações IQS mensais já testadas

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidores_regional
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidor_faturado_regional
python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consistencia_uc_regional
```

### 4.4 Extração anual sob demanda

```cmd
python -m backend.scripts.extrair_iqs_exemplo --anomes 2026 --consulta metas_uc
```

Observação:

- usar `2026`, não `202605`;
- esta extração é pesada;
- não deve rodar diariamente.

### 4.5 Materializar marts IQS mensais

```cmd
python -m backend.scripts.materializar_marts_iqs --anomes 202605
```

Ou pela API:

```text
POST /iqs/materializar/202605
```

### 4.6 Materializar `metas_uc` sob demanda

```text
POST /iqs/materializar-fonte/metas_uc/2026
```

### 4.7 Materializar pendências

```cmd
python -m backend.scripts.materializar_pendencias_apuracao --anomes 202605
```

Ou pela API:

```text
POST /apuracao/pendencias/materializar/202605
```

### 4.8 Rodar API

```cmd
python -m backend.scripts.run_api
```

### 4.9 Rodar frontend

```cmd
cd D:\ADMStoIQS\frontend
dev.cmd
```

### 4.10 Abrir prévia gestor

```text
http://127.0.0.1:5173/gestor-preview.html
```

## 5. Endpoints úteis

```text
GET  /
GET  /iqs/config
GET  /iqs/raw
GET  /iqs/resumo
GET  /iqs/resumo?refresh=true&anomes=202605
POST /iqs/materializar/202605
POST /iqs/materializar-fonte/metas_uc/2026
GET  /apuracao/pendencias/resumo
GET  /apuracao/pendencias?limit=100&offset=0
POST /apuracao/pendencias/materializar/202605
```

## 6. Estado das extrações IQS

Já extraídas com sucesso:

```text
consumidores_regional_202605.parquet
consumidor_faturado_regional_202605.parquet
consistencia_uc_regional_202605.parquet
teste_dual_202605.parquet
```

Em andamento / pesada:

```text
metas_uc_2026.parquet
```

Pendentes ou futuras:

```text
sobreposicao_hcai
componentes IQS
```

## 7. Pontos de atenção

### 7.1 Reiniciar API após patches

Sempre reiniciar:

```cmd
python -m backend.scripts.run_api
```

antes de testar novos endpoints.

### 7.2 Resumo IQS antigo

Se `/iqs/resumo` mostrar dados antigos, forçar:

```text
http://127.0.0.1:8000/iqs/resumo?refresh=true&anomes=202605
```

### 7.3 `metas_uc`

Não deve entrar em:

- rotina diária;
- rotina mensal;
- botão geral `Atualizar marts IQS`.

Deve ter botão próprio futuramente:

```text
Atualizar metas UC anual
```

### 7.4 GitHub

Antes de subir ao GitHub, garantir que não serão versionados:

```text
data/
data/external/
.env
.venv/
node_modules/
*.parquet
*.csv
```

## 8. Próxima sequência recomendada

### Passo 1 — Fechar marts IQS mensais

- testar `GET /iqs/resumo?refresh=true&anomes=202605`;
- confirmar 3 fontes processadas;
- confirmar 1 fonte pendente `sobreposicao_hcai`;
- confirmar que `metas_uc` não aparece no refresh mensal.

### Passo 2 — Fechar pendências materializadas

- rodar `materializar_pendencias_apuracao`;
- validar `/apuracao/pendencias/resumo`;
- ajustar contagens se necessário.

### Passo 3 — Separar visualmente a prévia

Na `gestor-preview.html`, separar:

- tabela de marts IQS;
- tabela de pendências OMS;
- bloco regulatório futuro.

### Passo 4 — Criar dashboard executivo integrado

Migrar a prévia para o app React principal usando o design system.

### Passo 5 — Próxima regra

Escolher uma:

- sobreposição HCAI/IQS;
- componente ausente via IQS;
- indicadores DEC/FEC;
- ressarcimento DIC/FIC/DMIC.

## 9. Mensagem para retomar

Na retomada, começar por:

```text
Vamos continuar a partir do docs/21_handoff_retomada_2_dias.md.
Primeiro validar /iqs/resumo?refresh=true&anomes=202605 e depois fechar pendências materializadas.
```

