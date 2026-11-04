import { Link } from 'react-router'

import { useClasses, usePersonagens } from '../api/consultas'
import { Foto } from '../componentes/Foto'
import { Aviso, Carregando } from '../componentes/ui'

export default function Personagens() {
  const personagens = usePersonagens()
  const classes = useClasses()
  const nomeDaClasse = (id: string) => {
    const c = classes.data?.find((x) => x.id === id)
    return c?.nome ?? ''
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl">Seus personagens</h1>
        <Link to="/personagens/novo"
          className="botao-principal">
          Novo personagem
        </Link>
      </div>

      {personagens.isPending && <Carregando />}
      <Aviso erro={personagens.error} />

      {personagens.data?.length === 0 && (
        <div className="rounded-2xl border border-dashed border-borda-campo p-10 text-center">
          <p className="font-titulo text-lg">Nenhuma aventura ainda.</p>
          <p className="mt-1 text-sm text-texto-suave">Crie seu primeiro personagem para começar.</p>
        </div>
      )}

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {personagens.data?.map((p) => (
          <li key={p.id}>
            <article className="carta relative flex h-full items-center gap-4 p-5 transition hover:border-texto sm:flex-col sm:gap-2 sm:p-6 sm:text-center">
              <Foto id={p.foto} nome={p.nome || '?'} tamanho="g" />
              <div className="min-w-0 space-y-1">
                <h2 className="text-xl leading-tight">
                  {/* a carta inteira é clicável; o link da sessão fica por cima */}
                  <Link to={`/personagens/${p.id}`} className="after:absolute after:inset-0 hover:underline">
                    {p.nome || 'Sem nome'}
                  </Link>
                </h2>
                <p className="text-sm text-texto-suave">Nível {p.nivel} · {nomeDaClasse(p.classe)}</p>
                {p.em_jogo && p.mesa_id ? (
                  <p className="relative text-sm">
                    Jogando agora:{' '}
                    <Link to={`/mesas/${p.mesa_id}?aba=sessao&sessao=${p.em_jogo.sessao_id}`} className="enlace font-semibold">
                      {p.em_jogo.titulo}
                    </Link>
                  </p>
                ) : <p className="text-sm text-texto-suave">{p.mesa_id ? 'Em uma mesa' : 'Sem mesa'}</p>}
              </div>
            </article>
          </li>
        ))}
      </ul>
    </div>
  )
}
