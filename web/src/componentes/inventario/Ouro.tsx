// Ouro como na ficha de papel: 9 punhados, 9 bolsas e 1 baú. Ganhar e gastar
// mandam o valor em punhados; quem sobe de punhado para bolsa (ou recusa
// passar de 1 baú) é o motor.
import { useState } from 'react'

import type { Ouro } from '../../api/tipos'
import { EM_MOEDAS, formatarOuro, type Moeda, separar } from '../../lib/ouro'
import { Botao } from '../ui'

/** Quadradinhos menores que os de PV: os 9 cabem numa linha no celular. */
function Marcas({ total, marcados, rotulo }: { total: number; marcados: number; rotulo: string }) {
  return (
    <span className="flex gap-1" role="img" aria-label={`${rotulo}: ${marcados} de ${total}`}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={`h-4 w-4 rounded-sm border border-borda ${i < marcados ? 'bg-esperanca' : ''}`} />
      ))}
    </span>
  )
}

export function OuroNaFicha({ ouro, usaMoedas }: { ouro: Ouro; usaMoedas?: boolean }) {
  const moedas = usaMoedas ? ouro.moedas ?? 0 : 0
  return (
    <div className="space-y-1.5 text-sm" aria-label={`Ouro: ${formatarOuro(ouro.total, moedas)}`}>
      <div className="grid grid-cols-[5rem_1fr] items-center gap-2">
        {usaMoedas && <><span className="text-texto-suave">Moedas</span><Marcas total={9} marcados={moedas} rotulo="Moedas" /></>}
        <span className="text-texto-suave">Punhados</span><Marcas total={9} marcados={ouro.punhados} rotulo="Punhados" />
        <span className="text-texto-suave">Bolsas</span><Marcas total={9} marcados={ouro.bolsas} rotulo="Bolsas" />
        <span className="text-texto-suave">Baú</span><Marcas total={1} marcados={ouro.baus} rotulo="Baú" />
      </div>
      <p className="text-xs text-texto-suave">{formatarOuro(ouro.total, moedas)}</p>
    </div>
  )
}

/** Ganhar ou gastar ouro. `aoMudar` recebe { punhados, moedas } (negativos = gastar). */
export function MudarOuro({ aoMudar, ocupado, usaMoedas, rotulos = ['Ganhar', 'Gastar'] }: {
  aoMudar: (valor: { punhados: number; moedas: number }) => void; ocupado?: boolean; usaMoedas?: boolean
  rotulos?: [string, string]
}) {
  const [quantidade, setQuantidade] = useState('1')
  const [escolhida, setMoeda] = useState<Moeda>('punhados')
  const moeda = !usaMoedas && escolhida === 'moedas' ? 'punhados' : escolhida
  const n = Number(quantidade)
  const valido = Number.isInteger(n) && n > 0
  const valor = valido ? n * EM_MOEDAS[moeda] : 0

  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-texto-suave">Quantidade</span>
        <input type="number" min={1} value={quantidade} onChange={(e) => setQuantidade(e.target.value)}
          className="w-20 rounded-lg border border-borda bg-fundo px-3 py-2 text-sm" />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-texto-suave">De</span>
        <select value={moeda} onChange={(e) => setMoeda(e.target.value as Moeda)}
          className="rounded-lg border border-borda bg-fundo px-3 py-2 text-sm">
          {usaMoedas && <option value="moedas">moedas</option>}
          <option value="punhados">punhados</option>
          <option value="bolsas">bolsas</option>
          <option value="baus">baús</option>
        </select>
      </label>
      <Botao variante="secundario" disabled={!valido || ocupado} onClick={() => aoMudar(separar(valor))}>{rotulos[0]}</Botao>
      <Botao variante="secundario" disabled={!valido || ocupado} onClick={() => aoMudar(separar(-valor))}>{rotulos[1]}</Botao>
    </div>
  )
}
