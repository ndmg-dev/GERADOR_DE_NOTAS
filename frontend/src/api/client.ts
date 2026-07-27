import axios, { AxiosError } from 'axios'

/**
 * Em desenvolvimento e produção a aplicação fala com `/api`, resolvido pelo
 * proxy do Vite (dev) ou pelo Nginx (produção).
 */
export const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

interface ApiErrorBody {
  detail?: string
}

export function mensagemDeErro(erro: unknown): string {
  if (erro instanceof AxiosError) {
    const detalhe = (erro.response?.data as ApiErrorBody | undefined)?.detail
    if (detalhe) return detalhe
    if (erro.response?.status === 429) {
      return 'Muitas requisições em pouco tempo. Aguarde um instante e tente novamente.'
    }
    return erro.message
  }
  if (erro instanceof Error) return erro.message
  return 'Erro inesperado'
}
