// Como um item criado pelo mestre aparece: tipo, patamar, números e características.
import type { ReactNode } from 'react'

import type { ItemProprio } from '../../api/tipos'
import { descreverBonus, NOME_TIPO_PROPRIO, resumoDoItem } from '../../lib/itens'
import { Selo } from '../ui'

export default function FichaItemProprio({ item, acoes }: { item: ItemProprio; acoes?: ReactNode }) {
  const equipamento = item.tipo === 'ARMA' || item.tipo === 'ARMADURA'
  return (
    <article className="space-y-3 rounded-2xl border border-borda bg-superficie p-4 sm:p-5">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg text-esperanca">{item.nome}</h2>
          <p className="text-sm text-texto-suave">{resumoDoItem(item)}</p>
        </div>
        <span className="flex gap-1">
          <Selo>{NOME_TIPO_PROPRIO[item.tipo]}</Selo>
          {equipamento && <Selo>P{item.tier}</Selo>}
        </span>
      </header>
      {item.descricao && <p className="whitespace-pre-line text-sm">{item.descricao}</p>}
      {(item.caracteristicas ?? []).length > 0 && (
        <ul className="space-y-1 text-sm">
          {item.caracteristicas!.map((c, i) => (
            <li key={i}>
              <b>{c.nome}</b>{c.descricao && `: ${c.descricao}`}
              {(c.modificadores ?? []).length > 0 && (
                <span className="block text-xs text-texto-suave">Na ficha: {c.modificadores.map(descreverBonus).join(', ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
    </article>
  )
}
