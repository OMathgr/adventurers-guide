import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Mesa, Sessao } from '../api/tipos'
import QuadroDaCampanha from '../componentes/QuadroDaCampanha'
import QuadroDaSessao from '../paginas/mesa/QuadroDaSessao'

function api(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string, opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    // salvar o quadro devolve o que foi enviado, com os itens vazios
    if (opcoes?.method === 'PUT' && caminho.endsWith('/quadro')) {
      return new Response(JSON.stringify({ ...JSON.parse(String(opcoes.body)), itens: {} }), { status: 200 })
    }
    return new Response(JSON.stringify(rotas[caminho] ?? []), { status: 200 })
  })
}

function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>)
}

afterEach(() => vi.unstubAllGlobals())

const mesa = { id: 'm1', personagens: [] } as unknown as Mesa
const sessao = (minha: boolean) => ({ id: 's1', sou_responsavel: minha, encontros: [] }) as unknown as Sessao

describe('Quadro da sessão', () => {
  it('criar uma nota, revelar e salvar sozinho', async () => {
    const fetch = api({ '/mesas/m1/sessoes/s1/quadro': { cartoes: [], ligacoes: [], itens: {} } })
    vi.stubGlobal('fetch', fetch)
    montar(<QuadroDaSessao mesa={mesa} sessao={sessao(true)} />)

    await userEvent.click(await screen.findByRole('button', { name: '+ Nota' }))
    // a nota nova já vem selecionada: o painel abre para editar
    const titulo = screen.getByLabelText('Título')
    await userEvent.clear(titulo)
    await userEvent.type(titulo, 'A ponte')
    await userEvent.click(screen.getByLabelText('Mostrar aos jogadores'))

    await waitFor(() => {
      const puts = fetch.mock.calls.filter(([, o]) => o?.method === 'PUT')
      expect(puts.length).toBeGreaterThan(0)
      const corpo = JSON.parse(String(puts.at(-1)![1]!.body))
      expect(corpo.cartoes).toEqual([expect.objectContaining({ tipo: 'nota', titulo: 'A ponte', revelado: true })])
    }, { timeout: 3000 })
    expect(await screen.findByText('Tudo salvo')).toBeInTheDocument()
  })

  it('sessão de outro mestre: só leitura', async () => {
    vi.stubGlobal('fetch', api({ '/mesas/m1/sessoes/s1/quadro': {
      cartoes: [{ id: 'a', tipo: 'nota', x: 0, y: 0, titulo: 'Pista', texto: 'O selo é falso', cor: 'padrao', revelado: false }],
      ligacoes: [], itens: {} } }))
    montar(<QuadroDaSessao mesa={mesa} sessao={sessao(false)} />)
    expect(await screen.findByText('Pista')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Nota' })).not.toBeInTheDocument()
    expect(screen.getByText(/só leitura/)).toBeInTheDocument()
  })
})

describe('Quadro da campanha', () => {
  it('mostra o revelado de cada sessão com o título da região', async () => {
    vi.stubGlobal('fetch', api({ '/mesas/m1/quadro-da-campanha': [{
      sessao_id: 's1', titulo: 'A ponte', ligacoes: [],
      cartoes: [{ id: 'b', tipo: 'item', x: 0, y: 0, titulo: '', texto: '', cor: 'padrao', revelado: true,
        item_tipo: 'npc', item_id: 'n1' }],
      itens: { 'npc:n1': { nome: 'Marlowe', foto: null, descricao: 'Ferreiro', existe: true } },
    }] }))
    montar(<QuadroDaCampanha mesaId="m1" />)
    expect(await screen.findByText('A ponte')).toBeInTheDocument()
    expect(screen.getByText('Marlowe')).toBeInTheDocument()
  })

  it('sem nada revelado avisa', async () => {
    vi.stubGlobal('fetch', api({ '/mesas/m1/quadro-da-campanha': [] }))
    montar(<QuadroDaCampanha mesaId="m1" />)
    expect(await screen.findByText(/Nada revelado ainda/)).toBeInTheDocument()
  })
})
