export interface Socio {
  nome: string
  participacao: string | null
  cpf: string | null
  cargo: string | null
}

export interface Empresa {
  id: string
  nome: string
  cnpj: string
  endereco: string | null
  socios: Socio[]
  contador_nome: string | null
  contador_crc: string | null
  contador_cpf: string | null
  timbrado_header_path: string | null
  timbrado_footer_path: string | null
  created_at: string
  updated_at: string
}

export type EmpresaPayload = Omit<
  Empresa,
  'id' | 'created_at' | 'updated_at' | 'timbrado_header_path' | 'timbrado_footer_path'
>

export type JobStatus = 'pending' | 'processing' | 'done' | 'error'

export interface Job {
  id: string
  empresa_id: string | null
  empresa_nome: string | null
  status: JobStatus
  ano_exercicio: number
  data_aprovacao: string | null
  progresso: number
  etapa_atual: string | null
  error_message: string | null
  output_disponivel: boolean
  created_at: string
  finished_at: string | null
}

export interface HistoricoResponse {
  items: Job[]
  total: number
  page: number
  limit: number
}

export interface ProcessarResponse {
  job_id: string
  status: JobStatus
  message: string
}

export interface StatusResponse {
  job_id: string
  status: JobStatus
  progresso: number
  etapa_atual: string | null
  output_disponivel: boolean
  error_message: string | null
}

export interface GerarResponse {
  job_id: string
  output_path: string
  status: JobStatus
}

/** Um item de conta dentro de um grupo do balanço. */
export interface ContaItem {
  descricao: string
  valor: number
}

/** Grupo de contas: total + composição. */
export interface GrupoContas {
  descricao: string
  total: number | null
  itens: ContaItem[]
}

export interface GrupoImobilizado {
  nome: string
  custo: number
  depreciacao: number
  liquido: number
}

export interface Imobilizado {
  grupos: GrupoImobilizado[]
  depreciacao_total: number | null
  total_liquido: number | null
  total_custo: number | null
}

export interface Balanco {
  ativo: {
    circulante: Record<string, GrupoContas | number | null>
    nao_circulante: Record<string, GrupoContas | Imobilizado | number | null>
  }
  passivo: {
    circulante: Record<string, GrupoContas | number | null>
  }
  patrimonio_liquido: Record<string, number | null>
  total_ativo: number | null
  total_passivo_pl: number | null
}

export interface Dre {
  receita_bruta: number | null
  deducoes: number | null
  receita_liquida: number | null
  custos: Record<string, number | null>
  lucro_bruto: number | null
  despesas_operacionais: {
    total: number | null
    despesas_pessoal: number | null
    impostos_taxas: number | null
    despesas_gerais: number | null
    itens: ContaItem[]
  }
  resultado_financeiro: {
    receitas_financeiras: number | null
    despesas_financeiras: number | null
    liquido: number | null
  }
  outras_receitas: number | null
  resultado_operacional: number | null
  lucro_liquido: number | null
}

export interface ConfigNotas {
  ano: number
  data_aprovacao: string | null
}

/**
 * Abertura da Nota 18 por natureza. A DRE do Domínio traz apenas o total das
 * despesas operacionais, então esta composição é ajustada pelo contador na
 * revisão.
 */
export interface NaturezaDespesas {
  custo_servico: number | null
  servicos_terceiros: number | null
  depreciacoes: number | null
  outros: number | null
}

/**
 * Movimentação de um grupo do imobilizado na Nota 08. O balanço só informa os
 * saldos, então estes valores são digitados na revisão.
 */
export interface MovimentoImobilizado {
  rotulo: string
  aquisicoes: number | null
  baixas: number | null
  depreciacao: number | null
}

/** Indexada pelo nome normalizado do grupo. */
export type MovimentacaoImobilizado = Record<string, MovimentoImobilizado>

/** Um exercício social com seus demonstrativos já extraídos. */
export interface Exercicio {
  ano: number
  balanco: Balanco
  dre: Dre
  natureza_despesas: NaturezaDespesas
  movimentacao_imobilizado: MovimentacaoImobilizado
}

export interface DadosExtraidos {
  /** Do exercício mais recente para o mais antigo (até 3). */
  exercicios: Exercicio[]
  empresa: Record<string, unknown>
  config: ConfigNotas
  notas: NotaPreview[]
}

export interface BlocoParagrafo {
  tipo: 'paragrafo'
  texto: string
}

export interface BlocoTabela {
  tipo: 'tabela'
  titulo: string | null
  colunas: string[]
  linhas: string[][]
  total: string[] | null
}

export type BlocoNota = BlocoParagrafo | BlocoTabela

export interface NotaPreview {
  numero: number
  titulo: string
  tipo: 'texto' | 'tabela' | 'misto'
  conteudo: BlocoNota[]
}

export interface PreviewResponse {
  job_id: string
  dados: DadosExtraidos
}
