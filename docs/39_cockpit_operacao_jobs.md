# Cockpit de Operação e Jobs em Background

## Objetivo

Transformar a tela operacional em um cockpit de acompanhamento diário do ADMStoIQS, evitando requests longos no navegador e melhorando a confiança do usuário sobre o estado dos arquivos.

## Jornada operacional

1. Admin acessa o portal unificado.
2. Visualiza pendências, correções automáticas e estado dos arquivos.
3. Aciona `Executar atualização diária`.
4. Backend cria um `job_id` e retorna imediatamente.
5. Frontend consulta `/jobs/{job_id}` periodicamente.
6. Usuário pode navegar para outras abas enquanto o job roda.
7. Ao concluir, o cockpit atualiza os arquivos/logs e a última execução.

## Endpoints

- `POST /etl/orquestrar-apuracao/jobs`: cria job assíncrono da trilha diária.
- `GET /jobs/{job_id}`: consulta status e etapas do job.
- `GET /etl/estado-dados?anomes=YYYYMM`: retorna estado dos arquivos e logs principais.

## Log de orquestração

Arquivo:

- `data/logs/log_orquestrador_apuracao.parquet`

Campos esperados:

- `job_id`
- `anomes`
- `status`
- `etapa_atual`
- `mensagem`
- `usuario`
- `perfil`
- `pc`
- `ip`
- `criado_em`
- `iniciado_em`
- `finalizado_em`
- `erro`

## Estado dos dados no cockpit

O painel deve mostrar:

- último CSV processado;
- `log_leitura_csv.parquet`;
- `log_oms_union.parquet`;
- `agrupamento_oms_APURACAO_ATUAL.parquet`;
- `agrupamento_oms_APURACAO_TRATADO_ATUAL.parquet`;
- `indicadores_comparativo_ATUAL.parquet`;
- `indicadores_ressarcimento_ATUAL.parquet`;
- último CSV IQS exportado.

## Padrão visual

- Status em badge: verde, amarelo, vermelho ou cinza.
- Caminhos de arquivos em fonte menor com botão de copiar.
- Datas em `dd/mm/aaaa hh:mm:ss`.
- Valores numéricos com separador brasileiro.

