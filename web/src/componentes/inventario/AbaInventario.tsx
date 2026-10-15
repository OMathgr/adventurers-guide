// Inventário do personagem: ouro, consumíveis (usar já aplica PV/PF/Esperança
// quando o efeito é simples), itens, itens livres e até 2 armas guardadas.
// Limites e efeitos são do motor; a tela só guia e mostra o erro da API.
import { useState } from 'react'

import {
  useAcaoNoInventario, useInventario, useTrocarArma, useUsarConsumivel,
} from '../../api/consultas'
import type { Ficha, ItemNoInventario } from '../../api/tipos'
import { Aviso, Botao, Campo, Carregando, Cartao, Original, Selo } from '../ui'
import { BuscarNoCatalogo } from './BuscarNoCatalogo'
import { MudarOuro, OuroNaFicha } from './Ouro'

const NOME_ORIGEM: Record<string, string> = { SAQUE: 'item', COMUM: 'inicial', CLASSE: 'de classe' }

function UsarConsumivel({ item, personagemId, aoUsar }: {
  item: ItemNoInventario; personagemId: string; aoUsar: (notas: string[]) => void
}) {
  const usar = useUsarConsumivel(personagemId)
  const [rolagem, setRolagem] = useState('')
  const [escolha, setEscolha] = useState<'PV' | 'PF'>('PV')
  return (
    <div className="mt-2 flex flex-wrap items-end gap-2">
      {item.dado && (
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-texto-suave">Resultado do {item.dado.replace(/\+\d+$/, '')} (vazio: o app rola)</span>
          <input type="number" min={1} value={rolagem} onChange={(e) => setRolagem(e.target.value)}
            aria-label={`Resultado do dado de ${item.nome}`}
            className="w-24 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
        </label>
      )}
      {item.escolha && (
        <select aria-label="Limpar" value={escolha} onChange={(e) => setEscolha(e.target.value as 'PV' | 'PF')}
          className="rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm">
          <option value="PV">Limpar PV</option>
          <option value="PF">Limpar PF</option>
        </select>
      )}
      <Botao disabled={usar.isPending} onClick={() => usar.mutate(
        { item_id: item.id, rolagem: rolagem ? Number(rolagem) : null, escolha: item.escolha ? escolha : null },
        { onSuccess: (r) => { setRolagem(''); aoUsar(r.notas) } })}>
        Usar
      </Botao>
      <div className="w-full"><Aviso erro={usar.error} /></div>
    </div>
  )
}

function ArmasGuardadas({ personagemId }: { personagemId: string }) {
  const inv = useInventario(personagemId)
  const acao = useAcaoNoInventario(personagemId)
  const trocar = useTrocarArma(personagemId)
  const [guardando, setGuardando] = useState(false)
  const armas = inv.data?.armas ?? []

  return (
    <Cartao titulo={`Armas guardadas (${armas.length}/2)`}>
      <div className="space-y-3">
        <p className="text-xs text-texto-suave">
          Trocar por uma arma ativa da mesma empunhadura é grátis num descanso ou momento de calma; em perigo, marca 1 PF.
        </p>
        {armas.length === 0 && <p className="text-sm text-texto-suave">Nenhuma arma guardada.</p>}
        <ul className="space-y-2">
          {armas.map((a) => (
            <li key={`${a.indice}-${a.id}`} className="rounded-lg border border-borda p-3 text-sm">
              <p className="flex items-center justify-between gap-2">
                <span className="font-medium">{a.nome}</span>
                <span className="flex gap-1">
                  <Selo>P{a.tier}</Selo><Selo>{a.principal ? 'principal' : 'secundária'}</Selo>
                  {a.duas_maos && <Selo>duas mãos</Selo>}
                </span>
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Botao variante="secundario" disabled={trocar.isPending}
                  onClick={() => trocar.mutate({ indice: a.indice, em_perigo: false })}>Trocar (na calma)</Botao>
                <Botao variante="secundario" disabled={trocar.isPending}
                  onClick={() => trocar.mutate({ indice: a.indice, em_perigo: true })}>Trocar em perigo (1 PF)</Botao>
                <Botao variante="fantasma" disabled={acao.isPending}
                  onClick={() => acao.mutate({ tipo: 'tirar_arma', indice: a.indice })}>Descartar</Botao>
              </div>
            </li>
          ))}
        </ul>
        <Aviso erro={trocar.error ?? acao.error} />
        {armas.length < 2 && (guardando
          ? <BuscarNoCatalogo tipos={['ARMA']} aoEscolher={(e) => acao.mutate({ tipo: 'arma', arma_id: e.id },
            { onSuccess: () => setGuardando(false) })} />
          : <Botao variante="secundario" onClick={() => setGuardando(true)}>Guardar uma arma</Botao>)}
      </div>
    </Cartao>
  )
}

export default function AbaInventario({ personagemId, ficha }: { personagemId: string; ficha: Ficha }) {
  const inv = useInventario(personagemId)
  const acao = useAcaoNoInventario(personagemId)
  const [usando, setUsando] = useState<string | null>(null)
  const [notas, setNotas] = useState<string[]>([])
  const [livre, setLivre] = useState({ nome: '', descricao: '' })

  if (inv.isPending) return <Carregando />
  if (inv.isError) return <Aviso erro={inv.error} />
  const { ouro, itens, livres } = inv.data
  const consumiveis = itens.filter((i) => i.tipo === 'CONSUMIVEL')
  const outros = itens.filter((i) => i.tipo !== 'CONSUMIVEL')
  const tirar = (i: ItemNoInventario) => acao.mutate({ tipo: 'tirar_item', item_id: i.id, quantidade: 1 })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Cartao titulo="Ouro">
        <div className="space-y-3">
          <OuroNaFicha ouro={ouro} usaMoedas={inv.data.usa_moedas} />
          <MudarOuro ocupado={acao.isPending} usaMoedas={inv.data.usa_moedas}
            aoMudar={(valor) => acao.mutate({ tipo: 'ouro', ...valor })} />
          {inv.data.moedas_pela_mesa ? (
            inv.data.usa_moedas && <p className="text-xs text-texto-suave">A mesa usa a regra opcional das moedas.</p>
          ) : (
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={inv.data.usa_moedas} disabled={acao.isPending}
                onChange={(e) => acao.mutate({ tipo: 'usar_moedas', usar: e.target.checked })} />
              Regra opcional das moedas (10 moedas = 1 punhado)
            </label>
          )}
        </div>
      </Cartao>

      <ArmasGuardadas personagemId={personagemId} />

      <Cartao titulo="Consumíveis" className="lg:col-span-2">
        <p className="mb-2 text-xs text-texto-suave">Até 5 de cada. Usar gasta 1.</p>
        {notas.length > 0 && (
          <p role="status" className="mb-2 rounded-lg border border-sucesso/50 bg-sucesso/10 px-3 py-2 text-sm">
            {notas.join(' ')}
          </p>
        )}
        {consumiveis.length === 0 && <p className="text-sm text-texto-suave">Nenhum consumível.</p>}
        <ul className="grid gap-2 sm:grid-cols-2">
          {consumiveis.map((i) => (
            <li key={i.id} className="rounded-lg border border-borda p-3 text-sm">
              <p className="flex items-center justify-between gap-2">
                <span className="font-medium">{i.nome}<Original nome={i.nome} original={i.nome_original} /></span>
                <Selo destaque>×{i.quantidade}</Selo>
              </p>
              <p className="mt-1 text-xs text-texto-suave">{i.texto}</p>
              {i.efeito_automatico && <p className="mt-1 text-xs text-medo">Usar já aplica na ficha.</p>}
              {usando === i.id
                ? <UsarConsumivel item={i} personagemId={personagemId} aoUsar={(n) => { setNotas(n); setUsando(null) }} />
                : (
                  <div className="mt-2 flex gap-2">
                    <Botao variante="secundario" onClick={() => { setUsando(i.id); setNotas([]) }}>Usar…</Botao>
                    <Botao variante="fantasma" disabled={acao.isPending} onClick={() => tirar(i)}>Descartar 1</Botao>
                  </div>
                )}
            </li>
          ))}
        </ul>
      </Cartao>

      <Cartao titulo="Itens">
        {outros.length === 0 && livres.length === 0 && <p className="text-sm text-texto-suave">Nenhum item.</p>}
        <ul className="space-y-2">
          {outros.map((i) => (
            <li key={i.id} className="rounded-lg border border-borda p-3 text-sm">
              <p className="flex items-center justify-between gap-2">
                <span className="font-medium">{i.nome}<Original nome={i.nome} original={i.nome_original} /></span>
                <span className="flex gap-1">
                  {i.reliquia && <Selo destaque>relíquia</Selo>}
                  <Selo>{NOME_ORIGEM[i.tipo] ?? i.tipo}</Selo>
                  {i.quantidade > 1 && <Selo>×{i.quantidade}</Selo>}
                </span>
              </p>
              {i.texto && <p className="mt-1 text-xs text-texto-suave">{i.texto}</p>}
              {i.reliquia === 'EXPERIENCIA' && (
                <label className="mt-2 flex items-center gap-2 text-xs">
                  <span className="text-texto-suave">+1 na Experiência</span>
                  <select value={inv.data.experiencia_da_reliquia ?? ''} aria-label="Experiência da relíquia"
                    onChange={(e) => acao.mutate({ tipo: 'reliquia', experiencia: e.target.value || null })}
                    className="rounded-lg border border-borda bg-fundo px-2 py-1 text-sm">
                    <option value="">Escolha…</option>
                    {Object.keys(ficha.experiencias).map((x) => <option key={x} value={x}>{x}</option>)}
                  </select>
                </label>
              )}
              <Botao variante="fantasma" className="mt-1" disabled={acao.isPending} onClick={() => tirar(i)}>
                {i.quantidade > 1 ? 'Descartar 1' : 'Descartar'}
              </Botao>
            </li>
          ))}
          {livres.map((l) => (
            <li key={l.id} className="rounded-lg border border-borda p-3 text-sm">
              <p className="flex items-center justify-between gap-2">
                <span className="font-medium">{l.nome}</span>
                <span className="flex gap-1"><Selo>da mesa</Selo>{l.quantidade > 1 && <Selo>×{l.quantidade}</Selo>}</span>
              </p>
              {l.descricao && <p className="mt-1 text-xs text-texto-suave">{l.descricao}</p>}
              <Botao variante="fantasma" className="mt-1" disabled={acao.isPending}
                onClick={() => acao.mutate({ tipo: 'tirar_livre', id: l.id, quantidade: 1 })}>
                {l.quantidade > 1 ? 'Descartar 1' : 'Descartar'}
              </Botao>
            </li>
          ))}
        </ul>
      </Cartao>

      <Cartao titulo="Adicionar">
        <div className="space-y-4">
          <BuscarNoCatalogo tipos={['SAQUE', 'CONSUMIVEL']}
            aoEscolher={(e) => acao.mutate({ tipo: 'item', item_id: e.id, quantidade: 1 })} />
          <form className="space-y-2 border-t border-borda pt-3" onSubmit={(e) => {
            e.preventDefault()
            acao.mutate({ tipo: 'livre', nome: livre.nome, descricao: livre.descricao, quantidade: 1 },
              { onSuccess: () => setLivre({ nome: '', descricao: '' }) })
          }}>
            <p className="text-sm font-medium">Item que não está no SRD (com o aval do mestre)</p>
            <Campo rotulo="Nome" value={livre.nome} maxLength={120}
              onChange={(e) => setLivre({ ...livre, nome: e.target.value })} />
            <Campo rotulo="Descrição (opcional)" value={livre.descricao} maxLength={2000}
              onChange={(e) => setLivre({ ...livre, descricao: e.target.value })} />
            <Botao type="submit" variante="secundario" disabled={!livre.nome.trim() || acao.isPending}>Adicionar item</Botao>
          </form>
          <Aviso erro={acao.error} />
        </div>
      </Cartao>
    </div>
  )
}
