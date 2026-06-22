# API FastAPI - Fase 1 (01/06/2026)

## Objetivo
Camada transacional para escrita concorrente, mantendo Streamlit focado em visualização.

## Execução local
```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8010 --reload
```

## Endpoints

### `GET /health`
- Uso: healthcheck da API.
- Retorno: `200` com `{"ok": true, "message": "ok", ...}`.

### `POST /v1/etl/execucoes`
- Uso: registrar execução ETL (INICIADO/SUCESSO/FALHA).
- Payload:
```json
{
  "run_id": "etl_uuid",
  "competencia": "2026-05",
  "modo": "db",
  "status": "SUCESSO",
  "iniciado_em": "2026-06-01T08:00:00",
  "finalizado_em": "2026-06-01T08:05:00",
  "duracao_segundos": 300.0
}
```
- Regra: reaproveita `run_id` como chave de upsert.

### `POST /v1/validacoes/upsert`
- Uso: gravar/atualizar validação pós-operação.
- Payload:
```json
{
  "id_validacao": 12345,
  "payload": {
    "status_validacao": "VALIDAR",
    "comentario": "ajuste operacional"
  }
}
```
- Regra: upsert por `id_validacao`.

### `POST /v1/validacoes/status-efetivacao`
- Uso: atualizar apenas status de efetivação.
- Payload:
```json
{
  "id_validacao": 12345,
  "status_efetivacao": "EFETIVADO",
  "usuario_efetivacao": "usuario@copel.com",
  "data_efetivacao": "2026-06-01T09:30:00",
  "comentario": "ajuste concluído"
}
```

## Regra de idempotência (fase 1)
- Chave lógica: `id_validacao + status_efetivacao + usuario_efetivacao + data_efetivacao + comentario`.
- Se o estado atual já for igual ao payload, a API retorna sucesso com `idempotent=true` e `updated=false` (sem novo update).
- A atualização ocorre em transação com `SELECT ... FOR UPDATE` para evitar race condition de escrita simultânea no mesmo `id_validacao`.

## Erros
- `400`: validação inexistente ou payload sem colunas atualizáveis no schema.
- `500`: erro de persistência em banco.

