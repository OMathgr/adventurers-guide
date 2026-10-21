// Morte do personagem: ao marcar o último PV, o jogador escolhe o movimento de
// morte (Sacrifício Glorioso, Evitar a Morte, Arriscar Tudo). Evitar a Morte pode
// dar uma cicatriz: risca 1 espaço de Esperança e o jogador escolhe o impacto
// narrativo. Os dados podem vir da mesa (digitados) ou o app rola.
import { useState } from 'react'

import { useCartas, useDefinirCicatriz, useEvitarMorteComCarta, useMovimentoDeMorte } from '../api/consultas'
import type { Ficha, ImpactoDaCicatriz, MovimentoDeMorte } from '../api/tipos'
import { NOME_IMPACTO, NOME_MOVIMENTO_MORTE } from '../lib/rotulos'
import { Aviso, Botao, Cartao, Escolhivel } from './ui'

const d12 = () => 1 + Math.floor(Math.random() * 12)

const EXPLICACAO: Record<MovimentoDeMorte, string> = {
  SACRIFICIO_GLORIOSO: 'Faça uma ação final: com o aval do mestre, ela é um sucesso crítico. Depois, o personagem atravessa o véu da morte.',
  EVITAR_A_MORTE: 'Fica inconsciente até um aliado limpar 1 PV ou o grupo terminar um descanso longo. Role o Dado de Esperança: '
    + 'se tirar o seu nível ou menos, ganha uma cicatriz (risca 1 espaço de Esperança).',
  ARRISCAR_TUDO: 'Role os Dados de Dualidade. Esperança maior: continua de pé e limpa PV e PF somando o Dado de Esperança. '
    + 'Medo maior: atravessa o véu da morte. Iguais: continua de pé e limpa todos os PV e PF.',
}

function Dado({ rotulo, valor, aoMudar }: { rotulo: string; valor: string; aoMudar: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-texto-suave">{rotulo}</span>
      <span className="flex gap-1">
        <input type="number" min={1} max={12} value={valor} onChange={(e) => aoMudar(e.target.value)} aria-label={rotulo}
          className="w-16 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
        <Botao type="button" variante="secundario" onClick={() => aoMudar(String(d12()))}>Rolar</Botao>
      </span>
    </label>
  )
}

/** Battle Hardened e Unbreakable: no lugar do movimento de morte. */
function CartasNoLugar({ ficha, usar }: { ficha: Ficha; usar: ReturnType<typeof useEvitarMorteComCarta> }) {
  const cartas = useCartas()
  const ids = ficha.alternativas_a_morte ?? []
  if (ids.length === 0) return null
  return (
    <div className="space-y-1">
      <p className="text-sm">Ou use uma carta da mão no lugar:</p>
      <div className="flex flex-wrap gap-2">
        {ids.map((id) => {
          const c = cartas.data?.find((x) => x.id === id)
          return (
            <Botao key={id} variante="secundario" disabled={usar.isPending} title={c?.texto}
              onClick={() => usar.mutate(id)}>{c?.nome ?? id}</Botao>
          )
        })}
      </div>
      <Aviso erro={usar.error} />
    </div>
  )
}

function EscolherMovimento({ ficha, morte, usar }: {
  ficha: Ficha; morte: ReturnType<typeof useMovimentoDeMorte>; usar: ReturnType<typeof useEvitarMorteComCarta>
}) {
  const [movimento, setMovimento] = useState<MovimentoDeMorte | null>(null)
  const [esperanca, setEsperanca] = useState('')
  const [medo, setMedo] = useState('')
  const [pv, setPv] = useState<number | null>(null)
  const e = Number(esperanca)
  const m = Number(medo)
  const venceuEsperanca = movimento === 'ARRISCAR_TUDO' && e >= 1 && m >= 1 && e > m
  const paraPv = pv ?? Math.min(e, ficha.pv_marcados)

  function confirmar() {
    if (!movimento) return
    if (movimento === 'SACRIFICIO_GLORIOSO' && !confirm('Sacrifício Glorioso: o personagem morre depois da ação final. Confirmar?')) return
    morte.mutate({
      movimento,
      rolagem_esperanca: movimento !== 'SACRIFICIO_GLORIOSO' && esperanca ? e : null,
      rolagem_medo: movimento === 'ARRISCAR_TUDO' && medo ? m : null,
      pv: venceuEsperanca ? paraPv : null,
    })
  }

  return (
    <div role="alertdialog" aria-label="Movimento de morte"
      className="space-y-3 rounded-2xl border-2 border-perigo/70 bg-perigo/10 p-4">
      <h2 className="font-titulo text-lg text-perigo">Movimento de morte</h2>
      <p className="text-sm">{ficha.nome || 'Seu personagem'} marcou o último PV. Escolha uma das opções:</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {(Object.keys(EXPLICACAO) as MovimentoDeMorte[]).map((x) => (
          <Escolhivel key={x} selecionado={movimento === x} onClick={() => { setMovimento(x); morte.reset() }}>
            <span className="block font-medium">{NOME_MOVIMENTO_MORTE[x]}</span>
            <span className="block text-xs text-texto-suave">{EXPLICACAO[x]}</span>
          </Escolhivel>
        ))}
      </div>
      {(movimento === 'EVITAR_A_MORTE' || movimento === 'ARRISCAR_TUDO') && (
        <div className="flex flex-wrap items-end gap-3">
          <Dado rotulo="Dado de Esperança (d12)" valor={esperanca} aoMudar={setEsperanca} />
          {movimento === 'ARRISCAR_TUDO' && <Dado rotulo="Dado de Medo (d12)" valor={medo} aoMudar={setMedo} />}
          <p className="text-xs text-texto-suave">Vazio: o app rola ao confirmar.</p>
        </div>
      )}
      {venceuEsperanca && (
        <label className="block space-y-1 text-sm">
          <span>Divida os {e} do Dado de Esperança: <b>{paraPv} PV</b> e <b>{e - paraPv} PF</b></span>
          <input type="range" min={0} max={e} value={paraPv} onChange={(ev) => setPv(Number(ev.target.value))}
            aria-label="Quanto vai para PV" className="w-full max-w-xs" />
        </label>
      )}
      <Aviso erro={morte.error} />
      <Botao variante="perigo" disabled={!movimento || morte.isPending} onClick={confirmar}>Confirmar</Botao>
      <CartasNoLugar ficha={ficha} usar={usar} />
    </div>
  )
}

function Cicatriz({ personagemId, indice, impacto, descricao }: {
  personagemId: string; indice: number; impacto: ImpactoDaCicatriz; descricao: string
}) {
  const salvar = useDefinirCicatriz(personagemId)
  const [i, setI] = useState<ImpactoDaCicatriz>(impacto)
  const [d, setD] = useState(descricao)
  const mudou = i !== impacto || d !== descricao
  return (
    <li className="space-y-1 rounded-lg border border-borda p-2 text-sm">
      <div className="flex flex-wrap items-end gap-2">
        <select aria-label={`Impacto da cicatriz ${indice + 1}`} value={i} onChange={(e) => setI(e.target.value as ImpactoDaCicatriz)}
          className="rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm">
          {Object.entries(NOME_IMPACTO).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <input value={d} onChange={(e) => setD(e.target.value)} maxLength={500} placeholder="O que ela representa"
          aria-label={`Descrição da cicatriz ${indice + 1}`}
          className="min-w-0 flex-1 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
        <Botao variante="secundario" disabled={!mudou || salvar.isPending}
          onClick={() => salvar.mutate({ indice, impacto: i, descricao: d })}>Salvar</Botao>
      </div>
      <Aviso erro={salvar.error} />
    </li>
  )
}

/** Movimento de morte (quando precisa), estado e cicatrizes. Na página do personagem. */
export default function Morte({ personagemId, ficha }: { personagemId: string; ficha: Ficha }) {
  const morte = useMovimentoDeMorte(personagemId)
  const usar = useEvitarMorteComCarta(personagemId)
  const cicatrizes = ficha.cicatrizes ?? []
  return (
    <>
      {ficha.morto && (
        <p role="status" className="rounded-2xl border border-borda bg-superficie-2 p-4 text-center font-titulo">
          {ficha.nome || 'O personagem'} atravessou o véu da morte.
          <span className="mt-1 block font-sans text-sm text-texto-suave">
            Converse com o mestre para criar um personagem novo no nível do grupo.
          </span>
        </p>
      )}
      {!ficha.morto && ficha.inconsciente && (
        <p role="status" className="rounded-xl border border-perigo/60 bg-perigo/10 px-3 py-2 text-sm">
          Inconsciente: não se move nem age e não pode ser alvo de ataques. Volta a si quando um aliado limpar 1 PV
          ou mais, ou no fim de um descanso longo.
        </p>
      )}
      {ficha.precisa_movimento_de_morte && <EscolherMovimento key={ficha.pv_marcados} ficha={ficha} morte={morte} usar={usar} />}
      {usar.data && <p role="status" className="rounded-xl border border-borda bg-superficie p-3 text-sm">{usar.data.notas.join(' ')}</p>}
      {morte.data && (
        <p role="status" className="rounded-xl border border-borda bg-superficie p-3 text-sm">
          <b>{NOME_MOVIMENTO_MORTE[morte.data.resultado.movimento]}</b>
          {morte.data.resultado.rolagem_esperanca && <> · Esperança {morte.data.resultado.rolagem_esperanca}</>}
          {morte.data.resultado.rolagem_medo && <> · Medo {morte.data.resultado.rolagem_medo}</>}
          : {morte.data.resultado.notas?.join(' ')}
        </p>
      )}
      {cicatrizes.length > 0 && (
        <Cartao titulo={`Cicatrizes (${cicatrizes.length})`}>
          <p className="mb-2 text-xs text-texto-suave">
            Cada uma risca 1 espaço de Esperança. O impacto é seu: uma cicatriz física, uma memória dolorosa, um medo
            paralisante... O mestre pode deixar curar (como projeto no repouso, por exemplo).
          </p>
          <ul className="space-y-2">
            {cicatrizes.map((c, i) => (
              <Cicatriz key={`${i}:${c.impacto}:${c.descricao}`} personagemId={personagemId} indice={i}
                impacto={c.impacto ?? ''} descricao={c.descricao ?? ''} />
            ))}
          </ul>
        </Cartao>
      )}
    </>
  )
}
