import { useQuery } from '@tanstack/react-query'
import { Building2, CheckCircle2, FileText, Loader2, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listarEmpresas } from '@/api/empresas'
import { listarHistorico } from '@/api/notas'
import { HistoricoTable } from '@/components/HistoricoTable'
import { baixarDocumento } from '@/api/notas'
import { mensagemDeErro } from '@/api/client'
import { useToast } from '@/components/Toast'
import type { Job } from '@/types'

function Card({
  titulo,
  valor,
  icone,
}: {
  titulo: string
  valor: number | string
  icone: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-600">{titulo}</p>
        <span className="text-neutral-400">{icone}</span>
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-neutral-900">{valor}</p>
    </div>
  )
}

export function Dashboard() {
  const { notificar } = useToast()

  const historico = useQuery({
    queryKey: ['historico', { page: 1, limit: 10 }],
    queryFn: () => listarHistorico({ page: 1, limit: 10 }),
  })

  const empresas = useQuery({ queryKey: ['empresas'], queryFn: listarEmpresas })

  const jobs = historico.data?.items ?? []
  const concluidos = jobs.filter((job) => job.status === 'done').length
  const emAndamento = jobs.filter(
    (job) => job.status === 'processing' || job.status === 'pending',
  ).length
  const comErro = jobs.filter((job) => job.status === 'error').length

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
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Visão geral</h1>
          <p className="mt-1 text-sm text-neutral-600">
            Gerações recentes de Notas Explicativas.
          </p>
        </div>
        <Link
          to="/gerar"
          className="rounded bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        >
          Gerar Notas
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card
          titulo="Total no histórico"
          valor={historico.data?.total ?? 0}
          icone={<FileText className="h-5 w-5" />}
        />
        <Card
          titulo="Concluídos (recentes)"
          valor={concluidos}
          icone={<CheckCircle2 className="h-5 w-5" />}
        />
        <Card
          titulo="Em andamento"
          valor={emAndamento}
          icone={<Loader2 className="h-5 w-5" />}
        />
        <Card
          titulo="Com erro"
          valor={comErro}
          icone={<TriangleAlert className="h-5 w-5" />}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card
          titulo="Empresas cadastradas"
          valor={empresas.data?.length ?? 0}
          icone={<Building2 className="h-5 w-5" />}
        />
      </div>

      <section className="rounded-lg border border-neutral-200 bg-white">
        <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-neutral-900">Últimas gerações</h2>
          <Link to="/historico" className="text-sm text-neutral-600 hover:text-neutral-900">
            Ver histórico completo
          </Link>
        </header>
        <HistoricoTable
          jobs={jobs}
          onDownload={baixar}
          carregando={historico.isLoading}
        />
      </section>
    </div>
  )
}
