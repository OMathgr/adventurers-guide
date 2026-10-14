// App instalável (PWA): registro do service worker, convite de instalação e estado da conexão.
import { useEffect, useState, useSyncExternalStore } from 'react'

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

// O Chrome manda o convite UMA vez por carregamento, logo no começo. Ele é guardado
// aqui assim que o app carrega (antes de qualquer tela): se só a barra do topo
// ouvisse, quem abre o site na tela de entrar perdia o convite.
let pedidoGuardado: PedidoDeInstalacao | null = null
const avisar = new Set<() => void>()
const mudou = () => avisar.forEach((f) => f())

/** Chame uma vez, no início (main.tsx), antes de montar as telas. */
export function capturarConviteDeInstalacao() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()   // o app decide quando mostrar (botão "Instalar")
    pedidoGuardado = e as PedidoDeInstalacao
    mudou()
  })
  window.addEventListener('appinstalled', () => { pedidoGuardado = null; mudou() })
}

function assinar(f: () => void) {
  avisar.add(f)
  return () => { avisar.delete(f) }
}

/** Devolve a função que abre o convite de instalação, ou null se não der para instalar agora. */
export function useInstalar(): (() => void) | null {
  const pedido = useSyncExternalStore(assinar, () => pedidoGuardado, () => null)
  if (!pedido) return null
  return () => {
    void pedido.prompt()
    // o mesmo pedido não pode ser usado duas vezes
    void pedido.userChoice.finally(() => { pedidoGuardado = null; mudou() })
  }
}

/** Já está aberto como app instalado (tela cheia, sem a barra do navegador)? */
export function abertoComoApp(): boolean {
  try {
    return window.matchMedia('(display-mode: standalone)').matches
      || (navigator as Navigator & { standalone?: boolean }).standalone === true
  } catch {
    return false
  }
}

/** iPhone/iPad: lá não há convite; instala pelo Compartilhar do Safari. */
export const ehIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent)

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
