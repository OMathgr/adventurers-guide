// Guia de Batalha (SRD, "Battle Points") dentro do encontro: orçamento de
// Pontos de Batalha, ajustes e quanto os inimigos já colocados gastam. As
// contas são do motor; aqui o mestre só marca as escolhas.
import { useGuiaDeBatalha } from '../api/consultas'
import type { GuiaDeBatalha as Guia, OpcoesDoGuia } from '../api/tipos'
import { PLURAL_TIPO_ADVERSARIO, comSinal } from '../lib/rotulos'
import { Aviso, Campo, Selecao } from './ui'

export default function GuiaDeBatalha({ mesaId, sid, encontroId, guia, podeEditar }:
  { mesaId: string; sid: string; encontroId: string; guia: Guia; podeEditar: boolean }) {
  const salvar = useGuiaDeBatalha(mesaId, sid, encontroId)
  const o = guia.opcoes
  const mudar = (parcial: Partial<OpcoesDoGuia>) => salvar.mutate({ ...o, ...parcial })
  const travado = !podeEditar || salvar.isPending
  const passou = guia.saldo < 0
  const proporcao = guia.total > 0 ? Math.min(100, Math.round((guia.gasto / guia.total) * 100)) : 100

  const escolha = (rotulo: string, valor: number, marcado: boolean, chave: 'mais_facil' | 'mais_dificil' | 'dano_extra') => (
    <label className="flex items-center justify-between gap-2 text-sm">
      <span className="flex items-center gap-2">
        <input type="checkbox" checked={marcado} disabled={travado}
          onChange={(e) => mudar({ [chave]: e.target.checked,
            // fácil e difícil se excluem
            ...(chave === 'mais_facil' && e.target.checked ? { mais_dificil: false } : {}),
            ...(chave === 'mais_dificil' && e.target.checked ? { mais_facil: false } : {}) })} />
        {rotulo}
      </span>
      <span className="text-texto-suave">{comSinal(valor)}</span>
    </label>
  )

  return (
    <section aria-label="Guia de Batalha" className="space-y-3 rounded-2xl border border-borda bg-superficie p-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm text-esperanca">Guia de Batalha</h3>
        <p className="text-sm">
          <b className={passou ? 'text-perigo' : 'text-texto'}>{guia.gasto}</b>
          <span className="text-texto-suave"> de {guia.total} PB gastos · </span>
          <b className={passou ? 'text-perigo' : 'text-sucesso'}>
            {passou ? `${-guia.saldo} PB acima` : `sobram ${guia.saldo} PB`}
          </b>
        </p>
      </header>
      <div className="h-2 overflow-hidden rounded-full bg-superficie-2" role="img"
        aria-label={`${guia.gasto} de ${guia.total} Pontos de Batalha gastos`}>
        <div className={`h-full ${passou ? 'bg-perigo' : 'bg-esperanca'}`} style={{ width: `${proporcao}%` }} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Campo rotulo="PJs no combate" type="number" min={1} max={12} value={o.pjs} disabled={travado}
              onChange={(e) => Number(e.target.value) >= 1 && mudar({ pjs: Number(e.target.value) })} />
            <Selecao rotulo="Patamar do grupo" value={String(o.patamar)} disabled={travado}
              onChange={(e) => mudar({ patamar: Number(e.target.value) })}
              opcoes={[1, 2, 3, 4].map((p): [string, string] => [String(p), `Patamar ${p}`])} />
          </div>
          <p className="text-xs text-texto-suave">PB iniciais: 3 × {o.pjs} PJs + 2 = <b className="text-texto">{guia.base}</b></p>
          {escolha('Luta mais fácil ou curta', -1, !!o.mais_facil, 'mais_facil')}
          {escolha('+1d4 (ou +2) no dano de todos os adversários', -2, !!o.dano_extra, 'dano_extra')}
          {escolha('Luta mais difícil ou longa', 2, !!o.mais_dificil, 'mais_dificil')}
          {(guia.ajustes ?? []).filter((a) => a.automatico).map((a) => (
            <p key={a.descricao} className="flex justify-between text-sm text-texto-suave">
              <span>{a.descricao} <span className="text-xs">(automático)</span></span><span>{comSinal(a.valor)}</span>
            </p>
          ))}
          <p className="flex justify-between border-t border-borda pt-1 text-sm font-medium">
            <span>Total</span><span>{guia.total} PB</span>
          </p>
        </div>

        <div className="space-y-1 text-sm">
          <p className="text-xs uppercase tracking-wider text-texto-suave">Gastos</p>
          {(guia.gastos ?? []).length === 0 && <p className="text-texto-suave">Nenhum inimigo ainda.</p>}
          {(guia.gastos ?? []).map((g) => (
            <p key={g.tipo} className="flex justify-between">
              <span>{g.quantidade} {PLURAL_TIPO_ADVERSARIO[g.tipo]}
                {g.tipo === 'LACAIO' && <span className="text-xs text-texto-suave"> (grupos de {o.pjs})</span>}</span>
              <span>{g.custo} PB</span>
            </p>
          ))}
          <p className="pt-2 text-xs text-texto-suave">
            Custos: lacaios 1 por grupo do tamanho do grupo de PJs · manipulador e assistente 1 · horda, atirador,
            oportunista e comum 2 · líder 3 · brutamonte 4 · solo 5. É um guia: dá para gastar a mais ou a menos.
          </p>
        </div>
      </div>
      <Aviso erro={salvar.error} />
    </section>
  )
}
