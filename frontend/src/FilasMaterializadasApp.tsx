import { useCallback, useEffect, useMemo, useState } from 'react'
import { FilaResponse, FilaResumo, getFilaPorRegra, getFilasResumo } from './filasApi'
import './filasMaterializadas.css'

type FeedbackType = 'info' | 'loading' | 'success' | 'error'

type Feedback = {
  type: FeedbackType
  message: string
}

const ruleLabels: Record<string, string> = {
  sobreposicao_interrupcao: 'Sobreposição interrupção',
  horario_negativo: 'Horário negativo',
  sem_causa_componente: 'Causa/componente',
}

const defaultRules = ['sobreposicao_interrupcao', 'horario_negativo', 'sem_causa_componente']

const priorityColumns = [
  'regra',
  'chave_registro',
  'NUM_SEQ_INTRP',
  'NUM_OPER_CHV_INTRP',
  'NUM_INTRP_UCI',
  'DATA_HORA_INIC_INTRP',
  'DATA_HORA_FIM_INTRP',
  'duracao_minutos',
  'campo_sugerido',
  'valor_sugerido',
  'sugestao',
  'status_pendencia',
  'status_registro',
  'gravidade',
]

function formatNumber(value: unknown): string {
  return Number(value || 0).toLocaleString('pt-BR')
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function getRuleTotal(resumo: FilaResumo | null, regra: string): number {
  return resumo?.por_regra.find((item) => item.regra === regra)?.total ?? 0
}

function getRuleDistinct(resumo: FilaResumo | null, regra: string): number {
  return resumo?.por_regra.find((item) => item.regra === regra)?.registros_distintos ?? 0
}

function getTableColumns(rows: Array<Record<string, unknown>>): string[] {
  if (!rows.length) return []

  const allColumns = Object.keys(rows[0])
  return [
    ...priorityColumns.filter((column) => allColumns.includes(column)),
    ...allColumns.filter((column) => !priorityColumns.includes(column)).slice(0, 12),
  ]
}

function StatusMessage({ feedback }: { feedback: Feedback }) {
  return <div className={`filas-status filas-status--${feedback.type}`}>{feedback.message}</div>
}

function Sidebar({
  activeRule,
  onRuleChange,
  resumo,
}: {
  activeRule: string
  onRuleChange: (regra: string) => void
  resumo: FilaResumo | null
}) {
  return (
    <aside className="filas-sidebar">
      <div className="filas-brand">
        <div className="filas-logo">AI</div>
        <div>
          <strong>ADMStoIQS</strong>
          <span>Filas materializadas</span>
        </div>
      </div>

      <section className="filas-focus">
        <span>FOCO DE ATUAÇÃO</span>
        <strong>{formatNumber(resumo?.total_pendencias)}</strong>
        <small>Pendências materializadas</small>
      </section>

      <nav className="filas-nav" aria-label="Filas de correção">
        {defaultRules.map((regra) => (
          <button
            className={activeRule === regra ? 'is-active' : ''}
            key={regra}
            onClick={() => onRuleChange(regra)}
            type="button"
          >
            <span>{ruleLabels[regra]}</span>
            <strong>{formatNumber(getRuleTotal(resumo, regra))}</strong>
          </button>
        ))}
      </nav>
    </aside>
  )
}

function Card({ label, value }: { label: string; value: unknown }) {
  return (
    <article className="filas-card">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </article>
  )
}

function RulesPanel({
  activeRule,
  onRuleChange,
  resumo,
}: {
  activeRule: string
  onRuleChange: (regra: string) => void
  resumo: FilaResumo | null
}) {
  const rules = resumo?.por_regra.length ? resumo.por_regra : defaultRules.map((regra) => ({ regra, total: 0, registros_distintos: 0 }))

  return (
    <section className="filas-panel">
      <h2>Regras materializadas</h2>
      <p>Selecione uma regra para consultar os registros persistidos em parquet.</p>
      <div className="filas-rules">
        {rules.map((item) => (
          <button
            className={activeRule === item.regra ? 'is-active' : ''}
            key={item.regra}
            onClick={() => onRuleChange(item.regra)}
            type="button"
          >
            <strong>
              <span>{ruleLabels[item.regra] ?? item.regra}</span>
              <span>{formatNumber(item.total)}</span>
            </strong>
            <small>{formatNumber(item.registros_distintos)} registro(s) distinto(s)</small>
          </button>
        ))}
      </div>
    </section>
  )
}

function QueueTable({ fila }: { fila: FilaResponse | null }) {
  const columns = useMemo(() => getTableColumns(fila?.registros ?? []), [fila])

  return (
    <section className="filas-panel filas-table-panel">
      <div className="filas-panel-title">
        <div>
          <h2>{ruleLabels[fila?.regra ?? ''] ?? fila?.regra ?? 'Fila'}</h2>
          <p>
            {fila
              ? `${formatNumber(fila.total)} pendência(s). Exibindo ${formatNumber(fila.registros.length)}.`
              : 'Aguardando carregamento.'}
          </p>
        </div>
      </div>

      <div className="filas-table-wrap">
        <table>
          <thead>
            <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
          </thead>
          <tbody>
            {!fila?.registros.length ? (
              <tr>
                <td colSpan={Math.max(columns.length, 1)}>Nenhum registro carregado.</td>
              </tr>
            ) : (
              fila.registros.map((row, index) => (
                <tr key={`${fila.regra}-${index}`}>
                  {columns.map((column) => (
                    <td key={column} title={formatCell(row[column])}>
                      {formatCell(row[column])}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export function FilasMaterializadasApp() {
  const [anomes, setAnomes] = useState(() => new URLSearchParams(window.location.search).get('anomes') ?? '202605')
  const [activeRule, setActiveRule] = useState(defaultRules[0])
  const [resumo, setResumo] = useState<FilaResumo | null>(null)
  const [fila, setFila] = useState<FilaResponse | null>(null)
  const [feedback, setFeedback] = useState<Feedback>({
    type: 'info',
    message: 'Carregando resumo materializado...',
  })

  const loadResumo = useCallback(async () => {
    try {
      setFeedback({ type: 'loading', message: 'Aguarde processamento: lendo resumo materializado...' })
      const payload = await getFilasResumo(anomes)
      setResumo(payload)
      setFeedback({ type: 'success', message: 'Processamento concluído: resumo materializado carregado.' })
      return payload
    } catch (error) {
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Falha ao carregar resumo.' })
      return null
    }
  }, [anomes])

  const loadFila = useCallback(async (regra: string) => {
    try {
      setFeedback({ type: 'loading', message: `Aguarde processamento: carregando ${ruleLabels[regra] ?? regra}...` })
      const payload = await getFilaPorRegra(regra, 100, 0, anomes)
      setFila(payload)
      setFeedback({ type: 'success', message: 'Processamento concluído: fila carregada.' })
    } catch (error) {
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Falha ao carregar fila.' })
    }
  }, [anomes])

  const handleRuleChange = useCallback(
    (regra: string) => {
      setActiveRule(regra)
      void loadFila(regra)
    },
    [loadFila],
  )

  useEffect(() => {
    void loadResumo().then(() => loadFila(activeRule))
  }, [activeRule, loadFila, loadResumo])

  return (
    <div className="filas-shell">
      <Sidebar activeRule={activeRule} onRuleChange={handleRuleChange} resumo={resumo} />

      <main className="filas-main">
        <header className="filas-header">
          <div>
            <span className="filas-pill">React oficial</span>
            <h1>Filas de correção</h1>
            <p>Fonte governada: `pendencias_APURACAO_ATUAL.parquet`.</p>
          </div>
          <div className="filas-actions">
            <label className="filas-filter">
              <span>Competência</span>
              <input
                maxLength={6}
                onChange={(event) => setAnomes(event.target.value)}
                value={anomes}
              />
            </label>
            <button onClick={() => { window.location.href = '/gestor.html' }} type="button">
              Portal gestor
            </button>
            <button onClick={() => { window.location.href = `/decisoes.html?anomes=${encodeURIComponent(anomes)}` }} type="button">
              Decisão governada
            </button>
            <button onClick={() => void loadResumo()} type="button">
              Atualizar resumo
            </button>
            <button onClick={() => void loadFila(activeRule)} type="button">
              Carregar fila
            </button>
          </div>
        </header>

        <StatusMessage feedback={feedback} />

        <section className="filas-cards">
          <Card label="Total de pendências" value={resumo?.total_pendencias} />
          <Card label="Sobreposição" value={getRuleTotal(resumo, 'sobreposicao_interrupcao')} />
          <Card label="Horário negativo" value={getRuleTotal(resumo, 'horario_negativo')} />
          <Card label="Sem causa/componente" value={getRuleTotal(resumo, 'sem_causa_componente')} />
          <Card label="Seq. distintas em horário negativo" value={getRuleDistinct(resumo, 'horario_negativo')} />
        </section>

        <section className="filas-content">
          <RulesPanel activeRule={activeRule} onRuleChange={handleRuleChange} resumo={resumo} />
          <QueueTable fila={fila} />
        </section>
      </main>
    </div>
  )
}

export default FilasMaterializadasApp
