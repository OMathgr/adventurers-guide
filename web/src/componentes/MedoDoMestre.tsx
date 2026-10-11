// Pontos de Medo do mestre (0 a 12). O livro pede que fiquem visíveis para
// os jogadores: todos veem; só mestres mudam (ganhar, gastar ou clicar).
import { useMedo } from '../api/consultas'
import { Aviso, Botao } from './ui'

const MAXIMO = 12

export default function MedoDoMestre({ mesaId, medo, podeMudar }: { mesaId: string; medo: number; podeMudar: boolean }) {
  const mudar = useMedo(mesaId)
  const pip = (i: number) => {
    const cheio = i < medo
    const classe = `h-5 w-5 rotate-45 rounded-[3px] border-2 border-medo ${cheio ? 'bg-medo' : 'bg-fundo'}`
    if (!podeMudar) return <span key={i} className={classe} />
    return (
      <button key={i} type="button" aria-label={`Medo ${i + 1}`} aria-pressed={cheio} disabled={mudar.isPending}
        onClick={() => mudar.mutate({ valor: i + 1 === medo ? i : i + 1 })}
        className={`${classe} transition hover:border-texto`} />
    )
  }
  return (
    <section aria-label="Medo" className="rounded-2xl border border-medo/50 bg-medo/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-titulo text-base">
          Medo <span className="text-2xl text-medo" aria-live="polite">{medo}</span>
          <span className="text-sm text-texto-suave">/{MAXIMO}</span>
        </h2>
        {podeMudar && (
          <div className="flex gap-1">
            <Botao variante="secundario" className="!px-3 !py-1" disabled={mudar.isPending || medo === 0}
              onClick={() => mudar.mutate({ delta: -1 })}>Gastar 1</Botao>
            <Botao variante="secundario" className="!px-3 !py-1" disabled={mudar.isPending || medo === MAXIMO}
              onClick={() => mudar.mutate({ delta: 1 })}>Ganhar 1</Botao>
          </div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2.5 pl-1" role={podeMudar ? 'group' : 'img'}
        aria-label={`Medo: ${medo} de ${MAXIMO}`}>
        {Array.from({ length: MAXIMO }, (_, i) => pip(i))}
      </div>
      <Aviso erro={mudar.error} />
    </section>
  )
}
