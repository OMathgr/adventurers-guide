// Pontos de Medo (0 a 12) de uma sessão. O livro pede que fiquem visíveis
// para os jogadores; só o mestre responsável muda (ganhar, gastar ou clicar).
import { Aviso, Botao } from './ui'

const MAXIMO = 12

type Mudanca = { delta: number } | { valor: number }

export default function MedoDoMestre({ medo, titulo = 'Medo', aoMudar, ocupado, erro }: {
  medo: number; titulo?: string; aoMudar?: (m: Mudanca) => void; ocupado?: boolean; erro?: unknown
}) {
  const podeMudar = !!aoMudar
  const pip = (i: number) => {
    const cheio = i < medo
    const classe = `h-5 w-5 rotate-45 rounded-[3px] border-2 border-medo max-sm:h-7 max-sm:w-7 ${cheio ? 'bg-medo' : 'bg-fundo'}`
    if (!aoMudar) return <span key={i} className={classe} />
    return (
      <button key={i} type="button" aria-label={`Medo ${i + 1}`} aria-pressed={cheio} disabled={ocupado}
        onClick={() => aoMudar({ valor: i + 1 === medo ? i : i + 1 })}
        className={`${classe} transition hover:border-texto`} />
    )
  }
  // quanto mais Medo, mais a mesa sente: de 9 em diante o painel pesa
  const alto = medo >= 9
  return (
    <section aria-label={titulo} data-alto={alto || undefined}
      className={`rounded-2xl border p-4 ${alto ? 'border-2 border-medo bg-medo/25' : 'border-medo/60 bg-medo/10'}`}>
      <header className="flex items-center gap-3">
        <h2 className="rubrica text-medo">{titulo}</h2>
        <span aria-hidden className="h-px min-w-4 flex-1 bg-medo/40" />
      </header>
      <p className="mt-2 font-titulo">
        <span className={`${alto ? 'text-6xl' : 'text-5xl'} font-bold leading-none text-medo`} aria-live="polite">{medo}</span>
        <span className="text-lg text-texto-suave">/{MAXIMO}</span>
      </p>
      <div className="mt-3 grid w-fit grid-cols-6 gap-3 pl-1 max-sm:gap-4" role={podeMudar ? 'group' : 'img'}
        aria-label={`${titulo}: ${medo} de ${MAXIMO}`}>
        {Array.from({ length: MAXIMO }, (_, i) => pip(i))}
      </div>
      {aoMudar && (
        <div className="mt-4 flex gap-2">
          <Botao variante="secundario" className="flex-1" disabled={ocupado || medo === 0}
            onClick={() => aoMudar({ delta: -1 })}>Gastar 1</Botao>
          <Botao variante="secundario" className="flex-1" disabled={ocupado || medo === MAXIMO}
            onClick={() => aoMudar({ delta: 1 })}>Ganhar 1</Botao>
        </div>
      )}
      <Aviso erro={erro} />
    </section>
  )
}
