// Tema da página. O script do index.html decide ao abrir (o escolhido ou o do
// sistema); aqui ele troca com a página aberta. Fica fora do Layout porque as
// telas sem login também acompanham o sistema.
import { useSyncExternalStore } from 'react'
import { flushSync } from 'react-dom'

const CHAVE_TEMA = 'ag.tema'
type Tema = 'escuro' | 'claro'

const ouvintes = new Set<() => void>()

function aplicar(tema: Tema) {
  document.documentElement.dataset.tema = tema
  ouvintes.forEach((ouvinte) => ouvinte())
}

function escolhido() {
  try { return localStorage.getItem(CHAVE_TEMA) } catch { return null }
}

/** Enquanto a pessoa não escolher um tema, muda junto com o do sistema. */
export function seguirOSistema() {
  window.matchMedia?.('(prefers-color-scheme: light)').addEventListener('change', (e) => {
    if (!escolhido()) aplicar(e.matches ? 'claro' : 'escuro')
  })
}

function assinar(ouvinte: () => void) {
  ouvintes.add(ouvinte)
  return () => { ouvintes.delete(ouvinte) }
}

const temaAtual = (): Tema => (document.documentElement.dataset.tema === 'claro' ? 'claro' : 'escuro')

export function useTema() {
  const tema = useSyncExternalStore(assinar, temaAtual)
  const alternar = () => {
    const novo = tema === 'escuro' ? 'claro' : 'escuro'
    // só guarda quando a pessoa escolhe: até lá, continua seguindo o sistema
    try { localStorage.setItem(CHAVE_TEMA, novo) } catch { /* modo privado */ }
    const trocar = () => flushSync(() => aplicar(novo))
    // onde o navegador sabe misturar as duas telas, a troca é suave
    if (document.startViewTransition) document.startViewTransition(trocar)
    else trocar()
  }
  return [tema, alternar] as const
}
