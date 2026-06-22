export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

let authToken =
  localStorage.getItem("admstoiqs_token") ||
  localStorage.getItem("token") ||
  "";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function setAuthToken(token: string | null) {
  authToken = token || "";
  if (token) {
    localStorage.setItem("admstoiqs_token", token);
    localStorage.setItem("token", token);
  } else {
    localStorage.removeItem("admstoiqs_token");
    localStorage.removeItem("token");
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

export function getAuthToken() {
  return authToken;
}

export const setToken = setAuthToken;
export const clearToken = clearAuthToken;
export const getToken = getAuthToken;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detailValue =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as { detail: unknown }).detail
        : body;
    const message =
      typeof detailValue === "string"
        ? detailValue
        : JSON.stringify(detailValue);
    throw new ApiError(message || `HTTP ${response.status}`, response.status, body);
  }

  return body as T;
}

function numericArg(value: unknown, fallback: number) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && /^\d+$/.test(value)) {
    return Number(value);
  }
  return fallback;
}

export type PerfilUsuario = "admin" | "gestor" | "usuario";

export interface LoginRequest {
  usuario: string;
  senha: string;
}

export type LoginPayload = LoginRequest;
export type LoginCredentials = LoginRequest;

export interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: string;
  nome_usuario: string;
  perfil: PerfilUsuario;
}

export type AuthResponse = LoginResponse;

export interface UserResponse {
  usuario: string;
  nome_usuario: string;
  perfil: PerfilUsuario;
}

export type AuthUser = UserResponse;
export type MeResponse = UserResponse;

export interface Competencia {
  anomes: string;
  arquivo: string;
  caminho: string;
  tamanho_bytes: number;
  modificado_em: string;
  fonte?: string;
}

export type CompetenciaResponse = Competencia;

export interface CompetenciasResponse {
  competencias: Competencia[];
}

export type ListaCompetenciasResponse = CompetenciasResponse;

export interface DadosResponse {
  anomes: string;
  limit: number;
  offset: number;
  total_retornado: number;
  registros: Record<string, unknown>[];
}

export type ConsultaDadosResponse = DadosResponse;

export interface MartResumoResponse {
  total_registros: number;
  pendentes: number;
  validados: number;
  rejeitados: number;
  ignorados: number;
  aplicados: number;
  horario_negativo: number;
  duracao_longa: number;
  sem_causa_componente: number;
  fonte: string;
  caminho: string;
  competencia_logica: string;
}

export interface EtlApuracaoRequest {
  anomes: string;
  remover_rejeitados?: boolean;
}

export interface EtlApuracaoResponse {
  anomes: string;
  fonte: string;
  arquivo: string;
  caminho: string;
  caminho_atual: string;
  linhas_saida: number;
  removidos_rejeitados: boolean;
  criterio: string;
  gerado_em: string;
}

export interface EtlOmsUnionResponse {
  status: string;
  mensagem: string;
  log: string;
}

export interface CsvPendenciaResumo {
  arquivos_encontrados: number;
  arquivos_processados: number;
  arquivos_com_erro: number;
  arquivos_pendentes: number;
  pendentes_por_mes: Record<string, number>;
  erros_por_mes: Record<string, number>;
  min_anomes: string;
  arquivos: Array<{
    arquivo: string;
    caminho: string;
    anomes: string;
    regional_origem: string;
    tamanho_bytes: number;
    modificado_em: string;
    status: string;
  }>;
}

export interface CsvProcessamentoResumo {
  linhas_lidas?: number;
  linhas_deduplicadas?: number;
  arquivos_processados_nesta_execucao?: number;
  antes?: CsvPendenciaResumo;
  depois?: CsvPendenciaResumo;
  [key: string]: unknown;
}

export interface AmostraResponse {
  anomes: string;
  criterio: string;
  total_retornado: number;
  registros: Record<string, unknown>[];
}

export type AmostraDuracaoResponse = AmostraResponse;

export interface TratamentoResponse {
  tipo: string;
  total_retornado: number;
  registros: Record<string, unknown>[];
}

export type FilaTratamentoResponse = TratamentoResponse;

export interface ExportCsvRequest {
  regional_origem: string;
  usuario?: string;
  justificativa?: string;
}

export type ExportRequest = ExportCsvRequest;

export interface ExportCsvResponse {
  anomes: string;
  regional_origem: string;
  arquivo: string;
  caminho: string;
  tamanho_bytes: number;
  total_linhas: number;
  colunas: number;
}

export type ExportResponse = ExportCsvResponse;

export interface ExportTodasRegionaisResponse {
  anomes: string;
  total_regionais: number;
  exports: ExportCsvResponse[];
}

export interface AlteracaoRequest {
  chave_registro: string;
  campo_alterado: string;
  valor_original?: string | null;
  valor_novo: string;
  justificativa: string;
}

export type AlteracaoPayload = AlteracaoRequest;

export interface AlteracaoResponse {
  status: string;
  mensagem?: string;
  registro?: Record<string, unknown>;
}

export interface OmsCorrigidoResponse {
  caminho: string;
  linhas_saida: number;
  alteracoes_aplicaveis: number;
}

export type GerarOmsCorrigidoResponse = OmsCorrigidoResponse;

export function login(payload: LoginRequest | string, senha?: string) {
  const body =
    typeof payload === "string"
      ? { usuario: payload, senha: senha || "" }
      : payload;

  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  }).then((response) => {
    setAuthToken(response.access_token);
    localStorage.setItem("admstoiqs_user", JSON.stringify(response));
    localStorage.setItem("user", JSON.stringify(response));
    return response;
  });
}

export function me() {
  return request<UserResponse>("/auth/me");
}

export const getMe = me;
export const usuarioAtual = me;
export const currentUser = me;

export function competencias() {
  return request<CompetenciasResponse>("/competencias");
}

export const listarCompetencias = competencias;
export const listCompetencias = competencias;
export const getCompetencias = competencias;

export function health() {
  return request<Record<string, unknown>>("/health");
}

export function dados(_anomesOrLimit: unknown = "UNION", limitArg: unknown = 100, offsetArg: unknown = 0) {
  const limit = numericArg(limitArg, 100);
  const offset = numericArg(offsetArg, 0);
  return request<DadosResponse>(`/mart/dados?limit=${limit}&offset=${offset}`);
}

export const getDados = dados;
export const consultarDados = dados;
export const getData = dados;

export function resumoMart() {
  return request<MartResumoResponse>("/mart/resumo");
}

export const getResumoMart = resumoMart;
export const martResumo = resumoMart;

export function executarEtlApuracao(payload: EtlApuracaoRequest) {
  return request<EtlApuracaoResponse>("/etl/apuracao", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function executarEtlOmsUnion() {
  return request<EtlOmsUnionResponse>("/etl/oms-union", {
    method: "POST",
  });
}

export function verificarCsvPendente(anomes?: string) {
  const query = anomes ? `?anomes=${encodeURIComponent(anomes)}` : "";
  return request<CsvPendenciaResumo>(`/etl/csv/verificar${query}`).catch((error) => {
    if (error instanceof ApiError && error.status === 404) {
      throw new ApiError(
        "Endpoint /etl/csv/verificar não encontrado. Reinicie a API para carregar as novas rotas.",
        404,
        error.detail,
      );
    }
    throw error;
  });
}

export function processarCsvPendente(anomes?: string) {
  return request<CsvProcessamentoResumo>("/etl/csv/processar", {
    method: "POST",
    body: JSON.stringify(anomes ? { anomes } : {}),
  }).catch((error) => {
    if (error instanceof ApiError && error.status === 404) {
      throw new ApiError(
        "Endpoint /etl/csv/processar não encontrado. Reinicie a API para carregar as novas rotas.",
        404,
        error.detail,
      );
    }
    throw error;
  });
}

export function amostra(_anomesOrLimit: unknown = "UNION", limitArg: unknown = 100) {
  const limit = numericArg(limitArg, 100);
  return request<AmostraResponse>(`/mart/amostra?limit=${limit}`);
}

export const getAmostra = amostra;
export const gerarAmostra = amostra;
export const getSample = amostra;

export function tratamento(tipo: string, limitArg: unknown = 100, offsetArg: unknown = 0) {
  const limit = numericArg(limitArg, 100);
  const offset = numericArg(offsetArg, 0);
  return request<TratamentoResponse>(`/tratamentos/${tipo}?limit=${limit}&offset=${offset}`);
}

export const getTratamento = tratamento;
export const listarTratamento = tratamento;
export const getTreatment = tratamento;

export function tratamentoHorarioNegativo(limit = 100, offset = 0) {
  return tratamento("horario-negativo", limit, offset);
}

export function tratamentoSobreposicaoInterrupcao(limit = 100, offset = 0) {
  return tratamento("sobreposicao-interrupcao", limit, offset);
}

export function tratamentoSobreposicaoUc(limit = 100, offset = 0) {
  return tratamento("sobreposicao-uc", limit, offset);
}

export function tratamentoSemCausaComponente(limit = 100, offset = 0) {
  return tratamento("sem-causa-componente", limit, offset);
}

export function exportRegional(_anomes: string, payload: ExportCsvRequest) {
  return request<ExportCsvResponse>("/mart/exportar-csv", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export const exportarCsv = exportRegional;
export const exportCsv = exportRegional;

export function exportTodas(_anomes: string, payload: ExportCsvRequest) {
  return request<ExportTodasRegionaisResponse>("/mart/exportar-csv-regionais", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export const exportarCsvRegionais = exportTodas;
export const exportAll = exportTodas;

export function solicitarAlteracao(payload: AlteracaoRequest) {
  return request<AlteracaoResponse>("/alteracoes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export const criarAlteracao = solicitarAlteracao;
export const registrarAlteracao = solicitarAlteracao;
export const createAlteracao = solicitarAlteracao;

export interface DecisaoRegistroRequest {
  usuario?: string;
  perfil?: string;
  pc?: string;
  justificativa: string;
}

function encodeChave(chave: string) {
  return chave
    .split("|")
    .map((part) => encodeURIComponent(part))
    .join("%7C");
}

export function validarRegistro(chave: string, payload: DecisaoRegistroRequest) {
  return request<Record<string, unknown>>(`/registros/${encodeChave(chave)}/validar`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rejeitarRegistro(chave: string, payload: DecisaoRegistroRequest) {
  return request<Record<string, unknown>>(`/registros/${encodeChave(chave)}/rejeitar`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function ignorarRegra(chave: string, payload: DecisaoRegistroRequest) {
  return request<Record<string, unknown>>(`/registros/${encodeChave(chave)}/ignorar-regra`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function aprovarAlteracao(idAlteracao: string, payload: DecisaoRegistroRequest) {
  return request<Record<string, unknown>>(`/alteracoes/${encodeURIComponent(idAlteracao)}/aprovar`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function rejeitarAlteracao(idAlteracao: string, payload: DecisaoRegistroRequest) {
  return request<Record<string, unknown>>(`/alteracoes/${encodeURIComponent(idAlteracao)}/rejeitar`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function gerarOmsCorrigido() {
  return request<OmsCorrigidoResponse>("/mart/oms-corrigido", {
    method: "POST",
  });
}

export const gerarMartCorrigido = gerarOmsCorrigido;
export const generateCorrectedOms = gerarOmsCorrigido;

export const api = {
  login,
  me,
  getMe,
  usuarioAtual,
  currentUser,
  competencias,
  listarCompetencias,
  listCompetencias,
  getCompetencias,
  health,
  dados,
  getDados,
  consultarDados,
  getData,
  resumoMart,
  getResumoMart,
  martResumo,
  executarEtlApuracao,
  executarEtlOmsUnion,
  verificarCsvPendente,
  processarCsvPendente,
  amostra,
  getAmostra,
  gerarAmostra,
  getSample,
  tratamento,
  getTratamento,
  listarTratamento,
  getTreatment,
  tratamentoHorarioNegativo,
  tratamentoSobreposicaoInterrupcao,
  tratamentoSobreposicaoUc,
  tratamentoSemCausaComponente,
  exportRegional,
  exportarCsv,
  exportCsv,
  exportTodas,
  exportarCsvRegionais,
  exportAll,
  solicitarAlteracao,
  criarAlteracao,
  registrarAlteracao,
  createAlteracao,
  validarRegistro,
  rejeitarRegistro,
  ignorarRegra,
  aprovarAlteracao,
  rejeitarAlteracao,
  gerarOmsCorrigido,
  gerarMartCorrigido,
  generateCorrectedOms,
};

export default api;
