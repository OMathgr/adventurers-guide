// A sessão para quem joga. Em andamento: entrar com um personagem seu da mesa,
// a sua ficha de jogo (marcas desta sessão), o Medo, o repouso, o que o mestre
// revelou, as lojas e a mini ficha dos aliados. Encerrada: consulta de como
// cada um terminou e do Medo final.
import { useState } from 'react'

import { useFicha, useFichaNaSessao, useJogo, useParticipar } from '../../api/consultas'
import type { Mesa, VistaDaSessao } from '../../api/tipos'
import { useAutenticacao } from '../../auth/Autenticacao'
import FichaDeJogo from '../../componentes/FichaDeJogo'
import { ContextoDaSessao } from '../../componentes/contextoDaSessao'
import RolagemDeDados from '../../componentes/RolagemDeDados'
import FichaVisao from '../../componentes/Ficha'
import { MiniFicha } from '../../componentes/FichaResumida'
import MedoDoMestre from '../../componentes/MedoDoMestre'
import PainelDeRepouso from '../../componentes/Repouso'
import { Revelado } from '../../componentes/VistaDosJogadores'
import { Abas, Aviso, Botao, Carregando, Cartao, Selecao, Selo } from '../../componentes/ui'

function Entrar({ mesa, sessao }: { mesa: Mesa; sessao: VistaDaSessao }) {
  const { usuario } = useAutenticacao()
  const participar = useParticipar(mesa.id, sessao.id)
  const meus = mesa.personagens.filter((p) => p.dono_id === usuario?.id && !p.morto)
  const [escolhido, setEscolhido] = useState('')
  const pid = escolhido || (meus.length === 1 ? meus[0].id : '')

  if (sessao.sou_responsavel) return null   // quem mestra não joga a própria sessão
  return (
    <Cartao titulo="Entrar na sessão">
      {meus.length === 0 ? (
        <p className="text-sm text-texto-suave">
          Você não tem personagem vivo nesta mesa. Traga um na aba Mesa para poder entrar.
        </p>
      ) : (
        <form className="flex flex-wrap items-end gap-2" onSubmit={(e) => {
          e.preventDefault()
          participar.mutate({ personagemId: pid })
        }}>
          {meus.length > 1 && (
            <Selecao rotulo="Com qual personagem" value={escolhido} onChange={(e) => setEscolhido(e.target.value)}
              opcoes={[['', 'Escolha…'], ...meus.map((p): [string, string] => [p.id, p.nome || 'Sem nome'])]} />
          )}
          <Botao type="submit" disabled={!pid || participar.isPending}>
            {meus.length === 1 ? `Entrar com ${meus[0].nome || 'meu personagem'}` : 'Entrar'}
          </Botao>
          <p className="w-full text-xs text-texto-suave">
            O personagem começa a sessão inteiro: PV, Fadiga, armadura e condições limpos e Esperança 2.
            Cicatrizes continuam.
          </p>
        </form>
      )}
      <Aviso erro={participar.error} />
    </Cartao>
  )
}

/** Minha ficha nesta sessão: em andamento, a de jogo (com controles); encerrada, como terminou. */
function MinhaFicha({ mesa, sessao, pid }: { mesa: Mesa; sessao: VistaDaSessao; pid: string }) {
  const emJogo = sessao.status === 'em_andamento'
  const atual = useFicha(pid)                                          // marcas da sessão ativa
  const final = useFichaNaSessao(mesa.id, sessao.id, pid, !emJogo)     // como terminou (consulta)
  const participar = useParticipar(mesa.id, sessao.id)
  const consulta = emJogo ? atual : final
  if (consulta.isPending) return <Carregando />
  if (consulta.isError) return <Aviso erro={consulta.error} />
  const f = consulta.data

  return (
    <section className="space-y-3">
      {emJogo ? (
        <>
          <FichaDeJogo personagemId={pid} ficha={f} />
          <Botao variante="fantasma" disabled={participar.isPending}
            onClick={() => confirm(`Tirar ${f.nome || 'o personagem'} desta sessão? As marcas dele nesta sessão se perdem.`)
              && participar.mutate({ personagemId: pid, sair: true })}>
            Sair da sessão
          </Botao>
          <Aviso erro={participar.error} />
        </>
      ) : (
        <>
          <p className="text-sm text-texto-suave">Como {f.nome || 'o personagem'} terminou esta sessão.</p>
          <FichaVisao ficha={f} />
        </>
      )}
    </section>
  )
}

export default function SessaoDeJogo({ mesa, sid }: { mesa: Mesa; sid: string }) {
  const jogo = useJogo(mesa.id, sid)
  const [meu, setMeu] = useState<string | null>(null)
  const [parte, setParte] = useState<'jogo' | 'dados'>('jogo')

  if (jogo.isPending) return <Carregando />
  if (jogo.isError) return <Aviso erro={jogo.error} />
  const s = jogo.data
  const emJogo = s.status === 'em_andamento'
  const atual = s.meus.includes(meu ?? '') ? meu! : s.meus[0]
  const nomes = Object.fromEntries(s.participantes.map((p) => [p.personagem_id, p.resumo.nome || 'Sem nome']))
  const aliados = s.participantes.filter((p) => p.personagem_id !== atual)
  // as cartas da mão (na ficha e no registro de rolagens) ganham "Usar", com os aliados como alvo
  const contexto = emJogo && atual ? {
    mesaId: mesa.id, sessaoId: s.id,
    aliados: aliados.map((x) => ({ id: x.personagem_id, nome: x.resumo.nome || 'Sem nome' })),
  } : null

  return (
    <ContextoDaSessao.Provider value={contexto}>
    <div className="space-y-4">
      <div>
        <h2 className="flex flex-wrap items-center gap-2 text-xl">
          {s.titulo} <Selo destaque={emJogo}>{emJogo ? 'Em andamento' : 'Encerrada'}</Selo>
        </h2>
        <p className="text-sm text-texto-suave">Mestre: {s.mestre}</p>
      </div>

      <MedoDoMestre medo={s.medo} titulo={emJogo ? 'Medo do mestre' : 'Medo ao fim da sessão'} />
      {emJogo && s.meus.length === 0 && <Entrar mesa={mesa} sessao={s} />}

      <Abas<'jogo' | 'dados'> atual={parte} aoTrocar={setParte}
        abas={[['jogo', emJogo ? 'Jogo' : 'Como terminou'], ['dados', 'Rolagem de dados']]} />
      {parte === 'dados' && (
        <RolagemDeDados mesaId={mesa.id} sessaoId={s.id} personagemId={atual ?? null} souMestre={false} emAndamento={emJogo} />
      )}
      {parte === 'jogo' && <>
      {emJogo && <PainelDeRepouso mesa={mesa} sessao={s} />}

      {s.meus.length > 1 && (
        <Abas<string> atual={atual} aoTrocar={setMeu} abas={s.meus.map((pid): [string, string] => [pid, nomes[pid]])} />
      )}
      {atual && <MinhaFicha key={atual} mesa={mesa} sessao={s} pid={atual} />}

      {emJogo && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Revelado v={{ combate: s.combate, npcs: s.npcs, lojas: s.lojas }} />
        </div>
      )}

      <Cartao titulo={emJogo ? 'Aliados na sessão' : 'Quem jogou'}>
        {(atual ? aliados : s.participantes).length === 0 && (
          <p className="text-sm text-texto-suave">{emJogo ? 'Ninguém mais entrou ainda.' : 'Ninguém jogou esta sessão.'}</p>
        )}
        <ul className="grid gap-3 md:grid-cols-2">
          {(atual ? aliados : s.participantes).map((p) => (
            <li key={p.personagem_id}>
              <p className="mb-1 font-medium">{p.resumo.nome || 'Sem nome'}</p>
              <MiniFicha f={p.resumo} />
            </li>
          ))}
        </ul>
      </Cartao>
      </>}
    </div>
    </ContextoDaSessao.Provider>
  )
}
