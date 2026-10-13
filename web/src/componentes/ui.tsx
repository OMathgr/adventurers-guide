// Peças visuais reutilizadas em todas as telas.
import {
  type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes,
  type TextareaHTMLAttributes, useId,
} from 'react'

import { ErroApi } from '../api/cliente'

const juntar = (...classes: (string | false | undefined)[]) => classes.filter(Boolean).join(' ')

type VarianteBotao = 'primario' | 'secundario' | 'perigo' | 'fantasma'

const ESTILO_BOTAO: Record<VarianteBotao, string> = {
  primario: 'bg-esperanca text-sobre-esperanca hover:bg-esperanca-forte font-semibold',
  secundario: 'bg-superficie-2 text-texto border border-borda hover:border-esperanca',
  perigo: 'bg-transparent text-perigo border border-perigo/60 hover:bg-perigo/10',
  fantasma: 'bg-transparent text-texto-suave hover:text-texto',
}

export function Botao({ variante = 'primario', className, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variante?: VarianteBotao }) {
  return (
    <button
      {...props}
      className={juntar(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm transition',
        'disabled:cursor-not-allowed disabled:opacity-50',
        ESTILO_BOTAO[variante], className,
      )}
    />
  )
}

export function Cartao({ titulo, acao, children, className }:
  { titulo?: ReactNode; acao?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={juntar('rounded-2xl border border-borda bg-superficie p-4 sm:p-5', className)}>
      {(titulo || acao) && (
        <header className="mb-3 flex items-center justify-between gap-2">
          {titulo && <h2 className="text-base text-esperanca">{titulo}</h2>}
          {acao}
        </header>
      )}
      {children}
    </section>
  )
}

const ESTILO_ENTRADA =
  'rounded-lg border border-borda bg-fundo px-3 py-2 text-texto placeholder:text-texto-suave/60 focus:border-esperanca focus:outline-none'

/** Rótulo + entrada + dica. A dica fica fora do <label> (não entra no nome
    acessível) e é ligada à entrada por aria-describedby. */
function ComRotulo({ rotulo, dica, className, children }:
  { rotulo: string; dica?: string; className?: string; children: (idDica?: string) => ReactNode }) {
  const id = useId()
  const idDica = dica ? `${id}-dica` : undefined
  return (
    <div className={juntar('flex flex-col gap-1 text-sm', className)}>
      <label className="flex flex-col gap-1">
        <span className="font-medium text-texto-suave">{rotulo}</span>
        {children(idDica)}
      </label>
      {dica && <span id={idDica} className="text-xs text-texto-suave">{dica}</span>}
    </div>
  )
}

export function Campo({ rotulo, dica, className, ...props }:
  InputHTMLAttributes<HTMLInputElement> & { rotulo: string; dica?: string }) {
  return (
    <ComRotulo rotulo={rotulo} dica={dica} className={className}>
      {(idDica) => <input aria-describedby={idDica} {...props} className={ESTILO_ENTRADA} />}
    </ComRotulo>
  )
}

export function Area({ rotulo, dica, className, ...props }:
  TextareaHTMLAttributes<HTMLTextAreaElement> & { rotulo: string; dica?: string }) {
  return (
    <ComRotulo rotulo={rotulo} dica={dica} className={className}>
      {(idDica) => <textarea rows={3} aria-describedby={idDica} {...props} className={ESTILO_ENTRADA} />}
    </ComRotulo>
  )
}

export function Selecao({ rotulo, opcoes, className, ...props }:
  SelectHTMLAttributes<HTMLSelectElement> & { rotulo: string; opcoes: [valor: string, texto: string][] }) {
  return (
    <label className={juntar('flex flex-col gap-1 text-sm', className)}>
      <span className="font-medium text-texto-suave">{rotulo}</span>
      <select {...props} className={ESTILO_ENTRADA}>
        {opcoes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
      </select>
    </label>
  )
}

/** Abas simples (botões com aria-selected). */
export function Abas<T extends string>({ abas, atual, aoTrocar }:
  { abas: [T, string][]; atual: T; aoTrocar: (aba: T) => void }) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-borda">
      {abas.map(([id, nome]) => (
        <button key={id} role="tab" type="button" aria-selected={id === atual} onClick={() => aoTrocar(id)}
          className={juntar(
            '-mb-px border-b-2 px-4 py-2 text-sm transition',
            id === atual ? 'border-esperanca text-esperanca' : 'border-transparent text-texto-suave hover:text-texto',
          )}>
          {nome}
        </button>
      ))}
    </div>
  )
}

export function Aviso({ erro, children }: { erro?: unknown; children?: ReactNode }) {
  if (!erro && !children) return null
  const texto = erro instanceof ErroApi || erro instanceof Error ? erro.message : children
  return (
    <p role="alert" className="rounded-lg border border-perigo/50 bg-perigo/10 px-3 py-2 text-sm text-perigo">
      {texto}
    </p>
  )
}

export function Carregando({ texto = 'Carregando…' }: { texto?: string }) {
  return <p className="py-8 text-center text-texto-suave" aria-live="polite">{texto}</p>
}

export function Selo({ children, destaque }: { children: ReactNode; destaque?: boolean }) {
  return (
    <span className={juntar(
      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
      destaque ? 'bg-esperanca/15 text-esperanca' : 'bg-superficie-2 text-texto-suave',
    )}>
      {children}
    </span>
  )
}

/** Quadradinhos de PV/Fadiga/armadura: `marcados` de `total`. */
export function Espacos({ total, marcados, rotulo, cor = 'esperanca' }:
  { total: number; marcados: number; rotulo: string; cor?: 'esperanca' | 'medo' | 'perigo' }) {
  const fundo = { esperanca: 'bg-esperanca', medo: 'bg-medo', perigo: 'bg-perigo' }[cor]
  return (
    <div className="flex flex-wrap gap-1" role="img" aria-label={`${rotulo}: ${marcados} de ${total} marcados`}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={juntar('h-4 w-6 rounded-sm border border-borda', i < marcados && fundo)} />
      ))}
    </div>
  )
}

/** Quadradinhos clicáveis: clicar no quadradinho N deixa N marcados; clicar
    no último marcado desmarca ele (como riscar e apagar na ficha de papel). */
export function EspacosClicaveis({ total, marcados, rotulo, cor = 'esperanca', aoMudar, desabilitado, sufixo = 'marcados' }: {
  total: number; marcados: number; rotulo: string; cor?: 'esperanca' | 'medo' | 'perigo'
  aoMudar: (marcados: number) => void; desabilitado?: boolean
  /** Fim da descrição para leitores de tela ("2 de 4 marcados"); vazio quando o rótulo já diz o que conta. */
  sufixo?: string
}) {
  const fundo = { esperanca: 'bg-esperanca', medo: 'bg-medo', perigo: 'bg-perigo' }[cor]
  return (
    <div className="flex flex-wrap gap-1" role="group"
      aria-label={`${rotulo}: ${marcados} de ${total}${sufixo ? ` ${sufixo}` : ''}`}>
      {Array.from({ length: total }, (_, i) => (
        <button key={i} type="button" disabled={desabilitado}
          aria-label={`${rotulo} ${i + 1}`} aria-pressed={i < marcados}
          onClick={() => aoMudar(i + 1 === marcados ? i : i + 1)}
          className={juntar('h-5 w-6 rounded-sm border border-borda transition hover:border-texto disabled:cursor-wait',
            i < marcados && fundo)} />
      ))}
    </div>
  )
}

/** Losangos de Esperança. */
export function Esperanca({ atual, maximo }: { atual: number; maximo: number }) {
  return (
    <div className="flex gap-1.5" role="img" aria-label={`Esperança: ${atual} de ${maximo}`}>
      {Array.from({ length: maximo }, (_, i) => (
        <span key={i} className={juntar(
          'h-4 w-4 rotate-45 rounded-[3px] border-2 border-esperanca',
          i < atual && 'bg-esperanca',
        )} />
      ))}
    </div>
  )
}

/** Nome original (inglês, do SRD) ao lado do traduzido, para quem consulta
    material oficial. Some quando os dois são iguais. */
export function Original({ nome, original }: { nome?: string | null; original?: string | null }) {
  if (!original || original === nome) return null
  return <span className="ml-1.5 text-xs font-normal italic text-texto-suave" lang="en">{original}</span>
}

/** Opção clicável em lista (classe, carta, ancestralidade...). */
export function Escolhivel({ selecionado, desabilitado, onClick, children }:
  { selecionado: boolean; desabilitado?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={desabilitado}
      aria-pressed={selecionado}
      className={juntar(
        'w-full rounded-xl border p-3 text-left transition',
        selecionado ? 'border-esperanca bg-esperanca/10' : 'border-borda bg-superficie hover:border-texto-suave',
        desabilitado && 'cursor-not-allowed opacity-40',
      )}
    >
      {children}
    </button>
  )
}

/** Barra de etapas dos assistentes. */
export function Etapas({ etapas, atual }: { etapas: string[]; atual: number }) {
  return (
    <ol className="mb-6 flex flex-wrap gap-x-4 gap-y-2 text-xs" aria-label="Etapas">
      {etapas.map((nome, i) => (
        <li key={nome} aria-current={i === atual ? 'step' : undefined}
          className={juntar('flex items-center gap-1.5', i === atual ? 'text-esperanca' : i < atual ? 'text-texto' : 'text-texto-suave')}>
          <span className={juntar(
            'flex h-5 w-5 items-center justify-center rounded-full border text-[10px]',
            i === atual ? 'border-esperanca bg-esperanca text-sobre-esperanca' : 'border-borda',
          )}>{i + 1}</span>
          {nome}
        </li>
      ))}
    </ol>
  )
}
