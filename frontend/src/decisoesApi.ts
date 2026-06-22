export type DecisaoPayload = {
  anomes: string
  regra: string
  acao: 'validar' | 'rejeitar' | 'ignorar_regra'
  chaves_registro: string[]
  justificativa: string
  usuario: string
  perfil: string
  pc?: string
}

export type DecisaoResponse = {
  id_lote: string
  anomes: string
  regra: string
  acao: string
  decisoes_registradas: number
  total_decisoes: number
  arquivo: string
  arquivo_atual: string
  status: string
}

export type DecisoesResumo = {
  anomes: string
  arquivo: string
  arquivo_atual: string
  total_decisoes: number
  por_acao: Array<{ acao: string; total: number }>
  por_regra: Array<{ regra: string; acao: string; total: number }>
  status: string
}

export type DecisoesLog = {
  anomes: string
  arquivo: string
  limit: number
  offset: number
  total: number
  registros: Array<Record<string, unknown>>
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
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

export function registrarDecisao(payload: DecisaoPayload): Promise<DecisaoResponse> {
  return requestJson<DecisaoResponse>('/apuracao/decisoes', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getDecisoesResumo(anomes: string): Promise<DecisoesResumo> {
  return requestJson<DecisoesResumo>(`/apuracao/decisoes/resumo?anomes=${encodeURIComponent(anomes)}`)
}

export function getDecisoesLog(anomes: string, limit = 50, offset = 0): Promise<DecisoesLog> {
  const params = new URLSearchParams({
    anomes,
    limit: String(limit),
    offset: String(offset),
  })
  return requestJson<DecisoesLog>(`/apuracao/decisoes/log?${params}`)
}

