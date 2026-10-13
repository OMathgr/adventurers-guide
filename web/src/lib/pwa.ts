// App instalável (PWA): registro do service worker, convite de instalação e estado da conexão.
import { useEffect, useState } from 'react'

/** Registra o service worker (só no build: em desenvolvimento o cache atrapalharia o Vite). */
export function registrarServiceWorker() {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return
  const registrar = () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* sem PWA, o site segue funcionando */ })
  }
  // depois de carregar, para não disputar a rede com a primeira tela
  if (document.readyState === 'complete') registrar()
  else window.addEventListener('load', registrar, { once: true })
}

// O Chrome/Edge (Android e computador) avisam quando o app pode ser instalado.
// O Safari (iPhone) não: lá é Compartilhar → "Adicionar à Tela de Início".
interface PedidoDeInstalacao extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/** Devolve a função que abre o convite de instalação, ou null se não der para instalar agora. */
export function useInstalar(): (() => void) | null {
  const [pedido, setPedido] = useState<PedidoDeInstalacao | null>(null)
  useEffect(() => {
    const guardar = (e: Event) => { e.preventDefault(); setPedido(e as PedidoDeInstalacao) }
    const instalado = () => setPedido(null)
    window.addEventListener('beforeinstallprompt', guardar)
    window.addEventListener('appinstalled', instalado)
    return () => {
      window.removeEventListener('beforeinstallprompt', guardar)
      window.removeEventListener('appinstalled', instalado)
    }
  }, [])
  if (!pedido) return null
  return () => {
    void pedido.prompt()
    // o mesmo pedido não pode ser usado duas vezes
    void pedido.userChoice.finally(() => setPedido(null))
  }
}

/** true enquanto o aparelho tiver conexão. */
export function useOnline() {
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    const ligar = () => setOnline(true)
    const desligar = () => setOnline(false)
    window.addEventListener('online', ligar)
    window.addEventListener('offline', desligar)
    return () => {
      window.removeEventListener('online', ligar)
      window.removeEventListener('offline', desligar)
    }
  }, [])
  return online
}
