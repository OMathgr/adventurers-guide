// Administração da mesa, só para os mestres: papéis e remoção de membros (quem
// criou), nível máximo e regra das moedas (permissão "nivel"), o que os mestres
// podem fazer (quem criou edita; os outros mestres só leem) e apagar a mesa.
import { useNavigate } from 'react-router'

import {
  useApagarMesa, useMoedasDaMesa, useMudarPapel, useNivelDaMesa, usePermissoesMestres, useRemoverMembro,
} from '../../api/consultas'
import type { Mesa, Permissao, PermissoesMestres } from '../../api/tipos'
import { Aviso, Botao, Cartao, Selecao, Selo } from '../../componentes/ui'
import { NOME_PAPEL, NOME_PERMISSAO } from '../../lib/rotulos'

const PERMISSOES = Object.keys(NOME_PERMISSAO) as Permissao[]

function PapeisDosMembros({ mesa }: { mesa: Mesa }) {
  const mudarPapel = useMudarPapel(mesa.id)
  const remover = useRemoverMembro(mesa.id)
  return (
    <Cartao titulo="Membros e papéis">
      {!mesa.sou_criador && <p className="mb-2 text-sm text-texto-suave">Só quem criou a mesa muda papéis e remove membros.</p>}
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

function NivelDaMesa({ mesa }: { mesa: Mesa }) {
  const mudar = useNivelDaMesa(mesa.id)
  const moedas = useMoedasDaMesa(mesa.id)
  const pode = mesa.minhas_permissoes.includes('nivel')
  return (
    <Cartao titulo="Nível e regras da mesa">
      <p className="mb-3 text-sm text-texto-suave">
        Os personagens desta mesa sobem até o nível <b className="text-texto">{mesa.nivel_maximo}</b>.
        {pode ? ' Baixar não desfaz níveis: quem já passou só não sobe até a mesa alcançar.'
          : ' Você não tem a permissão de mudar o nível.'}
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

function Permissoes({ mesa }: { mesa: Mesa }) {
  const salvar = usePermissoesMestres(mesa.id)
  const atuais = { ...mesa.permissoes_mestres } as Record<Permissao, boolean>
  const edita = mesa.sou_criador
  return (
    <Cartao titulo="O que os mestres podem fazer">
      <p className="mb-3 text-sm text-texto-suave">
        {edita ? 'Vale para todos os mestres; você, que criou a mesa, pode tudo.'
          : 'Definido por quem criou a mesa; vale para todos os mestres.'}
      </p>
      <div className="space-y-2">
        {PERMISSOES.map((p) => (
          <label key={p} className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="accent-[var(--esperanca)]" checked={atuais[p] ?? true}
              disabled={!edita || salvar.isPending}
              onChange={(e) => salvar.mutate({ ...atuais, [p]: e.target.checked } as PermissoesMestres)} />
            {NOME_PERMISSAO[p]}
          </label>
        ))}
      </div>
      <Aviso erro={salvar.error} />
    </Cartao>
  )
}

export default function AbaGerenciar({ mesa }: { mesa: Mesa }) {
  const apagar = useApagarMesa()
  const navegar = useNavigate()
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <PapeisDosMembros mesa={mesa} />
      <NivelDaMesa mesa={mesa} />
      <Permissoes mesa={mesa} />
      {mesa.sou_criador && (
        <div className="lg:col-span-2">
          <Botao variante="perigo" disabled={apagar.isPending}
            onClick={() => confirm(`Apagar a mesa "${mesa.nome}"? Inimigos e NPCs dela somem; os personagens continuam existindo.`)
              && apagar.mutate(mesa.id, { onSuccess: () => navegar('/mesas') })}>
            Apagar mesa
          </Botao>
          <Aviso erro={apagar.error} />
        </div>
      )}
    </div>
  )
}
