import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { EventoLinhaDoTempo } from '../api/tipos'
import { ProvedorAutenticacao } from '../auth/Autenticacao'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import { Espacos } from '../componentes/ui'
import { Entrar } from '../paginas/Acesso'

function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao><MemoryRouter>{ui}</MemoryRouter></ProvedorAutenticacao>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('Entrar', () => {
  it('mostra a mensagem da API quando o login falha', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'E-mail ou senha incorretos.' }), { status: 401 })))
    montar(<Entrar />)
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'errada123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos.')
  })
})

describe('Linha do tempo', () => {
  const eventos: EventoLinhaDoTempo[] = [
    { nivel: 1, tier: 1, status: 'feito', titulo: 'Criação', itens: ['Classe: Bard'] },
    { nivel: 2, tier: 2, status: 'feito', titulo: 'Nível 2', itens: ['Avanço: PV'] },
    { nivel: 3, tier: 2, status: 'futuro', titulo: 'Nível 3', itens: ['Escolher 2 avanços'] },
    { nivel: 4, tier: 2, status: 'futuro', titulo: 'Nível 4', itens: ['Escolher 2 avanços'] },
  ]

  it('oferece subir só para o próximo nível e desfazer só o último feito', async () => {
    const desfazer = vi.fn()
    montar(<LinhaDoTempo eventos={eventos} personagemId="p1" aoDesfazer={desfazer} desfazendo={false} />)
    const subir = screen.getByRole('link', { name: 'Subir para o nível 3' })
    expect(subir).toHaveAttribute('href', '/personagens/p1/subir')
    expect(screen.queryByText('Subir para o nível 4')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Desfazer este nível' }))
    expect(desfazer).toHaveBeenCalledOnce()
    expect(screen.getAllByRole('button', { name: 'Desfazer este nível' })).toHaveLength(1)
  })
})

describe('Espaços', () => {
  it('descreve os marcados para leitores de tela', () => {
    render(<Espacos total={6} marcados={2} rotulo="Estresse" />)
    expect(screen.getByRole('img', { name: 'Estresse: 2 de 6 marcados' })).toBeInTheDocument()
  })
})
