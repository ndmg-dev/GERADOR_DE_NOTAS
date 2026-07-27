import * as Dialog from '@radix-ui/react-dialog'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Image, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { mensagemDeErro } from '@/api/client'
import {
  atualizarEmpresa,
  criarEmpresa,
  enviarTimbrado,
  listarEmpresas,
  removerEmpresa,
} from '@/api/empresas'
import { EmpresaForm } from '@/components/EmpresaForm'
import { useToast } from '@/components/Toast'
import type { Empresa, EmpresaPayload } from '@/types'

export function Empresas() {
  const { notificar } = useToast()
  const queryClient = useQueryClient()
  const [dialogoAberto, setDialogoAberto] = useState(false)
  const [emEdicao, setEmEdicao] = useState<Empresa | null>(null)
  const inputTimbrado = useRef<HTMLInputElement>(null)
  const [empresaTimbrado, setEmpresaTimbrado] = useState<{
    id: string
    campo: 'header' | 'footer'
  } | null>(null)

  const empresas = useQuery({ queryKey: ['empresas'], queryFn: listarEmpresas })

  const invalidar = () => queryClient.invalidateQueries({ queryKey: ['empresas'] })

  const salvar = useMutation({
    mutationFn: (payload: EmpresaPayload) =>
      emEdicao ? atualizarEmpresa(emEdicao.id, payload) : criarEmpresa(payload),
    onSuccess: async () => {
      await invalidar()
      setDialogoAberto(false)
      setEmEdicao(null)
      notificar(emEdicao ? 'Empresa atualizada' : 'Empresa cadastrada')
    },
    onError: (erro) =>
      notificar('Falha ao salvar', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      }),
  })

  const remover = useMutation({
    mutationFn: removerEmpresa,
    onSuccess: async () => {
      await invalidar()
      notificar('Empresa removida')
    },
    onError: (erro) =>
      notificar('Falha ao remover', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      }),
  })

  const timbrado = useMutation({
    mutationFn: ({
      id,
      campo,
      arquivo,
    }: {
      id: string
      campo: 'header' | 'footer'
      arquivo: File
    }) => enviarTimbrado(id, { [campo]: arquivo }),
    onSuccess: async () => {
      await invalidar()
      notificar('Timbrado atualizado')
    },
    onError: (erro) =>
      notificar('Falha ao enviar o timbrado', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      }),
  })

  const selecionarTimbrado = (id: string, campo: 'header' | 'footer') => {
    setEmpresaTimbrado({ id, campo })
    inputTimbrado.current?.click()
  }

  return (
    <div>
      <input
        ref={inputTimbrado}
        type="file"
        accept="image/png"
        className="hidden"
        onChange={(evento) => {
          const arquivo = evento.target.files?.[0]
          if (arquivo && empresaTimbrado) {
            timbrado.mutate({ ...empresaTimbrado, arquivo })
          }
          evento.target.value = ''
        }}
      />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Empresas</h1>
          <p className="mt-1 text-sm text-neutral-600">
            Cadastro de clientes, quadro societário e papel timbrado.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEmEdicao(null)
            setDialogoAberto(true)
          }}
          className="inline-flex items-center gap-2 rounded bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        >
          <Plus className="h-4 w-4" /> Nova empresa
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
        {empresas.isLoading ? (
          <p className="p-6 text-sm text-neutral-500">Carregando...</p>
        ) : (empresas.data ?? []).length === 0 ? (
          <p className="p-6 text-sm text-neutral-500">Nenhuma empresa cadastrada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
                <th className="px-4 py-3 font-medium">Razão social</th>
                <th className="px-4 py-3 font-medium">CNPJ</th>
                <th className="px-4 py-3 font-medium">Sócios</th>
                <th className="px-4 py-3 font-medium">Timbrado</th>
                <th className="px-4 py-3 text-right font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(empresas.data ?? []).map((empresa) => (
                <tr key={empresa.id} className="border-b border-neutral-100 last:border-0">
                  <td className="px-4 py-3 text-neutral-900">{empresa.nome}</td>
                  <td className="px-4 py-3 tabular-nums text-neutral-700">{empresa.cnpj}</td>
                  <td className="px-4 py-3 text-neutral-700">{empresa.socios.length}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => selecionarTimbrado(empresa.id, 'header')}
                        className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs ${
                          empresa.timbrado_header_path
                            ? 'border-neutral-900 text-neutral-900'
                            : 'border-neutral-300 text-neutral-500'
                        } hover:bg-neutral-100`}
                      >
                        <Image className="h-3.5 w-3.5" /> Header
                      </button>
                      <button
                        type="button"
                        onClick={() => selecionarTimbrado(empresa.id, 'footer')}
                        className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs ${
                          empresa.timbrado_footer_path
                            ? 'border-neutral-900 text-neutral-900'
                            : 'border-neutral-300 text-neutral-500'
                        } hover:bg-neutral-100`}
                      >
                        <Image className="h-3.5 w-3.5" /> Footer
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setEmEdicao(empresa)
                          setDialogoAberto(true)
                        }}
                        aria-label={`Editar ${empresa.nome}`}
                        className="rounded border border-neutral-300 p-1.5 text-neutral-600 hover:bg-neutral-100"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (
                            window.confirm(`Remover a empresa "${empresa.nome}"?`)
                          ) {
                            remover.mutate(empresa.id)
                          }
                        }}
                        aria-label={`Remover ${empresa.nome}`}
                        className="rounded border border-neutral-300 p-1.5 text-neutral-600 hover:bg-neutral-100 hover:text-red-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Dialog.Root open={dialogoAberto} onOpenChange={setDialogoAberto}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[min(48rem,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold text-neutral-900">
                {emEdicao ? 'Editar empresa' : 'Nova empresa'}
              </Dialog.Title>
              <Dialog.Close aria-label="Fechar" className="text-neutral-400 hover:text-neutral-700">
                <X className="h-5 w-5" />
              </Dialog.Close>
            </div>

            <EmpresaForm
              empresa={emEdicao}
              salvando={salvar.isPending}
              onSubmit={(payload) => salvar.mutate(payload)}
              onCancel={() => setDialogoAberto(false)}
            />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
