// O que o mestre revelou aos jogadores: inimigos em combate (nome, foto,
// estado de vitalidade e condições; nunca os PV nem os números da ficha) e
// NPCs conhecidos (nome, foto e descrição) e lojas à mostra (itens, preços e
// estoque; quem vende é o mestre).
import { useRevelado } from '../api/consultas'
import type { VistaDosJogadores as Vista } from '../api/tipos'
import { resumoDoItem } from '../lib/itens'
import { formatarOuro } from '../lib/ouro'
import { condicao, NOME_VITALIDADE } from '../lib/rotulos'
import { Foto } from './Foto'
import TextoRico from './TextoRico'
import { Aviso, Cartao } from './ui'

/** Três barrinhas: cheia (3), metade (2), baixa (1), derrotado (0). */
const NIVEL: Record<string, number> = { vida_cheia: 3, metade_da_vida: 2, vida_baixa: 1, derrotado: 0 }
const COR: Record<string, string> = {
  vida_cheia: 'bg-sucesso', metade_da_vida: 'bg-esperanca', vida_baixa: 'bg-perigo', derrotado: 'bg-borda',
}

function Vitalidade({ estado }: { estado: string }) {
  const nivel = NIVEL[estado] ?? 0
  return (
    <span className="flex items-center gap-2" role="img" aria-label={NOME_VITALIDADE[estado] ?? estado}>
      <span aria-hidden className="flex gap-0.5">
        {[1, 2, 3].map((i) => (
          <span key={i} className={`h-2.5 w-5 rounded-sm border border-borda ${i <= nivel ? COR[estado] : ''}`} />
        ))}
      </span>
      <span className="text-xs text-texto-suave">{NOME_VITALIDADE[estado] ?? estado}</span>
    </span>
  )
}

export default function VistaDosJogadores({ mesaId }: { mesaId: string }) {
  const revelado = useRevelado(mesaId)
  if (revelado.isError) return <Aviso erro={revelado.error} />
  return revelado.data ? <Revelado v={revelado.data} /> : null
}

/** Combate, lojas e NPCs à mostra (a sessão passa só os dela). */
export function Revelado({ v }: { v: Vista }) {
  if (v.combate.length === 0 && v.npcs.length === 0 && (v.lojas ?? []).length === 0) return null

  return (
    <>
      {v.combate.map((e) => (
        <Cartao key={e.id} titulo={`Em combate: ${e.nome}`} className="lg:col-span-2">
          <p className="mb-3 text-xs text-texto-suave">Sessão de {e.mestre}. Atualiza sozinho durante a luta.</p>
          {e.inimigos.length === 0 && <p className="text-sm text-texto-suave">Nenhum inimigo à vista.</p>}
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {e.inimigos.map((i) => (
              <li key={i.id} aria-label={i.rotulo}
                className={`flex gap-3 rounded-xl border border-borda bg-fundo/60 p-3 ${i.vitalidade === 'derrotado' ? 'opacity-50' : ''}`}>
                <Foto id={i.foto} nome={i.rotulo} tamanho="p" />
                <div className="min-w-0 space-y-1">
                  <p className="font-medium">{i.rotulo}</p>
                  <Vitalidade estado={i.vitalidade} />
                  {i.condicoes.length > 0 && (
                    <p className="flex flex-wrap gap-1">
                      {i.condicoes.map((c) => (
                        <span key={c} className="rounded-full bg-perigo/15 px-2 py-0.5 text-xs text-perigo">{condicao(c)}</span>
                      ))}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Cartao>
      ))}
      {(v.lojas ?? []).map((l) => (
        <Cartao key={l.id} titulo={`Loja: ${l.nome}`} className="lg:col-span-2">
          <p className="mb-3 text-xs text-texto-suave">Sessão de {l.mestre}. Para comprar, fale com o mestre.</p>
          {l.itens.length === 0 && <p className="text-sm text-texto-suave">Nada à venda.</p>}
          <ul className="grid gap-2 sm:grid-cols-2">
            {l.itens.map((i) => (
              <li key={i.id} className={`rounded-xl border border-borda bg-fundo/60 p-3 text-sm ${i.estoque === 0 ? 'opacity-50' : ''}`}>
                <p className="flex items-center justify-between gap-2">
                  <span className="font-medium">{i.nome}</span>
                  <span className="text-esperanca">{i.preco.total === 0 && !i.preco.moedas ? 'de graça' : formatarOuro(i.preco.total, i.preco.moedas ?? 0)}</span>
                </p>
                {i.proprio && <p className="mt-1 text-xs text-texto-suave">{resumoDoItem(i.proprio)}</p>}
                {i.texto && <p className="mt-1 text-xs text-texto-suave">{i.texto}</p>}
                {i.estoque !== null && i.estoque !== undefined && (
                  <p className="mt-1 text-xs text-texto-suave">{i.estoque === 0 ? 'Esgotado' : `${i.estoque} em estoque`}</p>
                )}
              </li>
            ))}
          </ul>
        </Cartao>
      ))}
      {v.npcs.length > 0 && (
        <Cartao titulo="NPCs conhecidos" className="lg:col-span-2">
          <ul className="grid gap-3 sm:grid-cols-2">
            {v.npcs.map((n) => (
              <li key={n.id} className="flex gap-3">
                <Foto id={n.foto} nome={n.nome} />
                <div className="min-w-0">
                  <p className="font-medium">{n.nome}</p>
                  {n.descricao && <TextoRico texto={n.descricao} className="text-sm text-texto-suave" />}
                </div>
              </li>
            ))}
          </ul>
        </Cartao>
      )}
    </>
  )
}
