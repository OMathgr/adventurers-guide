import { describe, expect, it } from 'vitest'

import type { ProximoNivel, Subclasse } from '../api/tipos'
import {
  type AvancoMarcado, cartasNaCriacao, custoTotal, distribuicaoCompleta, podeMarcar, treinosExigidos,
  valoresRestantes,
} from './regras'

describe('distribuição de atributos', () => {
  it('tira cada valor usado só uma vez', () => {
    expect(valoresRestantes({ AGILITY: 1 })).toEqual([2, 1, 0, 0, -1])
    expect(valoresRestantes({ AGILITY: 1, STRENGTH: 1 })).toEqual([2, 0, 0, -1])
  })

  it('só fica completa com os seis atributos e todos os valores', () => {
    const quase = { AGILITY: 2, STRENGTH: 1, FINESSE: 1, INSTINCT: 0, PRESENCE: 0 }
    expect(distribuicaoCompleta(quase)).toBe(false)
    expect(distribuicaoCompleta({ ...quase, KNOWLEDGE: -1 })).toBe(true)
  })
})

const pv = { tier: 2, opcao: 'PV' as const, restantes: 2, custo: 1 }
const prof = { tier: 3, opcao: 'PROFICIENCIA' as const, restantes: 1, custo: 2 }
const marcar = (o: typeof pv | typeof prof, n: number): AvancoMarcado => ({ ...o, chave: String(n) })

describe('avanços', () => {
  it('soma o custo (Proficiência vale por dois)', () => {
    expect(custoTotal([marcar(pv, 1), marcar(prof, 2)])).toBe(3)
  })

  it('respeita os quadradinhos restantes e o limite de avanços', () => {
    expect(podeMarcar(pv, [marcar(pv, 1)], 2)).toBe(true)
    expect(podeMarcar(pv, [marcar(pv, 1), marcar(pv, 2)], 3)).toBe(false)   // sem quadradinho
    expect(podeMarcar(prof, [marcar(pv, 1)], 2)).toBe(false)                // custo não cabe
  })
})

describe('treinos do companheiro', () => {
  const proximo = { treinos: 1, treinos_extra_com_subclasse: 1 } as ProximoNivel
  it('somam o extra quando a subclasse é marcada', () => {
    expect(treinosExigidos(proximo, [marcar(pv, 1)])).toBe(1)
    const subclasse = { tier: 3, opcao: 'SUBCLASSE' as const, restantes: 1, custo: 1, chave: 's' }
    expect(treinosExigidos(proximo, [subclasse])).toBe(2)
  })
})

describe('cartas da criação', () => {
  const sub = (efeitos: (string | null)[]) => ({
    id: 's', nome: 'S', classe: 'WIZARD', traco_conjuracao: null,
    fundacao: efeitos.map((efeito, i) => ({ nome: `h${i}`, descricao: '', efeito })),
  }) as unknown as Subclasse

  it('são 2, mais uma por habilidade fundamental que dá carta (Promissor)', () => {
    expect(cartasNaCriacao(undefined)).toBe(2)
    expect(cartasNaCriacao(sub([null, null]))).toBe(2)
    expect(cartasNaCriacao(sub(['CARTA_EXTRA', null]))).toBe(3)
  })
})
