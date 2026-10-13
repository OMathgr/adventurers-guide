import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProvedorAutenticacao } from '../auth/Autenticacao'
import { Entrar, EntrarComGoogle, RecuperarSenha, RedefinirSenha } from '../paginas/Acesso'

/** fetch falso: responde por caminho (sem o /api) e guarda as chamadas. */
function api(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string, _opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    return new Response(JSON.stringify(caminho in rotas ? rotas[caminho] : {}), { status: 200 })
  })
}

function montar(ui: ReactNode, inicio = '/') {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao>
        <MemoryRouter initialEntries={[inicio]}>
          <Routes>
            <Route path="*" element={ui} />
            <Route path="/personagens" element={<p>Lista de personagens</p>} />
          </Routes>
        </MemoryRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
  window.location.hash = ''
})

describe('Entrar', () => {
  it('mostra o Google só quando configurado, o link de recuperação e o erro vindo do Google', async () => {
    vi.stubGlobal('fetch', api({ '/auth/provedores': { google: true } }))
    montar(<Entrar />, '/entrar?erro=Login%20com%20o%20Google%20cancelado.')
    expect(await screen.findByRole('link', { name: /Entrar com o Google/ })).toHaveAttribute('href', '/api/auth/google')
    expect(screen.getByRole('link', { name: 'Esqueci minha senha' })).toHaveAttribute('href', '/recuperar-senha')
    expect(screen.getByText('Login com o Google cancelado.')).toBeInTheDocument()
  })

  it('sem o Google configurado, não mostra o botão', async () => {
    const fetch = api({ '/auth/provedores': { google: false } })
    vi.stubGlobal('fetch', fetch)
    montar(<Entrar />)
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expect(screen.queryByRole('link', { name: /Google/ })).not.toBeInTheDocument()
  })
})

describe('Recuperar a senha', () => {
  it('pede o link e mostra a mesma mensagem sempre', async () => {
    const fetch = api({})
    vi.stubGlobal('fetch', fetch)
    montar(<RecuperarSenha />)
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    expect(fetch).toHaveBeenCalledWith('/api/auth/recuperar', expect.objectContaining({
      body: JSON.stringify({ email: 'ana@exemplo.com' }) }))
    expect(await screen.findByText(/Se houver uma conta com esse e-mail/)).toBeInTheDocument()
  })

  it('cria a senha nova pelo link e já entra', async () => {
    const fetch = api({ '/auth/redefinir': { access_token: 'novo-token' }, '/auth/eu': { id: 'u', nome: 'Ana' } })
    vi.stubGlobal('fetch', fetch)
    montar(<RedefinirSenha />, '/redefinir-senha?token=abc123')
    await userEvent.type(screen.getByLabelText('Nova senha'), 'senha-nova-1')
    await userEvent.type(screen.getByLabelText('Repita a senha'), 'senha-nova-2')
    expect(screen.getByText('As senhas não são iguais.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Salvar e entrar' })).toBeDisabled()
    await userEvent.clear(screen.getByLabelText('Repita a senha'))
    await userEvent.type(screen.getByLabelText('Repita a senha'), 'senha-nova-1')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar e entrar' }))
    expect(fetch).toHaveBeenCalledWith('/api/auth/redefinir', expect.objectContaining({
      body: JSON.stringify({ token: 'abc123', senha: 'senha-nova-1' }) }))
    expect(await screen.findByText('Lista de personagens')).toBeInTheDocument()
    expect(localStorage.getItem('ag.token')).toBe('novo-token')
  })
})

describe('Volta do Google', () => {
  it('guarda o token do fragmento e vai para o app', async () => {
    vi.stubGlobal('fetch', api({ '/auth/eu': { id: 'u', nome: 'Ana' } }))
    window.location.hash = '#token=token-do-google'
    montar(<EntrarComGoogle />, '/entrar/google')
    expect(await screen.findByText('Lista de personagens')).toBeInTheDocument()
    expect(localStorage.getItem('ag.token')).toBe('token-do-google')
  })
})
