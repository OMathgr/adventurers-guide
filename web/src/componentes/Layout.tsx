import { Link, NavLink, Outlet, useLocation } from 'react-router'

import { useAoVivo } from '../api/aoVivo'
import { usePersonagens } from '../api/consultas'
import { useAutenticacao } from '../auth/Autenticacao'
import { useInstalar, useOnline } from '../lib/pwa'
import { useTema } from '../lib/tema'
import Rodape from './Rodape'

export function Logo() {
  return (
    <span className="flex items-center gap-2 font-marca text-base font-bold text-texto">
      <svg viewBox="0 0 64 64" className="h-7 w-7" aria-hidden>
        <path d="M32 6 L52 32 L32 58 L12 32 Z" fill="none" stroke="var(--esperanca)" strokeWidth="5" strokeLinejoin="round" />
        <path d="M32 20 L41 32 L32 44 L23 32 Z" fill="var(--esperanca)" />
      </svg>
      Adventurer's Guide
    </span>
  )
}

const ICONE_DE_NAVEGACAO = {
  personagens: <><circle cx="12" cy="8" r="4" /><path d="M4.5 20c.8-4 3.8-6 7.5-6s6.7 2 7.5 6" strokeLinecap="round" /></>,
  mesas: <><path d="M12 2.5l8.5 5v9L12 21.5l-8.5-5v-9L12 2.5z" strokeLinejoin="round" /><path d="M12 7.5l4.5 7h-9l4.5-7z" strokeLinejoin="round" /></>,
  sessao: <path d="M5 3.5h14v17l-7-4-7 4v-17z" strokeLinejoin="round" />,
  conta: <><path d="M4 5h16v14H4V5z" strokeLinejoin="round" /><path d="M8 10h8M8 14h5" strokeLinecap="round" /></>,
}

/** Um único menu: no alto no computador; no celular, fixo embaixo, ao alcance do polegar. */
function ItemDoMenu({ para, icone, children, rotulo, ativo }: {
  para: string; icone: keyof typeof ICONE_DE_NAVEGACAO; children: React.ReactNode; rotulo?: string
  /** Quem decide é a tela, quando só o caminho não basta (a sessão fica dentro da página da mesa). */
  ativo?: boolean
}) {
  const classe = (marcado: boolean) => `flex items-center gap-1 max-sm:min-h-14 max-sm:flex-1 max-sm:flex-col max-sm:justify-center max-sm:gap-0.5 max-sm:text-xs ${
    marcado ? 'font-semibold text-esperanca-forte' : 'text-texto-suave hover:text-texto'}`
  const Item = ativo === undefined ? NavLink : Link
  return (
    <Item to={para} aria-label={rotulo} aria-current={ativo ? 'page' : undefined}
      className={ativo === undefined ? (({ isActive }: { isActive: boolean }) => classe(isActive)) as never : classe(ativo)}>
      <svg viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.6" className="h-6 w-6 sm:hidden">
        {ICONE_DE_NAVEGACAO[icone]}
      </svg>
      {children}
    </Item>
  )
}

export default function Layout() {
  const { usuario, sair, logado } = useAutenticacao()
  // só aparece logado: enquanto estiver aberto, recebe os avisos ao vivo
  useAoVivo(logado)
  const [tema, alternarTema] = useTema()
  const instalar = useInstalar()
  const online = useOnline()
  const personagens = usePersonagens()
  const local = useLocation()
  const busca = new URLSearchParams(local.search)
  // a sessão em andamento fica a um toque, de qualquer tela. Com personagens em
  // mais de uma, "Sessão" é a que está aberta; fora delas, a primeira.
  const jogando = Array.isArray(personagens.data) ? personagens.data.filter((p) => p.em_jogo && p.mesa_id) : []
  const aberta = jogando.find((p) => local.pathname === `/mesas/${p.mesa_id}` && busca.get('aba') === 'sessao'
    && (busca.get('sessao') ?? p.em_jogo?.sessao_id) === p.em_jogo?.sessao_id)
  const emJogo = aberta ?? jogando[0]
  // na sessão em que se está jogando, o menu marca "Sessão", não "Mesas"
  const naSessao = !!aberta

  return (
    <div className="flex min-h-screen flex-col max-sm:pb-14 max-sm:has-[[data-marcas-fixas]]:pb-36">
      <header className="border-b border-borda bg-superficie">
        <div className="mx-auto flex max-w-[84rem] items-center justify-between gap-3 px-4 py-2 sm:py-3">
          <Link to="/personagens"><Logo /></Link>
          <div className="flex items-center gap-4 text-sm">
            <nav aria-label="Principal" className="flex items-center gap-4 max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-30 max-sm:gap-0 max-sm:border-t max-sm:border-borda max-sm:bg-superficie">
              <ItemDoMenu para="/personagens" icone="personagens">Personagens</ItemDoMenu>
              <ItemDoMenu para="/mesas" icone="mesas" ativo={naSessao ? false : undefined}>Mesas</ItemDoMenu>
              {emJogo?.em_jogo && (
                <ItemDoMenu para={`/mesas/${emJogo.mesa_id}?aba=sessao&sessao=${emJogo.em_jogo.sessao_id}`} icone="sessao" ativo={naSessao}>Sessão</ItemDoMenu>
              )}
              {usuario && (
                <ItemDoMenu para="/conta" icone="conta" rotulo="Conta">
                  <span className="hidden sm:inline">{usuario.nome}</span><span className="sm:hidden">Conta</span>
                </ItemDoMenu>
              )}
            </nav>
            <button onClick={alternarTema} className="flex h-8 w-8 items-center justify-center text-texto-suave hover:text-texto max-sm:h-11 max-sm:w-11"
              aria-label={tema === 'escuro' ? 'Usar tema claro' : 'Usar tema escuro'}>
              <svg viewBox="0 0 20 20" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="h-5 w-5">
                {tema === 'escuro'
                  ? <><circle cx="10" cy="10" r="3.5" /><path d="M10 2v2.5M10 15.5V18M2 10h2.5M15.5 10H18M4.3 4.3l1.8 1.8M13.9 13.9l1.8 1.8M4.3 15.7l1.8-1.8M13.9 6.1l1.8-1.8" /></>
                  : <path d="M16.5 12.5A7 7 0 0 1 7.5 3.5a7 7 0 1 0 9 9z" strokeLinejoin="round" />}
              </svg>
            </button>
            {instalar && (
              <button onClick={instalar} className="enlace">Instalar<span className="hidden sm:inline"> app</span></button>
            )}
            {/* no celular, sair fica na tela de Conta */}
            <button onClick={sair} className="text-texto-suave hover:text-perigo max-sm:hidden">Sair</button>
          </div>
        </div>
      </header>
      {!online && (
        <p role="status" className="bg-perigo/15 px-4 py-2 text-center text-sm text-perigo">
          Sem conexão: dá para ver o que já estava aberto, mas nada é salvo até a rede voltar.
        </p>
      )}
      {/* a mesa precisa de mais espaço (a sessão tem três colunas); todas as abas iguais, para o título não pular */}
      <main className={`mx-auto w-full flex-1 px-4 py-6 ${/^\/mesas\/[^/]+/.test(local.pathname) ? 'max-w-[84rem]' : 'max-w-6xl'}`}>
        <div key={local.pathname} className="entrada"><Outlet /></div>
      </main>
      <Rodape />
    </div>
  )
}
