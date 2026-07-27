import type {
  DadosExtraidos,
  GerarResponse,
  HistoricoResponse,
  PreviewResponse,
  ProcessarResponse,
  StatusResponse,
} from '@/types'
import { api } from './client'

/** Balanço e DRE de um exercício anterior, para as tabelas comparativas. */
export interface ExercicioAnterior {
  balancoPdf: File | null
  drePdf: File | null
}

export interface ProcessarPayload {
  balancoPdf: File
  drePdf: File
  empresaId: string
  ano: number
  dataAprovacao: string
  anteriores?: [ExercicioAnterior, ExercicioAnterior]
}

export async function processarNotas(
  payload: ProcessarPayload,
): Promise<ProcessarResponse> {
  const form = new FormData()
  form.append('balanco_pdf', payload.balancoPdf)
  form.append('dre_pdf', payload.drePdf)
  form.append('empresa_id', payload.empresaId)
  form.append('ano', String(payload.ano))
  form.append('data_aprovacao', payload.dataAprovacao)

  payload.anteriores?.forEach((anterior, indice) => {
    const sufixo = `ant${indice + 1}`
    if (anterior.balancoPdf) form.append(`balanco_pdf_${sufixo}`, anterior.balancoPdf)
    if (anterior.drePdf) form.append(`dre_pdf_${sufixo}`, anterior.drePdf)
  })

  const { data } = await api.post<ProcessarResponse>('/notas/processar', form)
  return data
}

export async function obterStatus(jobId: string): Promise<StatusResponse> {
  const { data } = await api.get<StatusResponse>(`/notas/status/${jobId}`)
  return data
}

export async function obterPreview(jobId: string): Promise<PreviewResponse> {
  const { data } = await api.get<PreviewResponse>(`/notas/preview/${jobId}`)
  return data
}

export async function gerarDocumento(
  jobId: string,
  dadosEditados?: Partial<DadosExtraidos>,
): Promise<GerarResponse> {
  const { data } = await api.post<GerarResponse>(`/notas/gerar/${jobId}`, {
    dados_editados: dadosEditados ?? null,
  })
  return data
}

export async function listarHistorico(params: {
  empresaId?: string
  ano?: number
  page?: number
  limit?: number
}): Promise<HistoricoResponse> {
  const { data } = await api.get<HistoricoResponse>('/notas/historico', {
    params: {
      empresa_id: params.empresaId || undefined,
      ano: params.ano || undefined,
      page: params.page ?? 1,
      limit: params.limit ?? 20,
    },
  })
  return data
}

/** Baixa o .docx e devolve o nome do arquivo salvo. */
export async function baixarDocumento(jobId: string, ano: number): Promise<string> {
  const resposta = await api.get<Blob>(`/notas/download/${jobId}`, {
    responseType: 'blob',
  })

  const nomeArquivo = extrairNomeArquivo(
    resposta.headers['content-disposition'],
    `Notas_Explicativas_${ano}.docx`,
  )

  const url = URL.createObjectURL(resposta.data)
  const link = document.createElement('a')
  link.href = url
  link.download = nomeArquivo
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)

  return nomeArquivo
}

function extrairNomeArquivo(cabecalho: unknown, padrao: string): string {
  if (typeof cabecalho !== 'string') return padrao
  const match = cabecalho.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  return match?.[1] ? decodeURIComponent(match[1]) : padrao
}
