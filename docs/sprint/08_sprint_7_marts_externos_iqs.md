# Sprint 7 — Marts externos IQS e enriquecimento da apuração

## 1. Objetivo

Complementar a apuração OMS/ADMS com dados do IQS, usando credenciais via `.env` e materializando os marts externos necessários em Parquet local.

Nesta sprint, a extração OMS não será redesenhada. Ela será tratada como estabilizada.

## 2. Documento base

```text
docs/17_marts_externos_iqs.md
```

## 3. Escopo

### 3.1 Configuração

- Criar `.env.example`.
- Criar leitor seguro das variáveis:

```text
IQS_UID
IQS_PWD
IQS_DB
IQS_CONFIG_DIR
```

- Criar script de validação sem expor senha.
- Validar diretório Oracle/TNS.

### 3.2 Extração IQS

Criar serviço para executar consultas IQS e salvar Parquet bruto:

```text
data/external/iqs/raw/
```

Fontes iniciais:

- UC regional;
- consumidores regional;
- consumidor faturado regional;
- componentes;
- dia crítico/meta.

### 3.3 Materialização IQS

Criar marts tratados:

```text
data/external/iqs/mart/
```

### 3.4 Enriquecimento da apuração

Criar:

```text
data/mart/enriquecido/apuracao_iqs_enriquecida_[anomes].parquet
```

### 3.5 Logs

Criar:

```text
data/logs/log_extracao_iqs.parquet
```

## 4. Fora de escopo

Não faz parte desta sprint:

- alterar ingestão CSV OMS;
- alterar deduplicação OMS;
- implementar cálculo oficial de ressarcimento;
- publicar dados em banco;
- subir dados para GitHub.

## 5. Entregáveis backend

- `backend/app/core/iqs_settings.py`
- `backend/scripts/validar_iqs_env.py`
- `backend/scripts/testar_conexao_iqs.py`
- `backend/scripts/extrair_iqs.py`
- `backend/scripts/extrair_iqs_exemplo.py`
- `backend/app/sql/iqs/teste_dual.sql`
- `backend/app/services/iqs_extraction_service.py`
- `backend/app/services/iqs_mart_service.py`
- `backend/app/services/iqs_mart_service.py`
- `backend/app/services/apuracao_enrichment_service.py`
- `backend/scripts/extrair_iqs.py`
- `backend/scripts/extrair_iqs_exemplo.py`
- `backend/scripts/materializar_marts_iqs.py`
- `backend/scripts/enriquecer_apuracao_iqs.py`
 - `frontend/public/gestor-preview.html`

## 6. Entregáveis de documentação

- Atualizar `docs/17_marts_externos_iqs.md`.
- Atualizar checklist operacional.
- Documentar SQLs utilizados.
- Documentar logs gerados.

## 7. Critérios de aceite

- `.env.example` existe sem senha real.
- `.env` local carrega `IQS_UID`, `IQS_PWD` e `IQS_DB`.
- O script `validar_iqs_env` mascara a senha.
- Nenhum dado IQS é versionado.
- Extrações salvam Parquet local.
- Logs registram status da extração.
- Apuração enriquecida é gerada por mês.

## 8. Dependências

Antes de codificar a extração real, confirmar:

- driver necessário para `MIRA.world`;
- diretório `IQS_CONFIG_DIR`;
- existência do `tnsnames.ora`;
- string de conexão;
- se `IQS_UID=admiqs` tem permissão de leitura;
- SQLs oficiais a executar;
- volume esperado de retorno;
- janela operacional permitida.

## 9. Checklist

- [ ] Criar `.env` local com senha.
- [ ] Incluir `IQS_CONFIG_DIR=C:\APL\Oracle12_32\12CR2\network\admin`.
- [ ] Rodar `python -m backend.scripts.validar_iqs_env`.
- [ ] Rodar `python -m backend.scripts.testar_conexao_iqs`.
- [ ] Rodar `python -m backend.scripts.extrair_iqs --anomes 202605 --consulta teste_dual`.
- [ ] Rodar `python -m backend.scripts.extrair_iqs_exemplo --anomes 202605 --consulta consumidores_regional`.
- [ ] Rodar `python -m backend.scripts.extrair_iqs_exemplo --anomes 2026 --consulta metas_uc` somente sob demanda anual.
- [ ] Confirmar driver de conexão Oracle IQS.
- [ ] Confirmar alias `MIRA.world` no `tnsnames.ora`.
- [ ] Ler `extrair_componente_iqshml.py`.
- [ ] Ler SQLs de consumidores/regional.
- [ ] Criar serviço de conexão.
- [ ] Criar extração UC regional.
- [ ] Criar extração consumidores.
- [ ] Criar extração componentes.
- [ ] Criar log de extração.
- [ ] Criar marts tratados.
- [ ] Criar apuração enriquecida.
- [ ] Abrir prévia em `http://127.0.0.1:5173/gestor-preview.html`.

## 10. Atualização de fonte IQS

A fonte antiga `meta_dia_critico` foi substituída por:

```text
metas_uc -> exemplo/IQS_METAS UC 2026.sql
```

O mart esperado passa a ser:

```text
data/external/iqs/raw/metas_uc_[anomes].parquet
data/external/iqs/mart/mart_metas_uc_[anomes].parquet
```

Importante:

```text
metas_uc
```

é uma fonte anual pesada e não deve participar da materialização mensal geral.

Ela deve ser processada apenas por chamada explícita:

```text
POST /iqs/materializar-fonte/metas_uc/2026
```
