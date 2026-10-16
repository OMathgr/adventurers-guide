// Sessões da mesa: cada uma é um dia de jogo, de um mestre (o responsável,
// quem criou), com planejamento (resumo, notas privadas, NPCs e inimigos que
// devem aparecer), o Medo da sessão e os encontros. Outros mestres só veem o
// lado do mestre se o responsável compartilhar, e só para leitura. Em
// andamento ou encerrada, todos veem o lado dos jogadores (SessaoDeJogo):
// entrar, a ficha de jogo, o revelado, as lojas e os aliados.
import { lazy, Suspense, useState } from 'react'

import {
  useApagarSessao, useCompartilharSessao, useCriarSessao, useEditarSessao, useInimigos, useMedo, useNpcs,
  useSessao, useSessoes, useStatusDaSessao,
} from '../../api/consultas'
import type { Mesa, Sessao } from '../../api/tipos'
import { useAutenticacao } from '../../auth/Autenticacao'
import { AvisoDeConflito } from '../../componentes/Conflito'
import MedoDoMestre from '../../componentes/MedoDoMestre'
import PainelDeRepouso from '../../componentes/Repouso'
import { Abas, Area, Aviso, Botao, Campo, Cartao, Carregando, Escolhivel, Selecao, Selo } from '../../componentes/ui'
import Encontros from './Encontros'
import Lojas from './Lojas'
import PersonagensNaSessao from './PersonagensNaSessao'
import SessaoDeJogo from './SessaoDeJogo'
import { semConflito } from '../../lib/conflito'


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
                marcado ? 'border-esperanca bg-esperanca/15 text-esperanca' : 'border-borda text-texto-suave hover:text-texto'}`}>
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
    <Cartao titulo="Compartilhar com outros mestres">
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
  const [parte, setParte] = useState<ParteDaSessao>('planejamento')

  if (sessao.isPending) return <Carregando />
  if (sessao.isError) return <Aviso erro={sessao.error} />
  const s = sessao.data
  const minha = s.sou_responsavel

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl">{s.titulo}</h2>
          <p className="text-sm text-texto-suave">
            {dataCurta(s.data)} · {minha ? 'Você é o mestre responsável' : `Sessão de ${s.responsavel} (só leitura)`}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Selecao rotulo="Situação" value={s.status} disabled={!minha || status.isPending}
            onChange={(e) => status.mutate(e.target.value)}
            opcoes={Object.entries(NOME_STATUS)} />
          {minha && (
            <Botao variante="perigo" disabled={apagar.isPending}
              onClick={() => confirm(`Apagar a sessão "${s.titulo}" e os encontros dela?`)
                && apagar.mutate(s.id, { onSuccess: aoApagar })}>
              Apagar sessão
            </Botao>
          )}
        </div>
      </div>
      <Aviso erro={status.error ?? apagar.error} />
      {s.status === 'em_andamento' && (
        <p className="text-xs text-texto-suave">
          Em andamento: os jogadores entram pela aba Sessões e veem o Medo, o que você revelar e as lojas à mostra.
        </p>
      )}
      {s.status === 'planejada' && (
        <p className="text-xs text-texto-suave">Planejada: só você vê. Mude para "Em andamento" para os jogadores entrarem.</p>
      )}

      <MedoDoMestre medo={s.medo} titulo="Medo da sessão" ocupado={medo.isPending} erro={medo.error}
        aoMudar={minha ? (m) => medo.mutate(m) : undefined} />
      <PainelDeRepouso mesa={mesa} sessao={s} />

      <Abas<ParteDaSessao> atual={parte} aoTrocar={setParte}
        abas={[['planejamento', 'Planejamento'], ['quadro', 'Quadro'], ['encontros', 'Encontros'], ['lojas', 'Lojas'], ['personagens', 'Personagens']]} />

      {parte === 'planejamento' && (
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <Planejamento key={s.id} mesaId={mesa.id} sessao={s} />
          {minha && <Compartilhar mesa={mesa} sessao={s} />}
        </div>
      )}
      {parte === 'quadro' && <Suspense fallback={<Carregando />}><QuadroDaSessao mesa={mesa} sessao={s} /></Suspense>}
      {parte === 'encontros' && <Encontros mesaId={mesa.id} sessao={s} />}
      {parte === 'lojas' && <Lojas mesa={mesa} sessao={s} />}
      {parte === 'personagens' && <PersonagensNaSessao mesa={mesa} sessao={s} />}
    </div>
  )
}

type ParteDaSessao = 'planejamento' | 'quadro' | 'encontros' | 'lojas' | 'personagens'

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
  const { usuario } = useAutenticacao()
  const emJogo = mesa.personagens.filter((p) => p.dono_id !== usuario?.id).length
  const lista = sessoes.data ?? []
  // abre a escolhida, ou a em andamento (a minha, se eu mestro uma), ou a mais recente
  const atual = (lista.some((s) => s.id === escolhida) ? escolhida : null)
    ?? lista.find((s) => s.status === 'em_andamento' && s.sou_responsavel)?.id
    ?? lista.find((s) => s.status === 'em_andamento')?.id ?? lista.at(-1)?.id ?? null
  const escolhidaNaLista = lista.find((s) => s.id === atual)

  return (
    <div className="space-y-5">
      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-lg text-esperanca">Sessões</h2>
          {podePreparar && (
            <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
              e.preventDefault()
              criar.mutate({ titulo: titulo.trim(), data: data || null },
                { onSuccess: (s) => { setEscolhida(s.id); setTitulo(''); setData('') } })
            }}>
              <Campo rotulo="Planejar sessão" value={titulo} maxLength={120} onChange={(e) => setTitulo(e.target.value)}
                placeholder="Ex.: Sessão 3 — A ponte" />
              <Campo rotulo="Data" type="date" value={data} onChange={(e) => setData(e.target.value)} />
              <Botao type="submit" variante="secundario" disabled={!titulo.trim() || criar.isPending}>Criar</Botao>
            </form>
          )}
        </div>
        {podePreparar && (
          <p className="text-xs text-texto-suave">
            O Medo de uma sessão nova sua começa em {Math.min(12, emJogo)}: os personagens da mesa, sem contar
            os seus (você mestra, não joga, nessa sessão).
          </p>
        )}
        <Aviso erro={sessoes.error ?? criar.error} />
        {sessoes.isPending && <Carregando />}
        {sessoes.data?.length === 0 && (
          <p className="text-sm text-texto-suave">
            Nenhuma sessão em andamento ou encerrada ainda. Quando o mestre começar uma, ela aparece aqui para você entrar.
          </p>
        )}
        <ul className="flex flex-wrap gap-2">
          {lista.map((s) => (
            <li key={s.id} className="w-60">
              <Escolhivel selecionado={s.id === atual} onClick={() => setEscolhida(s.id)}>
                <span className="flex items-center justify-between gap-2">
                  <span className="font-medium">{s.titulo}</span>
                  <Selo destaque={s.status === 'em_andamento'}>{NOME_STATUS[s.status] ?? s.status}</Selo>
                </span>
                <span className="text-xs text-texto-suave">
                  {dataCurta(s.data)} · Medo {s.medo}{!s.sou_responsavel && ` · de ${s.responsavel}`}
                  {(s.participantes ?? 0) > 0 && ` · ${s.participantes} jogando`}
                </span>
              </Escolhivel>
            </li>
          ))}
        </ul>
      </section>

      {atual && (escolhidaNaLista?.posso_gerir
        ? <SessaoAberta key={atual} mesa={mesa} sid={atual} aoApagar={() => setEscolhida(null)} />
        : <SessaoDeJogo key={atual} mesa={mesa} sid={atual} />)}
    </div>
  )
}
