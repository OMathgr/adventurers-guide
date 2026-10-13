// Quadro (mapa mental) da sessão. O mestre responsável cria cartões (notas,
// itens da mesa, imagens), arrasta, liga com setas e marca o que os
// jogadores podem ver. Salva sozinho depois de cada mudança. Quem recebeu a
// sessão compartilhada vê sem editar.
import '@xyflow/react/dist/style.css'

import {
  addEdge, applyEdgeChanges, applyNodeChanges, Background, type Connection, ConnectionMode, Controls, type Edge,
  type EdgeChange, type NodeChange, ReactFlow,
} from '@xyflow/react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { useEnviarImagem, useInimigos, useNpcs, useQuadro, useSalvarQuadro } from '../../api/consultas'
import type { Cartao, ItemNoQuadro, Mesa, QuadroSaida, Sessao, TipoItem } from '../../api/tipos'
import { TIPOS_DE_CARTAO } from '../../componentes/quadro/tipos'
import { Area, Aviso, Botao, Campo, Carregando, Selecao } from '../../componentes/ui'
import { type NoDoQuadro, paraArestas, paraNos, paraQuadro } from '../../lib/quadro'

const CORES: [string, string][] = [
  ['padrao', 'Neutra'], ['esperanca', 'Laranja'], ['medo', 'Azul'], ['perigo', 'Vermelha'], ['sucesso', 'Verde'],
]
const NOME_ITEM: Record<TipoItem, string> = { npc: 'NPC', inimigo: 'Inimigo', encontro: 'Encontro', personagem: 'Personagem' }

const novoId = () => (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`)

/** Tema do React Flow igual ao do site. */
const modoDeCor = () => (document.documentElement.dataset.tema === 'claro' ? 'light' : 'dark')

function PainelDoCartao({ no, somenteLeitura, aoMudar, aoApagar }: {
  no: NoDoQuadro; somenteLeitura: boolean; aoMudar: (c: Partial<Cartao>) => void; aoApagar: () => void
}) {
  const c = no.data.cartao
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-wider text-texto-suave">
        {c.tipo === 'nota' ? 'Nota' : c.tipo === 'imagem' ? 'Imagem' : NOME_ITEM[c.item_tipo as TipoItem]}
      </p>
      {c.tipo === 'item' && <p className="font-medium">{no.data.item?.nome}</p>}
      <Campo rotulo={c.tipo === 'imagem' ? 'Legenda' : 'Título'} value={c.titulo ?? ''} maxLength={120}
        disabled={somenteLeitura} onChange={(e) => aoMudar({ titulo: e.target.value })} />
      {c.tipo !== 'imagem' && (
        <Area rotulo={c.tipo === 'item' ? 'Anotação' : 'Texto'} rows={5} value={c.texto ?? ''} maxLength={4000}
          disabled={somenteLeitura} dica="**negrito** e _itálico_ funcionam."
          onChange={(e) => aoMudar({ texto: e.target.value })} />
      )}
      <Selecao rotulo="Cor" value={c.cor ?? 'padrao'} opcoes={CORES} disabled={somenteLeitura}
        onChange={(e) => aoMudar({ cor: e.target.value })} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={!!c.revelado} disabled={somenteLeitura}
          onChange={(e) => aoMudar({ revelado: e.target.checked })} />
        Mostrar aos jogadores
      </label>
      <p className="text-xs text-texto-suave">
        Revelado, o cartão vai para o quadro da campanha (os jogadores veem título, texto e o item). Setas só
        aparecem entre dois cartões revelados.
      </p>
      {!somenteLeitura && <Botao variante="perigo" onClick={aoApagar}>Apagar cartão</Botao>}
    </div>
  )
}

function NovoItem({ mesa, sessao, aoEscolher }:
  { mesa: Mesa; sessao: Sessao; aoEscolher: (tipo: TipoItem, id: string, item: ItemNoQuadro) => void }) {
  const [tipo, setTipo] = useState<TipoItem>('npc')
  const [id, setId] = useState('')
  const npcs = useNpcs(mesa.id)
  const inimigos = useInimigos(mesa.id)
  const opcoes: { id: string; nome: string; foto?: string | null; descricao?: string }[] =
    tipo === 'npc' ? (npcs.data ?? []).map((n) => ({ id: n.id, nome: n.nome, foto: n.foto, descricao: n.descricao }))
      : tipo === 'inimigo' ? (inimigos.data ?? []).map((i) => ({ id: i.id, nome: i.nome }))
        : tipo === 'encontro' ? sessao.encontros.map((e) => ({ id: e.id, nome: e.nome }))
          : mesa.personagens.map((p) => ({ id: p.id, nome: p.nome || 'Sem nome', foto: p.foto }))
  return (
    <div className="flex flex-wrap items-end gap-2">
      <Selecao rotulo="Item da mesa" value={tipo} onChange={(e) => { setTipo(e.target.value as TipoItem); setId('') }}
        opcoes={Object.entries(NOME_ITEM)} />
      <Selecao rotulo="Qual" value={id} onChange={(e) => setId(e.target.value)} className="min-w-40"
        opcoes={[['', opcoes.length ? 'Escolha…' : 'Nada aqui ainda'], ...opcoes.map((o): [string, string] => [o.id, o.nome])]} />
      <Botao variante="secundario" disabled={!id} onClick={() => {
        const o = opcoes.find((x) => x.id === id)!
        aoEscolher(tipo, id, { nome: o.nome, foto: o.foto ?? null, descricao: o.descricao ?? '', existe: true })
        setId('')
      }}>Pôr no quadro</Botao>
    </div>
  )
}

function Editor({ mesa, sessao, inicial }: { mesa: Mesa; sessao: Sessao; inicial: QuadroSaida }) {
  const somenteLeitura = !sessao.sou_responsavel
  const [nos, setNos] = useState<NoDoQuadro[]>(() => paraNos(inicial.cartoes, inicial.itens))
  const [arestas, setArestas] = useState<Edge[]>(() => paraArestas(inicial.ligacoes))
  const [sujo, setSujo] = useState(false)
  const salvar = useSalvarQuadro(mesa.id, sessao.id)
  const { mutate: gravar } = salvar
  const enviar = useEnviarImagem()
  const entradaImagem = useRef<HTMLInputElement>(null)

  // salva sozinho 800 ms depois da última mudança
  useEffect(() => {
    if (!sujo || somenteLeitura) return
    const t = setTimeout(() => { setSujo(false); gravar(paraQuadro(nos, arestas)) }, 800)
    return () => clearTimeout(t)
  }, [sujo, nos, arestas, somenteLeitura, gravar])

  const mudou = () => setSujo(true)
  const onNodesChange = useCallback((m: NodeChange<NoDoQuadro>[]) => {
    setNos((n) => applyNodeChanges(m, n))
    // seleção e medida não precisam salvar; arrastar, apagar e mudar sim
    if (m.some((x) => x.type !== 'select' && x.type !== 'dimensions')) mudou()
  }, [])
  const onEdgesChange = useCallback((m: EdgeChange[]) => {
    setArestas((a) => applyEdgeChanges(m, a))
    if (m.some((x) => x.type !== 'select')) mudou()
  }, [])
  const onConnect = useCallback((c: Connection) => {
    setArestas((a) => addEdge({ ...c, id: novoId(), data: { rotulo: '' } }, a))
    mudou()
  }, [])

  const selecionado = nos.find((n) => n.selected)
  const arestaSelecionada = arestas.find((a) => a.selected)

  function adicionar(cartao: Partial<Cartao> & Pick<Cartao, 'tipo'>, item?: ItemNoQuadro) {
    const id = novoId()
    const deslocamento = (nos.length % 8) * 30
    const c = { id, x: 40 + deslocamento, y: 40 + deslocamento, titulo: '', texto: '', cor: 'padrao', revelado: false, ...cartao } as Cartao
    setNos((n) => [...n.map((x) => ({ ...x, selected: false })),
      { id, type: c.tipo, position: { x: c.x!, y: c.y! }, selected: true, data: { cartao: c, item } }])
    mudou()
  }

  function mudarCartao(id: string, parcial: Partial<Cartao>) {
    setNos((n) => n.map((x) => (x.id === id ? { ...x, data: { ...x.data, cartao: { ...x.data.cartao, ...parcial } } } : x)))
    mudou()
  }

  function mudarRotulo(id: string, rotulo: string) {
    setArestas((a) => a.map((x) => (x.id === id ? { ...x, label: rotulo || undefined, data: { rotulo } } : x)))
    mudou()
  }

  const estado = salvar.isPending || sujo ? 'Salvando…' : salvar.isError ? 'Não foi salvo' : 'Tudo salvo'

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_18rem]">
      <div className="space-y-2">
        {!somenteLeitura && (
          <div className="flex flex-wrap items-end gap-2 rounded-xl border border-borda p-2">
            <Botao variante="secundario" onClick={() => adicionar({ tipo: 'nota', titulo: 'Nova nota' })}>+ Nota</Botao>
            <input ref={entradaImagem} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only"
              aria-label="Imagem para o quadro" onChange={(e) => {
                const arquivo = e.target.files?.[0]
                e.target.value = ''
                if (arquivo) enviar.mutate(arquivo, { onSuccess: ({ id }) => adicionar({ tipo: 'imagem', imagem: id }) })
              }} />
            <Botao variante="secundario" disabled={enviar.isPending} onClick={() => entradaImagem.current?.click()}>
              {enviar.isPending ? 'Enviando…' : '+ Imagem'}
            </Botao>
            <NovoItem mesa={mesa} sessao={sessao}
              aoEscolher={(tipo, item_id, item) => adicionar({ tipo: 'item', item_tipo: tipo, item_id }, item)} />
            <span className="ml-auto text-xs text-texto-suave" aria-live="polite">{estado}</span>
          </div>
        )}
        <Aviso erro={salvar.error ?? enviar.error} />
        <div className="h-[65vh] overflow-hidden rounded-2xl border border-borda" aria-label="Quadro da sessão">
          <ReactFlow nodes={nos} edges={arestas} nodeTypes={TIPOS_DE_CARTAO} colorMode={modoDeCor()}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
            nodesDraggable={!somenteLeitura} nodesConnectable={!somenteLeitura} elementsSelectable
            deleteKeyCode={somenteLeitura ? null : ['Delete', 'Backspace']} fitView minZoom={0.2}
            // qualquer lado liga em qualquer lado; soltar em qualquer parte do cartão encaixa no lado mais perto
            connectionMode={ConnectionMode.Loose} connectionRadius={120}>
            <Background />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
        {!somenteLeitura && (
          <p className="text-xs text-texto-suave">
            Arraste de um dos pontos (em cima, embaixo ou nos lados) de um cartão até qualquer parte de outro para ligar;
            no celular, também dá para tocar num ponto e depois num ponto do outro cartão. Para apagar, selecione e use o
            botão no painel (ou a tecla Delete).
          </p>
        )}
      </div>

      <aside className="rounded-2xl border border-borda bg-superficie p-3">
        {selecionado ? (
          <PainelDoCartao no={selecionado} somenteLeitura={somenteLeitura}
            aoMudar={(p) => mudarCartao(selecionado.id, p)}
            aoApagar={() => {
              setNos((n) => n.filter((x) => x.id !== selecionado.id))
              setArestas((a) => a.filter((x) => x.source !== selecionado.id && x.target !== selecionado.id))
              mudou()
            }} />
        ) : arestaSelecionada ? (
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wider text-texto-suave">Ligação</p>
            <Campo rotulo="Texto da seta" maxLength={120} disabled={somenteLeitura} placeholder='Ex.: "trai", "leva a"'
              value={String((arestaSelecionada.data as { rotulo?: string } | undefined)?.rotulo ?? '')}
              onChange={(e) => mudarRotulo(arestaSelecionada.id, e.target.value)} />
            {!somenteLeitura && (
              <Botao variante="perigo" onClick={() => { setArestas((a) => a.filter((x) => x.id !== arestaSelecionada.id)); mudou() }}>
                Apagar ligação
              </Botao>
            )}
          </div>
        ) : (
          <p className="text-sm text-texto-suave">
            Escolha um cartão ou uma seta para editar. {somenteLeitura && 'Esta sessão é de outro mestre: só leitura.'}
          </p>
        )}
      </aside>
    </div>
  )
}

export default function QuadroDaSessao({ mesa, sessao }: { mesa: Mesa; sessao: Sessao }) {
  const quadro = useQuadro(mesa.id, sessao.id)
  if (quadro.isPending) return <Carregando />
  if (quadro.isError) return <Aviso erro={quadro.error} />
  // o editor lê o quadro só ao montar e depois mantém o próprio estado; quem só lê (sessão
  // compartilhada) remonta a cada atualização ao vivo, para ver o que o responsável mudou
  const chave = sessao.sou_responsavel ? sessao.id : `${sessao.id}:${quadro.dataUpdatedAt}`
  return <Editor key={chave} mesa={mesa} sessao={sessao} inicial={quadro.data} />
}
