import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Ficha, Mesa, Repouso, Sessao } from '../api/tipos'
import { ProvedorAutenticacao } from '../auth/Autenticacao'
import Morte from '../componentes/Morte'
import PainelDeRepouso from '../componentes/Repouso'
import PersonagensNaSessao from '../paginas/mesa/PersonagensNaSessao'

function api(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string, _opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    return new Response(JSON.stringify(caminho in rotas ? rotas[caminho] : {}), { status: 200 })
  })
}

function montar(ui: ReactNode) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao><MemoryRouter>{ui}</MemoryRouter></ProvedorAutenticacao>
    </QueryClientProvider>,
  )
}

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

const mesa = { id: 'm1', minhas_permissoes: [], personagens: [] } as unknown as Mesa
const jogador = { id: 's1', sou_responsavel: false }   // a sessão vista por quem joga
const repouso = (extra: Partial<Repouso> = {}): Repouso => ({
  id: 'r1', sessao_id: 's1', tipo: 'curto', status: 'aberto', mestre: 'Ana', sou_responsavel: false,
  participantes: [
    { id: 'lira', nome: 'Lira', jogador: 'Bia', dono_id: 'bia', pronto: false, escolha: null },
    { id: 'bruno', nome: 'Bruno', jogador: 'Carlos', dono_id: 'carlos', pronto: true,
      escolha: { movimentos: [{ movimento: 'PREPARAR', alvo: null, rolagem: null }, { movimento: 'PREPARAR', alvo: null, rolagem: null }] } },
  ],
  resultado: null, medo_ganho: null, ...extra,
})

describe('Repouso', () => {
  it('o jogador escolhe Tratar Feridas num aliado, com o d4 da mesa, e confirma', async () => {
    localStorage.setItem('ag.token', 'x')
    const fetch = api({ '/auth/eu': { id: 'bia', nome: 'Bia' }, '/mesas/m1/sessoes/s1/repouso': repouso(),
      '/mesas/m1/repouso/r1/escolhas/lira': repouso() })
    vi.stubGlobal('fetch', fetch)
    montar(<PainelDeRepouso mesa={mesa} sessao={jogador} />)

    expect(await screen.findByText(/Ana abriu um descanso curto/)).toBeInTheDocument()
    expect(screen.getByText('Preparar-se · Preparar-se')).toBeInTheDocument()   // a escolha do Bruno
    await userEvent.selectOptions(await screen.findByLabelText('Em quem (movimento 1)'), 'bruno')
    await userEvent.type(screen.getByLabelText('d4 do movimento 1 (vazio: o app rola)'), '3')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar movimentos' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/repouso/r1/escolhas/lira', expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ movimentos: [
        { movimento: 'CUIDAR_FERIDAS', alvo: 'bruno', rolagem: 3 }, { movimento: 'PREPARAR', alvo: null, rolagem: null }] }),
    }))
  })

  it('o mestre abre e só encerra com todos prontos', async () => {
    const sessao = { id: 's1', sou_responsavel: true } as unknown as Sessao
    let aberto: Repouso | null = null   // como a API: depois de abrir, o GET devolve o repouso aberto
    const fetch = vi.fn(async (url: string, opcoes?: RequestInit) => {
      if (opcoes?.method === 'POST') aberto = repouso({ sou_responsavel: true })
      return new Response(JSON.stringify(url.endsWith('/repouso') && opcoes?.method !== 'POST' ? aberto : aberto ?? {}),
        { status: 200 })
    })
    vi.stubGlobal('fetch', fetch)
    montar(<PainelDeRepouso mesa={mesa} sessao={sessao} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Descanso curto' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/sessoes/s1/repouso', expect.objectContaining({
      body: JSON.stringify({ tipo: 'curto', participantes: null }) }))
    expect(await screen.findByRole('button', { name: 'Encerrar repouso' })).toBeDisabled()   // a Lira ainda escolhe
  })

  it('depois de encerrado, mostra o que cada um recuperou e o Medo do mestre', async () => {
    vi.stubGlobal('fetch', api({ '/mesas/m1/sessoes/s1/repouso': repouso({ status: 'concluido', medo_ganho: 3, resultado: {
      tipo: 'curto', notas: [], por_personagem: {
        lira: [{ movimento: 'CUIDAR_FERIDAS', rolagem: 3, recuperado: 2, alvo: 'Bruno' }],
      } } }) }))
    montar(<PainelDeRepouso mesa={mesa} sessao={jogador} />)
    expect(await screen.findByText(/Tratar Feridas em Bruno \(d4 3: 2 limpos\)/)).toBeInTheDocument()
    expect(screen.getByText('O mestre ganhou 3 de Medo.')).toBeInTheDocument()
  })
})

describe('Movimento de morte', () => {
  const ficha = { nome: 'Lira', pv_marcados: 5, pv_max: 5, precisa_movimento_de_morte: true, morto: false,
    inconsciente: false, cicatrizes: [] } as unknown as Ficha

  it('Arriscar Tudo com os dados da mesa e a divisão entre PV e PF', async () => {
    const fetch = api({ '/personagens/p1/sessao/morte': { resultado: { movimento: 'ARRISCAR_TUDO', morreu: false,
      notas: ['A Esperança venceu.'] }, ficha: { ...ficha, precisa_movimento_de_morte: false } } })
    vi.stubGlobal('fetch', fetch)
    montar(<Morte personagemId="p1" ficha={ficha} />)
    await userEvent.click(screen.getByRole('button', { name: /Arriscar Tudo/ }))
    await userEvent.type(screen.getByLabelText('Dado de Esperança (d12)'), '8')
    await userEvent.type(screen.getByLabelText('Dado de Medo (d12)'), '3')
    fireEvent.change(screen.getByLabelText('Quanto vai para PV'), { target: { value: '6' } })
    expect(screen.getByText(/6 PV/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/sessao/morte', expect.objectContaining({
      body: JSON.stringify({ movimento: 'ARRISCAR_TUDO', rolagem_esperanca: 8, rolagem_medo: 3, pv: 6 }) }))
    expect(await screen.findByText(/A Esperança venceu/)).toBeInTheDocument()
  })

  it('morto e cicatrizes aparecem na ficha', () => {
    vi.stubGlobal('fetch', api({}))
    montar(<Morte personagemId="p1" ficha={{ ...ficha, precisa_movimento_de_morte: false, morto: true,
      cicatrizes: [{ impacto: 'MEDO', descricao: 'Água funda' }] } as unknown as Ficha} />)
    expect(screen.getByText(/atravessou o véu da morte/)).toBeInTheDocument()
    expect(screen.getByLabelText('Impacto da cicatriz 1')).toHaveValue('MEDO')
  })
})

describe('Cartas no dano e na morte', () => {
  it('no movimento de morte, oferece a carta que vai no lugar', async () => {
    const ficha = { nome: 'Bram', pv_marcados: 6, pv_max: 6, precisa_movimento_de_morte: true, morto: false,
      inconsciente: false, cicatrizes: [], alternativas_a_morte: ['bh'] } as unknown as Ficha
    const fetch = api({
      '/srd/cartas': [{ id: 'bh', nome: 'Calejado pela Batalha', texto: '' }],
      '/personagens/p1/sessao/morte/carta': { notas: ['Calejado pela Batalha: limpou 1 PV.'],
        ficha: { ...ficha, precisa_movimento_de_morte: false, pv_marcados: 5 } },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<Morte personagemId="p1" ficha={ficha} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Calejado pela Batalha' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/sessao/morte/carta', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ carta: 'bh' }) }))
    expect(await screen.findByText('Calejado pela Batalha: limpou 1 PV.')).toBeInTheDocument()
  })

  it('o mestre marca a carta de defesa que o jogador usa no dano', async () => {
    const mesa = { id: 'm1', minhas_permissoes: ['ver_fichas', 'aplicar_dano'] } as unknown as Mesa
    const sessao = { id: 's1', status: 'em_andamento', sou_responsavel: false } as unknown as Sessao
    const ficha = { nome: 'Bram', pv_max: 6, pv_marcados: 0, estresse_max: 6, estresse_marcado: 0, esperanca: 2,
      esperanca_max: 6, pontuacao_armadura: 0, armadura_marcada: 0, evasao: 9, limiar_maior: 1, limiar_grave: 2,
      condicoes: [], cicatrizes: [], defesas_de_carta: [{ carta: 'gbu', nome: 'Levantar', custo_esperanca: 0, custo_fadiga: 1 }] }
    const fetch = api({
      '/mesas/m1/sessoes/s1/jogo': { participantes: [{ personagem_id: 'p1', resumo: { nome: 'Bram', jogador: 'Bia', foto: null } }] },
      '/mesas/m1/personagens/p1': ficha,
      '/mesas/m1/personagens/p1/dano': { ficha, resultado: { dano: 30, gravidade: 'GRAVE', pv_marcados: 2, usou_armadura: false,
        caiu: false, espacos_marcados: 0, estresse_marcado: 1, notas: ['Levantar: marcou 1 PF e reduziu um nível'] } },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<PersonagensNaSessao mesa={mesa} sessao={sessao} />)
    await userEvent.type(await screen.findByLabelText('Dano em Bram'), '30')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Levantar (marca 1 PF)' }))
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar dano' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/personagens/p1/dano', expect.objectContaining({
      body: JSON.stringify({ dano: 30, usar_armadura: false, cartas: ['gbu'] }) }))
    expect(await screen.findByText(/reduziu um nível/)).toBeInTheDocument()
  })
})
