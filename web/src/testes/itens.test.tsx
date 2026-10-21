import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Arma, Ficha, Inventario, ItemProprio, Loja, Mesa, Sessao } from '../api/tipos'
import AbaEquipamento from '../componentes/AbaEquipamento'
import InventarioNaMesa from '../componentes/inventario/InventarioNaMesa'
import { itemEmBranco, resumoDoItem } from '../lib/itens'
import AbaItens from '../paginas/mesa/AbaItens'
import Lojas from '../paginas/mesa/Lojas'

/** fetch falso: responde por caminho (sem o /api) e guarda as chamadas. */
function api(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string, _opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '').split('?')[0]
    const corpo = caminho in rotas ? rotas[caminho] : (caminho.startsWith('/srd/') ? [] : {})
    return new Response(JSON.stringify(corpo), { status: 200 })
  })
}

function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={cliente}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

afterEach(() => vi.unstubAllGlobals())

const LAMINA: ItemProprio = {
  ...itemEmBranco('ARMA'), id: 'i1', nome: 'Lâmina do Eclipse', traco: 'PRESENCE', dado: 'd10', modificador_dano: 2,
  caracteristicas: [{ nome: 'Sombria', descricao: '', modificadores: [{ alvo: 'EVASAO', valor: 1 }], requisitos: [], nome_original: '' }],
}

const corpoDe = (fetch: ReturnType<typeof api>, caminho: string, metodo = 'POST') => {
  const chamada = fetch.mock.calls.find(([u, o]) => u.startsWith(`/api${caminho}`) && o?.method === metodo)
  return chamada ? JSON.parse(chamada[1]!.body as string) : undefined
}

describe('Itens da mesa', () => {
  it('resumo de uma linha por tipo', () => {
    expect(resumoDoItem(LAMINA)).toBe('Principal · Presença · Corpo a corpo · d10+2 físico')
    expect(resumoDoItem({ ...itemEmBranco('CONSUMIVEL'), limpa_pv: '1d4', limpa_pf: '2', escolha: true }))
      .toBe('Ao usar: limpa 1d4 PV ou 2 PF.')
    expect(resumoDoItem({ ...itemEmBranco('ARMADURA'), pontuacao: 4 })).toBe('Pontuação 4 · Limiares base 5/11')
  })

  it('cria uma arma com dado, bônus de dano e uma característica com bônus', async () => {
    const fetch = api({ '/mesas/m1/itens': [], '/mesas/m1/itens/i1': { ...LAMINA, versao: 'v1' } })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaItens mesaId="m1" podeEditar />)
    await userEvent.click(await screen.findByRole('button', { name: 'Criar do zero' }))   // Arma é o tipo padrão
    await userEvent.type(screen.getByLabelText('Nome'), 'Lâmina do Eclipse')
    await userEvent.selectOptions(screen.getByLabelText('Dado de dano'), 'd10')
    await userEvent.clear(screen.getByLabelText('Bônus de dano'))
    await userEvent.type(screen.getByLabelText('Bônus de dano'), '2')
    await userEvent.click(screen.getByRole('button', { name: 'Criar característica' }))
    const carac = screen.getByRole('group', { name: 'Características' })
    await userEvent.type(within(carac).getByLabelText('Nome'), 'Sombria')
    await userEvent.click(within(carac).getByRole('button', { name: '+ Bônus na ficha' }))
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))
    const corpo = corpoDe(fetch, '/mesas/m1/itens')
    expect(corpo).toMatchObject({ tipo: 'ARMA', nome: 'Lâmina do Eclipse', dado: 'd10', modificador_dano: 2 })
    expect(corpo.caracteristicas).toEqual([expect.objectContaining({ nome: 'Sombria', modificadores: [{ alvo: 'EVASAO', valor: 1 }] })])
    expect(corpo).not.toHaveProperty('versao')
  })

  it('jogador não vê os botões de criar', async () => {
    vi.stubGlobal('fetch', api({ '/mesas/m1/itens': [LAMINA] }))
    montar(<AbaItens mesaId="m1" podeEditar={false} />)
    expect(await screen.findByText('Lâmina do Eclipse')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Criar do zero' })).not.toBeInTheDocument()
  })
})

describe('Entregar e equipar', () => {
  const INVENTARIO: Inventario = {
    ouro: { baus: 0, bolsas: 0, punhados: 0, total: 0, maximo: 199, moedas: 0 }, itens: [], livres: [], armas: [],
    experiencia_da_reliquia: null, usa_moedas: false, moedas_pela_mesa: false,
  }

  it('o mestre dá um item da mesa ao personagem', async () => {
    const fetch = api({ '/mesas/m1/personagens/p1/inventario': INVENTARIO, '/mesas/m1/itens': [LAMINA],
      '/mesas/m1/personagens/p1/inventario/da-mesa': INVENTARIO })
    vi.stubGlobal('fetch', fetch)
    montar(<InventarioNaMesa mesaId="m1" pid="p1" nome="Lira" podeDar />)
    await userEvent.click(screen.getByRole('button', { name: 'Inventário de Lira' }))
    await userEvent.click(await screen.findByText('Dar um item da mesa (criado pelos mestres)'))
    await userEvent.click(await screen.findByRole('button', { name: /Lâmina do Eclipse/ }))
    expect(corpoDe(fetch, '/mesas/m1/personagens/p1/inventario/da-mesa')).toEqual({ item_id: 'i1', quantidade: 1 })
  })

  it('a arma recebida aparece no equipamento, marcada como da mesa', async () => {
    const recebida: Arma = { id: 'proprio_abc', nome: 'Lâmina do Eclipse', nome_original: 'Lâmina do Eclipse',
      categoria: 'PRIMARY_PHYSICAL', tier: 1, traco: 'PRESENCE', alcance: 'MELEE', dado: 'd10', modificador_dano: 2,
      tipo_dano: 'PHYSICAL', duas_maos: false, caracteristicas: [] }
    const fetch = api({ '/personagens/p1/equipamento': { principal: null, secundaria: null, armadura: null, versao: 'v1',
      armas_proprias: [recebida], armaduras_proprias: [] } })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaEquipamento personagemId="p1" ficha={{ nivel: 1, conjuracoes: [] } as unknown as Ficha} />)
    const botao = await screen.findByRole('button', { name: /Lâmina do Eclipse/ })
    expect(within(botao).getByText('da mesa')).toBeInTheDocument()
    await userEvent.click(botao)
    await userEvent.click(screen.getByRole('button', { name: 'Salvar equipamento' }))
    // só o equipamento vai no corpo (as listas de recebidas não)
    expect(corpoDe(fetch, '/personagens/p1/equipamento', 'PUT')).toEqual({ principal: 'proprio_abc', secundaria: null, armadura: null,
      traco_principal: null, traco_secundaria: null })
  })
})

describe('Loja com item da mesa', () => {
  it('põe à venda pelo id do modelo e mostra o resumo', async () => {
    const mesa = { id: 'm1', minhas_permissoes: ['dar_itens'], personagens: [] } as unknown as Mesa
    const sessao = { id: 's1', sou_responsavel: true } as unknown as Sessao
    const loja: Loja = { id: 'l1', nome: 'Ferreiro', visivel: false, versao: 'v1', itens: [] }
    const fetch = api({ '/mesas/m1/sessoes/s1/lojas': [loja], '/mesas/m1/itens': [LAMINA], '/mesas/m1/sessoes/s1/lojas/l1': loja })
    vi.stubGlobal('fetch', fetch)
    montar(<Lojas mesa={mesa} sessao={sessao} />)
    await userEvent.click(await screen.findByRole('button', { name: /Ferreiro/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar itens' }))
    await userEvent.selectOptions(await screen.findByLabelText('Item da mesa (criado pelos mestres)'), 'i1')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar loja' }))
    expect(corpoDe(fetch, '/mesas/m1/sessoes/s1/lojas/l1', 'PUT').itens).toEqual([
      { id: '', tipo: 'PROPRIO', ref: 'i1', nome: '', descricao: '', preco: 1, moedas: 0, estoque: null }])
  })
})
