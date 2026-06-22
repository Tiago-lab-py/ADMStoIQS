# Checklist complementar — estabilização do ADMStoIQS

## 1. Decisões antes de continuar codificando

- [ ] Aprovar o design system em `docs/14_design_system_layout.md`.
- [ ] Definir destino do repositório remoto: GitHub privado, GitHub Enterprise ou Azure DevOps.
- [ ] Confirmar que dados locais não serão versionados.
- [ ] Confirmar se a próxima sprint será Design System ou Pendências Materializadas.

## 2. Ordem recomendada

### Passo 1 — Segurança de versionamento

- [ ] Criar `.gitignore`.
- [ ] Verificar `git status`.
- [ ] Subir somente código e documentação.
- [ ] Criar branch `develop`.

### Passo 2 — Configurar IQS com segurança

- [ ] Criar `.env` local a partir de `.env.example`.
- [ ] Preencher `IQS_PWD` somente no `.env` local.
- [ ] Rodar `python -m backend.scripts.validar_iqs_env`.
- [ ] Confirmar driver/conector para `MIRA.world`.
- [ ] Confirmar permissões de leitura do usuário `admiqs`.
- [ ] Garantir que `data/external/` não será versionado.

### Passo 3 — Congelar layout

- [ ] Criar componentes visuais padrão.
- [ ] Migrar sidebar.
- [ ] Migrar cabeçalho.
- [ ] Migrar cards.
- [ ] Migrar tabelas.
- [ ] Migrar painel de decisão.

### Passo 4 — Criar camada de marts externos IQS

- [ ] Extrair UC regional.
- [ ] Extrair consumidores regional.
- [ ] Extrair consumidor faturado regional.
- [ ] Extrair componentes IQS.
- [ ] Extrair meta/dia crítico.
- [ ] Salvar Parquets brutos em `data/external/iqs/raw`.
- [ ] Salvar marts tratados em `data/external/iqs/mart`.
- [ ] Criar `log_extracao_iqs.parquet`.

### Passo 5 — Criar camada de pendências

- [ ] Criar `pendencias_APURACAO_[anomes].parquet`.
- [ ] Materializar horário negativo por `NUM_SEQ_INTRP`.
- [ ] Materializar sobreposição por equipamento.
- [ ] Materializar causa/componente.
- [ ] Atualizar resumo a partir das pendências.

### Passo 6 — Evoluir dashboard executivo

- [ ] Cards operacionais.
- [ ] Cards regulatórios.
- [ ] DEC/FEC antes e depois.
- [ ] Ressarcimento estimado antes e depois.
- [ ] Rejeitados por atividade.

### Passo 7 — Regras regulatórias

- [ ] Validar metodologia PRODIST Módulo 8 vigente.
- [ ] Definir fórmula DIC/FIC/DMIC.
- [ ] Definir regra de compensação/ressarcimento.
- [ ] Separar valor estimado de valor oficial.

## 3. Comandos úteis

API:

```cmd
python -m backend.scripts.run_api
```

Frontend:

```cmd
cd D:\ADMStoIQS\frontend
dev.cmd
```

Resumo:

```cmd
python -m backend.scripts.materializar_resumo_apuracao --anomes 202605
```

IQS:

```cmd
python -m backend.scripts.validar_iqs_env
```

Git:

```cmd
git status --short
```

## 4. Atenção permanente

Não versionar:

- `data/`
- `data/external/`
- `.venv/`
- `node_modules/`
- CSVs;
- Parquets;
- logs operacionais;
- `.env`;
- arquivos com senha/token.

## 5. Próxima decisão sugerida

Antes de continuar regras novas, executar:

```text
Sprint 6 — Versionamento, segurança e governança de desenvolvimento
```

Depois:

```text
Sprint 7 — Marts externos IQS e enriquecimento da apuração
```

Depois:

```text
Sprint 4 — Design system e estabilização do frontend
```

Em seguida:

```text
Sprint 5 — Pendências materializadas e dashboard regulatório
```

Essa ordem reduz risco de perder trabalho, estabiliza o visual e só então aprofunda regras complexas.

## 6. Retomada em 2 dias

Documento de referência:

```text
docs/21_handoff_retomada_2_dias.md
```

Sequência recomendada:

- [ ] Ler `docs/21_handoff_retomada_2_dias.md`.
- [ ] Reiniciar API.
- [ ] Validar `GET /iqs/resumo?refresh=true&anomes=202605`.
- [ ] Confirmar que `metas_uc` não entra no refresh mensal.
- [ ] Materializar pendências da apuração.
- [ ] Validar `GET /apuracao/pendencias/resumo`.
- [ ] Separar na prévia a tabela de IQS e a tabela de pendências.
- [ ] Planejar migração da prévia para Dashboard Executivo React.
