// Busca no catálogo do SRD (itens, consumíveis, armas e armaduras) para
// adicionar ao inventário, dar a um personagem ou pôr numa loja.
import { useMemo, useState } from 'react'

import { useArmaduras, useArmas, useItensSrd } from '../../api/consultas'
import { NOME_ALCANCE, NOME_TIPO_DANO, NOME_TRACO } from '../../lib/rotulos'
import { Carregando, Original, Selo } from '../ui'

export type TipoNoCatalogo = 'SAQUE' | 'CONSUMIVEL' | 'ARMA' | 'ARMADURA'

const NOME_TIPO_CATALOGO: Record<TipoNoCatalogo, string> = {
  SAQUE: 'Item', CONSUMIVEL: 'Consumível', ARMA: 'Arma', ARMADURA: 'Armadura',
}

export type Escolhido = { tipo: TipoNoCatalogo; id: string; nome: string }

type Linha = Escolhido & { original: string; detalhe: string; patamar?: number }

const LIMITE = 40

export function BuscarNoCatalogo({ tipos, aoEscolher }: {
  tipos: TipoNoCatalogo[]; aoEscolher: (e: Escolhido) => void
}) {
  const itens = useItensSrd()
  const armas = useArmas()
  const armaduras = useArmaduras()
  const [busca, setBusca] = useState('')
  const [tipo, setTipo] = useState<TipoNoCatalogo>(tipos[0])

  const linhas = useMemo((): Linha[] => {
    if (tipo === 'ARMA') {
      return (armas.data ?? []).map((a) => ({
        tipo, id: a.id, nome: a.nome, original: a.nome_original, patamar: a.tier,
        detalhe: `${NOME_TRACO[a.traco]} · ${NOME_ALCANCE[a.alcance] ?? a.alcance} · ${a.dado}`
          + `${a.modificador_dano ? `+${a.modificador_dano}` : ''} ${NOME_TIPO_DANO[a.tipo_dano]}${a.duas_maos ? ' · duas mãos' : ''}`,
      }))
    }
    if (tipo === 'ARMADURA') {
      return (armaduras.data ?? []).map((a) => ({
        tipo, id: a.id, nome: a.nome, original: a.nome_original, patamar: a.tier,
        detalhe: `Pontuação ${a.pontuacao} · Limiares base ${a.limiar_maior}/${a.limiar_grave}`,
      }))
    }
    return (itens.data ?? []).filter((i) => i.tipo === tipo)
      .map((i) => ({ tipo, id: i.id, nome: i.nome, original: i.nome_original, detalhe: i.texto }))
  }, [tipo, itens.data, armas.data, armaduras.data])

  const termo = busca.trim().toLocaleLowerCase('pt-BR')
  const filtradas = linhas.filter((l) => !termo || l.nome.toLocaleLowerCase('pt-BR').includes(termo)
    || l.original.toLowerCase().includes(termo))

  const carregando = { SAQUE: itens, CONSUMIVEL: itens, ARMA: armas, ARMADURA: armaduras }[tipo].isPending

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar (português ou inglês)"
          aria-label="Buscar no catálogo" className="min-w-0 rounded-lg border border-borda bg-fundo px-3 py-2 text-sm" />
        {tipos.length > 1 && (
          <select aria-label="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoNoCatalogo)}
            className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
            {tipos.map((t) => <option key={t} value={t}>{NOME_TIPO_CATALOGO[t]}</option>)}
          </select>
        )}
      </div>
      {carregando ? <Carregando /> : (
        <ul className="max-h-72 space-y-1 overflow-y-auto pr-1">
          {filtradas.slice(0, LIMITE).map((l) => (
            <li key={l.id}>
              <button type="button" onClick={() => aoEscolher({ tipo: l.tipo, id: l.id, nome: l.nome })}
                className="w-full rounded-lg border border-borda bg-superficie px-3 py-2 text-left text-sm hover:border-esperanca">
                <span className="flex items-center justify-between gap-2">
                  <span className="font-medium">{l.nome}<Original nome={l.nome} original={l.original} /></span>
                  {l.patamar && <Selo>P{l.patamar}</Selo>}
                </span>
                <span className="line-clamp-2 block text-xs text-texto-suave">{l.detalhe}</span>
              </button>
            </li>
          ))}
          {filtradas.length > LIMITE && (
            <li className="text-xs text-texto-suave">Mais {filtradas.length - LIMITE}: refine a busca.</li>
          )}
          {filtradas.length === 0 && <li className="text-sm text-texto-suave">Nada encontrado.</li>}
        </ul>
      )}
    </div>
  )
}
