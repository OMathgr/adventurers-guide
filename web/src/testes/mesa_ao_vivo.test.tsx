import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProvedorAutenticacao } from '../auth/Autenticacao'
import Layout from '../componentes/Layout'
import MedoDoMestre from '../componentes/MedoDoMestre'
import { Botao, Escolhivel, Espacos } from '../componentes/ui'
import Mesa from '../paginas/Mesa'
import Personagens from '../paginas/Personagens'

// a mesa 3D precisa de WebGL: no teste, fica de fora
vi.mock('../componentes/Dados3D', () => ({ default: () => null }))

function respostas(rotas: Record<string, unknown>) {
  return vi.fn(async (url: string) => {
    const caminho = url.replace(/^\/api/, '')
    if (!(caminho in rotas)) return new Response(JSON.stringify({ detail: 'não achei' }), { status: 404 })
    return new Response(JSON.stringify(rotas[caminho]), { status: 200 })
  })
}

function montarEm(caminho: string, elemento: ReactNode, rota: string) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ProvedorAutenticacao>
        <MemoryRouter initialEntries={[caminho]}>
          <Routes><Route path={rota} element={elemento} /></Routes>
        </MemoryRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>,
  )
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear() })

const MESA = {
  id: 'm1', nome: 'Sombras de Haven', codigo_convite: 'ABC123', nivel_maximo: 1, usar_moedas: false, meu_papel: 'mestre', sou_criador: true,
  medo_em_jogo: [], permissoes_mestres: { ver_fichas: true, aplicar_dano: true, aplicar_condicoes: true, preparar: true },
  minhas_permissoes: ['ver_fichas', 'aplicar_dano', 'aplicar_condicoes', 'preparar'],
  membros: [{ usuario_id: 'u1', nome: 'Ana', papel: 'mestre', criador: true, online: true }], personagens: [],
}
const base = '/mesas/m1/sessoes/s1'

function sessao(status: string) {
  const resumo = { id: 's1', titulo: 'A ponte', data: null, status, medo: 3, responsavel_id: 'u1', responsavel: 'Ana',
    sou_responsavel: true, posso_gerir: true, participantes: 0 }
  return { resumo, completa: { ...resumo, resumo: '', notas: '', compartilhada_com: [], npcs: [], inimigos: [], encontros: [] } }
}

function rotasDaSessao(status: string, novoStatus = status) {
  const { resumo, completa } = sessao(status)
  return {
    '/mesas/m1': MESA, '/mesas/m1/sessoes': [resumo], [base]: completa, [`${base}/status`]: { ...completa, status: novoStatus },
    [`${base}/jogo`]: { participantes: [] }, [`${base}/rolagens`]: [], [`${base}/repouso`]: null,
    '/mesas/m1/npcs': [], '/mesas/m1/inimigos': [],
  }
}

describe('Sessão do mestre', () => {
  it('planejada: inicia por um botão, sem mesa ao vivo ainda', async () => {
    const fetch = respostas(rotasDaSessao('planejada', 'em_andamento'))
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    const iniciar = await screen.findByRole('button', { name: 'Iniciar sessão' })
    expect(screen.queryByRole('tab', { name: 'Ao vivo' })).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Planejamento' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.click(iniciar)
    expect(fetch).toHaveBeenCalledWith(`/api${base}/status`, expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ status: 'em_andamento' }) }))
  })

  it('em andamento: abre ao vivo, com o grupo e os encontros na mesma tela e o Medo à vista', async () => {
    vi.stubGlobal('fetch', respostas(rotasDaSessao('em_andamento')))
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    expect(await screen.findByRole('tab', { name: 'Ao vivo' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByRole('heading', { name: 'Personagens na sessão' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Encontros' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Medo da sessão' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Últimas rolagens' })).toBeInTheDocument()
  })

  it('encerrar pede confirmação: recusando, nada muda', async () => {
    const fetch = respostas(rotasDaSessao('em_andamento', 'encerrada'))
    vi.stubGlobal('fetch', fetch)
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(false)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')

    await userEvent.click(await screen.findByRole('button', { name: 'Encerrar sessão' }))
    expect(confirmar).toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalledWith(`/api${base}/status`, expect.anything())
    confirmar.mockReturnValue(true)
    await userEvent.click(screen.getByRole('button', { name: 'Encerrar sessão' }))
    expect(fetch).toHaveBeenCalledWith(`/api${base}/status`, expect.objectContaining({
      body: JSON.stringify({ status: 'encerrada' }) }))
  })
})

describe('Sessão do jogador', () => {
  const FICHA = {
    nome: 'Lira', tracos: { AGILITY: 1, PRESENCE: 2, STRENGTH: -1, FINESSE: 0, INSTINCT: 0, KNOWLEDGE: 1 },
    experiencias: {}, ataques: [], conjuracoes: [], cartas_ativas: [], cartas_cofre: [], cartas_aplicadas: [], habilidades: [],
    proficiencia: 1, condicoes: [], cicatrizes: [], morto: false, pv_max: 5, pv_marcados: 1, estresse_max: 6, estresse_marcado: 0,
    esperanca: 2, esperanca_max: 6, pontuacao_armadura: 0, armadura_marcada: 0, tracos_marcados: [],
    caracteristicas_armadura: [], caracteristicas_ancestralidade: [], caracteristicas_comunidade: [],
  }
  const resumo = { id: 's1', titulo: 'A ponte', data: null, status: 'em_andamento', medo: 3, responsavel_id: 'u1', responsavel: 'Ana',
    sou_responsavel: false, posso_gerir: false, participantes: 1 }
  const vista = { ...resumo, mestre: 'Ana', meus: ['lira'], combate: [], npcs: [], lojas: [],
    participantes: [{ personagem_id: 'lira', resumo: { nome: 'Lira' } }] }

  function abrir(status = 'em_andamento') {
    const rotas: Record<string, unknown> = {
      '/mesas/m1': { ...MESA, meu_papel: 'jogador', sou_criador: false, minhas_permissoes: [], codigo_convite: null },
      '/mesas/m1/sessoes': [{ ...resumo, status }], [`${base}/jogo`]: { ...vista, status },
      [`${base}/rolagens`]: [], [`${base}/repouso`]: null, '/personagens/lira': FICHA, '/personagens/lira/sessao/pv': FICHA,
      '/personagens': [], '/srd/cartas': [], '/srd/classes': [],
    }
    const fetch = vi.fn(async (url: string, opcoes?: RequestInit) => {
      const caminho = url.replace(/^\/api/, '').split('?')[0]
      if (opcoes?.method && opcoes.method !== 'GET' && caminho.startsWith('/personagens/lira/sessao')) {
        return new Response(JSON.stringify(FICHA), { status: 200 })
      }
      return new Response(JSON.stringify(rotas[caminho] ?? (caminho.includes('/lira') ? FICHA : [])), { status: 200 })
    })
    vi.stubGlobal('fetch', fetch)
    montarEm('/mesas/m1?aba=sessao', <Mesa />, '/mesas/:id')
    return fetch
  }

  it('o painel de PV, PF e Esperança continua na aba de dados, e marca de lá', async () => {
    const fetch = abrir()
    await userEvent.click(await screen.findByRole('tab', { name: 'Rolagem de dados' }))
    const painel = await screen.findByRole('group', { name: 'Marcas da sessão' })
    expect(painel).toHaveClass('sm:hidden')   // no computador, a aba de dados segue sem ele
    await userEvent.click(within(painel).getByRole('button', { name: 'Marcar 1 PV' }))
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/personagens/lira/sessao'), expect.objectContaining({ method: expect.any(String) }))
  })

  it('na aba de jogo o painel é um só, e também aparece no computador', async () => {
    abrir()
    const painel = await screen.findByRole('group', { name: 'Marcas da sessão' })
    expect(painel).not.toHaveClass('sm:hidden')
    expect(screen.getAllByRole('group', { name: 'Marcas da sessão' })).toHaveLength(1)
  })

  it('sessão encerrada não tem painel na aba de dados', async () => {
    abrir('encerrada')
    await userEvent.click(await screen.findByRole('tab', { name: 'Rolagem de dados' }))
    expect(await screen.findByRole('region', { name: 'Registro de rolagens' })).toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Marcas da sessão' })).not.toBeInTheDocument()
  })
})

describe('Lista de personagens', () => {
  const lista = [
    { id: 'p1', nome: 'Lira', nivel: 1, classe: 'bardo', mesa_id: 'm1', foto: null, em_jogo: { sessao_id: 's1', titulo: 'A ponte' } },
    { id: 'p2', nome: 'Torvald', nivel: 2, classe: 'bardo', mesa_id: null, foto: null, em_jogo: null },
  ]

  it('leva direto à sessão em andamento e não mostra marcas, que só existem na sessão', async () => {
    vi.stubGlobal('fetch', respostas({ '/personagens': lista, '/srd/classes': [{ id: 'bardo', nome: 'Bardo' }] }))
    montarEm('/personagens', <Personagens />, '/personagens')

    const sessaoLink = await screen.findByRole('link', { name: 'A ponte' })
    expect(sessaoLink).toHaveAttribute('href', '/mesas/m1?aba=sessao&sessao=s1')
    expect(screen.getByRole('link', { name: 'Lira' })).toHaveAttribute('href', '/personagens/p1')
    expect(screen.getByText('Sem mesa')).toBeInTheDocument()
    expect(screen.queryByText(/Pontos de Vida|Esperança/)).not.toBeInTheDocument()
  })

  it('o menu ganha "Sessão" enquanto houver sessão em andamento', async () => {
    vi.stubGlobal('fetch', respostas({ '/personagens': lista }))
    montarEm('/x', <Layout />, '/x')
    const menu = screen.getByRole('navigation', { name: 'Principal' })
    expect(await within(menu).findByRole('link', { name: 'Sessão' })).toHaveAttribute('href', '/mesas/m1?aba=sessao&sessao=s1')
  })
})

describe('Menu na sessão em que se está jogando', () => {
  const lista = [{ id: 'p1', nome: 'Lira', nivel: 1, classe: 'bardo', mesa_id: 'm1', foto: null, em_jogo: { sessao_id: 's1', titulo: 'A ponte' } }]
  const marcados = async (caminho: string) => {
    vi.stubGlobal('fetch', respostas({ '/personagens': lista }))
    montarEm(caminho, <Layout />, '/mesas/:id')
    const menu = screen.getByRole('navigation', { name: 'Principal' })
    await within(menu).findByRole('link', { name: 'Sessão' })
    return within(menu).getAllByRole('link').filter((l) => l.getAttribute('aria-current') === 'page').map((l) => l.textContent)
  }

  it('dentro da sessão, marca "Sessão" e não "Mesas"', async () => {
    expect(await marcados('/mesas/m1?aba=sessao&sessao=s1')).toEqual(['Sessão'])
  })

  it('na aba de sessões, que abre a sessão em andamento, também', async () => {
    expect(await marcados('/mesas/m1?aba=sessao')).toEqual(['Sessão'])
  })

  it('em outra aba da mesa, marca "Mesas"', async () => {
    expect(await marcados('/mesas/m1')).toEqual(['Mesas'])
  })

  it('em outra sessão da mesma mesa, marca "Mesas"', async () => {
    expect(await marcados('/mesas/m1?aba=sessao&sessao=s2')).toEqual(['Mesas'])
  })

  it('com personagens em duas sessões, marca "Sessão" na segunda e aponta para ela', async () => {
    const duas = [...lista, { ...lista[0], id: 'p2', mesa_id: 'm2', em_jogo: { sessao_id: 's9', titulo: 'Outra' } }]
    vi.stubGlobal('fetch', respostas({ '/personagens': duas }))
    montarEm('/mesas/m2?aba=sessao&sessao=s9', <Layout />, '/mesas/:id')
    const menu = screen.getByRole('navigation', { name: 'Principal' })
    const sessaoLink = await within(menu).findByRole('link', { name: 'Sessão' })
    expect(sessaoLink).toHaveAttribute('aria-current', 'page')
    expect(sessaoLink).toHaveAttribute('href', '/mesas/m2?aba=sessao&sessao=s9')
    expect(within(menu).getByRole('link', { name: 'Mesas' })).not.toHaveAttribute('aria-current')
  })

  it('em outra mesa, marca "Mesas"', async () => {
    expect(await marcados('/mesas/m2?aba=sessao')).toEqual(['Mesas'])
  })
})

describe('Peças do tema', () => {
  it('cada recurso tem a sua cor: PV e Fadiga não usam a cor da Esperança nem a do Medo', () => {
    render(<>
      <Espacos total={1} marcados={0} rotulo="PV" restantes />
      <Espacos total={1} marcados={0} rotulo="PF" cor="fadiga" restantes />
    </>)
    expect(screen.getByRole('img', { name: /^PV/ }).firstElementChild).toHaveClass('bg-pv')
    expect(screen.getByRole('img', { name: /^PF/ }).firstElementChild).toHaveClass('bg-fadiga')
  })

  it('o que está selecionado ganha o laranja, além do sinal que não depende de cor', () => {
    const { container } = render(<Escolhivel selecionado onClick={() => {}}>Bardo</Escolhivel>)
    expect(screen.getByRole('button', { name: 'Bardo' })).toHaveClass('border-esperanca')
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('os losangos de Medo ficam sempre em duas fileiras de 6', () => {
    render(<MedoDoMestre medo={8} />)
    expect(screen.getByRole('img', { name: 'Medo: 8 de 12' })).toHaveClass('grid-cols-6')
  })

  it('o Medo pesa de 9 em diante', () => {
    const { rerender } = render(<MedoDoMestre medo={8} />)
    expect(screen.getByRole('region', { name: 'Medo' })).not.toHaveAttribute('data-alto')
    rerender(<MedoDoMestre medo={9} />)
    expect(screen.getByRole('region', { name: 'Medo' })).toHaveAttribute('data-alto')
  })

  it('botão desabilitado é neutro, sem a cor da ação principal apagada', () => {
    render(<Botao disabled>Confirmar</Botao>)
    expect(screen.getByRole('button', { name: 'Confirmar' })).toHaveClass('disabled:bg-superficie-2')
    expect(screen.getByRole('button', { name: 'Confirmar' }).className).not.toContain('disabled:opacity')
  })
})
