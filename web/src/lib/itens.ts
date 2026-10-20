// Itens criados pelo mestre (motor/itens_proprios.py): valores iniciais por
// tipo, os bônus que a ficha aplica e o resumo de uma linha. As regras
// (limites, o que vale em cada tipo) são do motor; a tela só guia.
import type { Arma, Armadura, Caracteristica, Item, ItemProprio, Modificador, TipoProprio } from '../api/tipos'
import { NOME_ALCANCE, NOME_TIPO_DANO, NOME_TRACO } from './rotulos'

export const NOME_TIPO_PROPRIO: Record<TipoProprio, string> = {
  COMUM: 'Item comum', CONSUMIVEL: 'Consumível', ARMA: 'Arma', ARMADURA: 'Armadura',
}

const BASE: ItemProprio = {
  tipo: 'COMUM', nome: '', descricao: '', tier: 1, categoria: 'PRIMARY_PHYSICAL', traco: 'STRENGTH', alcance: 'MELEE',
  dado: 'd8', modificador_dano: 0, tipo_dano: 'PHYSICAL', duas_maos: false, limiar_maior: 5, limiar_grave: 11,
  pontuacao: 3, limpa_pv: null, limpa_pf: null, ganha_esperanca: null, marca_pf: 0, escolha: false,
  caracteristicas: [], id: '',
}

export const itemEmBranco = (tipo: TipoProprio): ItemProprio => ({ ...BASE, tipo })

/** Começar de um item do SRD: copia os números e as características. */
export function deArma(a: Arma): ItemProprio {
  return { ...BASE, tipo: 'ARMA', nome: a.nome, tier: a.tier, categoria: a.categoria, traco: a.traco,
    alcance: a.alcance, dado: a.dado, modificador_dano: a.modificador_dano, tipo_dano: a.tipo_dano,
    duas_maos: a.duas_maos, caracteristicas: structuredClone(a.caracteristicas ?? []) }
}

export function deArmadura(a: Armadura): ItemProprio {
  return { ...BASE, tipo: 'ARMADURA', nome: a.nome, tier: a.tier, limiar_maior: a.limiar_maior,
    limiar_grave: a.limiar_grave, pontuacao: a.pontuacao, caracteristicas: structuredClone(a.caracteristicas ?? []) }
}

export function deItem(i: Item): ItemProprio {
  const e = i.efeito
  return { ...BASE, tipo: i.tipo === 'CONSUMIVEL' ? 'CONSUMIVEL' : 'COMUM', nome: i.nome, descricao: i.texto ?? '',
    limpa_pv: e?.limpa_pv ?? null, limpa_pf: e?.limpa_pf ?? null, ganha_esperanca: e?.ganha_esperanca ?? null,
    marca_pf: e?.marca_pf ?? 0, escolha: e?.escolha ?? false }
}

/** Onde um bônus fixo pode ir (o motor aplica na ficha). Ataque só em armas. */
export const ALVOS_DE_BONUS: [alvo: string, nome: string, soArma?: boolean][] = [
  ['EVASAO', 'Evasão'], ['PONTUACAO_ARMADURA', 'Pontuação de Armadura'], ['LIMIARES', 'Limiares (maior e grave)'],
  ['LIMIAR_GRAVE', 'Limiar grave'], ['PV', 'Pontos de Vida (espaços)'], ['ESTRESSE', 'Fadiga (espaços)'],
  ['CONJURACAO', 'Testes de conjuração'], ['ATAQUE', 'Ataques com esta arma', true],
  ...Object.entries(NOME_TRACO).map(([t, nome]): [string, string] => [t, nome]),
]
const NOME_ALVO = Object.fromEntries(ALVOS_DE_BONUS.map(([a, n]) => [a, n]))

export function descreverBonus(m: Modificador): string {
  const alvo = m.alvo === 'DANO' ? 'dano desta arma' : NOME_ALVO[m.alvo] ?? m.alvo
  if (m.igual_a) return `${alvo} + ${m.igual_a === 'NIVEL' ? 'seu nível' : NOME_TRACO[m.igual_a as keyof typeof NOME_TRACO]}`
  return `${m.valor >= 0 ? '+' : ''}${m.valor} ${alvo}`
}

/** Características das armas e armaduras do SRD, sem repetir, para copiar. */
export function caracteristicasDoSrd(pecas: { caracteristicas?: Caracteristica[] }[]): Caracteristica[] {
  const vistas = new Map<string, Caracteristica>()
  for (const p of pecas) for (const c of p.caracteristicas ?? []) vistas.set(`${c.nome}|${c.descricao}`, c)
  return [...vistas.values()].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
}

/** Uma linha com os números do item ("Força · Corpo a corpo · d10+2 físico"). */
export function resumoDoItem(i: ItemProprio): string {
  if (i.tipo === 'ARMA') {
    const dano = `${i.dado}${i.modificador_dano ? `${i.modificador_dano > 0 ? '+' : ''}${i.modificador_dano}` : ''}`
    return [i.categoria === 'SECONDARY' ? 'Secundária' : i.categoria === 'PRIMARY_MAGIC' ? 'Principal mágica' : 'Principal',
      NOME_TRACO[i.traco], NOME_ALCANCE[i.alcance] ?? i.alcance, `${dano} ${NOME_TIPO_DANO[i.tipo_dano]}`,
      ...(i.duas_maos ? ['duas mãos'] : [])].join(' · ')
  }
  if (i.tipo === 'ARMADURA') return `Pontuação ${i.pontuacao} · Limiares base ${i.limiar_maior}/${i.limiar_grave}`
  if (i.tipo === 'CONSUMIVEL') {
    const quanto = (q: string) => (q === 'tudo' ? 'todos os' : q)
    const partes = [
      ...(i.marca_pf ? [`marca ${i.marca_pf} PF`] : []),
      ...(i.limpa_pv && i.limpa_pf && i.escolha ? [`limpa ${quanto(i.limpa_pv)} PV ou ${quanto(i.limpa_pf)} PF`] : [
        ...(i.limpa_pv ? [`limpa ${quanto(i.limpa_pv)} PV`] : []),
        ...(i.limpa_pf ? [`limpa ${quanto(i.limpa_pf)} PF`] : []),
      ]),
      ...(i.ganha_esperanca ? [`ganha ${i.ganha_esperanca} de Esperança`] : []),
    ]
    return partes.length ? `Ao usar: ${partes.join(', ')}.` : 'Consumível (o efeito fica na descrição).'
  }
  return 'Item comum'
}
