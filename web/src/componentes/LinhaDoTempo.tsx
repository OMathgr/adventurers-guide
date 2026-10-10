// Visão "linha do tempo": os níveis 1 a 10, o que já foi escolhido em cada
// um e o que vem pela frente (para planejar).
import { Link } from 'react-router'

import type { EventoLinhaDoTempo } from '../api/tipos'
import { Botao } from './ui'

type Props = {
  eventos: EventoLinhaDoTempo[]
  personagemId: string
  aoDesfazer: () => void
  desfazendo: boolean
}

export default function LinhaDoTempo({ eventos, personagemId, aoDesfazer, desfazendo }: Props) {
  const ultimoFeito = Math.max(...eventos.filter((e) => e.status === 'feito').map((e) => e.nivel))

  return (
    <ol className="relative space-y-4 border-l-2 border-borda pl-6">
      {eventos.map((e, i) => {
        const feito = e.status === 'feito'
        const proximo = e.nivel === ultimoFeito + 1
        const novoTier = i === 0 || eventos[i - 1].tier !== e.tier
        return (
          <li key={e.nivel} className="relative">
            {novoTier && <p className="-ml-6 mb-2 text-xs uppercase tracking-widest text-texto-suave">Tier {e.tier}</p>}
            <span aria-hidden className={`absolute -left-[33px] top-1.5 h-4 w-4 rotate-45 rounded-[3px] border-2 ${
              feito ? 'border-esperanca bg-esperanca' : proximo ? 'border-esperanca bg-fundo' : 'border-borda bg-fundo'}`} />
            <div className={`rounded-2xl border p-4 ${feito ? 'border-borda bg-superficie' : 'border-dashed border-borda bg-transparent'}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className={`text-base ${feito ? 'text-texto' : 'text-texto-suave'}`}>{e.titulo}</h3>
                {proximo && (
                  <Link to={`/personagens/${personagemId}/subir`}
                    className="rounded-lg bg-esperanca px-3 py-1.5 text-sm font-semibold text-sobre-esperanca hover:bg-esperanca-forte">
                    Subir para o nível {e.nivel}
                  </Link>
                )}
                {feito && e.nivel === ultimoFeito && e.nivel > 1 && (
                  <Botao variante="fantasma" onClick={aoDesfazer} disabled={desfazendo} className="!px-2 !py-1">
                    {desfazendo ? 'Desfazendo…' : 'Desfazer este nível'}
                  </Botao>
                )}
              </div>
              <ul className={`mt-2 space-y-1 text-sm ${feito ? 'text-texto' : 'text-texto-suave'}`}>
                {e.itens.map((item, j) => <li key={j}>• {item}</li>)}
              </ul>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
