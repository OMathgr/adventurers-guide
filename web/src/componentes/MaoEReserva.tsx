// Cartas de domínio divididas em mão (até 5 ativas) e reserva. Mandar para
// a reserva é grátis; trazer de volta é grátis num descanso e, fora dele,
// marca PF igual ao custo de troca da carta. Cartas com passivo (Armorer,
// Bare Bones, as "-Touched"...) mostram se o efeito já está na ficha; na
// reserva elas não valem. As regras são do motor.
import { useState } from 'react'

import { useGuardarCarta, useRecuperarCarta } from '../api/consultas'
import type { CartaDeDominio, Ficha } from '../api/tipos'
import { useNomeDominio, useNomes } from '../lib/nomes'
import { LIMITE_MAO } from '../lib/regras'
import { Aviso, Botao, Cartao, Original, Selo } from './ui'

function Trazer({ ficha, carta, custo, aoTrazer, enviando }: {
  ficha: Ficha; carta: string; custo: number; enviando: boolean
  aoTrazer: (p: { noLugarDe?: string; emDescanso: boolean }) => void
}) {
  const nomes = useNomes(ficha)
  const [emDescanso, setEmDescanso] = useState(true)
  const [noLugarDe, setNoLugarDe] = useState('')
  const cheia = ficha.cartas_ativas.filter((c) => !nomes.carta(c)?.fora_do_limite).length >= LIMITE_MAO
  return (
    <div className="mt-3 space-y-2 border-t border-borda pt-3 text-sm">
      <fieldset className="space-y-1">
        <legend className="sr-only">Quando trazer</legend>
        <label className="flex items-center gap-2">
          <input type="radio" name={`quando-${carta}`} checked={emDescanso} onChange={() => setEmDescanso(true)} />
          Num descanso (grátis)
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" name={`quando-${carta}`} checked={!emDescanso} onChange={() => setEmDescanso(false)} />
          Agora (marca {custo} PF, o custo de troca)
        </label>
      </fieldset>
      {cheia && (
        <select value={noLugarDe} onChange={(e) => setNoLugarDe(e.target.value)} aria-label="Carta que vai para a reserva"
          className="w-full rounded-lg border border-borda bg-fundo px-3 py-2">
          <option value="">Mão cheia: qual vai para a reserva?</option>
          {ficha.cartas_ativas.filter((c) => !nomes.carta(c)?.fora_do_limite)
            .map((c) => <option key={c} value={c}>{nomes.carta(c)?.nome ?? c}</option>)}
        </select>
      )}
      <Botao variante="secundario" disabled={enviando || (cheia && !noLugarDe)}
        onClick={() => aoTrazer({ noLugarDe: noLugarDe || undefined, emDescanso })}>
        Trazer para a mão
      </Botao>
    </div>
  )
}

/** Por que o passivo não vale agora (a carta está na mão). */
function semEfeito(carta: CartaDeDominio, nomeDominio: (d: string) => string): string {
  const cond = carta.passivo?.condicao ?? ''
  if (cond === 'com_armadura') return 'só com armadura'
  if (cond === 'sem_armadura') return 'só sem armadura'
  if (cond.startsWith('dominio:')) return `precisa de 4 cartas de ${nomeDominio(cond.split(':')[1])} na mão`
  return 'sem efeito agora'
}

export default function MaoEReserva({ ficha, personagemId }: { ficha: Ficha; personagemId?: string }) {
  const nomes = useNomes(ficha)
  const dominio = useNomeDominio()
  const guardar = useGuardarCarta(personagemId ?? '')
  const recuperar = useRecuperarCarta(personagemId ?? '')
  const editavel = !!personagemId
  // Notorious não conta no limite da mão
  const naMao = ficha.cartas_ativas.filter((c) => !nomes.carta(c)?.fora_do_limite).length

  const lista = (ids: string[], naReserva: boolean) => (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {ids.map((id) => {
        const carta = nomes.carta(id)
        return (
          <details key={id} className={`rounded-xl border border-borda bg-fundo/60 p-3 ${naReserva ? 'opacity-75' : ''}`}>
            <summary className="cursor-pointer list-none">
              <span className="font-titulo">{carta?.nome ?? id}</span><Original nome={carta?.nome} original={carta?.nome_original} />
              <span className="mt-1 flex flex-wrap gap-1.5">
                {carta && <Selo>{dominio(carta.dominio)} · nível {carta.nivel}</Selo>}
                {carta && <Selo>troca {carta.custo_recall}</Selo>}
                {carta?.passivo && !naReserva && (ficha.cartas_aplicadas ?? []).includes(id) && <Selo destaque>na ficha</Selo>}
                {carta?.passivo && !naReserva && !(ficha.cartas_aplicadas ?? []).includes(id) && (
                  <span className="text-xs text-texto-suave">{semEfeito(carta, dominio)}</span>
                )}
                {carta?.reserva_permanente && naReserva && <Selo>reserva para sempre</Selo>}
              </span>
            </summary>
            {carta && <p className="mt-2 whitespace-pre-line text-sm text-texto-suave">{carta.texto}</p>}
            {carta?.fora_do_limite && !naReserva && <p className="mt-2 text-xs text-texto-suave">Não conta no limite da mão e não vai para a reserva.</p>}
            {editavel && !naReserva && !carta?.fora_do_limite && (
              <Botao variante="fantasma" className="mt-2 !px-0" disabled={guardar.isPending}
                onClick={() => guardar.mutate(id)}>Mandar para a reserva</Botao>
            )}
            {carta?.passivo && naReserva && <p className="mt-2 text-xs text-texto-suave">Na reserva, o efeito não vale.</p>}
            {editavel && naReserva && !carta?.reserva_permanente && (
              <Trazer ficha={ficha} carta={id} custo={carta?.custo_recall ?? 0} enviando={recuperar.isPending}
                aoTrazer={(p) => recuperar.mutate({ carta: id, ...p })} />
            )}
          </details>
        )
      })}
    </div>
  )

  return (
    <Cartao titulo={`Cartas de domínio: mão (${naMao}/${LIMITE_MAO})`} className="lg:col-span-3">
      <Aviso erro={guardar.error ?? recuperar.error} />
      {ficha.cartas_ativas.length === 0 && <p className="text-sm text-texto-suave">Nenhuma carta na mão.</p>}
      {lista(ficha.cartas_ativas, false)}
      {ficha.cartas_cofre.length > 0 && (
        <>
          <h3 className="mb-2 mt-4 text-sm text-esperanca">Reserva ({ficha.cartas_cofre.length})</h3>
          {lista(ficha.cartas_cofre, true)}
        </>
      )}
    </Cartao>
  )
}
