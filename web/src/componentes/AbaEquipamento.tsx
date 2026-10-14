// Equipamento do personagem: arma principal, secundária e armadura, do
// catálogo do SRD. As regras (secundária com arma de duas mãos, arma mágica
// sem atributo de conjuração, requisitos como Pompous) são do motor: a tela
// avisa o óbvio e mostra a mensagem da API.
import { useMemo, useState } from 'react'

import { useArmaduras, useArmas, useEquipamento, useEquipar } from '../api/consultas'
import type { Arma, Armadura, Equipamento, Ficha } from '../api/tipos'
import { semConflito } from '../lib/conflito'
import { NOME_ALCANCE, NOME_TIPO_DANO, NOME_TRACO } from '../lib/rotulos'
import { AvisoDeConflito } from './Conflito'
import { Aviso, Botao, Carregando, Cartao, Escolhivel, Original, Selecao, Selo } from './ui'

type Vaga = 'principal' | 'secundaria' | 'armadura'

const NOME_VAGA: Record<Vaga, string> = { principal: 'Arma principal', secundaria: 'Arma secundária', armadura: 'Armadura' }

function Caracteristicas({ lista }: { lista: { nome: string; descricao: string; nome_original?: string }[] }) {
  if (lista.length === 0) return null
  return (
    <ul className="mt-1 space-y-0.5 text-xs text-texto-suave">
      {lista.map((c) => <li key={c.nome}><b className="text-texto">{c.nome}</b>: {c.descricao}</li>)}
    </ul>
  )
}

function DescricaoArma({ a }: { a: Arma }) {
  const dano = `${a.dado}${a.modificador_dano ? `+${a.modificador_dano}` : ''}`
  return (
    <>
      <span className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{a.nome}<Original nome={a.nome} original={a.nome_original} /></span>
        <span className="flex gap-1">
          <Selo>P{a.tier}</Selo>
          {a.categoria === 'PRIMARY_MAGIC' && <Selo destaque>mágica</Selo>}
          {a.duas_maos && <Selo>duas mãos</Selo>}
        </span>
      </span>
      <span className="block text-xs text-texto-suave">
        {NOME_TRACO[a.traco]} · {NOME_ALCANCE[a.alcance] ?? a.alcance} · {dano} {NOME_TIPO_DANO[a.tipo_dano]}
      </span>
      <Caracteristicas lista={a.caracteristicas} />
    </>
  )
}

function DescricaoArmadura({ a, nivel }: { a: Armadura; nivel: number }) {
  return (
    <>
      <span className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium">{a.nome}<Original nome={a.nome} original={a.nome_original} /></span>
        <Selo>P{a.tier}</Selo>
      </span>
      <span className="block text-xs text-texto-suave">
        Pontuação {a.pontuacao} · Limiares {a.limiar_maior + nivel}/{a.limiar_grave + nivel} no seu nível
      </span>
      <Caracteristicas lista={a.caracteristicas} />
    </>
  )
}

function Catalogo<T extends { id: string; nome: string; nome_original: string; tier: number }>({ itens, escolhido, aoEscolher, render }: {
  itens: T[]; escolhido?: string | null; aoEscolher: (id: string | null) => void; render: (item: T) => React.ReactNode
}) {
  const [busca, setBusca] = useState('')
  const [tier, setTier] = useState('')
  const filtrados = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    return itens.filter((i) => (!tier || i.tier === Number(tier))
      && (!termo || i.nome.toLocaleLowerCase('pt-BR').includes(termo) || i.nome_original.toLowerCase().includes(termo)))
  }, [itens, busca, tier])
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[minmax(0,1fr)_8rem] gap-2">
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar (português ou inglês)"
          aria-label="Buscar no catálogo" className="min-w-0 rounded-lg border border-borda bg-fundo px-3 py-2 text-sm" />
        <Selecao rotulo="" aria-label="Patamar" value={tier} onChange={(e) => setTier(e.target.value)}
          opcoes={[['', 'Todos'], ...[1, 2, 3, 4].map((p): [string, string] => [String(p), `Patamar ${p}`])]} />
      </div>
      <ul className="max-h-96 space-y-1.5 overflow-y-auto pr-1">
        <li>
          <Escolhivel selecionado={!escolhido} onClick={() => aoEscolher(null)}>
            <span className="text-sm text-texto-suave">Nenhuma</span>
          </Escolhivel>
        </li>
        {filtrados.map((i) => (
          <li key={i.id}>
            <Escolhivel selecionado={i.id === escolhido} onClick={() => aoEscolher(i.id)}>{render(i)}</Escolhivel>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function AbaEquipamento({ personagemId, ficha }: { personagemId: string; ficha: Ficha }) {
  const atual = useEquipamento(personagemId)
  const armas = useArmas()
  const armaduras = useArmaduras()
  const equipar = useEquipar(personagemId)
  const [rascunho, setRascunho] = useState<Equipamento | null>(null)
  const [vaga, setVaga] = useState<Vaga>('principal')

  if (!atual.data || !armas.data || !armaduras.data) {
    const erro = atual.error ?? armas.error ?? armaduras.error
    return erro ? <Aviso erro={erro} /> : <Carregando />
  }
  const listaArmaduras: Armadura[] = armaduras.data
  const eq: Equipamento = rascunho ?? atual.data
  const porId = new Map(armas.data.map((a) => [a.id, a]))
  const principal = eq.principal ? porId.get(eq.principal) : undefined
  const armadura = eq.armadura ? listaArmaduras.find((a) => a.id === eq.armadura) : undefined
  const mudou = rascunho !== null && JSON.stringify(rascunho) !== JSON.stringify(atual.data)

  function escolher(id: string | null) {
    const novo = { ...eq, [vaga]: id }
    // arma de duas mãos não deixa mão livre para a secundária
    if (vaga === 'principal' && id && porId.get(id)?.duas_maos) novo.secundaria = null
    setRascunho(novo)
    equipar.reset()
  }

  const resumo = (v: Vaga) => {
    const id = eq[v]
    if (!id) return 'Nenhuma'
    return v === 'armadura' ? listaArmaduras.find((a) => a.id === id)?.nome ?? id : porId.get(id)?.nome ?? id
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
      <Cartao titulo="Equipado">
        <ul className="space-y-2">
          {(Object.keys(NOME_VAGA) as Vaga[]).map((v) => {
            const bloqueada = v === 'secundaria' && !!principal?.duas_maos
            return (
              <li key={v}>
                <Escolhivel selecionado={vaga === v} desabilitado={bloqueada} onClick={() => setVaga(v)}>
                  <span className="block text-xs text-texto-suave">{NOME_VAGA[v]}</span>
                  <span className="font-medium">{bloqueada ? 'Mãos ocupadas (duas mãos)' : resumo(v)}</span>
                </Escolhivel>
              </li>
            )
          })}
        </ul>
        {armadura && (
          <p className="mt-3 text-xs text-texto-suave">
            Com {armadura.nome}: pontuação {armadura.pontuacao}, limiares {armadura.limiar_maior + ficha.nivel}/
            {armadura.limiar_grave + ficha.nivel}.
          </p>
        )}
        <div className="mt-4 space-y-2">
          {/* o rascunho guarda a versão de onde partiu: se o equipamento mudou em outra aba, avisa */}
          <AvisoDeConflito erro={equipar.error} ocupado={equipar.isPending}
            aoVerAtual={() => { setRascunho(null); equipar.reset(); void atual.refetch() }}
            aoSalvarMesmoAssim={() => equipar.mutate({ ...eq, versao: null }, { onSuccess: () => setRascunho(null) })} />
          <Aviso erro={semConflito(equipar.error)} />
          <Botao className="w-full" disabled={!mudou || equipar.isPending}
            onClick={() => equipar.mutate(eq, { onSuccess: () => setRascunho(null) })}>
            {equipar.isPending ? 'Equipando…' : 'Salvar equipamento'}
          </Botao>
          {mudou && (
            <Botao variante="fantasma" className="w-full" onClick={() => { setRascunho(null); equipar.reset() }}>
              Desfazer mudanças
            </Botao>
          )}
        </div>
      </Cartao>

      <Cartao titulo={`Escolher: ${NOME_VAGA[vaga]}`}>
        {vaga === 'armadura' ? (
          <Catalogo<Armadura> itens={listaArmaduras} escolhido={eq.armadura} aoEscolher={escolher}
            render={(a) => <DescricaoArmadura a={a} nivel={ficha.nivel} />} />
        ) : (
          <Catalogo<Arma> key={vaga} escolhido={eq[vaga]} aoEscolher={escolher}
            itens={[...porId.values()].filter((a) => (vaga === 'principal') === (a.categoria !== 'SECONDARY'))}
            render={(a) => <DescricaoArma a={a} />} />
        )}
        {vaga === 'principal' && ficha.conjuracoes.length === 0 && (
          <p className="mt-2 text-xs text-texto-suave">Armas mágicas pedem um atributo de conjuração (sua subclasse não tem).</p>
        )}
      </Cartao>
    </div>
  )
}
