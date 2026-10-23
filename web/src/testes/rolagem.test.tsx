import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Rolagem } from '../api/tipos'
import { ContextoDaSessao } from '../componentes/contextoDaSessao'
import RolagemDeDados, { gruposDaRolagem } from '../componentes/RolagemDeDados'
import { CORES_PADRAO, notacao } from '../lib/coresDosDados'

// a mesa 3D precisa de WebGL: no teste, fica de fora
vi.mock('../componentes/Dados3D', () => ({ default: () => null }))

const FICHA = {
  nome: 'Lira', tracos: { AGILITY: 1, PRESENCE: 2, STRENGTH: -1, FINESSE: 0, INSTINCT: 0, KNOWLEDGE: 1 },
  experiencias: { Diplomata: 2 }, ataques: [], conjuracoes: [], cartas_ativas: [], habilidades: [], proficiencia: 1,
}

const ROLAGEM: Rolagem = {
  id: 'r1', autor: 'Bia', usuario_id: 'u2', personagem_id: 'lira', personagem: 'Lira', oculta: false, substituida: false,
  criado_em: '2026-10-16T10:00:00', reacoes: [],
  resultado: {
    titulo: 'Teste de Presença', total: 15, dualidade: 'esperanca', sucesso: true, dificuldade: 12, tipo: 'teste',
    dados: [{ faces: 12, valor: 9, papel: 'esperanca' }, { faces: 12, valor: 4, papel: 'medo' }],
    bonus: [{ fonte: 'Presença', valor: 2 }], efeitos: ['Com Esperança: +1 de Esperança.'], opcoes: [],
  },
} as unknown as Rolagem

function montar() {
  const chamadas: { url: string; corpo?: unknown }[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, opcoes?: RequestInit) => {
    const caminho = url.replace(/^\/api/, '')
    chamadas.push({ url: caminho, corpo: opcoes?.body ? JSON.parse(String(opcoes.body)) : undefined })
    const corpo = caminho.startsWith('/personagens/lira') ? FICHA
      : caminho.includes('/rolagens/opcoes') ? [
        { id: 'privilege', nome: 'Privilégio', momento: 'antes', condicao: 'conviver com nobres', disponivel: true,
          custo_esperanca: 0, custo_fadiga: 0, escolha: [] },
        { id: 'arcana_touched', nome: 'Toque Arcano', momento: 'automatico', disponivel: true, escolha: [] }]
      : caminho.includes('/rolagens') && opcoes?.method === 'POST' ? ROLAGEM
      : caminho.includes('/rolagens') ? [ROLAGEM]
      : caminho === '/srd/cartas' ? [] : {}
    return new Response(JSON.stringify(corpo), { status: 200 })
  }))
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={cliente}><MemoryRouter>
    <RolagemDeDados mesaId="m1" sessaoId="s1" personagemId="lira" souMestre={false} emAndamento />
  </MemoryRouter></QueryClientProvider>)
  return chamadas
}

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

describe('Rolagem de dados', () => {
  it('monta o teste com Experiência e opção e manda para o servidor rolar', async () => {
    const chamadas = montar()
    await userEvent.selectOptions(await screen.findByLabelText('Atributo'), 'PRESENCE')
    await userEvent.click(screen.getByLabelText('Diplomata (+2)'))
    expect(await screen.findByText('Toque Arcano')).toBeInTheDocument()   // automático: só aparece marcado
    await userEvent.click(screen.getByRole('checkbox', { name: /Privilégio/ }))
    await userEvent.type(screen.getByLabelText('Dificuldade'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Rolar' }))
    const pedido = chamadas.find((c) => c.url === '/mesas/m1/sessoes/s1/rolagens' && c.corpo)?.corpo as Record<string, unknown>
    expect(pedido).toMatchObject({ tipo: 'atributo', traco: 'PRESENCE', personagem_id: 'lira', experiencias: ['Diplomata'],
      dificuldade: 12, opcoes: [{ id: 'privilege', quantidade: null, escolha: null }] })
  })

  it('o registro mostra os dados, o total e o que foi aplicado', async () => {
    montar()
    const item = (await screen.findByRole('region', { name: 'Registro de rolagens' }))
    expect(await within(item).findByText('15')).toBeInTheDocument()
    expect(within(item).getByText('com Esperança')).toBeInTheDocument()
    expect(within(item).getByText('Dificuldade 12: sucesso')).toBeInTheDocument()
    expect(within(item).getByText('Com Esperança: +1 de Esperança.')).toBeInTheDocument()
  })

  it('separa os dados por cor para a mesa 3D, com os valores do servidor', () => {
    const grupos = gruposDaRolagem(ROLAGEM, CORES_PADRAO)
    expect(grupos.map((g) => [g.cor, notacao(g)])).toEqual([
      [CORES_PADRAO.esperanca, '1d12@9'], [CORES_PADRAO.medo, '1d12@4']])
  })
})

describe('Carta disparada pela rolagem', () => {
  it('o registro oferece a carta e usa ligada àquela rolagem', async () => {
    const FEROCIDADE = {
      id: 'fer', nome: 'Ferocidade', nome_original: 'Ferocity', dominio: 'BONE', nivel: 2, tipo: 'ABILITY', custo_recall: 2,
      texto: '', formulas: [], passivo: null, escolha: null, reserva_permanente: false, fora_do_limite: false,
      uso: { custo: { esperanca: 2 }, por_unidade: {}, quantidade_max: null, quantidade_min: 1, quantidade_rotulo: '',
        limite: null, alvo: 'si', condicao: null, teste: '', opcoes: [], efeitos: [], recarga: null,
        recarga_quando: 'descanso_longo', nota: 'Evasão + PV que o inimigo marcou.', gatilho: { rolagens: ['dano'], se: 'qualquer', de: 'si' } },
    }
    const dano = { ...ROLAGEM, id: 'd1', cartas: ['fer'], resultado: { ...ROLAGEM.resultado, titulo: 'Dano: Espada', tipo: 'dano',
      dualidade: null, sucesso: null, dificuldade: null } } as unknown as Rolagem
    const chamadas: { url: string; corpo?: unknown }[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, opcoes?: RequestInit) => {
      const caminho = url.replace(/^\/api/, '')
      chamadas.push({ url: caminho, corpo: opcoes?.body ? JSON.parse(String(opcoes.body)) : undefined })
      const corpo = caminho.startsWith('/personagens/lira') ? { ...FICHA, esperanca: 3, marcadores_cartas: {}, usos_de_carta_gastos: [] }
        : caminho.includes('/cartas/usar') ? { notas: ['Usou Ferocidade (2 de Esperança).'], teste: '', ficha: FICHA }
        : caminho.includes('/rolagens/opcoes') ? []
        : caminho.includes('/rolagens') ? [dano]
        : caminho === '/srd/cartas' ? [FEROCIDADE] : {}
      return new Response(JSON.stringify(corpo), { status: 200 })
    }))
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={cliente}><MemoryRouter>
      <ContextoDaSessao.Provider value={{ mesaId: 'm1', sessaoId: 's1', aliados: [] }}>
        <RolagemDeDados mesaId="m1" sessaoId="s1" personagemId="lira" souMestre={false} emAndamento />
      </ContextoDaSessao.Provider>
    </MemoryRouter></QueryClientProvider>)
    await userEvent.click(await screen.findByText('Carta: Ferocidade'))
    await userEvent.click(await screen.findByRole('button', { name: 'Usar Ferocidade' }))
    expect(chamadas.find((c) => c.url === '/mesas/m1/sessoes/s1/cartas/usar')?.corpo).toEqual(
      { personagem_id: 'lira', carta: 'fer', opcao: null, quantidade: null, alvos: [], rolagem_id: 'd1' })
    expect(await screen.findByText(/Usou Ferocidade/)).toBeInTheDocument()
  })
})
