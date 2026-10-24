import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Navigate, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProvedorAutenticacao, useAutenticacao } from '../auth/Autenticacao'
import { Entrar, EntrarComGoogle, RecuperarSenha, RedefinirSenha } from '../paginas/Acesso'
import Conta from '../paginas/Conta'

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

describe('Sessão por uso', () => {
  const jwt = (emitidoMs: number, validadeMs = 2 * 3_600_000) => {
    const corpo = btoa(JSON.stringify({ sub: 'u', iat: emitidoMs / 1000, exp: (emitidoMs + validadeMs) / 1000 }))
    return `x.${corpo.replace(/=+$/, '')}.y`
  }

  it('usar o app com o token já com uns minutos renova o login em silêncio', async () => {
    localStorage.setItem('ag.token', jwt(Date.now() - 10 * 60_000))
    const fetch = api({ '/auth/renovar': { access_token: 'renovado' }, '/auth/eu': { id: 'u', nome: 'Ana' } })
    vi.stubGlobal('fetch', fetch)
    montar(<p>App</p>, '/')
    await userEvent.click(screen.getByText('App'))
    await waitFor(() => expect(localStorage.getItem('ag.token')).toBe('renovado'))
    expect(fetch).toHaveBeenCalledWith('/api/auth/renovar', expect.objectContaining({ method: 'POST' }))
  })

  it('com o token vencido (ficou parado), sai e explica o motivo', async () => {
    localStorage.setItem('ag.token', jwt(Date.now() - 3 * 3_600_000))
    vi.stubGlobal('fetch', api({ '/auth/eu': { id: 'u', nome: 'Ana' }, '/auth/provedores': { google: false } }))
    // como no app: página de logado; ao sair, vai para /entrar (que monta de novo)
    function SoLogado() {
      const { logado } = useAutenticacao()
      return logado ? <p>App</p> : <Navigate to="/entrar" replace />
    }
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={cliente}>
        <ProvedorAutenticacao>
          <MemoryRouter initialEntries={['/']}>
            <Routes>
              <Route path="/" element={<SoLogado />} />
              <Route path="/entrar" element={<Entrar />} />
            </Routes>
          </MemoryRouter>
        </ProvedorAutenticacao>
      </QueryClientProvider>,
    )
    // já ao abrir: nem precisa de clique
    expect(await screen.findByText('Você ficou 2 horas sem usar o app. Entre de novo.')).toBeInTheDocument()
    expect(localStorage.getItem('ag.token')).toBeNull()
  })
})

describe('Aviso antes de cair', () => {
  const jwt = (emitidoMs: number, validadeMs = 2 * 3_600_000) => {
    const corpo = btoa(JSON.stringify({ sub: 'u', iat: emitidoMs / 1000, exp: (emitidoMs + validadeMs) / 1000 }))
    return `x.${corpo.replace(/=+$/, '')}.y`
  }

  it('faltando menos de 10 minutos mostra a contagem; continuar renova e o aviso some', async () => {
    // token vence em 5 minutos e a renovação está falhando (ex.: rede caiu)
    localStorage.setItem('ag.token', jwt(Date.now() - 115 * 60_000))
    let renovacaoFunciona = false
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url === '/api/auth/renovar') {
        return renovacaoFunciona
          ? new Response(JSON.stringify({ access_token: jwt(Date.now()) }), { status: 200 })
          : new Response('{}', { status: 503 })
      }
      return new Response(JSON.stringify({ id: 'u', nome: 'Ana' }), { status: 200 })
    }))
    montar(<p>App</p>, '/')
    const aviso = await screen.findByRole('alert')
    expect(aviso).toHaveTextContent(/Por segurança, vamos desconectar em (5:00|4:5\d)/)

    renovacaoFunciona = true
    await userEvent.click(screen.getByRole('button', { name: 'Continuar conectado' }))
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument(), { timeout: 3000 })
  })
})

describe('Excluir conta', () => {
  it('só libera com o e-mail digitado e depois sai', async () => {
    localStorage.setItem('ag.token', 'token-da-ana')
    const fetch = api({ '/auth/eu': { id: 'u', nome: 'Ana', email: 'ana@exemplo.com', google: false, tem_senha: true },
      '/auth/provedores': { google: false } })
    vi.stubGlobal('fetch', fetch)
    montar(<Conta />, '/conta')
    const botao = await screen.findByRole('button', { name: 'Excluir minha conta' })
    expect(botao).toBeDisabled()
    await userEvent.type(screen.getByLabelText('E-mail para confirmar a exclusão'), 'outro@exemplo.com')
    expect(botao).toBeDisabled()
    await userEvent.clear(screen.getByLabelText('E-mail para confirmar a exclusão'))
    await userEvent.type(screen.getByLabelText('E-mail para confirmar a exclusão'), 'ANA@exemplo.com')
    await userEvent.click(botao)
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/auth/eu', expect.objectContaining({
      method: 'DELETE', body: JSON.stringify({ email: 'ANA@exemplo.com' }) })))
    await waitFor(() => expect(localStorage.getItem('ag.token')).toBeNull())
  })
})
