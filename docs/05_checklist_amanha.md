# Checklist para Amanhã

## Estado Atual

- API FastAPI sobe com sucesso em `http://127.0.0.1:8000`.
- Swagger disponível em `http://127.0.0.1:8000/docs`.
- Frontend Vite sobe em `http://127.0.0.1:5173`.
- Login funcional:
  - `admin/admin123`
  - `gestor/gestor123`
  - `usuario/usuario123`
- Mart único ativo:
  - `data/mart/agrupamento_oms_UNION.parquet`
- Mart consolidado:
  - `data/mart/agrupamento_oms_UNION.parquet`
- Apuração mensal:
  - `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes].parquet`
- Corrigido passa a ser por apuração:
  - `data/mart/apuracao/agrupamento_oms_APURACAO_[anomes]_corrigido.parquet`
- Endpoints de governança aparecem no Swagger.

## Comandos de Partida

### API

```cmd
cd D:\ADMStoIQS
d:\ADMStoIQS\.venv\Scripts\activate.bat
python -m backend.scripts.run_api
```

### Frontend

Em outro terminal:

```cmd
cd D:\ADMStoIQS\frontend
dev.cmd
```

### Regenerar Corrigido da Apuração

```cmd
cd D:\ADMStoIQS
d:\ADMStoIQS\.venv\Scripts\activate.bat
python -m backend.scripts.gerar_oms_corrigido
```

## Testes de Amanhã

### 1. Validar Leitura

- Abrir frontend.
- Fazer login com `admin/admin123`.
- Confirmar dropdown:

```text
UNION · agrupamento_oms_UNION_corrigido.parquet
```

- Clicar em `Atualizar`.
- Confirmar carregamento de registros.

### 2. Testar Decisão de Registro

No Swagger:

```text
POST /registros/{chave_registro}/validar
POST /registros/{chave_registro}/rejeitar
POST /registros/{chave_registro}/ignorar-regra
```

Usar chave no formato:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

Body exemplo:

```json
{
  "usuario": "admin",
  "perfil": "admin",
  "justificativa": "Teste de governança do registro"
}
```

Depois regenerar:

```cmd
python -m backend.scripts.gerar_oms_corrigido
```

### 3. Verificar Colunas de Governança

Confirmar no parquet corrigido:

- `validado`
- `status_validacao`
- `motivo_status`
- `usuario_validacao`
- `data_hora_validacao`

### 4. Testar Exportação

- Rejeitar um registro.
- Regenerar o corrigido.
- Exportar CSV regional.
- Confirmar que `status_validacao = rejeitado` não entra na exportação.

## Próximas Implementações

### Frontend

- Botões iniciais adicionados:
  - `Validar`
  - `Rejeitar`
  - `Ignorar regra`
  - `Regenerar corrigido`
- Justificativa obrigatória antes de registrar decisão.
- Registro selecionado usa chave:

```text
NUM_INTRP_UCI|NUM_POSTO_UCI|NUM_UC_UCI
```

- Tabela prioriza colunas de status, chave, datas e duração.

### Backend

- Endpoint de resumo criado:

```text
GET /mart/resumo
```

Com contadores:

- total de registros;
- pendentes;
- validados;
- rejeitados;
- ignorados;
- aplicados;
- horário negativo;
- sobreposições.

Observação:

- O resumo inicial já cobre total, pendentes, validados, rejeitados, ignorados, aplicados, horário negativo, duração longa e causa/componente ausente.
- Contadores pesados de sobreposição podem ser adicionados depois com rotina própria para evitar lentidão no dashboard.

### Governança

- Implementar cadastro real de usuários.
- Implementar reset de senha no primeiro acesso.
- Separar permissões por perfil:
  - `admin`
  - `gestor`
  - `usuario`

## Observações

- `UNION` é competência lógica, não mês.
- `ANOMES_PROCESSAMENTO` é apenas rastreabilidade interna.
- O objetivo da ferramenta é reduzir análise manual, não forçar correção automática em casos ambíguos.
- Decisões do analista devem prevalecer e ficar registradas no log.

## Teste da Interface Governada

1. Subir API e frontend.
2. Login com `admin/admin123`.
3. Abrir `Preparar apuração`.
4. Informar mês, por exemplo `202605`.
5. Clicar em `Verificar CSV pendente`.
6. Se houver pendências, clicar em `Processar CSV pendente`.
7. Clicar em `Atualizar OMS UNION` se precisar renovar o consolidado.
8. Clicar em `Gerar apuração mensal`.
9. Confirmar geração de `data/mart/apuracao/agrupamento_oms_APURACAO_202605.parquet`.
10. Ir para o dashboard.
11. Clicar em uma fila, por exemplo `Horário negativo`.
12. Selecionar uma linha na tabela.
13. Preencher justificativa.
14. Clicar em `Validar`, `Rejeitar` ou `Ignorar regra`.
15. Clicar em `Regenerar corrigido`.
16. Confirmar geração de `data/mart/apuracao/agrupamento_oms_APURACAO_202605_corrigido.parquet`.
17. Clicar em `Atualizar`.

## Nova Etapa Antes do Dashboard

Documento:

```text
docs/06_etl_apuracao.md
```

Endpoint:

```text
POST /etl/apuracao
```
