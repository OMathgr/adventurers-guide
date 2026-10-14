// Lojas da sessão: o mestre responsável define o que está à venda (preço em
// punhados e estoque opcional) e vende para os personagens da mesa. Vender
// cobra o ouro e entrega o item na hora; quem confere ouro, espaço e limites
// é o motor. À mostra, a loja aparece para os jogadores na aba Mesa.
import { useState } from 'react'

import { useAcaoNaLoja, useLojas, useVender } from '../../api/consultas'
import type { ItemDaLojaEntrada, Loja, Mesa, Sessao, TipoNaLoja } from '../../api/tipos'
import { AvisoDeConflito } from '../../componentes/Conflito'
import { BuscarNoCatalogo } from '../../componentes/inventario/BuscarNoCatalogo'
import { Aviso, Botao, Campo, Carregando, Escolhivel, Selo } from '../../componentes/ui'
import { semConflito } from '../../lib/conflito'
import { formatarOuro } from '../../lib/ouro'

const NOME_TIPO: Record<TipoNaLoja, string> = { ITEM: 'item', ARMA: 'arma', ARMADURA: 'armadura', LIVRE: 'da mesa' }

type Linha = ItemDaLojaEntrada & { rotulo: string }

function paraRascunho(loja: Loja): Linha[] {
  return loja.itens.map((i) => ({
    id: i.id, tipo: i.tipo, ref: i.ref, preco: i.preco.total, moedas: i.preco.moedas ?? 0, estoque: i.estoque,
    rotulo: i.nome,
    nome: i.tipo === 'LIVRE' ? i.nome : '', descricao: i.tipo === 'LIVRE' ? i.texto : '',
  }))
}

function Vender({ mesa, sid, loja, itemId }: { mesa: Mesa; sid: string; loja: Loja; itemId: string }) {
  const vender = useVender(mesa.id, sid, loja.id)
  const [personagem, setPersonagem] = useState(mesa.personagens[0]?.id ?? '')
  const [quantidade, setQuantidade] = useState('1')
  if (mesa.personagens.length === 0) return <p className="text-xs text-texto-suave">Nenhum personagem na mesa.</p>
  return (
    <div className="mt-2 space-y-1">
      <div className="flex flex-wrap items-end gap-2">
        <select aria-label="Vender para" value={personagem} onChange={(e) => setPersonagem(e.target.value)}
          className="rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm">
          {mesa.personagens.map((p) => <option key={p.id} value={p.id}>{p.nome || 'Sem nome'} ({p.jogador})</option>)}
        </select>
        <input type="number" min={1} value={quantidade} aria-label="Quantidade"
          onChange={(e) => setQuantidade(e.target.value)}
          className="w-16 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
        <Botao variante="secundario" disabled={vender.isPending || !personagem || !(Number(quantidade) >= 1)}
          onClick={() => vender.mutate({ item_id: itemId, personagem_id: personagem, quantidade: Number(quantidade) })}>
          Vender
        </Botao>
      </div>
      {vender.data && <p role="status" className="text-xs text-sucesso">{vender.data.notas.join(' ')}</p>}
      <Aviso erro={vender.error} />
    </div>
  )
}

function EditorDeLoja({ mesa, sessao, loja }: { mesa: Mesa; sessao: Sessao; loja: Loja }) {
  const podeEditar = sessao.sou_responsavel
  const podeVender = podeEditar && (mesa.minhas_permissoes as string[]).includes('dar_itens')
  const acao = useAcaoNaLoja(mesa.id, sessao.id)
  // a versão de onde o rascunho partiu (o que estava salvo quando começou a editar)
  const [original, setOriginal] = useState(loja)
  const [nome, setNome] = useState(loja.nome)
  const [visivel, setVisivel] = useState(loja.visivel)
  const [itens, setItens] = useState<Linha[]>(() => paraRascunho(loja))
  const [livre, setLivre] = useState({ nome: '', descricao: '' })
  const [adicionando, setAdicionando] = useState(false)
  const salvo = JSON.stringify([original.nome, original.visivel, paraRascunho(original)])
  const mudou = JSON.stringify([nome, visivel, itens]) !== salvo

  function adotar(nova: Loja) {
    setOriginal(nova)
    setNome(nova.nome)
    setVisivel(nova.visivel)
    setItens(paraRascunho(nova))
  }
  // mudou no servidor (venda, outra aba): sem nada sendo editado, mostra o novo;
  // editando, guarda o rascunho (ao salvar, o servidor avisa do conflito).
  // Ajuste durante a renderização (o jeito que o React recomenda, sem efeito).
  if (loja.versao !== original.versao && !mudou) adotar(loja)
  const salvar = (versao: string | null) => acao.mutate({
    tipo: 'salvar', id: loja.id, nome: nome.trim(), visivel, versao,
    itens: itens.map(({ rotulo: _rotulo, ...resto }) => resto),
  }, { onSuccess: (nova) => { if (nova) adotar(nova) } })
  const mudar = (i: number, parcial: Partial<Linha>) => setItens(itens.map((x, j) => (j === i ? { ...x, ...parcial } : x)))
  const adicionar = (l: Omit<Linha, 'preco' | 'moedas' | 'estoque'>) =>
    setItens([...itens, { ...l, preco: 1, moedas: 0, estoque: null }])

  return (
    <div className="space-y-3 rounded-2xl border border-borda bg-superficie p-4">
      {podeEditar ? (
        <div className="flex flex-wrap items-end gap-3">
          <Campo rotulo="Nome da loja" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)} />
          <label className="mb-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={visivel} onChange={(e) => setVisivel(e.target.checked)} />
            Mostrar aos jogadores (com a sessão em andamento)
          </label>
        </div>
      ) : <h4 className="font-titulo">{loja.nome}</h4>}

      {itens.length === 0 && <p className="text-sm text-texto-suave">Nada à venda ainda.</p>}
      <ul className="space-y-2">
        {itens.map((item, i) => {
          const doServidor = loja.itens.find((x) => x.id === item.id)
          return (
            <li key={item.id || `novo-${i}`} className="rounded-lg border border-borda p-3 text-sm">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <p className="font-medium">{item.rotulo} <Selo>{NOME_TIPO[item.tipo]}</Selo></p>
                {podeEditar ? (
                  <div className="flex flex-wrap items-end gap-2">
                    <label className="flex flex-col gap-1 text-xs">
                      <span className="text-texto-suave">Preço (punhados)</span>
                      <input type="number" min={0} value={item.preco} aria-label={`Preço de ${item.rotulo}`}
                        onChange={(e) => mudar(i, { preco: Math.max(0, Number(e.target.value) || 0) })}
                        className="w-24 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
                    </label>
                    {mesa.usar_moedas && (
                      <label className="flex flex-col gap-1 text-xs">
                        <span className="text-texto-suave">+ moedas</span>
                        <input type="number" min={0} max={9} value={item.moedas} aria-label={`Moedas de ${item.rotulo}`}
                          onChange={(e) => mudar(i, { moedas: Math.min(9, Math.max(0, Number(e.target.value) || 0)) })}
                          className="w-16 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
                      </label>
                    )}
                    <label className="flex flex-col gap-1 text-xs">
                      <span className="text-texto-suave">Estoque (vazio: sem limite)</span>
                      <input type="number" min={0} value={item.estoque ?? ''} aria-label={`Estoque de ${item.rotulo}`}
                        onChange={(e) => mudar(i, { estoque: e.target.value === '' ? null : Math.max(0, Number(e.target.value)) })}
                        className="w-24 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
                    </label>
                    <Botao variante="fantasma" onClick={() => setItens(itens.filter((_, j) => j !== i))}>Tirar</Botao>
                  </div>
                ) : null}
              </div>
              <p className="text-xs text-texto-suave">
                {item.preco === 0 && !item.moedas ? 'de graça' : formatarOuro(item.preco, item.moedas)}{item.estoque !== null && item.estoque !== undefined ? ` · ${item.estoque} em estoque` : ''}
              </p>
              {doServidor?.texto && <p className="mt-1 text-xs text-texto-suave">{doServidor.texto}</p>}
              {podeVender && doServidor && !mudou && <Vender mesa={mesa} sid={sessao.id} loja={loja} itemId={doServidor.id} />}
            </li>
          )
        })}
      </ul>
      {podeVender && mudou && <p className="text-xs text-texto-suave">Salve a loja para vender.</p>}
      {podeEditar && !podeVender && (
        <p className="text-xs text-texto-suave">Quem criou a mesa não liberou "dar itens e ouro" para os mestres: dá para montar, mas não vender.</p>
      )}

      {podeEditar && (
        <div className="space-y-3 border-t border-borda pt-3">
          {adicionando ? (
            <>
              <BuscarNoCatalogo tipos={['SAQUE', 'CONSUMIVEL', 'ARMA', 'ARMADURA']} aoEscolher={(e) => adicionar({
                id: '', tipo: e.tipo === 'ARMA' || e.tipo === 'ARMADURA' ? e.tipo : 'ITEM', ref: e.id,
                nome: '', descricao: '', rotulo: e.nome,
              })} />
              <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
                e.preventDefault()
                adicionar({ id: '', tipo: 'LIVRE', ref: null, nome: livre.nome.trim(), descricao: livre.descricao.trim(),
                  rotulo: livre.nome.trim() })
                setLivre({ nome: '', descricao: '' })
              }}>
                <Campo rotulo="Item da mesa" value={livre.nome} maxLength={120} placeholder="Ex.: Mapa da Cripta"
                  onChange={(e) => setLivre({ ...livre, nome: e.target.value })} />
                <Campo rotulo="Descrição" value={livre.descricao} maxLength={2000}
                  onChange={(e) => setLivre({ ...livre, descricao: e.target.value })} />
                <Botao type="submit" variante="secundario" disabled={!livre.nome.trim()}>Pôr à venda</Botao>
              </form>
              <Botao variante="fantasma" onClick={() => setAdicionando(false)}>Fechar catálogo</Botao>
            </>
          ) : <Botao variante="secundario" onClick={() => setAdicionando(true)}>Adicionar itens</Botao>}
          <div className="flex flex-wrap gap-2">
            <Botao disabled={!mudou || !nome.trim() || acao.isPending} onClick={() => salvar(original.versao)}>
              Salvar loja
            </Botao>
            <Botao variante="perigo" disabled={acao.isPending}
              onClick={() => confirm(`Apagar a loja "${loja.nome}"?`) && acao.mutate({ tipo: 'apagar', id: loja.id })}>
              Apagar loja
            </Botao>
          </div>
        </div>
      )}
      <AvisoDeConflito erro={acao.error} ocupado={acao.isPending}
        aoVerAtual={() => { adotar(loja); acao.reset() }} aoSalvarMesmoAssim={() => salvar(null)} />
      <Aviso erro={semConflito(acao.error)} />
    </div>
  )
}

export default function Lojas({ mesa, sessao }: { mesa: Mesa; sessao: Sessao }) {
  const lojas = useLojas(mesa.id, sessao.id)
  const acao = useAcaoNaLoja(mesa.id, sessao.id)
  const [escolhida, setEscolhida] = useState<string | null>(null)
  const [nome, setNome] = useState('')
  if (lojas.isPending) return <Carregando />
  if (lojas.isError) return <Aviso erro={lojas.error} />
  const lista = lojas.data
  const atual = lista.find((l) => l.id === escolhida) ?? null

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-lg text-esperanca">Lojas</h3>
          <p className="text-xs text-texto-suave">Lugares onde os personagens podem comprar nesta sessão.</p>
        </div>
        {sessao.sou_responsavel && (
          <form className="flex items-end gap-2" onSubmit={(e) => {
            e.preventDefault()
            acao.mutate({ tipo: 'criar', nome: nome.trim() }, {
              onSuccess: (nova) => { if (nova) setEscolhida(nova.id); setNome('') },
            })
          }}>
            <Campo rotulo="Nova loja" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)}
              placeholder="Ex.: Ferreiro de Vila Alta" />
            <Botao type="submit" variante="secundario" disabled={!nome.trim() || acao.isPending}>Criar</Botao>
          </form>
        )}
      </div>
      <Aviso erro={acao.error} />
      {lista.length === 0 && <p className="text-sm text-texto-suave">Nenhuma loja nesta sessão ainda.</p>}
      <ul className="flex flex-wrap gap-2">
        {lista.map((l) => (
          <li key={l.id} className="w-56">
            <Escolhivel selecionado={l.id === atual?.id} onClick={() => setEscolhida(l.id === atual?.id ? null : l.id)}>
              <span className="block font-medium">{l.nome}</span>
              <span className="text-xs text-texto-suave">
                {l.itens.length} {l.itens.length === 1 ? 'item' : 'itens'}{l.visivel ? ' · à mostra' : ''}
              </span>
            </Escolhivel>
          </li>
        ))}
      </ul>
      {atual && <EditorDeLoja key={atual.id} mesa={mesa} sessao={sessao} loja={atual} />}
    </section>
  )
}
