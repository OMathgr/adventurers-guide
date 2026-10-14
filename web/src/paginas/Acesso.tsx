// Telas de entrar (senha ou Google), criar conta e recuperar a senha.
import { useQuery } from '@tanstack/react-query'
import { type FormEvent, useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router'

import { chamar } from '../api/cliente'
import { useAutenticacao } from '../auth/Autenticacao'
import { motivoDaSaida } from '../auth/sessao'
import { Logo } from '../componentes/Layout'
import { Aviso, Botao, Campo } from '../componentes/ui'
import { useInstalar } from '../lib/pwa'

/** Para onde voltar depois de entrar (ex.: link de convite aberto sem login). */
function useDestino(): string {
  const estado = useLocation().state as { de?: string } | null
  return estado?.de ?? '/personagens'
}

// O login com o Google sai do app e volta: o destino fica guardado no navegador.
const CHAVE_DESTINO = 'ag.destino'

function useProvedores() {
  return useQuery({
    queryKey: ['auth', 'provedores'],
    queryFn: () => chamar<{ google: boolean }>('/auth/provedores'),
    staleTime: Infinity,
  })
}

function BotaoGoogle({ destino }: { destino: string }) {
  const provedores = useProvedores()
  if (!provedores.data?.google) return null
  return (
    <>
      <div className="my-4 flex items-center gap-3 text-xs text-texto-suave">
        <span className="h-px flex-1 bg-borda" />ou<span className="h-px flex-1 bg-borda" />
      </div>
      <a href="/api/auth/google"
        onClick={() => { try { sessionStorage.setItem(CHAVE_DESTINO, destino) } catch { /* modo privado */ } }}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-borda bg-fundo px-4 py-2 text-sm font-medium hover:border-texto-suave">
        <svg viewBox="0 0 48 48" className="h-4 w-4" aria-hidden>
          <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
          <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
          <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
          <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
        </svg>
        Entrar com o Google
      </a>
    </>
  )
}

function Moldura({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  const instalar = useInstalar()
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex justify-center"><Logo /></div>
        {instalar && (
          <button type="button" onClick={instalar}
            className="mx-auto block rounded-full border border-esperanca/60 px-4 py-1.5 text-sm text-esperanca hover:bg-esperanca/10">
            Instalar o app no celular
          </button>
        )}
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
  const [busca] = useSearchParams()
  const erroDoGoogle = busca.get('erro')
  // ex.: "Você ficou 2 horas sem usar o app" (mostrado uma vez)
  const [motivo] = useState(() => motivoDaSaida.tirar())

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
        <p className="-mt-2 text-right text-xs">
          <Link to="/recuperar-senha" className="text-texto-suave hover:text-esperanca">Esqueci minha senha</Link>
        </p>
        {motivo && !erro && !erroDoGoogle && (
          <p role="status" className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm text-texto-suave">{motivo}</p>
        )}
        {erroDoGoogle && !erro && <Aviso>{erroDoGoogle}</Aviso>}
        <Aviso erro={erro} />
        <Botao type="submit" disabled={enviando} className="w-full">{enviando ? 'Entrando…' : 'Entrar'}</Botao>
      </form>
      <BotaoGoogle destino={destino} />
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
      <BotaoGoogle destino={destino} />
      <p className="mt-4 text-center text-sm text-texto-suave">
        Já tem conta? <Link to="/entrar" state={{ de: destino }} className="text-esperanca hover:underline">Entrar</Link>
      </p>
    </Moldura>
  )
}

/** Pede o link por e-mail. A resposta é sempre a mesma, exista a conta ou não. */
export function RecuperarSenha() {
  const [erro, setErro] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const email = String(new FormData(e.currentTarget).get('email'))
    setEnviando(true)
    setErro(null)
    try {
      await chamar('/auth/recuperar', { corpo: { email } })
      setEnviado(true)
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Moldura titulo="Esqueci minha senha">
      {enviado ? (
        <p role="status" className="text-sm">
          Se houver uma conta com esse e-mail, enviamos um link para criar uma nova senha. Ele vale por 1 hora;
          confira também a caixa de spam.
        </p>
      ) : (
        <form onSubmit={enviar} className="space-y-4">
          <p className="text-sm text-texto-suave">
            Mandamos um link para o seu e-mail. Serve também para quem entra pelo Google criar uma senha.
          </p>
          <Campo rotulo="E-mail" name="email" type="email" autoComplete="email" required />
          <Aviso erro={erro} />
          <Botao type="submit" disabled={enviando} className="w-full">{enviando ? 'Enviando…' : 'Enviar link'}</Botao>
        </form>
      )}
      <p className="mt-4 text-center text-sm">
        <Link to="/entrar" className="text-esperanca hover:underline">Voltar para entrar</Link>
      </p>
    </Moldura>
  )
}

/** Página do link do e-mail: cria a senha nova e já entra. */
export function RedefinirSenha() {
  const { entrarComToken } = useAutenticacao()
  const navegar = useNavigate()
  const [busca] = useSearchParams()
  const tokenDoLink = busca.get('token') ?? ''
  const [erro, setErro] = useState<unknown>(null)
  const [enviando, setEnviando] = useState(false)
  const [senha, setSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const diferentes = confirmacao !== '' && senha !== confirmacao

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      const t = await chamar<{ access_token: string }>('/auth/redefinir', { corpo: { token: tokenDoLink, senha } })
      entrarComToken(t.access_token)
      navegar('/personagens', { replace: true })
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  if (!tokenDoLink) {
    return (
      <Moldura titulo="Nova senha">
        <Aviso>Link incompleto. Abra o link do e-mail de novo ou peça outro.</Aviso>
        <p className="mt-4 text-center text-sm"><Link to="/recuperar-senha" className="text-esperanca hover:underline">Pedir outro link</Link></p>
      </Moldura>
    )
  }
  return (
    <Moldura titulo="Nova senha">
      <form onSubmit={enviar} className="space-y-4">
        <Campo rotulo="Nova senha" type="password" autoComplete="new-password" required minLength={8}
          dica="Pelo menos 8 caracteres." value={senha} onChange={(e) => setSenha(e.target.value)} />
        <Campo rotulo="Repita a senha" type="password" autoComplete="new-password" required minLength={8}
          value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} />
        {diferentes && <Aviso>As senhas não são iguais.</Aviso>}
        <Aviso erro={erro} />
        <Botao type="submit" disabled={enviando || diferentes || senha.length < 8} className="w-full">
          {enviando ? 'Salvando…' : 'Salvar e entrar'}
        </Botao>
      </form>
      <p className="mt-3 text-xs text-texto-suave">Quem estava logado com a senha antiga vai precisar entrar de novo.</p>
      <p className="mt-4 text-center text-sm"><Link to="/recuperar-senha" className="text-esperanca hover:underline">Pedir outro link</Link></p>
    </Moldura>
  )
}

/** Volta do Google: o token vem no fragmento (#token=...), que nunca vai a servidor nenhum. */
export function EntrarComGoogle() {
  const { entrarComToken } = useAutenticacao()
  const navegar = useNavigate()
  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
    let destino = '/personagens'
    try {
      destino = sessionStorage.getItem(CHAVE_DESTINO) ?? destino
      sessionStorage.removeItem(CHAVE_DESTINO)
    } catch { /* modo privado */ }
    if (token) {
      entrarComToken(token)
      navegar(destino, { replace: true })
    } else {
      navegar('/entrar?erro=' + encodeURIComponent('O login com o Google não voltou com a sua conta. Tente de novo.'),
        { replace: true })
    }
  }, [entrarComToken, navegar])
  return <Moldura titulo="Entrando…"><p className="text-sm text-texto-suave">Só um instante.</p></Moldura>
}
