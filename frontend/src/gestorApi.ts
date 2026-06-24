import { FilaResumo } from './filasApi'

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

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
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

export function getPortalRessarcimentoResumo(anomes: string): Promise<RessarcimentoResumo> {
  return requestJson<RessarcimentoResumo>(`/indicadores/ressarcimento/${encodeURIComponent(anomes)}/resumo`)
}

export function materializarPortalRessarcimento(anomes: string): Promise<RessarcimentoResumo> {
  return requestJson<RessarcimentoResumo>(`/indicadores/ressarcimento/${encodeURIComponent(anomes)}/materializar`, {
    method: 'POST',
  })
}
