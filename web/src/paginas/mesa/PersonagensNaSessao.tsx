// Personagens que entraram na sessão, do ponto de vista do mestre: lê a
// ficha (ver_fichas), aplica dano (aplicar_dano) e condições
// (aplicar_condicoes) e dá itens e ouro (dar_itens). O resto do personagem
// continua sendo do jogador. As marcas são as desta sessão.
import { useState } from 'react'

import { useAcaoNoPersonagem, useCurarCicatriz, useFichaNaMesa, useJogo, useParticipar } from '../../api/consultas'
import type { Mesa, ResultadoDano, Sessao } from '../../api/tipos'
import Condicoes from '../../componentes/Condicoes'
import { MiniFicha } from '../../componentes/FichaResumida'
import { Foto } from '../../componentes/Foto'
import InventarioNaMesa from '../../componentes/inventario/InventarioNaMesa'
import { Aviso, Botao, Campo, Carregando, Espacos, Esperanca } from '../../componentes/ui'
import { NOME_GRAVIDADE, NOME_IMPACTO } from '../../lib/rotulos'

function descrever(r: ResultadoDano) {
  return `${r.dano} de dano (${NOME_GRAVIDADE[r.gravidade]})${r.usou_armadura ? ', reduzido pela armadura' : ''}: `
    + `${r.pv_marcados} PV marcado${r.pv_marcados === 1 ? '' : 's'}${r.caiu ? '. Caiu: movimento de morte!' : '.'}`
}

function CartaoPersonagem({ mesa, pid, nome, jogador, foto }:
  { mesa: Mesa; pid: string; nome: string; jogador: string; foto?: string | null }) {
  const ficha = useFichaNaMesa(mesa.id, pid)
  const acao = useAcaoNoPersonagem(mesa.id, pid)
  const curar = useCurarCicatriz(mesa.id, pid)
  const [dano, setDano] = useState('')
  const [armadura, setArmadura] = useState(false)
  const pode = (p: string) => (mesa.minhas_permissoes as string[]).includes(p)

  if (ficha.isPending) return <Carregando />
  if (ficha.isError) return <Aviso erro={ficha.error} />
  const f = ficha.data

  return (
    <article aria-label={nome || 'Sem nome'} className="space-y-2 rounded-2xl border border-borda bg-superficie p-4">
      <header className="flex items-center gap-3">
        <Foto id={foto} nome={nome || '?'} tamanho="p" />
        <div>
        <h3 className="font-titulo text-base">{nome || 'Sem nome'}</h3>
          <p className="text-xs text-texto-suave">{jogador} · Evasão {f.evasao} · Limiares {f.limiar_maior}/{f.limiar_grave}</p>
        </div>
      </header>
      <p className="text-xs text-texto-suave">PV restantes: {f.pv_max - f.pv_marcados}/{f.pv_max}</p>
      <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo={`PV de ${nome}`} restantes />
      <p className="text-xs text-texto-suave">PF restantes: {f.estresse_max - f.estresse_marcado}/{f.estresse_max}</p>
      <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo={`PF de ${nome}`} cor="medo" restantes />
      {f.pontuacao_armadura > 0 && <>
        <p className="text-xs text-texto-suave">Armadura livre: {f.pontuacao_armadura - f.armadura_marcada}/{f.pontuacao_armadura}</p>
        <Espacos total={f.pontuacao_armadura} marcados={f.armadura_marcada} rotulo={`Armadura de ${nome}`} cor="medo" restantes />
      </>}
      <Esperanca atual={f.esperanca} maximo={f.esperanca_max} />
      {f.morto && <p className="text-sm font-medium text-perigo">Atravessou o véu da morte.</p>}
      {!f.morto && f.inconsciente && <p className="text-sm font-medium text-perigo">Inconsciente (volta a si com 1 PV limpo ou no descanso longo).</p>}
      {!f.morto && f.precisa_movimento_de_morte && <p className="text-sm font-medium text-perigo">Marcou o último PV: o jogador escolhe o movimento de morte.</p>}
      {(f.cicatrizes ?? []).length > 0 && (
        <ul className="space-y-1 text-xs">
          {(f.cicatrizes ?? []).map((c, i) => (
            <li key={i} className="flex items-center justify-between gap-2">
              <span>Cicatriz: {NOME_IMPACTO[c.impacto ?? '']}{c.descricao ? ` (${c.descricao})` : ''}</span>
              {pode('aplicar_condicoes') && (
                <Botao variante="fantasma" disabled={curar.isPending}
                  onClick={() => confirm('Curar esta cicatriz? O espaço de Esperança volta.') && curar.mutate(i)}>Curar</Botao>
              )}
            </li>
          ))}
        </ul>
      )}

      {pode('aplicar_dano') && (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
          e.preventDefault()
          acao.mutate({ tipo: 'dano', dano: Number(dano), usar_armadura: armadura }, { onSuccess: () => setDano('') })
        }}>
          <Campo rotulo="Dano" type="number" min={0} className="w-24" value={dano}
            onChange={(e) => setDano(e.target.value)} aria-label={`Dano em ${nome}`} />
          <label className="mb-2 flex items-center gap-1.5 text-xs">
            <input type="checkbox" checked={armadura} onChange={(e) => setArmadura(e.target.checked)} />
            Jogador usa armadura
          </label>
          <Botao type="submit" variante="secundario" className="mb-0.5" disabled={acao.isPending || dano === ''}>Aplicar dano</Botao>
        </form>
      )}
      {acao.data?.resultado && <p className="text-sm text-esperanca" aria-live="polite">{descrever(acao.data.resultado)}</p>}

      <Condicoes rotulo={nome} condicoes={f.condicoes} desabilitado={acao.isPending}
        aoAplicar={pode('aplicar_condicoes') ? (condicao) => acao.mutate({ tipo: 'condicao', condicao }) : undefined}
        aoTirar={pode('aplicar_condicoes') ? (condicao) => acao.mutate({ tipo: 'tirar_condicao', condicao }) : undefined} />
      <Aviso erro={acao.error} />
      <InventarioNaMesa mesaId={mesa.id} pid={pid} nome={nome} podeDar={pode('dar_itens')} />
    </article>
  )
}

export default function PersonagensNaSessao({ mesa, sessao }: { mesa: Mesa; sessao: Sessao }) {
  const podeVer = (mesa.minhas_permissoes as string[]).includes('ver_fichas')
  const jogo = useJogo(mesa.id, sessao.id)
  const tirar = useParticipar(mesa.id, sessao.id)
  const participantes = jogo.data?.participantes ?? []
  const emJogo = sessao.status === 'em_andamento'
  return (
    <section className="space-y-3">
      <h2 className="text-lg text-esperanca">Personagens na sessão</h2>
      {jogo.isPending && <Carregando />}
      {!jogo.isPending && participantes.length === 0 && (
        <p className="text-sm text-texto-suave">
          {emJogo ? 'Ninguém entrou ainda: os jogadores entram pela aba Sessões.'
            : 'Os jogadores entram quando a sessão estiver em andamento.'}
        </p>
      )}
      {!podeVer && participantes.length > 0 && (
        <p className="text-sm text-texto-suave">Quem criou a mesa não liberou ver as fichas para os mestres.</p>
      )}
      {podeVer && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {participantes.map((p) => (
            <div key={p.personagem_id} className="space-y-1">
              {emJogo ? (
                <CartaoPersonagem mesa={mesa} pid={p.personagem_id} nome={p.resumo.nome} jogador={p.resumo.jogador}
                  foto={p.resumo.foto} />
              ) : <MiniFicha f={p.resumo} />}
              {emJogo && sessao.sou_responsavel && (
                <Botao variante="fantasma" disabled={tirar.isPending}
                  onClick={() => confirm(`Tirar ${p.resumo.nome || 'o personagem'} da sessão? As marcas dele nesta sessão se perdem.`)
                    && tirar.mutate({ personagemId: p.personagem_id, sair: true })}>
                  Tirar da sessão
                </Botao>
              )}
            </div>
          ))}
        </div>
      )}
      <Aviso erro={jogo.error ?? tirar.error} />
    </section>
  )
}
