import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import codigoDoServiceWorker from '../../public/sw.js?raw'
import { useInstalar, useOnline } from './pwa'

type Estrategia = (url: string, modo: string, origem: string) => string | null

/** Carrega o public/sw.js com um `self` de mentira e devolve a função de decisão. */
function carregarServiceWorker(): Estrategia {
  const falso: Record<string, unknown> = { addEventListener: () => {} }
  new Function('self', codigoDoServiceWorker)(falso)
  return falso.estrategia as Estrategia
}

describe('service worker', () => {
  const estrategia = carregarServiceWorker()
  const ORIGEM = 'https://app.exemplo'

  it('nunca intercepta a API (dados e fluxo ao vivo vêm sempre do servidor)', () => {
    expect(estrategia(`${ORIGEM}/api/eventos?token=x`, 'cors', ORIGEM)).toBeNull()
    expect(estrategia(`${ORIGEM}/api/mesas`, 'cors', ORIGEM)).toBeNull()
    expect(estrategia(`${ORIGEM}/api/imagens/abc`, 'no-cors', ORIGEM)).toBeNull()
  })

  it('abre as páginas pela rede, com a casca guardada para quando não houver rede', () => {
    expect(estrategia(`${ORIGEM}/mesas/123`, 'navigate', ORIGEM)).toBe('navegacao')
  })

  it('guarda os arquivos do build e as fontes', () => {
    expect(estrategia(`${ORIGEM}/assets/index-abc123.js`, 'no-cors', ORIGEM)).toBe('cache-primeiro')
    expect(estrategia(`${ORIGEM}/icones/icone-192.png`, 'no-cors', ORIGEM)).toBe('cache-e-atualiza')
    expect(estrategia('https://fonts.gstatic.com/s/inter.woff2', 'cors', ORIGEM)).toBe('cache-e-atualiza')
  })

  it('deixa outras origens com o navegador', () => {
    expect(estrategia('https://outro.site/x.js', 'no-cors', ORIGEM)).toBeNull()
  })
})

describe('useInstalar', () => {
  it('só oferece instalar depois que o navegador permite, e uma vez só', async () => {
    const { result } = renderHook(() => useInstalar())
    expect(result.current).toBeNull()

    const prompt = vi.fn().mockResolvedValue(undefined)
    const pedido = Object.assign(new Event('beforeinstallprompt', { cancelable: true }),
      { prompt, userChoice: Promise.resolve({ outcome: 'accepted' }) })
    act(() => { window.dispatchEvent(pedido) })
    expect(pedido.defaultPrevented).toBe(true)   // o app decide quando mostrar
    expect(result.current).toBeTypeOf('function')

    await act(async () => { result.current!() })
    expect(prompt).toHaveBeenCalledOnce()
    expect(result.current).toBeNull()
  })
})

describe('useOnline', () => {
  it('acompanha a conexão', () => {
    const { result } = renderHook(() => useOnline())
    expect(result.current).toBe(true)
    act(() => { window.dispatchEvent(new Event('offline')) })
    expect(result.current).toBe(false)
    act(() => { window.dispatchEvent(new Event('online')) })
    expect(result.current).toBe(true)
  })
})
