// Convite, membros, personagens e (para quem criou) permissões dos mestres.
import { useState } from 'react'
import { useNavigate } from 'react-router'

import {
  useApagarMesa, useClasses, useMudarPapel, useNovoCodigo, usePermissoesMestres, usePersonagens,
  useRemoverMembro, useSairDaMesa, useVincularMesa,
} from '../../api/consultas'
import type { Mesa, Permissao, PermissoesMestres } from '../../api/tipos'
import MedoDoMestre from '../../componentes/MedoDoMestre'
import { Aviso, Botao, Cartao, Selecao, Selo } from '../../componentes/ui'
import { NOME_PAPEL, NOME_PERMISSAO } from '../../lib/rotulos'

const PERMISSOES = Object.keys(NOME_PERMISSAO) as Permissao[]

function Convite({ mesa }: { mesa: Mesa }) {
  const novoCodigo = useNovoCodigo(mesa.id)
  const [copiado, setCopiado] = useState(false)
  const link = `${window.location.origin}/convite/${mesa.codigo_convite}`

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch { /* sem permissão de área de transferência: o link continua visível */ }
  }

  return (
    <Cartao titulo="Convite">
      <p className="text-sm text-texto-suave">Passe o código ou o link para quem vai jogar. Quem entra começa como jogador.</p>
      <p className="my-3 font-titulo text-3xl tracking-[0.3em] text-esperanca" aria-label="Código de convite">
        {mesa.codigo_convite}
      </p>
      <p className="break-all text-xs text-texto-suave">{link}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Botao variante="secundario" onClick={copiar}>{copiado ? 'Link copiado' : 'Copiar link'}</Botao>
        {mesa.sou_criador && (
          <Botao variante="fantasma" disabled={novoCodigo.isPending}
            onClick={() => confirm('Gerar um código novo? O código e o link atuais param de funcionar.') && novoCodigo.mutate()}>
            Gerar novo código
          </Botao>
        )}
      </div>
      <Aviso erro={novoCodigo.error} />
    </Cartao>
  )
}

function Membros({ mesa }: { mesa: Mesa }) {
  const mudarPapel = useMudarPapel(mesa.id)
  const remover = useRemoverMembro(mesa.id)
  return (
    <Cartao titulo="Membros">
      <ul className="divide-y divide-borda">
        {mesa.membros.map((m) => (
          <li key={m.usuario_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>
              {m.nome}
              <span className="ml-2"><Selo destaque={m.papel === 'mestre'}>{NOME_PAPEL[m.papel] ?? m.papel}</Selo></span>
              {m.criador && <span className="ml-2 text-xs text-texto-suave">criou a mesa</span>}
            </span>
            {mesa.sou_criador && !m.criador && (
              <span className="flex gap-1">
                <Botao variante="fantasma" disabled={mudarPapel.isPending}
                  onClick={() => mudarPapel.mutate({ usuarioId: m.usuario_id, papel: m.papel === 'mestre' ? 'jogador' : 'mestre' })}>
                  {m.papel === 'mestre' ? 'Tornar jogador' : 'Tornar mestre'}
                </Botao>
                <Botao variante="perigo" disabled={remover.isPending}
                  onClick={() => confirm(`Remover ${m.nome} da mesa?`) && remover.mutate(m.usuario_id)}>
                  Remover
                </Botao>
              </span>
            )}
          </li>
        ))}
      </ul>
      <Aviso erro={mudarPapel.error ?? remover.error} />
    </Cartao>
  )
}

function Permissoes({ mesa }: { mesa: Mesa }) {
  const salvar = usePermissoesMestres(mesa.id)
  const atuais = { ...mesa.permissoes_mestres } as Record<Permissao, boolean>
  return (
    <Cartao titulo="O que os outros mestres podem fazer">
      <p className="mb-3 text-sm text-texto-suave">Vale para todos os mestres; você, que criou a mesa, pode tudo.</p>
      <div className="space-y-2">
        {PERMISSOES.map((p) => (
          <label key={p} className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="accent-[var(--esperanca)]" checked={atuais[p] ?? true}
              disabled={salvar.isPending}
              onChange={(e) => salvar.mutate({ ...atuais, [p]: e.target.checked } as PermissoesMestres)} />
            {NOME_PERMISSAO[p]}
          </label>
        ))}
      </div>
      <Aviso erro={salvar.error} />
    </Cartao>
  )
}

function Personagens({ mesa }: { mesa: Mesa }) {
  const meus = usePersonagens()
  const classes = useClasses()
  const vincular = useVincularMesa()
  const [escolhido, setEscolhido] = useState('')
  const nomeClasse = (id: string) => classes.data?.find((c) => c.id === id)?.nome ?? ''
  const meusIds = new Set(meus.data?.map((p) => p.id))
  const livres = meus.data?.filter((p) => !p.mesa_id) ?? []

  return (
    <Cartao titulo="Personagens">
      {mesa.personagens.length === 0 && <p className="text-sm text-texto-suave">Nenhum personagem nesta mesa ainda.</p>}
      <ul className="divide-y divide-borda">
        {mesa.personagens.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>
              <span className="font-medium">{p.nome || 'Sem nome'}</span>
              <span className="ml-2 text-sm text-texto-suave">Nível {p.nivel} · {nomeClasse(p.classe)} · {p.jogador}</span>
            </span>
            {meusIds.has(p.id) && (
              <Botao variante="fantasma" disabled={vincular.isPending}
                onClick={() => vincular.mutate({ personagemId: p.id, mesaId: null })}>Tirar da mesa</Botao>
            )}
          </li>
        ))}
      </ul>
      {livres.length > 0 && (
        <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={(e) => {
          e.preventDefault()
          vincular.mutate({ personagemId: escolhido, mesaId: mesa.id }, { onSuccess: () => setEscolhido('') })
        }}>
          <Selecao rotulo="Trazer um personagem seu" className="min-w-48 flex-1" value={escolhido}
            onChange={(e) => setEscolhido(e.target.value)}
            opcoes={[['', 'Escolha…'], ...livres.map((p): [string, string] => [p.id, `${p.nome || 'Sem nome'} (nível ${p.nivel})`])]} />
          <Botao type="submit" variante="secundario" disabled={!escolhido || vincular.isPending}>Trazer</Botao>
        </form>
      )}
      <Aviso erro={vincular.error} />
    </Cartao>
  )
}

export default function AbaGeral({ mesa }: { mesa: Mesa }) {
  const sair = useSairDaMesa()
  const apagar = useApagarMesa()
  const navegar = useNavigate()
  const irParaMesas = { onSuccess: () => navegar('/mesas') }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="lg:col-span-2">
        <MedoDoMestre mesaId={mesa.id} medo={mesa.medo} podeMudar={mesa.meu_papel === 'mestre'} />
      </div>
      <Convite mesa={mesa} />
      <Membros mesa={mesa} />
      <Personagens mesa={mesa} />
      {mesa.sou_criador && <Permissoes mesa={mesa} />}
      <div className="lg:col-span-2">
        {mesa.sou_criador ? (
          <Botao variante="perigo" disabled={apagar.isPending}
            onClick={() => confirm(`Apagar a mesa "${mesa.nome}"? Inimigos e NPCs dela somem; os personagens continuam existindo.`)
              && apagar.mutate(mesa.id, irParaMesas)}>
            Apagar mesa
          </Botao>
        ) : (
          <Botao variante="perigo" disabled={sair.isPending}
            onClick={() => confirm('Sair desta mesa? Seus personagens saem junto.') && sair.mutate(mesa.id, irParaMesas)}>
            Sair da mesa
          </Botao>
        )}
        <Aviso erro={sair.error ?? apagar.error} />
      </div>
    </div>
  )
}
