// Cores dos dados 3D (Esperança, Medo e os outros). Ficam neste aparelho; o
// padrão segue as cores do app (laranja da Esperança, azul do Medo).
import { useState } from 'react'

export type CoresDosDados = { esperanca: string; medo: string; outros: string }

export const CORES_PADRAO: CoresDosDados = { esperanca: '#f39237', medo: '#3d5fb8', outros: '#d8dde8' }
const CHAVE = 'ag.dados.cores'

export function lerCores(): CoresDosDados {
  try {
    const salvas = JSON.parse(localStorage.getItem(CHAVE) ?? 'null') as Partial<CoresDosDados> | null
    return { ...CORES_PADRAO, ...(salvas ?? {}) }
  } catch {
    return CORES_PADRAO
  }
}

export function useCoresDosDados() {
  const [cores, setCores] = useState(lerCores)
  const mudar = (parcial: Partial<CoresDosDados>) => {
    const novas = { ...cores, ...parcial }
    setCores(novas)
    try { localStorage.setItem(CHAVE, JSON.stringify(novas)) } catch { /* modo privado: vale até fechar */ }
  }
  return [cores, mudar] as const
}

/** Cor dos números sobre o dado: escura em dado claro, clara em dado escuro. */
export function corDoNumero(fundo: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(fundo.slice(i, i + 2), 16) / 255)
  const luz = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luz > 0.5 ? '#141414' : '#ffffff'
}

/** Faces que a biblioteca 3D sabe desenhar. */
export const FACES_3D = new Set([4, 6, 8, 10, 12, 20, 100])

export type GrupoDeDados = { cor: string; dados: { faces: number; valor: number }[] }

/** "1d6+1d8@3,5": a notação da biblioteca com os resultados já decididos pelo servidor. */
export function notacao(grupo: GrupoDeDados): string {
  const dados = grupo.dados.filter((d) => FACES_3D.has(d.faces) && d.valor >= 1 && d.valor <= d.faces)
  if (dados.length === 0) return ''
  return dados.map((d) => `1d${d.faces}`).join('+') + '@' + dados.map((d) => d.valor).join(',')
}
