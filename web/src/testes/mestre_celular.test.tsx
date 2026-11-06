import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ProvedorAutenticacao } from '../auth/Autenticacao'
import Mesa from '../paginas/Mesa'

vi.mock('../componentes/Dados3D', () => ({ default: () => null }))

const MESA = {
  id: 'm1', nome: 'Sombras de Haven', codigo_convite: 'ABC123', nivel_maximo: 1, usar_moedas: false, meu_papel: 'mestre', sou_criador: true,
  medo_em_jogo: [], permissoes_mestres: { ver_fichas: true, aplicar_dano: true, aplicar_condicoes: true, preparar: true },
  minhas_permissoes: ['ver_fichas', 'aplicar_dano', 'aplicar_condicoes', 'preparar'],
  membros: [{ usuario_id: 'u1', nome: 'Ana', papel: 'mestre', criador: true, online: true }], personagens: [],
}
const base = '/mesas/m1/sessoes/s1'
const FICHA = {
  nome: 'Lira', evasao: 10, limiar_maior: 3, limiar_grave: 6, pv_max: 6, pv_marcados: 1, estresse_max: 6, estresse_marcado: 0,
  pontuacao_armadura: 0, armadura_marcada: 0, esperanca: 2, esperanca_max: 6, condicoes: ['VULNERAVEL'], cicatrizes: [], defesas_de_carta: [],
}

function rotas(status: string, extra: Record<string, unknown> = {}, gerir = true) {
  const resumo = { id: 's1', titulo: 'A ponte', data: null, status, medo: 3, responsavel_id: 'u1', responsavel: 'Ana',
    sou_responsavel: gerir, posso_gerir: gerir, participantes: 1 }
  const outra = { ...resumo, id: 's2', titulo: 'A torre', status: 'planejada' }
  const completa = { ...resumo, resumo: '', notas: '', compartilhada_com: [], npcs: [], inimigos: [], encontros: [] }
  return {
    '/mesas/m1': MESA, '/mesas/m1/sessoes': [outra, resumo], [base]: completa, '/mesas/m1/sessoes/s2': { ...completa, ...outra },
    [`${base}/jogo`]: { participantes: [{ personagem_id: 'p1', resumo: { nome: 'Lira', jogador: 'Bia', foto: null } }] },
    [`${base}/rolagens`]: [], [`${base}/repouso`]: null, [`${base}/medo`]: { ...completa, medo: 4 },
    '/mesas/m1/personagens/p1': FICHA, '/mesas/m1/npcs': [], '/mesas/m1/inimigos': [], ...extra,
  }
}

function montar(respostas: Record<string, unknown>) {
  const fetch = vi.fn(async (url: string, _opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    if (!(caminho in respostas)) return new Response(JSON.stringify({ detail: 'não achei' }), { status: 404 })
    return new Response(JSON.stringify(respostas[caminho]), { status: 200 })
  })
  vi.stubGlobal('fetch', fetch)
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao>
        <MemoryRouter initialEntries={['/mesas/m1?aba=sessao&sessao=s1']}>
          <Routes><Route path="/mesas/:id" element={<Mesa />} /></Routes>
        </MemoryRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>,
  )
  return fetch
}

const depois = (a: Element, b: Element) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_PRECEDING)

beforeEach(() => {
  vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: () => {}, removeEventListener: () => {} }))
})
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear() })

describe('Sessão do mestre no celular', () => {
  it('a lista de sessões fica recolhida; ao escolher outra, recolhe de novo', async () => {
    montar(rotas('em_andamento'))
    await screen.findByRole('tab', { name: 'Ao vivo' })
    const lista = screen.getByText('Outras sessões (2) ou nova sessão')
    const outra = screen.getByRole('button', { name: /A torre/ })
    expect(outra).not.toBeVisible()
    await userEvent.click(lista)
    expect(outra).toBeVisible()
    await userEvent.click(outra)
    expect(lista.closest('details')).not.toHaveAttribute('open')
  })

  it('em andamento: Medo fixo, com os botões de mudar, sem o painel grande', async () => {
    const fetch = montar(rotas('em_andamento'))
    const medo = await screen.findByRole('group', { name: 'Medo da sessão' })
    expect(medo).toHaveAttribute('data-marcas-fixas')
    expect(screen.queryByRole('region', { name: 'Medo da sessão' })).not.toBeInTheDocument()
    await userEvent.click(within(medo).getByRole('button', { name: 'Ganhar 1 de Medo' }))
    expect(fetch).toHaveBeenCalledWith(`/api${base}/medo`, expect.objectContaining({ body: JSON.stringify({ delta: 1 }) }))
  })

  it('quem recebeu a sessão compartilhada vê o Medo fixo, sem os botões', async () => {
    const respostas = rotas('em_andamento')
    const so = (s: object) => ({ ...s, sou_responsavel: false })
    montar({ ...respostas, [base]: so(respostas[base] as object),
      '/mesas/m1/sessoes': (respostas['/mesas/m1/sessoes'] as object[]).map(so) })
    await screen.findByRole('group', { name: 'Medo da sessão' })
    expect(screen.queryByRole('button', { name: 'Ganhar 1 de Medo' })).not.toBeInTheDocument()
  })

  it('planejada: sem Medo fixo, o painel grande continua, depois das abas', async () => {
    montar(rotas('planejada'))
    const abas = await screen.findByRole('tab', { name: 'Planejamento' })
    const painel = screen.getByRole('region', { name: 'Medo da sessão' })
    expect(depois(painel, abas)).toBe(true)
    expect(screen.queryByRole('button', { name: 'Ganhar 1 de Medo' })).not.toBeInTheDocument()
  })

  it('apagar a sessão fica no fim, longe de encerrar', async () => {
    montar(rotas('em_andamento'))
    const encerrar = await screen.findByRole('button', { name: 'Encerrar sessão' })
    const abas = screen.getByRole('tab', { name: 'Ao vivo' })
    const apagar = screen.getByRole('button', { name: 'Apagar sessão' })
    expect(depois(abas, encerrar)).toBe(true)
    expect(depois(apagar, abas)).toBe(true)
  })

  it('repouso aberto sobe para antes das abas; fechado, fica depois', async () => {
    const aberto = { id: 'r1', status: 'aberto', tipo: 'curto', participantes: [], resultado: null }
    montar(rotas('em_andamento', { [`${base}/repouso`]: aberto }))
    const abas = await screen.findByRole('tab', { name: 'Ao vivo' })
    const encerrar = await screen.findByRole('button', { name: /Encerrar o|Encerrar repouso|Encerrar descanso/ })
    expect(depois(abas, encerrar)).toBe(true)
  })

  it('ao vivo: marcas e condições à vista, ações recolhidas', async () => {
    montar(rotas('em_andamento'))
    const cartao = await screen.findByRole('article', { name: 'Lira' })
    expect(within(cartao).getByRole('img', { name: /PV de Lira/ })).toBeVisible()
    expect(within(cartao).getByRole('list', { name: 'Condições de Lira' })).toHaveTextContent('Vulnerável')
    const aplicar = within(cartao).getByRole('button', { name: 'Aplicar dano' })
    const tirar = within(cartao).getByRole('button', { name: 'Tirar da sessão' })
    expect(aplicar).not.toBeVisible()
    await userEvent.click(within(cartao).getByText('Dano, condições e itens'))
    expect(aplicar).toBeVisible()
    expect(tirar).toBeVisible()
    // a lista de condições não se repete dentro das ações
    expect(within(cartao).getAllByRole('list', { name: 'Condições de Lira' })).toHaveLength(1)
  })

  it('a lista não recolhe para quem joga a sessão', async () => {
    montar(rotas('em_andamento', {}, false))
    await screen.findByRole('button', { name: /A torre/ })
    expect(screen.queryByText(/Outras sessões/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /A torre/ })).toBeVisible()
  })
})
