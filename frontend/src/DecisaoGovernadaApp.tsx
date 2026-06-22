import { useCallback, useEffect, useMemo, useState } from 'react'
import { FilaResponse, FilaResumo, getFilaPorRegra, getFilasResumo } from './filasApi'
import { DecisoesLog, DecisoesResumo, getDecisoesLog, getDecisoesResumo, registrarDecisao } from './decisoesApi'
import './decisaoGovernada.css'

type Acao = 'validar' | 'rejeitar' | 'ignorar_regra'

const ruleLabels: Record<string, string> = {
  sobreposicao_interrupcao: 'Sobreposição interrupção',
  horario_negativo: 'Horário negativo',
  sem_causa_componente: 'Causa/componente',
}

const rules = ['sobreposicao_interrupcao', 'horario_negativo', 'sem_causa_componente']

const columnsPriority = [
  'chave_registro',
  'regra',
  'NUM_SEQ_INTRP',
  'NUM_OPER_CHV_INTRP',
  'DATA_HORA_INIC_INTRP',
  'DATA_HORA_FIM_INTRP',
  'duracao_minutos',
  'campo_sugerido',
  'valor_sugerido',
  'sugestao',
  'gravidade',
]

function formatNumber(value: unknown): string {
  return Number(value || 0).toLocaleString('pt-BR')
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function getRowKey(row: Record<string, unknown>): string {
  const key = row.chave_registro ?? row.NUM_SEQ_INTRP ?? row.NUM_INTRP_UCI
  return String(key ?? '')
}

function tableColumns(rows: Array<Record<string, unknown>>): string[] {
  if (!rows.length) return []
  const allColumns = Object.keys(rows[0])
  return [
    ...columnsPriority.filter((column) => allColumns.includes(column)),
    ...allColumns.filter((column) => !columnsPriority.includes(column)).slice(0, 10),
  ]
}

export function DecisaoGovernadaApp() {
  const [anomes, setAnomes] = useState(() => new URLSearchParams(window.location.search).get('anomes') ?? '202605')
  const [regra, setRegra] = useState(rules[0])
  const [acao, setAcao] = useState<Acao>('validar')
  const [justificativa, setJustificativa] = useState('')
  const [usuario, setUsuario] = useState('admin')
  const [perfil, setPerfil] = useState('admin')
  const [feedback, setFeedback] = useState('Carregando dados governados...')
  const [feedbackType, setFeedbackType] = useState<'info' | 'loading' | 'success' | 'error'>('info')
  const [resumo, setResumo] = useState<FilaResumo | null>(null)
  const [fila, setFila] = useState<FilaResponse | null>(null)
  const [decisoesResumo, setDecisoesResumo] = useState<DecisoesResumo | null>(null)
  const [decisoesLog, setDecisoesLog] = useState<DecisoesLog | null>(null)
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set())

  const columns = useMemo(() => tableColumns(fila?.registros ?? []), [fila])
  const visibleKeys = useMemo(() => (fila?.registros ?? []).map(getRowKey).filter(Boolean), [fila])

  const loadAll = useCallback(async () => {
    setFeedbackType('loading')
    setFeedback('Aguarde processamento: carregando fila e log de decisões...')
    try {
      const [filasResumo, filaAtual, resumoDecisoes, logDecisoes] = await Promise.all([
        getFilasResumo(anomes),
        getFilaPorRegra(regra, 100, 0, anomes),
        getDecisoesResumo(anomes),
        getDecisoesLog(anomes),
      ])
      setResumo(filasResumo)
      setFila(filaAtual)
      setDecisoesResumo(resumoDecisoes)
      setDecisoesLog(logDecisoes)
      setSelectedKeys(new Set())
      setFeedbackType('success')
      setFeedback('Processamento concluído: decisão governada pronta.')
    } catch (error) {
      setFeedbackType('error')
      setFeedback(error instanceof Error ? error.message : 'Falha ao carregar decisão governada.')
    }
  }, [anomes, regra])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  function toggleKey(key: string) {
    setSelectedKeys((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function selectAllVisible() {
    setSelectedKeys(new Set(visibleKeys))
  }

  async function submitDecision() {
    setFeedbackType('loading')
    setFeedback('Aguarde processamento: registrando decisão governada...')
    try {
      await registrarDecisao({
        anomes,
        regra,
        acao,
        chaves_registro: Array.from(selectedKeys),
        justificativa,
        usuario,
        perfil,
      })
      setJustificativa('')
      setSelectedKeys(new Set())
      setFeedbackType('success')
      setFeedback('Processamento concluído: decisão registrada no log parquet.')
      await loadAll()
    } catch (error) {
      setFeedbackType('error')
      setFeedback(error instanceof Error ? error.message : 'Falha ao registrar decisão.')
    }
  }

  const totalRegra = resumo?.por_regra.find((item) => item.regra === regra)?.total ?? 0

  return (
    <div className="decisao-shell">
      <aside className="decisao-sidebar">
        <div className="decisao-brand">
          <div className="decisao-logo">AI</div>
          <div>
            <strong>ADMStoIQS</strong>
            <span>Decisão governada</span>
          </div>
        </div>

        <section className="decisao-focus">
          <span>Selecionados</span>
          <strong>{formatNumber(selectedKeys.size)}</strong>
          <small>{ruleLabels[regra]}</small>
        </section>

        <nav className="decisao-nav">
          {rules.map((item) => (
            <button className={item === regra ? 'is-active' : ''} key={item} onClick={() => setRegra(item)} type="button">
              <span>{ruleLabels[item]}</span>
              <small>{formatNumber(resumo?.por_regra.find((regraItem) => regraItem.regra === item)?.total)}</small>
            </button>
          ))}
        </nav>
      </aside>

      <main className="decisao-main">
        <header className="decisao-header">
          <div>
            <span className="decisao-pill">Governança</span>
            <h1>Decisão governada</h1>
            <p>Registre validação, rejeição ou exceção com trilha nominal.</p>
          </div>
          <div className="decisao-actions">
            <label>
              <span>Competência</span>
              <input maxLength={6} onChange={(event) => setAnomes(event.target.value)} value={anomes} />
            </label>
            <button onClick={() => { window.location.href = '/gestor.html' }} type="button">Portal</button>
            <button onClick={() => void loadAll()} type="button">Atualizar</button>
          </div>
        </header>

        <div className={`decisao-status decisao-status--${feedbackType}`}>{feedback}</div>

        <section className="decisao-cards">
          <article>
            <span>Pendências da regra</span>
            <strong>{formatNumber(totalRegra)}</strong>
          </article>
          <article>
            <span>Visíveis</span>
            <strong>{formatNumber(fila?.registros.length)}</strong>
          </article>
          <article>
            <span>Selecionadas</span>
            <strong>{formatNumber(selectedKeys.size)}</strong>
          </article>
          <article>
            <span>Decisões registradas</span>
            <strong>{formatNumber(decisoesResumo?.total_decisoes)}</strong>
          </article>
        </section>

        <section className="decisao-panel">
          <div className="decisao-toolbar">
            <strong>{ruleLabels[regra]}</strong>
            <div>
              <button onClick={selectAllVisible} type="button">Selecionar visíveis</button>
              <button onClick={() => setSelectedKeys(new Set())} type="button">Limpar seleção</button>
            </div>
          </div>

          <div className="decisao-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sel.</th>
                  {columns.map((column) => <th key={column}>{column}</th>)}
                </tr>
              </thead>
              <tbody>
                {!fila?.registros.length ? (
                  <tr>
                    <td colSpan={columns.length + 1}>Nenhum registro carregado.</td>
                  </tr>
                ) : (
                  fila.registros.map((row, index) => {
                    const key = getRowKey(row)
                    return (
                      <tr key={`${key}-${index}`}>
                        <td>
                          <input checked={selectedKeys.has(key)} onChange={() => toggleKey(key)} type="checkbox" />
                        </td>
                        {columns.map((column) => (
                          <td key={column} title={formatCell(row[column])}>{formatCell(row[column])}</td>
                        ))}
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="decisao-panel decisao-form">
          <div>
            <h2>Registrar decisão</h2>
            <p>Informe justificativa técnica. Cada chave selecionada gera uma linha auditável no parquet.</p>
          </div>
          <div className="decisao-form-grid">
            <label>
              <span>Ação</span>
              <select onChange={(event) => setAcao(event.target.value as Acao)} value={acao}>
                <option value="validar">Validar</option>
                <option value="rejeitar">Rejeitar</option>
                <option value="ignorar_regra">Ignorar regra</option>
              </select>
            </label>
            <label>
              <span>Usuário</span>
              <input onChange={(event) => setUsuario(event.target.value)} value={usuario} />
            </label>
            <label>
              <span>Perfil</span>
              <input onChange={(event) => setPerfil(event.target.value)} value={perfil} />
            </label>
          </div>
          <textarea
            onChange={(event) => setJustificativa(event.target.value)}
            placeholder="Descreva o motivo técnico da decisão."
            value={justificativa}
          />
          <button onClick={() => void submitDecision()} type="button">Registrar decisão</button>
        </section>

        <section className="decisao-panel">
          <h2>Últimas decisões</h2>
          <div className="decisao-log">
            {(decisoesLog?.registros ?? []).slice(0, 8).map((row, index) => (
              <article key={`${row.id_decisao}-${index}`}>
                <strong>{formatCell(row.acao)} · {formatCell(row.regra)}</strong>
                <span>{formatCell(row.chave_registro)}</span>
                <small>{formatCell(row.usuario)} · {formatCell(row.criado_em)}</small>
              </article>
            ))}
            {!decisoesLog?.registros.length ? <p>Nenhuma decisão registrada para a competência.</p> : null}
          </div>
        </section>
      </main>
    </div>
  )
}

export default DecisaoGovernadaApp

