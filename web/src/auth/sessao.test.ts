import { describe, expect, it } from 'vitest'

import { decidir, formatarContagem, msParaSair, prazosDoToken } from './sessao'

const MIN = 60 * 1000
const HORA = 60 * MIN

/** JWT falso com iat/exp (em segundos), como a API manda. */
function jwt(emitidoMs: number, validadeMs = 2 * HORA) {
  const corpo = btoa(JSON.stringify({ sub: 'u', iat: emitidoMs / 1000, exp: (emitidoMs + validadeMs) / 1000 }))
  return `x.${corpo.replace(/=+$/, '')}.y`
}

describe('sessão por uso', () => {
  const t0 = 1_800_000_000_000

  it('lê os prazos do token', () => {
    expect(prazosDoToken(jwt(t0))).toEqual({ emitido: t0, vence: t0 + 2 * HORA })
    expect(prazosDoToken('lixo')).toBeNull()
  })

  it('renova quando houve uso e o token já tem 5 minutos', () => {
    expect(decidir(jwt(t0), t0 + 3 * MIN, t0 + 4 * MIN)).toBe('nada')        // token novo demais
    expect(decidir(jwt(t0), t0 + 6 * MIN, t0 + 6 * MIN)).toBe('renovar')
    expect(decidir(jwt(t0), t0 - MIN, t0 + 30 * MIN)).toBe('nada')           // sem uso desde que foi emitido
  })

  it('sai depois de 2 horas sem uso', () => {
    expect(decidir(jwt(t0), t0, t0 + 2 * HORA - MIN)).toBe('nada')
    expect(decidir(jwt(t0), t0, t0 + 2 * HORA)).toBe('sair')
    // uso recente numa aba renovou o token (emitido depois): continua
    expect(decidir(jwt(t0 + 3 * HORA), t0 + 3 * HORA, t0 + 3 * HORA + 10 * MIN)).toBe('nada')
  })

  it('uma sessão longa de jogo nunca cai enquanto há uso', () => {
    let token = jwt(t0)
    for (let agora = t0; agora < t0 + 8 * HORA; agora += 10 * MIN) {   // 8 horas, um clique a cada 10 min
      const decisao = decidir(token, agora, agora)
      expect(decisao).not.toBe('sair')
      if (decisao === 'renovar') token = jwt(agora)
    }
  })
})

describe('aviso antes de cair', () => {
  const t0 = 1_800_000_000_000

  it('conta o que falta pelo que vier primeiro: token vencer ou 2 h sem uso', () => {
    expect(msParaSair(jwt(t0), t0, t0 + 110 * MIN)).toBe(10 * MIN)
    // usou há pouco, mas o token (não renovado) vence antes
    expect(msParaSair(jwt(t0), t0 + 100 * MIN, t0 + 115 * MIN)).toBe(5 * MIN)
    expect(msParaSair(jwt(t0), t0, t0 + 3 * HORA)).toBe(0)
  })

  it('mostra a contagem como no relógio', () => {
    expect(formatarContagem(10 * MIN)).toBe('10:00')
    expect(formatarContagem(9 * MIN + 5_000)).toBe('9:05')
    expect(formatarContagem(1)).toBe('0:01')
  })
})
