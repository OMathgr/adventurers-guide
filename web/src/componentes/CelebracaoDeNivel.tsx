// O momento de subir de nível: o d12 da Esperança se desenha, os losangos se
// espalham e aparece o que o personagem ganhou. Nada espera a animação: "Continuar"
// já funciona desde o começo, e Esc ou um clique fora também fecham.
import { type CSSProperties, useEffect, useId, useRef } from 'react'

import type { Ficha } from '../api/tipos'
import { ganhosDeNivel } from '../lib/ganhosDeNivel'
import { useNomes } from '../lib/nomes'
import { D12 } from './DadosDuais'
import { Botao } from './ui'

const LOSANGOS = 12
// a lista entra depois do dado, um item por vez, sem fazer ninguém esperar muito
const atrasoDoGanho = (i: number) => `${Math.min(650 + i * 70, 1200)}ms`

export default function CelebracaoDeNivel({ antes, depois, aoFechar }: { antes: Ficha; depois: Ficha; aoFechar: () => void }) {
  const nomes = useNomes(depois)
  const ganhos = ganhosDeNivel(antes, depois, (id) => nomes.carta(id)?.nome)
  const titulo = useId()
  const botao = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null
    botao.current?.focus()
    return () => anterior?.focus?.()
  }, [])

  return (
    <div role="dialog" aria-modal="true" aria-labelledby={titulo}
      className="celebracao fixed inset-0 z-50 !m-0 overflow-y-auto bg-fundo"
      onClick={(e) => { if (e.target === e.currentTarget) aoFechar() }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') aoFechar()
        if (e.key === 'Tab') e.preventDefault()   // só há um botão: o foco fica nele
      }}>
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center gap-4 px-4 py-8 text-center"
        onClick={(e) => { if (e.target === e.currentTarget) aoFechar() }}>
        <div aria-hidden className="relative h-44 w-44 sm:h-56 sm:w-56">
          {Array.from({ length: LOSANGOS }, (_, i) => (
            <span key={i} className="celebracao-losango" style={{ '--angulo': `${(360 / LOSANGOS) * i}deg` } as CSSProperties} />
          ))}
          <svg viewBox="0 0 200 200" className="h-full w-full"><D12 cor="var(--esperanca)" numero={depois.nivel} celebrando /></svg>
        </div>
        <div className="celebracao-titulo">
          <h2 id={titulo} className="text-5xl leading-tight text-esperanca-forte">Nível {depois.nivel}</h2>
          <p className="text-base text-texto-suave">{depois.nome || 'Seu personagem'} ficou mais forte.</p>
        </div>
        {ganhos.length > 0 && (
          <ul aria-label="O que você ganhou" className="w-full space-y-2 text-left">
            {ganhos.map((g, i) => (
              <li key={g} className="celebracao-ganho flex items-baseline gap-2.5 text-base" style={{ animationDelay: atrasoDoGanho(i) }}>
                <span aria-hidden className="inline-block h-2 w-2 shrink-0 translate-y-[-1px] rotate-45 rounded-[1px] bg-esperanca" />
                {g}
              </li>
            ))}
          </ul>
        )}
        <Botao ref={botao} className="mt-2 w-full" onClick={aoFechar}>Continuar</Botao>
      </div>
    </div>
  )
}
