// Habilidades de classe e de subclasse: na ficha (agrupadas por origem) e nas
// escolhas da criação e do level up (o que a carta de subclasse traz).
import type { Caracteristica, Ficha } from '../api/tipos'
import { NOME_ORIGEM_HABILIDADE } from '../lib/rotulos'
import { Cartao, Original, Selo } from './ui'

type ItemDaLista = { nome: string; descricao: string; nome_original?: string; automatica?: boolean }

/** Nome, texto (com quebras e marcadores) e, se o motor já aplica, o selo "na ficha". */
export function ListaDeHabilidades({ lista, resumida }: { lista: ItemDaLista[]; resumida?: boolean }) {
  return (
    <ul className="space-y-2 text-sm">
      {lista.map((h) => (
        <li key={h.nome}>
          <p className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{h.nome}</span>
            <Original nome={h.nome} original={h.nome_original} />
            {h.automatica && <Selo destaque>já na ficha</Selo>}
          </p>
          <p className={`whitespace-pre-line text-texto-suave ${resumida ? 'line-clamp-3 text-xs' : ''}`}>{h.descricao}</p>
        </li>
      ))}
    </ul>
  )
}

/** Habilidades vindas do SRD (Caracteristica): "automática" quando tem número ou regra no motor. */
export const comoItem = (c: Caracteristica): ItemDaLista => ({
  nome: c.nome, descricao: c.descricao, nome_original: c.nome_original,
  automatica: (c.modificadores?.length ?? 0) > 0 || !!c.efeito,
})

/** Cartão da ficha: um bloco por origem (classe, subclasse, multiclasse), na ordem do motor. */
export default function CartaoHabilidades({ ficha }: { ficha: Ficha }) {
  const grupos: { origem: string; itens: Ficha['habilidades'] }[] = []
  for (const h of ficha.habilidades) {
    const grupo = grupos.find((g) => g.origem === h.origem)
    if (grupo) grupo.itens.push(h)
    else grupos.push({ origem: h.origem, itens: [h] })
  }
  return (
    <Cartao titulo="Habilidades" className="lg:col-span-3">
      <div className="grid gap-5 md:grid-cols-2">
        {grupos.map((g) => (
          <section key={g.origem} className="space-y-3">
            <h3 className="text-sm text-esperanca">{g.origem}</h3>
            {Object.keys(NOME_ORIGEM_HABILIDADE).map((tipo) => {
              const itens = g.itens.filter((h) => h.tipo === tipo)
              if (itens.length === 0) return null
              return (
                <div key={tipo}>
                  <p className="mb-1 text-xs uppercase tracking-wider text-texto-suave">{NOME_ORIGEM_HABILIDADE[tipo]}</p>
                  <ListaDeHabilidades lista={itens} />
                </div>
              )
            })}
          </section>
        ))}
      </div>
    </Cartao>
  )
}
