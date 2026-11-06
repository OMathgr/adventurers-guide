// Personagens que entraram na sessão, do ponto de vista do mestre: lê a
// ficha (ver_fichas), aplica dano (aplicar_dano) e condições
// (aplicar_condicoes) e dá itens e ouro (dar_itens). O resto do personagem
// continua sendo do jogador. As marcas são as desta sessão.
import { type ReactNode, useState } from 'react'

import { useAcaoNoPersonagem, useCurarCicatriz, useFichaNaMesa, useJogo, useParticipar } from '../../api/consultas'
import type { DefesaDeCarta, Mesa, ResultadoDano, Sessao } from '../../api/tipos'
import Condicoes from '../../componentes/Condicoes'
import { MiniFicha } from '../../componentes/FichaResumida'
import { Foto } from '../../componentes/Foto'
import InventarioNaMesa from '../../componentes/inventario/InventarioNaMesa'
import { Aviso, Botao, Campo, Carregando, Espacos, Esperanca } from '../../componentes/ui'
import { NOME_GRAVIDADE, NOME_IMPACTO } from '../../lib/rotulos'
import { useCelular } from '../../lib/useCelular'

// no celular, rótulo e quadradinhos na mesma linha, alinhados entre si
const LINHA_DE_MARCA = 'space-y-2 max-sm:flex max-sm:flex-wrap max-sm:items-center max-sm:gap-x-2 max-sm:space-y-0'
const ROTULO_DE_MARCA = 'text-xs text-texto-suave max-sm:w-28'

function descrever(r: ResultadoDano) {
  return `${r.dano} de dano (${NOME_GRAVIDADE[r.gravidade]})${r.usou_armadura ? ', reduzido pela armadura' : ''}: `
    + `${r.pv_marcados} PV marcado${r.pv_marcados === 1 ? '' : 's'}${r.caiu ? '. Caiu: movimento de morte!' : '.'}`
    + ((r.notas ?? []).length ? ` ${(r.notas ?? []).join('. ')}.` : '')
}

function custo(d: DefesaDeCarta) {
  return [d.custo_fadiga ? `marca ${d.custo_fadiga} PF` : '', d.custo_esperanca ? `gasta ${d.custo_esperanca} de Esperança` : '']
    .filter(Boolean).join(', ')
}

function CartaoPersonagem({ mesa, pid, nome, jogador, foto, compacto, recolher, acaoExtra }: {
  mesa: Mesa; pid: string; nome: string; jogador: string; foto?: string | null; compacto?: boolean
  /** Celular, ao vivo: marcas e condições sempre à vista; as ações, a um toque. */
  recolher?: boolean; acaoExtra?: ReactNode
}) {
  const ficha = useFichaNaMesa(mesa.id, pid)
  const acao = useAcaoNoPersonagem(mesa.id, pid)
  const curar = useCurarCicatriz(mesa.id, pid)
  const [dano, setDano] = useState('')
  const [armadura, setArmadura] = useState(false)
  // cartas de defesa que o jogador decidiu usar neste dano (Get Back Up, Brace...)
  const [cartas, setCartas] = useState<string[]>([])
  const pode = (p: string) => (mesa.minhas_permissoes as string[]).includes(p)

  if (ficha.isPending) return <Carregando />
  if (ficha.isError) return <Aviso erro={ficha.error} />
  const f = ficha.data

  const formularioDeDano = pode('aplicar_dano') && (
    <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
      e.preventDefault()
      acao.mutate({ tipo: 'dano', dano: Number(dano), usar_armadura: armadura, cartas },
        { onSuccess: () => { setDano(''); setCartas([]) } })
    }}>
      <Campo rotulo="Dano" type="number" min={0} className="w-24" value={dano}
        onChange={(e) => setDano(e.target.value)} aria-label={`Dano em ${nome}`} />
      <label className="mb-2 flex items-center gap-1.5 text-xs max-sm:order-last max-sm:mb-0 max-sm:min-h-11 max-sm:w-full">
        <input type="checkbox" checked={armadura} onChange={(e) => setArmadura(e.target.checked)} />
        Jogador usa armadura
      </label>
      <Botao type="submit" variante="secundario" className="mb-0.5" disabled={acao.isPending || dano === ''}>Aplicar dano</Botao>
      {(f.defesas_de_carta ?? []).length > 0 && (
        <fieldset className="w-full space-y-1 text-xs max-sm:order-last">
          <legend className="text-texto-suave">O jogador usa (só paga se precisar):</legend>
          {(f.defesas_de_carta ?? []).map((d) => (
            <label key={d.carta} className="flex items-center gap-1.5 max-sm:min-h-11">
              <input type="checkbox" checked={cartas.includes(d.carta)}
                onChange={() => setCartas(cartas.includes(d.carta) ? cartas.filter((c) => c !== d.carta) : [...cartas, d.carta])} />
              {d.nome} ({custo(d)})
            </label>
          ))}
        </fieldset>
      )}
    </form>
  )
  const aplicar = pode('aplicar_condicoes') ? (condicao: string) => acao.mutate({ tipo: 'condicao', condicao }) : undefined
  const tirar = pode('aplicar_condicoes') ? (condicao: string) => acao.mutate({ tipo: 'tirar_condicao', condicao }) : undefined
  const resultadoDoDano = acao.data?.resultado && <p className="text-sm text-texto" aria-live="polite">{descrever(acao.data.resultado)}</p>
  const itens = <InventarioNaMesa mesaId={mesa.id} pid={pid} nome={nome} podeDar={pode('dar_itens')} />

  return (
    <article aria-label={nome || 'Sem nome'} className="space-y-2 rounded-2xl border border-borda bg-superficie p-4">
      <header className="flex items-center gap-3">
        <Foto id={foto} nome={nome || '?'} tamanho="p" />
        <div>
        <h3 className="font-titulo text-base">{nome || 'Sem nome'}</h3>
          <p className="text-xs text-texto-suave">{jogador} · Evasão {f.evasao} · Limiares {f.limiar_maior}/{f.limiar_grave}</p>
        </div>
      </header>
      <div className={LINHA_DE_MARCA}>
        <p className={ROTULO_DE_MARCA}>PV restantes: {f.pv_max - f.pv_marcados}/{f.pv_max}</p>
        <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo={`PV de ${nome}`} restantes />
      </div>
      <div className={LINHA_DE_MARCA}>
        <p className={ROTULO_DE_MARCA}>PF restantes: {f.estresse_max - f.estresse_marcado}/{f.estresse_max}</p>
        <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo={`PF de ${nome}`} cor="fadiga" restantes />
      </div>
      {f.pontuacao_armadura > 0 && (
        <div className={LINHA_DE_MARCA}>
          <p className={ROTULO_DE_MARCA}>Armadura livre: {f.pontuacao_armadura - f.armadura_marcada}/{f.pontuacao_armadura}</p>
          <Espacos total={f.pontuacao_armadura} marcados={f.armadura_marcada} rotulo={`Armadura de ${nome}`} cor="armadura" restantes />
        </div>
      )}
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

      {recolher ? (
        <>
          {resultadoDoDano}
          <Condicoes rotulo={nome} condicoes={f.condicoes} desabilitado={acao.isPending} aoTirar={tirar} />
          <Aviso erro={acao.error} />
          <details className="group text-sm">
            <summary className="flex min-h-11 cursor-pointer items-center text-texto-suave">
              <span aria-hidden className="mr-2 text-xs transition-transform group-open:rotate-90">▶</span>
              Dano, condições e itens
            </summary>
            <div className="space-y-3 pt-1">
              {formularioDeDano}
              <Condicoes rotulo={nome} condicoes={f.condicoes} desabilitado={acao.isPending} aoAplicar={aplicar} sem="lista" />
              {itens}
              {acaoExtra}
            </div>
          </details>
        </>
      ) : (
        <>
          {formularioDeDano}
          {resultadoDoDano}
          <Condicoes rotulo={nome} condicoes={f.condicoes} desabilitado={acao.isPending} aoAplicar={aplicar} aoTirar={tirar} />
          <Aviso erro={acao.error} />
          {compacto ? (
            <details className="text-sm">
              <summary className="cursor-pointer text-texto-suave">Itens e ouro</summary>
              <div className="mt-2">{itens}</div>
            </details>
          ) : itens}
        </>
      )}
    </article>
  )
}

export default function PersonagensNaSessao({ mesa, sessao, compacto }: { mesa: Mesa; sessao: Sessao; compacto?: boolean }) {
  const podeVer = (mesa.minhas_permissoes as string[]).includes('ver_fichas')
  const jogo = useJogo(mesa.id, sessao.id)
  const tirar = useParticipar(mesa.id, sessao.id)
  const participantes = jogo.data?.participantes ?? []
  const emJogo = sessao.status === 'em_andamento'
  const celular = useCelular()
  const recolher = !!compacto && celular
  return (
    <section className="space-y-3">
      <h2 className="rubrica">Personagens na sessão</h2>
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
        <div className="grid gap-3 md:grid-cols-2">
          {participantes.map((p) => {
            const tirarDaSessao = emJogo && sessao.sou_responsavel && (
              <Botao variante="fantasma" disabled={tirar.isPending}
                onClick={() => confirm(`Tirar ${p.resumo.nome || 'o personagem'} da sessão? As marcas dele nesta sessão se perdem.`)
                  && tirar.mutate({ personagemId: p.personagem_id, sair: true })}>
                Tirar da sessão
              </Botao>
            )
            return (
              <div key={p.personagem_id} className="space-y-1">
                {emJogo ? (
                  <CartaoPersonagem mesa={mesa} pid={p.personagem_id} nome={p.resumo.nome} jogador={p.resumo.jogador}
                    foto={p.resumo.foto} compacto={compacto} recolher={recolher} acaoExtra={tirarDaSessao} />
                ) : <MiniFicha f={p.resumo} />}
                {!recolher && tirarDaSessao}
              </div>
            )
          })}
        </div>
      )}
      <Aviso erro={jogo.error ?? tirar.error} />
    </section>
  )
}
