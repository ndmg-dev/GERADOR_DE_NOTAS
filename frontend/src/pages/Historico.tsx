import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { mensagemDeErro } from '@/api/client'
import { listarEmpresas } from '@/api/empresas'
import { baixarDocumento, listarHistorico } from '@/api/notas'
import { HistoricoTable } from '@/components/HistoricoTable'
import { useToast } from '@/components/Toast'
import type { Job } from '@/types'

const LIMITE = 20

export function Historico() {
  const { notificar } = useToast()
  const [empresaId, setEmpresaId] = useState('')
  const [ano, setAno] = useState('')
  const [page, setPage] = useState(1)

  const empresas = useQuery({ queryKey: ['empresas'], queryFn: listarEmpresas })

  const historico = useQuery({
    queryKey: ['historico', { empresaId, ano, page }],
    queryFn: () =>
      listarHistorico({
        empresaId: empresaId || undefined,
        ano: ano ? Number(ano) : undefined,
        page,
        limit: LIMITE,
      }),
  })

  const total = historico.data?.total ?? 0
  const totalPaginas = Math.max(1, Math.ceil(total / LIMITE))

  const baixar = async (job: Job) => {
    try {
      const nome = await baixarDocumento(job.id, job.ano_exercicio)
      notificar('Download concluído', { descricao: nome })
    } catch (erro) {
      notificar('Falha no download', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      })
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-neutral-900">Histórico</h1>
      <p className="mb-6 text-sm text-neutral-600">
        Todas as gerações de Notas Explicativas registradas.
      </p>

      <div className="mb-4 flex flex-wrap gap-3 rounded-lg border border-neutral-200 bg-white p-4">
        <div>
          <label htmlFor="filtro-empresa" className="mb-1 block text-xs text-neutral-600">
            Empresa
          </label>
          <select
            id="filtro-empresa"
            value={empresaId}
            onChange={(evento) => {
              setEmpresaId(evento.target.value)
              setPage(1)
            }}
            className="rounded border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-900 focus:outline-none"
          >
            <option value="">Todas</option>
            {(empresas.data ?? []).map((empresa) => (
              <option key={empresa.id} value={empresa.id}>
                {empresa.nome}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filtro-ano" className="mb-1 block text-xs text-neutral-600">
            Ano do exercício
          </label>
          <input
            id="filtro-ano"
            type="number"
            value={ano}
            placeholder="Todos"
            onChange={(evento) => {
              setAno(evento.target.value)
              setPage(1)
            }}
            className="w-32 rounded border border-neutral-300 px-3 py-2 text-sm tabular-nums focus:border-neutral-900 focus:outline-none"
          />
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white">
        <HistoricoTable
          jobs={historico.data?.items ?? []}
          onDownload={baixar}
          carregando={historico.isLoading}
        />
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-neutral-600">
        <span>
          {total} registro(s) — página {page} de {totalPaginas}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPage((atual) => Math.max(1, atual - 1))}
            disabled={page <= 1}
            className="rounded border border-neutral-300 px-3 py-1.5 hover:bg-neutral-100 disabled:opacity-40"
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPage((atual) => Math.min(totalPaginas, atual + 1))}
            disabled={page >= totalPaginas}
            className="rounded border border-neutral-300 px-3 py-1.5 hover:bg-neutral-100 disabled:opacity-40"
          >
            Próxima
          </button>
        </div>
      </div>
    </div>
  )
}
