// NPCs da mesa: ficha simples (descrição, motivações, notas privadas) e,
// se o mestre quiser, uma ficha de combate no formato de inimigo.
import { useState } from 'react'

import { useApagarNpc, useNpcs, useSalvarNpc } from '../../api/consultas'
import type { Npc, NpcEntrada } from '../../api/tipos'
import EditorInimigo from '../../componentes/EditorInimigo'
import FichaInimigo from '../../componentes/FichaInimigo'
import TextoRico from '../../componentes/TextoRico'
import { Area, Aviso, Botao, Campo, Carregando, Escolhivel, Selo } from '../../componentes/ui'
import { INIMIGO_EM_BRANCO } from '../../lib/inimigo'

type Rascunho = NpcEntrada & { id?: string }

const NPC_EM_BRANCO: Rascunho = { nome: '', descricao: '', motivacoes: '', notas: '', ficha_combate: null }

function Editor({ inicial, aoSalvar, aoCancelar, salvando, erro }: {
  inicial: Rascunho; aoSalvar: (r: Rascunho) => void; aoCancelar: () => void; salvando: boolean; erro: unknown
}) {
  const [r, setR] = useState(inicial)
  const mudar = (parcial: Partial<Rascunho>) => setR({ ...r, ...parcial })

  return (
    <form className="space-y-4 rounded-2xl border border-borda bg-superficie p-4 sm:p-5"
      onSubmit={(e) => { e.preventDefault(); aoSalvar(r) }}>
      <h2 className="text-lg text-esperanca">{r.id ? `Editar ${inicial.nome}` : 'Novo NPC'}</h2>
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

      <Aviso erro={erro} />
      <div className="flex gap-2">
        <Botao type="submit" disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar'}</Botao>
        <Botao type="button" variante="fantasma" onClick={aoCancelar}>Cancelar</Botao>
      </div>
    </form>
  )
}

function Detalhe({ npc, acoes }: { npc: Npc; acoes?: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <article className="space-y-3 rounded-2xl border border-borda bg-superficie p-4 sm:p-5">
        <header className="flex flex-wrap items-start justify-between gap-2">
          <h2 className="text-xl text-esperanca">{npc.nome}</h2>
          {acoes && <div className="flex gap-2">{acoes}</div>}
        </header>
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
                  <span className="font-medium">{n.nome}</span>
                  {n.ficha_combate && <Selo>combate</Selo>}
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
            aoSalvar={(r) => salvar.mutate(r, {
              onSuccess: (salvo) => { setRascunho(null); setSelecionado(salvo!.id) },
            })} />
        ) : npc ? (
          <>
            <Aviso erro={apagar.error} />
            <Detalhe npc={npc} acoes={podeEditar && <>
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
            Escolha um NPC para ver a ficha. Tudo aqui é visível só para os mestres.
          </div>
        )}
      </section>
    </div>
  )
}
