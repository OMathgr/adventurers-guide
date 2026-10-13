import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router'

import { useAoVivo } from '../api/aoVivo'
import { token } from '../api/cliente'
import { useAutenticacao } from '../auth/Autenticacao'

const CHAVE_TEMA = 'ag.tema'

function useTema() {
  const [tema, setTema] = useState<'escuro' | 'claro'>(() => {
    try { return localStorage.getItem(CHAVE_TEMA) === 'claro' ? 'claro' : 'escuro' } catch { return 'escuro' }
  })
  useEffect(() => {
    document.documentElement.dataset.tema = tema
    try { localStorage.setItem(CHAVE_TEMA, tema) } catch { /* modo privado */ }
  }, [tema])
  return [tema, () => setTema((t) => (t === 'escuro' ? 'claro' : 'escuro'))] as const
}

export function Logo() {
  return (
    <span className="flex items-center gap-2 font-titulo text-lg text-texto">
      <svg viewBox="0 0 64 64" className="h-7 w-7" aria-hidden>
        <path d="M32 6 L52 32 L32 58 L12 32 Z" fill="none" stroke="var(--esperanca)" strokeWidth="5" strokeLinejoin="round" />
        <path d="M32 20 L41 32 L32 44 L23 32 Z" fill="var(--esperanca)" />
      </svg>
      Adventurer's Guide
    </span>
  )
}

export default function Layout() {
  const { usuario, sair } = useAutenticacao()
  // só aparece logado: enquanto estiver aberto, recebe os avisos ao vivo
  useAoVivo(token.ler())
  const [tema, alternarTema] = useTema()

  return (
    <div className="min-h-screen">
      <header className="border-b border-borda bg-superficie/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/personagens"><Logo /></Link>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/personagens"
              className={({ isActive }) => (isActive ? 'text-esperanca' : 'text-texto-suave hover:text-texto')}>
              Personagens
            </NavLink>
            <NavLink to="/mesas"
              className={({ isActive }) => (isActive ? 'text-esperanca' : 'text-texto-suave hover:text-texto')}>
              Mesas
            </NavLink>
            <button onClick={alternarTema} className="text-texto-suave hover:text-texto"
              aria-label={tema === 'escuro' ? 'Usar tema claro' : 'Usar tema escuro'}>
              {tema === 'escuro' ? '☀' : '☾'}
            </button>
            {usuario && <span className="hidden text-texto-suave sm:inline">{usuario.nome}</span>}
            <button onClick={sair} className="text-texto-suave hover:text-perigo">Sair</button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
