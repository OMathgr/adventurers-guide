import { describe, expect, it } from 'vitest'

import type { Cartao } from '../api/tipos'
import { layoutDaCampanha, paraArestas, paraNos, paraQuadro } from './quadro'

const nota = (id: string, x: number, y: number): Cartao =>
  ({ id, tipo: 'nota', x, y, titulo: id, texto: '', cor: 'padrao', revelado: false }) as Cartao

describe('quadro', () => {
  it('vai e volta entre a API e o React Flow sem perder nada', () => {
    const cartoes = [nota('a', 10, 20), { ...nota('b', 0, 0), tipo: 'item', item_tipo: 'npc', item_id: 'n1' } as Cartao]
    // de baixo de um para o topo do outro: o lado de cada ponta também vai e volta
    const ligacoes = [{ id: 'l1', de: 'a', para: 'b', rotulo: 'trai', de_ponto: 'baixo', para_ponto: 'topo' }]
    const nos = paraNos(cartoes, { 'npc:n1': { nome: 'Marlowe', foto: null, descricao: '', existe: true } })
    expect(nos[1].data.item?.nome).toBe('Marlowe')
    expect(nos[1].type).toBe('item')
    nos[0].position = { x: 15.6, y: 20 }   // arrastou
    const volta = paraQuadro(nos, paraArestas(ligacoes))
    expect(volta.cartoes[0]).toMatchObject({ id: 'a', x: 16, y: 20 })
    expect(volta.ligacoes).toEqual(ligacoes)
  })

  it('campanha: uma região por sessão, sem sobrepor, com o título em cima', () => {
    const { nos, arestas } = layoutDaCampanha([
      { sessao_id: 's1', titulo: 'A ponte', cartoes: [nota('a', 500, 300), nota('b', 800, 300)], ligacoes: [{ id: 'l', de: 'a', para: 'b', rotulo: '' }], itens: {} },
      { sessao_id: 's2', titulo: 'A torre', cartoes: [nota('a', -50, -50)], ligacoes: [], itens: {} },
    ], 100)
    const pos = Object.fromEntries(nos.map((n) => [n.id, n.position]))
    expect(pos['s1:titulo']).toEqual({ x: 0, y: 0 })
    expect(pos['s1:a']).toEqual({ x: 0, y: 70 })           // a região começa no canto
    expect(pos['s1:b']).toEqual({ x: 300, y: 70 })         // e mantém as distâncias
    // a segunda região vem depois da largura da primeira (300 + 220) + espaço
    expect(pos['s2:titulo']).toEqual({ x: 620, y: 0 })
    expect(pos['s2:a']).toEqual({ x: 620, y: 70 })         // ids repetidos entre sessões não colidem
    expect(arestas).toEqual([expect.objectContaining({ id: 's1:l', source: 's1:a', target: 's1:b' })])
  })
})
