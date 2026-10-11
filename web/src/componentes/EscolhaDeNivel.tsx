// Escolhas do próximo nível, dentro da coluna dele na linha do tempo:
// conquista de patamar, avanços marcados direto na caixa do patamar (os
// detalhes aparecem logo abaixo), treinos do companheiro, carta do nível e
// confirmar. O que pode ser marcado vem da API (GET /proximo-nivel); o motor
// valida tudo no envio.
import { useMemo, useRef, useState } from 'react'

import {
  useClasses, useOpcoesDeCarta, useSubclasses, useSubirDeNivel,
} from '../api/consultas'
import type {
  AlvoFeroz, Escolha, Ficha, Opcao, OpcaoTreino, ProximoNivel, QuadroDeAvanco, Traco, Treino,
} from '../api/tipos'
import { useNomeDominio, useNomes } from '../lib/nomes'
import { type AvancoMarcado, custoTotal, podeMarcar, treinosExigidos } from '../lib/regras'
import { NOME_ALVO_FEROZ, NOME_OPCAO, NOME_TRACO, NOME_TREINO, TRACOS } from '../lib/rotulos'
import QuadroAvanco, { type Interacao } from './QuadroAvanco'
import { Aviso, Botao, Campo, Carregando, Escolhivel, Original, Selo } from './ui'

const BEASTBOUND = 'core_subclass_beastbound'

/** Detalhes que algumas opções pedem (atributos, experiências, carta, multiclasse). */
type Detalhe = {
  tracos: Traco[]
  experiencias: string[]
  carta?: string
  classe?: string
  dominio?: string
  subclasse?: string
  companheiro: { nome: string; experiencias: [string, string] }
}

const DETALHE_VAZIO: Detalhe = { tracos: [], experiencias: [], companheiro: { nome: '', experiencias: ['', ''] } }

function detalheCompleto(opcao: Opcao, d: Detalhe): boolean {
  switch (opcao) {
    case 'TRACOS': return d.tracos.length === 2
    case 'EXPERIENCIAS': return d.experiencias.length === 2
    case 'CARTA_DOMINIO': return !!d.carta
    case 'MULTICLASSE': {
      if (!d.classe || !d.dominio || !d.subclasse) return false
      if (d.subclasse !== BEASTBOUND) return true
      const [a, b] = d.companheiro.experiencias.map((e) => e.trim())
      return !!d.companheiro.nome.trim() && !!a && !!b && a !== b
    }
    default: return true
  }
}

const PEDE_DETALHE: Opcao[] = ['TRACOS', 'EXPERIENCIAS', 'CARTA_DOMINIO', 'MULTICLASSE']

function paraEscolha(m: AvancoMarcado, d: Detalhe): Escolha {
  const base: Escolha = { opcao: m.opcao, tier: m.tier, tracos: [], experiencias: [] }
  switch (m.opcao) {
    case 'TRACOS': return { ...base, tracos: d.tracos }
    case 'EXPERIENCIAS': return { ...base, experiencias: d.experiencias }
    case 'CARTA_DOMINIO': return { ...base, carta: d.carta }
    case 'MULTICLASSE': return {
      ...base, classe: d.classe, dominio: d.dominio, subclasse: d.subclasse,
      companheiro: d.subclasse === BEASTBOUND
        ? { nome: d.companheiro.nome.trim(), experiencias: d.companheiro.experiencias.map((e) => e.trim()),
            tipo_dano: 'PHYSICAL' }
        : null,
    }
    default: return base
  }
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h4 className="text-xs uppercase tracking-wider text-esperanca">{titulo}</h4>
      {children}
    </section>
  )
}

type Props = {
  id: string
  ficha: Ficha
  proximo: ProximoNivel
  quadros: QuadroDeAvanco[]
  aoConcluir?: () => void
}

export default function EscolhaDeNivel({ id, ficha, proximo, quadros, aoConcluir }: Props) {
  const [novaExp, setNovaExp] = useState('')
  const [expCompanheiro, setExpCompanheiro] = useState('')
  const [marcados, setMarcados] = useState<AvancoMarcado[]>([])
  const [detalhes, setDetalhes] = useState<Record<string, Detalhe>>({})
  const [treinosEscolhidos, setTreinos] = useState<Treino[]>([])
  const proximaChave = useRef(0)
  const [carta, setCarta] = useState<string>()
  const [troca, setTroca] = useState<{ antiga?: string; nova?: string } | null>(null)
  const subir = useSubirDeNivel(id)

  const nTreinos = treinosExigidos(proximo, marcados)
  // a quantidade de treinos depende dos avanços (subclasse dá treino extra)
  const treinos: Treino[] = Array.from({ length: nTreinos },
    (_, i) => treinosEscolhidos[i] ?? { opcao: 'ATENTO' as OpcaoTreino })
  const escolhas = useMemo(
    () => marcados.map((m) => paraEscolha(m, detalhes[m.chave] ?? DETALHE_VAZIO)), [marcados, detalhes])

  const conquistaOk = !proximo.nova_experiencia
    || (!!novaExp.trim() && (!proximo.experiencia_companheiro || !!expCompanheiro.trim()))
  const avancosOk = custoTotal(marcados) === proximo.avancos
    && marcados.every((m) => detalheCompleto(m.opcao, detalhes[m.chave] ?? DETALHE_VAZIO))
  const treinosOk = treinos.every((t) =>
    (t.opcao !== 'INTELIGENTE' || !!t.experiencia) && (t.opcao !== 'FEROZ' || !!t.alvo))
  const cartaOk = !!carta && (troca === null || (!!troca.antiga && !!troca.nova))
  const pronto = conquistaOk && avancosOk && treinosOk && cartaOk

  const daApi = (tier: number, opcao: Opcao) => proximo.opcoes.find((o) => o.tier === tier && o.opcao === opcao)

  const interacao: Interacao = {
    selecionados: (tier, opcao) => marcados.filter((m) => m.tier === tier && m.opcao === opcao).length,
    pode: (tier, opcao) => {
      const o = daApi(tier, opcao)
      return !!o && podeMarcar(o, marcados, proximo.avancos)
    },
    marcar: (tier, opcao) => {
      const o = daApi(tier, opcao)
      if (!o) return
      const chave = `${tier}-${opcao}-${proximaChave.current++}`
      setMarcados((m) => [...m, { ...o, chave }])
      setDetalhes((d) => ({ ...d, [chave]: DETALHE_VAZIO }))
      setCarta(undefined)   // mudar avanços pode mudar as cartas possíveis
      setTroca(null)
    },
    desmarcar: (tier, opcao) => {
      const ultimo = marcados.findLast((m) => m.tier === tier && m.opcao === opcao)
      if (!ultimo) return
      setMarcados((m) => m.filter((x) => x.chave !== ultimo.chave))
      setCarta(undefined)
      setTroca(null)
    },
  }

  const mudarDetalhe = (chave: string, parcial: Partial<Detalhe>) =>
    setDetalhes((d) => ({ ...d, [chave]: { ...(d[chave] ?? DETALHE_VAZIO), ...parcial } }))

  function confirmar() {
    subir.mutate({
      nivel: proximo.nivel,
      escolhas,
      carta: carta!,
      nova_experiencia: proximo.nova_experiencia ? novaExp.trim() : null,
      experiencia_companheiro: proximo.experiencia_companheiro ? expCompanheiro.trim() : null,
      troca_carta: troca ? [troca.antiga!, troca.nova!] : null,
      treinos,
    }, { onSuccess: aoConcluir })
  }

  const experienciasDisponiveis = [...Object.keys(ficha.experiencias), ...(novaExp.trim() ? [novaExp.trim()] : [])]
  const [proprio, ...anteriores] = quadros
  // patamares anteriores só aparecem se ainda têm quadradinho livre
  const anterioresUteis = anteriores.filter((q) => proximo.opcoes.some((o) => o.tier === q.tier))
  const comDetalhe = marcados.filter((m) => PEDE_DETALHE.includes(m.opcao))

  return (
    <div className="space-y-5">
      {proximo.nova_experiencia && (
        <Secao titulo="Conquista de patamar">
          <p className="text-sm text-texto-suave">
            Nova Experiência com +2 e +1 de Proficiência
            {proximo.limpa_marcas_tracos && '; as marcas dos atributos são limpas'}.
          </p>
          <Campo rotulo="Nova Experiência" value={novaExp} onChange={(e) => setNovaExp(e.target.value)} />
          {proximo.experiencia_companheiro && (
            <Campo rotulo="Nova Experiência do companheiro" value={expCompanheiro}
              onChange={(e) => setExpCompanheiro(e.target.value)} />
          )}
        </Secao>
      )}

      <Secao titulo={`Avanços (${custoTotal(marcados)}/${proximo.avancos})`}>
        <p className="text-sm text-texto-suave">Marque {proximo.avancos} avanços na caixa do patamar.</p>
        {proprio && <QuadroAvanco quadro={proprio} interacao={interacao} />}
        {anterioresUteis.length > 0 && (
          <details className="rounded-xl border border-borda p-2" open={anterioresUteis.some((q) =>
            marcados.some((m) => m.tier === q.tier))}>
            <summary className="cursor-pointer text-sm text-texto-suave">Usar um patamar anterior</summary>
            <div className="mt-2 space-y-2">
              {anterioresUteis.map((q) => <QuadroAvanco key={q.tier} quadro={q} interacao={interacao} />)}
            </div>
          </details>
        )}
        {comDetalhe.map((m) => (
          <div key={m.chave} className="rounded-xl border border-esperanca/40 p-3">
            <p className="mb-2 text-sm font-medium">
              {NOME_OPCAO[m.opcao]} <span className="text-xs text-texto-suave">({m.tier}º patamar)</span>
            </p>
            <DetalheAvanco id={id} ficha={ficha} proximo={proximo} marcado={m}
              detalhe={detalhes[m.chave] ?? DETALHE_VAZIO}
              outrosTracos={marcados.filter((x) => x.chave !== m.chave && x.opcao === 'TRACOS')
                .flatMap((x) => detalhes[x.chave]?.tracos ?? [])}
              experiencias={experienciasDisponiveis}
              mudar={(p) => mudarDetalhe(m.chave, p)} />
          </div>
        ))}
      </Secao>

      {nTreinos > 0 && ficha.companheiro && (
        <Secao titulo={`Treinos de ${ficha.companheiro.nome} (${nTreinos})`}>
          {treinos.map((t, i) => (
            <div key={i} className="grid gap-2">
              <select value={t.opcao} aria-label={`Treino ${i + 1}`}
                onChange={(e) => setTreinos(treinos.map((x, j) => j === i ? { opcao: e.target.value as OpcaoTreino } : x))}
                className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
                {(Object.keys(NOME_TREINO) as OpcaoTreino[]).map((o) => <option key={o} value={o}>{NOME_TREINO[o]}</option>)}
              </select>
              {t.opcao === 'INTELIGENTE' && (
                <select value={t.experiencia ?? ''} aria-label="Experiência do companheiro"
                  onChange={(e) => setTreinos(treinos.map((x, j) => j === i ? { ...x, experiencia: e.target.value } : x))}
                  className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
                  <option value="">Qual Experiência?</option>
                  {[...Object.keys(ficha.companheiro!.experiencias), ...(expCompanheiro.trim() ? [expCompanheiro.trim()] : [])]
                    .map((e) => <option key={e} value={e}>{e}</option>)}
                </select>
              )}
              {t.opcao === 'FEROZ' && (
                <select value={t.alvo ?? ''} aria-label="O que melhorar"
                  onChange={(e) => setTreinos(treinos.map((x, j) => j === i ? { ...x, alvo: e.target.value as AlvoFeroz } : x))}
                  className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
                  <option value="">Melhorar o quê?</option>
                  {(['DANO', 'ALCANCE'] as const).map((a) => <option key={a} value={a}>{NOME_ALVO_FEROZ[a]}</option>)}
                </select>
              )}
            </div>
          ))}
        </Secao>
      )}

      <Secao titulo="Carta do nível">
        {avancosOk ? (
          <EscolhaDeCarta id={id} ficha={ficha} escolhas={escolhas} carta={carta} setCarta={setCarta}
            troca={troca} setTroca={setTroca} />
        ) : (
          <p className="text-sm text-texto-suave">Complete os avanços para ver as cartas (uma multiclasse muda as opções).</p>
        )}
      </Secao>

      <div className="space-y-2 border-t border-borda pt-4">
        <p className="text-sm text-texto-suave">Os limiares de dano sobem +1 automaticamente.</p>
        <Aviso erro={subir.error} />
        <Botao onClick={confirmar} disabled={!pronto || subir.isPending} className="w-full">
          {subir.isPending ? 'Subindo de nível…' : `Confirmar nível ${proximo.nivel}`}
        </Botao>
      </div>
    </div>
  )
}

type PropsDetalhe = {
  id: string
  ficha: Ficha
  proximo: ProximoNivel
  marcado: AvancoMarcado
  detalhe: Detalhe
  outrosTracos: Traco[]
  experiencias: string[]
  mudar: (p: Partial<Detalhe>) => void
}

function alternar<T>(lista: T[], item: T, maximo: number): T[] {
  if (lista.includes(item)) return lista.filter((x) => x !== item)
  return lista.length < maximo ? [...lista, item] : lista
}

function DetalheAvanco({ id, ficha, proximo, marcado, detalhe, outrosTracos, experiencias, mudar }: PropsDetalhe) {
  switch (marcado.opcao) {
    case 'TRACOS':
      return (
        <div className="grid grid-cols-2 gap-2">
          {TRACOS.map((t) => {
            const bloqueado = proximo.tracos_marcados.includes(t) || outrosTracos.includes(t)
            return (
              <label key={t} className={`flex items-center gap-2 text-sm ${bloqueado ? 'opacity-40' : ''}`}>
                <input type="checkbox" disabled={bloqueado} checked={detalhe.tracos.includes(t)}
                  onChange={() => mudar({ tracos: alternar(detalhe.tracos, t, 2) })} />
                {NOME_TRACO[t]} {bloqueado && <span className="text-xs text-texto-suave">(marcado)</span>}
              </label>
            )
          })}
        </div>
      )
    case 'EXPERIENCIAS':
      return (
        <div className="space-y-1">
          {experiencias.map((e) => (
            <label key={e} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={detalhe.experiencias.includes(e)}
                onChange={() => mudar({ experiencias: alternar(detalhe.experiencias, e, 2) })} />{e}
            </label>
          ))}
        </div>
      )
    case 'CARTA_DOMINIO':
      return <CartaDoAvanco id={id} tier={marcado.tier} carta={detalhe.carta} mudar={(carta) => mudar({ carta })} />
    case 'MULTICLASSE':
      return <Multiclasse ficha={ficha} detalhe={detalhe} mudar={mudar} />
    default:
      return null
  }
}

function CartaDoAvanco({ id, tier, carta, mudar }: { id: string; tier: number; carta?: string; mudar: (c: string) => void }) {
  const opcoes = useOpcoesDeCarta(id, { para: 'avanco', tier })
  const dominio = useNomeDominio()
  if (opcoes.isPending) return <Carregando />
  return (
    <select value={carta ?? ''} onChange={(e) => mudar(e.target.value)} aria-label="Carta do avanço"
      className="w-full rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
      <option value="">Escolha uma carta</option>
      {opcoes.data?.map((c) => <option key={c.id} value={c.id}>{c.nome} ({dominio(c.dominio)}, nível {c.nivel})</option>)}
    </select>
  )
}

function Multiclasse({ ficha, detalhe, mudar }: { ficha: Ficha; detalhe: Detalhe; mudar: (p: Partial<Detalhe>) => void }) {
  const classes = useClasses()
  const subclasses = useSubclasses(detalhe.classe)
  const classe = classes.data?.find((c) => c.id === detalhe.classe)
  const dominio = useNomeDominio()
  const seletor = 'w-full rounded-lg border border-borda bg-fundo px-3 py-2 text-sm'
  return (
    <div className="space-y-2">
      <select value={detalhe.classe ?? ''} aria-label="Classe" className={seletor}
        onChange={(e) => mudar({ classe: e.target.value, dominio: undefined, subclasse: undefined })}>
        <option value="">Classe</option>
        {classes.data?.filter((c) => c.id !== ficha.classe)
          .map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
      </select>
      {classe && (
        <>
          <select value={detalhe.dominio ?? ''} aria-label="Domínio" className={seletor}
            onChange={(e) => mudar({ dominio: e.target.value })}>
            <option value="">Domínio</option>
            {classe.dominios.map((d) => <option key={d} value={d}>{dominio(d)}</option>)}
          </select>
          <select value={detalhe.subclasse ?? ''} aria-label="Subclasse" className={seletor}
            onChange={(e) => mudar({ subclasse: e.target.value })}>
            <option value="">Subclasse</option>
            {subclasses.data?.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
          </select>
        </>
      )}
      {detalhe.subclasse === BEASTBOUND && (
        <div className="grid gap-2">
          <Campo rotulo="Companheiro" value={detalhe.companheiro.nome}
            onChange={(e) => mudar({ companheiro: { ...detalhe.companheiro, nome: e.target.value } })} />
          {[0, 1].map((i) => (
            <Campo key={i} rotulo={`Experiência ${i + 1}`} value={detalhe.companheiro.experiencias[i]}
              onChange={(e) => {
                const exps = [...detalhe.companheiro.experiencias] as [string, string]
                exps[i] = e.target.value
                mudar({ companheiro: { ...detalhe.companheiro, experiencias: exps } })
              }} />
          ))}
        </div>
      )}
    </div>
  )
}

type PropsCarta = {
  id: string
  ficha: Ficha
  escolhas: Escolha[]
  carta?: string
  setCarta: (c: string) => void
  troca: { antiga?: string; nova?: string } | null
  setTroca: (t: { antiga?: string; nova?: string } | null) => void
}

function EscolhaDeCarta({ id, ficha, escolhas, carta, setCarta, troca, setTroca }: PropsCarta) {
  const opcoes = useOpcoesDeCarta(id, { para: 'nivel', escolhas })
  const opcoesTroca = useOpcoesDeCarta(id, troca?.antiga
    ? { para: 'troca', antiga: troca.antiga, escolhas, carta_do_nivel: carta ?? null } : null)
  const nomes = useNomes(ficha)
  const dominio = useNomeDominio()

  return (
    <div className="space-y-3">
      <Aviso erro={opcoes.error} />
      {opcoes.isPending ? <Carregando /> : (
        <ul className="max-h-96 space-y-1.5 overflow-y-auto pr-1">
          {opcoes.data?.map((c) => (
            <li key={c.id}>
              <Escolhivel selecionado={carta === c.id} onClick={() => setCarta(c.id)}>
                <p className="flex items-center justify-between gap-2">
                  <span className="font-titulo">{c.nome}<Original nome={c.nome} original={c.nome_original} /></span>
                  <Selo>{dominio(c.dominio)} · nível {c.nivel}</Selo>
                </p>
                <p className="mt-1 line-clamp-3 whitespace-pre-line text-xs text-texto-suave">{c.texto}</p>
              </Escolhivel>
            </li>
          ))}
        </ul>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={troca !== null} onChange={(e) => setTroca(e.target.checked ? {} : null)} />
        Trocar uma carta que já tenho por outra de nível igual ou menor
      </label>
      {troca && (
        <div className="grid gap-2">
          <select value={troca.antiga ?? ''} aria-label="Carta que sai"
            onChange={(e) => setTroca({ antiga: e.target.value })}
            className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
            <option value="">Carta que sai</option>
            {ficha.cartas.map((cid) => <option key={cid} value={cid}>{nomes.carta(cid)?.nome ?? cid}</option>)}
          </select>
          <select value={troca.nova ?? ''} aria-label="Carta que entra" disabled={!troca.antiga}
            onChange={(e) => setTroca({ ...troca, nova: e.target.value })}
            className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
            <option value="">Carta que entra</option>
            {opcoesTroca.data?.map((c) => <option key={c.id} value={c.id}>{c.nome} (nível {c.nivel})</option>)}
          </select>
        </div>
      )}
    </div>
  )
}
