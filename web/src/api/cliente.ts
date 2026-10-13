// Cliente HTTP da API. Todas as chamadas passam por aqui: põe o token,
// converte JSON e transforma respostas de erro em ErroApi.

const BASE = '/api'   // em desenvolvimento o Vite encaminha para o FastAPI
const CHAVE_TOKEN = 'ag.token'

export class ErroApi extends Error {
  readonly status: number
  /** "regra" quando o motor recusou (ex.: atributos mal distribuídos). */
  readonly tipo?: string

  constructor(status: number, mensagem: string, tipo?: string) {
    super(mensagem)
    this.status = status
    this.tipo = tipo
  }
}

export const token = {
  ler: (): string | null => {
    try { return localStorage.getItem(CHAVE_TOKEN) } catch { return null }
  },
  gravar: (valor: string) => {
    try { localStorage.setItem(CHAVE_TOKEN, valor) } catch { /* modo privado */ }
  },
  apagar: () => {
    try { localStorage.removeItem(CHAVE_TOKEN) } catch { /* modo privado */ }
  },
}

/** Chamado quando a API responde 401 (token vencido): o AuthContext desloga. */
let aoExpirar: () => void = () => {}
export function quandoExpirar(callback: () => void) {
  aoExpirar = callback
}

type Opcoes = {
  metodo?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  corpo?: unknown
  formulario?: Record<string, string>
  /** Envio de arquivo (multipart); o navegador põe o Content-Type com o boundary. */
  multipart?: FormData
}

/** Endereço de uma foto enviada (para <img src>; a leitura não precisa de token). */
export const urlDaImagem = (id: string) => `${BASE}/imagens/${id}`

export async function chamar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const cabecalhos: Record<string, string> = {}
  const t = token.ler()
  if (t) cabecalhos.Authorization = `Bearer ${t}`

  let body: BodyInit | undefined
  if (opcoes.multipart) {
    body = opcoes.multipart
  } else if (opcoes.formulario) {
    body = new URLSearchParams(opcoes.formulario)
  } else if (opcoes.corpo !== undefined) {
    cabecalhos['Content-Type'] = 'application/json'
    body = JSON.stringify(opcoes.corpo)
  }

  const resposta = await fetch(BASE + caminho, {
    method: opcoes.metodo ?? (body ? 'POST' : 'GET'),
    headers: cabecalhos,
    body,
  })

  if (resposta.status === 204) return undefined as T
  const dados = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    if (resposta.status === 401 && t) aoExpirar()
    throw new ErroApi(resposta.status, mensagemDeErro(dados, resposta.status), dados?.tipo)
  }
  return dados as T
}

/** O FastAPI manda `detail` como texto (nossos erros) ou lista (validação). */
export function mensagemDeErro(dados: unknown, status: number): string {
  const detalhe = (dados as { detail?: unknown } | null)?.detail
  if (typeof detalhe === 'string') return detalhe
  if (Array.isArray(detalhe) && detalhe.length > 0) {
    const primeiro = detalhe[0] as { msg?: string; loc?: unknown[] }
    const campo = primeiro.loc?.slice(1).join('.')
    return campo ? `${campo}: ${primeiro.msg}` : (primeiro.msg ?? 'Dados inválidos.')
  }
  if (status >= 500) return 'O servidor teve um problema. Tente de novo em instantes.'
  return 'Algo deu errado.'
}
