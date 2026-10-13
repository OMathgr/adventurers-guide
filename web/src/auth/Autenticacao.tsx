// Quem está logado. Guarda o token (localStorage), busca /auth/eu e oferece
// entrar, cadastrar e sair. Se a API disser que o token venceu, desloga.
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { chamar, quandoExpirar, token } from '../api/cliente'
import type { Token, Usuario } from '../api/tipos'

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
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function useAutenticacao(): Autenticacao {
  const valor = useContext(Contexto)
  if (!valor) throw new Error('useAutenticacao fora do ProvedorAutenticacao')
  return valor
}
