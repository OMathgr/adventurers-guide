// Itens criados pelo mestre (privados dos mestres): comuns, consumíveis, armas
// e armaduras, do zero ou a partir de um item do SRD. Entregar é pelo inventário
// do personagem (na sessão) ou pelas lojas; quem recebe guarda uma cópia, então
// editar aqui só vale para as próximas entregas.
import { useState } from 'react'

import {
  type ComVersao, useApagarItemDaMesa, useArmaduras, useArmas, useItemDaMesa, useItensDaMesa, useItensSrd,
  useSalvarItemDaMesa,
} from '../../api/consultas'
import type { ItemProprio, TipoProprio } from '../../api/tipos'
import { AvisoDeConflito } from '../../componentes/Conflito'
import { BuscarNoCatalogo, type Escolhido } from '../../componentes/inventario/BuscarNoCatalogo'
import EditorItemProprio from '../../componentes/inventario/EditorItemProprio'
import FichaItemProprio from '../../componentes/inventario/FichaItemProprio'
import { Aviso, Botao, Carregando, Escolhivel, Selo } from '../../componentes/ui'
import { semConflito } from '../../lib/conflito'
import { deArma, deArmadura, deItem, itemEmBranco, NOME_TIPO_PROPRIO } from '../../lib/itens'

type Painel =
  | { modo: 'vazio' }
  | { modo: 'ver'; id: string }
  | { modo: 'srd' }
  | { modo: 'editar'; item: ComVersao<ItemProprio> }

export default function AbaItens({ mesaId, podeEditar }: { mesaId: string; podeEditar: boolean }) {
  const itens = useItensDaMesa(mesaId)
  const [painel, setPainel] = useState<Painel>({ modo: 'vazio' })
  const [tipoNovo, setTipoNovo] = useState<TipoProprio>('ARMA')
  const atual = useItemDaMesa(mesaId, painel.modo === 'ver' ? painel.id : null)
  const salvar = useSalvarItemDaMesa(mesaId)
  const apagar = useApagarItemDaMesa(mesaId)
  const armas = useArmas()
  const armaduras = useArmaduras()
  const srd = useItensSrd()

  function editar(item: ComVersao<ItemProprio>) {
    salvar.reset()
    setPainel({ modo: 'editar', item: structuredClone(item) })
  }

  function doSrd(e: Escolhido) {
    let base: ItemProprio | undefined
    if (e.tipo === 'ARMA') {
      const a = armas.data?.find((x) => x.id === e.id)
      base = a && deArma(a)
    } else if (e.tipo === 'ARMADURA') {
      const a = armaduras.data?.find((x) => x.id === e.id)
      base = a && deArmadura(a)
    } else {
      const i = srd.data?.find((x) => x.id === e.id)
      base = i && deItem(i)
    }
    if (base) editar(base)
  }

  // a versão é a de quando abriu: se outro mestre salvar antes, avisa
  const salvarEdicao = (item: ComVersao<ItemProprio>) =>
    salvar.mutate(item, { onSuccess: (salvo) => setPainel({ modo: 'ver', id: salvo!.id }) })

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_1fr]">
      <aside className="space-y-3">
        {podeEditar && (
          <div className="space-y-2 rounded-xl border border-borda p-3">
            <div className="flex flex-wrap items-end gap-2">
              <select aria-label="Tipo do item novo" value={tipoNovo} onChange={(e) => setTipoNovo(e.target.value as TipoProprio)}
                className="flex-1 rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
                {(Object.keys(NOME_TIPO_PROPRIO) as TipoProprio[]).map((t) => <option key={t} value={t}>{NOME_TIPO_PROPRIO[t]}</option>)}
              </select>
              <Botao variante="secundario" onClick={() => editar(itemEmBranco(tipoNovo))}>Criar do zero</Botao>
            </div>
            <Botao variante="fantasma" className="w-full" onClick={() => setPainel({ modo: 'srd' })}>
              Começar de um item do SRD
            </Botao>
          </div>
        )}
        {itens.isPending && <Carregando />}
        <Aviso erro={itens.error} />
        {itens.data?.length === 0 && (
          <p className="text-sm text-texto-suave">
            Nenhum item ainda. Crie armas, armaduras, consumíveis e itens para dar aos personagens ou vender nas lojas.
          </p>
        )}
        <ul className="space-y-1.5">
          {itens.data?.map((i) => (
            <li key={i.id}>
              <Escolhivel selecionado={painel.modo === 'ver' && painel.id === i.id} onClick={() => setPainel({ modo: 'ver', id: i.id })}>
                <span className="flex items-center justify-between gap-2">
                  <span className="font-medium">{i.nome}</span>
                  <Selo>{NOME_TIPO_PROPRIO[i.tipo]}</Selo>
                </span>
              </Escolhivel>
            </li>
          ))}
        </ul>
      </aside>

      <section aria-live="polite">
        {painel.modo === 'vazio' && (
          <div className="rounded-2xl border border-dashed border-borda p-10 text-center text-texto-suave">
            Escolha um item para ver. Tudo aqui é visível só para os mestres; entregue na sessão
            (inventário do personagem) ou ponha à venda numa loja.
          </div>
        )}

        {painel.modo === 'srd' && (
          <div className="space-y-3 rounded-2xl border border-borda bg-superficie p-4">
            <h2 className="text-lg text-esperanca">Começar de um item do SRD</h2>
            <p className="text-sm text-texto-suave">Os números e as características vêm junto; depois é só ajustar.</p>
            <BuscarNoCatalogo tipos={['ARMA', 'ARMADURA', 'CONSUMIVEL', 'SAQUE']} aoEscolher={doSrd} />
          </div>
        )}

        {painel.modo === 'ver' && (
          <>
            {atual.isPending && <Carregando />}
            <Aviso erro={atual.error ?? apagar.error} />
            {atual.data && (
              <FichaItemProprio item={atual.data} acoes={podeEditar && <>
                <Botao variante="secundario" onClick={() => editar(atual.data)}>Editar</Botao>
                <Botao variante="perigo" disabled={apagar.isPending}
                  onClick={() => confirm(`Apagar ${atual.data.nome}? Quem já recebeu continua com o item.`)
                    && apagar.mutate(atual.data.id, { onSuccess: () => setPainel({ modo: 'vazio' }) })}>
                  Apagar
                </Botao>
              </>} />
            )}
            {podeEditar && atual.data && (
              <p className="mt-2 text-xs text-texto-suave">
                Editar não muda o que já foi entregue: só as próximas entregas e as lojas abertas.
              </p>
            )}
          </>
        )}

        {painel.modo === 'editar' && (
          <form className="space-y-4 rounded-2xl border border-borda bg-superficie p-4 sm:p-5"
            onSubmit={(e) => { e.preventDefault(); salvarEdicao(painel.item) }}>
            <h2 className="text-lg text-esperanca">{painel.item.id ? `Editar ${painel.item.nome}` : 'Novo item'}</h2>
            <EditorItemProprio valor={painel.item} aoMudar={(item) => setPainel({ modo: 'editar', item: { ...item, versao: painel.item.versao } })} />
            <AvisoDeConflito erro={salvar.error} ocupado={salvar.isPending}
              aoVerAtual={() => { salvar.reset(); setPainel({ modo: 'ver', id: painel.item.id }); void atual.refetch() }}
              aoSalvarMesmoAssim={() => salvarEdicao({ ...painel.item, versao: null })} />
            <Aviso erro={semConflito(salvar.error)} />
            <div className="flex gap-2">
              <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
              <Botao type="button" variante="fantasma"
                onClick={() => setPainel(painel.item.id ? { modo: 'ver', id: painel.item.id } : { modo: 'vazio' })}>
                Cancelar
              </Botao>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
