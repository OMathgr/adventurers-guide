import { afterEach, describe, expect, it, vi } from 'vitest'

import { chamar, ErroApi, mensagemDeErro, quandoExpirar, token } from './cliente'

function responder(status: number, corpo: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
    new Response(corpo === undefined ? null : JSON.stringify(corpo), { status })))
}

afterEach(() => vi.unstubAllGlobals())

describe('cliente da API', () => {
  it('manda o token e o JSON', async () => {
    token.gravar('abc')
    responder(200, { ok: true })
    await chamar('/personagens', { corpo: { nome: 'Lira' } })
    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toBe('/api/personagens')
    expect(init.method).toBe('POST')
    expect(init.headers.Authorization).toBe('Bearer abc')
    expect(JSON.parse(init.body)).toEqual({ nome: 'Lira' })
  })

  it('transforma erro de regra em ErroApi com o tipo', async () => {
    responder(422, { detail: 'Distribua exatamente +2, +1, +1, +0, +0 e -1.', tipo: 'regra' })
    const erro = (await chamar('/personagens', { corpo: {} }).catch((e) => e)) as ErroApi
    expect(erro).toBeInstanceOf(ErroApi)
    expect(erro.status).toBe(422)
    expect(erro.tipo).toBe('regra')
    expect(erro.message).toMatch(/Distribua/)
  })

  it('avisa quando o token vence', async () => {
    token.gravar('vencido')
    const expirou = vi.fn()
    quandoExpirar(expirou)
    responder(401, { detail: 'Token inválido ou expirado.' })
    await chamar('/personagens').catch(() => {})
    expect(expirou).toHaveBeenCalled()
  })

  it('204 não tem corpo', async () => {
    responder(204, undefined)
    await expect(chamar('/personagens/x', { metodo: 'DELETE' })).resolves.toBeUndefined()
  })
})

describe('mensagens de erro', () => {
  it('lê a lista de validação do FastAPI', () => {
    const dados = { detail: [{ loc: ['body', 'senha'], msg: 'muito curta' }] }
    expect(mensagemDeErro(dados, 422)).toBe('senha: muito curta')
  })
})
