// Resumo da mesa para todos: quem joga (e quem está online), os personagens e o
// nível. Trazer um personagem seu e sair da mesa também ficam aqui. Administrar
// (papéis, nível, permissões, apagar) é na aba Gerenciar; o convite, na aba
// Convite; as duas só dos mestres.
import { useState } from 'react'
import { useNavigate } from 'react-router'

import {
  useClasses, useCopiarParaMesa, usePersonagens, useRemoverPersonagemDaMesa, useSairDaMesa, useVincularMesa,
} from '../../api/consultas'
import type { Mesa } from '../../api/tipos'
import { Foto } from '../../componentes/Foto'
import { Aviso, Botao, Cartao, Selecao, Selo } from '../../componentes/ui'
import { NOME_PAPEL } from '../../lib/rotulos'

function Membros({ mesa }: { mesa: Mesa }) {
  return (
    <Cartao titulo="Jogadores e mestres">
      <ul className="divide-y divide-borda">
        {mesa.membros.map((m) => (
          <li key={m.usuario_id} className="flex flex-wrap items-center gap-2 py-2">
            {/* presença: verde = com o app aberto agora */}
            <span role="img" aria-label={m.online ? 'online' : 'offline'} title={m.online ? 'Online agora' : 'Offline'}
              className={`inline-block h-2.5 w-2.5 rounded-full ${m.online ? 'bg-sucesso' : 'bg-borda'}`} />
            {m.nome}
            <Selo destaque={m.papel === 'mestre'}>{NOME_PAPEL[m.papel] ?? m.papel}</Selo>
            {m.criador && <span className="text-xs text-texto-suave">criou a mesa</span>}
          </li>
        ))}
      </ul>
    </Cartao>
  )
}

/** Personagens da mesa e como trazer um seu: um sem mesa e dentro do nível entra
    direto; os outros entram por cópia (o original fica onde está). */
function Personagens({ mesa }: { mesa: Mesa }) {
  const meus = usePersonagens()
  const classes = useClasses()
  const vincular = useVincularMesa()
  const copiar = useCopiarParaMesa()
  const remover = useRemoverPersonagemDaMesa(mesa.id)
  const [escolhido, setEscolhido] = useState('')
  // tirar da mesa: quem criou a mesa, ou o dono (a API confere de novo)
  const meusIds = new Set(meus.data?.map((c) => c.id))
  const podeTirar = (id: string) => mesa.sou_criador || meusIds.has(id)
  const nomeClasse = (id: string) => classes.data?.find((c) => c.id === id)?.nome ?? ''
  const candidatos = meus.data?.filter((p) => p.mesa_id !== mesa.id) ?? []
  const p = candidatos.find((c) => c.id === escolhido)
  const direto = !!p && !p.mesa_id && p.nivel <= mesa.nivel_maximo

  return (
    <Cartao titulo="Personagens">
      <p className="mb-2 text-sm text-texto-suave">Nível máximo da mesa: <b className="text-texto">{mesa.nivel_maximo}</b></p>
      {mesa.personagens.length === 0 && <p className="text-sm text-texto-suave">Nenhum personagem nesta mesa ainda.</p>}
      <ul className="divide-y divide-borda">
        {mesa.personagens.map((x) => (
          <li key={x.id} className="py-2">
            <div className="flex w-full items-center gap-3">
              <Foto id={x.foto} nome={x.nome || '?'} tamanho="p" />
              <span className="min-w-0 flex-1">
                <span className="font-medium">{x.nome || 'Sem nome'}</span>
                {x.morto && <span className="ml-2 text-xs text-perigo">atravessou o véu</span>}
                <span className="ml-2 text-sm text-texto-suave">Nível {x.nivel} · {nomeClasse(x.classe)} · {x.jogador}</span>
              </span>
              {podeTirar(x.id) && (
                <Botao variante="perigo" className="shrink-0 px-3 py-1" disabled={remover.isPending}
                  onClick={() => confirm(`Tirar ${x.nome || 'este personagem'} da mesa? Ele continua existindo, `
                    + 'só fica sem mesa. Se estiver numa sessão em andamento, sai dela e as marcas dela se perdem.')
                    && remover.mutate(x.id)}>
                  Tirar da mesa
                </Botao>
              )}
            </div>
          </li>
        ))}
      </ul>
      {candidatos.length > 0 && (
        <form className="mt-3 space-y-2" onSubmit={(e) => {
          e.preventDefault()
          const limpar = { onSuccess: () => setEscolhido('') }
          if (direto) vincular.mutate({ personagemId: escolhido, mesaId: mesa.id }, limpar)
          else copiar.mutate({ personagemId: escolhido, mesaId: mesa.id }, limpar)
        }}>
          <div className="flex flex-wrap items-end gap-2">
            <Selecao rotulo="Trazer um personagem seu" className="min-w-48 flex-1" value={escolhido}
              onChange={(e) => setEscolhido(e.target.value)}
              opcoes={[['', 'Escolha…'], ...candidatos.map((c): [string, string] =>
                [c.id, `${c.nome || 'Sem nome'} (nível ${c.nivel}${c.mesa_id ? ', em outra mesa' : ''})`])]} />
            <Botao type="submit" variante="secundario" disabled={!escolhido || vincular.isPending || copiar.isPending}>
              {direto || !p ? 'Trazer' : 'Trazer uma cópia'}
            </Botao>
          </div>
          {p && !direto && (
            <p className="text-xs text-texto-suave">
              {p.mesa_id ? 'Ele está em outra mesa' : `Ele está acima do nível da mesa (${mesa.nivel_maximo})`}:
              entra uma cópia. {p.nivel > mesa.nivel_maximo && 'Os níveis acima viram plano, aplicado quando o mestre liberar.'}
            </p>
          )}
        </form>
      )}
      <Aviso erro={vincular.error ?? copiar.error ?? remover.error} />
    </Cartao>
  )
}

export default function AbaGeral({ mesa }: { mesa: Mesa }) {
  const sair = useSairDaMesa()
  const navegar = useNavigate()

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Medo, repouso, revelado, lojas e as fichas de jogo ficam em cada sessão (aba Sessões) */}
      {mesa.medo_em_jogo.length > 0 && (
        <p className="rounded-xl border border-esperanca/50 bg-esperanca/10 px-3 py-2 text-sm lg:col-span-2">
          Há sessão em andamento: entre pela aba <b>Sessões</b>.
        </p>
      )}
      <Membros mesa={mesa} />
      <Personagens mesa={mesa} />
      {!mesa.sou_criador && (   // quem criou não sai: apaga a mesa (aba Gerenciar)
        <div className="lg:col-span-2">
          <Botao variante="perigo" disabled={sair.isPending}
            onClick={() => confirm('Sair desta mesa? Seus personagens saem junto (e da sessão em andamento, se estiverem jogando).')
              && sair.mutate(mesa.id, { onSuccess: () => navegar('/mesas') })}>
            Sair da mesa
          </Botao>
          <Aviso erro={sair.error} />
        </div>
      )}
    </div>
  )
}
