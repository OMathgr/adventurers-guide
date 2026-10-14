import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Arma, Armadura, EventoLinhaDoTempo, Ficha, Mesa, ProximoNivel } from '../api/tipos'
import AbaEquipamento from '../componentes/AbaEquipamento'
import { EnviarFoto } from '../componentes/Foto'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import AbaGeral from '../paginas/mesa/AbaGeral'

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

const arma = (id: string, nome: string, extra: Partial<Arma> = {}): Arma => ({
  id, nome, nome_original: nome, categoria: 'PRIMARY_PHYSICAL', tier: 1, traco: 'STRENGTH', alcance: 'MELEE',
  dado: 'd8', modificador_dano: 0, tipo_dano: 'PHYSICAL', duas_maos: false, caracteristicas: [], ...extra,
})
const COURO: Armadura = { id: 'couro', nome: 'Armadura de Couro', nome_original: 'Leather Armor', tier: 1,
  limiar_maior: 6, limiar_grave: 13, pontuacao: 3, caracteristicas: [] }

describe('Equipamento', () => {
  it('arma de duas mãos ocupa a secundária e salvar manda os ids', async () => {
    const fetch = api({
      '/personagens/p1/equipamento': { principal: null, secundaria: 'adaga', armadura: null },
      '/srd/armas': [arma('espada', 'Espada'), arma('montante', 'Montante', { duas_maos: true }),
        arma('adaga', 'Adaga de Mão', { categoria: 'SECONDARY' })],
      '/srd/armaduras': [COURO],
    })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaEquipamento personagemId="p1" ficha={{ nivel: 2, conjuracoes: [] } as unknown as Ficha} />)

    await userEvent.click(await screen.findByRole('button', { name: /Montante/ }))
    expect(screen.getByText('Mãos ocupadas (duas mãos)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Armadura\s*Nenhuma/ }))
    await userEvent.click(screen.getByRole('button', { name: /Armadura de Couro/ }))
    expect(screen.getByText('Pontuação 3 · Limiares 8/15 no seu nível')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Salvar equipamento' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/equipamento', expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ principal: 'montante', secundaria: null, armadura: 'couro' }) }))
  })
})

describe('Linha do tempo com mesa e plano', () => {
  const quadros = [{ tier: 2, opcoes: [] }]
  const eventos: EventoLinhaDoTempo[] = [
    { nivel: 1, tier: 1, status: 'feito', titulo: 'Criação', itens: [], quadros: [], planejado: false, bloqueado_pela_mesa: false },
    { nivel: 2, tier: 2, status: 'futuro', titulo: 'Nível 2', itens: ['Planejado: Avanço: +1 de Evasão'], quadros,
      planejado: true, bloqueado_pela_mesa: false },
  ]
  const proximo = (extra: Partial<ProximoNivel>): ProximoNivel => ({
    nivel: 2, tier: 2, nova_experiencia: true, limpa_marcas_tracos: false, experiencia_companheiro: false,
    avancos: 2, opcoes: [], tracos_marcados: [], treinos: 0, treinos_extra_com_subclasse: 0,
    limite_mesa: 2, bloqueado_pela_mesa: false, planejado: true, ...extra,
  })
  const ficha = { nome: 'Lia', experiencias: {}, cartas: [], cartas_ativas: [], companheiro: null } as unknown as Ficha

  it('nível travado pela mesa mostra o aviso, sem formulário', async () => {
    vi.stubGlobal('fetch', api({ '/personagens/p1/proximo-nivel': proximo({ limite_mesa: 1, bloqueado_pela_mesa: true }) }))
    montar(<LinhaDoTempo eventos={eventos} personagemId="p1" ficha={ficha} aoDesfazer={vi.fn()} desfazendo={false} />)
    expect(await screen.findByText('A mesa está no nível 1. O mestre ainda não liberou o nível 2.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Confirmar nível/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Aplicar o plano/ })).not.toBeInTheDocument()
  })

  it('nível planejado e liberado: aplicar o plano ou escolher outra coisa', async () => {
    const fetch = api({ '/personagens/p1/proximo-nivel': proximo({}) })
    vi.stubGlobal('fetch', fetch)
    montar(<LinhaDoTempo eventos={eventos} personagemId="p1" ficha={ficha} aoDesfazer={vi.fn()} desfazendo={false} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Aplicar o plano do nível 2' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/plano/aplicar', expect.objectContaining({ method: 'POST' }))
    await userEvent.click(screen.getByRole('button', { name: 'Escolher outra coisa' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/plano/2', expect.objectContaining({ method: 'DELETE' }))
    expect(screen.getByText('planejado')).toBeInTheDocument()
  })
})

describe('Foto', () => {
  it('recusa tipo errado na hora e envia imagem válida', async () => {
    const fetch = api({ '/imagens': { id: 'img1', url: '/imagens/img1' } })
    vi.stubGlobal('fetch', fetch)
    const aoMudar = vi.fn()
    montar(<EnviarFoto temFoto={false} aoMudar={aoMudar} />)
    const entrada = screen.getByLabelText('Arquivo da foto')
    await userEvent.upload(entrada, new File(['x'], 'nota.txt', { type: 'text/plain' }), { applyAccept: false })
    expect(screen.getByRole('alert')).toHaveTextContent('JPG, PNG ou WebP')
    expect(fetch).not.toHaveBeenCalled()
    await userEvent.upload(entrada, new File(['png'], 'foto.png', { type: 'image/png' }))
    await vi.waitFor(() => expect(aoMudar).toHaveBeenCalledWith('img1'))
    expect(fetch.mock.calls[0][1]?.body).toBeInstanceOf(FormData)
  })
})

describe('Trazer personagem para a mesa', () => {
  it('acima do nível da mesa, entra por cópia', async () => {
    const mesa = {
      id: 'm1', nome: 'Mesa', codigo_convite: 'ABC', medo_em_jogo: [], nivel_maximo: 2, meu_papel: 'jogador', sou_criador: false,
      permissoes_mestres: {}, minhas_permissoes: [], membros: [], personagens: [],
    } as unknown as Mesa
    const fetch = api({
      '/personagens': [{ id: 'p1', nome: 'Lia', nivel: 5, classe: 'x', mesa_id: null, foto: null }],
      '/personagens/p1/copia': { id: 'p2', ficha: {} },
      '/mesas/m1/revelado': { combate: [], npcs: [] },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaGeral mesa={mesa} />)
    await userEvent.selectOptions(await screen.findByLabelText('Trazer um personagem seu'), 'p1')
    expect(screen.getByText(/acima do nível da mesa \(2\)/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Trazer uma cópia' }))
    expect(fetch).toHaveBeenCalledWith('/api/personagens/p1/copia', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ mesa_id: 'm1' }) }))
    // jogador vê o nível da mesa, sem poder mudar
    expect(screen.queryByLabelText('Nível máximo')).not.toBeInTheDocument()
  })
})

describe('Ficha simplificada dos outros personagens', () => {
  it('tocar no personagem da mesa abre quem é e PV, PF e Esperança', async () => {
    const mesa = {
      id: 'm1', nome: 'Mesa', codigo_convite: 'ABC', medo_em_jogo: [], nivel_maximo: 2, meu_papel: 'jogador', sou_criador: false,
      permissoes_mestres: {}, minhas_permissoes: [], membros: [],
      personagens: [{ id: 'lira', nome: 'Lira', nivel: 2, classe: 'bardo', jogador: 'Bia', dono_id: 'b', foto: null }],
    } as unknown as Mesa
    const fetch = api({
      '/personagens': [],
      '/mesas/m1/revelado': { combate: [], npcs: [] },
      '/mesas/m1/personagens/lira/resumo': {
        id: 'lira', nome: 'Lira', foto: null, jogador: 'Bia', nivel: 2, classe: 'Bardo', subclasse: 'Trovador',
        estagio_subclasse: 'FUNDAMENTAL', multiclasse: null, ancestralidade: 'Fauno', comunidade: 'Aristocrática',
        pv_max: 6, pv_marcados: 2, estresse_max: 6, estresse_marcado: 1, esperanca: 3, esperanca_max: 6,
      },
    })
    vi.stubGlobal('fetch', fetch)
    montar(<AbaGeral mesa={mesa} />)
    await userEvent.click(await screen.findByRole('button', { name: /Lira/ }))
    expect(await screen.findByText('Vida: 4/6 PV')).toBeInTheDocument()
    expect(screen.getByText('Fadiga: 5/6 PF')).toBeInTheDocument()
    expect(screen.getByText('Esperança: 3/6')).toBeInTheDocument()
    expect(screen.getByText(/Fauno · Aristocrática · jogado por Bia/)).toBeInTheDocument()
  })
})
