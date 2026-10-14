// Convite, membros, personagens e (para quem criou) permissões dos mestres.
import { useState } from 'react'
import { useNavigate } from 'react-router'

import {
  useApagarMesa, useClasses, useCopiarParaMesa, useMoedasDaMesa, useMudarPapel, useNivelDaMesa, useNovoCodigo,
  usePermissoesMestres, usePersonagens, useRemoverMembro, useSairDaMesa, useVincularMesa,
} from '../../api/consultas'
import type { Mesa, Permissao, PermissoesMestres } from '../../api/tipos'
import FichaResumida from '../../componentes/FichaResumida'
import { Foto } from '../../componentes/Foto'
import MedoDoMestre from '../../componentes/MedoDoMestre'
import PainelDeRepouso from '../../componentes/Repouso'
import VistaDosJogadores from '../../componentes/VistaDosJogadores'
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
              {/* presença: verde = com o app aberto agora */}
              <span role="img" aria-label={m.online ? 'online' : 'offline'} title={m.online ? 'Online agora' : 'Offline'}
                className={`mr-2 inline-block h-2.5 w-2.5 rounded-full ${m.online ? 'bg-sucesso' : 'bg-borda'}`} />
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

function NivelDaMesa({ mesa }: { mesa: Mesa }) {
  const mudar = useNivelDaMesa(mesa.id)
  const moedas = useMoedasDaMesa(mesa.id)
  const pode = mesa.minhas_permissoes.includes('nivel')
  return (
    <Cartao titulo="Nível e regras da mesa">
      <p className="mb-3 text-sm text-texto-suave">
        Os personagens desta mesa sobem até o nível <b className="text-texto">{mesa.nivel_maximo}</b>.
        {pode && ' Baixar não desfaz níveis: quem já passou só não sobe até a mesa alcançar.'}
      </p>
      {pode && (
        <Selecao rotulo="Nível máximo" className="max-w-40" value={String(mesa.nivel_maximo)} disabled={mudar.isPending}
          onChange={(e) => mudar.mutate(Number(e.target.value))}
          opcoes={Array.from({ length: 10 }, (_, i): [string, string] => [String(i + 1), `Nível ${i + 1}`])} />
      )}
      <label className="mt-3 flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1" checked={mesa.usar_moedas} disabled={!pode || moedas.isPending}
          onChange={(e) => moedas.mutate(e.target.checked)} />
        <span>
          Regra opcional das moedas
          <span className="block text-xs text-texto-suave">10 moedas valem 1 punhado, para contar o ouro com mais detalhe.</span>
        </span>
      </label>
      <Aviso erro={mudar.error ?? moedas.error} />
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
  const [escolhido, setEscolhido] = useState('')
  const [aberto, setAberto] = useState<string | null>(null)   // ficha simplificada aberta
  const nomeClasse = (id: string) => classes.data?.find((c) => c.id === id)?.nome ?? ''
  const candidatos = meus.data?.filter((p) => p.mesa_id !== mesa.id) ?? []
  const p = candidatos.find((c) => c.id === escolhido)
  const direto = !!p && !p.mesa_id && p.nivel <= mesa.nivel_maximo

  return (
    <Cartao titulo="Personagens">
      {mesa.personagens.length === 0 && <p className="text-sm text-texto-suave">Nenhum personagem nesta mesa ainda.</p>}
      <ul className="divide-y divide-borda">
        {mesa.personagens.map((x) => (
          <li key={x.id} className="py-2">
            <button type="button" aria-expanded={aberto === x.id} onClick={() => setAberto(aberto === x.id ? null : x.id)}
              className="flex w-full items-center gap-3 rounded-lg text-left hover:bg-superficie-2/50">
              <Foto id={x.foto} nome={x.nome || '?'} tamanho="p" />
              <span className="min-w-0 flex-1">
                <span className="font-medium">{x.nome || 'Sem nome'}</span>
                {x.morto && <span className="ml-2 text-xs text-perigo">atravessou o véu</span>}
                <span className="ml-2 text-sm text-texto-suave">Nível {x.nivel} · {nomeClasse(x.classe)} · {x.jogador}</span>
              </span>
              <span aria-hidden className="text-xs text-texto-suave">{aberto === x.id ? '▲' : '▼'}</span>
            </button>
            {aberto === x.id && <div className="mt-2"><FichaResumida mesaId={mesa.id} pid={x.id} /></div>}
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
      <Aviso erro={vincular.error ?? copiar.error} />
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
      {/* repouso aberto pelo mestre: cada jogador escolhe os movimentos do seu personagem */}
      <PainelDeRepouso mesa={mesa} />
      {/* o que o mestre revelou: inimigos em combate e NPCs conhecidos */}
      <VistaDosJogadores mesaId={mesa.id} />
      {/* Medo das sessões em andamento: todos veem (quem muda é o mestre, na sessão) */}
      {mesa.medo_em_jogo.map((m) => (
        <div key={m.sessao_id} className="lg:col-span-2">
          <MedoDoMestre medo={m.medo} titulo={`Medo (sessão de ${m.mestre})`} />
        </div>
      ))}
      <Convite mesa={mesa} />
      <Membros mesa={mesa} />
      <Personagens mesa={mesa} />
      <NivelDaMesa mesa={mesa} />
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
