// Conversões entre o quadro da API (cartões e ligações) e o React Flow (nós e
// arestas), e o layout do quadro da campanha. Sem regras de jogo: o que pode ou
// não ir no quadro, e o que os jogadores veem, é decidido no motor.
import type { Edge, Node } from '@xyflow/react'

import type { Cartao, ItemNoQuadro, Ligacao } from '../api/tipos'

export type DadosDoCartao = { cartao: Cartao; item?: ItemNoQuadro }
export type NoDoQuadro = Node<DadosDoCartao>

/** Tamanho aproximado de um cartão, para o layout da campanha. */
export const LARGURA_CARTAO = 220
export const ALTURA_CARTAO = 130

export const chaveDoItem = (c: Pick<Cartao, 'item_tipo' | 'item_id'>) => `${c.item_tipo}:${c.item_id}`

export function paraNos(cartoes: Cartao[], itens: Record<string, ItemNoQuadro>, prefixo = '', desloca = { x: 0, y: 0 }): NoDoQuadro[] {
  return cartoes.map((c) => ({
    id: prefixo + c.id,
    type: c.tipo,
    position: { x: (c.x ?? 0) + desloca.x, y: (c.y ?? 0) + desloca.y },
    data: { cartao: c, item: c.tipo === 'item' ? itens[chaveDoItem(c)] : undefined },
  }))
}

export function paraArestas(ligacoes: Ligacao[], prefixo = ''): Edge[] {
  return ligacoes.map((l) => ({
    id: prefixo + l.id, source: prefixo + l.de, target: prefixo + l.para,
    // o lado de cada cartão onde a seta encosta (id do ponto de ligação)
    sourceHandle: l.de_ponto ?? null, targetHandle: l.para_ponto ?? null,
    label: l.rotulo || undefined, data: { rotulo: l.rotulo ?? '' },
  }))
}

/** Volta para o formato da API (a posição do nó vira x/y do cartão). */
export function paraQuadro(nos: NoDoQuadro[], arestas: Edge[]): { cartoes: Cartao[]; ligacoes: Ligacao[] } {
  return {
    cartoes: nos.map((n) => ({ ...n.data.cartao, id: n.id, x: Math.round(n.position.x), y: Math.round(n.position.y) })),
    ligacoes: arestas.map((a) => ({
      id: a.id, de: a.source, para: a.target, rotulo: String((a.data as { rotulo?: string } | undefined)?.rotulo ?? ''),
      de_ponto: a.sourceHandle ?? null, para_ponto: a.targetHandle ?? null,
    })),
  }
}

type Regiao = { sessao_id: string; titulo: string; cartoes: Cartao[]; ligacoes: Ligacao[]; itens: Record<string, ItemNoQuadro> }

/** Quadro da campanha: uma região por sessão, lado a lado, cada uma com o
    título em cima. Os ids ganham o prefixo da sessão (podem se repetir entre quadros). */
export function layoutDaCampanha(regioes: Regiao[], espaco = 160): { nos: Node[]; arestas: Edge[] } {
  const nos: Node[] = []
  const arestas: Edge[] = []
  let x = 0
  for (const r of regioes) {
    const xs = r.cartoes.map((c) => c.x ?? 0)
    const ys = r.cartoes.map((c) => c.y ?? 0)
    const minX = Math.min(...xs), minY = Math.min(...ys)
    const largura = Math.max(...xs) - minX + LARGURA_CARTAO
    const prefixo = `${r.sessao_id}:`
    nos.push({ id: `${prefixo}titulo`, type: 'titulo', position: { x, y: 0 }, data: { titulo: r.titulo },
      draggable: false, selectable: false })
    nos.push(...paraNos(r.cartoes, r.itens, prefixo, { x: x - minX, y: 70 - minY }))
    arestas.push(...paraArestas(r.ligacoes, prefixo))
    x += Math.max(largura, LARGURA_CARTAO) + espaco
  }
  return { nos, arestas }
}
