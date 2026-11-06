// Peças visuais reutilizadas em todas as telas.
import {
  type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type Ref, type SelectHTMLAttributes,
  type TextareaHTMLAttributes, useEffect, useId, useLayoutEffect, useRef, useState,
} from 'react'

import { ErroApi } from '../api/cliente'

const juntar = (...classes: (string | false | undefined)[]) => classes.filter(Boolean).join(' ')

type VarianteBotao = 'primario' | 'secundario' | 'perigo' | 'fantasma'

const ESTILO_BOTAO: Record<VarianteBotao, string> = {
  primario: 'bg-esperanca text-sobre-esperanca hover:bg-esperanca-forte font-semibold',
  secundario: 'bg-superficie-2 text-texto border border-borda-campo hover:border-texto',
  perigo: 'bg-transparent text-perigo border border-perigo/60 hover:bg-perigo/10',
  fantasma: 'bg-transparent text-texto-suave hover:text-texto',
}

/** O valor que acabou de mudar (`de` e `para`), por um instante, para a tela reagir.
    Ao abrir a tela nada muda, então nada anima. */
export function useMudanca<T>(valor: T, duracao = 400) {
  const anterior = useRef(valor)
  const [mudanca, setMudanca] = useState<{ de: T; para: T } | null>(null)
  useEffect(() => {
    if (Object.is(anterior.current, valor)) return
    setMudanca({ de: anterior.current, para: valor })
    anterior.current = valor
    const espera = setTimeout(() => setMudanca(null), duracao)
    return () => clearTimeout(espera)
  }, [valor, duracao])
  return mudanca
}

/** A posição `i` está entre o valor antigo e o novo? (a marca que acabou de encher ou esvaziar) */
export const mudouAqui = (m: { de: number; para: number } | null, i: number) =>
  !!m && i >= Math.min(m.de, m.para) && i < Math.max(m.de, m.para)

export function Botao({ variante = 'primario', className, ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variante?: VarianteBotao; ref?: Ref<HTMLButtonElement> }) {
  return (
    <button
      {...props}
      className={juntar(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm transition active:translate-y-px max-sm:min-h-11',
        // desabilitado é sempre neutro: o laranja apagado sobre o azul virava marrom
        'disabled:cursor-not-allowed disabled:border disabled:border-borda disabled:bg-superficie-2 disabled:font-normal disabled:text-texto-suave',
        ESTILO_BOTAO[variante], className,
      )}
    />
  )
}

/** `destaque`: o título em laranja, para o que é do personagem (habilidades, herança, cartas). */
export function Cartao({ titulo, acao, children, className, destaque }:
  { titulo?: ReactNode; acao?: ReactNode; children: ReactNode; className?: string; destaque?: boolean }) {
  return (
    <section className={juntar('rounded-2xl border border-borda bg-superficie p-4 sm:p-5', className)}>
      {(titulo || acao) && (
        <header className="mb-3 flex items-center gap-3">
          {titulo && <h2 className={juntar('rubrica', destaque && 'text-esperanca-forte')}>{titulo}</h2>}
          <span aria-hidden className="h-px min-w-4 flex-1 bg-borda" />
          {acao}
        </header>
      )}
      {children}
    </section>
  )
}

/** Seção aberta, sem caixa: o título de livro e o filete. Para o conteúdo principal da tela. */
export function Secao({ titulo, children, className }: { titulo: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={juntar('space-y-3', className)}>
      <header className="flex items-center gap-3">
        <h2 className="rubrica">{titulo}</h2>
        <span aria-hidden className="h-px min-w-4 flex-1 bg-borda" />
      </header>
      {children}
    </section>
  )
}

const ESTILO_ENTRADA =
  'rounded-lg border border-borda-campo bg-fundo px-3 py-2 text-texto placeholder:text-texto-suave focus:border-esperanca focus:outline-none max-sm:min-h-11'

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

/** Abas simples (botões com aria-selected). No celular a barra rola para os lados. */
export function Abas<T extends string>({ abas, atual, aoTrocar }:
  { abas: [T, string][]; atual: T; aoTrocar: (aba: T) => void }) {
  const barra = useRef<HTMLDivElement>(null)
  const marca = useRef<HTMLSpanElement>(null)
  // a marca desliza até a aba escolhida; mede de novo se o tamanho mudar (fonte carregada, tela girada)
  useLayoutEffect(() => {
    const b = barra.current
    const medir = () => {
      const aba = b?.querySelector<HTMLElement>('[aria-selected="true"]')
      if (!aba || !marca.current) return
      marca.current.style.translate = `${aba.offsetLeft}px`
      marca.current.style.width = `${aba.offsetWidth}px`
    }
    medir()
    const observador = new ResizeObserver(medir)
    if (b) observador.observe(b)
    document.fonts?.ready.then(medir)
    return () => observador.disconnect()
  }, [atual, abas.length])
  useEffect(() => {
    // a aba escolhida não pode ficar cortada na borda (só rola a barra, nunca a página)
    const b = barra.current
    const aba = b?.querySelector<HTMLElement>('[aria-selected="true"]')
    if (!b || !aba) return
    if (aba.offsetLeft < b.scrollLeft) b.scrollLeft = aba.offsetLeft
    else if (aba.offsetLeft + aba.offsetWidth > b.scrollLeft + b.clientWidth) {
      b.scrollLeft = aba.offsetLeft + aba.offsetWidth - b.clientWidth
    }
  }, [atual])
  return (
    <div ref={barra} role="tablist" className="relative flex gap-1 overflow-x-auto shadow-[inset_0_-1px_0_var(--borda)] [scrollbar-width:none]">
      {abas.map(([id, nome]) => (
        <button key={id} role="tab" type="button" aria-selected={id === atual} onClick={() => aoTrocar(id)}
          className={juntar(
            'shrink-0 whitespace-nowrap px-3 py-2.5 text-sm transition sm:px-4',
            id === atual ? 'font-semibold text-esperanca-forte' : 'text-texto-suave hover:text-texto',
          )}>
          {nome}
        </button>
      ))}
      <span ref={marca} data-marca-da-aba aria-hidden className="pointer-events-none absolute bottom-0 left-0 h-0.5 bg-esperanca" />
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

export function Selo({ children, destaque, tom }: { children: ReactNode; destaque?: boolean; tom?: 'esperanca' | 'medo' }) {
  return (
    <span className={juntar(
      'inline-flex items-center whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium',
      tom === 'esperanca' ? 'border-esperanca text-esperanca-forte'
        : tom === 'medo' ? 'border-medo text-medo'
          : destaque ? 'border-texto text-texto' : 'border-borda-campo text-texto-suave',
    )}>
      {children}
    </span>
  )
}

// cada recurso tem a sua cor: laranja é só da Esperança, azul é só do Medo
type CorDeEspaco = 'pv' | 'fadiga' | 'armadura' | 'perigo'
const FUNDO_DE_ESPACO: Record<CorDeEspaco, string> = {
  pv: 'bg-pv', fadiga: 'bg-fadiga', armadura: 'bg-texto-suave', perigo: 'bg-perigo',
}

/** Quadradinhos de PV/Fadiga/armadura. Com `restantes`, o padrão do projeto
    para PV/PF (PJs e inimigos): começam cheios e esvaziam com o dano
    (quadradinho cheio = o que resta). A API continua contando os marcados. */
export function Espacos({ total, marcados, rotulo, cor = 'pv', restantes }:
  { total: number; marcados: number; rotulo: string; cor?: CorDeEspaco; restantes?: boolean }) {
  const fundo = FUNDO_DE_ESPACO[cor]
  const cheios = restantes ? total - marcados : marcados
  const mudanca = useMudanca(cheios)
  const descricao = restantes ? `${rotulo} restantes: ${cheios} de ${total}` : `${rotulo}: ${marcados} de ${total} marcados`
  return (
    <div className="flex flex-wrap gap-1" role="img" aria-label={descricao}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={juntar('h-4 w-6 rounded-sm border border-borda-campo transition-colors duration-200', i < cheios && fundo, mudouAqui(mudanca, i) && 'marca-muda')} />
      ))}
    </div>
  )
}

/** Quadradinhos clicáveis: clicar no quadradinho N deixa N marcados; clicar
    no último marcado desmarca ele (como riscar e apagar na ficha de papel). */
export function EspacosClicaveis({ total, marcados, rotulo, cor = 'pv', aoMudar, desabilitado, sufixo = 'marcados' }: {
  total: number; marcados: number; rotulo: string; cor?: CorDeEspaco
  aoMudar: (marcados: number) => void; desabilitado?: boolean
  /** Fim da descrição para leitores de tela ("2 de 4 marcados"); vazio quando o rótulo já diz o que conta. */
  sufixo?: string
}) {
  const fundo = FUNDO_DE_ESPACO[cor]
  const mudanca = useMudanca(marcados)
  return (
    <div className="flex flex-wrap gap-1" role="group"
      aria-label={`${rotulo}: ${marcados} de ${total}${sufixo ? ` ${sufixo}` : ''}`}>
      {Array.from({ length: total }, (_, i) => (
        <button key={i} type="button" disabled={desabilitado}
          aria-label={`${rotulo} ${i + 1}`} aria-pressed={i < marcados}
          onClick={() => aoMudar(i + 1 === marcados ? i : i + 1)}
          className={juntar('h-5 w-6 rounded-sm border border-borda-campo transition hover:border-texto disabled:cursor-wait max-sm:h-10 max-sm:w-10',
            i < marcados && fundo, mudouAqui(mudanca, i) && 'marca-muda')} />
      ))}
    </div>
  )
}

/** Losangos de Esperança. */
export function Esperanca({ atual, maximo }: { atual: number; maximo: number }) {
  const mudanca = useMudanca(atual)
  return (
    <div className="flex flex-wrap gap-x-1.5 gap-y-2" role="img" aria-label={`Esperança: ${atual} de ${maximo}`}>
      {Array.from({ length: maximo }, (_, i) => (
        <span key={i} className={juntar(
          // sem encolher: comprimido e girado, o losango viraria um retângulo na diagonal
          'h-4 w-4 shrink-0 rotate-45 rounded-[3px] border-2 border-esperanca transition-colors duration-200',
          i < atual && 'bg-esperanca', mudouAqui(mudanca, i) && 'marca-muda',
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
        'relative w-full rounded-xl border p-3 text-left transition',
        selecionado ? 'border-esperanca bg-esperanca/10 pr-8' : 'border-borda-campo bg-superficie hover:border-texto-suave',
        desabilitado && 'cursor-not-allowed opacity-40',
      )}
    >
      {/* a seleção não depende só da cor */}
      {selecionado && (
        <svg viewBox="0 0 16 16" aria-hidden className="absolute right-2.5 top-3 h-4 w-4 text-esperanca-forte">
          <path d="M3 8.5 6.5 12 13 4.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
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
          className={juntar('flex items-center gap-1.5', i === atual ? 'font-semibold text-esperanca-forte' : i < atual ? 'text-texto' : 'text-texto-suave')}>
          <span className={juntar(
            'flex h-6 w-6 items-center justify-center rounded-sm border text-xs',
            i === atual ? 'border-esperanca bg-esperanca text-sobre-esperanca' : 'border-borda-campo',
          )}>{i + 1}</span>
          {nome}
        </li>
      ))}
    </ol>
  )
}
