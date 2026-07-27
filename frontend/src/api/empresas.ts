import type { Empresa, EmpresaPayload } from '@/types'
import { api } from './client'

export async function listarEmpresas(): Promise<Empresa[]> {
  const { data } = await api.get<Empresa[]>('/empresas')
  return data
}

export async function obterEmpresa(id: string): Promise<Empresa> {
  const { data } = await api.get<Empresa>(`/empresas/${id}`)
  return data
}

export async function criarEmpresa(payload: EmpresaPayload): Promise<Empresa> {
  const { data } = await api.post<Empresa>('/empresas', payload)
  return data
}

export async function atualizarEmpresa(
  id: string,
  payload: Partial<EmpresaPayload>,
): Promise<Empresa> {
  const { data } = await api.put<Empresa>(`/empresas/${id}`, payload)
  return data
}

export async function removerEmpresa(id: string): Promise<void> {
  await api.delete(`/empresas/${id}`)
}

export interface TimbradoResponse {
  empresa_id: string
  timbrado_header_path: string | null
  timbrado_footer_path: string | null
}

export async function enviarTimbrado(
  id: string,
  arquivos: { header?: File; footer?: File },
): Promise<TimbradoResponse> {
  const form = new FormData()
  if (arquivos.header) form.append('header', arquivos.header)
  if (arquivos.footer) form.append('footer', arquivos.footer)

  const { data } = await api.post<TimbradoResponse>(`/empresas/${id}/timbrado`, form)
  return data
}
