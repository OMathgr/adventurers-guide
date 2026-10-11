// Bloco de estatísticas de um adversário, no formato do SRD: cabeçalho,
// faixa de números (Dificuldade, limiares, PV, PF), ataque, experiências
// e características.
import type { Adversario } from '../api/tipos'
import { NOME_ALCANCE, NOME_TIPO_ADVERSARIO, NOME_TIPO_DANO, NOME_TIPO_HABILIDADE, comSinal } from '../lib/rotulos'
import TextoRico from './TextoRico'
import { Espacos, Original } from './ui'

function Numero({ rotulo, valor }: { rotulo: string; valor: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center px-3 py-1.5">
      <dt className="text-[10px] uppercase tracking-wider text-texto-suave">{rotulo}</dt>
      <dd className="font-titulo text-lg">{valor}</dd>
    </div>
  )
}

function limiares(a: Pick<Adversario, 'limiar_maior' | 'limiar_grave'>) {
  if (a.limiar_maior == null) return 'Nenhum'
  return `${a.limiar_maior}/${a.limiar_grave ?? '—'}`
}

export default function FichaInimigo({ adversario: a, acoes }: { adversario: Adversario; acoes?: React.ReactNode }) {
  const experiencias = Object.entries(a.experiencias ?? {})
  const tipo = a.tipo === 'HORDA' && a.horda_por_pv ? `Horda (${a.horda_por_pv}/PV)` : NOME_TIPO_ADVERSARIO[a.tipo]

  return (
    <article className="rounded-2xl border border-borda bg-superficie p-4 sm:p-5" aria-label={`Ficha de ${a.nome}`}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-xl text-esperanca">
            {a.nome}<Original nome={a.nome} original={a.nome_original} />
          </h2>
          <p className="text-sm font-medium uppercase tracking-wide text-texto-suave">
            Patamar {a.patamar} · {tipo}
          </p>
        </div>
        {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
      </header>

      {a.descricao && <p className="mt-2 text-sm italic">{a.descricao}</p>}
      {a.motivacoes && (
        <p className="mt-1 text-sm"><span className="font-semibold">Motivações e táticas:</span> {a.motivacoes}</p>
      )}

      <dl className="mt-3 flex flex-wrap justify-around divide-x divide-borda rounded-xl border border-borda bg-superficie-2">
        <Numero rotulo="Dificuldade" valor={a.dificuldade} />
        <Numero rotulo="Limiares" valor={limiares(a)} />
        <Numero rotulo="PV" valor={a.pv} />
        <Numero rotulo="PF" valor={a.pf} />
      </dl>

      <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
        <Espacos total={a.pv} marcados={0} rotulo="Pontos de Vida" />
        <Espacos total={a.pf} marcados={0} rotulo="Pontos de Fadiga" cor="medo" />
      </div>

      <p className="mt-3 text-sm">
        <span className="font-semibold">ATQ:</span> {a.ataque}
        <span className="mx-2 text-borda">|</span>
        <span className="font-semibold">{a.arma}<Original nome={a.arma} original={a.arma_original} />:</span>{' '}
        {NOME_ALCANCE[a.alcance] ?? a.alcance}
        <span className="mx-2 text-borda">|</span>
        {a.dano} {NOME_TIPO_DANO[a.tipo_dano]}
      </p>

      {experiencias.length > 0 && (
        <p className="mt-1 text-sm">
          <span className="font-semibold">Experiência:</span>{' '}
          {experiencias.map(([nome, valor]) => `${nome} ${comSinal(valor)}`).join(', ')}
        </p>
      )}

      {(a.habilidades?.length ?? 0) > 0 && (
        <section className="mt-4">
          <h3 className="mb-2 border-b border-borda pb-1 text-sm uppercase text-texto-suave">Características</h3>
          <ul className="space-y-2.5 text-sm">
            {a.habilidades!.map((h, i) => (
              <li key={i}>
                <p className="font-semibold">
                  {h.nome} – {NOME_TIPO_HABILIDADE[h.tipo]}
                  {h.detalhe && <span className="font-normal text-texto-suave"> ({h.detalhe})</span>}
                  <Original nome={h.nome} original={h.nome_original} />
                </p>
                <TextoRico texto={h.texto} className="text-texto-suave" />
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
