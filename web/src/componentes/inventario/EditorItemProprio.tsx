// Formulário de item criado pelo mestre: os campos seguem o tipo (arma com dado
// e bônus de dano, armadura com limiares e pontuação, consumível com efeitos
// simples). Armas e armaduras têm características: copiadas do SRD (com bônus e
// regras especiais) ou criadas com texto e bônus fixos. Controlado: quem usa
// guarda o valor e decide quando salvar; as regras são do motor (erro da API).
import { useMemo, useState } from 'react'

import { useArmaduras, useArmas } from '../../api/consultas'
import type { Caracteristica, ItemProprio, Modificador, TipoProprio } from '../../api/tipos'
import { ALVOS_DE_BONUS, caracteristicasDoSrd, descreverBonus, itemEmBranco, NOME_TIPO_PROPRIO } from '../../lib/itens'
import { NOME_ALCANCE, NOME_TIPO_DANO, NOME_TRACO } from '../../lib/rotulos'
import { Area, Botao, Campo, Selecao } from '../ui'

const opcoes = (nomes: Record<string, string>): [string, string][] => Object.entries(nomes)
const numero = (v: string) => (v === '' ? 0 : Number(v))
const textoOuNulo = (v: string) => (v.trim() === '' ? null : v.trim())

const CATEGORIAS: [string, string][] = [
  ['PRIMARY_PHYSICAL', 'Principal física'], ['PRIMARY_MAGIC', 'Principal mágica'], ['SECONDARY', 'Secundária'],
]
const DADOS = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20']
const DICA_QUANTIDADE = 'Um número, um dado ("1d4+1") ou "tudo". Vazio: não faz.'

function Bonus({ lista, arma, aoMudar }: { lista: Modificador[]; arma: boolean; aoMudar: (l: Modificador[]) => void }) {
  const alvos = ALVOS_DE_BONUS.filter(([, , soArma]) => arma || !soArma)
  const mudar = (i: number, parcial: Partial<Modificador>) => aoMudar(lista.map((m, j) => (j === i ? { ...m, ...parcial } : m)))
  return (
    <div className="space-y-2">
      {lista.map((m, i) => m.igual_a ? (
        // "igual ao seu nível/atributo" (vem do SRD, ex.: Vinculada): fica como está
        <p key={i} className="text-xs text-texto-suave">Do SRD: {descreverBonus(m)}</p>
      ) : (
        <div key={i} className="flex flex-wrap items-end gap-2">
          <Selecao rotulo="Bônus em" className="min-w-40 flex-1" value={m.alvo}
            onChange={(e) => mudar(i, { alvo: e.target.value as Modificador['alvo'] })}
            opcoes={alvos.map(([a, nome]): [string, string] => [a, nome])} />
          <Campo rotulo="Valor" type="number" min={-10} max={10} className="w-20" value={m.valor}
            onChange={(e) => mudar(i, { valor: numero(e.target.value) })} />
          <Botao type="button" variante="fantasma" onClick={() => aoMudar(lista.filter((_, j) => j !== i))}>Tirar</Botao>
        </div>
      ))}
      <Botao type="button" variante="fantasma" onClick={() => aoMudar([...lista, { alvo: 'EVASAO', valor: 1 }])}>
        + Bônus na ficha
      </Botao>
    </div>
  )
}

function Caracteristicas({ valor, aoMudar }: { valor: ItemProprio; aoMudar: (l: Caracteristica[]) => void }) {
  const armas = useArmas()
  const armaduras = useArmaduras()
  const lista = valor.caracteristicas ?? []
  const arma = valor.tipo === 'ARMA'
  const doSrd = useMemo(() => caracteristicasDoSrd((arma ? armas.data : armaduras.data) ?? []), [arma, armas.data, armaduras.data])
  const [copiar, setCopiar] = useState('')
  const mudar = (i: number, parcial: Partial<Caracteristica>) => aoMudar(lista.map((c, j) => (j === i ? { ...c, ...parcial } : c)))

  return (
    <fieldset className="space-y-3">
      <legend className="font-medium">Características</legend>
      {lista.length === 0 && <p className="text-sm text-texto-suave">Nenhuma. Copie uma do SRD ou crie a sua.</p>}
      {lista.map((c, i) => (
        <div key={i} className="space-y-2 rounded-xl border border-borda p-3">
          <div className="grid gap-2 sm:grid-cols-[minmax(0,14rem)_1fr]">
            <Campo rotulo="Nome" value={c.nome} maxLength={120} required onChange={(e) => mudar(i, { nome: e.target.value })} />
            <Campo rotulo="Descrição" value={c.descricao} maxLength={2000} onChange={(e) => mudar(i, { descricao: e.target.value })} />
          </div>
          {(c.efeito || (c.requisitos ?? []).length > 0) && (
            <p className="text-xs text-texto-suave">Regra do SRD aplicada pelo motor (vem com a característica copiada).</p>
          )}
          <Bonus lista={c.modificadores ?? []} arma={arma} aoMudar={(modificadores) => mudar(i, { modificadores })} />
          <Botao type="button" variante="perigo" onClick={() => aoMudar(lista.filter((_, j) => j !== i))}>
            Tirar característica
          </Botao>
        </div>
      ))}
      <div className="flex flex-wrap items-end gap-2">
        <Selecao rotulo="Copiar do SRD" className="min-w-48 flex-1" value={copiar} onChange={(e) => setCopiar(e.target.value)}
          opcoes={[['', 'Escolha…'], ...doSrd.map((c, i): [string, string] => [String(i), `${c.nome}: ${c.descricao}`.slice(0, 90)])]} />
        <Botao type="button" variante="secundario" disabled={copiar === ''}
          onClick={() => { aoMudar([...lista, structuredClone(doSrd[Number(copiar)])]); setCopiar('') }}>
          Copiar
        </Botao>
        <Botao type="button" variante="secundario"
          onClick={() => aoMudar([...lista, { nome: '', descricao: '', modificadores: [], requisitos: [], nome_original: '' }])}>
          Criar característica
        </Botao>
      </div>
    </fieldset>
  )
}

export default function EditorItemProprio({ valor, aoMudar }: { valor: ItemProprio; aoMudar: (i: ItemProprio) => void }) {
  const mudar = (parcial: Partial<ItemProprio>) => aoMudar({ ...valor, ...parcial })
  const equipamento = valor.tipo === 'ARMA' || valor.tipo === 'ARMADURA'

  function mudarTipo(tipo: TipoProprio) {
    // troca os campos do tipo; nome e descrição ficam
    aoMudar({ ...itemEmBranco(tipo), id: valor.id, nome: valor.nome, descricao: valor.descricao })
  }

  return (
    <div className="space-y-5">
      <fieldset className="grid gap-3 sm:grid-cols-4">
        <legend className="sr-only">Identificação</legend>
        <Selecao rotulo="Tipo" value={valor.tipo} onChange={(e) => mudarTipo(e.target.value as TipoProprio)}
          opcoes={opcoes(NOME_TIPO_PROPRIO)} />
        <Campo rotulo="Nome" className="sm:col-span-2" value={valor.nome} maxLength={120} required
          onChange={(e) => mudar({ nome: e.target.value })} />
        {equipamento && (
          <Selecao rotulo="Patamar" value={String(valor.tier)} onChange={(e) => mudar({ tier: Number(e.target.value) })}
            opcoes={[1, 2, 3, 4].map((p): [string, string] => [String(p), `Patamar ${p}`])} />
        )}
        <Area rotulo="Descrição" className="sm:col-span-4" value={valor.descricao} maxLength={4000}
          onChange={(e) => mudar({ descricao: e.target.value })} />
      </fieldset>

      {valor.tipo === 'ARMA' && (
        <fieldset className="grid gap-3 sm:grid-cols-4">
          <legend className="mb-2 font-medium">Arma</legend>
          <Selecao rotulo="Categoria" value={valor.categoria} opcoes={CATEGORIAS}
            onChange={(e) => mudar({ categoria: e.target.value as ItemProprio['categoria'] })} />
          <Selecao rotulo="Atributo" value={valor.traco} opcoes={opcoes(NOME_TRACO)}
            onChange={(e) => mudar({ traco: e.target.value as ItemProprio['traco'] })} />
          <Selecao rotulo="Alcance" value={valor.alcance} opcoes={opcoes(NOME_ALCANCE)}
            onChange={(e) => mudar({ alcance: e.target.value })} />
          <Selecao rotulo="Tipo de dano" value={valor.tipo_dano} opcoes={opcoes(NOME_TIPO_DANO)}
            onChange={(e) => mudar({ tipo_dano: e.target.value as ItemProprio['tipo_dano'] })} />
          <Selecao rotulo="Dado de dano" value={valor.dado} opcoes={DADOS.map((d): [string, string] => [d, d])}
            onChange={(e) => mudar({ dado: e.target.value })} />
          <Campo rotulo="Bônus de dano" type="number" min={-10} max={20} value={valor.modificador_dano}
            dica="Somado ao dano (os dados são a Proficiência)." onChange={(e) => mudar({ modificador_dano: numero(e.target.value) })} />
          <label className="flex items-center gap-2 self-end pb-2 text-sm sm:col-span-2">
            <input type="checkbox" checked={valor.duas_maos} onChange={(e) => mudar({ duas_maos: e.target.checked })} />
            Duas mãos (sem arma secundária)
          </label>
        </fieldset>
      )}

      {valor.tipo === 'ARMADURA' && (
        <fieldset className="grid gap-3 sm:grid-cols-3">
          <legend className="mb-2 font-medium">Armadura</legend>
          <Campo rotulo="Limiar maior (base)" type="number" min={1} max={98} value={valor.limiar_maior}
            onChange={(e) => mudar({ limiar_maior: numero(e.target.value) })} />
          <Campo rotulo="Limiar grave (base)" type="number" min={2} max={99} value={valor.limiar_grave}
            onChange={(e) => mudar({ limiar_grave: numero(e.target.value) })} />
          <Campo rotulo="Pontuação de Armadura" type="number" min={0} max={12} value={valor.pontuacao}
            onChange={(e) => mudar({ pontuacao: numero(e.target.value) })} />
          <p className="text-xs text-texto-suave sm:col-span-3">A ficha soma o nível do personagem aos limiares.</p>
        </fieldset>
      )}

      {valor.tipo === 'CONSUMIVEL' && (
        <fieldset className="grid gap-3 sm:grid-cols-4">
          <legend className="mb-2 font-medium">Ao usar (aplicado na ficha)</legend>
          <Campo rotulo="Limpa PV" value={valor.limpa_pv ?? ''} placeholder="Ex.: 1d4+1"
            onChange={(e) => mudar({ limpa_pv: textoOuNulo(e.target.value) })} />
          <Campo rotulo="Limpa PF" value={valor.limpa_pf ?? ''} placeholder="Ex.: 2"
            onChange={(e) => mudar({ limpa_pf: textoOuNulo(e.target.value) })} />
          <Campo rotulo="Ganha Esperança" value={valor.ganha_esperanca ?? ''}
            onChange={(e) => mudar({ ganha_esperanca: textoOuNulo(e.target.value) })} />
          <Campo rotulo="Marca PF (custo)" type="number" min={0} max={6} value={valor.marca_pf}
            onChange={(e) => mudar({ marca_pf: numero(e.target.value) })} />
          <p className="text-xs text-texto-suave sm:col-span-4">{DICA_QUANTIDADE} No máximo um dado por consumível. O resto do efeito fica na descrição.</p>
          {valor.limpa_pv && valor.limpa_pf && (
            <label className="flex items-center gap-2 text-sm sm:col-span-4">
              <input type="checkbox" checked={valor.escolha} onChange={(e) => mudar({ escolha: e.target.checked })} />
              Quem usa escolhe: limpa PV <b>ou</b> PF
            </label>
          )}
        </fieldset>
      )}

      {equipamento && <Caracteristicas valor={valor} aoMudar={(caracteristicas) => mudar({ caracteristicas })} />}
    </div>
  )
}
