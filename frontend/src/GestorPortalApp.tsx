import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  exportarPortalTratamentoCsv,
  gerarPortalTratamentoMassivo,
  getPortalIndicadoresResumo,
  getPortalFilasResumo,
  getPortalIqsResumo,
  getPortalMartResumo,
  getPortalTratamentoResumo,
  IndicadoresResumo,
  materializarPortalIndicadores,
  IqsResumo,
  MartResumo,
  TratamentoExportacao,
  TratamentoResumo,
} from './gestorApi'
import { FilaResumo } from './filasApi'
import './gestorPortal.css'

type PortalPage = 'dashboard' | 'etl' | 'produto' | 'indicadores' | 'filas' | 'iqs' | 'governanca'

type LoadState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  message: string
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
  if (status === 'processado') return 'ok'
  if (status === 'erro') return 'error'
  if (status === 'pendente_raw') return 'warn'
  return 'neutral'
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

function Sidebar({
  activePage,
  filasResumo,
  onNavigate,
}: {
  activePage: PortalPage
  filasResumo: FilaResumo | null
  onNavigate: (page: PortalPage) => void
}) {
  const total = filasResumo?.total_pendencias ?? 0

  return (
    <aside className="gestor-sidebar">
      <div className="gestor-brand">
        <div className="gestor-logo">AI</div>
        <div>
          <strong>ADMStoIQS</strong>
          <span>Portal gestor</span>
        </div>
      </div>

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
        <button className={activePage === 'etl' ? 'is-active' : ''} onClick={() => onNavigate('etl')} type="button">
          <span>ETL operacional</span>
          <small>CSV, UNION e apuração</small>
        </button>
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
        <button className={activePage === 'iqs' ? 'is-active' : ''} onClick={() => onNavigate('iqs')} type="button">
          <span>Fontes IQS</span>
          <small>Marts externos</small>
        </button>
        <button className={activePage === 'governanca' ? 'is-active' : ''} onClick={() => onNavigate('governanca')} type="button">
          <span>Governança</span>
          <small>Trilha e decisões</small>
        </button>
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
  onResumoUpdate,
}: {
  anomes: string
  indicadoresResumo: IndicadoresResumo | null
  onResumoUpdate: (resumo: IndicadoresResumo) => void
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

  const copel = indicadoresResumo?.copel

  return (
    <>
      <section className="gestor-grid gestor-grid--cards">
        <Card label="DEC antes" value={copel?.dec_antes?.toFixed?.(4) ?? 0} hint="COPEL em horas" />
        <Card label="DEC depois" value={copel?.dec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="FEC antes" value={copel?.fec_antes?.toFixed?.(4) ?? 0} hint="COPEL" />
        <Card label="FEC depois" value={copel?.fec_depois?.toFixed?.(4) ?? 0} hint="Após tratamento" accent="success" />
        <Card label="DMIC máx. depois" value={copel?.dmic_max_depois?.toFixed?.(2) ?? 0} hint="Horas" />
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

function EtlPage({ anomes }: { anomes: string }) {
  return (
    <section className="gestor-panel">
      <div className="gestor-panel-title">
        <div>
          <h2>ETL operacional</h2>
          <p>
            Área de preparação dos dados: verificação de CSVs, atualização do UNION e geração da apuração mensal.
          </p>
        </div>
        <a className="gestor-link" href="/operacional.html">
          Abrir ETL completo
        </a>
      </div>

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

export function GestorPortalApp() {
  const [anomes, setAnomes] = useState('202605')
  const [activePage, setActivePage] = useState<PortalPage>('dashboard')
  const [loadState, setLoadState] = useState<LoadState>({
    status: 'idle',
    message: 'Aguardando carregamento.',
  })
  const [filasResumo, setFilasResumo] = useState<FilaResumo | null>(null)
  const [iqsResumo, setIqsResumo] = useState<IqsResumo | null>(null)
  const [martResumo, setMartResumo] = useState<MartResumo | null>(null)
  const [tratamentoResumo, setTratamentoResumo] = useState<TratamentoResumo | null>(null)
  const [indicadoresResumo, setIndicadoresResumo] = useState<IndicadoresResumo | null>(null)

  const loadPortal = useCallback(async () => {
    setLoadState({ status: 'loading', message: 'Aguarde processamento: carregando resumos materializados...' })
    try {
      const [filas, iqs, mart, tratamento, indicadores] = await Promise.allSettled([
        getPortalFilasResumo(anomes),
        getPortalIqsResumo(anomes),
        getPortalMartResumo(),
        getPortalTratamentoResumo(anomes),
        getPortalIndicadoresResumo(anomes),
      ])

      if (filas.status === 'fulfilled') setFilasResumo(filas.value)
      if (iqs.status === 'fulfilled') setIqsResumo(iqs.value)
      if (mart.status === 'fulfilled') setMartResumo(mart.value)
      if (tratamento.status === 'fulfilled') setTratamentoResumo(tratamento.value)
      if (indicadores.status === 'fulfilled') setIndicadoresResumo(indicadores.value)

      const errors = [filas, iqs, mart, tratamento, indicadores].filter((result) => result.status === 'rejected').length
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
    void loadPortal()
  }, [loadPortal])

  return (
    <div className="gestor-shell">
      <Sidebar activePage={activePage} filasResumo={filasResumo} onNavigate={setActivePage} />

      <main className="gestor-main">
        <header className="gestor-header">
          <div>
            <span className="gestor-pill">Versão definitiva</span>
            <h1>ADMStoIQS</h1>
            <p>Middleware local para reduzir falhas entre ADMS e IQS.</p>
          </div>
          <button className="gestor-primary" onClick={() => void loadPortal()} type="button">
            Atualizar portal
          </button>
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
        {activePage === 'etl' ? <EtlPage anomes={anomes} /> : null}
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
            onResumoUpdate={setIndicadoresResumo}
          />
        ) : null}
        {activePage === 'filas' ? <FilasPage anomes={anomes} filasResumo={filasResumo} /> : null}
        {activePage === 'iqs' ? <IqsPage iqsResumo={iqsResumo} /> : null}
        {activePage === 'governanca' ? <GovernancaPage /> : null}
      </main>
    </div>
  )
}

export default GestorPortalApp
