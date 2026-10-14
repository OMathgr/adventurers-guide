// Quem está logado. Guarda o token (localStorage), busca /auth/eu e oferece
// entrar, cadastrar e sair. Se a API disser que o token venceu, desloga.
// Enquanto a pessoa usa o app, o login se renova; parada 2 h, sai (sessao.ts).
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { chamar, quandoExpirar, token } from '../api/cliente'
import type { Token, Usuario } from '../api/tipos'
import {
  atividade, AVISO_ANTES_MS, decidir, formatarContagem, motivoDaSaida, msParaSair, prazosDoToken,
} from './sessao'

const INTERACOES = ['pointerdown', 'keydown', 'wheel', 'touchstart'] as const
// a cada segundo: a contagem do aviso desce de segundo em segundo (a conta é barata)
const VERIFICAR_A_CADA_MS = 1000

/** Aviso dos últimos 10 minutos antes de cair por inatividade: a contagem e a
    barra descem até zero. Qualquer interação (ou o botão) conta como uso. */
function AvisoDeInatividade({ restante }: { restante: number }) {
  const fracao = Math.max(0, Math.min(1, restante / AVISO_ANTES_MS))
  return (
    <div role="alert" className="fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:bottom-4 sm:left-auto sm:right-4 sm:w-96 sm:px-0 sm:pb-0">
      <div className="overflow-hidden rounded-2xl border border-esperanca/60 bg-superficie shadow-lg">
        <div className="space-y-2 p-4">
          <p className="font-semibold">Você está sem usar o app</p>
          <p className="text-sm text-texto-suave">
            Por segurança, vamos desconectar em{' '}
            <b aria-hidden className="font-titulo text-lg tabular-nums text-esperanca">{formatarContagem(restante)}</b>
            <span className="sr-only">alguns minutos</span>.
          </p>
          <button type="button"
            className="w-full rounded-lg bg-esperanca px-4 py-2 text-sm font-semibold text-sobre-esperanca hover:bg-esperanca-forte">
            Continuar conectado
          </button>
        </div>
        <div className="h-1.5 bg-borda" aria-hidden>
          <div className="h-full bg-esperanca transition-[width] duration-1000 ease-linear" style={{ width: `${fracao * 100}%` }} />
        </div>
      </div>
    </div>
  )
}

type Autenticacao = {
  logado: boolean
  usuario: Usuario | undefined
  entrar: (email: string, senha: string) => Promise<void>
  /** Token que já veio pronto (login com o Google, senha redefinida). */
  entrarComToken: (accessToken: string) => void
  cadastrar: (dados: { email: string; nome: string; senha: string }) => Promise<void>
  sair: () => void
}

const Contexto = createContext<Autenticacao | null>(null)

export function ProvedorAutenticacao({ children }: { children: ReactNode }) {
  const cliente = useQueryClient()
  const [tokenAtual, setTokenAtual] = useState(token.ler())
  // ms até cair por inatividade, só nos últimos 10 minutos (senão null)
  const [restante, setRestante] = useState<number | null>(null)

  const usuario = useQuery({
    queryKey: ['eu', tokenAtual],
    queryFn: () => chamar<Usuario>('/auth/eu'),
    enabled: !!tokenAtual,
    staleTime: Infinity,
  })

  const sair = useCallback(() => {
    token.apagar()
    setTokenAtual(null)
    cliente.clear()   // nada de dados de um usuário vazando para o próximo
  }, [cliente])

  useEffect(() => quandoExpirar(sair), [sair])

  // Renovação por uso e saída por inatividade.
  useEffect(() => {
    if (!tokenAtual) return
    let renovando = false
    let proximaTentativa = 0   // depois de uma falha, espera 30 s (ou a próxima interação)
    function verificar() {
      const atual = token.ler()
      if (!atual) return
      const agora = Date.now()
      const falta = msParaSair(atual, atividade.ler(), agora)
      setRestante(falta !== null && falta <= AVISO_ANTES_MS ? falta : null)
      const decisao = decidir(atual, atividade.ler(), agora)
      if (decisao === 'sair') {
        const prazos = prazosDoToken(atual)
        const horas = prazos ? Math.round((prazos.vence - prazos.emitido) / 3_600_000) : 2
        motivoDaSaida.gravar(`Você ficou ${horas} ${horas === 1 ? 'hora' : 'horas'} sem usar o app. Entre de novo.`)
        sair()
      } else if (decisao === 'renovar' && !renovando && agora >= proximaTentativa) {
        renovando = true
        // só troca o token guardado: a tela não precisa recarregar nada
        chamar<Token>('/auth/renovar', { corpo: {} })
          .then((novo) => { if (token.ler()) token.gravar(novo.access_token) })
          .catch(() => { proximaTentativa = Date.now() + 30_000 })   // 401 já desloga pelo cliente
          .finally(() => { renovando = false })
      }
    }
    function usou() {
      proximaTentativa = 0
      atividade.marcar()
      verificar()
    }
    function outraAba(e: StorageEvent) {
      if (e.key === 'ag.token' && e.newValue === null) sair()   // saiu em outra aba
    }
    atividade.marcar(Date.now(), true)   // entrar (ou abrir o app) conta como uso
    INTERACOES.forEach((ev) => window.addEventListener(ev, usou, { passive: true }))
    window.addEventListener('storage', outraAba)
    const relogio = window.setInterval(verificar, VERIFICAR_A_CADA_MS)
    verificar()   // já ao abrir (ex.: voltou de horas com o computador hibernando)
    return () => {
      INTERACOES.forEach((ev) => window.removeEventListener(ev, usou))
      window.removeEventListener('storage', outraAba)
      window.clearInterval(relogio)
      setRestante(null)
    }
  }, [tokenAtual, sair])

  const entrar = useCallback(async (email: string, senha: string) => {
    const t = await chamar<Token>('/auth/login', { formulario: { username: email, password: senha } })
    token.gravar(t.access_token)
    setTokenAtual(t.access_token)
  }, [])

  const entrarComToken = useCallback((accessToken: string) => {
    token.gravar(accessToken)
    setTokenAtual(accessToken)
  }, [])

  const cadastrar = useCallback(async (dados: { email: string; nome: string; senha: string }) => {
    await chamar<Usuario>('/auth/cadastro', { corpo: dados })
    await entrar(dados.email, dados.senha)
  }, [entrar])

  const valor = useMemo(
    () => ({ logado: !!tokenAtual, usuario: usuario.data, entrar, entrarComToken, cadastrar, sair }),
    [tokenAtual, usuario.data, entrar, entrarComToken, cadastrar, sair],
  )
  return (
    <Contexto.Provider value={valor}>
      {children}
      {tokenAtual && restante !== null && <AvisoDeInatividade restante={restante} />}
    </Contexto.Provider>
  )
}

export function useAutenticacao(): Autenticacao {
  const valor = useContext(Contexto)
  if (!valor) throw new Error('useAutenticacao fora do ProvedorAutenticacao')
  return valor
}
