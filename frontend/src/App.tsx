import React, { useCallback, useEffect, useMemo, useState } from "react";

type Perfil = "admin" | "gestor" | "usuario" | string;

type UsuarioSessao = {
  usuario: string;
  nome_usuario: string;
  perfil: Perfil;
};

type ApiResponse = Record<string, any>;
type Registro = Record<string, any>;

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const MENU = [
  ["etl", "Preparar apuração", "ETL mensal do mart"],
  ["dashboard", "Dashboard", "Visão geral do mart"],
  ["horario-negativo", "Horário negativo", "Correção de duração/fuso"],
  ["sobreposicao-interrupcao", "Sobreposição interrupção", "Alimentador e chave"],
  ["sobreposicao-uc", "Sobreposição UC", "Conflitos por unidade consumidora"],
  ["sem-causa-componente", "Causa/componente", "Campos ausentes"],
  ["revisao", "Revisão final", "Pendências e alterações"],
  ["exportacao", "Exportação", "CSVs regionais"],
  ["admin", "Administração", "Usuários e perfis"],
] as const;

const COLUNAS_PADRAO = [
  "NUM_OPER_CHV_INTRP",
  "sugestao_atividade",
  "NUM_MOTIVO_TRAT_DIF_UCI_SUGERIDO",
  "qtd_interrupcoes_sobrepostas",
  "num_seq_intrp_mantido",
  "data_hora_inicio_sugerida",
  "data_hora_fim_sugerida",
  "qtd_ucs_afetadas",
  "DATA_HORA_INIC_INTRP_SUGERIDA",
  "DATA_HORA_FIM_INTRP_SUGERIDA",
  "VALOR_INICIO_SUGERIDO",
  "VALOR_FIM_SUGERIDO",
  "NUM_INTRP_UCI",
  "NUM_POSTO_UCI",
  "NUM_UC_UCI",
  "NUM_SEQ_INTRP",
  "ALIM_INTRP_PIN",
  "DATA_HORA_INIC_INTRP",
  "DATA_HORA_FIM_INTRP",
  "DTHR_INICIO_INTRP_UC",
  "duracao_minutos",
  "erro_duracao",
  "duracao_longa",
  "REGIONAL_ORIGEM",
  "status_validacao",
];

function token(): string {
  return (
    localStorage.getItem("admstoiqs_token") ||
    localStorage.getItem("token") ||
    ""
  );
}

function setToken(value: string): void {
  localStorage.setItem("admstoiqs_token", value);
  localStorage.setItem("token", value);
}

function chaveRegistro(registro: Registro): string {
  return [
    registro.NUM_INTRP_UCI ?? "",
    registro.NUM_POSTO_UCI ?? "",
    registro.NUM_UC_UCI ?? "",
  ].join("|");
}

function chaveNumSeq(registro: Registro): string {
  return valor(
    registro.NUM_SEQ_INTRP ??
      registro.num_seq_intrp ??
      registro.PID_INTRP_CONJTO_PIN ??
      registro.NUM_INTRP_UCI,
  ).trim();
}

function valor(valor: any): string {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "boolean") return valor ? "true" : "false";
  return String(valor);
}

function normalizarColuna(coluna: string): string {
  return coluna.trim().toUpperCase();
}

function valorColuna(registro: Registro, coluna: string): string {
  if (normalizarColuna(coluna) === "NUM_SEQ_INTRP") {
    return valor(
      registro.NUM_SEQ_INTRP ??
        registro.num_seq_intrp ??
        registro.PID_INTRP_CONJTO_PIN ??
        registro.NUM_INTRP_UCI,
    );
  }
  return valor(registro[coluna]);
}

function numeroDuracao(registro: Registro): number | null {
  const raw =
    registro.duracao_minutos ??
    registro.DURACAO_MINUTOS ??
    registro.duracao ??
    registro.DURACAO;
  if (raw === null || raw === undefined || raw === "") return null;
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : null;
  const parsed = Number(String(raw).trim().replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

async function request<T = ApiResponse>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };
  const bearer = token();
  if (bearer) headers.Authorization = `Bearer ${bearer}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const text = await response.text();
  let body: any = text;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = text;
  }
  if (!response.ok) {
    const detail = body?.detail || body?.message || body || response.statusText;
    throw new Error(`${response.status}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
  }
  return body as T;
}

function extrairRegistros(body: ApiResponse): Registro[] {
  if (Array.isArray(body)) return body;
  return body.registros || body.dados || body.items || [];
}

function Login({ onLogin }: { onLogin: (usuario: UsuarioSessao) => void }) {
  const [usuario, setUsuario] = useState("admin");
  const [senha, setSenha] = useState("admin123");
  const [erro, setErro] = useState("");
  const [loading, setLoading] = useState(false);

  const entrar = async (event: React.FormEvent) => {
    event.preventDefault();
    setErro("");
    setLoading(true);
    try {
      const body = await request<ApiResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ usuario, senha }),
      });
      setToken(body.access_token);
      onLogin({
        usuario: body.usuario || usuario,
        nome_usuario: body.nome_usuario || usuario,
        perfil: body.perfil || "usuario",
      });
    } catch (error: any) {
      setErro(error.message || "Falha ao autenticar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={entrar}>
        <div className="brand-mark">AI</div>
        <h1>ADMStoIQS</h1>
        <p>Trilha governada de correções OMS.</p>
        <label>
          Usuário
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </label>
        {erro && <div className="alert error">{erro}</div>}
        <button className="primary" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
        <small>Dev: admin/admin123 • gestor/gestor123 • usuario/usuario123</small>
      </form>
    </main>
  );
}

function TabelaRegistros({
  registros,
  registrosOrigem,
  selecionados,
  setSelecionados,
  onSelect,
  pagina,
}: {
  registros: Registro[];
  registrosOrigem?: Registro[];
  selecionados?: Set<string>;
  setSelecionados?: (selecionados: Set<string>) => void;
  onSelect: (registro: Registro) => void;
  pagina: string;
}) {
  const colunas = useMemo(() => {
    const presentes = COLUNAS_PADRAO.filter((coluna) =>
      registros.some((registro) => registro[coluna] !== undefined),
    );
    const extras = registros[0]
      ? Object.keys(registros[0]).filter((coluna) => !presentes.includes(coluna)).slice(0, 8)
      : [];
    const colunasBase = [...presentes, ...extras];
    if (pagina === "horario-negativo") {
      const filtradas = colunasBase.filter(
        (coluna) =>
          !["NUM_POSTO_UCI", "NUM_UC_UCI", "NUM_INTRP_UCI"].includes(
            normalizarColuna(coluna),
          ),
      );
      if (!filtradas.some((coluna) => normalizarColuna(coluna) === "NUM_SEQ_INTRP")) {
        const alternativaSeq = filtradas.find((coluna) =>
          ["PID_INTRP_CONJTO_PIN", "NUM_INTRP_UCI"].includes(normalizarColuna(coluna)),
        );
        return alternativaSeq
          ? ["NUM_SEQ_INTRP", ...filtradas.filter((coluna) => coluna !== "NUM_SEQ_INTRP")]
          : filtradas;
      }
      return filtradas;
    }
    return colunasBase;
  }, [registros]);

  const usarCheckbox = pagina === "horario-negativo" && selecionados && setSelecionados;
  const baseSelecao = registrosOrigem || registros;
  const chavesDaInterrupcao = (registro: Registro) => {
    if (pagina !== "horario-negativo") return [chaveRegistro(registro)];
    const seq = chaveNumSeq(registro);
    return baseSelecao
      .filter((item) => chaveNumSeq(item) === seq)
      .map(chaveRegistro);
  };
  const todosSelecionados =
    !!usarCheckbox &&
    registros.length > 0 &&
    registros.every((registro) =>
      chavesDaInterrupcao(registro).every((chave) => selecionados.has(chave)),
    );

  const alternarTodos = () => {
    if (!usarCheckbox) return;
    const proximo = new Set(selecionados);
    if (todosSelecionados) {
      registros.forEach((registro) =>
        chavesDaInterrupcao(registro).forEach((chave) => proximo.delete(chave)),
      );
    } else {
      registros.forEach((registro) =>
        chavesDaInterrupcao(registro).forEach((chave) => proximo.add(chave)),
      );
    }
    setSelecionados(proximo);
  };

  const alternarRegistro = (registro: Registro) => {
    if (!usarCheckbox) return;
    const proximo = new Set(selecionados);
    const chaves = chavesDaInterrupcao(registro);
    const todasMarcadas = chaves.every((chave) => proximo.has(chave));
    if (todasMarcadas) chaves.forEach((chave) => proximo.delete(chave));
    else chaves.forEach((chave) => proximo.add(chave));
    setSelecionados(proximo);
  };

  if (!registros.length) {
    return <div className="empty-state">Nenhum registro carregado.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {usarCheckbox && (
              <th className="check-cell">
                <input
                  type="checkbox"
                  checked={todosSelecionados}
                  onChange={alternarTodos}
                  title="Selecionar todos os registros visíveis"
                />
              </th>
            )}
            {colunas.map((coluna) => (
              <th key={coluna}>{coluna}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {registros.map((registro, index) => {
            const chave = chaveRegistro(registro);
            const checked =
              usarCheckbox && pagina === "horario-negativo"
                ? chavesDaInterrupcao(registro).some((item) => selecionados.has(item))
                : !!usarCheckbox && selecionados.has(chave);
            return (
              <tr key={`${chave}-${index}`} onClick={() => onSelect(registro)}>
                {usarCheckbox && (
                  <td className="check-cell" onClick={(event) => event.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => alternarRegistro(registro)}
                    />
                  </td>
                )}
                {colunas.map((coluna) => (
                  <td key={coluna}>{valorColuna(registro, coluna)}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PainelAlteracao({
  registro,
  justificativa,
  setJustificativa,
  selecionados,
  onAcao,
  busy,
}: {
  registro: Registro | null;
  justificativa: string;
  setJustificativa: (value: string) => void;
  selecionados: Set<string>;
  onAcao: (acao: "validar" | "rejeitar" | "ignorar-regra") => void;
  busy: boolean;
}) {
  return (
    <section className="decision-card">
      <span className="section-kicker">Log de alteração</span>
      <h3>Decisão governada</h3>
      <div className="audit-grid">
        <span>NUM_INTRP_UCI alterada</span>
        <strong>{registro ? valor(registro.NUM_INTRP_UCI) : "Nenhum registro selecionado"}</strong>
        <span>Chave do registro</span>
        <strong>{registro ? chaveRegistro(registro) : "-"}</strong>
        <span>Selecionados na tabela</span>
        <strong>{selecionados.size}</strong>
      </div>
      <label>
        Justificativa
        <textarea
          value={justificativa}
          onChange={(event) => setJustificativa(event.target.value)}
          placeholder="Descreva o motivo técnico da decisão."
        />
      </label>
      <div className="actions">
        <button disabled={busy} onClick={() => onAcao("validar")}>
          Validar
        </button>
        <button disabled={busy} onClick={() => onAcao("rejeitar")}>
          Rejeitar
        </button>
        <button disabled={busy} onClick={() => onAcao("ignorar-regra")}>
          Ignorar regra
        </button>
      </div>
    </section>
  );
}

function TabelaDetalheNumSeq({
  registro,
  registros,
}: {
  registro: Registro | null;
  registros: Registro[];
}) {
  const seqRegistro =
    registro?.NUM_SEQ_INTRP ??
    registro?.num_seq_intrp ??
    registro?.PID_INTRP_CONJTO_PIN ??
    registro?.NUM_INTRP_UCI;
  if (!seqRegistro) return null;

  const numSeq = valor(seqRegistro);
  const detalhes = registros.filter((item) => {
    const seqItem =
      item.NUM_SEQ_INTRP ??
      item.num_seq_intrp ??
      item.PID_INTRP_CONJTO_PIN ??
      item.NUM_INTRP_UCI;
    return valor(seqItem) === numSeq;
  });
  const colunas = [
    "NUM_SEQ_INTRP",
    "NUM_POSTO_UCI",
    "NUM_UC_UCI",
    "NUM_INTRP_UCI",
    "DTHR_INICIO_INTRP_UC",
    "duracao_minutos",
  ].filter((coluna) => detalhes.some((item) => item[coluna] !== undefined));

  if (!detalhes.length) return null;

  return (
    <section className="records-card seq-detail-card">
      <span className="section-kicker">Detalhe da NUM_SEQ_INTRP</span>
      <h3>{numSeq}</h3>
      <p>
        UCs vinculadas à interrupção selecionada. Esta tabela mantém
        `NUM_POSTO_UCI` e `NUM_UC_UCI` para apoiar a tratativa.
      </p>
      <div className="table-wrap seq-detail-table">
        <table>
          <thead>
            <tr>
              {colunas.map((coluna) => (
                <th key={coluna}>{coluna}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {detalhes.map((item, index) => (
              <tr key={`${numSeq}-${index}`}>
                {colunas.map((coluna) => (
                  <td key={coluna}>{valorColuna(item, coluna)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function App() {
  const [usuario, setUsuario] = useState<UsuarioSessao | null>(null);
  const [pagina, setPagina] = useState("etl");
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [registroAtual, setRegistroAtual] = useState<Registro | null>(null);
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set());
  const [resumo, setResumo] = useState<ApiResponse>({});
  const [mensagem, setMensagem] = useState("");
  const [mensagemTipo, setMensagemTipo] = useState<"info" | "processing" | "success">("info");
  const [erro, setErro] = useState("");
  const [busy, setBusy] = useState(false);
  const [mesApuracao, setMesApuracao] = useState("202605");
  const [removerCanceladas, setRemoverCanceladas] = useState(false);
  const [justificativa, setJustificativa] = useState("");
  const [csvResumo, setCsvResumo] = useState<ApiResponse | null>(null);
  const [sobreposicaoUcFase2Resumo, setSobreposicaoUcFase2Resumo] = useState<ApiResponse | null>(null);
  const [sobreposicaoUcResumo, setSobreposicaoUcResumo] = useState<ApiResponse | null>(null);
  const [duracaoMinFiltro, setDuracaoMinFiltro] = useState("");
  const [duracaoMaxFiltro, setDuracaoMaxFiltro] = useState("");

  useEffect(() => {
    const bearer = token();
    if (!bearer) return;
    request<ApiResponse>("/auth/me")
      .then((body) =>
        setUsuario({
          usuario: body.usuario || body.username || "usuario",
          nome_usuario: body.nome_usuario || body.nome || body.usuario || "Usuário",
          perfil: body.perfil || "usuario",
        }),
      )
      .catch(() => {
        localStorage.removeItem("admstoiqs_token");
        localStorage.removeItem("token");
      });
  }, []);

  const carregarResumo = useCallback(async () => {
    const body = await request<ApiResponse>("/mart/resumo");
    setResumo(body);
  }, []);

  const carregarDados = useCallback(async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    const paginaAtual = pagina;
    try {
      const endpoint =
        paginaAtual === "dashboard" || paginaAtual === "etl" || paginaAtual === "exportacao" || paginaAtual === "admin"
          ? "/mart/dados?limit=100&offset=0"
          : paginaAtual === "sobreposicao-uc"
            ? `/apuracao/analises/sobreposicao-uc-fase2?anomes=${encodeURIComponent(mesApuracao)}&limit=100&offset=0`
            : `/tratamentos/${paginaAtual}?limit=100&offset=0`;
      const body = await request<ApiResponse>(endpoint);
      const dados = extrairRegistros(body);
      setRegistros(dados);
      setRegistroAtual(dados[0] || null);
      setSelecionados(new Set());
      setMensagemTipo("info");
      setMensagem(`${dados.length} registro(s) carregado(s).`);
      await carregarResumo().catch(() => undefined);
    } catch (error: any) {
      setErro(error.message || "Falha ao carregar dados.");
    } finally {
      setBusy(false);
    }
  }, [pagina, carregarResumo, mesApuracao]);

  useEffect(() => {
    if (usuario && pagina !== "etl") {
      carregarDados();
    }
  }, [usuario, pagina, carregarDados]);

  const verificarCsv = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    try {
      const body = await request<ApiResponse>("/etl/csv/verificar");
      setCsvResumo(body);
      setMensagemTipo("success");
      setMensagem(`Processamento concluído. ${body.arquivos_pendentes || 0} CSV(s) pendente(s).`);
    } catch (error: any) {
      setErro(error.message || "Falha ao verificar CSV pendente.");
    } finally {
      setBusy(false);
    }
  };

  const processarCsv = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    try {
      const body = await request<ApiResponse>("/etl/csv/processar", { method: "POST" });
      setCsvResumo(body.depois || body);
      setMensagemTipo("success");
      setMensagem(
        `Processamento concluído. Linhas lidas: ${body.linhas_lidas || 0}. Deduplicadas: ${body.linhas_deduplicadas || 0}.`,
      );
    } catch (error: any) {
      setErro(error.message || "Falha ao processar CSV pendente.");
    } finally {
      setBusy(false);
    }
  };

  const atualizarUnion = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    try {
      const body = await request<ApiResponse>("/etl/oms-union", { method: "POST" });
      setMensagemTipo("success");
      setMensagem(`Processamento concluído. UNION atualizado com ${body.linhas_saida || body.linhas || 0} linha(s).`);
    } catch (error: any) {
      setErro(error.message || "Falha ao atualizar UNION.");
    } finally {
      setBusy(false);
    }
  };

  const gerarApuracao = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    try {
      const body = await request<ApiResponse>("/etl/apuracao", {
        method: "POST",
        body: JSON.stringify({
          anomes: mesApuracao,
          remover_rejeitados: false,
          remover_canceladas: removerCanceladas,
        }),
      });
      setMensagemTipo("success");
      setMensagem(`Processamento concluído. Apuração e cards materializados com ${body.linhas_saida || body.linhas || 0} linha(s).`);
      setPagina("dashboard");
    } catch (error: any) {
      setErro(error.message || "Falha ao gerar apuração.");
    } finally {
      setBusy(false);
    }
  };

  const materializarPendencias = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento: materializando pendências da apuração...");
    try {
      const body = await request<ApiResponse>(
        `/apuracao/pendencias/materializar/${encodeURIComponent(mesApuracao)}`,
        { method: "POST" },
      );
      setMensagemTipo("success");
      setMensagem(
          `Processamento concluído. ${body.total_pendencias || 0} pendência(s) materializada(s). ` +
          `Horário negativo: ${body.horario_negativo || 0}. ` +
          `Sobreposição: ${body.sobreposicao_interrupcao || 0}. ` +
          `Sobreposição UC: ${body.sobreposicao_uc || 0}. ` +
          `Causa/componente: ${body.sem_causa_componente || 0}.`,
      );
      await carregarResumo().catch(() => undefined);
    } catch (error: any) {
      setErro(error.message || "Falha ao materializar pendências.");
    } finally {
      setBusy(false);
    }
  };

  const analisarSobreposicaoUc = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento: analisando sobreposição temporal por UC...");
    try {
      const body = await request<ApiResponse>(
        `/apuracao/analises/sobreposicao-uc/materializar/${encodeURIComponent(mesApuracao)}`,
        { method: "POST" },
      );
      setSobreposicaoUcResumo(body);
      setMensagemTipo("success");
      setMensagem(
        `Processamento concluído. ${body.registros_classificar_91 || 0} registro(s) sugeridos para motivo 91. ` +
          `CHI reduzido estimado: ${Number(body.chi_reduzido_estimado || 0).toLocaleString("pt-BR", {
            maximumFractionDigits: 2,
          })}.`,
      );
    } catch (error: any) {
      setErro(error.message || "Falha ao analisar sobreposição temporal por UC.");
    } finally {
      setBusy(false);
    }
  };

  const implantarSobreposicaoUc = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento: implantando motivo 91 e recalculando marts...");
    try {
      const body = await request<ApiResponse>(
        `/apuracao/analises/sobreposicao-uc/implantar/${encodeURIComponent(mesApuracao)}`,
        {
          method: "POST",
          body: JSON.stringify({
            usuario: usuario?.usuario || "sistema",
            perfil: usuario?.perfil || "gestor",
            pc: navigator.userAgent,
            justificativa:
              "Implantação governada de motivo 91 por sobreposição temporal de UC.",
            recalcular: true,
          }),
        },
      );
      setSobreposicaoUcResumo(body);
      setMensagemTipo("success");
      setMensagem(
        `Processamento concluído. ${body.registros_atualizados || 0} registro(s) atualizados com motivo 91. ` +
          "Pendências, tratamento, indicadores e ressarcimento foram solicitados para recálculo.",
      );
      await carregarResumo().catch(() => undefined);
    } catch (error: any) {
      setErro(error.message || "Falha ao implantar motivo 91 para sobreposição UC.");
    } finally {
      setBusy(false);
    }
  };

  const analisarSobreposicaoUcFase2 = async () => {
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento: analisando interseções temporais por UC...");
    try {
      const body = await request<ApiResponse>(
        `/apuracao/analises/sobreposicao-uc-fase2/materializar/${encodeURIComponent(mesApuracao)}`,
        { method: "POST" },
      );
      setSobreposicaoUcFase2Resumo(body);
      const lista = await request<ApiResponse>(
        `/apuracao/analises/sobreposicao-uc-fase2?anomes=${encodeURIComponent(mesApuracao)}&limit=100&offset=0`,
      );
      const dados = extrairRegistros(lista);
      setRegistros(dados);
      setRegistroAtual(dados[0] || null);
      setSelecionados(new Set());
      setMensagemTipo("success");
      setMensagem(
        `Processamento concluído. ${body.total_ajustes || 0} ajuste(s) sugerido(s), ` +
          `${body.ucs_afetadas || 0} UC(s) afetada(s).`,
      );
    } catch (error: any) {
      setErro(error.message || "Falha ao analisar sobreposição UC Fase 2.");
    } finally {
      setBusy(false);
    }
  };

  const implantarSobreposicaoUcFase2 = async () => {
    if (!justificativa.trim()) {
      setErro("Informe a justificativa para implantar os ajustes da Fase 2.");
      return;
    }
    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento: implantando ajustes da sobreposição UC Fase 2...");
    try {
      const body = await request<ApiResponse>(
        `/apuracao/analises/sobreposicao-uc-fase2/implantar/${encodeURIComponent(mesApuracao)}`,
        {
          method: "POST",
          body: JSON.stringify({
            usuario: usuario.usuario,
            perfil: usuario.perfil,
            justificativa,
            recalcular: true,
          }),
        },
      );
      setSobreposicaoUcFase2Resumo(body);
      setJustificativa("");
      setMensagemTipo("success");
      setMensagem(
        `Processamento concluído. ${body.registros_atualizados || 0} registro(s) ajustado(s); ` +
          `${body.interrupcoes_ajustadas || 0} interrupção(ões) afetada(s).`,
      );
      await carregarResumo().catch(() => undefined);
      await carregarDados().catch(() => undefined);
    } catch (error: any) {
      setErro(error.message || "Falha ao implantar sobreposição UC Fase 2.");
    } finally {
      setBusy(false);
    }
  };

  const agirRegistros = async (acao: "validar" | "rejeitar" | "ignorar-regra") => {
    const alvos =
      selecionados.size > 0
        ? registros.filter((registro) => selecionados.has(chaveRegistro(registro)))
        : registroAtual
          ? [registroAtual]
          : [];

    if (!alvos.length) {
      setErro("Selecione ao menos um registro.");
      return;
    }
    if (!justificativa.trim()) {
      setErro("Informe a justificativa para registrar a alteração.");
      return;
    }

    setBusy(true);
    setErro("");
    setMensagemTipo("processing");
    setMensagem("Aguarde processamento...");
    try {
      for (const registro of alvos) {
        const chave = encodeURIComponent(chaveRegistro(registro));
        await request(`/registros/${chave}/${acao}`, {
          method: "POST",
          body: JSON.stringify({
            justificativa,
            NUM_INTRP_UCI: registro.NUM_INTRP_UCI,
            num_intrp_uci: registro.NUM_INTRP_UCI,
            chave_registro: chaveRegistro(registro),
            data_hora_inicio_original: registro.DATA_HORA_INIC_INTRP,
            data_hora_fim_original: registro.DATA_HORA_FIM_INTRP,
            data_hora_inicio_sugerida:
              registro.DATA_HORA_INIC_INTRP_SUGERIDA ?? registro.VALOR_INICIO_SUGERIDO,
            data_hora_fim_sugerida:
              registro.DATA_HORA_FIM_INTRP_SUGERIDA ??
              registro.VALOR_FIM_SUGERIDO ??
              registro.VALOR_SUGERIDO,
          }),
        });
      }
      setMensagemTipo("success");
      setMensagem(`Processamento concluído. ${alvos.length} registro(s) enviados para o log de alteração.`);
      setJustificativa("");
      setSelecionados(new Set());
      await carregarDados();
    } catch (error: any) {
      setErro(error.message || "Falha ao registrar alteração.");
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("admstoiqs_token");
    localStorage.removeItem("token");
    setUsuario(null);
  };

  const registrosVisiveis = useMemo(() => {
    if (pagina !== "horario-negativo") return registros;
    const min =
      duracaoMinFiltro.trim() === ""
        ? null
        : Number(duracaoMinFiltro.trim().replace(",", "."));
    const max =
      duracaoMaxFiltro.trim() === ""
        ? null
        : Number(duracaoMaxFiltro.trim().replace(",", "."));
    const filtrados = registros.filter((registro) => {
      const duracao = numeroDuracao(registro);
      if (duracao === null) return false;
      if (min !== null && Number.isFinite(min) && duracao < min) return false;
      if (max !== null && Number.isFinite(max) && duracao > max) return false;
      return true;
    });
    const porNumSeq = new Map<string, Registro>();
    for (const registro of filtrados) {
      const chave = chaveNumSeq(registro);
      if (!chave) continue;
      if (!porNumSeq.has(chave)) {
        porNumSeq.set(chave, registro);
      }
    }
    return Array.from(porNumSeq.values());
  }, [duracaoMaxFiltro, duracaoMinFiltro, pagina, registros]);

  const numSeqDistintasVisiveis = useMemo(() => {
    if (pagina !== "horario-negativo") return 0;
    return new Set(
      registrosVisiveis
        .map((registro) => chaveNumSeq(registro))
        .filter(Boolean),
    ).size;
  }, [pagina, registrosVisiveis]);

  if (!usuario) {
    return <Login onLogin={setUsuario} />;
  }

  const metricas = [
    ["Pendências totais", resumo.pendentes ?? resumo.pendencias_totais ?? 0],
    ["Horário negativo", resumo.horario_negativo ?? 0],
    ["Sobreposições", resumo.sobreposicoes ?? resumo.sobreposicao_interrupcao ?? 0],
    ["Rejeitados", resumo.rejeitados ?? 0],
  ];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">AI</div>
          <div>
            <strong>ADMStoIQS</strong>
            <small>OMS Correções</small>
          </div>
        </div>
        <section className="focus-card">
          <span>FOCO DE ATUAÇÃO</span>
          <strong>{resumo.pendentes ?? 0}</strong>
          <small>Pendências mapeadas</small>
        </section>
        <nav>
          {MENU.map(([id, titulo, subtitulo]) => (
            <button
              key={id}
              className={pagina === id ? "active" : ""}
              onClick={() => {
                if (id === "horario-negativo") {
                  setDuracaoMinFiltro("");
                  setDuracaoMaxFiltro("");
                }
                if (id !== pagina) {
                  setRegistros([]);
                  setRegistroAtual(null);
                  setSelecionados(new Set());
                  setMensagemTipo("processing");
                  setMensagem("Aguarde processamento...");
                }
                setPagina(id);
              }}
            >
              <span>{titulo}</span>
              <small>{subtitulo}</small>
              <b>{id === "horario-negativo" ? resumo.horario_negativo ?? 0 : 0}</b>
            </button>
          ))}
        </nav>
        <section className="user-card">
          <strong>{usuario.nome_usuario}</strong>
          <small>{usuario.perfil}</small>
          <button onClick={logout}>Sair</button>
        </section>
      </aside>

      <section className="content">
        {erro && <div className="alert error">{erro}</div>}
        {mensagem && <div className={`alert ${mensagemTipo}`}>{mensagem}</div>}

        {pagina === "etl" ? (
          <>
            <header className="page-header">
              <div>
                <h1>Preparar apuração</h1>
                <p>Etapas operacionais antes da análise mensal.</p>
              </div>
            </header>

            <section className="etl-card">
              <div className="etl-window">
                <div>
                  <span className="section-kicker">Janela 1</span>
                  <h2>CSVs pendentes</h2>
                  <p>Lista somente arquivos novos ou ainda não processados no log de leitura.</p>
                </div>
                <div className="etl-window-controls">
                  <button disabled={busy} onClick={verificarCsv}>Verificar CSV pendente</button>
                  <button disabled={busy} onClick={processarCsv}>Processar CSV pendente</button>
                </div>
              </div>

              <div className="etl-window">
                <div>
                  <span className="section-kicker">Janela 2</span>
                  <h2>Atualizar UNION</h2>
                  <p>Atualiza `agrupamento_oms_UNION.parquet` a partir dos parquets mensais.</p>
                </div>
                <button disabled={busy} onClick={atualizarUnion}>Atualizar OMS UNION</button>
              </div>

              <div className="etl-window">
                <div>
                  <span className="section-kicker">Janela 3</span>
                  <h2>Apuração mensal</h2>
                  <p>Filtra início e fim dentro do mês de apuração.</p>
                </div>
                <label>
                  Mês de apuração
                  <input value={mesApuracao} onChange={(event) => setMesApuracao(event.target.value)} />
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={removerCanceladas}
                    onChange={(event) => setRemoverCanceladas(event.target.checked)}
                  />
                  Remover canceladas (`ESTADO_INTRP = 7`)
                </label>
                <button disabled={busy} onClick={gerarApuracao}>Gerar apuração mensal</button>
              </div>

              <div className="etl-window">
                <div>
                  <span className="section-kicker">Janela 4</span>
                  <h2>Materializar pendências</h2>
                  <p>
                    Gera `pendencias_APURACAO_{mesApuracao}.parquet` e atualiza
                    `pendencias_APURACAO_ATUAL.parquet` para as filas de correção.
                  </p>
                </div>
                <button disabled={busy} onClick={materializarPendencias}>
                  Materializar pendências
                </button>
              </div>

              {csvResumo && (
                <>
                  <div className="metric-grid">
                    <div><span>CSV encontrados</span><strong>{csvResumo.arquivos_encontrados ?? 0}</strong></div>
                    <div><span>Processados</span><strong>{csvResumo.arquivos_processados ?? 0}</strong></div>
                    <div><span>Pendentes</span><strong>{csvResumo.arquivos_pendentes ?? 0}</strong></div>
                    <div><span>Com erro</span><strong>{csvResumo.arquivos_com_erro ?? 0}</strong></div>
                  </div>
                  <TabelaRegistros
                    registros={csvResumo.arquivos || []}
                    onSelect={() => undefined}
                    pagina="csv"
                  />
                </>
              )}
            </section>
          </>
        ) : (
          <>
            <header className="page-header">
              <div>
                <h1>{MENU.find(([id]) => id === pagina)?.[1] || "Dashboard"}</h1>
                <p>{MENU.find(([id]) => id === pagina)?.[2] || "Visão operacional"}</p>
              </div>
              <button disabled={busy} onClick={carregarDados}>Atualizar</button>
            </header>

            <div className="metric-grid">
              {metricas.map(([titulo, valorMetrica]) => (
                <div key={titulo}>
                  <span>{titulo}</span>
                  <strong>{valor(valorMetrica)}</strong>
                </div>
              ))}
            </div>

            {pagina === "sobreposicao-uc" && (
              <section className="etl-card uc-fase2-card">
                <div className="etl-window">
                  <div>
                    <span className="section-kicker">Sobreposição UC — Fase 2</span>
                    <h2>Interseção parcial por UC</h2>
                    <p>
                      Analisa registros com `ESTADO_INTRP = 4`, mesmo protocolo e motivo nulo.
                      Quando o início da segunda interrupção cruza o fim da primeira, sugere
                      deslocar `DTHR_INICIO_INTRP_UC` e preencher `NUM_INTRP_INIC_MANOBRA_UCI`.
                    </p>
                  </div>
                  <div className="etl-window-controls">
                    <button disabled={busy} onClick={analisarSobreposicaoUcFase2}>
                      Analisar Fase 2
                    </button>
                    <button disabled={busy} onClick={implantarSobreposicaoUcFase2}>
                      Implantar ajustes
                    </button>
                  </div>
                </div>
                <div className="metric-grid">
                  <div>
                    <span>Ajustes sugeridos</span>
                    <strong>{sobreposicaoUcFase2Resumo?.total_ajustes ?? sobreposicaoUcFase2Resumo?.registros_atualizados ?? 0}</strong>
                  </div>
                  <div>
                    <span>UCs afetadas</span>
                    <strong>{sobreposicaoUcFase2Resumo?.ucs_afetadas ?? 0}</strong>
                  </div>
                  <div>
                    <span>Interrupções ajustadas</span>
                    <strong>{sobreposicaoUcFase2Resumo?.interrupcoes_ajustadas ?? 0}</strong>
                  </div>
                  <div>
                    <span>Minutos interseção</span>
                    <strong>{valor(sobreposicaoUcFase2Resumo?.minutos_interseccao ?? 0)}</strong>
                  </div>
                </div>
              </section>
            )}

            {pagina === "dashboard" && Array.isArray(resumo.rejeitados_por_atividade) && resumo.rejeitados_por_atividade.length > 0 && (
              <section className="records-card activity-summary">
                <span className="section-kicker">Rejeitados por atividade</span>
                <div className="activity-list">
                  {resumo.rejeitados_por_atividade.map((item: any, index: number) => (
                    <div key={`${item.atividade}-${index}`}>
                      <span>{item.atividade || "sem atividade"}</span>
                      <strong>{item.quantidade || 0}</strong>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {pagina === "horario-negativo" && (
              <div className="metric-grid horario-negativo-metrics">
                <div>
                  <span>NUM_SEQ_INTRP distintas</span>
                  <strong>{numSeqDistintasVisiveis}</strong>
                </div>
                <div>
                  <span>Registros visíveis</span>
                  <strong>{registrosVisiveis.length}</strong>
                </div>
                <div>
                  <span>Selecionados</span>
                  <strong>{selecionados.size}</strong>
                </div>
              </div>
            )}

            {pagina === "sobreposicao-interrupcao" && (
              <section className="records-card activity-summary">
                <div className="etl-window">
                  <div>
                    <span className="section-kicker">Análise complementar</span>
                    <h3>Sobreposição temporal por UC</h3>
                    <p>
                      Verifica registros com `ESTADO_INTRP = 4`, mesmo protocolo e
                      `NUM_MOTIVO_TRAT_DIF_UCI` nulo, onde a janela da UC está
                      contida em outra interrupção da mesma UC.
                    </p>
                  </div>
                  <div className="etl-window-controls">
                    <button disabled={busy} onClick={analisarSobreposicaoUc}>
                      Analisar UC
                    </button>
                    <button
                      disabled={busy || !sobreposicaoUcResumo}
                      onClick={implantarSobreposicaoUc}
                    >
                      Implantar motivo 91
                    </button>
                  </div>
                </div>
                <div className="metric-grid">
                  <div>
                    <span>Classificar com 91</span>
                    <strong>
                      {valor(
                        sobreposicaoUcResumo?.registros_classificar_91 ??
                          sobreposicaoUcResumo?.registros_atualizados ??
                          0,
                      )}
                    </strong>
                  </div>
                  <div>
                    <span>UCs afetadas</span>
                    <strong>{valor(sobreposicaoUcResumo?.ucs_afetadas ?? 0)}</strong>
                  </div>
                  <div>
                    <span>Interrupções afetadas</span>
                    <strong>{valor(sobreposicaoUcResumo?.interrupcoes_afetadas ?? 0)}</strong>
                  </div>
                  <div>
                    <span>CHI reduzido estimado</span>
                    <strong>
                      {Number(sobreposicaoUcResumo?.chi_reduzido_estimado || 0).toLocaleString(
                        "pt-BR",
                        { maximumFractionDigits: 2 },
                      )}
                    </strong>
                  </div>
                </div>
                {sobreposicaoUcResumo?.backup && (
                  <div className="audit-grid">
                    <span>Backup</span>
                    <strong>{valor(sobreposicaoUcResumo.backup)}</strong>
                    <span>Log</span>
                    <strong>{valor(sobreposicaoUcResumo.log)}</strong>
                  </div>
                )}
              </section>
            )}

            {pagina === "horario-negativo" && (
              <div className="toolbar">
                <strong>{selecionados.size} selecionado(s)</strong>
                <label>
                  Duração mín.
                  <input
                    type="number"
                    value={duracaoMinFiltro}
                    onChange={(event) => setDuracaoMinFiltro(event.target.value)}
                    placeholder="-180"
                  />
                </label>
                <label>
                  Duração máx.
                  <input
                    type="number"
                    value={duracaoMaxFiltro}
                    onChange={(event) => setDuracaoMaxFiltro(event.target.value)}
                    placeholder="0"
                  />
                </label>
                <span>{registrosVisiveis.length} visível(is)</span>
                {(duracaoMinFiltro || duracaoMaxFiltro) && (
                  <span className="filter-active">Filtro ativo</span>
                )}
                <button
                  onClick={() => {
                    setDuracaoMinFiltro("-180");
                    setDuracaoMaxFiltro("0");
                  }}
                >
                  0 a -3h
                </button>
                <button
                  onClick={() => {
                    setDuracaoMinFiltro("-1440");
                    setDuracaoMaxFiltro("-181");
                  }}
                >
                  -3h a -24h
                </button>
                <button
                  onClick={() => {
                    setDuracaoMinFiltro("");
                    setDuracaoMaxFiltro("-1441");
                  }}
                >
                  &lt; -24h
                </button>
                <button
                  onClick={() => {
                    setDuracaoMinFiltro("");
                    setDuracaoMaxFiltro("");
                  }}
                >
                  Limpar filtro
                </button>
                <button
                  onClick={() => {
                    const seqsVisiveis = new Set(registrosVisiveis.map(chaveNumSeq));
                    setSelecionados(
                      new Set(
                        registros
                          .filter((registro) => seqsVisiveis.has(chaveNumSeq(registro)))
                          .map(chaveRegistro),
                      ),
                    );
                  }}
                >
                  Selecionar todos visíveis
                </button>
                <button onClick={() => setSelecionados(new Set())}>Limpar seleção</button>
              </div>
            )}

            <section className={pagina === "dashboard" ? "workspace-grid dashboard-only" : "workspace-grid"}>
              <section className="records-card">
                <span className="section-kicker">Registros</span>
                <TabelaRegistros
                  registros={registrosVisiveis}
                  registrosOrigem={registros}
                  selecionados={pagina === "dashboard" ? undefined : selecionados}
                  setSelecionados={pagina === "dashboard" ? undefined : setSelecionados}
                  onSelect={setRegistroAtual}
                  pagina={pagina}
                />
              </section>
              {pagina === "horario-negativo" && (
                <TabelaDetalheNumSeq registro={registroAtual} registros={registros} />
              )}
              {pagina !== "dashboard" && (
                <PainelAlteracao
                  registro={registroAtual}
                  justificativa={justificativa}
                  setJustificativa={setJustificativa}
                  selecionados={selecionados}
                  onAcao={agirRegistros}
                  busy={busy}
                />
              )}
            </section>
          </>
        )}
      </section>
    </main>
  );
}

export default App;
