export type FilaResumoRegra = {
  regra: string
  total: number
  registros_distintos: number
}

export type FilaResumoStatus = {
  status: string
  total: number
}

export type FilaResumo = {
  arquivo: string
  anomes?: string
  status: string
  total_pendencias: number
  por_regra: FilaResumoRegra[]
  por_status: FilaResumoStatus[]
}

export type FilaResponse = {
  arquivo: string
  anomes?: string
  regra: string
  limit: number
  offset: number
  total: number
  registros: Array<Record<string, unknown>>
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

export function getFilasResumo(anomes?: string): Promise<FilaResumo> {
  const params = new URLSearchParams()
  if (anomes) params.set('anomes', anomes)
  const query = params.toString()
  return requestJson<FilaResumo>(`/apuracao/filas/resumo${query ? `?${query}` : ''}`)
}

export function getFilaPorRegra(regra: string, limit = 100, offset = 0, anomes?: string): Promise<FilaResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  if (anomes) params.set('anomes', anomes)

  return requestJson<FilaResponse>(`/apuracao/filas/${encodeURIComponent(regra)}?${params}`)
}
