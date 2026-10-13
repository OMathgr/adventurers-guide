// Ouro em punhados, bolsas e baús (só para mostrar e digitar: as regras, como
// o máximo de 1 baú, ficam no motor e chegam como mensagem da API).
// Regra opcional: 10 moedas = 1 punhado (só com a regra ligada na mesa).
export const PUNHADOS_POR_BOLSA = 10
export const PUNHADOS_POR_BAU = 100
export const MOEDAS_POR_PUNHADO = 10

export type Moeda = 'moedas' | 'punhados' | 'bolsas' | 'baus'

/** Quanto vale uma unidade, em moedas (a menor de todas). */
export const EM_MOEDAS: Record<Moeda, number> = {
  moedas: 1, punhados: MOEDAS_POR_PUNHADO, bolsas: MOEDAS_POR_PUNHADO * PUNHADOS_POR_BOLSA,
  baus: MOEDAS_POR_PUNHADO * PUNHADOS_POR_BAU,
}

/** Valor em moedas -> o que a API recebe ({ punhados, moedas }, mesmo sinal). */
export function separar(valorEmMoedas: number) {
  return { punhados: Math.trunc(valorEmMoedas / MOEDAS_POR_PUNHADO), moedas: valorEmMoedas % MOEDAS_POR_PUNHADO }
}

export function decompor(total: number) {
  return {
    baus: Math.floor(total / PUNHADOS_POR_BAU),
    bolsas: Math.floor((total % PUNHADOS_POR_BAU) / PUNHADOS_POR_BOLSA),
    punhados: total % PUNHADOS_POR_BOLSA,
  }
}

/** "1 baú, 2 bolsas e 3 punhados" (ou "nada"); `moedas` só com a regra opcional. */
export function formatarOuro(total: number, moedas = 0): string {
  const { baus, bolsas, punhados } = decompor(total)
  const partes = [
    baus && `${baus} ${baus === 1 ? 'baú' : 'baús'}`,
    bolsas && `${bolsas} ${bolsas === 1 ? 'bolsa' : 'bolsas'}`,
    punhados && `${punhados} ${punhados === 1 ? 'punhado' : 'punhados'}`,
    moedas && `${moedas} ${moedas === 1 ? 'moeda' : 'moedas'}`,
  ].filter(Boolean) as string[]
  if (partes.length === 0) return 'nada'
  return partes.length === 1 ? partes[0] : `${partes.slice(0, -1).join(', ')} e ${partes.at(-1)}`
}
