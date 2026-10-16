// NPCs da mesa: ficha simples (descrição, motivações, notas privadas) e,
// se o mestre quiser, uma ficha de combate no formato de inimigo. Cada NPC é de
// quem criou e começa visível só para ele; ele escolhe mostrar aos mestres ou a
// todos (os jogadores o veem na sessão a que for vinculado).
import { useState } from 'react'

import { useApagarNpc, useNpcs, useSalvarNpc, useVisibilidadeNpc } from '../../api/consultas'
import type { Npc, NpcEntrada } from '../../api/tipos'
import { AvisoDeConflito } from '../../componentes/Conflito'
import EditorInimigo from '../../componentes/EditorInimigo'
import FichaInimigo from '../../componentes/FichaInimigo'
import { EnviarFoto, Foto } from '../../componentes/Foto'
import TextoRico from '../../componentes/TextoRico'
import { Area, Aviso, Botao, Campo, Carregando, Escolhivel, Selo } from '../../componentes/ui'
import { semConflito } from '../../lib/conflito'
import { INIMIGO_EM_BRANCO } from '../../lib/inimigo'
import { NOME_VISIBILIDADE_NPC } from '../../lib/rotulos'

// `versao`: a de quando abriu o editor (se outro mestre salvar antes, o servidor avisa)
type Rascunho = NpcEntrada & { id?: string; versao?: string | null }

const NPC_EM_BRANCO: Rascunho = { nome: '', descricao: '', motivacoes: '', notas: '', ficha_combate: null, foto: null }

function Editor({ inicial, aoSalvar, aoCancelar, aoVerAtual, salvando, erro }: {
  inicial: Rascunho; aoSalvar: (r: Rascunho) => void; aoCancelar: () => void; aoVerAtual: () => void
  salvando: boolean; erro: unknown
}) {
  const [r, setR] = useState(inicial)
  const mudar = (parcial: Partial<Rascunho>) => setR({ ...r, ...parcial })

  return (
    <form className="space-y-4 rounded-2xl border border-borda bg-superficie p-4 sm:p-5"
      onSubmit={(e) => { e.preventDefault(); aoSalvar(r) }}>
      <h2 className="text-lg text-esperanca">{r.id ? `Editar ${inicial.nome}` : 'Novo NPC'}</h2>
      <div className="flex items-center gap-3">
        <Foto id={r.foto} nome={r.nome || '?'} />
        <EnviarFoto temFoto={!!r.foto} aoMudar={(foto) => mudar({ foto })} />
      </div>
      <Campo rotulo="Nome" value={r.nome} required maxLength={120} onChange={(e) => mudar({ nome: e.target.value })} />
      <Area rotulo="Descrição" value={r.descricao} maxLength={4000} onChange={(e) => mudar({ descricao: e.target.value })} />
      <Area rotulo="Motivações" rows={2} value={r.motivacoes} maxLength={2000}
        onChange={(e) => mudar({ motivacoes: e.target.value })} />
      <Area rotulo="Notas do mestre" rows={4} value={r.notas} maxLength={8000}
        dica="Segredos, ganchos, o que o NPC sabe." onChange={(e) => mudar({ notas: e.target.value })} />

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" className="accent-[var(--esperanca)]" checked={!!r.ficha_combate}
          onChange={(e) => mudar({ ficha_combate: e.target.checked ? { ...INIMIGO_EM_BRANCO, tipo: 'SOCIAL' } : null })} />
        Tem ficha de combate
      </label>
      {r.ficha_combate && (
        <div className="rounded-xl border border-borda p-3">
          <EditorInimigo nomeOpcional valor={r.ficha_combate} aoMudar={(ficha_combate) => mudar({ ficha_combate })} />
        </div>
      )}

      <AvisoDeConflito erro={erro} ocupado={salvando} aoVerAtual={aoVerAtual}
        aoSalvarMesmoAssim={() => aoSalvar({ ...r, versao: null })} />
      <Aviso erro={semConflito(erro)} />
      <div className="flex gap-2">
        <Botao type="submit" disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar'}</Botao>
        <Botao type="button" variante="fantasma" onClick={aoCancelar}>Cancelar</Botao>
      </div>
    </form>
  )
}

/** Quem vê: só o dono escolhe; os outros mestres veem de quem é. */
function Visibilidade({ mesaId, npc }: { mesaId: string; npc: Npc }) {
  const mudar = useVisibilidadeNpc(mesaId)
  const atual = npc.visibilidade ?? 'privado'
  if (!npc.sou_dono) {
    return <p className="text-sm text-texto-suave">NPC de {npc.dono}, compartilhado com os mestres: só ele edita.</p>
  }
  return (
    <fieldset className="space-y-1">
      <legend className="mb-1 text-sm font-medium">Quem vê</legend>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(NOME_VISIBILIDADE_NPC).map(([valor, { nome }]) => (
          <button key={valor} type="button" aria-pressed={atual === valor} disabled={mudar.isPending}
            onClick={() => atual !== valor && mudar.mutate({ npcId: npc.id, visibilidade: valor as Npc['visibilidade'] })}
            className={`rounded-full border px-3 py-1 text-sm transition ${atual === valor
              ? 'border-esperanca bg-esperanca/15 text-esperanca' : 'border-borda text-texto-suave hover:text-texto'}`}>
            {nome}
          </button>
        ))}
      </div>
      <p className="text-xs text-texto-suave">{NOME_VISIBILIDADE_NPC[atual]?.dica}</p>
      <Aviso erro={mudar.error} />
    </fieldset>
  )
}

/** Selo da lista: quem vê (e de quem é, se não for seu). */
function SeloVisibilidade({ npc }: { npc: Npc }) {
  if (!npc.sou_dono) return <Selo>de {npc.dono}</Selo>
  const v = npc.visibilidade ?? 'privado'
  return <Selo destaque={v === 'todos'}>{NOME_VISIBILIDADE_NPC[v]?.nome}</Selo>
}

function Detalhe({ npc, acoes, revelar }: { npc: Npc; acoes?: React.ReactNode; revelar?: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <article className="space-y-3 rounded-2xl border border-borda bg-superficie p-4 sm:p-5">
        <header className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <Foto id={npc.foto} nome={npc.nome} />
            <h2 className="text-xl text-esperanca">{npc.nome}</h2>
            <SeloVisibilidade npc={npc} />
          </div>
          {acoes && <div className="flex gap-2">{acoes}</div>}
        </header>
        {revelar}
        {npc.descricao && <TextoRico texto={npc.descricao} className="text-sm" />}
        {npc.motivacoes && <p className="text-sm"><span className="font-semibold">Motivações:</span> {npc.motivacoes}</p>}
        {npc.notas && (
          <div className="rounded-xl border border-medo/50 bg-medo/10 p-3 text-sm">
            <p className="mb-1 text-xs uppercase tracking-wider text-texto-suave">Notas do mestre</p>
            <TextoRico texto={npc.notas} />
          </div>
        )}
        {!npc.ficha_combate && <p className="text-sm text-texto-suave">Sem ficha de combate.</p>}
      </article>
      {npc.ficha_combate && <FichaInimigo adversario={npc.ficha_combate} />}
    </div>
  )
}

export default function AbaNpcs({ mesaId, podeEditar }: { mesaId: string; podeEditar: boolean }) {
  const npcs = useNpcs(mesaId)
  const salvar = useSalvarNpc(mesaId)
  const apagar = useApagarNpc(mesaId)
  const [selecionado, setSelecionado] = useState<string | null>(null)
  const [rascunho, setRascunho] = useState<Rascunho | null>(null)
  const npc = npcs.data?.find((n) => n.id === selecionado)

  function editar(r: Rascunho) {
    salvar.reset()
    setRascunho(structuredClone(r))
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_1fr]">
      <aside className="space-y-2">
        {podeEditar && <Botao variante="secundario" className="w-full" onClick={() => editar(NPC_EM_BRANCO)}>Novo NPC</Botao>}
        {npcs.isPending && <Carregando />}
        <Aviso erro={npcs.error} />
        {npcs.data?.length === 0 && <p className="text-sm text-texto-suave">Nenhum NPC ainda.</p>}
        <ul className="space-y-1.5">
          {npcs.data?.map((n) => (
            <li key={n.id}>
              <Escolhivel selecionado={n.id === selecionado && !rascunho}
                onClick={() => { setRascunho(null); setSelecionado(n.id) }}>
                <span className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2"><Foto id={n.foto} nome={n.nome} tamanho="p" />
                    <span className="font-medium">{n.nome}</span></span>
                  <span className="flex gap-1"><SeloVisibilidade npc={n} />{n.ficha_combate && <Selo>combate</Selo>}</span>
                </span>
              </Escolhivel>
            </li>
          ))}
        </ul>
      </aside>

      <section aria-live="polite">
        {rascunho ? (
          <Editor key={rascunho.id ?? 'novo'} inicial={rascunho} salvando={salvar.isPending} erro={salvar.error}
            aoCancelar={() => setRascunho(null)}
            aoVerAtual={() => { salvar.reset(); setRascunho(null) }}
            aoSalvar={(r) => salvar.mutate(r, {
              onSuccess: (salvo) => { setRascunho(null); setSelecionado(salvo!.id) },
            })} />
        ) : npc ? (
          <>
            <Aviso erro={apagar.error} />
            <Detalhe npc={npc} revelar={<Visibilidade mesaId={mesaId} npc={npc} />} acoes={podeEditar && npc.sou_dono && <>
              <Botao variante="secundario" onClick={() => editar(npc)}>Editar</Botao>
              <Botao variante="perigo" disabled={apagar.isPending}
                onClick={() => confirm(`Apagar ${npc.nome}?`)
                  && apagar.mutate(npc.id, { onSuccess: () => setSelecionado(null) })}>
                Apagar
              </Botao>
            </>} />
          </>
        ) : (
          <div className="rounded-2xl border border-dashed border-borda p-10 text-center text-texto-suave">
            Escolha um NPC para ver a ficha. Um NPC novo começa visível só para você.
          </div>
        )}
      </section>
    </div>
  )
}
