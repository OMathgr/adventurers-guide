// Atualização ao vivo: uma conexão SSE (GET /api/eventos) por aba enquanto se
// está logado. Os avisos só dizem o que mudou; aqui eles viram "invalidar"
// no React Query, que busca de novo só o que estiver na tela.
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { token } from './cliente'

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

/** Conexão ao vivo enquanto `ativo`. O token é lido na hora de conectar: como
    ele se renova durante o uso, a conexão não precisa reabrir a cada renovação.
    Se o servidor recusar o token antigo (numa reconexão), reabre com o atual. */
export function useAoVivo(ativo: boolean) {
  const cliente = useQueryClient()
  useEffect(() => {
    if (!ativo || typeof EventSource === 'undefined') return
    let fonte: EventSource | null = null
    let espera: number | undefined
    let primeira = true
    let fechado = false

    function abrir() {
      const atual = token.ler()
      if (fechado || !atual) return
      fonte = new EventSource(`/api/eventos?token=${encodeURIComponent(atual)}`)
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
        // o navegador reconecta sozinho, mas com a URL (e o token) de antes; se o
        // servidor recusou, a conexão fecha de vez: abre outra com o token atual
        if (fonte?.readyState === EventSource.CLOSED) espera = window.setTimeout(abrir, 5000)
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
