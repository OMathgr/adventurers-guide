import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAoVivo } from '../api/aoVivo'

class FonteFalsa {
  static CLOSED = 2
  static abertas: FonteFalsa[] = []
  readyState = 1
  fechada = false
  onmessage: ((e: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  url: string
  constructor(url: string) { this.url = url; FonteFalsa.abertas.push(this) }
  close() { this.fechada = true }
}

const passar = (ms = 0) => act(async () => { await vi.advanceTimersByTimeAsync(ms) })

function conectar() {
  const cliente = new QueryClient()
  const envolver = ({ children }: { children: ReactNode }) => <QueryClientProvider client={cliente}>{children}</QueryClientProvider>
  return renderHook(() => useAoVivo(true), { wrapper: envolver })
}

function apiDePasses() {
  let n = 0
  return vi.fn(async () => {
    n += 1
    return { status: 200, ok: true, json: async () => ({ passe: `passe-${n}` }) }
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  FonteFalsa.abertas = []
  vi.stubGlobal('EventSource', FonteFalsa)
  localStorage.setItem('ag.token', 'login-secreto')
})
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); localStorage.clear() })

describe('Conexão ao vivo', () => {
  it('a URL leva o passe, nunca o login; o passe é pedido com o login no cabeçalho', async () => {
    const api = apiDePasses()
    vi.stubGlobal('fetch', api)
    conectar()
    await passar()
    expect(FonteFalsa.abertas.map((f) => f.url)).toEqual(['/api/eventos?passe=passe-1'])
    expect(api).toHaveBeenCalledWith('/api/eventos/passe', expect.objectContaining({
      method: 'POST', headers: expect.objectContaining({ Authorization: 'Bearer login-secreto' }) }))
  })

  it('recusada ao reconectar com o passe vencido, abre com um passe novo', async () => {
    vi.stubGlobal('fetch', apiDePasses())
    conectar()
    await passar()
    const primeira = FonteFalsa.abertas[0]
    primeira.readyState = FonteFalsa.CLOSED
    primeira.onerror?.()
    await passar(5000)
    expect(FonteFalsa.abertas.map((f) => f.url)).toEqual(['/api/eventos?passe=passe-1', '/api/eventos?passe=passe-2'])
  })

  it('o navegador ainda tentando sozinho (rede caiu) não abre outra conexão', async () => {
    vi.stubGlobal('fetch', apiDePasses())
    conectar()
    await passar()
    FonteFalsa.abertas[0].readyState = 0
    FonteFalsa.abertas[0].onerror?.()
    await passar(5000)
    expect(FonteFalsa.abertas).toHaveLength(1)
  })

  it('sem rede ao pedir o passe, tenta de novo', async () => {
    const api = vi.fn()
      .mockRejectedValueOnce(new TypeError('sem rede'))
      .mockResolvedValue({ status: 200, ok: true, json: async () => ({ passe: 'depois' }) })
    vi.stubGlobal('fetch', api)
    conectar()
    await passar()
    expect(FonteFalsa.abertas).toHaveLength(0)
    await passar(5000)
    expect(FonteFalsa.abertas.map((f) => f.url)).toEqual(['/api/eventos?passe=depois'])
  })

  it('ao sair da tela antes de o passe chegar, não abre a conexão', async () => {
    vi.stubGlobal('fetch', apiDePasses())
    const { unmount } = conectar()
    unmount()
    await passar(5000)
    expect(FonteFalsa.abertas).toHaveLength(0)
  })
})
