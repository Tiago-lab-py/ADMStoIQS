import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import {
  clearAuthToken,
  criarUsuarioAdmin,
  listarUsuariosAdmin,
  login,
  me,
  resetarSenhaUsuarioAdmin,
  type AdminUsuario,
  type UserResponse,
} from './api'
import {
  executarOrquestradorApuracao,
  exportarPortalTratamentoCsv,
  getEstadoDados,
  getOrquestradorJob,
  gerarPortalTratamentoMassivo,
  getPortalIndicadoresResumo,
  getPortalFilasResumo,
  getPortalIqsResumo,
  getPortalMartResumo,
  getPortalRessarcimentoResumo,
  getPortalTratamentoResumo,
  IndicadoresResumo,
  materializarPortalRessarcimento,
  materializarPortalIndicadores,
  iniciarOrquestradorApuracao,
  EstadoDados,
  IqsResumo,
  MartResumo,
  OrquestradorJob,
  RessarcimentoResumo,
  TratamentoExportacao,
  TratamentoResumo,
} from './gestorApi'
import { FilaResumo } from './filasApi'
import { materializarPortalPendencias } from './gestorApi'
import { featuresEmDesenvolvimento } from './featureFlags'
import './gestorPortal.css'

type PortalPage =
  | 'dashboard'
  | 'etl'
  | 'produto'
  | 'indicadores'
  | 'sobreposicao'
  | 'filas'
  | 'iqs'
  | 'governanca'
  | 'administracao'

type LoadState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  message: string
}

function LoginPage({
  initialMessage,
  onAuthenticated,
}: {
  initialMessage?: string
  onAuthenticated: (user: UserResponse) => void
}) {
  const [usuario, setUsuario] = useState('admin')
  const [senha, setSenha] = useState('')
  const [state, setState] = useState<LoadState>({
    status: initialMessage ? 'idle' : 'idle',
    message: initialMessage || 'Informe usuário e senha para acessar o portal.',
  })

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setState({ status: 'loading', message: 'Aguarde: autenticando usuário...' })
    try {
      const response = await login({ usuario, senha })
      onAuthenticated({
        usuario: response.usuario,
        nome_usuario: response.nome_usuario,
        perfil: response.perfil,
      })
      setState({ status: 'success', message: 'Login efetuado com sucesso.' })
    } catch (error) {
      clearAuthToken()
      setState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao autenticar.',
      })
    }
  }

  return (
    <main className="gestor-login-shell">
      <form className="gestor-login-card" onSubmit={(event) => void submit(event)}>
        <div className="gestor-logo">AI</div>
        <h1>ADMStoIQS</h1>
        <p>Portal unificado governado.</p>

        <label>
          <span>Usuário</span>
          <input
            autoComplete="username"
            onChange={(event) => setUsuario(event.target.value)}
            required
            value={usuario}
          />
        </label>

        <label>
          <span>Senha</span>
          <input
            autoComplete="current-password"
            onChange={(event) => setSenha(event.target.value)}
            required
            type="password"
            value={senha}
          />
        </label>

        <div className={`gestor-status gestor-status--${state.status}`}>{state.message}</div>

        <button className="gestor-primary" disabled={state.status === 'loading'} type="submit">
          Entrar
        </button>

        <small>Dev: admin/admin123 · gestor/gestor123 · usuario/usuario123</small>
      </form>
    </main>
  )
}

const ruleLabels: Record<string, string> = {
  sobreposicao_interrupcao: 'Sobreposição interrupção',
  horario_negativo: 'Horário negativo',
  sem_causa_componente: 'Causa/componente',
}

function formatNumber(value: unknown): string {
  if (typeof value === 'number') return value.toLocaleString('pt-BR')
  if (typeof value === 'string' && value.trim() && Number.isNaN(Number(value))) return value
  return Number(value || 0).toLocaleString('pt-BR')
}

function statusClass(status?: string): string {
  if (status === 'processado' || status === 'concluido') return 'ok'
  if (status === 'erro') return 'error'
  if (status === 'pendente_raw' || status === 'processando' || status === 'aguardando') return 'warn'
  return 'neutral'
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('pt-BR')
}

function formatBytes(value?: number | null): string {
  const bytes = Number(value || 0)
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** index).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${units[index]}`
}

function copyText(value?: string | null): void {
  if (!value) return
  void navigator.clipboard?.writeText(value)
}

function normalizePerfil(perfil?: string): 'admin' | 'gestor' | 'analista' {
  if (perfil === 'admin' || perfil === 'gestor') return perfil
  return 'analista'
}

function canAccessPage(perfil: string | undefined, page: PortalPage): boolean {
  const normalized = normalizePerfil(perfil)
  if (normalized === 'admin') return true
  if (page === 'etl' || page === 'administracao') return false
  if (normalized === 'analista' && page === 'governanca') return false
  return true
}

function Card({
  label,
  value,
  hint,
  accent = 'default',
}: {
  label: string
  value: unknown
  hint?: string
  accent?: 'default' | 'danger' | 'success' | 'warning'
}) {
  return (
    <article className={`gestor-card gestor-card--${accent}`}>
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  )
}

function FileStateCard({
  label,
  arquivo,
}: {
  label: string
  arquivo?: {
    arquivo: string | null
    caminho: string
    existe: boolean
    tamanho_bytes: number
    modificado_em: string | null
  }
}) {
  return (
    <article className="gestor-file-card">
      <div>
        <span>{label}</span>
        <strong>{arquivo?.arquivo ?? 'não encontrado'}</strong>
      </div>
      <span className={`gestor-badge gestor-badge--${arquivo?.existe ? 'ok' : 'warn'}`}>
        {arquivo?.existe ? 'disponível' : 'pendente'}
      </span>
      <small>{formatDateTime(arquivo?.modificado_em)}</small>
      <small>{formatBytes(arquivo?.tamanho_bytes)}</small>
      <code>{arquivo?.caminho ?? '-'}</code>
      <button className="gestor-copy" onClick={() => copyText(arquivo?.caminho)} type="button">
        copiar
      </button>
    </article>
  )
}

function Sidebar({
  activePage,
  estadoDados,
  filasResumo,
  perfil,
  onNavigate,
}: {
  activePage: PortalPage
  estadoDados: EstadoDados | null
  filasResumo: FilaResumo | null
  perfil: string
  onNavigate: (page: PortalPage) => void
}) {
  const total = filasResumo?.total_pendencias ?? 0
  const show = (page: PortalPage) => canAccessPage(perfil, page)
  const ultimaExecucao = estadoDados?.ultima_execucao_orquestrador
  const ultimaExecucaoStatus = String(ultimaExecucao?.['status'] || 'sem execução')
  const ultimaExecucaoHorario = String(
    ultimaExecucao?.['finalizado_em']
      || ultimaExecucao?.['iniciado_em']
      || estadoDados?.tratado_atual?.modificado_em
      || '',
  )

  return (
    <aside className="gestor-sidebar">
      <div className="gestor-brand">
        <div className="gestor-logo">AI</div>
        <div>
          <strong>ADMStoIQS</strong>
          <span>Portal gestor</span>
        </div>
      </div>

      <section className="gestor-auto-card">
        <span>Correções automáticas aplicadas</span>
        <strong>{ultimaExecucaoStatus}</strong>
        <small>{formatDateTime(ultimaExecucaoHorario)}</small>
      </section>

      <section className="gestor-focus">
        <span>FOCO DE ATUAÇÃO</span>
        <strong>{formatNumber(total)}</strong>
        <small>Pendências materializadas</small>
      </section>

      <nav className="gestor-nav" aria-label="Navegação principal">
        <button className={activePage === 'dashboard' ? 'is-active' : ''} onClick={() => onNavigate('dashboard')} type="button">
          <span>Dashboard executivo</span>
          <small>Somente leitura</small>
        </button>
        {show('etl') ? (
          <button className={activePage === 'etl' ? 'is-active' : ''} onClick={() => onNavigate('etl')} type="button">
            <span>ETL operacional</span>
            <small>CSV, UNION e apuração</small>
          </button>
        ) : null}
        <button className={activePage === 'produto' ? 'is-active' : ''} onClick={() => onNavigate('produto')} type="button">
          <span>Produto IQS</span>
          <small>Tratado e CSVs finais</small>
        </button>
        <button className={activePage === 'indicadores' ? 'is-active' : ''} onClick={() => onNavigate('indicadores')} type="button">
          <span>Indicadores</span>
          <small>DEC, FEC, DIC, FIC, DMIC</small>
        </button>
        <button className={activePage === 'filas' ? 'is-active' : ''} onClick={() => onNavigate('filas')} type="button">
          <span>Filas de correção</span>
          <small>Por regra materializada</small>
        </button>
        <button className={activePage === 'sobreposicao' ? 'is-active' : ''} onClick={() => onNavigate('sobreposicao')} type="button">
          <span>Sobreposição</span>
          <small>Interrupção e UC</small>
        </button>
        <button className={activePage === 'iqs' ? 'is-active' : ''} onClick={() => onNavigate('iqs')} type="button">
          <span>Fontes IQS</span>
          <small>Marts externos</small>
        </button>
        {show('governanca') ? (
          <button className={activePage === 'governanca' ? 'is-active' : ''} onClick={() => onNavigate('governanca')} type="button">
            <span>Governança</span>
            <small>Trilha e decisões</small>
          </button>
        ) : null}
        {show('administracao') ? (
          <button className={activePage === 'administracao' ? 'is-active' : ''} onClick={() => onNavigate('administracao')} type="button">
            <span>Administração</span>
            <small>Usuários e perfis</small>
          </button>
        ) : null}
      </nav>
    </aside>
  )
}

function DashboardPage({
  anomes,
  filasResumo,
  iqsResumo,
  martResumo,
  indicadoresResumo,
}: {
  anomes: string
  filasResumo: FilaResumo | null
  iqsResumo: IqsResumo | null
  martResumo: MartResumo | null
  indicadoresResumo: IndicadoresResumo | null
}) {
  const porRegra = useMemo(() => {
    const rules = filasResumo?.por_regra ?? []
    return Object.fromEntries(rules.map((item) => [item.regra, item.total]))
  }, [filasResumo])

  const iqsErros = iqsResumo?.arquivos?.filter((item) => item.status === 'erro').length ?? 0
  const iqsPendentes = iqsResumo?.arquivos?.filter((item) => item.status === 'pendente_raw').length ?? 0
  const copel = indicadoresResumo?.copel

  return (
    <>
      <section className="gestor-grid gestor-grid--cards">
        <Card label="Pendências totais" value={filasResumo?.total_pendencias} hint="Filas materializadas" accent="danger" />
        <Card label="Sobreposição" value={porRegra.sobreposicao_interrupcao} hint="Interrupção/equipamento" />
        <Card label="Horário negativo" value={porRegra.horario_negativo} hint="Correção de data/hora" accent="warning" />
        <Card label="Sem causa/componente" value={porRegra.sem_causa_componente} hint="Campos ausentes" />
        <Card label="Fontes IQS OK" value={iqsResumo?.fontes_processadas} hint={`${iqsPendentes} pendente(s), ${iqsErros} erro(s)`} accent="success" />
      </section>

      <section className="gestor-grid gestor-grid--cards">
        <Card label="DEC antes" value={copel?.dec_antes?.toFixed?.(4) ?? 0} hint="COPEL em horas" />
        <Card label="DEC depois" value={copel?.dec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="FEC antes" value={copel?.fec_antes?.toFixed?.(4) ?? 0} hint="COPEL" />
        <Card label="FEC depois" value={copel?.fec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="DMIC máx." value={copel?.dmic_max_depois?.toFixed?.(2) ?? 0} hint="Depois, em horas" />
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>Visão executiva</h2>
            <p>Resumo somente leitura para acompanhamento da apuração antes das decisões governadas.</p>
          </div>
          <a className="gestor-link" href={`/filas.html?anomes=${encodeURIComponent(anomes)}`}>
            Abrir filas
          </a>
        </div>

        <div className="gestor-kpis">
          <div>
            <span>Arquivo de pendências</span>
            <strong>{filasResumo?.arquivo ?? '-'}</strong>
          </div>
          <div>
            <span>Status IQS</span>
            <strong>{iqsResumo?.status ?? '-'}</strong>
          </div>
          <div>
            <span>Mart resumo</span>
            <strong>{martResumo ? 'disponível' : 'não carregado'}</strong>
          </div>
        </div>
      </section>
    </>
  )
}

function IndicadoresPage({
  anomes,
  indicadoresResumo,
  ressarcimentoResumo,
  onResumoUpdate,
  onRessarcimentoUpdate,
}: {
  anomes: string
  indicadoresResumo: IndicadoresResumo | null
  ressarcimentoResumo: RessarcimentoResumo | null
  onResumoUpdate: (resumo: IndicadoresResumo) => void
  onRessarcimentoUpdate: (resumo: RessarcimentoResumo) => void
}) {
  const [actionState, setActionState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando materialização dos indicadores.',
  })

  const materializar = async () => {
    setActionState({ status: 'loading', message: 'Aguarde processamento: materializando DEC/FEC/DIC/FIC/DMIC...' })
    try {
      await materializarPortalIndicadores(anomes)
      const resumo = await getPortalIndicadoresResumo(anomes)
      onResumoUpdate(resumo)
      setActionState({ status: 'success', message: 'Processamento concluído: indicadores atualizados.' })
    } catch (error) {
      setActionState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao materializar indicadores.',
      })
    }
  }

  const materializarRessarcimento = async () => {
    setActionState({ status: 'loading', message: 'Aguarde processamento: materializando ressarcimento estimado...' })
    try {
      const resumo = await materializarPortalRessarcimento(anomes)
      onRessarcimentoUpdate(resumo)
      setActionState({ status: 'success', message: 'Processamento concluído: ressarcimento atualizado.' })
    } catch (error) {
      setActionState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao materializar ressarcimento.',
      })
    }
  }

  const copel = indicadoresResumo?.copel
  const valorAntes = ressarcimentoResumo?.valor_estimado_antes ?? 0
  const valorDepois = ressarcimentoResumo?.valor_estimado_depois ?? 0
  const ganhoEstimado = valorAntes - valorDepois

  return (
    <>
      <section className="gestor-grid gestor-grid--cards">
        <Card label="DEC antes" value={copel?.dec_antes?.toFixed?.(4) ?? 0} hint="COPEL em horas" />
        <Card label="DEC depois" value={copel?.dec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="FEC antes" value={copel?.fec_antes?.toFixed?.(4) ?? 0} hint="COPEL" />
        <Card label="FEC depois" value={copel?.fec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="DMIC máx. depois" value={copel?.dmic_max_depois?.toFixed?.(2) ?? 0} hint="Horas" />
      </section>

      <section className="gestor-grid gestor-grid--cards">
        <Card label="Ressarc. antes" value={valorAntes.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} hint="Estimativa operacional" />
        <Card label="Ressarc. depois" value={valorDepois.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} hint="Após tratamento" accent="success" />
        <Card label="Redução estimada" value={ganhoEstimado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} hint="Antes - depois" accent={ganhoEstimado >= 0 ? 'success' : 'warning'} />
        <Card label="Violações antes" value={ressarcimentoResumo?.violacoes_antes ?? 0} hint="UCs/linhas com violação" />
        <Card label="Violações depois" value={ressarcimentoResumo?.violacoes_depois ?? 0} hint="Após tratamento" />
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>Indicadores de continuidade</h2>
            <p>Comparativo antes/depois do tratamento massivo para apoiar decisão do gestor.</p>
          </div>
          <button className="gestor-primary" onClick={() => void materializar()} type="button">
            Materializar indicadores
          </button>
          <button className="gestor-primary" onClick={() => void materializarRessarcimento()} type="button">
            Materializar ressarcimento
          </button>
        </div>

        <div className={`gestor-status gestor-status--${actionState.status}`}>{actionState.message}</div>

        <div className="gestor-kpis gestor-kpis--single">
          <div>
            <span>Arquivo comparativo</span>
            <strong>{indicadoresResumo?.arquivo ?? '-'}</strong>
          </div>
          <div>
            <span>Fonte denominador</span>
            <strong>{copel?.fonte_denominador ?? '-'}</strong>
          </div>
          <div>
            <span>Regra líquido</span>
            <strong>{copel?.regra_liquido ?? '-'}</strong>
          </div>
          <div>
            <span>Fórmula ressarcimento</span>
            <strong>{ressarcimentoResumo?.status_formula ?? '-'}</strong>
          </div>
        </div>
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>Regionais</h2>
            <p>Impacto do tratamento por regional.</p>
          </div>
        </div>

        <div className="gestor-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Regional</th>
                <th>UCs</th>
                <th>DEC antes</th>
                <th>DEC depois</th>
                <th>Δ DEC</th>
                <th>FEC antes</th>
                <th>FEC depois</th>
                <th>Δ FEC</th>
                <th>DMIC depois</th>
              </tr>
            </thead>
            <tbody>
              {(indicadoresResumo?.regionais ?? []).map((item) => (
                <tr key={`${item.regional_origem}-${item.cod_conjunto_aneel}`}>
                  <td>{item.regional_origem}</td>
                  <td>{formatNumber(item.quantidade_ucs)}</td>
                  <td>{item.dec_antes?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.dec_depois?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.dec_delta?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.fec_antes?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.fec_depois?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.fec_delta?.toFixed?.(4) ?? '-'}</td>
                  <td>{item.dmic_max_depois?.toFixed?.(2) ?? '-'}</td>
                </tr>
              ))}
              {!indicadoresResumo?.regionais?.length ? (
                <tr>
                  <td colSpan={9}>Indicadores ainda não materializados para a competência.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function FilasPage({ anomes, filasResumo }: { anomes: string; filasResumo: FilaResumo | null }) {
  return (
    <section className="gestor-panel">
      <div className="gestor-panel-title">
        <div>
          <h2>Filas de correção</h2>
          <p>As filas detalhadas já estão no React oficial e usam `pendencias_APURACAO_ATUAL.parquet`.</p>
        </div>
        <a className="gestor-link" href={`/filas.html?anomes=${encodeURIComponent(anomes)}`}>
          Abrir tela de filas
        </a>
      </div>

      <div className="gestor-rule-list">
        {(filasResumo?.por_regra ?? []).map((item) => (
          <article key={item.regra}>
            <strong>
              <span>{ruleLabels[item.regra] ?? item.regra}</span>
              <span>{formatNumber(item.total)}</span>
            </strong>
            <small>{formatNumber(item.registros_distintos)} registro(s) distinto(s)</small>
          </article>
        ))}
      </div>
    </section>
  )
}

function SobreposicaoPage({ anomes, filasResumo }: { anomes: string; filasResumo: FilaResumo | null }) {
  const regras = useMemo(() => {
    const porRegra = filasResumo?.por_regra ?? []
    return Object.fromEntries(porRegra.map((item) => [item.regra, item.total]))
  }, [filasResumo])

  return (
    <>
      <section className="gestor-grid gestor-grid--cards">
        <Card label="Sobreposição interrupção" value={regras.sobreposicao_interrupcao} hint="Equipamento e intervalo" accent="warning" />
        <Card label="Sobreposição UC" value={regras.sobreposicao_uc ?? 0} hint="UC, protocolo e intervalo" accent="warning" />
        <Card label="Horário negativo" value={regras.horario_negativo} hint="Impacta análise temporal" />
        <Card label="Competência" value={anomes} hint="Apuração ativa" accent="success" />
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>Jornada de sobreposição</h2>
            <p>
              A aba consolida as duas frentes: interrupções sobrepostas por equipamento e intersecções por UC.
              A implantação continua governada no operacional.
            </p>
          </div>
          <a className="gestor-link" href="/operacional.html">
            Abrir operacional
          </a>
        </div>

        <div className="gestor-roadmap gestor-roadmap--two">
          <article>
            <strong>Fase 1 — Interrupção/equipamento</strong>
            <span>
              Classifica registros contidos em outra interrupção do mesmo `NUM_OPER_CHV_INTRP` e prepara motivo 91.
            </span>
          </article>
          <article>
            <strong>Fase 2 — Sobreposição UC</strong>
            <span>
              Ajusta intersecções por `NUM_UC_UCI`, mesmo protocolo e motivo nulo, mantendo trilha de alteração.
            </span>
          </article>
        </div>
      </section>
    </>
  )
}

function EtlPage({
  anomes,
  authUser,
  filasResumo,
  estadoDados,
  onFilasResumoUpdate,
  onEstadoDadosUpdate,
}: {
  anomes: string
  authUser: UserResponse
  filasResumo: FilaResumo | null
  estadoDados: EstadoDados | null
  onFilasResumoUpdate: (resumo: FilaResumo) => void
  onEstadoDadosUpdate: (estado: EstadoDados) => void
}) {
  const [pendenciasState, setPendenciasState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando materialização das pendências.',
  })
  const [jobState, setJobState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando execução da atualização diária.',
  })
  const [job, setJob] = useState<OrquestradorJob | null>(null)

  useEffect(() => {
    if (!job?.job_id || !['aguardando', 'processando'].includes(job.status)) return

    const interval = window.setInterval(() => {
      getOrquestradorJob(job.job_id)
        .then((updated) => {
          setJob(updated)
          if (updated.status === 'concluido') {
            setJobState({
              status: 'success',
              message: `Processamento concluído: ${updated.mensagem || 'trilha operacional finalizada.'}`,
            })
            getEstadoDados(anomes).then(onEstadoDadosUpdate).catch(() => undefined)
          }
          if (updated.status === 'erro') {
            setJobState({
              status: 'error',
              message: updated.erro || updated.mensagem || 'Falha na atualização diária.',
            })
          }
        })
        .catch((error) => {
          setJobState({
            status: 'error',
            message: error instanceof Error ? error.message : 'Falha ao consultar job.',
          })
        })
    }, 5000)

    return () => window.clearInterval(interval)
  }, [anomes, job?.job_id, job?.status, onEstadoDadosUpdate])

  const atualizarEstadoDados = async () => {
    const estado = await getEstadoDados(anomes)
    onEstadoDadosUpdate(estado)
  }

  const executarTrilhaCompletaJob = async () => {
    setJobState({
      status: 'loading',
      message: 'Aguarde processamento: criando job da atualização diária...',
    })
    try {
      const created = await iniciarOrquestradorApuracao({
        anomes,
        usuario: authUser.usuario,
        perfil: authUser.perfil,
      })
      setJob(created)
      setJobState({
        status: 'loading',
        message: `Job ${created.job_id} criado. Você pode navegar; o cockpit continuará acompanhando.`,
      })
    } catch (error) {
      setJobState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao iniciar atualização diária.',
      })
    }
  }
  const [orquestradorState, setOrquestradorState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando execução da trilha operacional completa.',
  })
  const [orquestradorEtapas, setOrquestradorEtapas] = useState<string[]>([])

  const materializarPendencias = async () => {
    setPendenciasState({
      status: 'loading',
      message: 'Aguarde processamento: materializando pendências da apuração...',
    })
    try {
      const result = await materializarPortalPendencias(anomes)
      const resumo = await getPortalFilasResumo(anomes)
      onFilasResumoUpdate(resumo)
      await atualizarEstadoDados()
      setPendenciasState({
        status: 'success',
        message: `Processamento concluído: ${formatNumber(result.total_pendencias)} pendência(s) materializada(s).`,
      })
    } catch (error) {
      setPendenciasState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao materializar pendências.',
      })
    }
  }

  const executarTrilhaCompleta = async () => {
    const confirmar = window.confirm(
      `Executar a trilha completa da competência ${anomes}? ` +
        'Esse fluxo pode demorar e gera logs de orquestração.',
    )
    if (!confirmar) return

    setOrquestradorEtapas([])
    setOrquestradorState({
      status: 'loading',
      message: 'Aguarde processamento: executando trilha completa da apuração...',
    })

    try {
      const result = await executarOrquestradorApuracao({
        anomes,
        processar_csv: true,
        atualizar_union: true,
        gerar_apuracao: true,
        materializar_pendencias: true,
        materializar_sobreposicao_interrupcao: true,
        gerar_tratado: true,
        materializar_indicadores: true,
        materializar_ressarcimento: true,
        remover_canceladas: true,
      })
      const resumo = await getPortalFilasResumo(anomes)
      onFilasResumoUpdate(resumo)
      setOrquestradorEtapas(
        result.etapas.map((etapa, index) => `${index + 1}. ${etapa.etapa}: ${etapa.status} — ${etapa.mensagem}`),
      )
      setOrquestradorState({
        status: result.status === 'processado' ? 'success' : 'error',
        message:
          result.status === 'processado'
            ? 'Processamento concluído: trilha operacional executada.'
            : 'Processamento concluído com erro: revise o log do orquestrador.',
      })
    } catch (error) {
      setOrquestradorState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao executar trilha completa.',
      })
    }
  }

  const regras = filasResumo?.por_regra ?? {}
  const validacaoManual = Math.max(
    0,
    (filasResumo?.total_pendencias ?? 0)
      - (regras.horario_negativo ?? 0)
      - (regras.sem_causa_componente ?? 0)
      - (regras.sobreposicao_interrupcao ?? 0),
  )

  const etapas = job?.etapas?.length
    ? job.etapas
    : [
        { ordem: 1, etapa: 'CSV pendentes', status: 'aguardando', mensagem: '' },
        { ordem: 2, etapa: 'OMS UNION', status: 'aguardando', mensagem: '' },
        { ordem: 3, etapa: 'Apuração mensal', status: 'aguardando', mensagem: '' },
        { ordem: 4, etapa: 'Pendências', status: 'aguardando', mensagem: '' },
        { ordem: 5, etapa: 'Sobreposições', status: 'aguardando', mensagem: '' },
        { ordem: 6, etapa: 'Base tratada', status: 'aguardando', mensagem: '' },
        { ordem: 7, etapa: 'Indicadores', status: 'aguardando', mensagem: '' },
        { ordem: 8, etapa: 'Ressarcimento', status: 'aguardando', mensagem: '' },
      ]

  return (
    <section className="gestor-panel">
      <div className="gestor-panel-title">
        <div>
          <h2>Cockpit de Operação</h2>
          <p>Atualização diária governada, com job em background e rastreabilidade dos arquivos.</p>
        </div>
        <div className="gestor-actions">
          <button className="gestor-primary" onClick={() => void executarTrilhaCompletaJob()} type="button">
            Executar atualização diária
          </button>
          <a className="gestor-link" href="/operacional.html">
            Abrir ETL completo
          </a>
        </div>
      </div>

      <div className={`gestor-status gestor-status--${jobState.status}`}>{jobState.message}</div>

      <section className="gestor-panel gestor-panel--nested">
        <div className="gestor-panel-title">
          <div>
            <h2>Trilha completa</h2>
            <p>O job retorna imediatamente e continua em backend; a navegação do usuário fica livre.</p>
          </div>
          {job ? <span className={`gestor-badge gestor-badge--${statusClass(job.status)}`}>{job.status}</span> : null}
        </div>

        <div className="gestor-job-grid">
          {etapas.map((etapa) => (
            <article key={`${etapa.ordem}-${etapa.etapa}`} className="gestor-job-step">
              <span>{String(etapa.ordem).padStart(2, '0')}</span>
              <strong>{etapa.etapa}</strong>
              <small className={`gestor-badge gestor-badge--${statusClass(etapa.status)}`}>{etapa.status}</small>
              {etapa.mensagem ? <em>{etapa.mensagem}</em> : null}
            </article>
          ))}
        </div>

        {job ? (
          <div className="gestor-kpis gestor-kpis--single">
            <div>
              <span>Job ativo</span>
              <strong>{job.job_id}</strong>
            </div>
            <div>
              <span>Etapa atual</span>
              <strong>{job.etapa_atual || '-'}</strong>
            </div>
            <div>
              <span>Última atualização</span>
              <strong>{formatDateTime(job.finalizado_em || job.iniciado_em || job.criado_em)}</strong>
            </div>
          </div>
        ) : null}
      </section>

      <section className="gestor-panel gestor-panel--nested">
        <div className="gestor-panel-title">
          <div>
            <h2>Foco de atuação</h2>
            <p>Pendências separadas por criticidade operacional para priorizar a atuação.</p>
          </div>
        </div>
        <div className="gestor-grid gestor-grid--cards gestor-grid--criticity">
          <Card label="Horário" value={regras.horario_negativo ?? 0} hint="Datas negativas e fuso" accent="danger" />
          <Card label="Causa/componente" value={regras.sem_causa_componente ?? 0} hint="Campos ausentes" accent="warning" />
          <Card label="Sobreposição" value={regras.sobreposicao_interrupcao ?? 0} hint="Interrupção e UC" accent="danger" />
          <Card label="Validação manual" value={validacaoManual} hint="Pendências restantes" />
        </div>
      </section>

      <section className="gestor-panel gestor-panel--nested">
        <div className="gestor-panel-title">
          <div>
            <h2>Estado dos dados</h2>
            <p>Arquivos e logs que sustentam a operação diária do middleware.</p>
          </div>
          <button className="gestor-primary" onClick={() => void atualizarEstadoDados()} type="button">
            Atualizar estado
          </button>
        </div>

        <div className="gestor-file-grid">
          <FileStateCard label="Último CSV processado" file={estadoDados?.ultimo_csv_processado} />
          <FileStateCard label="Log leitura CSV" file={estadoDados?.log_leitura_csv} />
          <FileStateCard label="Log OMS UNION" file={estadoDados?.log_oms_union} />
          <FileStateCard label="Log orquestrador" file={estadoDados?.log_orquestrador} />
          <FileStateCard label="Apuração atual" file={estadoDados?.apuracao_atual} />
          <FileStateCard label="Tratado atual" file={estadoDados?.tratado_atual} />
          <FileStateCard label="Indicadores atualizados em" file={estadoDados?.indicadores_atualizados} />
          <FileStateCard label="Ressarcimento atualizado em" file={estadoDados?.ressarcimento_atualizado} />
        </div>
      </section>

      <div className="gestor-roadmap">
        <article>
          <strong>1. CSVs pendentes</strong>
          <span>Compara `P:\Common\IQS\ADMS\Backup` com `log_leitura_csv.parquet`.</span>
        </article>
        <article>
          <strong>2. Atualizar OMS UNION</strong>
          <span>Regera o consolidado `agrupamento_oms_UNION.parquet`.</span>
        </article>
        <article>
          <strong>3. Apuração mensal</strong>
          <span>Gera `agrupamento_oms_APURACAO_{anomes}.parquet`.</span>
        </article>
        <article>
          <strong>4. Pendências materializadas</strong>
          <span>Materializa filas para análise governada.</span>
        </article>
      </div>

      <section className="gestor-panel gestor-panel--nested">
        <div className="gestor-panel-title">
          <div>
            <h2>Trilha completa — implantação diária</h2>
            <p>
              Executa CSVs pendentes, OMS UNION, apuração mensal, pendências, sobreposição,
              base tratada, indicadores e ressarcimento com log nominal.
            </p>
          </div>
          <button
            className="gestor-primary"
            disabled={orquestradorState.status === 'loading'}
            onClick={() => void executarTrilhaCompleta()}
            type="button"
          >
            Executar trilha completa
          </button>
        </div>
        <div className={`gestor-status gestor-status--${orquestradorState.status}`}>{orquestradorState.message}</div>
        {orquestradorEtapas.length ? (
          <div className="gestor-roadmap gestor-roadmap--two">
            {orquestradorEtapas.map((etapa) => (
              <article key={etapa}>
                <span>{etapa}</span>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="gestor-panel gestor-panel--nested">
        <div className="gestor-panel-title">
          <div>
            <h2>Janela 4 — Materializar pendências</h2>
            <p>
              Gera `pendencias_APURACAO_{anomes}.parquet` e atualiza
              `pendencias_APURACAO_ATUAL.parquet` para as filas de correção.
            </p>
          </div>
          <button className="gestor-primary" onClick={() => void materializarPendencias()} type="button">
            Materializar pendências
          </button>
        </div>
        <div className={`gestor-status gestor-status--${pendenciasState.status}`}>{pendenciasState.message}</div>
      </section>

      <div className="gestor-kpis gestor-kpis--single">
        <div>
          <span>Competência selecionada</span>
          <strong>{anomes}</strong>
        </div>
        <div>
          <span>Observação</span>
          <strong>O portal gestor é executivo; o ETL completo fica em tela operacional dedicada.</strong>
        </div>
      </div>
    </section>
  )
}

function ProdutoIqsPage({
  anomes,
  tratamentoResumo,
  onResumoUpdate,
  onRefresh,
}: {
  anomes: string
  tratamentoResumo: TratamentoResumo | null
  onResumoUpdate: (resumo: TratamentoResumo) => void
  onRefresh: () => Promise<void>
}) {
  const [actionState, setActionState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando ação do gestor.',
  })
  const [exportacao, setExportacao] = useState<TratamentoExportacao | null>(null)

  const remocoes = useMemo(() => {
    return Object.fromEntries((tratamentoResumo?.remocoes ?? []).map((item) => [item.regra, item.total]))
  }, [tratamentoResumo])

  const gerarTratado = async () => {
    setActionState({ status: 'loading', message: 'Aguarde processamento: gerando base tratada...' })
    try {
      const result = await gerarPortalTratamentoMassivo(anomes)
      onResumoUpdate({
        anomes: result.anomes,
        parquet: result.parquet,
        log: result.log,
        status: result.status,
        total_final: result.total_final,
        remocoes: [
          { regra: 'horario_negativo', total: result.removido_horario_negativo ?? 0 },
          { regra: 'sem_causa_componente', total: result.removido_sem_causa_componente ?? 0 },
          { regra: 'sobreposicao_interrupcao', total: result.removido_sobreposicao_interrupcao ?? 0 },
        ],
      })
      setActionState({ status: 'success', message: 'Processamento concluído: base tratada gerada.' })
      await onRefresh()
    } catch (error) {
      setActionState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao gerar base tratada.',
      })
    }
  }

  const exportarCsv = async () => {
    setActionState({ status: 'loading', message: 'Aguarde processamento: exportando CSVs regionais...' })
    try {
      const result = await exportarPortalTratamentoCsv(anomes)
      setExportacao(result)
      setActionState({
        status: 'success',
        message: `Processamento concluído: ${result.total_arquivos} arquivo(s) exportado(s).`,
      })
    } catch (error) {
      setActionState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao exportar CSVs tratados.',
      })
    }
  }

  return (
    <>
      <section className="gestor-grid gestor-grid--cards">
        <Card label="Status tratado" value={tratamentoResumo?.status ?? 'pendente'} hint="Base mensal final" accent="success" />
        <Card label="Total final" value={tratamentoResumo?.total_final} hint="Linhas após limpeza" />
        <Card label="Horário negativo" value={remocoes.horario_negativo} hint="Removidos" accent="warning" />
        <Card label="Causa/componente" value={remocoes.sem_causa_componente} hint="Removidos" />
        <Card label="Sobreposição" value={remocoes.sobreposicao_interrupcao} hint="Removidos" accent="danger" />
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>Produto IQS massivo</h2>
            <p>Gera a base tratada e exporta CSVs regionais com o layout esperado pelo IQS.</p>
          </div>
          <div className="gestor-actions">
            <button className="gestor-primary" onClick={() => void gerarTratado()} type="button">
              Gerar base tratada
            </button>
            <button className="gestor-primary" onClick={() => void exportarCsv()} type="button">
              Exportar CSV IQS
            </button>
          </div>
        </div>

        <div className={`gestor-status gestor-status--${actionState.status}`}>{actionState.message}</div>

        <div className="gestor-kpis gestor-kpis--single">
          <div>
            <span>Parquet tratado</span>
            <strong>{tratamentoResumo?.parquet ?? '-'}</strong>
          </div>
          <div>
            <span>Log de tratamento</span>
            <strong>{tratamentoResumo?.log ?? '-'}</strong>
          </div>
        </div>
      </section>

      <section className="gestor-panel">
        <div className="gestor-panel-title">
          <div>
            <h2>CSVs exportados</h2>
            <p>Arquivos gerados em `data/exports/iqs`, separados por regional de origem.</p>
          </div>
          <strong>{formatNumber(exportacao?.total_linhas)} linha(s)</strong>
        </div>

        <div className="gestor-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Regional</th>
                <th>Linhas</th>
                <th>Arquivo</th>
              </tr>
            </thead>
            <tbody>
              {(exportacao?.arquivos ?? []).map((arquivo) => (
                <tr key={arquivo.arquivo}>
                  <td>{arquivo.regional}</td>
                  <td>{formatNumber(arquivo.linhas)}</td>
                  <td>{arquivo.arquivo}</td>
                </tr>
              ))}
              {!exportacao?.arquivos?.length ? (
                <tr>
                  <td colSpan={3}>Nenhuma exportação executada nesta sessão.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function IqsPage({ iqsResumo }: { iqsResumo: IqsResumo | null }) {
  return (
    <section className="gestor-panel">
      <div className="gestor-panel-title">
        <div>
          <h2>Fontes IQS materializadas</h2>
          <p>Resumo das fontes externas disponíveis para apoiar conciliação e indicadores.</p>
        </div>
      </div>

      <div className="gestor-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Fonte</th>
              <th>Status</th>
              <th>Raw</th>
              <th>Mart</th>
              <th>Erro</th>
            </tr>
          </thead>
          <tbody>
            {(iqsResumo?.arquivos ?? []).map((item) => (
              <tr key={item.fonte}>
                <td>{item.fonte}</td>
                <td>
                  <span className={`gestor-badge gestor-badge--${statusClass(item.status)}`}>{item.status}</span>
                </td>
                <td>{formatNumber(item.linhas_raw)}</td>
                <td>{formatNumber(item.linhas_mart)}</td>
                <td>{item.erro || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function GovernancaPage() {
  return (
    <section className="gestor-panel">
      <h2>Governança e trilha de decisão</h2>
      <a className="gestor-link" href="/decisoes.html?anomes=202605">
        Abrir decisão governada
      </a>
      <p>
        Próxima etapa: conectar validação, rejeição e ignorar-regra ao fluxo nominal com usuário, PC, IP,
        justificativa e log de alteração.
      </p>
      <div className="gestor-roadmap">
        <article>
          <strong>1. Dashboard somente leitura</strong>
          <span>Sem alteração direta nos dados.</span>
        </article>
        <article>
          <strong>2. Filas por regra</strong>
          <span>Analista atua em pendências materializadas.</span>
        </article>
        <article>
          <strong>3. Decisão governada</strong>
          <span>Gestor aprova/rejeita conforme perfil.</span>
        </article>
        <article>
          <strong>4. Exportação IQS</strong>
          <span>CSV final gerado com rastreabilidade.</span>
        </article>
      </div>
    </section>
  )
}

function AdministracaoPage() {
  return (
    <section className="gestor-panel">
      <div className="gestor-panel-title">
        <div>
          <h2>Administração</h2>
          <p>Preparação da governança de acesso sem quebrar o login atual.</p>
        </div>
        <span className="gestor-badge gestor-badge--warn">Em desenvolvimento</span>
      </div>

      <div className="gestor-roadmap gestor-roadmap--two">
        <article>
          <strong>Cadastro por e-mail</strong>
          <span>Solicitação entra pendente para aprovação do administrador.</span>
        </article>
        <article>
          <strong>Perfis</strong>
          <span>Admin, gestor e analista POS com permissões separadas.</span>
        </article>
        <article>
          <strong>Primeiro acesso</strong>
          <span>Senha inicial `inicio123`, troca obrigatória e segundo fator de 4 dígitos.</span>
        </article>
        <article>
          <strong>Auditoria</strong>
          <span>Parquet local com usuário, perfil, ação, PC/IP e trilha da alteração.</span>
        </article>
      </div>

      <section className="gestor-panel gestor-panel--nested">
        <h3>Módulos visíveis em desenvolvimento</h3>
        <div className="gestor-feature-grid">
          {featuresEmDesenvolvimento.map((feature) => (
            <article className="gestor-feature-card" key={feature.id}>
              <span className="gestor-badge gestor-badge--warn">Em desenvolvimento</span>
              <strong>{feature.titulo}</strong>
              <p>{feature.descricao}</p>
              <small>Perfil alvo: {feature.perfilAlvo}</small>
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}

export function GestorPortalApp() {
  const [anomes, setAnomes] = useState('202605')
  const [activePage, setActivePage] = useState<PortalPage>('dashboard')
  const [authUser, setAuthUser] = useState<UserResponse | null>(null)

  useEffect(() => {
    if (authUser && !canAccessPage(authUser.perfil, activePage)) {
      setActivePage('dashboard')
    }
  }, [activePage, authUser])
  const [authState, setAuthState] = useState<LoadState>({
    status: 'loading',
    message: 'Validando sessão...',
  })
  const [loadState, setLoadState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando carregamento.',
  })
  const [filasResumo, setFilasResumo] = useState<FilaResumo | null>(null)
  const [iqsResumo, setIqsResumo] = useState<IqsResumo | null>(null)
  const [martResumo, setMartResumo] = useState<MartResumo | null>(null)
  const [tratamentoResumo, setTratamentoResumo] = useState<TratamentoResumo | null>(null)
  const [indicadoresResumo, setIndicadoresResumo] = useState<IndicadoresResumo | null>(null)
  const [ressarcimentoResumo, setRessarcimentoResumo] = useState<RessarcimentoResumo | null>(null)
  const [estadoDados, setEstadoDados] = useState<EstadoDados | null>(null)

  useEffect(() => {
    let mounted = true

    me()
      .then((user) => {
        if (!mounted) return
        setAuthUser(user)
        setAuthState({ status: 'success', message: 'Sessão validada.' })
      })
      .catch(() => {
        if (!mounted) return
        clearAuthToken()
        setAuthUser(null)
        setAuthState({ status: 'idle', message: 'Faça login para acessar o portal.' })
      })

    return () => {
      mounted = false
    }
  }, [])

  const loadPortal = useCallback(async () => {
    setLoadState({ status: 'loading', message: 'Aguarde processamento: carregando resumos materializados...' })
    try {
      const [filas, iqs, mart, tratamento, indicadores, ressarcimento, estado] = await Promise.allSettled([
        getPortalFilasResumo(anomes),
        getPortalIqsResumo(anomes),
        getPortalMartResumo(),
        getPortalTratamentoResumo(anomes),
        getPortalIndicadoresResumo(anomes),
        getPortalRessarcimentoResumo(anomes),
        getEstadoDados(anomes),
      ])

      if (filas.status === 'fulfilled') setFilasResumo(filas.value)
      if (iqs.status === 'fulfilled') setIqsResumo(iqs.value)
      if (mart.status === 'fulfilled') setMartResumo(mart.value)
      if (tratamento.status === 'fulfilled') setTratamentoResumo(tratamento.value)
      if (indicadores.status === 'fulfilled') setIndicadoresResumo(indicadores.value)
      if (ressarcimento.status === 'fulfilled') setRessarcimentoResumo(ressarcimento.value)
      if (estado.status === 'fulfilled') setEstadoDados(estado.value)

      const errors = [filas, iqs, mart, tratamento, indicadores, ressarcimento, estado].filter(
        (result) => result.status === 'rejected',
      ).length
      setLoadState({
        status: errors ? 'error' : 'success',
        message: errors
          ? `Carregamento parcial concluído com ${errors} fonte(s) indisponível(is).`
          : 'Processamento concluído: portal atualizado.',
      })
    } catch (error) {
      setLoadState({
        status: 'error',
        message: error instanceof Error ? error.message : 'Falha ao carregar portal.',
      })
    }
  }, [anomes])

  useEffect(() => {
    if (authUser) void loadPortal()
  }, [authUser, loadPortal])

  const logout = () => {
    clearAuthToken()
    localStorage.removeItem('admstoiqs_user')
    localStorage.removeItem('user')
    setAuthUser(null)
    setLoadState({ status: 'idle', message: 'Sessão encerrada.' })
  }

  if (!authUser) {
    return (
      <LoginPage
        initialMessage={authState.message}
        onAuthenticated={(user) => {
          setAuthUser(user)
          setAuthState({ status: 'success', message: 'Sessão iniciada.' })
        }}
      />
    )
  }

  return (
    <div className="gestor-shell">
      <Sidebar
        activePage={activePage}
        estadoDados={estadoDados}
        filasResumo={filasResumo}
        perfil={authUser.perfil}
        onNavigate={setActivePage}
      />

      <main className="gestor-main">
        <header className="gestor-header">
          <div>
            <span className="gestor-pill">Versão definitiva · Portal unificado</span>
            <h1>ADMStoIQS</h1>
            <p>Middleware local para reduzir falhas entre ADMS e IQS.</p>
          </div>
          <button className="gestor-primary" onClick={() => void loadPortal()} type="button">
            Atualizar portal
          </button>
          <div className="gestor-userbox">
            <span>{authUser.nome_usuario}</span>
            <strong>{authUser.perfil}</strong>
            <button onClick={logout} type="button">Sair</button>
          </div>
          <label className="gestor-filter">
            <span>Competência</span>
            <input
              maxLength={6}
              onChange={(event) => setAnomes(event.target.value)}
              value={anomes}
            />
          </label>
        </header>

        <div className={`gestor-status gestor-status--${loadState.status}`}>{loadState.message}</div>

        {activePage === 'dashboard' ? (
          <DashboardPage
            anomes={anomes}
            filasResumo={filasResumo}
            indicadoresResumo={indicadoresResumo}
            iqsResumo={iqsResumo}
            martResumo={martResumo}
          />
        ) : null}
        {activePage === 'etl' ? (
          <EtlPage
            anomes={anomes}
            authUser={authUser}
            filasResumo={filasResumo}
            estadoDados={estadoDados}
            onEstadoDadosUpdate={setEstadoDados}
            onFilasResumoUpdate={setFilasResumo}
          />
        ) : null}
        {activePage === 'produto' ? (
          <ProdutoIqsPage
            anomes={anomes}
            tratamentoResumo={tratamentoResumo}
            onRefresh={loadPortal}
            onResumoUpdate={setTratamentoResumo}
          />
        ) : null}
        {activePage === 'indicadores' ? (
          <IndicadoresPage
            anomes={anomes}
            indicadoresResumo={indicadoresResumo}
            ressarcimentoResumo={ressarcimentoResumo}
            onResumoUpdate={setIndicadoresResumo}
            onRessarcimentoUpdate={setRessarcimentoResumo}
          />
        ) : null}
        {activePage === 'filas' ? <FilasPage anomes={anomes} filasResumo={filasResumo} /> : null}
        {activePage === 'sobreposicao' ? <SobreposicaoPage anomes={anomes} filasResumo={filasResumo} /> : null}
        {activePage === 'iqs' ? <IqsPage iqsResumo={iqsResumo} /> : null}
        {activePage === 'governanca' ? <GovernancaPage /> : null}
        {activePage === 'administracao' ? <AdministracaoUsuariosPage authUser={authUser} /> : null}
      </main>
    </div>
  )
}

function AdministracaoUsuariosPage({ authUser }: { authUser: UserResponse }) {
  const [usuarios, setUsuarios] = useState<AdminUsuario[]>([])
  const [form, setForm] = useState({
    email: '',
    nome_usuario: '',
    perfil: 'analista' as 'admin' | 'gestor' | 'analista',
  })
  const [state, setState] = useState<LoadState>({ status: 'idle', message: '' })

  const carregarUsuarios = useCallback(async () => {
    setState({ status: 'loading', message: 'Aguarde processamento: carregando usuários...' })
    try {
      const response = await listarUsuariosAdmin()
      setUsuarios(response.usuarios)
      setState({ status: 'success', message: 'Usuários carregados.' })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Falha ao carregar usuários.' })
    }
  }, [])

  useEffect(() => {
    if (authUser.perfil === 'admin') {
      void carregarUsuarios()
    }
  }, [authUser.perfil, carregarUsuarios])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setState({ status: 'loading', message: 'Aguarde processamento: cadastrando usuário...' })
    try {
      const response = await criarUsuarioAdmin(form)
      setForm({ email: '', nome_usuario: '', perfil: 'analista' })
      await carregarUsuarios()
      setState({
        status: 'success',
        message: `Usuário ${response.usuario.email} cadastrado. Senha inicial: ${response.usuario.senha_inicial || 'inicio123'}`,
      })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Falha ao cadastrar usuário.' })
    }
  }

  async function handleResetSenha(usuario: string) {
    const confirmar = window.confirm(`Resetar a senha de ${usuario} para inicio123 e obrigar troca no próximo login?`)
    if (!confirmar) return
    setState({ status: 'loading', message: 'Aguarde processamento: resetando senha...' })
    try {
      await resetarSenhaUsuarioAdmin(usuario)
      await carregarUsuarios()
      setState({ status: 'success', message: `Senha de ${usuario} resetada para inicio123. Próximo login exigirá troca.` })
    } catch (error) {
      setState({ status: 'error', message: error instanceof Error ? error.message : 'Falha ao resetar senha.' })
    }
  }

  if (authUser.perfil !== 'admin') {
    return (
      <section className="gestor-section">
        <h1>Administração</h1>
        <p>Seu perfil não possui permissão para administrar usuários.</p>
      </section>
    )
  }

  return (
    <section className="gestor-section">
      <div className="gestor-section-header">
        <div>
          <span className="gestor-pill">Administração</span>
          <h1>Usuários e perfis</h1>
          <p>Cadastro por e-mail com senha inicial controlada e trilha em parquet.</p>
        </div>
      </div>

      {state.message ? <div className={`gestor-status gestor-status--${state.status}`}>{state.message}</div> : null}

      <div className="gestor-admin-grid">
        <form className="gestor-admin-form" onSubmit={handleSubmit}>
          <label>
            E-mail
            <input
              autoComplete="email"
              required
              type="email"
              value={form.email}
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="usuario@empresa.com"
            />
          </label>
          <label>
            Nome
            <input
              autoComplete="name"
              required
              value={form.nome_usuario}
              onChange={(event) => setForm((current) => ({ ...current, nome_usuario: event.target.value }))}
              placeholder="Nome completo"
            />
          </label>
          <label>
            Perfil
            <select
              value={form.perfil}
              onChange={(event) => setForm((current) => ({ ...current, perfil: event.target.value as 'admin' | 'gestor' | 'analista' }))}
            >
              <option value="analista">Analista</option>
              <option value="gestor">Gestor</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <button className="gestor-primary" disabled={state.status === 'loading'} type="submit">
            Cadastrar usuário
          </button>
          <small>Senha inicial: <strong>inicio123</strong>. Primeiro acesso exigirá troca e segundo fator.</small>
        </form>

        <div className="gestor-table-card">
          <div className="gestor-card-title">
            <span>Usuários cadastrados</span>
            <button className="gestor-primary gestor-primary--small" type="button" onClick={() => void carregarUsuarios()}>
              Atualizar
            </button>
          </div>
          <div className="gestor-table-scroll">
            <table className="gestor-table">
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Nome</th>
                  <th>Perfil</th>
                  <th>Status</th>
                  <th>Reset senha</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((usuario) => (
                  <tr key={usuario.usuario}>
                    <td>{usuario.email || usuario.usuario}</td>
                    <td>{usuario.nome_usuario}</td>
                    <td>{usuario.perfil}</td>
                    <td>{usuario.status}</td>
                    <td>{usuario.troca_senha_obrigatoria === 'true' ? 'Obrigatório' : 'Não'}</td>
                    <td>
                      <button
                        className="gestor-primary gestor-primary--small"
                        type="button"
                        onClick={() => void handleResetSenha(usuario.usuario)}
                      >
                        Resetar senha
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}

export default GestorPortalApp
