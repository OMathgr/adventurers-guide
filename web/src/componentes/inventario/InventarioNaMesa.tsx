// Inventário de um personagem da mesa, visto pelo mestre: lê com "ver_fichas"
// e, com "dar_itens", dá ou tira ouro e itens (o item vai direto para a ficha):
// do SRD, da biblioteca de itens da mesa (o tesouro que o mestre criou) ou livres.
import { useState } from 'react'

import { useDarNoInventario, useInventarioNaMesa, useItensDaMesa } from '../../api/consultas'
import { NOME_TIPO_PROPRIO, resumoDoItem } from '../../lib/itens'
import { formatarOuro } from '../../lib/ouro'
import { Aviso, Botao, Campo, Carregando } from '../ui'
import { BuscarNoCatalogo } from './BuscarNoCatalogo'
import { MudarOuro } from './Ouro'

export default function InventarioNaMesa({ mesaId, pid, nome, podeDar }: {
  mesaId: string; pid: string; nome: string; podeDar: boolean
}) {
  const [aberto, setAberto] = useState(false)
  const inv = useInventarioNaMesa(mesaId, pid, aberto)
  const dar = useDarNoInventario(mesaId, pid)
  const [livre, setLivre] = useState('')
  const daMesa = useItensDaMesa(mesaId, aberto && podeDar)

  if (!aberto) {
    return <Botao variante="fantasma" onClick={() => setAberto(true)}>Inventário de {nome || 'Sem nome'}</Botao>
  }
  if (inv.isPending) return <Carregando />
  if (inv.isError) return <Aviso erro={inv.error} />
  const { ouro, itens, livres, armas } = inv.data

  return (
    <section aria-label={`Inventário de ${nome}`} className="space-y-2 rounded-xl border border-borda p-3 text-sm">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">Inventário</h4>
        <Botao variante="fantasma" onClick={() => setAberto(false)}>Fechar</Botao>
      </div>
      <p>Ouro: <b>{formatarOuro(ouro.total, ouro.moedas ?? 0)}</b></p>
      <p className="text-xs text-texto-suave">
        {[...itens.map((i) => (i.quantidade > 1 ? `${i.nome} ×${i.quantidade}` : i.nome)),
          ...livres.map((l) => l.nome), ...armas.map((a) => `${a.nome} (guardada)`)].join(', ') || 'Nenhum item.'}
      </p>
      {podeDar && (
        <div className="space-y-3 border-t border-borda pt-2">
          <MudarOuro rotulos={['Dar', 'Tirar']} ocupado={dar.isPending} usaMoedas={inv.data.usa_moedas}
            aoMudar={(valor) => dar.mutate({ tipo: 'ouro', ...valor })} />
          <details>
            <summary className="cursor-pointer text-texto-suave">Dar um item do SRD</summary>
            <div className="mt-2">
              <BuscarNoCatalogo tipos={['SAQUE', 'CONSUMIVEL', 'ARMA']} aoEscolher={(e) => dar.mutate(
                e.tipo === 'ARMA' ? { tipo: 'arma', arma_id: e.id } : { tipo: 'item', item_id: e.id, quantidade: 1 })} />
            </div>
          </details>
          <details>
            <summary className="cursor-pointer text-texto-suave">Dar um item da mesa (criado pelos mestres)</summary>
            <div className="mt-2 space-y-1">
              {daMesa.isPending && <Carregando />}
              {daMesa.data?.length === 0 && (
                <p className="text-xs text-texto-suave">Nenhum item criado ainda (aba Itens da mesa).</p>
              )}
              <ul className="max-h-72 space-y-1 overflow-y-auto pr-1">
                {daMesa.data?.map((i) => (
                  <li key={i.id}>
                    <button type="button" disabled={dar.isPending}
                      onClick={() => dar.mutate({ tipo: 'da_mesa', item_id: i.id, quantidade: 1 })}
                      className="w-full rounded-lg border border-borda bg-superficie px-3 py-2 text-left text-sm hover:border-esperanca">
                      <span className="flex items-center justify-between gap-2">
                        <span className="font-medium">{i.nome}</span>
                        <span className="text-xs text-texto-suave">{NOME_TIPO_PROPRIO[i.tipo]}</span>
                      </span>
                      <span className="line-clamp-2 block text-xs text-texto-suave">{resumoDoItem(i)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-texto-suave">Arma vai para as guardadas; armadura é vestida na hora.</p>
            </div>
          </details>
          <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
            e.preventDefault()
            dar.mutate({ tipo: 'livre', nome: livre, descricao: '', quantidade: 1 }, { onSuccess: () => setLivre('') })
          }}>
            <Campo rotulo="Item livre" value={livre} maxLength={120} onChange={(e) => setLivre(e.target.value)}
              placeholder="Ex.: Chave da torre" />
            <Botao type="submit" variante="secundario" disabled={!livre.trim() || dar.isPending}>Dar</Botao>
          </form>
          <Aviso erro={dar.error} />
        </div>
      )}
    </section>
  )
}
