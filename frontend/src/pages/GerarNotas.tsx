import * as Progress from '@radix-ui/react-progress'
import { useMutation, useQuery } from '@tanstack/react-query'
import { CheckCircle2, Download, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { mensagemDeErro } from '@/api/client'
import { listarEmpresas } from '@/api/empresas'
import {
  baixarDocumento,
  gerarDocumento,
  obterPreview,
  obterStatus,
  processarNotas,
} from '@/api/notas'
import { NotasPreview } from '@/components/NotasPreview'
import { useToast } from '@/components/Toast'
import { UploadZone } from '@/components/UploadZone'
import { useGerarNotasStore, type Step } from '@/store/gerarNotasStore'
import type { DadosExtraidos } from '@/types'

const PASSOS: { numero: Step; rotulo: string }[] = [
  { numero: 1, rotulo: 'Upload e configuração' },
  { numero: 2, rotulo: 'Revisão dos dados' },
  { numero: 3, rotulo: 'Download' },
]

function Indicador({ atual }: { atual: Step }) {
  return (
    <ol className="mb-8 flex flex-wrap gap-4">
      {PASSOS.map((passo) => (
        <li key={passo.numero} className="flex items-center gap-2">
          <span
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
              atual >= passo.numero
                ? 'bg-ouro text-fundo-alt'
                : 'border border-borda bg-superficie text-texto-fraco'
            }`}
          >
            {passo.numero}
          </span>
          <span
            className={`text-sm ${
              atual >= passo.numero ? 'text-texto' : 'text-texto-fraco'
            }`}
          >
            {passo.rotulo}
          </span>
        </li>
      ))}
    </ol>
  )
}

export function GerarNotas() {
  const { notificar } = useToast()
  const store = useGerarNotasStore()
  const [gerando, setGerando] = useState(false)

  const empresas = useQuery({ queryKey: ['empresas'], queryFn: listarEmpresas })

  // Polling do status enquanto o job está em processamento.
  const status = useQuery({
    queryKey: ['status', store.jobId],
    queryFn: () => obterStatus(store.jobId as string),
    enabled: Boolean(store.jobId) && store.step !== 2,
    refetchInterval: (query) =>
      query.state.data?.status === 'processing' || query.state.data?.status === 'pending'
        ? 1500
        : false,
  })

  const processar = useMutation({
    mutationFn: processarNotas,
    onSuccess: (resposta) => {
      store.setJobId(resposta.job_id)
      notificar('Processamento iniciado', {
        descricao: 'Extraindo os dados dos PDFs enviados.',
      })
    },
    onError: (erro) =>
      notificar('Falha ao enviar os arquivos', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      }),
  })

  // Ao concluir a extração (step 1 → 2), carrega os dados para revisão.
  useEffect(() => {
    const jobId = store.jobId
    if (!jobId || store.step !== 1) return

    if (status.data?.status === 'done') {
      obterPreview(jobId)
        .then((resposta) => {
          store.setDados(resposta.dados)
          store.setStep(2)
        })
        .catch((erro) =>
          notificar('Falha ao carregar os dados extraídos', {
            descricao: mensagemDeErro(erro),
            variante: 'erro',
          }),
        )
    } else if (status.data?.status === 'error') {
      notificar('Erro no processamento', {
        descricao: status.data.error_message ?? 'Verifique os PDFs enviados.',
        variante: 'erro',
      })
    }
  }, [status.data?.status, store.jobId, store.step])

  const enviar = () => {
    if (!store.balancoPdf || !store.drePdf) {
      notificar('Envie os dois PDFs', {
        descricao: 'Balanço Patrimonial e DRE são obrigatórios.',
        variante: 'erro',
      })
      return
    }
    if (!store.empresaId) {
      notificar('Selecione a empresa', { variante: 'erro' })
      return
    }
    if (!store.dataAprovacao.trim()) {
      notificar('Informe a data de aprovação', {
        descricao: 'Exemplo: 20 de julho de 2026.',
        variante: 'erro',
      })
      return
    }

    const incompleto = store.anteriores.findIndex(
      (a) => Boolean(a.balancoPdf) !== Boolean(a.drePdf),
    )
    if (incompleto >= 0) {
      notificar('Exercício anterior incompleto', {
        descricao: `Envie o Balanço e a DRE de ${store.ano - incompleto - 1}, ou nenhum dos dois.`,
        variante: 'erro',
      })
      return
    }

    processar.mutate({
      balancoPdf: store.balancoPdf,
      drePdf: store.drePdf,
      empresaId: store.empresaId,
      ano: store.ano,
      dataAprovacao: store.dataAprovacao,
      anteriores: [
        { ...store.anteriores[0] },
        { ...store.anteriores[1] },
      ],
    })
  }

  const confirmarEGerar = async () => {
    if (!store.jobId || !store.dados) return

    setGerando(true)
    store.setStep(3)
    try {
      await gerarDocumento(store.jobId, store.dados)
      await status.refetch()
      notificar('Documento gerado', {
        descricao: 'O arquivo .docx está pronto para download.',
      })
    } catch (erro) {
      notificar('Falha ao gerar o documento', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      })
    } finally {
      setGerando(false)
    }
  }

  const baixar = async () => {
    if (!store.jobId) return
    try {
      const nome = await baixarDocumento(store.jobId, store.ano)
      store.setNomeArquivoBaixado(nome)
      notificar('Download concluído', { descricao: nome })
    } catch (erro) {
      notificar('Falha no download', {
        descricao: mensagemDeErro(erro),
        variante: 'erro',
      })
    }
  }

  const processando = processar.isPending || status.data?.status === 'processing'

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-texto">Gerar Notas Explicativas</h1>
      <p className="mb-8 text-sm text-texto-suave">
        Envie o Balanço Patrimonial e a DRE em PDF gerados pelo Domínio.
      </p>

      <Indicador atual={store.step} />

      {store.step === 1 && (
        <div className="space-y-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <UploadZone
              titulo="Balanço Patrimonial"
              descricao="Arquivo .pdf de até 50 MB"
              arquivo={store.balancoPdf}
              onArquivoSelecionado={store.setBalancoPdf}
              onErro={(mensagem) =>
                notificar('Arquivo inválido', { descricao: mensagem, variante: 'erro' })
              }
            />
            <UploadZone
              titulo="DRE"
              descricao="Arquivo .pdf de até 50 MB"
              arquivo={store.drePdf}
              onArquivoSelecionado={store.setDrePdf}
              onErro={(mensagem) =>
                notificar('Arquivo inválido', { descricao: mensagem, variante: 'erro' })
              }
            />
          </div>

          <details className="rounded-lg border border-borda bg-superficie p-5">
            <summary className="cursor-pointer text-sm font-semibold text-texto">
              Exercícios anteriores (opcional) — para as tabelas comparativas
            </summary>
            <p className="mt-2 text-sm text-texto-suave">
              O modelo das Notas Explicativas apresenta até três exercícios lado a lado.
              Envie o Balanço e a DRE de cada ano anterior que deva aparecer no
              comparativo. Anos não enviados aparecem zerados e podem ser corrigidos na
              revisão.
            </p>

            {([0, 1] as const).map((indice) => (
              <div key={indice} className="mt-4">
                <p className="mb-2 text-sm font-medium text-texto-suave">
                  Exercício de {store.ano - indice - 1}
                </p>
                <div className="grid gap-4 lg:grid-cols-2">
                  <UploadZone
                    titulo={`Balanço Patrimonial ${store.ano - indice - 1}`}
                    descricao="Arquivo .pdf de até 50 MB"
                    arquivo={store.anteriores[indice].balancoPdf}
                    onArquivoSelecionado={(arquivo) =>
                      store.setAnterior(indice, 'balancoPdf', arquivo)
                    }
                    onErro={(mensagem) =>
                      notificar('Arquivo inválido', {
                        descricao: mensagem,
                        variante: 'erro',
                      })
                    }
                  />
                  <UploadZone
                    titulo={`DRE ${store.ano - indice - 1}`}
                    descricao="Arquivo .pdf de até 50 MB"
                    arquivo={store.anteriores[indice].drePdf}
                    onArquivoSelecionado={(arquivo) =>
                      store.setAnterior(indice, 'drePdf', arquivo)
                    }
                    onErro={(mensagem) =>
                      notificar('Arquivo inválido', {
                        descricao: mensagem,
                        variante: 'erro',
                      })
                    }
                  />
                </div>
              </div>
            ))}
          </details>

          <div className="grid gap-4 rounded-lg border border-borda bg-superficie p-5 sm:grid-cols-3">
            <div>
              <label htmlFor="empresa" className="mb-1 block text-sm font-medium text-texto-suave">
                Empresa *
              </label>
              <select
                id="empresa"
                value={store.empresaId}
                onChange={(evento) => store.setEmpresaId(evento.target.value)}
                className="campo"
              >
                <option value="">Selecione...</option>
                {(empresas.data ?? []).map((empresa) => (
                  <option key={empresa.id} value={empresa.id}>
                    {empresa.nome}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="ano" className="mb-1 block text-sm font-medium text-texto-suave">
                Ano do exercício *
              </label>
              <input
                id="ano"
                type="number"
                min={1900}
                max={2999}
                value={store.ano}
                onChange={(evento) => store.setAno(Number(evento.target.value))}
                className="campo"
              />
            </div>

            <div>
              <label htmlFor="aprovacao" className="mb-1 block text-sm font-medium text-texto-suave">
                Data de aprovação *
              </label>
              <input
                id="aprovacao"
                type="text"
                placeholder="20 de julho de 2026"
                value={store.dataAprovacao}
                onChange={(evento) => store.setDataAprovacao(evento.target.value)}
                className="campo"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={enviar}
              disabled={processando}
              className="inline-flex items-center gap-2 btn-ouro px-5 py-2.5"
            >
              {processando && <Loader2 className="h-4 w-4 animate-spin" />}
              {processando ? 'Processando...' : 'Processar'}
            </button>
            {processando && status.data?.etapa_atual && (
              <span className="text-sm text-texto-suave">{status.data.etapa_atual}</span>
            )}
          </div>
        </div>
      )}

      {store.step === 2 && store.dados && (
        <div className="space-y-6">
          <NotasPreview
            dados={store.dados}
            onChange={(dados: DadosExtraidos) => store.setDados(dados)}
          />
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => store.setStep(1)}
              className="btn-neutro"
            >
              Voltar
            </button>
            <button
              type="button"
              onClick={confirmarEGerar}
              className="btn-ouro px-5 py-2.5"
            >
              Confirmar e Gerar
            </button>
          </div>
        </div>
      )}

      {store.step === 3 && (
        <div className="rounded-lg border border-borda bg-superficie p-8">
          {gerando ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-texto-suave" />
                <p className="text-sm text-texto-suave">
                  Gerando o documento Word com o papel timbrado...
                </p>
              </div>
              <Progress.Root
                value={null}
                className="h-2 w-full overflow-hidden rounded-full bg-superficie-alt"
              >
                <Progress.Indicator className="h-full w-1/3 animate-pulse rounded-full bg-ouro" />
              </Progress.Root>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-6 w-6 text-texto" />
                <div>
                  <p className="font-medium text-texto">Documento pronto</p>
                  <p className="text-sm text-texto-suave">
                    Notas_Explicativas_{store.ano}.docx
                  </p>
                </div>
              </div>

              <Progress.Root
                value={100}
                className="h-2 w-full overflow-hidden rounded-full bg-superficie-alt"
              >
                <Progress.Indicator
                  className="h-full rounded-full bg-ouro transition-all"
                  style={{ width: '100%' }}
                />
              </Progress.Root>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={baixar}
                  disabled={!status.data?.output_disponivel}
                  className="inline-flex items-center gap-2 btn-ouro px-5 py-2.5"
                >
                  <Download className="h-4 w-4" /> Baixar .docx
                </button>
                <button
                  type="button"
                  onClick={() => store.reset()}
                  className="btn-neutro"
                >
                  Gerar outro
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
