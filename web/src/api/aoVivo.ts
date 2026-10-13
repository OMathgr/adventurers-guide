// Atualização ao vivo: uma conexão SSE (GET /api/eventos) por aba enquanto se
// está logado. Os avisos só dizem o que mudou; aqui eles viram "invalidar"
// no React Query, que busca de novo só o que estiver na tela.
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

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

export function useAoVivo(token: string | null) {
  const cliente = useQueryClient()
  useEffect(() => {
    if (!token || typeof EventSource === 'undefined') return
    const fonte = new EventSource(`/api/eventos?token=${encodeURIComponent(token)}`)
    let primeira = true
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
    return () => fonte.close()
  }, [token, cliente])
}
