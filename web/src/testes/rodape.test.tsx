import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProvedorAutenticacao } from '../auth/Autenticacao'
import Layout from '../componentes/Layout'
import { Cadastro, Entrar } from '../paginas/Acesso'
import Privacidade from '../paginas/Privacidade'

function montar(rotas: ReactNode, inicio: string) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ google: false }), { status: 200 })))
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao>
        <MemoryRouter initialEntries={[inicio]}>
          <Routes>
            {rotas}
            <Route path="/privacidade" element={<Privacidade />} />
          </Routes>
        </MemoryRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>,
  )
}

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

const LICENCA = /Darrington Press Community Gaming \(DPCGL\) License/

describe('Rodapé', () => {
  it('aparece nas telas de entrada e leva ao aviso de privacidade', async () => {
    montar(<Route path="/entrar" element={<Entrar />} />, '/entrar')
    expect(screen.getByText(/projeto independente de fã/)).toBeInTheDocument()
    expect(screen.getByText(LICENCA)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://www.daggerheart.com' })).toHaveAttribute('href', 'https://www.daggerheart.com')
    await userEvent.click(screen.getByRole('link', { name: 'Aviso de privacidade' }))
    expect(await screen.findByRole('heading', { name: 'Privacidade no Adventurer’s Guide' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'o.mathgr@outlook.com' })).toHaveAttribute('href', 'mailto:o.mathgr@outlook.com')
  })

  it('aparece nas páginas de quem está logado', () => {
    montar(<Route element={<Layout />}><Route path="/mesas" element={<p>Mesas</p>} /></Route>, '/mesas')
    expect(screen.getByText(LICENCA)).toBeInTheDocument()
  })

  it('o cadastro tem o link para o aviso de privacidade', () => {
    montar(<Route path="/cadastro" element={<Cadastro />} />, '/cadastro')
    const links = screen.getAllByRole('link', { name: 'Aviso de privacidade' })
    expect(links).toHaveLength(2)   // no formulário e no rodapé
    expect(links.every((l) => l.getAttribute('href') === '/privacidade')).toBe(true)
  })

  it('a página de privacidade abre sem login', () => {
    montar(null, '/privacidade')
    expect(screen.getByRole('heading', { name: 'Seus direitos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/entrar')
  })
})
