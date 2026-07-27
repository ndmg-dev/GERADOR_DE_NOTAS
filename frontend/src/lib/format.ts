const formatadorMoeda = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatarValor(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return '-'
  return formatadorMoeda.format(valor)
}

export function formatarDataHora(iso: string | null): string {
  if (!iso) return '-'
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '-'
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

/** Converte "1.234,56" ou "1234.56" digitado pelo usuário em número. */
export function parsearValor(texto: string): number | null {
  const limpo = texto.trim().replace(/\s/g, '')
  if (!limpo) return null

  const normalizado = limpo.includes(',')
    ? limpo.replace(/\./g, '').replace(',', '.')
    : limpo

  const numero = Number(normalizado)
  return Number.isFinite(numero) ? numero : null
}
