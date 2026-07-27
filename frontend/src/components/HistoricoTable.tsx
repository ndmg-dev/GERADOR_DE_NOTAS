import { Download } from 'lucide-react'
import { formatarDataHora } from '@/lib/format'
import type { Job, JobStatus } from '@/types'

interface HistoricoTableProps {
  jobs: Job[]
  onDownload: (job: Job) => void
  carregando?: boolean
}

const ROTULO_STATUS: Record<JobStatus, string> = {
  pending: 'Pendente',
  processing: 'Processando',
  done: 'Concluído',
  error: 'Erro',
}

const CLASSE_STATUS: Record<JobStatus, string> = {
  pending: 'bg-neutral-100 text-neutral-700',
  processing: 'bg-neutral-200 text-neutral-800',
  done: 'bg-neutral-900 text-white',
  error: 'bg-red-100 text-red-700',
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${CLASSE_STATUS[status]}`}
    >
      {ROTULO_STATUS[status]}
    </span>
  )
}

export function HistoricoTable({ jobs, onDownload, carregando }: HistoricoTableProps) {
  if (carregando) {
    return <p className="p-6 text-sm text-neutral-500">Carregando...</p>
  }

  if (jobs.length === 0) {
    return (
      <p className="p-6 text-sm text-neutral-500">
        Nenhuma geração encontrada para os filtros selecionados.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
            <th className="px-4 py-3 font-medium">Empresa</th>
            <th className="px-4 py-3 font-medium">Exercício</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Criado em</th>
            <th className="px-4 py-3 font-medium">Concluído em</th>
            <th className="px-4 py-3 text-right font-medium">Ações</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b border-neutral-100 last:border-0">
              <td className="px-4 py-3 text-neutral-900">
                {job.empresa_nome ?? '—'}
                {job.error_message && (
                  <p className="mt-0.5 text-xs text-red-600">{job.error_message}</p>
                )}
              </td>
              <td className="px-4 py-3 tabular-nums text-neutral-700">
                {job.ano_exercicio}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-4 py-3 text-neutral-600">
                {formatarDataHora(job.created_at)}
              </td>
              <td className="px-4 py-3 text-neutral-600">
                {formatarDataHora(job.finished_at)}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  type="button"
                  onClick={() => onDownload(job)}
                  disabled={!job.output_disponivel}
                  className="inline-flex items-center gap-1.5 rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Download className="h-3.5 w-3.5" /> Baixar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
