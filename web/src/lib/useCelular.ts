// Para o que muda de lugar ou de forma no celular e o CSS sozinho não resolve
// (a mesma quebra `sm` do Tailwind).
import { useSyncExternalStore } from 'react'

const CONSULTA = '(max-width: 639px)'

function assinar(aoMudar: () => void) {
  const consulta = window.matchMedia?.(CONSULTA)
  consulta?.addEventListener('change', aoMudar)
  return () => consulta?.removeEventListener('change', aoMudar)
}

export function useCelular() {
  return useSyncExternalStore(assinar, () => window.matchMedia?.(CONSULTA).matches ?? false)
}
