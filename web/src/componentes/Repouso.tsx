// Repouso do grupo: o mestre responsável abre um descanso curto ou longo, cada
// jogador escolhe os dois movimentos do seu personagem (alguns podem ser num
// aliado) e o mestre encerra; aí tudo é aplicado de uma vez e o mestre ganha
// Medo. As regras (e o que vale ou não) são do motor; aqui a tela só guia.
import { useState } from 'react'

import { useAcaoNoRepouso, useRepouso } from '../api/consultas'
import type { EscolhaDeRepouso, Mesa, MovimentoDeDescanso, Participante, Repouso, Sessao } from '../api/tipos'
import { useAutenticacao } from '../auth/Autenticacao'
import { efeitoDoMovimento, nomeDoMovimento } from '../lib/rotulos'
import { Aviso, Botao, Cartao, Selo } from './ui'

const MOVIMENTOS: MovimentoDeDescanso[] = [
  'CUIDAR_FERIDAS', 'ALIVIAR_ESTRESSE', 'REPARAR_ARMADURA', 'PREPARAR', 'PREPARAR_EM_GRUPO', 'PROJETO',
]
const EM_ALIADO: MovimentoDeDescanso[] = ['CUIDAR_FERIDAS', 'REPARAR_ARMADURA']
const RECUPERA: MovimentoDeDescanso[] = ['CUIDAR_FERIDAS', 'ALIVIAR_ESTRESSE', 'REPARAR_ARMADURA']

type Linha = { movimento: MovimentoDeDescanso; alvo: string; rolagem: string }

function resumo(e: EscolhaDeRepouso, longo: boolean, nomes: Record<string, string>) {
  return e.movimentos.map((m) => nomeDoMovimento(m.movimento, longo)
    + (m.alvo && nomes[m.alvo] ? ` em ${nomes[m.alvo]}` : '')).join(' · ')
}

function Escolher({ mesa, repouso, p, aoTerminar }: {
  mesa: Mesa; repouso: Repouso; p: Participante; aoTerminar: () => void
}) {
  const acao = useAcaoNoRepouso(mesa.id)
  const longo = repouso.tipo === 'longo'
  const inicial = (p.escolha?.movimentos ?? []).map((m) => ({
    movimento: m.movimento, alvo: m.alvo ?? '', rolagem: m.rolagem ? String(m.rolagem) : '' }))
  const [linhas, setLinhas] = useState<Linha[]>(inicial.length === 2 ? inicial : [
    { movimento: 'CUIDAR_FERIDAS', alvo: '', rolagem: '' }, { movimento: 'PREPARAR', alvo: '', rolagem: '' }])
  const aliados = repouso.participantes.filter((x) => x.id !== p.id)
  const opcoes = MOVIMENTOS.filter((m) => longo || m !== 'PROJETO')
  const mudar = (i: number, parcial: Partial<Linha>) => setLinhas(linhas.map((l, j) => (j === i ? { ...l, ...parcial } : l)))

  return (
    <form className="space-y-2" onSubmit={(e) => {
      e.preventDefault()
      acao.mutate({ tipo: 'escolher', repousoId: repouso.id, personagemId: p.id, escolha: {
        movimentos: linhas.map((l) => ({
          movimento: l.movimento, alvo: EM_ALIADO.includes(l.movimento) && l.alvo ? l.alvo : null,
          rolagem: !longo && RECUPERA.includes(l.movimento) && l.rolagem ? Number(l.rolagem) : null,
        })),
      } }, { onSuccess: aoTerminar })
    }}>
      {linhas.map((l, i) => (
        <fieldset key={i} className="space-y-1 rounded-lg border border-borda p-2">
          <legend className="px-1 text-xs text-texto-suave">Movimento {i + 1}</legend>
          <div className="flex flex-wrap items-end gap-2">
            <select aria-label={`Movimento ${i + 1}`} value={l.movimento}
              onChange={(e) => mudar(i, { movimento: e.target.value as MovimentoDeDescanso })}
              className="w-full rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm sm:w-auto sm:min-w-0 sm:flex-1">
              {opcoes.map((m) => <option key={m} value={m}>{nomeDoMovimento(m, longo)}</option>)}
            </select>
            {EM_ALIADO.includes(l.movimento) && aliados.length > 0 && (
              <select aria-label={`Em quem (movimento ${i + 1})`} value={l.alvo} onChange={(e) => mudar(i, { alvo: e.target.value })}
                className="rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm">
                <option value="">Em si</option>
                {aliados.map((a) => <option key={a.id} value={a.id}>Em {a.nome}</option>)}
              </select>
            )}
            {!longo && RECUPERA.includes(l.movimento) && (
              <input type="number" min={1} max={4} value={l.rolagem} placeholder="d4"
                aria-label={`d4 do movimento ${i + 1} (vazio: o app rola)`} onChange={(e) => mudar(i, { rolagem: e.target.value })}
                className="w-16 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
            )}
          </div>
          <p className="text-xs text-texto-suave">{efeitoDoMovimento(l.movimento, longo)}</p>
        </fieldset>
      ))}
      {!longo && <p className="text-xs text-texto-suave">d4 vazio: o app rola quando o mestre encerrar.</p>}
      <Aviso erro={acao.error} />
      <Botao type="submit" disabled={acao.isPending}>Confirmar movimentos</Botao>
    </form>
  )
}

function Resultado({ repouso }: { repouso: Repouso }) {
  const r = repouso.resultado
  if (!r) return null
  const longo = r.tipo === 'longo'
  const nomes = Object.fromEntries(repouso.participantes.map((p) => [p.id, p.nome]))
  return (
    <div className="space-y-2 text-sm">
      {(r.notas ?? []).map((n) => <p key={n} className="text-texto-suave">{n}</p>)}
      <ul className="space-y-1">
        {Object.entries(r.por_personagem ?? {}).map(([pid, movimentos]) => (
          <li key={pid}>
            <b>{nomes[pid] ?? 'Personagem'}</b>:{' '}
            {movimentos.map((m) => {
              const nome = m.fonte ?? nomeDoMovimento(m.movimento, longo)
              const em = m.alvo ? ` em ${m.alvo}` : ''
              const quanto = m.movimento.startsWith('PREPARAR') ? `+${m.recuperado} Esperança`
                : m.movimento === 'PROJETO' ? 'projeto' : `${m.recuperado} limpo${m.recuperado === 1 ? '' : 's'}`
              return `${nome}${em} (${m.rolagem ? `d4 ${m.rolagem}: ` : ''}${quanto})`
            }).join(' · ')}
          </li>
        ))}
      </ul>
      {repouso.medo_ganho !== null && repouso.medo_ganho !== undefined && (
        <p className="text-medo">O mestre ganhou {repouso.medo_ganho} de Medo.</p>
      )}
    </div>
  )
}

/** Painel do repouso. Com `sessao` (a sessão do mestre), mostra também abrir e encerrar. */
export default function PainelDeRepouso({ mesa, sessao }: { mesa: Mesa; sessao?: Sessao }) {
  const repouso = useRepouso(mesa.id)
  const acao = useAcaoNoRepouso(mesa.id)
  const { usuario } = useAutenticacao()
  const [editando, setEditando] = useState<string | null>(null)
  const [d4, setD4] = useState('')
  const [interrompido, setInterrompido] = useState(false)
  const r = repouso.data
  const responsavel = sessao?.sou_responsavel ?? r?.sou_responsavel ?? false
  const aberto = r?.status === 'aberto'

  if (!r || r.status === 'cancelado' || (!aberto && !r.resultado)) {
    if (!sessao?.sou_responsavel) return null
    return (
      <Cartao titulo="Repouso">
        <p className="mb-3 text-sm text-texto-suave">
          Cada jogador escolhe dois movimentos para o seu personagem; ao encerrar, tudo vale de uma vez
          e você ganha Medo (1d4 no curto, 1d4 + o número de personagens no longo).
        </p>
        <div className="flex flex-wrap gap-2">
          <Botao variante="secundario" disabled={acao.isPending}
            onClick={() => acao.mutate({ tipo: 'abrir', sessaoId: sessao.id, repouso: 'curto' })}>Descanso curto</Botao>
          <Botao variante="secundario" disabled={acao.isPending}
            onClick={() => acao.mutate({ tipo: 'abrir', sessaoId: sessao.id, repouso: 'longo' })}>Descanso longo</Botao>
        </div>
        <Aviso erro={acao.error} />
      </Cartao>
    )
  }
  if (sessao && r.sessao_id !== sessao.id) return null   // o repouso é de outra sessão
  const longo = r.tipo === 'longo'
  const nomes = Object.fromEntries(r.participantes.map((p) => [p.id, p.nome]))
  const prontos = r.participantes.filter((p) => p.pronto).length

  return (
    <Cartao titulo={aberto ? `Repouso: descanso ${r.tipo}` : `Repouso encerrado: descanso ${r.resultado?.tipo ?? r.tipo}`}
      className="lg:col-span-2">
      {aberto ? (
        <div className="space-y-3">
          <p className="text-sm text-texto-suave">
            {r.mestre} abriu um descanso {r.tipo}. Escolha dois movimentos (pode repetir) e confirme.
            {' '}{prontos} de {r.participantes.length} pronto{r.participantes.length === 1 ? '' : 's'}.
          </p>
          <ul className="space-y-2">
            {r.participantes.map((p) => {
              const meu = p.dono_id === usuario?.id || responsavel
              return (
                <li key={p.id} className="rounded-xl border border-borda p-3">
                  <p className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{p.nome} <span className="text-xs text-texto-suave">({p.jogador})</span></span>
                    {p.pronto ? <Selo destaque>pronto</Selo> : <Selo>escolhendo…</Selo>}
                  </p>
                  {p.escolha && editando !== p.id && (
                    <p className="mt-1 text-sm text-texto-suave">{resumo(p.escolha, longo, nomes)}</p>
                  )}
                  {meu && (editando === p.id || !p.pronto
                    ? <div className="mt-2"><Escolher mesa={mesa} repouso={r} p={p} aoTerminar={() => setEditando(null)} /></div>
                    : <Botao variante="fantasma" className="mt-1" onClick={() => setEditando(p.id)}>Mudar</Botao>)}
                </li>
              )
            })}
          </ul>
          {responsavel && (
            <div className="space-y-2 border-t border-borda pt-3">
              <div className="flex flex-wrap items-end gap-2">
                <label className="flex flex-col gap-1 text-xs">
                  <span className="text-texto-suave">d4 do Medo (vazio: o app rola)</span>
                  <input type="number" min={1} max={4} value={d4} onChange={(e) => setD4(e.target.value)}
                    className="w-20 rounded-lg border border-borda bg-fundo px-2 py-1.5 text-sm" />
                </label>
                {longo && (
                  <label className="mb-2 flex items-center gap-1.5 text-xs">
                    <input type="checkbox" checked={interrompido} onChange={(e) => setInterrompido(e.target.checked)} />
                    Foi interrompido (vale como curto)
                  </label>
                )}
                <Botao disabled={acao.isPending || prontos < r.participantes.length}
                  onClick={() => acao.mutate({ tipo: 'encerrar', sessaoId: r.sessao_id, repousoId: r.id, interrompido,
                    rolagem_medo: d4 ? Number(d4) : null })}>
                  Encerrar repouso
                </Botao>
                <Botao variante="fantasma" disabled={acao.isPending}
                  onClick={() => confirm(longo ? 'Cancelar o repouso? Ninguém ganha nada.'
                    : 'Cancelar (ou interrompido)? No descanso curto interrompido, ninguém ganha nada.')
                    && acao.mutate({ tipo: 'cancelar', sessaoId: r.sessao_id, repousoId: r.id })}>
                  Cancelar
                </Botao>
              </div>
              {prontos < r.participantes.length && (
                <p className="text-xs text-texto-suave">Dá para encerrar quando todos estiverem prontos (ou você escolher por eles).</p>
              )}
            </div>
          )}
          <Aviso erro={acao.error} />
        </div>
      ) : <Resultado repouso={r} />}
    </Cartao>
  )
}
