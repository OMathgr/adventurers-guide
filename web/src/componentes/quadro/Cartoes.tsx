// Os cartões do quadro (nós do React Flow): nota, item da mesa, imagem e o
// título de região do quadro da campanha. Os mesmos no editor e na leitura.
import { Handle, type NodeProps, Position } from '@xyflow/react'

import { urlDaImagem } from '../../api/cliente'
import type { NoDoQuadro } from '../../lib/quadro'
import { Foto } from '../Foto'
import TextoRico from '../TextoRico'

const BORDA: Record<string, string> = {
  padrao: 'border-borda', esperanca: 'border-esperanca', medo: 'border-medo', perigo: 'border-perigo', sucesso: 'border-sucesso',
}

const NOME_ITEM: Record<string, string> = { npc: 'NPC', inimigo: 'Inimigo', encontro: 'Encontro', personagem: 'Personagem' }

/** Um ponto de ligação em cada lado (id = o lado salvo na ligação). O quadro
    usa o modo "solto" do React Flow: qualquer ponto liga em qualquer ponto. */
const PONTOS = [
  ['topo', Position.Top], ['direita', Position.Right], ['baixo', Position.Bottom], ['esquerda', Position.Left],
] as const

function Moldura({ cor, selecionado, revelado, children }:
  { cor?: string | null; selecionado: boolean; revelado?: boolean | null; children: React.ReactNode }) {
  return (
    <div className={`relative w-[220px] rounded-xl border-2 bg-superficie p-3 text-texto shadow-md ${BORDA[cor ?? 'padrao']}
      ${selecionado ? 'ring-2 ring-esperanca ring-offset-2 ring-offset-fundo' : ''}`}>
      {PONTOS.map(([id, lado]) => (
        <Handle key={id} id={id} type="source" position={lado} className="!h-2.5 !w-2.5 !bg-texto-suave" />
      ))}
      {revelado && (
        <span className="absolute -top-2.5 right-2 rounded-full bg-esperanca px-2 text-[10px] font-semibold text-sobre-esperanca"
          title="Os jogadores veem este cartão">revelado</span>
      )}
      {children}
    </div>
  )
}

export function CartaoNota({ data, selected }: NodeProps<NoDoQuadro>) {
  const c = data.cartao
  return (
    <Moldura cor={c.cor} selecionado={selected} revelado={c.revelado}>
      {c.titulo && <p className="font-titulo text-sm">{c.titulo}</p>}
      {c.texto ? <TextoRico texto={c.texto} className="mt-1 max-h-40 overflow-hidden text-xs text-texto-suave" />
        : !c.titulo && <p className="text-xs italic text-texto-suave">Nota vazia</p>}
    </Moldura>
  )
}

export function CartaoItem({ data, selected }: NodeProps<NoDoQuadro>) {
  const c = data.cartao
  const item = data.item
  return (
    <Moldura cor={c.cor} selecionado={selected} revelado={c.revelado}>
      <div className="flex items-center gap-2">
        <Foto id={item?.foto} nome={item?.nome ?? '?'} tamanho="p" />
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wider text-texto-suave">{NOME_ITEM[c.item_tipo ?? ''] ?? 'Item'}</p>
          <p className={`truncate text-sm font-medium ${item?.existe === false ? 'italic text-texto-suave' : ''}`}>
            {item?.nome ?? '…'}
          </p>
        </div>
      </div>
      {c.texto && <TextoRico texto={c.texto} className="mt-1 max-h-24 overflow-hidden text-xs text-texto-suave" />}
    </Moldura>
  )
}

export function CartaoImagem({ data, selected }: NodeProps<NoDoQuadro>) {
  const c = data.cartao
  return (
    <Moldura cor={c.cor} selecionado={selected} revelado={c.revelado}>
      {c.imagem && <img src={urlDaImagem(c.imagem)} alt={c.titulo || 'Imagem do quadro'}
        className="max-h-48 w-full rounded-lg object-contain" draggable={false} />}
      {c.titulo && <p className="mt-1 text-center text-xs text-texto-suave">{c.titulo}</p>}
    </Moldura>
  )
}

export function TituloDeRegiao({ data }: NodeProps) {
  return (
    <p className="whitespace-nowrap font-titulo text-lg text-esperanca">{(data as { titulo: string }).titulo}</p>
  )
}
