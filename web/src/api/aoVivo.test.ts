import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import { aplicarAviso } from './aoVivo'

/** Um cliente com algumas consultas em cache, para ver quais ficam "velhas". */
function cliente() {
  const c = new QueryClient()
  for (const chave of [
    ['mesas'], ['mesas', 'm1'], ['mesas', 'm1', 'revelado'], ['mesas', 'm1', 'sessoes', 's1', 'quadro'],
    ['mesas', 'm2'], ['personagens'], ['personagens', 'p1', 'ficha'], ['personagens', 'p2', 'ficha'],
    ['mesas', 'm1', 'personagens', 'p1'],
  ]) c.setQueryData(chave, {})
  return c
}

const velhas = (c: QueryClient) =>
  c.getQueryCache().getAll().filter((q) => q.state.isInvalidated).map((q) => q.queryKey.join('/')).sort()

describe('avisos ao vivo', () => {
  it('mesa: invalida tudo daquela mesa (e a lista), nada de outra mesa', () => {
    const c = cliente()
    aplicarAviso(c, { tipo: 'mesa', id: 'm1' })
    expect(velhas(c)).toEqual(['mesas', 'mesas/m1', 'mesas/m1/personagens/p1', 'mesas/m1/revelado',
      'mesas/m1/sessoes/s1/quadro'])
  })

  it('personagem: a ficha dele, a lista e o que a mesa mostra dele', () => {
    const c = cliente()
    aplicarAviso(c, { tipo: 'personagem', id: 'p1', mesa_id: 'm1' })
    expect(velhas(c)).toEqual(['mesas/m1', 'mesas/m1/personagens/p1', 'personagens', 'personagens/p1/ficha'])
  })
})
