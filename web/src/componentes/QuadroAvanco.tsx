// A caixa de avanços de um patamar, como a página de Level Up: uma linha por
// opção, com um quadradinho por vez que ela pode ser marcada (duplo para as
// que valem dois avanços). Só leitura, ou interativa no próximo nível.
import type { Opcao, QuadroDeAvanco } from '../api/tipos'
import { NOME_OPCAO } from '../lib/rotulos'

export type Interacao = {
  selecionados: (tier: number, opcao: Opcao) => number
  pode: (tier: number, opcao: Opcao) => boolean
  marcar: (tier: number, opcao: Opcao) => void
  desmarcar: (tier: number, opcao: Opcao) => void
}

type Estado = 'antes' | 'neste' | 'riscado' | 'livre'

const ESTILO: Record<Estado, string> = {
  antes: 'border-esperanca/60 bg-esperanca/35',
  neste: 'border-esperanca bg-esperanca',
  riscado: 'border-borda bg-superficie-2 text-texto-suave',
  livre: 'border-texto-suave/60 bg-fundo',
}

const DESCRICAO: Record<Estado, string> = {
  antes: 'marcado em nível anterior', neste: 'marcado neste nível', riscado: 'riscado', livre: 'livre',
}

const niveisDoPatamar =(tier: number) => [3 * tier - 4, 3 * tier - 2] as const

export default function QuadroAvanco({ quadro, interacao }: { quadro: QuadroDeAvanco; interacao?: Interacao }) {
  const [inicio, fim] = niveisDoPatamar(quadro.tier)
  return (
    <section className="rounded-xl border border-borda bg-superficie-2/40 text-sm"
      aria-label={`${quadro.tier}º patamar`}>
      <h4 className="rounded-t-xl bg-medo/25 px-3 py-1.5 font-titulo text-xs uppercase tracking-wider">
        {quadro.tier}º patamar <span className="text-texto-suave">· níveis {inicio} a {fim}</span>
      </h4>
      <ul className="space-y-1.5 p-3">
        {quadro.opcoes.map((o) => {
          const sel = interacao ? interacao.selecionados(quadro.tier, o.opcao) : o.neste
          const estados: Estado[] = Array.from({ length: o.limite }, (_, i) =>
            i < o.antes ? 'antes' : i < o.antes + sel ? 'neste' : i < o.antes + sel + o.riscados ? 'riscado' : 'livre')
          const cortada = o.riscados > 0 && !estados.includes('livre')
          const nome = NOME_OPCAO[o.opcao]
          const largura = o.custo === 2 ? 'w-9' : 'w-4'
          return (
            <li key={o.opcao} className="flex items-start gap-2">
              <span className="flex w-[3.75rem] shrink-0 justify-end gap-1 pt-0.5">
                {estados.map((estado, i) => {
                  const classe = `flex h-4 ${largura} items-center justify-center rounded-[3px] border text-[10px] leading-none ${ESTILO[estado]}`
                  const rotulo = `${nome} (${quadro.tier}º patamar)${o.limite > 1 ? `, quadradinho ${i + 1}` : ''}`
                  if (interacao && (estado === 'neste' || estado === 'livre')) {
                    const marcado = estado === 'neste'
                    const habilitado = marcado || interacao.pode(quadro.tier, o.opcao)
                    return (
                      <button key={i} type="button" role="checkbox" aria-checked={marcado} aria-label={rotulo}
                        disabled={!habilitado}
                        onClick={() => (marcado ? interacao.desmarcar : interacao.marcar)(quadro.tier, o.opcao)}
                        className={`${classe} ${habilitado ? 'cursor-pointer hover:border-esperanca' : 'cursor-not-allowed opacity-40'}`}>
                        {marcado && '✓'}
                      </button>
                    )
                  }
                  return (
                    <span key={i} className={classe} title={DESCRICAO[estado]}
                      role="img" aria-label={`${rotulo}: ${DESCRICAO[estado]}`}>
                      {estado === 'riscado' && '✕'}
                    </span>
                  )
                })}
              </span>
              <span className={cortada ? 'text-texto-suave line-through' : sel > 0 ? 'text-esperanca' : ''}>
                {nome}{o.custo === 2 && <span className="text-xs text-texto-suave"> (vale 2 avanços)</span>}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
