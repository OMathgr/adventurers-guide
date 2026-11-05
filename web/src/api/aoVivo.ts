// Atualização ao vivo: uma conexão SSE (GET /api/eventos) por aba enquanto se
// está logado. Os avisos só dizem o que mudou; aqui eles viram "invalidar"
// no React Query, que busca de novo só o que estiver na tela.
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { chamar, token } from './cliente'

export type Aviso =
  | { tipo: 'conectado' }
  | { tipo: 'mesa'; id: string }
  | { tipo: 'personagem'; id: string; mesa_id?: string | null }

/** O que cada aviso invalida (separado para dar para testar sem rede). */
export function aplicarAviso(cliente: QueryClient, aviso: Aviso) {
  switch (aviso.tipo) {
    case 'mesa':
      // tudo da mesa: dados, sessões, encontros, quadros, o revelado, a biblioteca
      cliente.invalidateQueries({ queryKey: ['mesas', aviso.id] })
      cliente.invalidateQueries({ queryKey: ['mesas'], exact: true })
      break
    case 'personagem':
      cliente.invalidateQueries({ queryKey: ['personagens', aviso.id] })
      cliente.invalidateQueries({ queryKey: ['personagens'], exact: true })
      if (aviso.mesa_id) {
        cliente.invalidateQueries({ queryKey: ['mesas', aviso.mesa_id, 'personagens', aviso.id] })
        cliente.invalidateQueries({ queryKey: ['mesas', aviso.mesa_id], exact: true })   // nível/foto na mesa
      }
      break
  }
}

const ESPERA_PARA_REABRIR_MS = 5000

/** Conexão ao vivo enquanto `ativo`. A URL leva um passe curto, nunca o login.
    Numa reconexão o navegador repete o passe vencido: o servidor recusa, a
    conexão fecha de vez e aqui se pede outro passe. */
export function useAoVivo(ativo: boolean) {
  const cliente = useQueryClient()
  useEffect(() => {
    if (!ativo || typeof EventSource === 'undefined') return
    let fonte: EventSource | null = null
    let espera: number | undefined
    let primeira = true
    let fechado = false

    async function abrir() {
      if (fechado || !token.ler()) return
      let passe: string
      try {
        ({ passe } = await chamar<{ passe: string }>('/eventos/passe', { metodo: 'POST' }))
      } catch {
        // sem rede ou servidor fora do ar (login vencido desliga o `ativo`)
        espera = window.setTimeout(abrir, ESPERA_PARA_REABRIR_MS)
        return
      }
      if (fechado) return
      fonte = new EventSource(`/api/eventos?passe=${encodeURIComponent(passe)}`)
      fonte.onmessage = (e) => {
        const aviso = JSON.parse(e.data) as Aviso
        if (aviso.tipo === 'conectado') {
          // numa reconexão (rede caiu, servidor reiniciou) algo pode ter mudado sem aviso
          if (!primeira) cliente.invalidateQueries()
          primeira = false
          return
        }
        aplicarAviso(cliente, aviso)
      }
      fonte.onerror = () => {
        if (fonte?.readyState === EventSource.CLOSED) espera = window.setTimeout(abrir, ESPERA_PARA_REABRIR_MS)
      }
    }
    abrir()
    return () => {
      fechado = true
      window.clearTimeout(espera)
      fonte?.close()
    }
  }, [ativo, cliente])
}
