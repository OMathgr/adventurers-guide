// Telas de entrar e de criar conta.
import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'

import { useAutenticacao } from '../auth/Autenticacao'
import { Logo } from '../componentes/Layout'
import { Aviso, Botao, Campo } from '../componentes/ui'

/** Para onde voltar depois de entrar (ex.: link de convite aberto sem login). */
function useDestino(): string {
  const estado = useLocation().state as { de?: string } | null
  return estado?.de ?? '/personagens'
}

function Moldura({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex justify-center"><Logo /></div>
        <div className="rounded-2xl border border-borda bg-superficie p-6">
          <h1 className="mb-4 text-xl">{titulo}</h1>
          {children}
        </div>
      </div>
    </div>
  )
}

export function Entrar() {
  const { logado, entrar } = useAutenticacao()
  const navegar = useNavigate()
  const [erro, setErro] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)

  const destino = useDestino()

  if (logado) return <Navigate to={destino} replace />

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const dados = new FormData(e.currentTarget)
    setEnviando(true)
    setErro(null)
    try {
      await entrar(String(dados.get('email')), String(dados.get('senha')))
      navegar(destino, { replace: true })
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Moldura titulo="Entrar">
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="E-mail" name="email" type="email" autoComplete="email" required />
        <Campo rotulo="Senha" name="senha" type="password" autoComplete="current-password" required />
        <Aviso erro={erro} />
        <Botao type="submit" disabled={enviando} className="w-full">{enviando ? 'Entrando…' : 'Entrar'}</Botao>
      </form>
      <p className="mt-4 text-center text-sm text-texto-suave">
        Novo por aqui? <Link to="/cadastro" state={{ de: destino }} className="text-esperanca hover:underline">Crie sua conta</Link>
      </p>
    </Moldura>
  )
}

export function Cadastro() {
  const { logado, cadastrar } = useAutenticacao()
  const navegar = useNavigate()
  const [erro, setErro] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)

  const destino = useDestino()

  if (logado) return <Navigate to={destino} replace />

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const dados = new FormData(e.currentTarget)
    setEnviando(true)
    setErro(null)
    try {
      await cadastrar({
        email: String(dados.get('email')),
        nome: String(dados.get('nome')),
        senha: String(dados.get('senha')),
      })
      navegar(destino, { replace: true })
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Moldura titulo="Criar conta">
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="Seu nome" name="nome" autoComplete="name" required maxLength={120} />
        <Campo rotulo="E-mail" name="email" type="email" autoComplete="email" required />
        <Campo rotulo="Senha" name="senha" type="password" autoComplete="new-password" required
          minLength={8} dica="Pelo menos 8 caracteres." />
        <Aviso erro={erro} />
        <Botao type="submit" disabled={enviando} className="w-full">{enviando ? 'Criando…' : 'Criar conta'}</Botao>
      </form>
      <p className="mt-4 text-center text-sm text-texto-suave">
        Já tem conta? <Link to="/entrar" state={{ de: destino }} className="text-esperanca hover:underline">Entrar</Link>
      </p>
    </Moldura>
  )
}
