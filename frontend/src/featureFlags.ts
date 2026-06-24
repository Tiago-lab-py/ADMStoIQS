export type FeatureStatus = 'ativo' | 'em_desenvolvimento'

export type FeatureFlag = {
  id: string
  titulo: string
  descricao: string
  status: FeatureStatus
  perfilAlvo: 'admin' | 'gestor' | 'analista' | 'todos'
}

export const FRONTEND_FEATURES: FeatureFlag[] = [
  {
    id: 'sobreposicao',
    titulo: 'Sobreposição',
    descricao: 'Agrupa sobreposição de interrupção por equipamento e sobreposição UC em uma única jornada operacional.',
    status: 'ativo',
    perfilAlvo: 'gestor',
  },
  {
    id: 'administracao_usuarios',
    titulo: 'Administração de usuários',
    descricao: 'Cadastro por e-mail, perfil admin/gestor/analista, reset inicial e trilha de auditoria.',
    status: 'em_desenvolvimento',
    perfilAlvo: 'admin',
  },
  {
    id: 'causa_componente',
    titulo: 'Causa/componente',
    descricao: 'Sugestão e implantação governada para registros sem causa ou componente.',
    status: 'em_desenvolvimento',
    perfilAlvo: 'analista',
  },
  {
    id: 'janela_ise',
    titulo: 'Janela ISE',
    descricao: 'Módulo futuro para avaliação e implantação de janelas ISE.',
    status: 'em_desenvolvimento',
    perfilAlvo: 'gestor',
  },
  {
    id: 'dia_critico',
    titulo: 'Dia crítico',
    descricao: 'Módulo futuro para regras de dia crítico e conciliação com metas IQS.',
    status: 'em_desenvolvimento',
    perfilAlvo: 'gestor',
  },
]

export const featuresEmDesenvolvimento = FRONTEND_FEATURES.filter(
  (feature) => feature.status === 'em_desenvolvimento',
)
