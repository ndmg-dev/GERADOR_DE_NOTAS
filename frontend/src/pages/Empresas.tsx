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
          <h1 className="text-2xl font-semibold text-texto">Empresas</h1>
          <p className="mt-1 text-sm text-texto-suave">
            Cadastro de clientes, quadro societário e papel timbrado.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEmEdicao(null)
            setDialogoAberto(true)
          }}
          className="btn-ouro"
        >
          <Plus className="h-4 w-4" /> Nova empresa
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-borda bg-superficie">
        {empresas.isLoading ? (
          <p className="p-6 text-sm text-texto-fraco">Carregando...</p>
        ) : (empresas.data ?? []).length === 0 ? (
          <p className="p-6 text-sm text-texto-fraco">Nenhuma empresa cadastrada.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-borda text-left text-xs uppercase tracking-wide text-texto-fraco">
                <th className="px-4 py-3 font-medium">Razão social</th>
                <th className="px-4 py-3 font-medium">CNPJ</th>
                <th className="px-4 py-3 font-medium">Sócios</th>
                <th className="px-4 py-3 font-medium">Timbrado</th>
                <th className="px-4 py-3 text-right font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(empresas.data ?? []).map((empresa) => (
                <tr key={empresa.id} className="border-b border-borda/60 last:border-0">
                  <td className="px-4 py-3 text-texto">{empresa.nome}</td>
                  <td className="px-4 py-3 tabular-nums text-texto-suave">{empresa.cnpj}</td>
                  <td className="px-4 py-3 text-texto-suave">{empresa.socios.length}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => selecionarTimbrado(empresa.id, 'header')}
                        className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs ${
                          empresa.timbrado_header_path
                            ? 'border-ouro/50 bg-ouro-tenue text-ouro'
                            : 'border-borda text-texto-fraco'
                        } hover:bg-superficie-alt`}
                      >
                        <Image className="h-3.5 w-3.5" /> Header
                      </button>
                      <button
                        type="button"
                        onClick={() => selecionarTimbrado(empresa.id, 'footer')}
                        className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs ${
                          empresa.timbrado_footer_path
                            ? 'border-ouro/50 bg-ouro-tenue text-ouro'
                            : 'border-borda text-texto-fraco'
                        } hover:bg-superficie-alt`}
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
                        className="rounded border border-borda p-1.5 text-texto-suave hover:bg-superficie-alt"
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
                        className="rounded border border-borda p-1.5 text-texto-suave hover:bg-superficie-alt hover:text-erro"
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
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[min(48rem,92vw)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-borda bg-superficie p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold text-texto">
                {emEdicao ? 'Editar empresa' : 'Nova empresa'}
              </Dialog.Title>
              <Dialog.Close aria-label="Fechar" className="text-texto-fraco hover:text-texto-suave">
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
