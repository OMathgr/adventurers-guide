import { describe, expect, it } from 'vitest'

import { decompor, formatarOuro, separar } from './ouro'

describe('ouro', () => {
  it('separa em baú, bolsas e punhados', () => {
    expect(decompor(123)).toEqual({ baus: 1, bolsas: 2, punhados: 3 })
    expect(decompor(9)).toEqual({ baus: 0, bolsas: 0, punhados: 9 })
  })

  it('escreve como na ficha', () => {
    expect(formatarOuro(0)).toBe('nada')
    expect(formatarOuro(1)).toBe('1 punhado')
    expect(formatarOuro(20)).toBe('2 bolsas')
    expect(formatarOuro(111)).toBe('1 baú, 1 bolsa e 1 punhado')
    expect(formatarOuro(2, 5)).toBe('2 punhados e 5 moedas')
    expect(formatarOuro(0, 1)).toBe('1 moeda')
  })

  it('separa um valor em moedas para a API', () => {
    expect(separar(123)).toEqual({ punhados: 12, moedas: 3 })
    expect(separar(-15)).toEqual({ punhados: -1, moedas: -5 })
  })
})
