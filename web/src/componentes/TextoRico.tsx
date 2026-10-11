import { blocos, type Trecho } from '../lib/texto'

function Linha({ trechos }: { trechos: Trecho[] }) {
  return trechos.map((t, i) => {
    let no: React.ReactNode = t.texto
    if (t.italico) no = <em>{no}</em>
    if (t.negrito) no = <strong className="text-texto">{no}</strong>
    return <span key={i}>{no}</span>
  })
}

/** Texto do SRD com negrito, itálico e listas (sem HTML cru). */
export default function TextoRico({ texto, className }: { texto: string; className?: string }) {
  return (
    <div className={className}>
      {blocos(texto).map((b, i) =>
        b.tipo === 'lista' ? (
          <ul key={i} className="my-1 list-disc space-y-0.5 pl-5">
            {b.itens.map((item, j) => <li key={j}><Linha trechos={item} /></li>)}
          </ul>
        ) : (
          <p key={i} className="[&+*]:mt-1.5"><Linha trechos={b.trechos} /></p>
        ))}
    </div>
  )
}
