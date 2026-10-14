// Conflito de edição: alguém salvou o mesmo formulário antes (ver api/concorrencia.py).
import { ErroApi } from '../api/cliente'

export function ehConflito(erro: unknown): boolean {
  return erro instanceof ErroApi && erro.status === 409 && erro.tipo === 'conflito'
}

/** O erro para o <Aviso> comum: o conflito tem o aviso próprio (AvisoDeConflito). */
export const semConflito = (erro: unknown) => (ehConflito(erro) ? null : erro)
