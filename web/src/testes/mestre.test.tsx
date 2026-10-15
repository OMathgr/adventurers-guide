import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ReactNode, useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Adversario, Mesa as MesaT } from '../api/tipos'
import { ProvedorAutenticacao } from '../auth/Autenticacao'
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
      <ProvedorAutenticacao>
        <MemoryRouter initialEntries={[caminho]}><Routes><Route path={rota} element={ui} /></Routes></MemoryRouter>
      </ProvedorAutenticacao>
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
    expect(screen.getByRole('img', { name: 'Pontos de Fadiga restantes: 6 de 6' })).toBeInTheDocument()
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

const RESUMO_EM_JOGO = { id: 's1', titulo: 'A ponte', data: null, status: 'em_andamento', medo: 3,
  responsavel_id: 'u1', responsavel: 'Ana', sou_responsavel: false, posso_gerir: false, participantes: 1 }

const vista = (extra: Record<string, unknown> = {}) => ({
  id: 's1', titulo: 'A ponte', status: 'em_andamento', mestre: 'Ana', responsavel_id: 'u1', sou_responsavel: false,
  posso_gerir: false, medo: 3, participantes: [], meus: [], combate: [], npcs: [], lojas: [], ...extra,
})

describe('Página da mesa', () => {
  const mesa = (papel: string): MesaT => ({
    id: 'm1', nome: 'Sombras de Haven', codigo_convite: papel === 'mestre' ? 'ABC123' : null, nivel_maximo: 1, usar_moedas: false, meu_papel: papel, sou_criador: papel === 'mestre',
    medo_em_jogo: [{ sessao_id: 's1', mestre: 'Ana', medo: 3 }],
    permissoes_mestres: { ver_fichas: true, aplicar_dano: true, aplicar_condicoes: true, preparar: true },
    minhas_permissoes: papel === 'mestre' ? ['ver_fichas', 'aplicar_dano', 'aplicar_condicoes', 'preparar'] : [],
    membros: [{ usuario_id: 'u1', nome: 'Ana', papel, criador: papel === 'mestre', online: true }],
    personagens: [],
  })

  it('jogador vê na sessão o que o mestre revelou: vitalidade e condições, nunca os números', async () => {
    vi.stubGlobal('fetch', respostas({
      '/mesas/m1': mesa('jogador'), '/personagens': [], '/srd/classes': [],
      '/mesas/m1/sessoes': [RESUMO_EM_JOGO],
      '/mesas/m1/sessoes/s1/jogo': vista({
        combate: [{ id: 'e1', nome: 'Emboscada na ponte', mestre: 'Ana', inimigos: [
          { id: 'c1', rotulo: 'Lobo 1', foto: null, vitalidade: 'metade_da_vida', condicoes: ['VULNERAVEL'] },
          { id: 'c2', rotulo: 'Lobo 2', foto: null, vitalidade: 'derrotado', condicoes: [] }] }],
        npcs: [{ id: 'n1', nome: 'Marlowe', foto: null, descricao: 'Ferreiro da vila' }],
      }),
    }))
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')
    expect(await screen.findByRole('img', { name: 'Medo do mestre: 3 de 12' })).toBeInTheDocument()
    const lobo = await screen.findByRole('listitem', { name: 'Lobo 1' })
    expect(lobo).toHaveTextContent('Metade da vida')
    expect(lobo).toHaveTextContent('Vulnerável')
    expect(screen.getByRole('img', { name: 'Derrotado' })).toBeInTheDocument()
    expect(screen.getByText('Em combate: Emboscada na ponte')).toBeInTheDocument()
    expect(screen.getByText('Ferreiro da vila')).toBeInTheDocument()
  })

  it('jogador entra com o personagem e mexe nas marcas da sessão; os aliados aparecem resumidos', async () => {
    localStorage.setItem('ag.token', 'x')
    const resumo = (id: string, nome: string, jogador: string, pv: number) => ({
      id, nome, foto: null, jogador, nivel: 1, classe: 'Bardo', subclasse: 'Trovador', estagio_subclasse: 'fundacao',
      multiclasse: null, ancestralidade: 'Fauno', comunidade: 'Aristocrática', pv_max: 5, pv_marcados: pv,
      estresse_max: 6, estresse_marcado: 0, esperanca: 2, esperanca_max: 6 })
    const ficha = {
      nome: 'Lira', nivel: 1, classe: 'core_class_bard', subclasse: 'core_subclass_troubadour', estagio_subclasse: 'fundacao',
      tracos: {}, tracos_marcados: [], evasao: 10, pontuacao_armadura: 0, armadura_marcada: 0, armadura: null,
      limiar_maior: 1, limiar_grave: 2, pv_max: 5, pv_marcados: 0, estresse_max: 6, estresse_marcado: 0,
      esperanca: 2, esperanca_max: 6, condicoes: [], experiencias: {}, proficiencia: 1, ataques: [], conjuracoes: [],
      cartas: [], cartas_ativas: [], cartas_cofre: [], habilidades: [], caracteristicas_ancestralidade: [],
      caracteristicas_comunidade: [], caracteristicas_armadura: [], companheiro: null, cicatrizes: [],
      morto: false, inconsciente: false, precisa_movimento_de_morte: false,
    }
    const fetch = respostas({
      '/auth/eu': { id: 'u2', nome: 'Bia', email: 'b@x' },
      '/mesas/m1': mesa('jogador'), '/personagens': [], '/srd/classes': [],
      '/mesas/m1/sessoes': [RESUMO_EM_JOGO], '/mesas/m1/sessoes/s1/repouso': null,
      '/mesas/m1/sessoes/s1/jogo': vista({ meus: ['lira'], participantes: [
        { personagem_id: 'lira', dono_id: 'u2', resumo: resumo('lira', 'Lira', 'Bia', 0) },
        { personagem_id: 'bruno', dono_id: 'u3', resumo: resumo('bruno', 'Bruno', 'Carlos', 2) }] }),
      '/personagens/lira': ficha,
      '/personagens/lira/sessao/pv/marcar': { ...ficha, pv_marcados: 1 },
    })
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    await userEvent.click(await screen.findByRole('button', { name: 'Marcar 1 PV' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/lira/sessao/pv/marcar', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ quantidade: 1 }) }))
    expect(await screen.findByText('(restam 4/5)')).toBeInTheDocument()
    // aliado: só a mini ficha (quem é e PV, PF, Esperança)
    expect(screen.getByRole('region', { name: 'Ficha de Bruno' })).toHaveTextContent('Vida: 3/5 PV')
    localStorage.clear()
  })

  it('mestre vê o convite numa aba própria', async () => {
    vi.stubGlobal('fetch', respostas({ '/mesas/m1': mesa('mestre'), '/personagens': [], '/srd/classes': [] }))
    montarEm('/mesas/m1', <Mesa />, '/mesas/:id')
    expect(await screen.findByText('Membros')).toBeInTheDocument()
    expect(screen.queryByLabelText('Código de convite')).not.toBeInTheDocument()   // fora da aba Mesa
    await userEvent.click(screen.getByRole('tab', { name: 'Convite' }))
    expect(await screen.findByLabelText('Código de convite')).toHaveTextContent('ABC123')
  })

  it('jogador não vê a área do mestre', async () => {
    vi.stubGlobal('fetch', respostas({
      '/mesas/m1': mesa('jogador'), '/personagens': [], '/srd/classes': [], '/mesas/m1/revelado': { combate: [], npcs: [] } }))
    montarEm('/mesas/m1?aba=convite', <Mesa />, '/mesas/:id')
    expect(await screen.findByRole('button', { name: 'Sair da mesa' })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Inimigos' })).not.toBeInTheDocument()
    // o convite é dos mestres: nem aba, nem código
    expect(screen.queryByRole('tab', { name: 'Convite' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Código de convite')).not.toBeInTheDocument()
    // o Medo e o resto do jogo ficam na sessão: a aba Mesa só avisa que há uma em andamento
    expect(screen.getByText(/Há sessão em andamento/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ganhar 1' })).not.toBeInTheDocument()
  })

  it('sessão: mestre ganha Medo, abre o encontro, marca PV por clique e aplica dano', async () => {
    const lobo = { id: 'c1', rotulo: 'Lobo 1', adversario: { ...MAGO, nome: 'Lobo', pv: 4, pf: 2 }, origem: 'srd:x',
      pv_marcados: 0, pf_marcados: 0, condicoes: [], derrotado: false }
    const guia = {
      opcoes: { pjs: 4, patamar: 2, mais_facil: false, mais_dificil: false, dano_extra: false }, base: 14,
      ajustes: [{ descricao: 'Sem brutamonte, horda, líder ou solo', valor: 1, automatico: true }], total: 15,
      gastos: [{ tipo: 'ATIRADOR', quantidade: 1, custo: 2 }], gasto: 2, saldo: 13,
      custos: { LACAIO: 1, SOCIAL: 1, SUPORTE: 1, HORDA: 2, ATIRADOR: 2, ESPREITADOR: 2, PADRAO: 2, LIDER: 3, BRUTAMONTES: 4, SOLO: 5 },
    }
    const encontro = { id: 'e1', nome: 'Emboscada na ponte', combatentes: [lobo], guia }
    const comPv = (pv: number) => ({ ...encontro, combatentes: [{ ...lobo, pv_marcados: pv, derrotado: pv >= 4 }] })
    const resumo = { id: 's1', titulo: 'A ponte', data: null, status: 'em_andamento', medo: 3,
      responsavel_id: 'u1', responsavel: 'Ana', sou_responsavel: true, posso_gerir: true, participantes: 0 }
    const sessao = { ...resumo, resumo: '', notas: '', compartilhada_com: [], npcs: [], inimigos: [],
      encontros: [{ id: 'e1', nome: 'Emboscada na ponte', combatentes: 1, derrotados: 0 }] }
    const base = '/mesas/m1/sessoes/s1'
    const fetch = respostas({
      '/mesas/m1': mesa('mestre'), '/mesas/m1/sessoes': [resumo], [base]: sessao,
      [`${base}/medo`]: { ...sessao, medo: 4 },
      [`${base}/encontros/e1`]: encontro,
      [`${base}/encontros/e1/combatentes/c1/marcas`]: comPv(2),
      [`${base}/encontros/e1/combatentes/c1/dano`]: {
        resultado: { dano: 12, gravidade: 2, pv_marcados: 2, derrotado: true }, encontro: comPv(4) },
      '/mesas/m1/npcs': [], '/mesas/m1/inimigos': [{ id: 'i1', nome: 'Ogro', patamar: 1, tipo: 'BRUTAMONTES', base_id: null }],
      [`${base}/encontros/e1/guia/simular`]: { ...guia, gasto: 6, total: 17, saldo: 11 },
    })
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    expect(await screen.findByRole('tab', { name: 'Sessões' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(await screen.findByRole('button', { name: 'Ganhar 1' }))
    expect(fetch).toHaveBeenCalledWith(`/api${base}/medo`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ delta: 1 }) }))
    expect(await screen.findByRole('group', { name: 'Medo da sessão: 4 de 12' })).toBeInTheDocument()

    // encontros não têm ordem: o mestre abre o que acontecer (na sub-aba Encontros da sessão)
    await userEvent.click(screen.getByRole('tab', { name: 'Encontros' }))
    await userEvent.click(screen.getByRole('button', { name: /Emboscada na ponte/ }))
    const painel = await screen.findByRole('region', { name: 'Guia de Batalha' })
    expect(painel).toHaveTextContent('2 de 15 PB gastos · sobram 13 PB')
    expect(painel).toHaveTextContent('1 Atiradores2 PB')

    // ao escolher um inimigo, o custo aparece antes de adicionar (simulado pela API)
    expect(await screen.findByRole('option', { name: 'Ogro (P1, Brutamonte · 4 PB)' })).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Ficha'), 'i1')
    expect(await screen.findByText((_, el) => el?.tagName === 'P' && !!el.textContent?.startsWith('Esta escolha custa'))).toHaveTextContent('Esta escolha custa 4 PB e muda o total em +2 PB (patamar) · sobrariam 11 PB')

    await userEvent.click(await screen.findByRole('button', { name: 'PV restantes de Lobo 1 2' }))
    expect(fetch).toHaveBeenCalledWith(`/api${base}/encontros/e1/combatentes/c1/marcas`, expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ pv_marcados: 2, pf_marcados: 0 }) }))
    expect(await screen.findByRole('group', { name: 'PV restantes de Lobo 1: 2 de 4' })).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Dano em Lobo 1'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar dano' }))
    expect(await screen.findByText('12 de dano (Maior): 2 PV marcados. Derrotado!')).toBeInTheDocument()
    expect(screen.getByText('Derrotado')).toBeInTheDocument()
  })

  it('sessão compartilhada é só leitura', async () => {
    const resumo = { id: 's2', titulo: 'Do Carlos', data: null, status: 'planejada', medo: 2,
      responsavel_id: 'u2', responsavel: 'Carlos', sou_responsavel: false, posso_gerir: true, participantes: 0 }
    const sessao = { ...resumo, resumo: 'Segredo', notas: '', compartilhada_com: ['u1'], npcs: [], inimigos: [], encontros: [] }
    vi.stubGlobal('fetch', respostas({
      '/mesas/m1': mesa('mestre'), '/mesas/m1/sessoes': [resumo], '/mesas/m1/sessoes/s2': sessao,
      '/mesas/m1/npcs': [], '/mesas/m1/inimigos': [],
    }))
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')
    expect(await screen.findByText(/Sessão de Carlos \(só leitura\)/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ganhar 1' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Resumo e objetivos')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Salvar planejamento' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Apagar sessão' })).not.toBeInTheDocument()
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
