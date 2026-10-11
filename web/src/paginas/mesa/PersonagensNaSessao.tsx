// Personagens da mesa durante a sessão, do ponto de vista do mestre: lê a
// ficha (ver_fichas), aplica dano (aplicar_dano) e condições
// (aplicar_condicoes). O resto do personagem continua sendo do jogador.
import { useState } from 'react'

import { useAcaoNoPersonagem, useFichaNaMesa } from '../../api/consultas'
import type { Mesa, ResultadoDano } from '../../api/tipos'
import Condicoes from '../../componentes/Condicoes'
import { Aviso, Botao, Campo, Carregando, Espacos, Esperanca } from '../../componentes/ui'
import { NOME_GRAVIDADE } from '../../lib/rotulos'

function descrever(r: ResultadoDano) {
  return `${r.dano} de dano (${NOME_GRAVIDADE[r.gravidade]})${r.usou_armadura ? ', reduzido pela armadura' : ''}: `
    + `${r.pv_marcados} PV marcado${r.pv_marcados === 1 ? '' : 's'}${r.caiu ? '. Caiu: movimento de morte!' : '.'}`
}

function CartaoPersonagem({ mesa, pid, nome, jogador }: { mesa: Mesa; pid: string; nome: string; jogador: string }) {
  const ficha = useFichaNaMesa(mesa.id, pid)
  const acao = useAcaoNoPersonagem(mesa.id, pid)
  const [dano, setDano] = useState('')
  const [armadura, setArmadura] = useState(false)
  const pode = (p: string) => (mesa.minhas_permissoes as string[]).includes(p)

  if (ficha.isPending) return <Carregando />
  if (ficha.isError) return <Aviso erro={ficha.error} />
  const f = ficha.data

  return (
    <article aria-label={nome || 'Sem nome'} className="space-y-2 rounded-2xl border border-borda bg-superficie p-4">
      <header>
        <h3 className="font-titulo text-base">{nome || 'Sem nome'}</h3>
        <p className="text-xs text-texto-suave">{jogador} · Evasão {f.evasao} · Limiares {f.limiar_maior}/{f.limiar_grave}</p>
      </header>
      <p className="text-xs text-texto-suave">PV</p>
      <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo={`PV de ${nome}`} cor="perigo" />
      <p className="text-xs text-texto-suave">PF</p>
      <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo={`PF de ${nome}`} cor="medo" />
      {f.pontuacao_armadura > 0 && <>
        <p className="text-xs text-texto-suave">Armadura</p>
        <Espacos total={f.pontuacao_armadura} marcados={f.armadura_marcada} rotulo={`Armadura de ${nome}`} />
      </>}
      <Esperanca atual={f.esperanca} maximo={f.esperanca_max} />

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
    </article>
  )
}

export default function PersonagensNaSessao({ mesa }: { mesa: Mesa }) {
  const podeVer = (mesa.minhas_permissoes as string[]).includes('ver_fichas')
  return (
    <section className="space-y-3">
      <h2 className="text-lg text-esperanca">Personagens</h2>
      {mesa.personagens.length === 0 && <p className="text-sm text-texto-suave">Nenhum personagem na mesa.</p>}
      {!podeVer && mesa.personagens.length > 0 && (
        <p className="text-sm text-texto-suave">Quem criou a mesa não liberou ver as fichas para os mestres.</p>
      )}
      {podeVer && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {mesa.personagens.map((p) => (
            <CartaoPersonagem key={p.id} mesa={mesa} pid={p.id} nome={p.nome} jogador={p.jogador} />
          ))}
        </div>
      )}
    </section>
  )
}
