import { FilaResumo } from './filasApi'
import { getAuthToken } from './api'

export type IqsResumoItem = {
  anomes: string
  fonte: string
  linhas_raw: number
  linhas_mart: number
  status: string
  erro?: string
}

export type IqsResumo = {
  arquivos?: IqsResumoItem[]
  total_fontes?: number
  fontes_processadas?: number
  status?: string
  resumo?: string
  resumo_atual?: string
}

export type MartResumo = Record<string, unknown>

export type TratamentoRemocao = {
  regra: string
  total: number
}

export type TratamentoResumo = {
  anomes: string
  parquet: string
  log: string
  status: string
  total_final: number
  remocoes: TratamentoRemocao[]
}

export type TratamentoGeracao = TratamentoResumo & {
  origem?: string
  sobreposicao?: string
  parquet_atual?: string
  total_original?: number
  removido_horario_negativo?: number
  removido_sem_causa_componente?: number
  removido_sobreposicao_interrupcao?: number
}

export type TratamentoExportArquivo = {
  regional: string
  linhas: number
  arquivo: string
}

export type TratamentoExportacao = {
  anomes: string
  origem: string
  total_arquivos: number
  total_linhas: number
  arquivos: TratamentoExportArquivo[]
  status: string
}

export type IndicadoresComparativoItem = {
  anomes: string
  nivel: string
  regional_origem: string
  cod_conjunto_aneel: string
  quantidade_ucs: number
  dec_antes: number | null
  dec_depois: number | null
  dec_delta: number | null
  dec_delta_percentual: number | null
  fec_antes: number | null
  fec_depois: number | null
  fec_delta: number | null
  fec_delta_percentual: number | null
  dmic_max_antes: number | null
  dmic_max_depois: number | null
  dmic_delta: number | null
  fonte_denominador: string
  filtro_faturamento: string
  regra_liquido: string
}

export type IndicadoresResumo = {
  anomes: string
  arquivo: string
  status: string
  copel: IndicadoresComparativoItem | null
  regionais: IndicadoresComparativoItem[]
}

export type RessarcimentoGrupoItem = {
  cenario: string
  grupo_tensao: string
  ucs: number
  violacoes: number
  valor_estimado: number
}

export type RessarcimentoResumo = {
  status: string
  arquivo?: string
  total_registros?: number
  total_ucs?: number
  violacoes_antes?: number
  violacoes_depois?: number
  valor_estimado_antes?: number
  valor_estimado_depois?: number
  status_formula?: string
  por_grupo?: RessarcimentoGrupoItem[]
}

export type IndicadoresMaterializacao = {
  anomes: string
  mart_uc: string
  mart_agregado: string
  mart_comparativo: string
  total_uc: number
  total_agregado: number
  total_comparativo: number
  fonte_denominador: string
  filtro_faturamento: string
  status: string
}

export type PendenciasMaterializacao = {
  anomes: string
  origem: string
  parquet: string
  parquet_atual: string
  total_pendencias: number
  horario_negativo: number
  sobreposicao_interrupcao: number
  sem_causa_componente: number
}

export type OrquestradorEtapa = {
  etapa: string
  status: string
  mensagem: string
  iniciado_em: string
  finalizado_em?: string | null
  detalhes?: Record<string, unknown>
}

export type OrquestradorApuracaoRequest = {
  anomes: string
  processar_csv?: boolean
  atualizar_union?: boolean
  gerar_apuracao?: boolean
  materializar_pendencias?: boolean
  materializar_sobreposicao_interrupcao?: boolean
  gerar_tratado?: boolean
  materializar_indicadores?: boolean
  materializar_ressarcimento?: boolean
  remover_canceladas?: boolean
}

export type OrquestradorApuracaoResponse = {
  anomes: string
  status: string
  usuario: string
  perfil: string
  iniciado_em: string
  finalizado_em: string
  etapas: OrquestradorEtapa[]
}

export type EstadoArquivo = {
  arquivo: string | null
  caminho: string
  existe: boolean
  tamanho_bytes: number
  modificado_em: string | null
}

export type OrquestradorEtapa = {
  ordem: number
  etapa: string
  status: string
  mensagem?: string
}

export type OrquestradorJob = {
  job_id: string
  anomes: string
  tipo: string
  status: 'aguardando' | 'processando' | 'concluido' | 'erro' | string
  mensagem: string
  usuario?: string
  perfil?: string
  etapa_atual?: string
  etapas: OrquestradorEtapa[]
  criado_em?: string
  iniciado_em?: string | null
  finalizado_em?: string | null
  erro?: string
}

export type EstadoDados = {
  anomes: string
  ultimo_csv_processado: EstadoArquivo
  log_leitura_csv: EstadoArquivo
  log_oms_union: EstadoArquivo
  log_orquestrador: EstadoArquivo
  oms_union: EstadoArquivo
  apuracao_atual: EstadoArquivo
  apuracao_resumo: EstadoArquivo
  tratado_atual: EstadoArquivo
  indicadores_atualizados: EstadoArquivo
  ressarcimento_atualizado: EstadoArquivo
  ultimo_export_iqs: EstadoArquivo
  ultima_execucao_orquestrador?: Record<string, unknown> | null
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getAuthToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })
  const text = await response.text()
  let payload: unknown = {}

  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    payload = { detail: text }
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' && payload && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : text
    throw new Error(`${response.status}: ${detail}`)
  }

  return payload as T
}

export function getPortalFilasResumo(anomes?: string): Promise<FilaResumo> {
  const params = new URLSearchParams()
  if (anomes) params.set('anomes', anomes)
  const query = params.toString()
  return requestJson<FilaResumo>(`/apuracao/filas/resumo${query ? `?${query}` : ''}`)
}

export function getPortalIqsResumo(anomes = '202605'): Promise<IqsResumo> {
  return requestJson<IqsResumo>(`/iqs/resumo?anomes=${encodeURIComponent(anomes)}`)
}

export function getPortalMartResumo(): Promise<MartResumo> {
  return requestJson<MartResumo>('/mart/resumo')
}

export function getPortalTratamentoResumo(anomes: string): Promise<TratamentoResumo> {
  return requestJson<TratamentoResumo>(`/tratamento-massivo/${encodeURIComponent(anomes)}/resumo`)
}

export function gerarPortalTratamentoMassivo(anomes: string): Promise<TratamentoGeracao> {
  return requestJson<TratamentoGeracao>(`/tratamento-massivo/${encodeURIComponent(anomes)}/gerar`, {
    method: 'POST',
  })
}

export function exportarPortalTratamentoCsv(anomes: string): Promise<TratamentoExportacao> {
  return requestJson<TratamentoExportacao>(`/tratamento-massivo/${encodeURIComponent(anomes)}/exportar-csv`, {
    method: 'POST',
  })
}

export function getPortalIndicadoresResumo(anomes: string): Promise<IndicadoresResumo> {
  return requestJson<IndicadoresResumo>(`/indicadores/continuidade/${encodeURIComponent(anomes)}/resumo`)
}

export function materializarPortalIndicadores(anomes: string): Promise<IndicadoresMaterializacao> {
  return requestJson<IndicadoresMaterializacao>(`/indicadores/continuidade/${encodeURIComponent(anomes)}/materializar`, {
    method: 'POST',
  })
}

export function materializarPortalPendencias(anomes: string): Promise<PendenciasMaterializacao> {
  return requestJson<PendenciasMaterializacao>(`/apuracao/pendencias/materializar/${encodeURIComponent(anomes)}`, {
    method: 'POST',
  })
}

export function executarOrquestradorApuracao(
  payload: OrquestradorApuracaoRequest,
): Promise<OrquestradorApuracaoResponse> {
  return requestJson<OrquestradorApuracaoResponse>('/etl/orquestrar-apuracao', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

export function getPortalRessarcimentoResumo(anomes: string): Promise<RessarcimentoResumo> {
  return requestJson<RessarcimentoResumo>(`/indicadores/ressarcimento/${encodeURIComponent(anomes)}/resumo`)
}

export function materializarPortalRessarcimento(anomes: string): Promise<RessarcimentoResumo> {
  return requestJson<RessarcimentoResumo>(`/indicadores/ressarcimento/${encodeURIComponent(anomes)}/materializar`, {
    method: 'POST',
  })
}

export function getEstadoDados(anomes: string): Promise<EstadoDados> {
  return requestJson<EstadoDados>(`/etl/estado-dados?anomes=${encodeURIComponent(anomes)}`)
}

export function iniciarOrquestradorApuracao(payload: {
  anomes: string
  usuario?: string
  perfil?: string
  pc?: string
}): Promise<OrquestradorJob> {
  return requestJson<OrquestradorJob>('/etl/orquestrar-apuracao/jobs', {
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  })
}

export function getOrquestradorJob(jobId: string): Promise<OrquestradorJob> {
  return requestJson<OrquestradorJob>(`/jobs/${encodeURIComponent(jobId)}`)
}
