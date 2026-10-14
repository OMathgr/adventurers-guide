import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Ficha, Inventario, Loja, Mesa, Sessao, VistaDosJogadores as Vista } from '../api/tipos'
import AbaInventario from '../componentes/inventario/AbaInventario'
import VistaDosJogadores from '../componentes/VistaDosJogadores'
import Lojas from '../paginas/mesa/Lojas'

/** fetch falso: responde por caminho (sem o /api) e guarda as chamadas. */
function api(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string, _opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    const corpo = caminho in rotas ? rotas[caminho] : (caminho.startsWith('/srd/') ? [] : {})
    return new Response(JSON.stringify(corpo), { status: 200 })
  })
}

function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={cliente}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

afterEach(() => vi.unstubAllGlobals())

const ouro = (total: number) => ({ baus: Math.floor(total / 100), bolsas: Math.floor((total % 100) / 10),
  punhados: total % 10, total, maximo: 199, moedas: 0 })

const INVENTARIO: Inventario = {
  ouro: ouro(12),
  itens: [{ id: 'pocao', nome: 'Poção de Vida', nome_original: 'Health Potion', tipo: 'CONSUMIVEL',
    texto: 'Limpe 1d4+1 PV.', quantidade: 2, efeito_automatico: true, dado: '1d4+1', escolha: false, reliquia: null },
  { id: 'tocha', nome: 'Tocha', nome_original: 'Torch', tipo: 'COMUM', texto: '', quantidade: 1,
    efeito_automatico: false, dado: null, escolha: false, reliquia: null }],
  livres: [], armas: [], experiencia_da_reliquia: null, usa_moedas: false, moedas_pela_mesa: false,
}

describe('Inventário', () => {
  it('mostra o ouro e usa um consumível com o dado rolado na mesa', async () => {
    const fetch = api({
      '/personagens/p1/inventario': INVENTARIO,
      '/personagens/p1/inventario/itens/pocao/usar': {
        notas: ['Usou Poção de Vida.', 'Rolagem: 1d4+1 = 4.', 'Limpou 4 PV.'], inventario: INVENTARIO, ficha: {},
      },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaInventario personagemId="p1" ficha={{ experiencias: {} } as unknown as Ficha} />)

    expect(await screen.findByLabelText('Ouro: 1 bolsa e 2 punhados')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Usar…' }))
    await userEvent.type(screen.getByLabelText('Resultado do dado de Poção de Vida'), '3')
    await userEvent.click(screen.getByRole('button', { name: 'Usar' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/inventario/itens/pocao/usar', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ rolagem: 3, escolha: null }) }))
    expect(await screen.findByText(/Limpou 4 PV\./)).toBeInTheDocument()
  })

  it('ganhar ouro manda o valor em punhados', async () => {
    const fetch = api({ '/personagens/p1/inventario': INVENTARIO, '/personagens/p1/inventario/ouro': INVENTARIO })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaInventario personagemId="p1" ficha={{ experiencias: {} } as unknown as Ficha} />)

    await userEvent.clear(await screen.findByLabelText('Quantidade'))
    await userEvent.type(screen.getByLabelText('Quantidade'), '2')
    await userEvent.selectOptions(screen.getByLabelText('De'), 'bolsas')
    await userEvent.click(screen.getByRole('button', { name: 'Ganhar' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/inventario/ouro', expect.objectContaining({
      body: JSON.stringify({ punhados: 20, moedas: 0 }) }))
  })

  it('com a regra das moedas, mostra a linha de moedas e manda punhados e moedas', async () => {
    const comMoedas = { ...INVENTARIO, ouro: { ...ouro(2), moedas: 5 }, usa_moedas: true, moedas_pela_mesa: true }
    const fetch = api({ '/personagens/p1/inventario': comMoedas, '/personagens/p1/inventario/ouro': comMoedas })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaInventario personagemId="p1" ficha={{ experiencias: {} } as unknown as Ficha} />)

    expect(await screen.findByLabelText('Ouro: 2 punhados e 5 moedas')).toBeInTheDocument()
    expect(screen.getByText('A mesa usa a regra opcional das moedas.')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Quantidade'))
    await userEvent.type(screen.getByLabelText('Quantidade'), '15')
    await userEvent.selectOptions(screen.getByLabelText('De'), 'moedas')
    await userEvent.click(screen.getByRole('button', { name: 'Gastar' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/inventario/ouro', expect.objectContaining({
      body: JSON.stringify({ punhados: -1, moedas: -5 }) }))
  })
})

describe('Lojas', () => {
  const mesa = {
    id: 'm1', minhas_permissoes: ['dar_itens'],
    personagens: [{ id: 'lira', nome: 'Lira', jogador: 'Bia' }],
  } as unknown as Mesa
  const sessao = { id: 's1', sou_responsavel: true } as unknown as Sessao
  const loja: Loja = { id: 'l1', nome: 'Boticário', visivel: false, versao: 'v1', itens: [
    { id: 'i1', tipo: 'ITEM', ref: 'pocao', nome: 'Poção de Vida', texto: 'Limpe 1d4+1 PV.', preco: ouro(3), estoque: 2 },
  ] }

  it('muda o preço, salva e vende para um personagem', async () => {
    const fetch = api({
      '/mesas/m1/sessoes/s1/lojas': [loja],
      '/mesas/m1/sessoes/s1/lojas/l1?versao=v1': loja,   // salva mandando a versão que carregou
      '/mesas/m1/sessoes/s1/lojas/l1/vender': { notas: ['Comprou 1× Poção de Vida (3 punhados).'], loja, inventario: INVENTARIO },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<Lojas mesa={mesa} sessao={sessao} />)

    await userEvent.click(await screen.findByRole('button', { name: /Boticário/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Vender' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/sessoes/s1/lojas/l1/vender', expect.objectContaining({
      body: JSON.stringify({ item_id: 'i1', personagem_id: 'lira', quantidade: 1 }) }))
    expect(await screen.findByText('Comprou 1× Poção de Vida (3 punhados).')).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText('Preço de Poção de Vida'))
    await userEvent.type(screen.getByLabelText('Preço de Poção de Vida'), '15')
    expect(screen.getByText('Salve a loja para vender.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Salvar loja' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/sessoes/s1/lojas/l1?versao=v1', expect.objectContaining({
      method: 'PUT',
      body: JSON.stringify({ nome: 'Boticário', visivel: false, itens: [
        { id: 'i1', tipo: 'ITEM', ref: 'pocao', preco: 15, moedas: 0, estoque: 2, nome: '', descricao: '' }] }),
    }))
  })
})

describe('Loja à mostra para os jogadores', () => {
  it('mostra preço e estoque, sem botão de compra', async () => {
    const vista: Vista = { combate: [], npcs: [], lojas: [{ id: 'l1', nome: 'Ferreiro', mestre: 'Ana', itens: [
      { id: 'i1', tipo: 'ARMA', ref: 'adaga', nome: 'Adaga', texto: '', preco: ouro(25), estoque: 0 },
      { id: 'i2', tipo: 'LIVRE', ref: null, nome: 'Mapa', texto: 'A carvão', preco: ouro(0), estoque: null },
    ] }] }
    vi.stubGlobal('fetch', api({ '/mesas/m1/revelado': vista }))
    montar(<VistaDosJogadores mesaId="m1" />)
    expect(await screen.findByText('Loja: Ferreiro')).toBeInTheDocument()
    expect(screen.getByText('2 bolsas e 5 punhados')).toBeInTheDocument()
    expect(screen.getByText('Esgotado')).toBeInTheDocument()
    expect(screen.getByText('de graça')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
