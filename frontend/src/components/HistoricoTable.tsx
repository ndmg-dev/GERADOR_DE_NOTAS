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
  pending: 'border-borda bg-superficie-alt text-texto-suave',
  processing: 'border-ouro/30 bg-ouro-tenue text-ouro',
  done: 'border-sucesso/30 bg-sucesso/10 text-sucesso',
  error: 'border-erro/30 bg-erro/10 text-erro',
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium ${CLASSE_STATUS[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {ROTULO_STATUS[status]}
    </span>
  )
}

export function HistoricoTable({ jobs, onDownload, carregando }: HistoricoTableProps) {
  if (carregando) {
    return <p className="p-6 text-sm text-texto-fraco">Carregando...</p>
  }

  if (jobs.length === 0) {
    return (
      <p className="p-6 text-sm text-texto-fraco">
        Nenhuma geração encontrada para os filtros selecionados.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-borda text-left">
            {['Empresa', 'Exercício', 'Status', 'Criado em', 'Concluído em'].map(
              (coluna) => (
                <th key={coluna} className="rotulo-mini px-5 py-3 font-medium">
                  {coluna}
                </th>
              ),
            )}
            <th className="rotulo-mini px-5 py-3 text-right font-medium">Ações</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr
              key={job.id}
              className="border-b border-borda/60 transition-colors last:border-0 hover:bg-superficie-alt/60"
            >
              <td className="px-5 py-3">
                <span className="font-medium text-texto">
                  {job.empresa_nome ?? '—'}
                </span>
                {job.error_message && (
                  <p className="mt-0.5 text-xs text-erro">{job.error_message}</p>
                )}
              </td>
              <td className="px-5 py-3 font-mono tabular-nums text-texto-suave">
                {job.ano_exercicio}
              </td>
              <td className="px-5 py-3">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-5 py-3 text-texto-suave">
                {formatarDataHora(job.created_at)}
              </td>
              <td className="px-5 py-3 text-texto-suave">
                {formatarDataHora(job.finished_at)}
              </td>
              <td className="px-5 py-3 text-right">
                <button
                  type="button"
                  onClick={() => onDownload(job)}
                  disabled={!job.output_disponivel}
                  className="btn-neutro px-3 py-1.5 text-xs"
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
