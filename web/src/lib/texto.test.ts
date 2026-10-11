import { describe, expect, it } from 'vitest'

import { blocos, trechos } from './texto'

describe('trechos', () => {
  it('separa negrito e itálico', () => {
    expect(trechos('**Gaste 1 Ponto de Medo** e fique _Oculto_.')).toEqual([
      { texto: 'Gaste 1 Ponto de Medo', negrito: true },
      { texto: ' e fique ' },
      { texto: 'Oculto', italico: true },
      { texto: '.' },
    ])
  })

  it('aceita itálico dentro de negrito', () => {
    expect(trechos('**_Contido_**')).toEqual([{ texto: 'Contido', italico: true, negrito: true }])
  })

  it('não confunde sublinhado no meio de palavra nem marca sem par', () => {
    expect(trechos('srd_acid_burrower e **solto')).toEqual([{ texto: 'srd_acid_burrower e **solto' }])
  })
})

describe('blocos', () => {
  it('reconhece parágrafos e listas', () => {
    const b = blocos('Role um d6:\n\n- 1. _Fogo_\n- 2. Gelo\n\nDepois descanse.')
    expect(b.map((x) => x.tipo)).toEqual(['paragrafo', 'lista', 'paragrafo'])
    expect(b[1]).toMatchObject({ tipo: 'lista', itens: [[{ texto: '1. ' }, { texto: 'Fogo', italico: true }], [{ texto: '2. Gelo' }]] })
  })
})
