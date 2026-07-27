import { useState } from 'react'
import { formatarValor, parsearValor } from '@/lib/format'
import type { Balanco, ContaItem, DadosExtraidos, Dre, GrupoContas, Imobilizado } from '@/types'

interface NotasPreviewProps {
  dados: DadosExtraidos
  onChange: (dados: DadosExtraidos) => void
}

/** Uma linha editável no formulário de revisão. */
interface LinhaEditavel {
  caminho: string[]
  rotulo: string
  valor: number | null
}

const ROTULOS_BALANCO: Record<string, string> = {
  caixa_equivalentes: 'Caixa e equivalentes de caixa',
  clientes: 'Clientes',
  estoques: 'Estoques',
  outros_creditos: 'Outros créditos',
  cartao_corporativo: 'Cartão corporativo de colaboradores',
  realizavel_lp: 'Realizável a longo prazo',
  imobilizado: 'Imobilizado',
  intangivel: 'Intangível',
  fornecedores: 'Fornecedores',
  obrigacoes_fiscais: 'Obrigações fiscais',
  parcelamentos: 'Parcelamentos',
  obrigacoes_trabalhistas: 'Obrigações trabalhistas',
  adiantamento_clientes: 'Adiantamento de clientes',
  provisoes: 'Provisões',
  outras_obrigacoes: 'Outras obrigações',
  emprestimos: 'Empréstimos e financiamentos',
  capital_social: 'Capital social',
  reservas: 'Reservas',
  ajustes: 'Ajustes de avaliação patrimonial',
  total: 'Total do grupo',
}

const ROTULOS_DRE: Record<string, string> = {
  receita_bruta: 'Receita operacional bruta',
  deducoes: 'Deduções da receita bruta',
  receita_liquida: 'Receita operacional líquida',
  custos_aplicados: 'Custos aplicados',
  mao_obra_direta: 'Mão de obra direta',
  lucro_bruto: 'Lucro bruto',
  despesas_pessoal: 'Despesas com pessoal',
  impostos_taxas: 'Impostos, taxas e contribuições',
  despesas_gerais: 'Despesas gerais',
  receitas_financeiras: 'Receitas financeiras',
  despesas_financeiras: 'Despesas financeiras',
  liquido: 'Resultado financeiro líquido',
  outras_receitas: 'Outras receitas',
  resultado_operacional: 'Resultado operacional',
  lucro_liquido: 'Lucro líquido do exercício',
  total: 'Total das despesas operacionais',
}

const ROTULOS_MOVIMENTO = {
  aquisicoes: 'Aquisições',
  baixas: 'Baixas',
  depreciacao: 'Depreciação do período',
} as const

const ROTULOS_NATUREZA = {
  custo_servico: 'Custo do serviço prestado',
  servicos_terceiros: 'Serviços de terceiros',
  depreciacoes: 'Depreciações',
  outros: 'Outros custos e despesas',
} as const

function rotular(chave: string, dicionario: Record<string, string>): string {
  return dicionario[chave] ?? chave.replace(/_/g, ' ')
}

function ehGrupo(valor: unknown): valor is GrupoContas {
  return typeof valor === 'object' && valor !== null && 'itens' in valor
}

function ehImobilizado(valor: unknown): valor is Imobilizado {
  return typeof valor === 'object' && valor !== null && 'grupos' in valor
}

/** Substitui imutavelmente o valor no caminho informado, preservando arrays. */
function definirEmCaminho<T>(objeto: T, caminho: string[], valor: number | null): T {
  if (caminho.length === 0) return objeto
  const [chave, ...resto] = caminho
  const atual = (objeto as Record<string, unknown>)[chave]
  const novo =
    resto.length === 0 ? valor : definirEmCaminho(atual as Record<string, unknown>, resto, valor)

  if (Array.isArray(objeto)) {
    const copia = [...objeto] as unknown[]
    copia[Number(chave)] = novo
    return copia as T
  }

  return { ...(objeto as Record<string, unknown>), [chave]: novo } as T
}

function CampoValor({
  rotulo,
  valor,
  onChange,
}: {
  rotulo: string
  valor: number | null
  onChange: (novo: number | null) => void
}) {
  return (
    <div className="flex items-center gap-3 border-b border-borda/60 py-2 last:border-0">
      <label className="flex-1 text-sm text-texto-suave">{rotulo}</label>
      <input
        type="text"
        defaultValue={valor === null ? '' : formatarValor(valor)}
        onBlur={(evento) => onChange(parsearValor(evento.target.value))}
        aria-label={rotulo}
        className="campo w-40 px-2 py-1 text-right font-mono tabular-nums"
      />
    </div>
  )
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-borda bg-superficie p-5">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-texto">
        {titulo}
      </h3>
      {children}
    </section>
  )
}

export function NotasPreview({ dados, onChange }: NotasPreviewProps) {
  const [indiceExercicio, setIndiceExercicio] = useState(0)

  const atualizar = (caminho: string[], valor: number | null) => {
    onChange(definirEmCaminho(dados, caminho, valor))
  }

  const linhasDeGrupo = (
    grupo: GrupoContas,
    caminhoBase: string[],
  ): LinhaEditavel[] => [
    { caminho: [...caminhoBase, 'total'], rotulo: 'Total', valor: grupo.total },
    ...grupo.itens.map((item: ContaItem, indice: number) => ({
      caminho: [...caminhoBase, 'itens', String(indice), 'valor'],
      rotulo: item.descricao,
      valor: item.valor,
    })),
  ]

  const renderizarGrupos = (
    origem: Record<string, unknown>,
    caminhoBase: string[],
  ) =>
    Object.entries(origem).map(([chave, valor]) => {
      if (valor === null || valor === undefined) return null

      if (ehImobilizado(valor)) {
        return (
          <Secao key={chave} titulo={rotular(chave, ROTULOS_BALANCO)}>
            {valor.grupos.map((grupo, indice) => (
              <CampoValor
                key={grupo.nome}
                rotulo={`${grupo.nome} (custo)`}
                valor={grupo.custo}
                onChange={(novo) =>
                  atualizar([...caminhoBase, chave, 'grupos', String(indice), 'custo'], novo)
                }
              />
            ))}
            <CampoValor
              rotulo="Depreciação acumulada"
              valor={valor.depreciacao_total}
              onChange={(novo) =>
                atualizar([...caminhoBase, chave, 'depreciacao_total'], novo)
              }
            />
            <CampoValor
              rotulo="Total líquido"
              valor={valor.total_liquido}
              onChange={(novo) => atualizar([...caminhoBase, chave, 'total_liquido'], novo)}
            />
          </Secao>
        )
      }

      if (ehGrupo(valor)) {
        return (
          <Secao key={chave} titulo={rotular(chave, ROTULOS_BALANCO)}>
            {linhasDeGrupo(valor, [...caminhoBase, chave]).map((linha) => (
              <CampoValor
                key={linha.caminho.join('.')}
                rotulo={linha.rotulo}
                valor={linha.valor}
                onChange={(novo) => atualizar(linha.caminho, novo)}
              />
            ))}
          </Secao>
        )
      }

      if (typeof valor === 'number') {
        return (
          <Secao key={chave} titulo={rotular(chave, ROTULOS_BALANCO)}>
            <CampoValor
              rotulo={rotular(chave, ROTULOS_BALANCO)}
              valor={valor}
              onChange={(novo) => atualizar([...caminhoBase, chave], novo)}
            />
          </Secao>
        )
      }

      return null
    })

  const exercicio = dados.exercicios[indiceExercicio]
  if (!exercicio) {
    return <p className="text-sm text-texto-suave">Nenhum exercício extraído.</p>
  }

  const balanco: Balanco = exercicio.balanco
  const dre: Dre = exercicio.dre
  const base = ['exercicios', String(indiceExercicio)]

  return (
    <div className="space-y-8">
      {dados.exercicios.length > 1 && (
        <div className="flex flex-wrap gap-2 border-b border-borda pb-3">
          {dados.exercicios.map((e, indice) => (
            <button
              key={e.ano}
              type="button"
              onClick={() => setIndiceExercicio(indice)}
              className={`rounded px-3 py-1.5 text-sm ${
                indice === indiceExercicio
                  ? 'bg-ouro text-fundo-alt'
                  : 'text-texto-suave hover:bg-superficie-alt hover:text-texto'
              }`}
            >
              Exercício {e.ano}
            </button>
          ))}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-lg font-semibold text-texto">
          Balanço Patrimonial de {exercicio.ano}
        </h2>
        <p className="mb-4 text-sm text-texto-suave">
          Confira os valores extraídos e corrija o que for necessário antes de gerar o
          documento. Valores credores aparecem negativos, como no relatório do Domínio.
        </p>

        <div className="grid gap-4 lg:grid-cols-2">
          {renderizarGrupos(balanco.ativo.circulante, [...base, 'balanco', 'ativo', 'circulante'])}
          {renderizarGrupos(balanco.ativo.nao_circulante, [...base, 'balanco', 'ativo', 'nao_circulante'])}
          {renderizarGrupos(balanco.passivo.circulante, [...base, 'balanco', 'passivo', 'circulante'])}
          <Secao titulo="Patrimônio líquido">
            {Object.entries(balanco.patrimonio_liquido).map(([chave, valor]) => (
              <CampoValor
                key={chave}
                rotulo={rotular(chave, ROTULOS_BALANCO)}
                valor={valor}
                onChange={(novo) =>
                  atualizar([...base, 'balanco', 'patrimonio_liquido', chave], novo)
                }
              />
            ))}
          </Secao>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-texto">
          Demonstração do Resultado
        </h2>

        <div className="grid gap-4 lg:grid-cols-2">
          <Secao titulo="Receitas">
            <CampoValor
              rotulo={ROTULOS_DRE.receita_bruta}
              valor={dre.receita_bruta}
              onChange={(novo) => atualizar([...base, 'dre', 'receita_bruta'], novo)}
            />
            <CampoValor
              rotulo={ROTULOS_DRE.deducoes}
              valor={dre.deducoes}
              onChange={(novo) => atualizar([...base, 'dre', 'deducoes'], novo)}
            />
            <CampoValor
              rotulo={ROTULOS_DRE.receita_liquida}
              valor={dre.receita_liquida}
              onChange={(novo) => atualizar([...base, 'dre', 'receita_liquida'], novo)}
            />
          </Secao>

          <Secao titulo="Custos">
            {Object.entries(dre.custos).map(([chave, valor]) => (
              <CampoValor
                key={chave}
                rotulo={rotular(chave, ROTULOS_DRE)}
                valor={valor}
                onChange={(novo) => atualizar([...base, 'dre', 'custos', chave], novo)}
              />
            ))}
            <CampoValor
              rotulo={ROTULOS_DRE.lucro_bruto}
              valor={dre.lucro_bruto}
              onChange={(novo) => atualizar([...base, 'dre', 'lucro_bruto'], novo)}
            />
          </Secao>

          <Secao titulo="Despesas operacionais">
            {(['total', 'despesas_pessoal', 'impostos_taxas', 'despesas_gerais'] as const).map(
              (chave) => (
                <CampoValor
                  key={chave}
                  rotulo={rotular(chave, ROTULOS_DRE)}
                  valor={dre.despesas_operacionais[chave]}
                  onChange={(novo) =>
                    atualizar([...base, 'dre', 'despesas_operacionais', chave], novo)
                  }
                />
              ),
            )}
          </Secao>

          <Secao titulo="Resultado financeiro e do exercício">
            {(['receitas_financeiras', 'despesas_financeiras', 'liquido'] as const).map(
              (chave) => (
                <CampoValor
                  key={chave}
                  rotulo={rotular(chave, ROTULOS_DRE)}
                  valor={dre.resultado_financeiro[chave]}
                  onChange={(novo) =>
                    atualizar([...base, 'dre', 'resultado_financeiro', chave], novo)
                  }
                />
              ),
            )}
            <CampoValor
              rotulo={ROTULOS_DRE.outras_receitas}
              valor={dre.outras_receitas}
              onChange={(novo) => atualizar([...base, 'dre', 'outras_receitas'], novo)}
            />
            <CampoValor
              rotulo={ROTULOS_DRE.resultado_operacional}
              valor={dre.resultado_operacional}
              onChange={(novo) => atualizar([...base, 'dre', 'resultado_operacional'], novo)}
            />
            <CampoValor
              rotulo={ROTULOS_DRE.lucro_liquido}
              valor={dre.lucro_liquido}
              onChange={(novo) => atualizar([...base, 'dre', 'lucro_liquido'], novo)}
            />
          </Secao>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-texto">
          Movimentação do Imobilizado ({exercicio.ano})
        </h2>
        <p className="mb-4 text-sm text-texto-suave">
          O balanço informa apenas os saldos. Preencha aqui as aquisições, baixas e a
          depreciação do período que aparecerão na Nota 08. O saldo anterior vem do balanço
          do exercício precedente, quando enviado.
        </p>

        {Object.keys(exercicio.movimentacao_imobilizado ?? {}).length === 0 ? (
          <p className="rounded-lg border border-borda bg-superficie p-5 text-sm text-texto-fraco">
            Nenhum grupo de imobilizado encontrado neste exercício.
          </p>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {Object.entries(exercicio.movimentacao_imobilizado).map(
              ([chave, movimento]) => (
                <Secao key={chave} titulo={movimento.rotulo}>
                  {(['aquisicoes', 'baixas', 'depreciacao'] as const).map((campo) => (
                    <CampoValor
                      key={campo}
                      rotulo={ROTULOS_MOVIMENTO[campo]}
                      valor={movimento[campo] ?? null}
                      onChange={(novo) =>
                        atualizar(
                          [...base, 'movimentacao_imobilizado', chave, campo],
                          novo,
                        )
                      }
                    />
                  ))}
                </Secao>
              ),
            )}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-texto">
          Natureza das Despesas e Custos ({exercicio.ano})
        </h2>
        <p className="mb-4 text-sm text-texto-suave">
          A DRE do Domínio informa apenas o total das despesas operacionais. Ajuste aqui a
          abertura por natureza que aparecerá na Nota 18 — o total da coluna deve fechar com
          a DRE.
        </p>

        <div className="grid gap-4 lg:grid-cols-2">
          <Secao titulo="Custos">
            <CampoValor
              rotulo={ROTULOS_NATUREZA.custo_servico}
              valor={exercicio.natureza_despesas?.custo_servico ?? null}
              onChange={(novo) =>
                atualizar([...base, 'natureza_despesas', 'custo_servico'], novo)
              }
            />
          </Secao>

          <Secao titulo="Despesas gerais e administrativas">
            {(['servicos_terceiros', 'depreciacoes', 'outros'] as const).map((chave) => (
              <CampoValor
                key={chave}
                rotulo={ROTULOS_NATUREZA[chave]}
                valor={exercicio.natureza_despesas?.[chave] ?? null}
                onChange={(novo) =>
                  atualizar([...base, 'natureza_despesas', chave], novo)
                }
              />
            ))}
          </Secao>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-texto">
          Notas que serão geradas ({dados.notas.length})
        </h2>
        <ol className="grid gap-1 rounded-lg border border-borda bg-superficie p-5 text-sm text-texto-suave sm:grid-cols-2">
          {dados.notas.map((nota) => (
            <li key={nota.numero}>
              <span className="font-medium text-texto">
                {String(nota.numero).padStart(2, '0')}.
              </span>{' '}
              {nota.titulo}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
