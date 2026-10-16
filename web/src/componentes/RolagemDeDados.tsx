// Rolagem de dados da sessão. Quem joga escolhe o tipo (teste, ataque,
// conjuração, reação, dano ou livre); o servidor rola com as regras e os
// efeitos do personagem (os automáticos aparecem marcados; as opções, com custo,
// para escolher) e guarda no registro, que todos veem ao vivo. O mestre rola
// livre (e pode rolar oculto). Reações (rerrolar, trocar os dados...) aparecem
// em cada rolagem para quem pode usá-las.
import { lazy, Suspense, useState } from 'react'

import { useCartas, useFicha, useOpcoesDeRolagem, usePadroesEstranhos, useRolagens, useRolar } from '../api/consultas'
import type { DadoRolado, Ficha, OpcaoDeRolagem, OpcaoEscolhida, PedidoDeRolagem, Rolagem, Traco } from '../api/tipos'
import { type CoresDosDados, type GrupoDeDados, useCoresDosDados } from '../lib/coresDosDados'
import { NOME_TRACO, TRACOS } from '../lib/rotulos'
import { Abas, Aviso, Botao, Campo, Cartao, Selecao, Selo } from './ui'

// three.js é pesado: só carrega quando a aba de dados abre
const Dados3D = lazy(() => import('./Dados3D'))

type Tipo = 'atributo' | 'ataque' | 'conjuracao' | 'reacao' | 'dano' | 'livre'
const NOME_TIPO: Record<Tipo, string> = {
  atributo: 'Teste', ataque: 'Ataque', conjuracao: 'Conjuração', reacao: 'Reação', dano: 'Dano', livre: 'Livre',
}
const NOME_DUALIDADE: Record<string, string> = { esperanca: 'com Esperança', medo: 'com Medo', critico: 'Crítico!' }
const LIMITE: Record<string, string> = { sessao: '1x por sessão', descanso: '1x por descanso', descanso_longo: '1x por descanso longo' }

function custo(o: OpcaoDeRolagem): string {
  const partes = []
  if (o.custo_esperanca) partes.push(`${o.custo_esperanca} Esperança`)
  if (o.custo_fadiga) partes.push(`${o.custo_fadiga} PF`)
  return partes.join(' + ') + (partes.length && o.por_unidade ? ' cada' : '')
}

/** Cor de cada dado no registro e na mesa 3D. */
function corDoDado(d: DadoRolado, cores: CoresDosDados) {
  return d.papel === 'esperanca' ? cores.esperanca : d.papel === 'medo' ? cores.medo : cores.outros
}

export function gruposDaRolagem(r: Rolagem, cores: CoresDosDados): GrupoDeDados[] {
  const dados = r.resultado.dados.filter((d) => !d.descartado)
  const de = (papeis: string[]) => dados.filter((d) => papeis.includes(d.papel ?? 'comum'))
  return [
    { cor: cores.esperanca, dados: de(['esperanca']) },
    { cor: cores.medo, dados: de(['medo']) },
    { cor: cores.outros, dados: de(['vantagem', 'desvantagem', 'comum', 'extra']).map((d) => ({ ...d, valor: Math.abs(d.valor) })) },
  ].filter((g) => g.dados.length > 0)
}

function Dado({ d, cores }: { d: DadoRolado; cores: CoresDosDados }) {
  const cor = corDoDado(d, cores)
  const rotulo = d.papel === 'esperanca' ? 'Esperança' : d.papel === 'medo' ? 'Medo'
    : d.papel === 'vantagem' ? 'vantagem' : d.papel === 'desvantagem' ? 'desvantagem' : d.fonte || ''
  return (
    <span title={`d${d.faces}${rotulo ? ` · ${rotulo}` : ''}${d.original !== null && d.original !== undefined ? ` (era ${d.original})` : ''}`}
      className={`inline-flex min-w-9 flex-col items-center rounded-lg border px-1.5 py-0.5 text-xs ${d.descartado ? 'opacity-40 line-through' : ''}`}
      style={{ borderColor: cor }}>
      <b className="text-base leading-tight" style={{ color: cor }}>
        {d.papel === 'desvantagem' ? '−' : ''}{Math.abs(d.valor)}
      </b>
      <span className="text-[10px] text-texto-suave">d{d.faces}</span>
    </span>
  )
}

function Registro({ r, cores, personagemId, mesaId, sessaoId }: {
  r: Rolagem; cores: CoresDosDados; personagemId?: string | null; mesaId: string; sessaoId: string
}) {
  const rolar = useRolar(mesaId, sessaoId)
  const [escolha, setEscolha] = useState<Record<string, string>>({})
  const res = r.resultado
  const dual = res.dualidade
  return (
    <li className={`space-y-2 rounded-xl border border-borda bg-fundo/60 p-3 text-sm ${r.substituida ? 'opacity-50' : ''}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p><b>{r.personagem ?? r.autor}</b> <span className="text-texto-suave">· {res.titulo}</span>
          {r.oculta && <span className="ml-2"><Selo>oculta</Selo></span>}
          {res.reacao_de && <span className="ml-2"><Selo destaque>{res.reacao_de}</Selo></span>}
          {r.substituida && <span className="ml-2 text-xs text-texto-suave">(refeita)</span>}</p>
        <p className="flex items-center gap-2">
          {dual && <Selo destaque={dual !== 'medo'}>{NOME_DUALIDADE[dual]}</Selo>}
          <span className="font-titulo text-2xl text-esperanca">{res.total}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {res.dados.map((d, i) => <Dado key={i} d={d} cores={cores} />)}
        {res.bonus.map((b, i) => (
          <span key={`b${i}`} className="text-xs text-texto-suave">{b.valor >= 0 ? '+' : '−'}{Math.abs(b.valor)} {b.fonte}</span>
        ))}
      </div>
      {res.dificuldade !== null && res.dificuldade !== undefined && (
        <p className={`text-xs font-semibold ${res.sucesso ? 'text-sucesso' : 'text-perigo'}`}>
          Dificuldade {res.dificuldade}: {res.sucesso ? 'sucesso' : 'falha'}
        </p>
      )}
      {(res.opcoes ?? []).length > 0 && <p className="text-xs text-texto-suave">Com: {(res.opcoes ?? []).join(', ')}</p>}
      {(res.efeitos ?? []).length > 0 && (
        <ul className="list-inside list-disc text-xs text-texto-suave">{(res.efeitos ?? []).map((e, i) => <li key={i}>{e}</li>)}</ul>
      )}
      {personagemId && (r.reacoes ?? []).length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-borda pt-2">
          {(r.reacoes ?? []).map((o) => (
            <span key={o.id} className="flex items-center gap-1">
              {(o.escolha ?? []).length > 0 && (
                <select aria-label={`${o.nome}: qual dado`} value={escolha[o.id] ?? ''}
                  onChange={(e) => setEscolha({ ...escolha, [o.id]: e.target.value })}
                  className="rounded-lg border border-borda bg-fundo px-1.5 py-1 text-xs">
                  <option value="">dado…</option>
                  {(o.escolha ?? []).map((x) => <option key={x} value={x}>{x === 'esperanca' ? 'Esperança' : 'Medo'}</option>)}
                </select>
              )}
              <Botao variante="secundario" className="!px-2 !py-1 text-xs"
                disabled={!o.disponivel || rolar.isPending || ((o.escolha ?? []).length > 0 && !escolha[o.id])}
                title={o.disponivel ? o.condicao : o.motivo}
                onClick={() => rolar.mutate({ reacao: { rolagemId: r.id, personagem_id: personagemId, efeito: o.id, escolha: escolha[o.id] } })}>
                {o.nome}{custo(o) && ` (${custo(o)})`}
              </Botao>
            </span>
          ))}
          <Aviso erro={rolar.error} />
        </div>
      )}
    </li>
  )
}

function Opcoes({ opcoes, escolhidas, mudar }: {
  opcoes: OpcaoDeRolagem[]; escolhidas: Record<string, OpcaoEscolhida>; mudar: (e: Record<string, OpcaoEscolhida>) => void
}) {
  const automaticas = opcoes.filter((o) => o.momento === 'automatico')
  const antes = opcoes.filter((o) => o.momento === 'antes')
  if (automaticas.length === 0 && antes.length === 0) return null
  return (
    <div className="space-y-2">
      {automaticas.length > 0 && (
        <p className="flex flex-wrap items-center gap-1.5 text-xs text-texto-suave">
          Aplicado sozinho: {automaticas.map((o) => <Selo key={o.id} destaque>{o.nome}</Selo>)}
        </p>
      )}
      {antes.map((o) => {
        const marcada = !!escolhidas[o.id]
        const alternar = () => {
          const novas = { ...escolhidas }
          if (marcada) delete novas[o.id]
          else novas[o.id] = { id: o.id, quantidade: o.quantidade_max ? 1 : null, escolha: o.escolha?.[0] ?? null }
          mudar(novas)
        }
        return (
          <div key={o.id} className={`rounded-lg border border-borda p-2 text-sm ${o.disponivel ? '' : 'opacity-50'}`}>
            <label className="flex items-start gap-2">
              <input type="checkbox" className="mt-1" checked={marcada} disabled={!o.disponivel} onChange={alternar} />
              <span>
                <b>{o.nome}</b>
                {custo(o) && <span className="ml-1 text-xs text-esperanca">({custo(o)})</span>}
                {o.limite && <span className="ml-1 text-xs text-texto-suave">· {LIMITE[o.limite]}</span>}
                {(o.condicao || o.motivo) && (
                  <span className="block text-xs text-texto-suave">{o.disponivel ? o.condicao : o.motivo}</span>
                )}
              </span>
            </label>
            {marcada && o.quantidade_max && (
              <label className="mt-1 flex items-center gap-2 pl-6 text-xs">
                Quantidade
                <input type="number" min={1} max={o.quantidade_max} value={escolhidas[o.id].quantidade ?? 1}
                  onChange={(e) => mudar({ ...escolhidas, [o.id]: { ...escolhidas[o.id], quantidade: Number(e.target.value) } })}
                  className="w-16 rounded border border-borda bg-fundo px-1.5 py-0.5" />
                <span className="text-texto-suave">(até {o.quantidade_max})</span>
              </label>
            )}
            {marcada && (o.escolha ?? []).length > 0 && (
              <select aria-label={`${o.nome}: em qual dado`} value={escolhidas[o.id].escolha ?? ''}
                onChange={(e) => mudar({ ...escolhidas, [o.id]: { ...escolhidas[o.id], escolha: e.target.value } })}
                className="ml-6 mt-1 rounded border border-borda bg-fundo px-1.5 py-0.5 text-xs">
                {(o.escolha ?? []).map((x) => <option key={x} value={x}>{x === 'esperanca' ? 'Dado de Esperança' : 'Dado de Medo'}</option>)}
              </select>
            )}
          </div>
        )
      })}
    </div>
  )
}

/** Montar a rolagem de um personagem (ou só a livre, para o mestre). */
function Montar({ mesaId, sessaoId, ficha, personagemId, souMestre, aoRolar }: {
  mesaId: string; sessaoId: string; ficha?: Ficha; personagemId?: string | null; souMestre: boolean
  aoRolar: (r: Rolagem) => void
}) {
  const comPersonagem = !!ficha && !!personagemId
  const [tipo, setTipo] = useState<Tipo>(comPersonagem ? 'atributo' : 'livre')
  const [traco, setTraco] = useState<Traco>('AGILITY')
  const [ataque, setAtaque] = useState(0)
  const [conjuracao, setConjuracao] = useState(0)
  const [origemDano, setOrigemDano] = useState('arma:0')
  const [experiencias, setExperiencias] = useState<string[]>([])
  const [vantagem, setVantagem] = useState(false)
  const [desvantagem, setDesvantagem] = useState(false)
  const [dificuldade, setDificuldade] = useState('')
  const [somar, setSomar] = useState('')
  const [extra, setExtra] = useState('')
  const [critico, setCritico] = useState(false)
  const [expressao, setExpressao] = useState('1d20')
  const [oculta, setOculta] = useState(false)
  const [escolhidas, setEscolhidas] = useState<Record<string, OpcaoEscolhida>>({})
  const rolar = useRolar(mesaId, sessaoId)
  const cartas = useCartas()
  const padroes = usePadroesEstranhos(personagemId ?? '')

  const [origem, indice] = origemDano.split(':')
  const cartaDano = origem === 'carta' ? indice : null
  const formula = origem === 'carta' ? Number(origemDano.split(':')[2] ?? 0) : 0
  const tipoDaApi = tipo === 'atributo' ? 'teste' : tipo
  const tracoDaRolagem = tipo === 'atributo' || tipo === 'reacao' ? traco
    : tipo === 'ataque' ? ficha?.ataques[ataque]?.traco : tipo === 'conjuracao' ? ficha?.conjuracoes[conjuracao]?.traco : null
  const opcoes = useOpcoesDeRolagem(mesaId, sessaoId, comPersonagem && tipo !== 'livre' ? {
    personagemId: personagemId!, tipo: tipoDaApi, traco: tracoDaRolagem ?? null,
    ataque: tipo === 'ataque' ? ataque : tipo === 'dano' && origem === 'arma' ? Number(indice) : null,
    carta: tipo === 'dano' ? cartaDano : null,
  } : null)
  const teste = tipo !== 'dano' && tipo !== 'livre'
  const temPadroes = ficha?.habilidades.some((h) => h.nome_original === 'Strange Patterns')
  const cartasComDano = (ficha?.cartas_ativas ?? []).flatMap((id) => {
    const c = cartas.data?.find((x) => x.id === id)
    return (c?.formulas ?? []).map((f, i) => ({ chave: `carta:${id}:${i}`,
      rotulo: `${c!.nome}: ${f.dados ? f.dados : ficha!.proficiencia}d${f.faces}${f.modificador ? `+${f.modificador}` : ''}` }))
  })

  function enviar() {
    const pedido: PedidoDeRolagem = {
      tipo: tipo === 'reacao' ? 'atributo' : tipo, personagem_id: comPersonagem ? personagemId : null,
      traco: tipo === 'atributo' || tipo === 'reacao' ? traco : null,
      ataque: tipo === 'ataque' ? ataque : tipo === 'dano' && origem === 'arma' ? Number(indice) : null,
      conjuracao, carta: tipo === 'dano' ? cartaDano : null, formula,
      experiencias: teste ? experiencias : [], vantagem: teste && vantagem, desvantagem: teste && desvantagem,
      dificuldade: teste && dificuldade ? Number(dificuldade) : null, reacao: tipo === 'reacao',
      critico: tipo === 'dano' && critico, extra: tipo === 'dano' ? extra : '', somar: teste ? somar : '',
      expressao: tipo === 'livre' ? expressao : '', opcoes: Object.values(escolhidas), oculta: souMestre && oculta,
    }
    rolar.mutate({ pedido }, { onSuccess: (r) => { setEscolhidas({}); aoRolar(r) } })
  }

  const tipos: Tipo[] = comPersonagem
    ? ['atributo', 'reacao', ...(ficha!.ataques.length ? ['ataque' as Tipo] : []),
      ...(ficha!.conjuracoes.length ? ['conjuracao' as Tipo] : []), 'dano', 'livre']
    : ['livre']

  return (
    <Cartao titulo="Rolar">
      <div className="space-y-3">
        {tipos.length > 1 && (
          <Abas<Tipo> atual={tipo} aoTrocar={(t) => { setTipo(t); setEscolhidas({}) }}
            abas={tipos.map((t): [Tipo, string] => [t, NOME_TIPO[t]])} />
        )}
        {(tipo === 'atributo' || tipo === 'reacao') && (
          <Selecao rotulo="Atributo" value={traco} onChange={(e) => { setTraco(e.target.value as Traco); setEscolhidas({}) }}
            opcoes={TRACOS.map((t): [string, string] => [t, `${NOME_TRACO[t]} (${(ficha?.tracos[t] ?? 0) >= 0 ? '+' : ''}${ficha?.tracos[t] ?? 0})`])} />
        )}
        {tipo === 'ataque' && (
          <Selecao rotulo="Arma" value={String(ataque)} onChange={(e) => { setAtaque(Number(e.target.value)); setEscolhidas({}) }}
            opcoes={ficha!.ataques.map((a, i): [string, string] => [String(i), `${a.arma} (${a.bonus >= 0 ? '+' : ''}${a.bonus})`])} />
        )}
        {tipo === 'conjuracao' && ficha!.conjuracoes.length > 1 && (
          <Selecao rotulo="Atributo de conjuração" value={String(conjuracao)} onChange={(e) => setConjuracao(Number(e.target.value))}
            opcoes={ficha!.conjuracoes.map((c, i): [string, string] => [String(i), `${c.subclasse} (${NOME_TRACO[c.traco]})`])} />
        )}
        {tipo === 'dano' && (
          <>
            <Selecao rotulo="Dano de" value={origemDano} onChange={(e) => { setOrigemDano(e.target.value); setEscolhidas({}) }}
              opcoes={[...ficha!.ataques.map((a, i): [string, string] => [`arma:${i}`, `${a.arma} (${a.dano})`]),
                ...cartasComDano.map((c): [string, string] => [c.chave, c.rotulo])]} />
            <div className="grid grid-cols-2 gap-2">
              <Campo rotulo="Somar (ex.: 1d6+2)" value={extra} maxLength={60} onChange={(e) => setExtra(e.target.value)} />
              <label className="mt-6 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={critico} onChange={(e) => setCritico(e.target.checked)} /> Crítico
              </label>
            </div>
          </>
        )}
        {teste && (
          <>
            {Object.keys(ficha?.experiencias ?? {}).length > 0 && (
              <fieldset className="space-y-1">
                <legend className="text-sm">Experiências (1 de Esperança cada)</legend>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {Object.entries(ficha!.experiencias).map(([nome, v]) => (
                    <label key={nome} className="flex items-center gap-1.5 text-sm">
                      <input type="checkbox" checked={experiencias.includes(nome)}
                        onChange={() => setExperiencias(experiencias.includes(nome)
                          ? experiencias.filter((x) => x !== nome) : [...experiencias, nome])} />
                      {nome} (+{v})
                    </label>
                  ))}
                </div>
              </fieldset>
            )}
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex items-center gap-1.5 text-sm">
                <input type="checkbox" checked={vantagem} onChange={(e) => setVantagem(e.target.checked)} /> Vantagem (+d6)
              </label>
              <label className="flex items-center gap-1.5 text-sm">
                <input type="checkbox" checked={desvantagem} onChange={(e) => setDesvantagem(e.target.checked)} /> Desvantagem (−d6)
              </label>
              <Campo rotulo="Dificuldade" type="number" min={1} max={60} className="w-24" value={dificuldade}
                onChange={(e) => setDificuldade(e.target.value)} />
              <Campo rotulo="Somar dado (Inspiração, Oração…)" className="w-40" value={somar} maxLength={60}
                onChange={(e) => setSomar(e.target.value)} placeholder="ex.: 1d8" />
            </div>
            {temPadroes && (
              <Selecao rotulo="Padrões Estranhos: número" value={String(ficha!.padroes_estranhos ?? '')}
                disabled={padroes.isPending} onChange={(e) => padroes.mutate(e.target.value ? Number(e.target.value) : null)}
                opcoes={[['', 'Escolha…'], ...Array.from({ length: 12 }, (_, i): [string, string] => [String(i + 1), String(i + 1)])]} />
            )}
          </>
        )}
        {tipo === 'livre' && (
          <div className="flex flex-wrap items-end gap-3">
            <Campo rotulo="Rolagem" value={expressao} maxLength={80} onChange={(e) => setExpressao(e.target.value)}
              placeholder="ex.: 2d8+1d6+3" />
            {souMestre && (
              <label className="mb-2 flex items-center gap-1.5 text-sm">
                <input type="checkbox" checked={oculta} onChange={(e) => setOculta(e.target.checked)} /> Oculta (só você vê)
              </label>
            )}
          </div>
        )}
        {opcoes.data && <Opcoes opcoes={opcoes.data} escolhidas={escolhidas} mudar={setEscolhidas} />}
        <Aviso erro={rolar.error ?? opcoes.error ?? padroes.error} />
        <Botao className="w-full" disabled={rolar.isPending} onClick={enviar}>
          {rolar.isPending ? 'Rolando…' : 'Rolar'}
        </Botao>
      </div>
    </Cartao>
  )
}

function Cores({ cores, mudar }: { cores: CoresDosDados; mudar: (p: Partial<CoresDosDados>) => void }) {
  const campo = (chave: keyof CoresDosDados, rotulo: string) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="color" value={cores[chave]} onChange={(e) => mudar({ [chave]: e.target.value })}
        className="h-8 w-10 cursor-pointer rounded border border-borda bg-transparent" aria-label={`Cor: ${rotulo}`} />
      {rotulo}
    </label>
  )
  return (
    <details className="rounded-xl border border-borda p-3">
      <summary className="cursor-pointer text-sm text-texto-suave">Cores dos dados</summary>
      <div className="mt-2 flex flex-wrap gap-4">
        {campo('esperanca', 'Esperança')}
        {campo('medo', 'Medo')}
        {campo('outros', 'Outros dados')}
      </div>
    </details>
  )
}

export default function RolagemDeDados({ mesaId, sessaoId, personagemId, souMestre, emAndamento }: {
  mesaId: string; sessaoId: string; personagemId?: string | null; souMestre: boolean; emAndamento: boolean
}) {
  const ficha = useFicha(personagemId ?? '', !!personagemId)
  const registro = useRolagens(mesaId, sessaoId, emAndamento ? personagemId : null)
  const [cores, mudarCores] = useCoresDosDados()
  const [ultima, setUltima] = useState<Rolagem | null>(null)
  const comFicha = personagemId ? ficha.data : undefined

  return (
    // grid-cols-1 + min-w-0: no celular a coluna não cresce até a largura das abas
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      <div className="min-w-0 space-y-3">
        {emAndamento && (!personagemId || comFicha) && (
          <Montar mesaId={mesaId} sessaoId={sessaoId} ficha={comFicha} personagemId={personagemId}
            souMestre={souMestre} aoRolar={setUltima} />
        )}
        <Cores cores={cores} mudar={mudarCores} />
      </div>
      <div className="min-w-0 space-y-3">
        <Suspense fallback={<div className="h-56 rounded-2xl border border-borda sm:h-64" />}>
          <Dados3D chave={ultima?.id ?? null} grupos={ultima ? gruposDaRolagem(ultima, cores) : []} />
        </Suspense>
        <section aria-label="Registro de rolagens" className="space-y-2">
          <h3 className="text-sm text-esperanca">Registro da sessão</h3>
          <Aviso erro={registro.error} />
          {registro.data?.length === 0 && <p className="text-sm text-texto-suave">Ninguém rolou ainda.</p>}
          <ul className="space-y-2">
            {registro.data?.map((r) => (
              <Registro key={r.id} r={r} cores={cores} personagemId={emAndamento ? personagemId : null}
                mesaId={mesaId} sessaoId={sessaoId} />
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
