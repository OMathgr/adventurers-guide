// O que o mestre revelou aos jogadores: inimigos em combate (nome, foto,
// estado de vitalidade e condições; nunca os PV nem os números da ficha) e
// NPCs conhecidos (nome, foto e descrição).
import { useRevelado } from '../api/consultas'
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
  const v = revelado.data
  if (!v || (v.combate.length === 0 && v.npcs.length === 0)) return null

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
