// Condições aplicadas (com botão para tirar) e o campo para aplicar uma
// nova: as três do SRD ou uma de característica, escrita à mão.
import { useState } from 'react'

import { condicao as nomeCondicao } from '../lib/rotulos'
import { Botao } from './ui'

const PADRAO = ['OCULTO', 'CONTIDO', 'VULNERAVEL']

export default function Condicoes({ condicoes, aoAplicar, aoTirar, desabilitado, rotulo, sem }: {
  condicoes: string[]; rotulo: string; desabilitado?: boolean
  aoAplicar?: (c: string) => void; aoTirar?: (c: string) => void
  /** Sem a lista: só o campo de aplicar, quando a lista já está à vista em outro lugar. */
  sem?: 'lista'
}) {
  const [escolha, setEscolha] = useState('')
  const [outra, setOutra] = useState('')
  const valor = escolha === 'outra' ? outra.trim() : escolha

  return (
    <div className="space-y-1.5">
      {sem !== 'lista' && <ul className="flex flex-wrap gap-1.5" aria-label={`Condições de ${rotulo}`}>
        {condicoes.length === 0 && <li className="text-xs text-texto-suave">Sem condições.</li>}
        {condicoes.map((c) => (
          <li key={c} className="inline-flex items-center gap-1 rounded-full bg-perigo/15 px-2.5 py-0.5 text-xs text-perigo">
            {nomeCondicao(c)}
            {aoTirar && (
              <button type="button" aria-label={`Tirar ${nomeCondicao(c)} de ${rotulo}`} disabled={desabilitado}
                onClick={() => aoTirar(c)} className="hover:text-texto max-sm:-my-1 max-sm:-mr-1 max-sm:p-2">✕</button>
            )}
          </li>
        ))}
      </ul>}
      {aoAplicar && (
        <form className="flex flex-wrap gap-1.5" onSubmit={(e) => {
          e.preventDefault()
          if (!valor) return
          aoAplicar(valor)
          setEscolha('')
          setOutra('')
        }}>
          <select value={escolha} onChange={(e) => setEscolha(e.target.value)} aria-label={`Nova condição para ${rotulo}`}
            className="rounded-lg border border-borda bg-fundo px-2 py-1 text-xs max-sm:min-h-11 max-sm:min-w-0 max-sm:flex-1">
            <option value="">Condição…</option>
            {PADRAO.filter((c) => !condicoes.includes(c)).map((c) => <option key={c} value={c}>{nomeCondicao(c)}</option>)}
            <option value="outra">Outra…</option>
          </select>
          {escolha === 'outra' && (
            <input value={outra} onChange={(e) => setOutra(e.target.value)} maxLength={60} placeholder="Ex.: Envolvido"
              aria-label="Nome da condição" className="w-32 rounded-lg border border-borda bg-fundo px-2 py-1 text-xs max-sm:min-h-11" />
          )}
          <Botao type="submit" variante="secundario" className="!px-2 !py-1 text-xs max-sm:min-h-11 max-sm:!px-4" disabled={desabilitado || !valor}>
            Aplicar
          </Botao>
        </form>
      )}
    </div>
  )
}
