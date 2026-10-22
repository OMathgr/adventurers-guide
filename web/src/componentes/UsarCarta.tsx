// "Usar" de uma carta da mão durante a sessão de jogo: escolhe a opção, o alvo
// (você ou um aliado da sessão) e a quantidade, e o motor paga o custo, marca o
// limite e aplica os efeitos (motor/usos_de_cartas.py). O teste e o dano contra
// inimigos continuam na aba Rolagem de dados; o mestre aplica no inimigo.
import { useState } from 'react'

import { useUsarCarta } from '../api/consultas'
import type { CartaDeDominio, Ficha, UsoDeCarta } from '../api/tipos'
import type { SessaoEmJogo } from './contextoDaSessao'
import { Aviso, Botao } from './ui'

const NOME_LIMITE: Record<string, string> = {
  sessao: 'uma vez por sessão', descanso: 'uma vez por descanso', descanso_longo: 'uma vez por descanso longo',
}

/** O máximo da quantidade, quando a tela sabe (o motor confere de qualquer jeito). */
function maximo(uso: UsoDeCarta, ficha: Ficha, carta: string): number | undefined {
  const m = uso.quantidade_max
  if (typeof m === 'number') return m
  if (m === 'marcadores') return ficha.marcadores_cartas?.[carta] ?? 0
  if (m === 'esperanca') return ficha.esperanca
  return undefined
}

export default function UsarCarta({ carta, ficha, personagemId, sessao }: {
  carta: CartaDeDominio; ficha: Ficha; personagemId: string; sessao: SessaoEmJogo
}) {
  const uso = carta.uso!
  const usar = useUsarCarta(sessao.mesaId, sessao.sessaoId, personagemId)
  const [opcao, setOpcao] = useState(uso.opcoes.length === 1 ? uso.opcoes[0].id : '')
  const [alvo, setAlvo] = useState('')
  const [quantidade, setQuantidade] = useState(String(uso.quantidade_min ?? 1))
  const escolhida = uso.opcoes.find((o) => o.id === opcao)
  const tipoAlvo = escolhida?.alvo ?? uso.alvo
  const pedeQuantidade = uso.quantidade_max != null && (escolhida ? escolhida.quantidade !== false : uso.opcoes.length === 0)
  const max = maximo(uso, ficha, carta.id)
  const gastos = ficha.usos_de_carta_gastos ?? []
  const gasto = (chave: string) => gastos.includes(chave)
  const cartaGasta = !!uso.limite && gasto(`carta:${carta.id}`)
  const marcadores = ficha.marcadores_cartas?.[carta.id]
  const alvoOk = tipoAlvo !== 'aliado' || !!alvo
  const pronto = (uso.opcoes.length === 0 || !!escolhida) && alvoOk && !cartaGasta
    && !(escolhida?.limite && gasto(`carta:${carta.id}:${escolhida.id}`))

  function enviar() {
    usar.mutate({
      carta: carta.id, opcao: escolhida?.id ?? null, quantidade: pedeQuantidade ? Number(quantidade) : null,
      alvos: (tipoAlvo === 'aliado' || tipoAlvo === 'qualquer') && alvo ? [alvo] : [],
    })
  }

  return (
    <div className="mt-3 space-y-2 border-t border-borda pt-3 text-sm">
      <p className="flex flex-wrap gap-x-3 text-xs text-texto-suave">
        {uso.limite && <span>{NOME_LIMITE[uso.limite]}{cartaGasta ? ' (já usada)' : ''}</span>}
        {marcadores !== undefined && <span>Marcadores na carta: <b className="text-texto">{marcadores}</b></span>}
      </p>
      {uso.opcoes.length > 1 && (
        <fieldset className="space-y-1">
          <legend className="sr-only">Opção</legend>
          {uso.opcoes.map((o) => {
            const usada = !!o.limite && gasto(`carta:${carta.id}:${o.id}`)
            return (
              <label key={o.id} className={`flex items-center gap-2 ${usada ? 'opacity-50' : ''}`}>
                <input type="radio" name={`opcao-${carta.id}`} checked={opcao === o.id} disabled={usada}
                  onChange={() => { setOpcao(o.id); usar.reset() }} />
                {o.rotulo}{o.limite ? ` (${NOME_LIMITE[o.limite]}${usada ? ', já usada' : ''})` : ''}
              </label>
            )
          })}
        </fieldset>
      )}
      {(tipoAlvo === 'aliado' || tipoAlvo === 'qualquer') && (
        <select aria-label={`Alvo de ${carta.nome}`} value={alvo} onChange={(e) => setAlvo(e.target.value)}
          className="w-full rounded-lg border border-borda bg-fundo px-3 py-2">
          <option value="">{tipoAlvo === 'qualquer' ? 'Em você' : 'Escolha o aliado'}</option>
          {sessao.aliados.map((a) => <option key={a.id} value={a.id}>{a.nome}</option>)}
        </select>
      )}
      {tipoAlvo === 'aliados' && <p className="text-xs text-texto-suave">Vale para todos os aliados da sessão.</p>}
      {tipoAlvo === 'grupo' && <p className="text-xs text-texto-suave">Vale para você e todos os aliados da sessão.</p>}
      {pedeQuantidade && (
        <label className="flex items-center gap-2">
          <span className="text-texto-suave">{uso.quantidade_rotulo || 'Quantidade'}</span>
          <input type="number" min={uso.quantidade_min ?? 1} max={max} value={quantidade}
            onChange={(e) => setQuantidade(e.target.value)} aria-label={`${uso.quantidade_rotulo || 'Quantidade'} (${carta.nome})`}
            className="w-20 rounded-lg border border-borda bg-fundo px-2 py-1.5" />
          {max !== undefined && <span className="text-xs text-texto-suave">até {max}</span>}
        </label>
      )}
      {uso.nota && <p className="text-xs text-texto-suave">{uso.nota}</p>}
      <Botao variante="secundario" disabled={!pronto || usar.isPending} onClick={enviar}>Usar {carta.nome}</Botao>
      {usar.data && (
        <div role="status" className="rounded-lg border border-esperanca/40 bg-esperanca/10 p-2 text-xs">
          {usar.data.notas.join(' ')}
          {usar.data.teste && <p className="mt-1 font-medium">Role agora: {usar.data.teste} (aba Rolagem de dados).</p>}
        </div>
      )}
      <Aviso erro={usar.error} />
    </div>
  )
}
