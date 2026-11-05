import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { EventoLinhaDoTempo, Ficha } from '../api/tipos'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import MedoDoMestre from '../componentes/MedoDoMestre'
import { Abas, Esperanca } from '../componentes/ui'
import { ganhosDeNivel } from '../lib/ganhosDeNivel'

const FICHA = {
  nome: 'Lira', nivel: 1, tracos: { AGILITY: 1, STRENGTH: 0 }, experiencias: { Diplomata: 2 }, cartas: [], cartas_ativas: ['a'], cartas_cofre: [],
  companheiro: null, pv_max: 5, estresse_max: 6, esperanca_max: 6, evasao: 10, proficiencia: 1, limiar_maior: 3, limiar_grave: 6,
} as unknown as Ficha
const NIVEL_2 = {
  ...FICHA, nivel: 2, tracos: { AGILITY: 2, STRENGTH: 1 }, experiencias: { Diplomata: 2, Viajante: 2 }, cartas_ativas: ['a', 'b'],
  pv_max: 6, proficiencia: 2, limiar_maior: 4, limiar_grave: 7,
} as unknown as Ficha

const EVENTOS = [
  { nivel: 1, tier: 1, status: 'feito', titulo: 'Criação', itens: [], quadros: [], planejado: false, bloqueado_pela_mesa: false },
] as unknown as EventoLinhaDoTempo[]

function comCliente(filho: ReactNode, cliente: QueryClient) {
  return <QueryClientProvider client={cliente}><MemoryRouter>{filho}</MemoryRouter></QueryClientProvider>
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(
    JSON.stringify(url.includes('/srd/cartas') ? [{ id: 'b', nome: 'Palavras Inspiradoras' }] : []), { status: 200 })))
})
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

describe('O que se ganha ao subir de nível', () => {
  it('lista só o que mudou entre as duas fichas', () => {
    expect(ganhosDeNivel(FICHA, NIVEL_2, (id) => (id === 'b' ? 'Palavras Inspiradoras' : undefined))).toEqual([
      'Nova carta: Palavras Inspiradoras',
      'Nova Experiência: Viajante (+2)',
      '+1 em Agilidade',
      '+1 em Força',
      '+1 espaço de Ponto de Vida',
      '+1 de Proficiência',
      'Limiares de dano: 3/6 → 4/7',
    ])
  })

  it('Experiência que subiu aparece com o valor de antes e o novo', () => {
    const depois = { ...FICHA, experiencias: { Diplomata: 3 } } as unknown as Ficha
    expect(ganhosDeNivel(FICHA, depois, () => undefined)).toEqual(['Diplomata: +2 → +3'])
  })
})

describe('Celebração de nível', () => {
  function montar() {
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const props = { eventos: EVENTOS, personagemId: 'p1', aoDesfazer: vi.fn(), desfazendo: false }
    const r = render(comCliente(<LinhaDoTempo {...props} ficha={FICHA} />, cliente))
    return { trocar: (ficha: Ficha) => r.rerender(comCliente(<LinhaDoTempo {...props} ficha={ficha} />, cliente)) }
  }

  it('aparece quando o nível sobe, com o que foi ganho, e o foco vai para "Continuar"', async () => {
    const { trocar } = montar()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    trocar(NIVEL_2)
    const dialogo = await screen.findByRole('dialog', { name: 'Nível 2' })
    expect(within(within(dialogo).getByRole('list', { name: 'O que você ganhou' })).getByText('+1 de Proficiência')).toBeInTheDocument()
    expect(within(dialogo).getByRole('button', { name: 'Continuar' })).toHaveFocus()
  })

  it('fecha com "Continuar" e com Esc', async () => {
    const { trocar } = montar()
    trocar(NIVEL_2)
    await userEvent.click(await screen.findByRole('button', { name: 'Continuar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    trocar({ ...NIVEL_2, nivel: 3 } as unknown as Ficha)
    await screen.findByRole('dialog', { name: 'Nível 3' })
    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('não aparece ao desfazer um nível nem quando só outras marcas mudam', async () => {
    const { trocar } = montar()
    trocar({ ...FICHA, pv_marcados: 2 } as unknown as Ficha)
    trocar({ ...FICHA, nivel: 0 } as unknown as Ficha)
    await act(async () => {})
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('Respostas às mudanças', () => {
  const comAnimacao = (c: HTMLElement) => [...c.querySelectorAll('.marca-muda')]

  it('ao abrir a tela nada anima; só o losango que mudou reage, e depois para', () => {
    vi.useFakeTimers()
    const { container, rerender } = render(<Esperanca atual={2} maximo={6} />)
    expect(comAnimacao(container)).toHaveLength(0)
    rerender(<Esperanca atual={3} maximo={6} />)
    const losangos = [...container.querySelectorAll('[role=img] > span')]
    expect(comAnimacao(container)).toEqual([losangos[2]])
    act(() => { vi.advanceTimersByTime(1000) })
    expect(comAnimacao(container)).toHaveLength(0)
  })

  it('em coluna estreita os losangos de Esperança descem de linha, sem se deformar', () => {
    const { container } = render(<Esperanca atual={2} maximo={6} />)
    expect(container.querySelector('[role=img]')).toHaveClass('flex-wrap')
    for (const losango of container.querySelectorAll('[role=img] > span')) expect(losango).toHaveClass('shrink-0')
  })

  it('quando o Medo muda, o losango e o número reagem', () => {
    vi.useFakeTimers()
    const { container, rerender } = render(<MedoDoMestre medo={4} />)
    expect(container.querySelector('.numero-muda')).toBeNull()
    rerender(<MedoDoMestre medo={3} />)
    expect(container.querySelector('.numero-muda')).toHaveTextContent('3')
    expect(comAnimacao(container)).toHaveLength(1)
  })

  it('a marca da aba existe, fora da leitura de quem usa leitor de tela', () => {
    render(<Abas abas={[['a', 'Um'], ['b', 'Dois']]} atual="a" aoTrocar={() => {}} />)
    const barra = screen.getByRole('tablist')
    expect(barra.querySelector('[data-marca-da-aba]')).toHaveAttribute('aria-hidden')
    expect(within(barra).getAllByRole('tab')).toHaveLength(2)
  })
})
