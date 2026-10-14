// Sessão por uso: enquanto a pessoa usa o app (clica, toca, digita, rola), o
// login se renova sozinho; parada pela validade do token (2 h), sai.
//
// "Uso" é só interação de verdade: atualizações ao vivo, que chegam quando os
// outros jogam, não contam (senão uma aba esquecida na mesa nunca cairia). A
// última interação fica no localStorage, compartilhada entre as abas: usar uma
// aba mantém todas logadas (o token também é um só).

const CHAVE_ATIVIDADE = 'ag.atividade'
const CHAVE_MOTIVO = 'ag.motivo-saida'

/** Renovar só se o token tiver pelo menos esta idade (evita uma chamada a cada clique). */
export const RENOVAR_APOS_MS = 5 * 60 * 1000
/** Gravar a atividade no máximo uma vez a cada… */
const GRAVAR_A_CADA_MS = 30 * 1000

export type Decisao = 'renovar' | 'sair' | 'nada'

/** iat e exp (em ms) de um JWT, sem conferir a assinatura (quem confere é a API). */
export function prazosDoToken(jwt: string): { emitido: number; vence: number } | null {
  try {
    const meio = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const dados = JSON.parse(atob(meio + '='.repeat((4 - (meio.length % 4)) % 4))) as { iat?: number; exp?: number }
    if (typeof dados.iat !== 'number' || typeof dados.exp !== 'number') return null
    return { emitido: dados.iat * 1000, vence: dados.exp * 1000 }
  } catch {
    return null
  }
}

/** Faltando isto para cair por inatividade, aparece o aviso com a contagem. */
export const AVISO_ANTES_MS = 10 * 60 * 1000

/** Quanto falta (ms) para cair: o que vier primeiro entre o token vencer e
    passar a validade inteira sem uso. Null se o token não tiver prazos legíveis. */
export function msParaSair(jwt: string, ultimaAtividade: number, agora: number): number | null {
  const prazos = prazosDoToken(jwt)
  if (!prazos) return null
  const validade = prazos.vence - prazos.emitido
  return Math.max(0, Math.min(prazos.vence, ultimaAtividade + validade) - agora)
}

/** "9:05" */
export function formatarContagem(ms: number): string {
  const segundos = Math.ceil(ms / 1000)
  return `${Math.floor(segundos / 60)}:${String(segundos % 60).padStart(2, '0')}`
}

/** O que fazer agora, dado o token, a última interação e o relógio (tudo em ms). */
export function decidir(jwt: string, ultimaAtividade: number, agora: number): Decisao {
  const prazos = prazosDoToken(jwt)
  if (!prazos) return 'nada'   // token sem prazo legível: a API decide no próximo pedido
  const validade = prazos.vence - prazos.emitido
  if (agora >= prazos.vence || agora - ultimaAtividade >= validade) return 'sair'
  if (ultimaAtividade > prazos.emitido && agora - prazos.emitido >= RENOVAR_APOS_MS) return 'renovar'
  return 'nada'
}

export const atividade = {
  ler(): number {
    try { return Number(localStorage.getItem(CHAVE_ATIVIDADE)) || 0 } catch { return 0 }
  },
  /** Grava "agora" (com folga de 30 s entre gravações, para não escrever a cada movimento). */
  marcar(agora = Date.now(), forcar = false) {
    if (!forcar && agora - atividade.ler() < GRAVAR_A_CADA_MS) return
    try { localStorage.setItem(CHAVE_ATIVIDADE, String(agora)) } catch { /* modo privado */ }
  },
}

/** Por que saiu (mostrado na tela de entrar, uma vez). */
export const motivoDaSaida = {
  gravar(texto: string) {
    try { sessionStorage.setItem(CHAVE_MOTIVO, texto) } catch { /* modo privado */ }
  },
  tirar(): string | null {
    try {
      const texto = sessionStorage.getItem(CHAVE_MOTIVO)
      sessionStorage.removeItem(CHAVE_MOTIVO)
      return texto
    } catch {
      return null
    }
  },
}
