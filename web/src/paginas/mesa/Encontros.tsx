// Encontros de uma sessão: cópias de inimigos com PV, PF e condições marcados
// por clique, o Guia de Batalha e como pôr inimigos. Sem ordem entre eles:
// um encontro pode nunca acontecer, conforme o caminho dos jogadores.
// `podeEditar` é só do mestre responsável; quem recebeu a sessão compartilhada só vê.
import { useMemo, useState } from 'react'

import {
  useAcaoNoEncontro, useAdversariosSrd, useApagarEncontro, useCriarEncontro, useDanoEmCombatente,
  useEncontro, useInimigos, useNpcs,
} from '../../api/consultas'
import type { Combatente, ResultadoDanoAdversario, Sessao } from '../../api/tipos'
import Condicoes from '../../componentes/Condicoes'
import FichaInimigo from '../../componentes/FichaInimigo'
import { Foto } from '../../componentes/Foto'
import GuiaDeBatalha from '../../componentes/GuiaDeBatalha'
import { Aviso, Botao, Campo, Carregando, EspacosClicaveis, Escolhivel, Selecao, Selo } from '../../componentes/ui'
import { NOME_GRAVIDADE, NOME_TIPO_ADVERSARIO } from '../../lib/rotulos'

type Alvo = { mesaId: string; sid: string; encontroId: string; podeEditar: boolean }

function descreverDano(r: ResultadoDanoAdversario) {
  if (r.dano === 0) return 'Nenhum dano depois da resistência.'
  return `${r.dano} de dano (${NOME_GRAVIDADE[r.gravidade]}): ${r.pv_marcados} PV marcado${r.pv_marcados === 1 ? '' : 's'}`
    + (r.derrotado ? '. Derrotado!' : '.')
}

function CartaoCombatente({ mesaId, sid, encontroId, podeEditar, c }: Alvo & { c: Combatente }) {
  const acao = useAcaoNoEncontro(mesaId, sid, encontroId)
  const dano = useDanoEmCombatente(mesaId, sid, encontroId)
  const [valor, setValor] = useState('')
  const [resistente, setResistente] = useState(false)
  const [verFicha, setVerFicha] = useState(false)
  const a = c.adversario
  const ocupado = acao.isPending || dano.isPending
  const limiares = a.limiar_maior == null ? 'Nenhum' : `${a.limiar_maior}/${a.limiar_grave ?? '—'}`

  return (
    <article aria-label={c.rotulo}
      className={`space-y-3 rounded-2xl border p-4 ${c.derrotado ? 'border-borda bg-superficie/40 opacity-60' : 'border-borda bg-superficie'}`}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex gap-3">
          {a.foto && <Foto id={a.foto} nome={c.rotulo} tamanho="p" />}
          <div>
            <h3 className="font-titulo text-base">{c.rotulo}</h3>
            <p className="text-xs text-texto-suave">
              Patamar {a.patamar} · {NOME_TIPO_ADVERSARIO[a.tipo]} · Dificuldade {a.dificuldade} · Limiares {limiares}
            </p>
            <p className="text-xs text-texto-suave">ATQ {a.ataque} · {a.arma} · {a.dano}</p>
          </div>
        </div>
        {c.derrotado && <Selo>Derrotado</Selo>}
      </header>

      {/* inimigo começa cheio e o mestre vai esvaziando: quadradinho cheio = ponto que resta
          (a API guarda os marcados, como na ficha do livro) */}
      <div className="space-y-1.5">
        <p className="text-xs text-texto-suave">PV restantes: {a.pv - c.pv_marcados}/{a.pv}</p>
        <EspacosClicaveis total={a.pv} marcados={a.pv - c.pv_marcados} rotulo={`PV restantes de ${c.rotulo}`}
          sufixo="" desabilitado={ocupado || !podeEditar}
          aoMudar={(restam) => acao.mutate({
            tipo: 'marcas', combatente: c.id, pv_marcados: a.pv - restam, pf_marcados: c.pf_marcados })} />
        {a.pf > 0 && <>
          <p className="text-xs text-texto-suave">PF restantes: {a.pf - c.pf_marcados}/{a.pf}</p>
          <EspacosClicaveis total={a.pf} marcados={a.pf - c.pf_marcados} rotulo={`PF restantes de ${c.rotulo}`}
            cor="medo" sufixo="" desabilitado={ocupado || !podeEditar}
            aoMudar={(restam) => acao.mutate({
              tipo: 'marcas', combatente: c.id, pv_marcados: c.pv_marcados, pf_marcados: a.pf - restam })} />
        </>}
      </div>

      {podeEditar && !c.derrotado && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
          e.preventDefault()
          dano.mutate({ combatente: c.id, dano: Number(valor), resistente }, { onSuccess: () => setValor('') })
        }}>
          <Campo rotulo="Dano" type="number" min={0} className="w-24" value={valor}
            onChange={(e) => setValor(e.target.value)} aria-label={`Dano em ${c.rotulo}`} />
          <label className="mb-2 flex items-center gap-1.5 text-xs">
            <input type="checkbox" checked={resistente} onChange={(e) => setResistente(e.target.checked)} />
            Resistente (metade)
          </label>
          <Botao type="submit" variante="secundario" className="mb-0.5" disabled={ocupado || valor === ''}>Aplicar dano</Botao>
        </form>
      )}
      {dano.data && <p className="text-sm text-esperanca" aria-live="polite">{descreverDano(dano.data.resultado)}</p>}

      <Condicoes rotulo={c.rotulo} condicoes={c.condicoes} desabilitado={ocupado}
        aoAplicar={podeEditar ? (condicao) => acao.mutate({ tipo: 'condicao', combatente: c.id, condicao }) : undefined}
        aoTirar={podeEditar ? (condicao) => acao.mutate({ tipo: 'tirar_condicao', combatente: c.id, condicao }) : undefined} />

      <Aviso erro={acao.error ?? dano.error} />
      <div className="flex flex-wrap gap-2">
        <Botao variante="fantasma" className="!px-0" onClick={() => setVerFicha(!verFicha)}>
          {verFicha ? 'Esconder ficha' : 'Ver ficha completa'}
        </Botao>
        {podeEditar && (
          <Botao variante="fantasma" className="!px-2 text-perigo" disabled={ocupado}
            onClick={() => confirm(`Tirar ${c.rotulo} do encontro?`) && acao.mutate({ tipo: 'remover', combatente: c.id })}>
            Tirar do encontro
          </Botao>
        )}
      </div>
      {verFicha && <FichaInimigo adversario={a} />}
    </article>
  )
}

type Origem = 'inimigo' | 'npc' | 'srd'

function AdicionarCombatentes({ mesaId, sid, encontroId }: Alvo) {
  const [origem, setOrigem] = useState<Origem>('inimigo')
  const [id, setId] = useState('')
  const [busca, setBusca] = useState('')
  const [quantidade, setQuantidade] = useState(1)
  const inimigos = useInimigos(mesaId)
  const npcs = useNpcs(mesaId)
  const srd = useAdversariosSrd(origem === 'srd')
  const acao = useAcaoNoEncontro(mesaId, sid, encontroId)

  const opcoes: [string, string][] = useMemo(() => {
    if (origem === 'inimigo') return (inimigos.data ?? []).map((i) => [i.id, `${i.nome} (P${i.patamar})`])
    if (origem === 'npc') return (npcs.data ?? []).filter((n) => n.ficha_combate).map((n) => [n.id, n.nome])
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    return (srd.data ?? [])
      .filter((a) => !termo || a.nome.toLocaleLowerCase('pt-BR').includes(termo) || a.nome_original.toLowerCase().includes(termo))
      .map((a) => [a.id, `${a.nome} (P${a.patamar}, ${NOME_TIPO_ADVERSARIO[a.tipo]})`])
  }, [origem, inimigos.data, npcs.data, srd.data, busca])

  return (
    <form className="space-y-2 rounded-2xl border border-dashed border-borda p-4" onSubmit={(e) => {
      e.preventDefault()
      acao.mutate({ tipo: 'adicionar', origem, id, quantidade }, { onSuccess: () => setQuantidade(1) })
    }}>
      <h3 className="text-sm text-esperanca">Pôr inimigos no encontro</h3>
      <div className="grid gap-2 sm:grid-cols-[10rem_1fr_6rem_auto] sm:items-end">
        <Selecao rotulo="De onde" value={origem} onChange={(e) => { setOrigem(e.target.value as Origem); setId('') }}
          opcoes={[['inimigo', 'Inimigos da mesa'], ['npc', 'NPCs com ficha'], ['srd', 'Catálogo do SRD']]} />
        <div className="space-y-1">
          {origem === 'srd' && (
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar no SRD"
              aria-label="Buscar no SRD" className="w-full rounded-lg border border-borda bg-fundo px-3 py-1.5 text-sm" />
          )}
          <Selecao rotulo="Ficha" value={id} onChange={(e) => setId(e.target.value)}
            opcoes={[['', opcoes.length ? 'Escolha…' : 'Nada para escolher aqui'], ...opcoes]} />
        </div>
        <Campo rotulo="Cópias" type="number" min={1} max={20} value={quantidade}
          onChange={(e) => setQuantidade(Number(e.target.value) || 1)} />
        <Botao type="submit" disabled={!id || acao.isPending}>Adicionar</Botao>
      </div>
      <Aviso erro={acao.error} />
    </form>
  )
}

function EncontroAtual(alvo: Alvo) {
  const encontro = useEncontro(alvo.mesaId, alvo.sid, alvo.encontroId)
  if (encontro.isPending) return <Carregando />
  if (encontro.isError) return <Aviso erro={encontro.error} />
  const e = encontro.data
  const vivos = e.combatentes.filter((c) => !c.derrotado).length
  return (
    <div className="space-y-3">
      <p className="text-sm text-texto-suave">
        {e.combatentes.length === 0 ? 'Ninguém no encontro ainda.' : `${vivos} de ${e.combatentes.length} de pé.`}
      </p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {e.combatentes.map((c) => <CartaoCombatente key={c.id} {...alvo} c={c} />)}
      </div>
      {/* montar o encontro: o guia ao lado de onde se põem os inimigos (é só auxílio) */}
      <GuiaDeBatalha mesaId={alvo.mesaId} sid={alvo.sid} encontroId={e.id} guia={e.guia} podeEditar={alvo.podeEditar} />
      {alvo.podeEditar && <AdicionarCombatentes {...alvo} />}
    </div>
  )
}

export default function Encontros({ mesaId, sessao }: { mesaId: string; sessao: Sessao }) {
  const podeEditar = sessao.sou_responsavel
  const criar = useCriarEncontro(mesaId, sessao.id)
  const apagar = useApagarEncontro(mesaId, sessao.id)
  const [escolhido, setEscolhido] = useState<string | null>(null)
  const [nome, setNome] = useState('')
  const encontros = sessao.encontros
  const atual = encontros.some((e) => e.id === escolhido) ? escolhido : null

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-lg text-esperanca">Encontros</h3>
          <p className="text-xs text-texto-suave">Sem ordem: alguns podem não acontecer, conforme o caminho dos jogadores.</p>
        </div>
        {podeEditar && (
          <form className="flex items-end gap-2" onSubmit={(e) => {
            e.preventDefault()
            criar.mutate(nome.trim(), { onSuccess: (novo) => { setEscolhido(novo.id); setNome('') } })
          }}>
            <Campo rotulo="Novo encontro" value={nome} maxLength={120} onChange={(e) => setNome(e.target.value)}
              placeholder="Ex.: Emboscada na ponte" />
            <Botao type="submit" variante="secundario" disabled={!nome.trim() || criar.isPending}>Criar</Botao>
          </form>
        )}
      </div>
      <Aviso erro={criar.error ?? apagar.error} />
      {encontros.length === 0 && <p className="text-sm text-texto-suave">Nenhum encontro nesta sessão ainda.</p>}
      <ul className="flex flex-wrap gap-2">
        {encontros.map((e) => (
          <li key={e.id} className="w-56">
            <Escolhivel selecionado={e.id === atual} onClick={() => setEscolhido(e.id === atual ? null : e.id)}>
              <span className="block font-medium">{e.nome}</span>
              <span className="text-xs text-texto-suave">
                {e.combatentes - e.derrotados} de pé · {e.derrotados} derrotado{e.derrotados === 1 ? '' : 's'}
              </span>
            </Escolhivel>
          </li>
        ))}
      </ul>
      {atual && (
        <>
          {podeEditar && (
            <Botao variante="fantasma" className="!px-0 text-perigo" disabled={apagar.isPending}
              onClick={() => confirm('Apagar este encontro?') && apagar.mutate(atual, { onSuccess: () => setEscolhido(null) })}>
              Apagar este encontro
            </Botao>
          )}
          <EncontroAtual key={atual} mesaId={mesaId} sid={sessao.id} encontroId={atual} podeEditar={podeEditar} />
        </>
      )}
    </section>
  )
}
