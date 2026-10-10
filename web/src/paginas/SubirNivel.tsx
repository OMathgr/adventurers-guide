// Assistente de subir de nível. As etapas vêm do que a API diz que o
// próximo nível pede (GET /proximo-nivel): conquista de tier, avanços,
// treinos do companheiro, carta do nível. O motor valida tudo no envio.
import { useMemo, useRef, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router'

import {
  useClasses, useFicha, useOpcoesDeCarta, useProximoNivel, useSubclasses, useSubirDeNivel,
} from '../api/consultas'
import type { AlvoFeroz, Escolha, Ficha, OpcaoAvanco, OpcaoTreino, ProximoNivel, Traco, Treino } from '../api/tipos'
import { Aviso, Botao, Campo, Carregando, Cartao, Escolhivel, Etapas, Selo } from '../componentes/ui'
import { useNomes } from '../lib/nomes'
import { type AvancoMarcado, custoTotal, opcoesPorTier, podeMarcar, treinosExigidos } from '../lib/regras'
import {
  dominio, NOME_ALVO_FEROZ, NOME_OPCAO, NOME_TRACO, NOME_TREINO, nomeClasse, TRACOS,
} from '../lib/rotulos'

const BEASTBOUND = 'core_subclass_beastbound'

/** Detalhes que algumas opções pedem (traços, experiências, carta, multiclasse). */
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

function detalheCompleto(opcao: OpcaoAvanco['opcao'], d: Detalhe): boolean {
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

export default function SubirNivel() {
  const { id = '' } = useParams()
  const ficha = useFicha(id)
  const proximo = useProximoNivel(id)

  if (ficha.isPending || proximo.isPending) return <Carregando />
  if (ficha.error || proximo.error) return <Aviso erro={ficha.error ?? proximo.error} />
  if (!proximo.data) return <Navigate to={`/personagens/${id}`} replace />
  return <Assistente id={id} ficha={ficha.data} proximo={proximo.data} />
}

function Assistente({ id, ficha, proximo }: { id: string; ficha: Ficha; proximo: ProximoNivel }) {
  const [etapa, setEtapa] = useState(0)
  const [novaExp, setNovaExp] = useState('')
  const [expCompanheiro, setExpCompanheiro] = useState('')
  const [marcados, setMarcados] = useState<AvancoMarcado[]>([])
  const [detalhes, setDetalhes] = useState<Record<string, Detalhe>>({})
  const [treinosEscolhidos, setTreinos] = useState<Treino[]>([])
  const proximaChave = useRef(0)
  const [carta, setCarta] = useState<string>()
  const [troca, setTroca] = useState<{ antiga?: string; nova?: string } | null>(null)
  const subir = useSubirDeNivel(id)
  const navegar = useNavigate()

  const nTreinos = treinosExigidos(proximo, marcados)
  // a quantidade de treinos depende dos avanços (subclasse dá treino extra)
  const treinos: Treino[] = Array.from({ length: nTreinos },
    (_, i) => treinosEscolhidos[i] ?? { opcao: 'ATENTO' as OpcaoTreino })
  const escolhas = useMemo(
    () => marcados.map((m) => paraEscolha(m, detalhes[m.chave] ?? DETALHE_VAZIO)), [marcados, detalhes])

  const etapas = [
    ...(proximo.nova_experiencia ? ['Conquista'] : []),
    'Avanços',
    ...(nTreinos > 0 ? ['Companheiro'] : []),
    'Carta',
    'Revisão',
  ]
  const nomeEtapa = etapas[etapa]

  const completo: Record<string, boolean> = {
    Conquista: !!novaExp.trim() && (!proximo.experiencia_companheiro || !!expCompanheiro.trim()),
    Avanços: custoTotal(marcados) === proximo.avancos
      && marcados.every((m) => detalheCompleto(m.opcao, detalhes[m.chave] ?? DETALHE_VAZIO)),
    Companheiro: treinos.length === nTreinos && treinos.every((t) =>
      (t.opcao !== 'INTELIGENTE' || !!t.experiencia) && (t.opcao !== 'FEROZ' || !!t.alvo)),
    Carta: !!carta && (troca === null || (!!troca.antiga && !!troca.nova)),
    Revisão: true,
  }

  function marcar(o: OpcaoAvanco) {
    const chave = `${o.tier}-${o.opcao}-${proximaChave.current++}`
    setMarcados((m) => [...m, { ...o, chave }])
    setDetalhes((d) => ({ ...d, [chave]: DETALHE_VAZIO }))
    setCarta(undefined)   // mudar avanços pode mudar as cartas possíveis
    setTroca(null)
  }
  function desmarcar(chave: string) {
    setMarcados((m) => m.filter((x) => x.chave !== chave))
    setCarta(undefined)
    setTroca(null)
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
    }, { onSuccess: () => navegar(`/personagens/${id}?visao=tempo`) })
  }

  const experienciasDisponiveis = [...Object.keys(ficha.experiencias), ...(novaExp.trim() ? [novaExp.trim()] : [])]

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl">{ficha.nome}: nível {proximo.nivel}</h1>
        <p className="text-sm text-texto-suave">Tier {proximo.tier}. Limiares de dano sobem +1 automaticamente.</p>
      </div>
      <Etapas etapas={etapas} atual={etapa} />

      {nomeEtapa === 'Conquista' && (
        <Cartao titulo="Conquista de tier">
          <p className="mb-3 text-sm text-texto-suave">
            Você ganha uma nova Experiência (+2) e +1 de Proficiência
            {proximo.limpa_marcas_tracos && ', e as marcas dos traços são limpas'}.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo rotulo="Nova Experiência" value={novaExp} onChange={(e) => setNovaExp(e.target.value)} />
            {proximo.experiencia_companheiro && (
              <Campo rotulo="Nova Experiência do companheiro" value={expCompanheiro}
                onChange={(e) => setExpCompanheiro(e.target.value)} />
            )}
          </div>
        </Cartao>
      )}

      {nomeEtapa === 'Avanços' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Cartao titulo={`Escolha avanços (${custoTotal(marcados)}/${proximo.avancos})`}>
            <div className="space-y-4">
              {opcoesPorTier(proximo.opcoes).map(([tier, opcoes]) => (
                <div key={tier}>
                  <p className="mb-1 text-xs uppercase tracking-wider text-texto-suave">Tier {tier}</p>
                  <ul className="space-y-1">
                    {opcoes.map((o) => (
                      <li key={o.opcao} className="flex items-center justify-between gap-2 text-sm">
                        <span>{NOME_OPCAO[o.opcao]}{o.custo === 2 && <Selo>vale por 2</Selo>}
                          <span className="ml-1 text-xs text-texto-suave">({o.restantes} restante{o.restantes > 1 && 's'})</span></span>
                        <Botao variante="secundario" className="!px-2 !py-1"
                          disabled={!podeMarcar(o, marcados, proximo.avancos)} onClick={() => marcar(o)}>Marcar</Botao>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Cartao>
          <div className="space-y-3">
            {marcados.length === 0 && <p className="text-sm text-texto-suave">Nenhum avanço marcado ainda.</p>}
            {marcados.map((m) => (
              <Cartao key={m.chave} titulo={NOME_OPCAO[m.opcao]}
                acao={<Botao variante="fantasma" className="!px-2 !py-1" onClick={() => desmarcar(m.chave)}>Remover</Botao>}>
                <DetalheAvanco id={id} ficha={ficha} proximo={proximo} marcado={m}
                  detalhe={detalhes[m.chave] ?? DETALHE_VAZIO}
                  outrosTracos={marcados.filter((x) => x.chave !== m.chave && x.opcao === 'TRACOS')
                    .flatMap((x) => detalhes[x.chave]?.tracos ?? [])}
                  experiencias={experienciasDisponiveis}
                  mudar={(p) => mudarDetalhe(m.chave, p)} />
              </Cartao>
            ))}
          </div>
        </div>
      )}

      {nomeEtapa === 'Companheiro' && ficha.companheiro && (
        <Cartao titulo={`Treinos de ${ficha.companheiro.nome} (${nTreinos})`}>
          <div className="space-y-3">
            {treinos.map((t, i) => (
              <div key={i} className="grid gap-2 sm:grid-cols-2">
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
          </div>
        </Cartao>
      )}

      {nomeEtapa === 'Carta' && (
        <EtapaCarta id={id} ficha={ficha} escolhas={escolhas} carta={carta} setCarta={setCarta}
          troca={troca} setTroca={setTroca} />
      )}

      {nomeEtapa === 'Revisão' && (
        <Revisao ficha={ficha} marcados={marcados} escolhas={escolhas} carta={carta!} troca={troca}
          novaExp={novaExp} treinos={treinos} erro={subir.error} enviando={subir.isPending} confirmar={confirmar} />
      )}

      <div className="flex justify-between pt-2">
        <Botao variante="secundario" onClick={() => setEtapa((e) => e - 1)} disabled={etapa === 0}>Voltar</Botao>
        {etapa < etapas.length - 1 && (
          <Botao onClick={() => setEtapa((e) => e + 1)} disabled={!completo[nomeEtapa]}>Continuar</Botao>
        )}
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
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
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
      return <p className="text-sm text-texto-suave">Nada a escolher.</p>
  }
}

function CartaDoAvanco({ id, tier, carta, mudar }: { id: string; tier: number; carta?: string; mudar: (c: string) => void }) {
  const opcoes = useOpcoesDeCarta(id, { para: 'avanco', tier })
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
  const seletor = 'w-full rounded-lg border border-borda bg-fundo px-3 py-2 text-sm'
  return (
    <div className="space-y-2">
      <select value={detalhe.classe ?? ''} aria-label="Classe" className={seletor}
        onChange={(e) => mudar({ classe: e.target.value, dominio: undefined, subclasse: undefined })}>
        <option value="">Classe</option>
        {classes.data?.filter((c) => c.id !== ficha.classe)
          .map((c) => <option key={c.id} value={c.id}>{nomeClasse(c.nome)}</option>)}
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
        <div className="grid gap-2 sm:grid-cols-3">
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

function EtapaCarta({ id, ficha, escolhas, carta, setCarta, troca, setTroca }: PropsCarta) {
  const opcoes = useOpcoesDeCarta(id, { para: 'nivel', escolhas })
  const opcoesTroca = useOpcoesDeCarta(id, troca?.antiga
    ? { para: 'troca', antiga: troca.antiga, escolhas, carta_do_nivel: carta ?? null } : null)
  const nomes = useNomes(ficha)

  return (
    <div className="space-y-4">
      <Aviso erro={opcoes.error} />
      {opcoes.isPending ? <Carregando /> : (
        <div className="grid gap-3 sm:grid-cols-2">
          {opcoes.data?.map((c) => (
            <Escolhivel key={c.id} selecionado={carta === c.id} onClick={() => setCarta(c.id)}>
              <p className="flex items-center justify-between gap-2">
                <span className="font-titulo">{c.nome}</span><Selo>{dominio(c.dominio)} · nível {c.nivel}</Selo>
              </p>
              <p className="mt-2 line-clamp-4 whitespace-pre-line text-sm text-texto-suave">{c.texto}</p>
            </Escolhivel>
          ))}
        </div>
      )}
      <Cartao titulo="Trocar uma carta antiga (opcional)">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={troca !== null} onChange={(e) => setTroca(e.target.checked ? {} : null)} />
          Trocar uma carta que já tenho por outra de nível igual ou menor
        </label>
        {troca && (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
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
      </Cartao>
    </div>
  )
}

type PropsRevisao = {
  ficha: Ficha
  marcados: AvancoMarcado[]
  escolhas: Escolha[]
  carta: string
  troca: { antiga?: string; nova?: string } | null
  novaExp: string
  treinos: Treino[]
  erro: unknown
  enviando: boolean
  confirmar: () => void
}

function Revisao({ ficha, marcados, escolhas, carta, troca, novaExp, treinos, erro, enviando, confirmar }: PropsRevisao) {
  const nomes = useNomes(ficha)
  const nomeCarta = (id?: string) => (id ? nomes.carta(id)?.nome ?? id : '')
  return (
    <Cartao titulo="Revisão">
      <ul className="space-y-1.5 text-sm">
        {novaExp.trim() && <li>• Nova Experiência: <b>{novaExp.trim()}</b> +2</li>}
        {marcados.map((m, i) => {
          const e = escolhas[i]
          const extra = e.tracos.length ? ` (${e.tracos.map((t) => NOME_TRACO[t]).join(', ')})`
            : e.experiencias.length ? ` (${e.experiencias.join(', ')})`
              : e.carta ? ` (${nomeCarta(e.carta)})` : ''
          return <li key={m.chave}>• {NOME_OPCAO[m.opcao]}{extra} <span className="text-texto-suave">[tier {m.tier}]</span></li>
        })}
        {treinos.map((t, i) => <li key={i}>• Treino: {NOME_TREINO[t.opcao]}</li>)}
        <li>• Limiares de dano +1</li>
        <li>• Carta: <b>{nomeCarta(carta)}</b></li>
        {troca && <li>• Troca: {nomeCarta(troca.antiga)} → {nomeCarta(troca.nova)}</li>}
      </ul>
      <div className="mt-4 space-y-3">
        <Aviso erro={erro} />
        <Botao onClick={confirmar} disabled={enviando} className="w-full">
          {enviando ? 'Subindo de nível…' : 'Confirmar nível'}
        </Botao>
      </div>
    </Cartao>
  )
}
