import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { EventoLinhaDoTempo, Ficha, OpcaoNoQuadro, ProximoNivel, QuadroDeAvanco } from '../api/tipos'
import { ProvedorAutenticacao } from '../auth/Autenticacao'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import MaoEReserva from '../componentes/MaoEReserva'
import QuadroAvanco from '../componentes/QuadroAvanco'
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
    // uma resposta nova a cada chamada (a tela também pergunta /auth/provedores)
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () =>
      new Response(JSON.stringify({ detail: 'E-mail ou senha incorretos.' }), { status: 401 })))
    montar(<Entrar />)
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.com')
    await userEvent.type(screen.getByLabelText('Senha'), 'errada123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos.')
  })
})

/** Quadro do patamar 2 com PV e Evasão marcados no nível 2 (`antes` ou `neste`). */
function quadroTier2(onde: 'antes' | 'neste'): QuadroDeAvanco {
  const linha = (opcao: OpcaoNoQuadro['opcao'], limite: number, marcados = 0): OpcaoNoQuadro =>
    ({ opcao, limite, custo: 1, antes: onde === 'antes' ? marcados : 0, neste: onde === 'neste' ? marcados : 0, riscados: 0 })
  return {
    tier: 2,
    opcoes: [linha('TRACOS', 3), linha('PV', 2, 1), linha('ESTRESSE', 2), linha('EXPERIENCIAS', 1),
      linha('CARTA_DOMINIO', 1), linha('EVASAO', 1, 1)],
  }
}

const PROXIMO: ProximoNivel = {
  nivel: 3, tier: 2, nova_experiencia: false, limpa_marcas_tracos: false, experiencia_companheiro: false,
  avancos: 2, tracos_marcados: [], treinos: 0, treinos_extra_com_subclasse: 0, bloqueado_pela_mesa: false, planejado: false,
  opcoes: [
    { tier: 2, opcao: 'TRACOS', restantes: 3, custo: 1 }, { tier: 2, opcao: 'PV', restantes: 1, custo: 1 },
    { tier: 2, opcao: 'ESTRESSE', restantes: 2, custo: 1 }, { tier: 2, opcao: 'EXPERIENCIAS', restantes: 1, custo: 1 },
    { tier: 2, opcao: 'CARTA_DOMINIO', restantes: 1, custo: 1 },
  ],
}

describe('Linha do tempo', () => {
  const eventos: EventoLinhaDoTempo[] = [
    { nivel: 1, tier: 1, status: 'feito', titulo: 'Criação', itens: ['Classe: Bardo'], quadros: [], planejado: false, bloqueado_pela_mesa: false },
    { nivel: 2, tier: 2, status: 'feito', titulo: 'Nível 2', itens: ['Avanço: PV'], quadros: [quadroTier2('neste')], planejado: false, bloqueado_pela_mesa: false },
    { nivel: 3, tier: 2, status: 'futuro', titulo: 'Nível 3', itens: [], quadros: [quadroTier2('antes')], planejado: false, bloqueado_pela_mesa: false },
    { nivel: 4, tier: 2, status: 'futuro', titulo: 'Nível 4', itens: ['Escolher 2 avanços'], quadros: [quadroTier2('antes')], planejado: false, bloqueado_pela_mesa: false },
  ]
  const fichaCom = (ativas: string[]) => ({
    nome: 'Lia', experiencias: { Diplomata: 2 }, cartas: ativas, cartas_ativas: ativas, cartas_cofre: [],
    companheiro: null,
  }) as unknown as Ficha
  const ficha = fichaCom([])

  function montarLinha(desfazer = vi.fn(), f = ficha) {
    const fetch = vi.fn(async (url: string) => new Response(
      JSON.stringify(url.endsWith('/proximo-nivel') ? PROXIMO : []), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    montar(<LinhaDoTempo eventos={eventos} personagemId="p1" ficha={f} aoDesfazer={desfazer} desfazendo={false} />)
    return fetch
  }

  it('com a mão cheia, oferece mandar uma carta antiga para a reserva', async () => {
    montarLinha(vi.fn(), fichaCom(['c1', 'c2', 'c3', 'c4', 'c5']))
    expect(await screen.findByText('Mão cheia')).toBeInTheDocument()
    const c1 = screen.getByRole('checkbox', { name: 'c1' })
    await userEvent.click(c1)
    expect(c1).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'c2' })).toBeDisabled()   // só 1 carta nova neste nível
  })

  it('mostra a caixa do patamar em cada nível e desfazer só no último feito', async () => {
    const desfazer = vi.fn()
    montarLinha(desfazer)
    expect(await screen.findAllByRole('checkbox')).not.toHaveLength(0)   // próximo nível carregou
    expect(screen.getAllByRole('region', { name: '2º patamar' })).toHaveLength(3)
    expect(screen.getByRole('img', { name: '+1 de Evasão (2º patamar): marcado neste nível' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Desfazer este nível' })).toHaveLength(1)
    // desfazer pede confirmação: cancelar não desfaz
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    await userEvent.click(screen.getByRole('button', { name: 'Desfazer este nível' }))
    expect(desfazer).not.toHaveBeenCalled()
    // o botão da barra fica sempre à vista, mesmo com a linha rolada para o próximo nível
    await userEvent.click(screen.getByRole('button', { name: 'Desfazer o nível 2' }))
    expect(confirmar).toHaveBeenLastCalledWith(expect.stringContaining('Desfazer o nível 2?'))
    expect(desfazer).toHaveBeenCalledOnce()
    confirmar.mockRestore()
  })

  it('marca os avanços do próximo nível direto na caixa', async () => {
    montarLinha()
    const pv = await screen.findByRole('checkbox', { name: '+1 espaço de Ponto de Vida (2º patamar), quadradinho 2' })
    // o quadradinho 1 do PV já foi usado no nível 2: não é marcável
    expect(screen.queryByRole('checkbox', { name: /Ponto de Vida.*quadradinho 1/ })).not.toBeInTheDocument()
    await userEvent.click(pv)
    expect(pv).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(screen.getByRole('checkbox', { name: /dois atributos.*quadradinho 1/ }))
    expect(screen.getByText('Avanços (2/2)')).toBeInTheDocument()
    // avanço que pede detalhe abre os campos logo abaixo; com 2/2, o resto trava
    expect(screen.getByLabelText('Agilidade')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /Fadiga.*quadradinho 1/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Confirmar nível 3' })).toBeDisabled()
    await userEvent.click(pv)
    expect(screen.getByText('Avanços (1/2)')).toBeInTheDocument()
  })
})

describe('Mão e reserva', () => {
  it('com a mão cheia, trazer da reserva pede qual carta sai', async () => {
    const fetch = vi.fn(async (url: string) =>
      new Response(JSON.stringify(url.includes('/srd/') ? [] : {}), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    const ativas = ['a1', 'a2', 'a3', 'a4', 'a5']
    const f = { cartas: [...ativas, 'r1'], cartas_ativas: ativas, cartas_cofre: ['r1'] } as unknown as Ficha
    montar(<MaoEReserva ficha={f} personagemId="p1" />)
    expect(screen.getByText('Cartas de domínio: mão (5/5)')).toBeInTheDocument()
    await userEvent.click(screen.getByText('r1'))
    const trazer = screen.getByRole('button', { name: 'Trazer para a mão' })
    expect(trazer).toBeDisabled()
    await userEvent.selectOptions(screen.getByLabelText('Carta que vai para a reserva'), 'a2')
    await userEvent.click(trazer)
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/cartas/r1/recuperar', expect.objectContaining({
      body: JSON.stringify({ no_lugar_de: 'a2', em_descanso: true }),
    }))
  })
})

describe('Caixa de avanços', () => {
  it('mostra marcados antes, riscados e opção cortada', () => {
    render(<QuadroAvanco quadro={{
      tier: 3,
      opcoes: [
        { opcao: 'SUBCLASSE', limite: 1, custo: 1, antes: 1, neste: 0, riscados: 0 },
        { opcao: 'MULTICLASSE', limite: 1, custo: 2, antes: 0, neste: 0, riscados: 1 },
      ],
    }} />)
    expect(screen.getByRole('img', { name: 'Carta de subclasse aprimorada (3º patamar): marcado em nível anterior' }))
      .toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Multiclasse (3º patamar): riscado' })).toBeInTheDocument()
    expect(screen.getByText('Multiclasse')).toHaveClass('line-through')
  })
})

describe('Espaços', () => {
  it('descreve os marcados para leitores de tela', () => {
    render(<Espacos total={6} marcados={2} rotulo="Estresse" />)
    expect(screen.getByRole('img', { name: 'Estresse: 2 de 6 marcados' })).toBeInTheDocument()
  })

  it('padrão de PV/PF: começa cheio e esvazia com o dano', () => {
    render(<Espacos total={6} marcados={2} rotulo="Pontos de Vida" restantes />)
    expect(screen.getByRole('img', { name: 'Pontos de Vida restantes: 4 de 6' })).toBeInTheDocument()
  })
})
