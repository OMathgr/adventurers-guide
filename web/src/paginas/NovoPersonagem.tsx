// Assistente de criação de personagem. Cada etapa só libera a seguinte
// quando está completa; a validação final é do motor (a API devolve a
// mensagem da regra, que aparece na revisão).
import { useState } from 'react'
import { useNavigate } from 'react-router'

import {
  useAncestralidades, useCartas, useClasses, useComunidades, useCriarPersonagem, useItensSrd, useSubclasses,
} from '../api/consultas'
import type { Ancestralidade, Caracteristica, Classe, Subclasse, TipoDano, Traco } from '../api/tipos'
import { comoItem, ListaDeHabilidades } from '../componentes/Habilidades'
import { Aviso, Botao, Campo, Carregando, Cartao, Escolhivel, Etapas, Original, Selo } from '../componentes/ui'
import { useNomeDominio } from '../lib/nomes'
import { cartasNaCriacao, type Distribuicao, distribuicaoCompleta, valoresRestantes } from '../lib/regras'
import {
  comSinal, NOME_TIPO_DANO, NOME_TRACO, TRACOS, USO_TRACO,
} from '../lib/rotulos'

const ETAPAS = ['Classe', 'Subclasse', 'Herança', 'Atributos', 'Experiências', 'Cartas', 'Itens', 'Revisão']
// Passo 5 do SRD: além destes, o motor dá tocha, corda, suprimentos e 1 punhado de ouro
const POCOES = ['core_consumable_minor_health_potion', 'core_consumable_minor_stamina_potion']
// Única subclasse do SRD 1.0 com companheiro (a API recusa se faltar ou sobrar)
const BEASTBOUND = 'core_subclass_beastbound'

type Rascunho = {
  classe?: Classe
  subclasse?: Subclasse
  companheiro: { nome: string; experiencias: [string, string]; tipo_dano: TipoDano }
  ancestralidade?: Ancestralidade
  mista: boolean
  segunda?: Ancestralidade
  comunidade?: string
  tracos: Distribuicao
  experiencias: [string, string]
  proposito?: string
  cartas: string[]
  pocao?: string
  item_de_classe?: string
  nome: string
}

const VAZIO: Rascunho = {
  companheiro: { nome: '', experiencias: ['', ''], tipo_dano: 'PHYSICAL' },
  mista: false, tracos: {}, experiencias: ['', ''], cartas: [], nome: '',
}

/** As duas características que o personagem terá (mista: 1ª de uma, 2ª de outra). */
function caracteristicasEscolhidas(r: Rascunho): Caracteristica[] {
  if (!r.ancestralidade) return []
  if (r.mista && r.segunda) return [r.ancestralidade.caracteristicas[0], r.segunda.caracteristicas[1]]
  return r.ancestralidade.caracteristicas
}

export default function NovoPersonagem() {
  const [etapa, setEtapa] = useState(0)
  const [r, setR] = useState<Rascunho>(VAZIO)
  const atualizar = (parcial: Partial<Rascunho>) => setR((atual) => ({ ...atual, ...parcial }))

  const temCompanheiro = r.subclasse?.id === BEASTBOUND
  const temProposito = caracteristicasEscolhidas(r).some((c) => c.efeito === 'PROPOSITO')
  const exps = r.experiencias.map((e) => e.trim())

  const etapaCompleta = [
    !!r.classe,
    !!r.subclasse && (!temCompanheiro || (r.companheiro.nome.trim() !== ''
      && r.companheiro.experiencias.every((e) => e.trim()) &&
      r.companheiro.experiencias[0].trim() !== r.companheiro.experiencias[1].trim())),
    !!r.ancestralidade && !!r.comunidade && (!r.mista || !!r.segunda),
    distribuicaoCompleta(r.tracos),
    exps.every(Boolean) && exps[0] !== exps[1] && (!temProposito || exps.includes(r.proposito ?? '')),
    r.cartas.length === cartasNaCriacao(r.subclasse),
    !!r.pocao && !!r.item_de_classe,
    r.nome.trim() !== '',
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-2xl">Novo personagem</h1>
      <Etapas etapas={ETAPAS} atual={etapa} />

      {etapa === 0 && <EtapaClasse r={r} atualizar={atualizar} />}
      {etapa === 1 && <EtapaSubclasse r={r} atualizar={atualizar} temCompanheiro={temCompanheiro} />}
      {etapa === 2 && <EtapaHeranca r={r} atualizar={atualizar} />}
      {etapa === 3 && <EtapaTracos r={r} atualizar={atualizar} />}
      {etapa === 4 && <EtapaExperiencias r={r} atualizar={atualizar} temProposito={temProposito} />}
      {etapa === 5 && <EtapaCartas r={r} atualizar={atualizar} />}
      {etapa === 6 && <EtapaItens r={r} atualizar={atualizar} />}
      {etapa === 7 && <EtapaRevisao r={r} atualizar={atualizar} temCompanheiro={temCompanheiro} temProposito={temProposito} />}

      <div className="flex justify-between pt-2">
        <Botao variante="secundario" onClick={() => setEtapa((e) => e - 1)} disabled={etapa === 0}>Voltar</Botao>
        {etapa < ETAPAS.length - 1 && (
          <Botao onClick={() => setEtapa((e) => e + 1)} disabled={!etapaCompleta[etapa]}>Continuar</Botao>
        )}
      </div>
    </div>
  )
}

type PropsEtapa = { r: Rascunho; atualizar: (p: Partial<Rascunho>) => void }

function EtapaClasse({ r, atualizar }: PropsEtapa) {
  const classes = useClasses()
  const dominio = useNomeDominio()
  if (classes.isPending) return <Carregando />
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {classes.data?.map((c) => (
        <Escolhivel key={c.id} selecionado={r.classe?.id === c.id}
          onClick={() => atualizar({ classe: c, subclasse: undefined, cartas: [], item_de_classe: undefined })}>
          <p className="font-titulo text-lg">{c.nome}<Original nome={c.nome} original={c.nome_original} /></p>
          <p className="mt-1 text-sm text-texto-suave">{c.dominios.map(dominio).join(' & ')}</p>
          <p className="mt-2 flex gap-2"><Selo>Evasão {c.evasao_inicial}</Selo><Selo>PV {c.pv_iniciais}</Selo></p>
        </Escolhivel>
      ))}
      {r.classe && (
        <Cartao titulo={`Habilidades de ${r.classe.nome}`} className="sm:col-span-2 lg:col-span-3">
          <ListaDeHabilidades lista={[...(r.classe.habilidade_esperanca ? [r.classe.habilidade_esperanca] : []),
            ...(r.classe.habilidades ?? [])].map(comoItem)} />
        </Cartao>
      )}
    </div>
  )
}

function EtapaSubclasse({ r, atualizar, temCompanheiro }: PropsEtapa & { temCompanheiro: boolean }) {
  const subclasses = useSubclasses(r.classe?.id)
  const comp = r.companheiro
  const mudarComp = (parcial: Partial<Rascunho['companheiro']>) => atualizar({ companheiro: { ...comp, ...parcial } })
  if (subclasses.isPending) return <Carregando />
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        {subclasses.data?.map((s) => (
          <Escolhivel key={s.id} selecionado={r.subclasse?.id === s.id}
            onClick={() => atualizar({ subclasse: s, cartas: r.cartas.slice(0, cartasNaCriacao(s)) })}>
            <p className="font-titulo text-lg">{s.nome}<Original nome={s.nome} original={s.nome_original} /></p>
            <p className="mt-1 text-sm text-texto-suave">
              {s.traco_conjuracao ? `Conjura com ${NOME_TRACO[s.traco_conjuracao as Traco]}` : 'Não conjura'}
            </p>
            <p className="mt-2 text-xs uppercase tracking-wider text-texto-suave">Fundamental</p>
            <div className="mt-1"><ListaDeHabilidades lista={(s.fundacao ?? []).map(comoItem)} resumida /></div>
          </Escolhivel>
        ))}
      </div>
      {temCompanheiro && (
        <Cartao titulo="Seu companheiro animal">
          <div className="grid gap-3 sm:grid-cols-3">
            <Campo rotulo="Nome" value={comp.nome} onChange={(e) => mudarComp({ nome: e.target.value })} />
            {[0, 1].map((i) => (
              <Campo key={i} rotulo={`Experiência ${i + 1} (+2)`} placeholder="Ex.: Farejar"
                value={comp.experiencias[i]}
                onChange={(e) => {
                  const novas = [...comp.experiencias] as [string, string]
                  novas[i] = e.target.value
                  mudarComp({ experiencias: novas })
                }} />
            ))}
          </div>
          <fieldset className="mt-3 flex gap-4 text-sm">
            <legend className="mb-1 text-texto-suave">Dano</legend>
            {(['PHYSICAL', 'MAGICAL'] as const).map((t) => (
              <label key={t} className="flex items-center gap-1.5">
                <input type="radio" checked={comp.tipo_dano === t} onChange={() => mudarComp({ tipo_dano: t })} />
                {NOME_TIPO_DANO[t]}
              </label>
            ))}
          </fieldset>
        </Cartao>
      )}
    </div>
  )
}

function CaracteristicasDe({ lista }: { lista: Caracteristica[] }) {
  return (
    <ul className="mt-2 space-y-1 text-sm">
      {lista.map((c) => (
        <li key={c.nome}><span className="font-semibold text-texto">{c.nome}</span>
          <Original nome={c.nome} original={c.nome_original} />:{' '}
          <span className="text-texto-suave">{c.descricao}</span></li>
      ))}
    </ul>
  )
}

function EtapaHeranca({ r, atualizar }: PropsEtapa) {
  const ancestralidades = useAncestralidades()
  const comunidades = useComunidades()
  if (ancestralidades.isPending || comunidades.isPending) return <Carregando />
  const escolhidas = caracteristicasEscolhidas(r)

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg">Ancestralidade</h2>
          <label className="flex items-center gap-2 text-sm text-texto-suave">
            <input type="checkbox" checked={r.mista}
              onChange={(e) => atualizar({ mista: e.target.checked, segunda: undefined })} />
            Ancestralidade mista
          </label>
        </div>
        {r.mista && (
          <p className="text-sm text-texto-suave">
            Escolha a primeira ancestralidade (dá a 1ª característica) e depois a segunda (dá a 2ª).
          </p>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          {ancestralidades.data?.map((a) => {
            const ehPrimeira = r.ancestralidade?.id === a.id
            const ehSegunda = r.segunda?.id === a.id
            return (
              <Escolhivel key={a.id} selecionado={ehPrimeira || ehSegunda}
                onClick={() => {
                  if (!r.mista || !r.ancestralidade || ehPrimeira) atualizar({ ancestralidade: a, segunda: undefined })
                  else atualizar({ segunda: a })
                }}>
                <p className="flex items-center gap-2 font-titulo text-lg">
                  <span>{a.nome}<Original nome={a.nome} original={a.nome_original} /></span>
                  {r.mista && ehPrimeira && <Selo destaque>1ª</Selo>}
                  {r.mista && ehSegunda && <Selo destaque>2ª</Selo>}
                </p>
                <CaracteristicasDe lista={a.caracteristicas} />
              </Escolhivel>
            )
          })}
        </div>
        {r.mista && r.ancestralidade && r.segunda && (
          <Cartao titulo="Suas características">
            <CaracteristicasDe lista={escolhidas} />
          </Cartao>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg">Comunidade</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {comunidades.data?.map((c) => (
            <Escolhivel key={c.id} selecionado={r.comunidade === c.id} onClick={() => atualizar({ comunidade: c.id })}>
              <p className="font-titulo">{c.nome}<Original nome={c.nome} original={c.nome_original} /></p>
              <CaracteristicasDe lista={c.caracteristicas ?? []} />
            </Escolhivel>
          ))}
        </div>
      </section>
    </div>
  )
}

function EtapaTracos({ r, atualizar }: PropsEtapa) {
  const restantes = valoresRestantes(r.tracos)
  return (
    <div className="space-y-3">
      <p className="text-sm text-texto-suave">
        Distribua +2, +1, +1, +0, +0 e −1 entre os seis atributos.
        {restantes.length > 0 && <> Faltam: {restantes.map(comSinal).join(', ')}.</>}
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {TRACOS.map((t) => {
          const atual = r.tracos[t]
          const opcoes = [...new Set([...(atual !== undefined ? [atual] : []), ...restantes])].sort((a, b) => b - a)
          return (
            <label key={t} className="flex items-center justify-between gap-3 rounded-xl border border-borda bg-superficie p-3">
              <span>
                <span className="block font-semibold">{NOME_TRACO[t]}</span>
                <span className="text-xs text-texto-suave">{USO_TRACO[t]}</span>
              </span>
              <select value={atual ?? ''} aria-label={NOME_TRACO[t]}
                onChange={(e) => {
                  const novo = { ...r.tracos }
                  if (e.target.value === '') delete novo[t]
                  else novo[t] = Number(e.target.value)
                  atualizar({ tracos: novo })
                }}
                className="rounded-lg border border-borda bg-fundo px-2 py-1 text-lg">
                <option value="">—</option>
                {opcoes.map((v) => <option key={v} value={v}>{comSinal(v)}</option>)}
              </select>
            </label>
          )
        })}
      </div>
    </div>
  )
}

function EtapaExperiencias({ r, atualizar, temProposito }: PropsEtapa & { temProposito: boolean }) {
  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-texto-suave">
        Duas Experiências que contam a história do personagem (ex.: “Diplomata”, “Ladra de tavernas”). Cada uma começa em +2.
      </p>
      {[0, 1].map((i) => (
        <Campo key={i} rotulo={`Experiência ${i + 1}`} value={r.experiencias[i]}
          onChange={(e) => {
            const novas = [...r.experiencias] as [string, string]
            novas[i] = e.target.value
            atualizar({ experiencias: novas })
          }} />
      ))}
      {temProposito && (
        <Cartao titulo="Projeto com Propósito">
          <p className="mb-2 text-sm text-texto-suave">Qual Experiência combina com o propósito para o qual você foi feito? Ela ganha +1.</p>
          {r.experiencias.filter((e) => e.trim()).map((e) => (
            <label key={e} className="flex items-center gap-2 text-sm">
              <input type="radio" checked={r.proposito === e.trim()} onChange={() => atualizar({ proposito: e.trim() })} />
              {e}
            </label>
          ))}
        </Cartao>
      )}
    </div>
  )
}

function EtapaCartas({ r, atualizar }: PropsEtapa) {
  const cartas = useCartas()
  const dominio = useNomeDominio()
  if (cartas.isPending) return <Carregando />
  const disponiveis = cartas.data?.filter((c) => c.nivel === 1 && r.classe?.dominios.includes(c.dominio)) ?? []
  const quantas = cartasNaCriacao(r.subclasse)
  const alternar = (id: string) =>
    atualizar({ cartas: r.cartas.includes(id) ? r.cartas.filter((c) => c !== id) : [...r.cartas, id] })

  return (
    <div className="space-y-3">
      <p className="text-sm text-texto-suave">
        Escolha {quantas} cartas de nível 1 dos domínios da classe ({r.cartas.length}/{quantas})
        {quantas > 2 && `: ${r.subclasse?.nome} dá uma a mais`}.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {disponiveis.map((c) => (
          <Escolhivel key={c.id} selecionado={r.cartas.includes(c.id)}
            desabilitado={!r.cartas.includes(c.id) && r.cartas.length >= quantas} onClick={() => alternar(c.id)}>
            <p className="flex items-center justify-between gap-2">
              <span className="font-titulo">{c.nome}<Original nome={c.nome} original={c.nome_original} /></span>
              <Selo>{dominio(c.dominio)}</Selo>
            </p>
            <p className="mt-2 whitespace-pre-line text-sm text-texto-suave">{c.texto}</p>
          </Escolhivel>
        ))}
      </div>
    </div>
  )
}

function EtapaItens({ r, atualizar }: PropsEtapa) {
  const itens = useItensSrd()
  if (itens.isPending) return <Carregando />
  const porId = (id: string) => itens.data?.find((i) => i.id === id)
  const comuns = itens.data?.filter((i) => i.tipo === 'COMUM') ?? []

  return (
    <div className="space-y-4">
      <p className="text-sm text-texto-suave">
        Todo personagem começa com {comuns.map((i) => i.nome.toLowerCase()).join(', ')} e 1 punhado de ouro.
      </p>
      <div>
        <h2 className="mb-2 text-sm font-semibold">Escolha uma poção</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {POCOES.map((id) => {
            const p = porId(id)
            return p && (
              <Escolhivel key={id} selecionado={r.pocao === id} onClick={() => atualizar({ pocao: id })}>
                <span className="font-medium">{p.nome}<Original nome={p.nome} original={p.nome_original} /></span>
                <span className="block text-sm text-texto-suave">{p.texto}</span>
              </Escolhivel>
            )
          })}
        </div>
      </div>
      <div>
        <h2 className="mb-2 text-sm font-semibold">Escolha um item da classe</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {r.classe?.itens.map((id) => (
            <Escolhivel key={id} selecionado={r.item_de_classe === id} onClick={() => atualizar({ item_de_classe: id })}>
              <span className="font-medium">{porId(id)?.nome ?? id}</span>
            </Escolhivel>
          ))}
        </div>
      </div>
    </div>
  )
}

function EtapaRevisao({ r, atualizar, temCompanheiro, temProposito }:
  PropsEtapa & { temCompanheiro: boolean; temProposito: boolean }) {
  const criar = useCriarPersonagem()
  const navegar = useNavigate()
  const cartas = useCartas()
  const itens = useItensSrd()

  function confirmar() {
    criar.mutate({
      nome: r.nome.trim(),
      classe: r.classe!.id,
      subclasse: r.subclasse!.id,
      ancestralidade: r.ancestralidade!.id,
      segunda_ancestralidade: r.mista ? r.segunda?.id : null,
      comunidade: r.comunidade!,
      tracos: r.tracos as Record<string, number>,
      experiencias: r.experiencias.map((e) => e.trim()),
      experiencia_proposito: temProposito ? r.proposito : null,
      cartas: r.cartas,
      pocao_inicial: r.pocao,
      item_de_classe: r.item_de_classe,
      companheiro: temCompanheiro ? {
        nome: r.companheiro.nome.trim(),
        experiencias: r.companheiro.experiencias.map((e) => e.trim()),
        tipo_dano: r.companheiro.tipo_dano,
      } : null,
    }, { onSuccess: (criado) => navegar(`/personagens/${criado.id}`) })
  }

  const linha = (rotulo: string, valor: string) => (
    <div className="flex justify-between gap-4 border-b border-borda/60 py-1.5 text-sm">
      <span className="text-texto-suave">{rotulo}</span><span className="text-right">{valor}</span>
    </div>
  )

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Cartao titulo="Resumo">
        {linha('Classe', `${r.classe!.nome} · ${r.subclasse!.nome}`)}
        {linha('Ancestralidade', r.mista && r.segunda ? `${r.ancestralidade!.nome} / ${r.segunda.nome}` : r.ancestralidade!.nome)}
        {linha('Atributos', TRACOS.map((t) => `${NOME_TRACO[t]} ${comSinal(r.tracos[t] ?? 0)}`).join(', '))}
        {linha('Experiências', r.experiencias.join(', '))}
        {linha('Cartas', r.cartas.map((id) => cartas.data?.find((c) => c.id === id)?.nome ?? id).join(', '))}
        {linha('Itens', [r.pocao, r.item_de_classe].map((id) => itens.data?.find((i) => i.id === id)?.nome ?? id).join(', '))}
        {temCompanheiro && linha('Companheiro', r.companheiro.nome)}
      </Cartao>
      <Cartao titulo="Como se chama?">
        <div className="space-y-4">
          <Campo rotulo="Nome do personagem" value={r.nome} maxLength={120}
            onChange={(e) => atualizar({ nome: e.target.value })} />
          <Aviso erro={criar.error} />
          <Botao onClick={confirmar} disabled={!r.nome.trim() || criar.isPending} className="w-full">
            {criar.isPending ? 'Criando…' : 'Criar personagem'}
          </Botao>
        </div>
      </Cartao>
    </div>
  )
}
