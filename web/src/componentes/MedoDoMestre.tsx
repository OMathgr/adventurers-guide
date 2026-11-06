// Pontos de Medo (0 a 12) de uma sessão. O livro pede que fiquem visíveis
// para os jogadores; só o mestre responsável muda (ganhar, gastar ou clicar).
import { Aviso, Botao, mudouAqui, useMudanca } from './ui'

const MAXIMO = 12

type Mudanca = { delta: number } | { valor: number }

/** No celular, com a sessão em andamento: o Medo fica sempre à mão, acima do
    menu, como as marcas do jogador. Os botões são a forma de mudar (losangos tão
    pequenos não dão para tocar). */
export function MedoFixo({ medo, titulo, aoMudar, ocupado, erro }: {
  medo: number; titulo: string; aoMudar?: (m: Mudanca) => void; ocupado?: boolean; erro?: unknown
}) {
  const mudanca = useMudanca(medo)
  const alto = medo >= 9
  return (
    <div role="group" aria-label={titulo} data-marcas-fixas data-alto={alto || undefined}
      className={`fixed inset-x-0 bottom-14 z-20 !m-0 border-t px-4 py-2 ${alto ? 'border-t-2 border-medo bg-[color-mix(in_srgb,var(--medo)_25%,var(--superficie))]' : 'border-medo/60 bg-[color-mix(in_srgb,var(--medo)_10%,var(--superficie))]'}`}>
      <Aviso erro={erro} />
      <div className="flex items-center gap-3">
        <span className="rubrica text-medo">Medo</span>
        <p className="font-titulo leading-none">
          <span className={`text-3xl font-bold text-medo ${mudanca ? 'numero-muda' : ''}`} aria-live="polite">{medo}</span>
          <span className="text-sm text-texto-suave">/{MAXIMO}</span>
        </p>
        <div aria-hidden className="grid grid-cols-6 gap-1.5">
          {Array.from({ length: MAXIMO }, (_, i) => (
            <span key={i} className={`h-2 w-2 rotate-45 rounded-[1px] border border-medo ${i < medo ? 'bg-medo' : ''} ${mudouAqui(mudanca, i) ? 'marca-muda' : ''}`} />
          ))}
        </div>
        {aoMudar && (
          <div className="ml-auto flex gap-2">
            <Botao variante="secundario" className="!min-h-11 !w-11 !px-0 !text-2xl !leading-none" aria-label="Gastar 1 de Medo"
              disabled={ocupado || medo === 0} onClick={() => aoMudar({ delta: -1 })}>−</Botao>
            <Botao variante="secundario" className="!min-h-11 !w-11 !px-0 !text-2xl !leading-none" aria-label="Ganhar 1 de Medo"
              disabled={ocupado || medo === MAXIMO} onClick={() => aoMudar({ delta: 1 })}>+</Botao>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MedoDoMestre({ medo, titulo = 'Medo', aoMudar, ocupado, erro }: {
  medo: number; titulo?: string; aoMudar?: (m: Mudanca) => void; ocupado?: boolean; erro?: unknown
}) {
  const podeMudar = !!aoMudar
  const mudanca = useMudanca(medo)
  const pip = (i: number) => {
    const cheio = i < medo
    const classe = `h-5 w-5 rotate-45 rounded-[3px] border-2 border-medo transition-colors duration-200 max-sm:h-7 max-sm:w-7 ${cheio ? 'bg-medo' : 'bg-fundo'} ${mudouAqui(mudanca, i) ? 'marca-muda' : ''}`
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
      className={`rounded-2xl border p-4 transition-colors duration-500 ${alto ? 'border-2 border-medo bg-medo/25' : 'border-medo/60 bg-medo/10'}`}>
      <header className="flex items-center gap-3">
        <h2 className="rubrica text-medo">{titulo}</h2>
        <span aria-hidden className="h-px min-w-4 flex-1 bg-medo/40" />
      </header>
      <p className="mt-2 font-titulo">
        <span className={`${alto ? 'text-6xl' : 'text-5xl'} font-bold leading-none text-medo ${mudanca ? 'numero-muda' : ''}`} aria-live="polite">{medo}</span>
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
