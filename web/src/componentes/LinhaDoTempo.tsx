// Visão "linha do tempo": os níveis 1 a 10 lado a lado, com rolagem
// horizontal. Embaixo de cada nível fica a caixa de avanços do patamar
// (como a página de Level Up do livro): marcada nos níveis feitos, para
// marcar no próximo e só para consulta nos futuros.
import { useEffect, useRef } from 'react'

import { useAplicarPlano, useDescartarPlano, useProximoNivel } from '../api/consultas'
import type { EventoLinhaDoTempo, Ficha, ProximoNivel } from '../api/tipos'
import EscolhaDeNivel from './EscolhaDeNivel'
import QuadroAvanco from './QuadroAvanco'
import { Aviso, Botao, Carregando, Selo } from './ui'

function Itens({ itens, apagado }: { itens: string[]; apagado?: boolean }) {
  return (
    <ul className={`space-y-1 text-sm ${apagado ? 'text-texto-suave' : 'text-texto'}`}>
      {itens.map((item, j) => <li key={j}>• {item}</li>)}
    </ul>
  )
}

/** Próximo nível: travado pela mesa, com plano (vindo de uma cópia) ou para escolher. */
function ProximoNivelColuna({ evento, proximo, personagemId, ficha }:
  { evento: EventoLinhaDoTempo; proximo: ProximoNivel; personagemId: string; ficha: Ficha }) {
  const aplicar = useAplicarPlano(personagemId)
  const descartar = useDescartarPlano(personagemId)

  if (proximo.bloqueado_pela_mesa) {
    return (
      <div className="space-y-3">
        <p className="rounded-xl border border-medo/50 bg-medo/10 p-3 text-sm">
          A mesa está no nível {proximo.limite_mesa}. O mestre ainda não liberou o nível {proximo.nivel}.
        </p>
        {proximo.planejado && <Itens itens={evento.itens} apagado />}
        <div className="space-y-2 opacity-60">
          {evento.quadros.map((q) => <QuadroAvanco key={q.tier} quadro={q} />)}
        </div>
      </div>
    )
  }
  if (proximo.planejado) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-texto-suave">Este nível já está planejado (veio da cópia do personagem):</p>
        <Itens itens={evento.itens} />
        <Aviso erro={aplicar.error ?? descartar.error} />
        <div className="flex flex-wrap gap-2">
          <Botao disabled={aplicar.isPending || descartar.isPending} onClick={() => aplicar.mutate()}>
            {aplicar.isPending ? 'Aplicando…' : `Aplicar o plano do nível ${proximo.nivel}`}
          </Botao>
          <Botao variante="secundario" disabled={aplicar.isPending || descartar.isPending}
            onClick={() => descartar.mutate(proximo.nivel)}>
            Escolher outra coisa
          </Botao>
        </div>
      </div>
    )
  }
  return <EscolhaDeNivel key={proximo.nivel} id={personagemId} ficha={ficha} proximo={proximo} quadros={evento.quadros} />
}

type Props = {
  eventos: EventoLinhaDoTempo[]
  personagemId: string
  ficha: Ficha
  aoDesfazer: () => void
  desfazendo: boolean
}

export default function LinhaDoTempo({ eventos, personagemId, ficha, aoDesfazer, desfazendo }: Props) {
  const ultimoFeito = Math.max(...eventos.filter((e) => e.status === 'feito').map((e) => e.nivel))
  const trilho = useRef<HTMLOListElement>(null)
  const atual = useRef<HTMLLIElement>(null)
  const proximo = useProximoNivel(personagemId)

  // começa mostrando o próximo nível (ou o último, no nível máximo)
  useEffect(() => {
    atual.current?.scrollIntoView?.({ behavior: 'smooth', inline: 'start', block: 'nearest' })
  }, [ultimoFeito])

  const rolar = (sentido: number) => trilho.current?.scrollBy?.({ left: sentido * 320, behavior: 'smooth' })

  /** Desfazer pede confirmação: as escolhas do nível se perdem. */
  function desfazer() {
    if (window.confirm(`Desfazer o nível ${ultimoFeito}? As escolhas feitas nele (avanços, carta, Experiência) se perdem.`)) {
      aoDesfazer()
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-texto-suave">Role para os lados para ver todos os níveis.</p>
        <div className="flex flex-wrap gap-1">
          {ultimoFeito > 1 && (
            <Botao variante="perigo" className="!px-3 !py-1" onClick={desfazer} disabled={desfazendo}>
              {desfazendo ? 'Desfazendo…' : `Desfazer o nível ${ultimoFeito}`}
            </Botao>
          )}
          <Botao variante="secundario" className="!px-3 !py-1" aria-label="Níveis anteriores" onClick={() => rolar(-1)}>←</Botao>
          <Botao variante="secundario" className="!px-3 !py-1" aria-label="Próximos níveis" onClick={() => rolar(1)}>→</Botao>
        </div>
      </div>

      <ol ref={trilho} aria-label="Linha do tempo"
        className="flex snap-x snap-mandatory items-start gap-4 overflow-x-auto scroll-smooth pb-4">
        {eventos.map((e, i) => {
          const feito = e.status === 'feito'
          const ehProximo = e.nivel === ultimoFeito + 1
          const novoTier = i === 0 || eventos[i - 1].tier !== e.tier
          const foco = ehProximo || (ultimoFeito === 10 && e.nivel === 10)
          return (
            <li key={e.nivel} ref={foco ? atual : undefined} aria-current={ehProximo ? 'step' : undefined}
              className={`shrink-0 snap-start ${ehProximo ? 'w-[min(32rem,88vw)]' : 'w-72'}`}>
              {/* trilho: patamar, losango e a linha que liga os níveis */}
              <p className="h-5 text-xs uppercase tracking-widest text-texto-suave">{novoTier && `Patamar ${e.tier}`}</p>
              <div className="relative mb-3 flex h-5 items-center">
                <span aria-hidden className="absolute inset-x-[-1rem] top-1/2 h-0.5 -translate-y-1/2 bg-borda" />
                <span aria-hidden className={`relative ml-1 h-4 w-4 rotate-45 rounded-[3px] border-2 ${
                  feito ? 'border-esperanca bg-esperanca' : ehProximo ? 'border-esperanca bg-fundo' : 'border-borda bg-fundo'}`} />
              </div>

              <div className={`space-y-3 rounded-2xl border p-4 ${
                ehProximo ? 'border-esperanca bg-superficie' : feito ? 'border-borda bg-superficie' : 'border-dashed border-borda'}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className={`text-base ${feito || ehProximo ? 'text-texto' : 'text-texto-suave'}`}>{e.titulo}</h3>
                  {!feito && (e.planejado || e.bloqueado_pela_mesa) && (
                    <span className="flex gap-1">
                      {e.planejado && <Selo destaque>planejado</Selo>}
                      {e.bloqueado_pela_mesa && <Selo>acima da mesa</Selo>}
                    </span>
                  )}
                  {feito && e.nivel === ultimoFeito && e.nivel > 1 && (
                    <Botao variante="perigo" onClick={desfazer} disabled={desfazendo} className="!px-2 !py-1 text-xs">
                      {desfazendo ? 'Desfazendo…' : 'Desfazer este nível'}
                    </Botao>
                  )}
                </div>

                {ehProximo ? (
                  proximo.isPending ? <Carregando /> : proximo.error ? <Aviso erro={proximo.error} /> : proximo.data && (
                    <ProximoNivelColuna evento={e} proximo={proximo.data} personagemId={personagemId} ficha={ficha} />
                  )
                ) : (
                  <>
                    <Itens itens={e.itens} apagado={!feito} />
                    <div className={`space-y-2 ${feito ? '' : 'opacity-60'}`}>
                      {e.quadros.map((q) => <QuadroAvanco key={q.tier} quadro={q} />)}
                    </div>
                  </>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
