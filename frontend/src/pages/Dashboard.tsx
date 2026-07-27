import { useQuery } from '@tanstack/react-query'
import { Building2, CheckCircle2, FileText, Loader2, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { mensagemDeErro } from '@/api/client'
import { listarEmpresas } from '@/api/empresas'
import { baixarDocumento, listarHistorico } from '@/api/notas'
import { HistoricoTable } from '@/components/HistoricoTable'
import { useToast } from '@/components/Toast'
import type { Job } from '@/types'

function Card({
  titulo,
  valor,
  legenda,
  icone,
  destaque = false,
}: {
  titulo: string
  valor: number | string
  legenda: string
  icone: React.ReactNode
  destaque?: boolean
}) {
  return (
    <div className={`${destaque ? 'cartao-destaque' : 'cartao'} p-5`}>
      <div className="flex items-start justify-between">
        <span className="flex h-9 w-9 items-center justify-center rounded-md border border-borda bg-superficie-alt text-ouro">
          {icone}
        </span>
        <span className="rotulo-mini">{titulo}</span>
      </div>
      <p className="mt-4 text-3xl font-semibold tabular-nums text-texto">{valor}</p>
      <p className="mt-1 text-sm text-texto-suave">{legenda}</p>
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
          <h1 className="text-3xl font-semibold tracking-tight text-texto">
            Visão geral
          </h1>
          <p className="mt-1 text-sm text-texto-suave">
            Gerações recentes de Notas Explicativas
          </p>
        </div>
        <Link to="/gerar" className="btn-ouro">
          <FileText className="h-4 w-4" /> Gerar Notas
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card
          titulo="Empresas"
          valor={empresas.data?.length ?? 0}
          legenda="cadastradas no sistema"
          icone={<Building2 className="h-4 w-4" />}
        />
        <Card
          titulo="Gerações"
          valor={historico.data?.total ?? 0}
          legenda="documentos no histórico"
          icone={<FileText className="h-4 w-4" />}
          destaque
        />
        <Card
          titulo="Concluídos"
          valor={concluidos}
          legenda="entre as gerações recentes"
          icone={<CheckCircle2 className="h-4 w-4" />}
        />
        <Card
          titulo={comErro > 0 ? 'Com erro' : 'Em andamento'}
          valor={comErro > 0 ? comErro : emAndamento}
          legenda={comErro > 0 ? 'exigem atenção' : 'processando agora'}
          icone={
            comErro > 0 ? (
              <TriangleAlert className="h-4 w-4" />
            ) : (
              <Loader2 className="h-4 w-4" />
            )
          }
        />
      </div>

      <section className="cartao">
        <header className="flex items-center justify-between border-b border-borda px-5 py-4">
          <h2 className="text-sm font-semibold text-texto">Últimas gerações</h2>
          <Link
            to="/historico"
            className="text-sm text-ouro transition-colors hover:text-ouro-claro"
          >
            Ver histórico completo →
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
