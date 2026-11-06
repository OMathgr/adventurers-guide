// Sessões da mesa: cada uma é um dia de jogo, de um mestre (o responsável,
// quem criou), com planejamento (resumo, notas privadas, NPCs e inimigos que
// devem aparecer), o Medo da sessão e os encontros. Outros mestres só veem o
// lado do mestre se o responsável compartilhar, e só para leitura. Em
// andamento ou encerrada, todos veem o lado dos jogadores (SessaoDeJogo):
// entrar, a ficha de jogo, o revelado, as lojas e os aliados.
import { lazy, Suspense, useRef, useState } from 'react'

import {
  useApagarSessao, useCompartilharSessao, useCriarSessao, useEditarSessao, useInimigos, useMedo, useNpcs,
  useRepouso, useSessao, useSessoes, useStatusDaSessao,
} from '../../api/consultas'
import type { Mesa, Sessao } from '../../api/tipos'
import { useAutenticacao } from '../../auth/Autenticacao'
import { AvisoDeConflito } from '../../componentes/Conflito'
import MedoDoMestre, { MedoFixo } from '../../componentes/MedoDoMestre'
import PainelDeRepouso from '../../componentes/Repouso'
import { Abas, Area, Aviso, Botao, Campo, Cartao, Carregando, Escolhivel, Secao, Selo } from '../../componentes/ui'
import Encontros from './Encontros'
import Lojas from './Lojas'
import PersonagensNaSessao from './PersonagensNaSessao'
import SessaoDeJogo from './SessaoDeJogo'
import RolagemDeDados, { RegistroRecente } from '../../componentes/RolagemDeDados'
import { semConflito } from '../../lib/conflito'
import { useCelular } from '../../lib/useCelular'


const NOME_STATUS: Record<string, string> = {
  planejada: 'Planejada', em_andamento: 'Em andamento', encerrada: 'Encerrada',
}

const dataCurta = (d?: string | null) => (d ? new Date(`${d}T12:00:00`).toLocaleDateString('pt-BR') : 'sem data')

function Destaques({ titulo, opcoes, escolhidos, aoMudar, desabilitado, dica }: {
  titulo: string; opcoes: { id: string; nome: string }[]; escolhidos: string[]
  aoMudar: (ids: string[]) => void; desabilitado: boolean; dica?: string
}) {
  return (
    <fieldset className="space-y-1">
      <legend className="mb-1 text-sm font-medium text-texto-suave">{titulo}</legend>
      {dica && <p className="text-xs text-texto-suave">{dica}</p>}
      {opcoes.length === 0 && <p className="text-xs text-texto-suave">Nada na biblioteca da mesa ainda.</p>}
      <div className="flex flex-wrap gap-1.5">
        {opcoes.map((o) => {
          const marcado = escolhidos.includes(o.id)
          return (
            <button key={o.id} type="button" aria-pressed={marcado} disabled={desabilitado}
              onClick={() => aoMudar(marcado ? escolhidos.filter((x) => x !== o.id) : [...escolhidos, o.id])}
              className={`rounded-full border px-2.5 py-0.5 text-xs transition ${
                marcado ? 'border-esperanca bg-esperanca/15 text-esperanca-forte' : 'border-borda text-texto-suave hover:text-texto'}`}>
              {o.nome}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

/** Planejamento: os dados que o responsável edita e salva de uma vez. */
const dadosDe = (s: Sessao) => ({
  titulo: s.titulo, data: s.data ?? null, resumo: s.resumo, notas: s.notas, npcs: s.npcs, inimigos: s.inimigos,
})

function Planejamento({ mesaId, sessao }: { mesaId: string; sessao: Sessao }) {
  const editar = useEditarSessao(mesaId, sessao.id)
  const recarregar = useSessao(mesaId, sessao.id)
  const npcs = useNpcs(mesaId)
  const inimigos = useInimigos(mesaId)
  const inicial = dadosDe(sessao)
  const [r, setR] = useState(inicial)
  // versão de onde o rascunho partiu: se outra aba salvar antes, o servidor avisa
  const [base, setBase] = useState(sessao.versao)
  const salvar = (versao: string | null) =>
    editar.mutate({ ...r, versao }, { onSuccess: (nova) => setBase(nova.versao) })
  const so = !sessao.sou_responsavel
  const mudou = JSON.stringify(r) !== JSON.stringify(inicial)
  const mudar = (p: Partial<typeof r>) => setR({ ...r, ...p })

  return (
    <Cartao titulo="Planejamento">
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); salvar(base) }}>
        <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
          <Campo rotulo="Título" value={r.titulo} maxLength={120} required disabled={so}
            onChange={(e) => mudar({ titulo: e.target.value })} />
          <Campo rotulo="Data" type="date" value={r.data ?? ''} disabled={so}
            onChange={(e) => mudar({ data: e.target.value || null })} />
        </div>
        <Area rotulo="Resumo e objetivos" rows={3} value={r.resumo} maxLength={4000} disabled={so}
          dica="O que deve acontecer, ganchos, para onde a história pode ir."
          onChange={(e) => mudar({ resumo: e.target.value })} />
        <Area rotulo="Notas do mestre" rows={4} value={r.notas} maxLength={8000} disabled={so}
          dica="Segredos e lembretes. Ninguém além de você vê (nem quem recebeu a sessão compartilhada edita)."
          onChange={(e) => mudar({ notas: e.target.value })} />
        <Destaques titulo="NPCs que participam" escolhidos={r.npcs} desabilitado={so}
          dica="Os exibidos para todos aparecem aos jogadores na página da sessão (nome, foto e descrição)."
          opcoes={(npcs.data ?? []).map((n) => ({ id: n.id, nome: n.nome }))} aoMudar={(ids) => mudar({ npcs: ids })} />
        <Destaques titulo="Inimigos que devem aparecer" escolhidos={r.inimigos} desabilitado={so}
          opcoes={(inimigos.data ?? []).map((i) => ({ id: i.id, nome: i.nome }))} aoMudar={(ids) => mudar({ inimigos: ids })} />
        <AvisoDeConflito erro={editar.error} ocupado={editar.isPending}
          aoVerAtual={async () => {
            const atual = (await recarregar.refetch()).data
            if (atual) { setR(dadosDe(atual)); setBase(atual.versao) }
            editar.reset()
          }}
          aoSalvarMesmoAssim={() => salvar(null)} />
        <Aviso erro={semConflito(editar.error)} />
        {!so && (
          <div className="flex gap-2">
            <Botao type="submit" disabled={!mudou || !r.titulo.trim() || editar.isPending}>
              {editar.isPending ? 'Salvando…' : 'Salvar planejamento'}
            </Botao>
            {mudou && <Botao type="button" variante="fantasma" onClick={() => setR(inicial)}>Desfazer mudanças</Botao>}
          </div>
        )}
      </form>
    </Cartao>
  )
}

function Compartilhar({ mesa, sessao }: { mesa: Mesa; sessao: Sessao }) {
  const salvar = useCompartilharSessao(mesa.id, sessao.id)
  const outros = mesa.membros.filter((m) => (m.papel === 'mestre' || m.criador) && m.usuario_id !== sessao.responsavel_id)
  return (
    <Cartao titulo="Compartilhar">
      <h3 className="mb-1 text-sm font-semibold">Compartilhar com outros mestres</h3>
      {outros.length === 0 && <p className="text-sm text-texto-suave">A mesa não tem outros mestres.</p>}
      <p className="mb-2 text-xs text-texto-suave">Quem recebe só vê a sessão; conduzir continua sendo seu.</p>
      <div className="space-y-1">
        {outros.map((m) => {
          const marcado = sessao.compartilhada_com.includes(m.usuario_id)
          return (
            <label key={m.usuario_id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={marcado} disabled={salvar.isPending}
                onChange={() => salvar.mutate(marcado
                  ? sessao.compartilhada_com.filter((x) => x !== m.usuario_id)
                  : [...sessao.compartilhada_com, m.usuario_id])} />
              {m.nome}
            </label>
          )
        })}
      </div>
      <Aviso erro={salvar.error} />
    </Cartao>
  )
}

function SessaoAberta({ mesa, sid, aoApagar }: { mesa: Mesa; sid: string; aoApagar: () => void }) {
  const sessao = useSessao(mesa.id, sid)
  const status = useStatusDaSessao(mesa.id, sid)
  const medo = useMedo(mesa.id, sid)
  const apagar = useApagarSessao(mesa.id)
  const repouso = useRepouso(mesa.id, sid)
  const celular = useCelular()
  const conteudo = useRef<HTMLDivElement>(null)
  const [escolhida, setParte] = useState<ParteDaSessao | null>(null)

  if (sessao.isPending) return <Carregando />
  if (sessao.isError) return <Aviso erro={sessao.error} />
  const s = sessao.data
  const minha = s.sou_responsavel
  const emJogo = s.status === 'em_andamento'
  // em andamento, a sessão abre na mesa ao vivo; fora disso, essa parte não existe
  const parte: ParteDaSessao = escolhida && (escolhida !== 'ao_vivo' || emJogo) ? escolhida : emJogo ? 'ao_vivo' : 'planejamento'
  const mudarStatus = (novo: string, aviso?: string) => {
    if (aviso && !confirm(aviso)) return
    status.mutate(novo, { onSuccess: () => setParte(null) })
  }
  const trocarParte = (nova: ParteDaSessao) => {
    setParte(nova)
    // as abas ficam presas no alto do celular: a aba nova começa do início, não do meio da anterior
    const inicio = conteudo.current
    if (celular && inicio && inicio.getBoundingClientRect().top < 0) requestAnimationFrame(() => inicio.scrollIntoView())
  }
  // no celular o que vem primeiro é a sessão; o repouso só sobe quando está acontecendo
  const repousoNoTopo = celular && repouso.data?.status === 'aberto'
  const painelDeRepouso = <PainelDeRepouso mesa={mesa} sessao={s} />
  const botaoApagar = minha && (
    <Botao variante="fantasma" className="!text-perigo" disabled={apagar.isPending}
      onClick={() => confirm(`Apagar a sessão "${s.titulo}" e os encontros dela?`)
        && apagar.mutate(s.id, { onSuccess: aoApagar })}>
      Apagar sessão
    </Botao>
  )

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
      <div className="min-w-0 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex flex-wrap items-center gap-2 text-2xl">{s.titulo} <Selo destaque={emJogo}>{NOME_STATUS[s.status] ?? s.status}</Selo></h2>
          <p className="text-sm text-texto-suave">
            {dataCurta(s.data)} · {minha ? 'Você é o mestre responsável' : `Sessão de ${s.responsavel} (só leitura)`}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          {minha && s.status === 'planejada' && (
            <Botao disabled={status.isPending} onClick={() => mudarStatus('em_andamento')}>Iniciar sessão</Botao>
          )}
          {minha && emJogo && (
            <>
              <Botao variante="secundario" disabled={status.isPending}
                onClick={() => mudarStatus('encerrada', `Encerrar "${s.titulo}"? As marcas ficam guardadas para consulta.`)}>
                Encerrar sessão
              </Botao>
              <Botao variante="fantasma" disabled={status.isPending}
                onClick={() => mudarStatus('planejada', 'Voltar a planejar? Os jogadores deixam de ver a sessão.')}>
                Voltar a planejar
              </Botao>
            </>
          )}
          {minha && s.status === 'encerrada' && (
            <Botao variante="secundario" disabled={status.isPending} onClick={() => mudarStatus('em_andamento')}>Reabrir sessão</Botao>
          )}
          {!celular && botaoApagar}
        </div>
      </div>
      <Aviso erro={status.error ?? apagar.error} />
      {s.status === 'em_andamento' && (
        <p className="text-xs text-texto-suave max-sm:hidden">
          Em andamento: os jogadores entram pela aba Sessões e veem o Medo, o que você revelar e as lojas à mostra.
        </p>
      )}
      {s.status === 'planejada' && (
        <p className="text-xs text-texto-suave">Planejada: só você vê. Inicie a sessão para os jogadores entrarem.</p>
      )}

      {repousoNoTopo && painelDeRepouso}

      <div ref={conteudo}>
      <div className="max-sm:sticky max-sm:top-0 max-sm:z-10 max-sm:bg-fundo">
        <Abas<ParteDaSessao> atual={parte} aoTrocar={trocarParte}
          abas={[...(emJogo ? [['ao_vivo', 'Ao vivo'] as [ParteDaSessao, string]] : []),
            ['planejamento', 'Planejamento'], ['quadro', 'Quadro'], ['encontros', 'Encontros'], ['lojas', 'Lojas'],
            ['personagens', 'Personagens'], ['dados', 'Dados']]} />
      </div>

      <div key={parte} className="entrada mt-4">
      {/* numa rodada de combate, o grupo e os inimigos ficam na mesma tela */}
      {parte === 'ao_vivo' && (
        <div className="space-y-6">
          <PersonagensNaSessao mesa={mesa} sessao={s} compacto />
          <Encontros mesaId={mesa.id} sessao={s} />
        </div>
      )}

      {parte === 'planejamento' && (
        <Planejamento key={s.id} mesaId={mesa.id} sessao={s} />
      )}
      {parte === 'quadro' && <Suspense fallback={<Carregando />}><QuadroDaSessao mesa={mesa} sessao={s} /></Suspense>}
      {parte === 'encontros' && <Encontros mesaId={mesa.id} sessao={s} />}
      {parte === 'lojas' && <Lojas mesa={mesa} sessao={s} />}
      {parte === 'personagens' && <PersonagensNaSessao mesa={mesa} sessao={s} />}
      {parte === 'dados' && (
        <RolagemDeDados mesaId={mesa.id} sessaoId={s.id} souMestre={minha} emAndamento={s.status === 'em_andamento'} />
      )}
      </div>
      </div>
      </div>
      <aside className="min-w-0 space-y-4 sm:max-lg:order-first lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto">
        {celular && emJogo
          ? <MedoFixo medo={s.medo} titulo="Medo da sessão" ocupado={medo.isPending} erro={medo.error}
              aoMudar={minha ? (m) => medo.mutate(m) : undefined} />
          : <MedoDoMestre medo={s.medo} titulo="Medo da sessão" ocupado={medo.isPending} erro={medo.error}
              aoMudar={minha ? (m) => medo.mutate(m) : undefined} />}
        {!repousoNoTopo && painelDeRepouso}
        {emJogo && <div className="max-lg:hidden"><RegistroRecente mesaId={mesa.id} sessaoId={s.id} /></div>}
        {minha && parte === 'planejamento' && <Compartilhar mesa={mesa} sessao={s} />}
        {celular && botaoApagar}
      </aside>
    </div>
  )
}

type ParteDaSessao = 'ao_vivo' | 'planejamento' | 'quadro' | 'encontros' | 'lojas' | 'personagens' | 'dados'

// o quadro usa o React Flow (pesado): só carrega quando alguém abre a aba
const QuadroDaSessao = lazy(() => import('./QuadroDaSessao'))

export default function AbaSessoes({ mesa, podePreparar, inicial }: {
  mesa: Mesa; podePreparar: boolean; inicial?: string | null
}) {
  const sessoes = useSessoes(mesa.id)
  const criar = useCriarSessao(mesa.id)
  const [escolhida, setEscolhida] = useState<string | null>(inicial ?? null)
  const [titulo, setTitulo] = useState('')
  const [data, setData] = useState('')
  const [listaAberta, setListaAberta] = useState(false)
  const celular = useCelular()
  const { usuario } = useAutenticacao()
  const emJogo = mesa.personagens.filter((p) => p.dono_id !== usuario?.id).length
  const lista = sessoes.data ?? []
  // abre a escolhida, ou a em andamento (a minha, se eu mestro uma), ou a mais recente
  const atual = (lista.some((s) => s.id === escolhida) ? escolhida : null)
    ?? lista.find((s) => s.status === 'em_andamento' && s.sou_responsavel)?.id
    ?? lista.find((s) => s.status === 'em_andamento')?.id ?? lista.at(-1)?.id ?? null
  const escolhidaNaLista = lista.find((s) => s.id === atual)

  const listaESessaoNova = (
      <div className="min-w-0 space-y-6">
        <Secao titulo="Sessões">
          <Aviso erro={sessoes.error} />
          {sessoes.isPending && <Carregando />}
          {sessoes.data?.length === 0 && (
            <p className="text-sm text-texto-suave">
              Nenhuma sessão em andamento ou encerrada ainda. Quando o mestre começar uma, ela aparece aqui para você entrar.
            </p>
          )}
          <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
            {lista.map((s) => (
              <li key={s.id}>
                <Escolhivel selecionado={s.id === atual} onClick={() => { setEscolhida(s.id); setListaAberta(false) }}>
                  <span className="block font-semibold">{s.titulo}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-texto-suave">
                    {dataCurta(s.data)} · Medo {s.medo}{!s.sou_responsavel && ` · de ${s.responsavel}`}
                    {(s.participantes ?? 0) > 0 && ` · ${s.participantes} jogando`}
                    <Selo destaque={s.status === 'em_andamento'}>{NOME_STATUS[s.status] ?? s.status}</Selo>
                  </span>
                </Escolhivel>
              </li>
            ))}
          </ul>
        </Secao>
        {podePreparar && (
          <Secao titulo="Planejar sessão">
            <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto] sm:items-end xl:grid-cols-1" onSubmit={(e) => {
              e.preventDefault()
              criar.mutate({ titulo: titulo.trim(), data: data || null },
                { onSuccess: (s) => { setEscolhida(s.id); setTitulo(''); setData('') } })
            }}>
              <Campo rotulo="Título da nova sessão" value={titulo} maxLength={120} onChange={(e) => setTitulo(e.target.value)}
                placeholder="Ex.: Sessão 3 — A ponte" />
              <Campo rotulo="Data da nova sessão" type="date" value={data} onChange={(e) => setData(e.target.value)} />
              <Botao type="submit" variante="secundario" className="w-full" disabled={!titulo.trim() || criar.isPending}>Criar</Botao>
            </form>
            <Aviso erro={criar.error} />
            <p className="text-xs text-texto-suave">
              O Medo de uma sessão nova sua começa em {Math.min(12, emJogo)}: os personagens da mesa, sem contar
              os seus (você mestra, não joga, nessa sessão).
            </p>
          </Secao>
        )}
      </div>
  )

  return (
    // três colunas no computador: as sessões, a sessão aberta e o painel do mestre
    <div className="grid gap-6 xl:grid-cols-[16.5rem_minmax(0,1fr)] xl:items-start">
      {/* no celular, quem conduz uma sessão vai direto a ela; a lista fica a um toque */}
      {celular && escolhidaNaLista?.posso_gerir ? (
        <details open={listaAberta} onToggle={(e) => setListaAberta(e.currentTarget.open)}
          className="group min-w-0 rounded-xl border border-borda">
          <summary className="flex min-h-11 cursor-pointer items-center px-3 text-sm text-texto-suave">
            <span aria-hidden className="mr-2 text-xs transition-transform group-open:rotate-90">▶</span>
            Outras sessões ({lista.length}) ou nova sessão
          </summary>
          <div className="px-3 pb-3 pt-1">{listaESessaoNova}</div>
        </details>
      ) : listaESessaoNova}

      <div key={atual} className="entrada min-w-0">
        {atual && (escolhidaNaLista?.posso_gerir
          ? <SessaoAberta key={atual} mesa={mesa} sid={atual} aoApagar={() => setEscolhida(null)} />
          : <SessaoDeJogo key={atual} mesa={mesa} sid={atual} />)}
      </div>
    </div>
  )
}
