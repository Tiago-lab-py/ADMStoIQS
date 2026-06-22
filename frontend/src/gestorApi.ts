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

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
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
