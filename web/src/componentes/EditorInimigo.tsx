// Formulário de adversário (inimigo da mesa ou ficha de combate de NPC).
// Controlado: quem usa guarda o valor e decide quando salvar. A validação
// das regras (limiares, dano, ataque...) é do motor; a tela mostra o erro da API.
import { useState } from 'react'

import type { Adversario, Habilidade, TipoAdversario, TipoDano, TipoHabilidade } from '../api/tipos'
import {
  NOME_ALCANCE, NOME_TIPO_ADVERSARIO, NOME_TIPO_DANO, NOME_TIPO_HABILIDADE, TIPOS_ADVERSARIO,
} from '../lib/rotulos'
import { Area, Botao, Campo, Selecao } from './ui'

const HABILIDADE_EM_BRANCO: Habilidade = { nome: '', tipo: 'PASSIVA', texto: '', detalhe: '', nome_original: '' }

const opcoes = <T extends string>(nomes: Record<T, string>, ordem?: T[]): [string, string][] =>
  (ordem ?? (Object.keys(nomes) as T[])).map((k) => [k, nomes[k]])

const numero = (v: string) => (v === '' ? 0 : Number(v))

export default function EditorInimigo({ valor, aoMudar, nomeOpcional }:
  { valor: Adversario; aoMudar: (a: Adversario) => void; nomeOpcional?: boolean }) {
  const mudar = (parcial: Partial<Adversario>) => aoMudar({ ...valor, ...parcial })
  // experiências: lista local para o nome poder ser editado sem perder a linha
  const [exps, setExps] = useState<[string, number][]>(() => Object.entries(valor.experiencias ?? {}))
  const habilidades = valor.habilidades ?? []

  function mudarExps(novas: [string, number][]) {
    setExps(novas)
    mudar({ experiencias: Object.fromEntries(novas.filter(([n]) => n.trim()).map(([n, v]) => [n.trim(), v])) })
  }

  function mudarTipo(tipo: TipoAdversario) {
    const parcial: Partial<Adversario> = { tipo }
    if (tipo === 'LACAIO') Object.assign(parcial, { limiar_maior: null, limiar_grave: null })
    else if (valor.limiar_maior == null) Object.assign(parcial, { limiar_maior: 6, limiar_grave: 11 })
    parcial.horda_por_pv = tipo === 'HORDA' ? (valor.horda_por_pv ?? 2) : null
    mudar(parcial)
  }

  const mudarHabilidade = (i: number, parcial: Partial<Habilidade>) =>
    mudar({ habilidades: habilidades.map((h, j) => (j === i ? { ...h, ...parcial } : h)) })

  function moverHabilidade(i: number, delta: number) {
    const lista = [...habilidades]
    ;[lista[i], lista[i + delta]] = [lista[i + delta], lista[i]]
    mudar({ habilidades: lista })
  }

  return (
    <div className="space-y-5">
      <fieldset className="grid gap-3 sm:grid-cols-4">
        <legend className="sr-only">Identificação</legend>
        <Campo rotulo="Nome" className="sm:col-span-2" value={valor.nome} maxLength={120}
          required={!nomeOpcional} placeholder={nomeOpcional ? 'Igual ao do NPC' : undefined}
          onChange={(e) => mudar({ nome: e.target.value })} />
        <Selecao rotulo="Patamar" value={String(valor.patamar)} opcoes={[1, 2, 3, 4].map((p) => [String(p), `Patamar ${p}`])}
          onChange={(e) => mudar({ patamar: Number(e.target.value) })} />
        <Selecao rotulo="Tipo" value={valor.tipo} opcoes={opcoes(NOME_TIPO_ADVERSARIO, TIPOS_ADVERSARIO)}
          onChange={(e) => mudarTipo(e.target.value as TipoAdversario)} />
        <Area rotulo="Descrição" className="sm:col-span-4" rows={2} value={valor.descricao}
          onChange={(e) => mudar({ descricao: e.target.value })} />
        <Area rotulo="Motivações e táticas" className="sm:col-span-4" rows={2} value={valor.motivacoes}
          onChange={(e) => mudar({ motivacoes: e.target.value })} />
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3 sm:grid-cols-6">
        <legend className="mb-2 text-sm text-esperanca">Números</legend>
        <Campo rotulo="Dificuldade" type="number" min={1} value={valor.dificuldade}
          onChange={(e) => mudar({ dificuldade: numero(e.target.value) })} />
        <Campo rotulo="PV" type="number" min={1} value={valor.pv} onChange={(e) => mudar({ pv: numero(e.target.value) })} />
        <Campo rotulo="PF" type="number" min={0} value={valor.pf} onChange={(e) => mudar({ pf: numero(e.target.value) })} />
        {valor.tipo !== 'LACAIO' && <>
          <Campo rotulo="Limiar Maior" type="number" min={1} value={valor.limiar_maior ?? ''}
            onChange={(e) => mudar({ limiar_maior: numero(e.target.value) })} />
          <Campo rotulo="Limiar Grave" type="number" min={1} value={valor.limiar_grave ?? ''}
            dica="Vazio: sem limiar Grave"
            onChange={(e) => mudar({ limiar_grave: e.target.value === '' ? null : Number(e.target.value) })} />
        </>}
        {valor.tipo === 'HORDA' && (
          <Campo rotulo="Integrantes por PV" type="number" min={1} value={valor.horda_por_pv ?? ''}
            onChange={(e) => mudar({ horda_por_pv: e.target.value === '' ? null : Number(e.target.value) })} />
        )}
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <legend className="mb-2 text-sm text-esperanca">Ataque padrão</legend>
        <Campo rotulo="Modificador" value={valor.ataque} placeholder="+2" dica="Ex.: +3 ou +1d4"
          onChange={(e) => mudar({ ataque: e.target.value })} />
        <Campo rotulo="Arma" className="col-span-2 sm:col-span-1" value={valor.arma}
          onChange={(e) => mudar({ arma: e.target.value })} />
        <Selecao rotulo="Alcance" value={valor.alcance} opcoes={opcoes(NOME_ALCANCE)}
          onChange={(e) => mudar({ alcance: e.target.value })} />
        <Campo rotulo="Dano" value={valor.dano} placeholder="1d8+2" onChange={(e) => mudar({ dano: e.target.value })} />
        <Selecao rotulo="Tipo de dano" value={valor.tipo_dano} opcoes={opcoes(NOME_TIPO_DANO)}
          onChange={(e) => mudar({ tipo_dano: e.target.value as TipoDano })} />
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm text-esperanca">Experiências</legend>
        {exps.map(([nome, bonus], i) => (
          <div key={i} className="flex items-end gap-2">
            <Campo rotulo="Experiência" className="flex-1" value={nome}
              onChange={(e) => mudarExps(exps.map((x, j) => (j === i ? [e.target.value, x[1]] : x)))} />
            <Campo rotulo="Bônus" type="number" className="w-24" value={bonus}
              onChange={(e) => mudarExps(exps.map((x, j) => (j === i ? [x[0], numero(e.target.value)] : x)))} />
            <Botao type="button" variante="fantasma" aria-label={`Remover experiência ${i + 1}`}
              onClick={() => mudarExps(exps.filter((_, j) => j !== i))}>✕</Botao>
          </div>
        ))}
        <Botao type="button" variante="secundario" onClick={() => mudarExps([...exps, ['', 2]])}>
          Adicionar experiência
        </Botao>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className="mb-2 text-sm text-esperanca">Características</legend>
        {habilidades.map((h, i) => (
          <div key={i} className="space-y-2 rounded-xl border border-borda p-3">
            <div className="grid gap-2 sm:grid-cols-4">
              <Campo rotulo="Nome" className="sm:col-span-2" value={h.nome}
                onChange={(e) => mudarHabilidade(i, { nome: e.target.value })} />
              <Selecao rotulo="Tipo" value={h.tipo} opcoes={opcoes(NOME_TIPO_HABILIDADE)}
                onChange={(e) => mudarHabilidade(i, { tipo: e.target.value as TipoHabilidade })} />
              <Campo rotulo="Detalhe" value={h.detalhe} placeholder="Contagem Regressiva (4)"
                onChange={(e) => mudarHabilidade(i, { detalhe: e.target.value })} />
            </div>
            <Area rotulo="Texto" value={h.texto} dica="**negrito** e _itálico_ funcionam como no SRD."
              onChange={(e) => mudarHabilidade(i, { texto: e.target.value })} />
            <div className="flex justify-end gap-1">
              <Botao type="button" variante="fantasma" disabled={i === 0} aria-label="Subir característica"
                onClick={() => moverHabilidade(i, -1)}>↑</Botao>
              <Botao type="button" variante="fantasma" disabled={i === habilidades.length - 1}
                aria-label="Descer característica" onClick={() => moverHabilidade(i, 1)}>↓</Botao>
              <Botao type="button" variante="perigo"
                onClick={() => mudar({ habilidades: habilidades.filter((_, j) => j !== i) })}>Remover</Botao>
            </div>
          </div>
        ))}
        <Botao type="button" variante="secundario"
          onClick={() => mudar({ habilidades: [...habilidades, { ...HABILIDADE_EM_BRANCO }] })}>
          Adicionar característica
        </Botao>
      </fieldset>
    </div>
  )
}
