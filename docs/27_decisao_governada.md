# 27 - Decisão Governada

## Objetivo

Fechar o ciclo:

```text
pendência materializada -> seleção pelo analista -> decisão nominal -> log parquet
```

Esta etapa ainda não altera a base OMS. Ela registra decisões auditáveis para posterior aplicação controlada na base corrigida/exportação.

## Backend

Rotas criadas no app atual `backend.app.server:app`:

### Resumo

```http
GET /apuracao/decisoes/resumo?anomes=202605
```

### Log paginado

```http
GET /apuracao/decisoes/log?anomes=202605&limit=100&offset=0
```

### Registrar decisão

```http
POST /apuracao/decisoes
```

Payload:

```json
{
  "anomes": "202605",
  "regra": "horario_negativo",
  "acao": "validar",
  "chaves_registro": ["2606040190604020"],
  "justificativa": "Registro conferido e aceito para tratamento posterior.",
  "usuario": "admin",
  "perfil": "admin",
  "pc": "nome-do-computador"
}
```

Ações aceitas:

- `validar`
- `rejeitar`
- `ignorar_regra`

## Saídas

Os registros são gravados em:

```text
data/logs/decisoes_pendencias_[anomes].parquet
data/logs/decisoes_pendencias_ATUAL.parquet
```

Campos principais:

- `id_decisao`
- `id_lote`
- `anomes`
- `regra`
- `acao`
- `chave_registro`
- `justificativa`
- `usuario`
- `perfil`
- `pc`
- `ip`
- `origem`
- `status_decisao`
- `criado_em`

## Frontend

Página oficial:

```text
http://127.0.0.1:5173/decisoes.html?anomes=202605
```

Entradas de navegação:

- Portal gestor -> Governança -> `Abrir decisão governada`
- Filas -> `Decisão governada`

## Critérios de aceite

- Carrega a fila da regra selecionada.
- Permite selecionar registros visíveis.
- Exige justificativa.
- Registra decisão no parquet.
- Atualiza o log de últimas decisões.
- Não altera a base OMS neste momento.

## Próximo passo

Aplicar decisões em uma base corrigida:

- `validar`: marca registro/regra como aprovado.
- `rejeitar`: marca registro para exclusão ou desconsideração.
- `ignorar_regra`: mantém registro na base, mas remove da fila daquela regra.

Essa aplicação deve gerar uma versão auditável da apuração corrigida antes da exportação IQS.

