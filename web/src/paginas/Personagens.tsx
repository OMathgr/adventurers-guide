import { Link } from 'react-router'

import { useClasses, usePersonagens } from '../api/consultas'
import { Aviso, Carregando } from '../componentes/ui'
import { nomeClasse } from '../lib/rotulos'

export default function Personagens() {
  const personagens = usePersonagens()
  const classes = useClasses()
  const nomeDaClasse = (id: string) => {
    const c = classes.data?.find((x) => x.id === id)
    return c ? nomeClasse(c.nome) : ''
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl">Seus personagens</h1>
        <Link to="/personagens/novo"
          className="rounded-lg bg-esperanca px-4 py-2 text-sm font-semibold text-sobre-esperanca hover:bg-esperanca-forte">
          Novo personagem
        </Link>
      </div>

      {personagens.isPending && <Carregando />}
      <Aviso erro={personagens.error} />

      {personagens.data?.length === 0 && (
        <div className="rounded-2xl border border-dashed border-borda p-10 text-center">
          <p className="font-titulo text-lg">Nenhuma aventura ainda.</p>
          <p className="mt-1 text-sm text-texto-suave">Crie seu primeiro personagem para começar.</p>
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {personagens.data?.map((p) => (
          <li key={p.id}>
            <Link to={`/personagens/${p.id}`}
              className="block rounded-2xl border border-borda bg-superficie p-4 transition hover:border-esperanca">
              <p className="font-titulo text-lg">{p.nome || 'Sem nome'}</p>
              <p className="text-sm text-texto-suave">
                Nível {p.nivel} · {nomeDaClasse(p.classe)}
                {p.mesa_id && <span className="ml-2 text-esperanca">em uma mesa</span>}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
