import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ReactNode, useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Adversario, Mesa as MesaT } from '../api/tipos'
import EditorInimigo from '../componentes/EditorInimigo'
import { INIMIGO_EM_BRANCO } from '../lib/inimigo'
import FichaInimigo from '../componentes/FichaInimigo'
import Mesa from '../paginas/Mesa'

const MAGO: Adversario = {
  ...INIMIGO_EM_BRANCO,
  id: 'x', nome: 'Mago de Batalha', nome_original: 'War Wizard', patamar: 2, tipo: 'ATIRADOR',
  dificuldade: 16, limiar_maior: 11, limiar_grave: 23, pv: 5, pf: 6, ataque: '+4',
  arma: 'Cajado', arma_original: 'Staff', alcance: 'FAR', dano: '2d10+4', tipo_dano: 'MAGICAL',
  experiencias: { 'Conhecimento Mágico': 2 },
  habilidades: [{ nome: 'Erupção', tipo: 'ACAO', texto: '**Gaste 1 Ponto de Medo** para escolher um ponto.', detalhe: '', nome_original: 'Eruption' }],
}

function respostas(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string) => {
    const caminho = url.replace(/^\/api/, '')
    if (!(caminho in rotas)) return new Response(JSON.stringify({ detail: 'não achei' }), { status: 404 })
    return new Response(JSON.stringify(rotas[caminho]), { status: 200 })
  })
}

function montarEm(caminho: string, ui: ReactNode, rota: string) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[caminho]}><Routes><Route path={rota} element={ui} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('Ficha do inimigo', () => {
  it('mostra os números no formato do SRD', () => {
    render(<FichaInimigo adversario={MAGO} />)
    expect(screen.getByRole('heading', { name: /Mago de Batalha/ })).toHaveTextContent('War Wizard')
    expect(screen.getByText('Patamar 2 · Atirador')).toBeInTheDocument()
    expect(screen.getByText('11/23')).toBeInTheDocument()
    expect(screen.getByText(/Distante/)).toHaveTextContent('2d10+4 mágico')
    expect(screen.getByText('Conhecimento Mágico +2', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Gaste 1 Ponto de Medo').tagName).toBe('STRONG')
    expect(screen.getByRole('img', { name: 'Pontos de Fadiga: 0 de 6 marcados' })).toBeInTheDocument()
  })

  it('lacaio não tem limiares e horda mostra integrantes por PV', () => {
    render(<FichaInimigo adversario={{ ...MAGO, tipo: 'LACAIO', limiar_maior: null, limiar_grave: null }} />)
    expect(screen.getByText('Nenhum')).toBeInTheDocument()
    render(<FichaInimigo adversario={{ ...MAGO, nome: 'Mosquitos', tipo: 'HORDA', horda_por_pv: 5 }} />)
    expect(screen.getByText('Patamar 2 · Horda (5/PV)')).toBeInTheDocument()
  })
})

describe('Editor de inimigo', () => {
  function Controlado() {
    const [valor, setValor] = useState(INIMIGO_EM_BRANCO)
    return <EditorInimigo valor={valor} aoMudar={setValor} />
  }

  it('esconde os limiares para lacaio e pede integrantes para horda', async () => {
    render(<QueryClientProvider client={new QueryClient()}><Controlado /></QueryClientProvider>)
    expect(screen.getByLabelText('Limiar Maior')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'LACAIO')
    expect(screen.queryByLabelText('Limiar Maior')).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'HORDA')
    expect(screen.getByLabelText('Limiar Maior')).toHaveValue(6)
    expect(screen.getByLabelText('Integrantes por PV')).toHaveValue(2)
  })

  it('adiciona experiências e características', async () => {
    render(<QueryClientProvider client={new QueryClient()}><Controlado /></QueryClientProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar experiência' }))
    await userEvent.type(screen.getByLabelText('Experiência'), 'Emboscada')
    expect(screen.getByLabelText('Bônus')).toHaveValue(2)
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar característica' }))
    expect(screen.getByLabelText('Texto')).toBeInTheDocument()
  })
})

describe('Página da mesa', () => {
  const mesa = (papel: string): MesaT => ({
    id: 'm1', nome: 'Sombras de Haven', codigo_convite: 'ABC123', medo: 3, nivel_maximo: 1, meu_papel: papel, sou_criador: papel === 'mestre',
    permissoes_mestres: { ver_fichas: true, aplicar_dano: true, aplicar_condicoes: true, preparar: true },
    minhas_permissoes: papel === 'mestre' ? ['ver_fichas', 'aplicar_dano', 'aplicar_condicoes', 'preparar'] : [],
    membros: [{ usuario_id: 'u1', nome: 'Ana', papel, criador: papel === 'mestre' }],
    personagens: [],
  })

  it('jogador não vê a área do mestre', async () => {
    vi.stubGlobal('fetch', respostas({ '/mesas/m1': mesa('jogador'), '/personagens': [], '/srd/classes': [] }))
    montarEm('/mesas/m1?aba=inimigos', <Mesa />, '/mesas/:id')
    expect(await screen.findByText('ABC123')).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Inimigos' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sair da mesa' })).toBeInTheDocument()
    // o Medo fica visível para os jogadores, sem botões
    expect(screen.getByRole('img', { name: 'Medo: 3 de 12' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ganhar 1' })).not.toBeInTheDocument()
  })

  it('sessão: mestre ganha Medo, marca PV por clique e aplica dano', async () => {
    const lobo = { id: 'c1', rotulo: 'Lobo 1', adversario: { ...MAGO, nome: 'Lobo', pv: 4, pf: 2 }, origem: 'srd:x',
      pv_marcados: 0, pf_marcados: 0, condicoes: [], derrotado: false }
    const encontro = { id: 'e1', nome: 'Emboscada', combatentes: [lobo] }
    const comPv = (pv: number) => ({ ...encontro, combatentes: [{ ...lobo, pv_marcados: pv, derrotado: pv >= 4 }] })
    const fetch = respostas({
      '/mesas/m1': mesa('mestre'), '/mesas/m1/medo': { medo: 4 },
      '/mesas/m1/encontros': [{ id: 'e1', nome: 'Emboscada', combatentes: 1, derrotados: 0 }],
      '/mesas/m1/encontros/e1': encontro,
      '/mesas/m1/encontros/e1/combatentes/c1/marcas': comPv(2),
      '/mesas/m1/encontros/e1/combatentes/c1/dano': {
        resultado: { dano: 12, gravidade: 2, pv_marcados: 2, derrotado: true }, encontro: comPv(4) },
    })
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    await userEvent.click(await screen.findByRole('button', { name: 'Ganhar 1' }))
    expect(await screen.findByRole('group', { name: 'Medo: 4 de 12' })).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('button', { name: 'PV restantes de Lobo 1 2' }))
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/encontros/e1/combatentes/c1/marcas', expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ pv_marcados: 2, pf_marcados: 0 }) }))
    expect(await screen.findByRole('group', { name: 'PV restantes de Lobo 1: 2 de 4' })).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Dano em Lobo 1'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar dano' }))
    expect(await screen.findByText('12 de dano (Maior): 2 PV marcados. Derrotado!')).toBeInTheDocument()
    expect(screen.getByText('Derrotado')).toBeInTheDocument()
  })

  it('mestre copia um adversário do SRD para a mesa', async () => {
    const fetch = respostas({
      '/mesas/m1': mesa('mestre'), '/mesas/m1/inimigos': [], '/srd/adversarios': [{ ...MAGO, id: 'srd_war_wizard' }],
      '/mesas/m1/inimigos/do-srd/srd_war_wizard': { ...MAGO, id: 'novo', base_id: 'srd_war_wizard' },
      '/mesas/m1/inimigos/novo': { ...MAGO, id: 'novo', base_id: 'srd_war_wizard' },
    })
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1', <Mesa />, '/mesas/:id')
    await userEvent.click(await screen.findByRole('tab', { name: 'Inimigos' }))
    await userEvent.click(screen.getByRole('button', { name: 'Catálogo do SRD' }))
    await userEvent.type(screen.getByLabelText('Buscar'), 'wizard')
    await userEvent.click(await screen.findByRole('button', { name: /Mago de Batalha/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Adicionar à mesa' }))
    expect(await screen.findByRole('button', { name: 'Editar' })).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/mesas/m1/inimigos/do-srd/srd_war_wizard', expect.objectContaining({ method: 'POST' }))
  })
})
