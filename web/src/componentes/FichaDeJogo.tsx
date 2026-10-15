// A ficha do jogador dentro da sessão em andamento: marcar e limpar PV e
// Fadiga, ganhar e gastar Esperança, marcar armadura, condições, o companheiro,
// o movimento de morte e a mão de cartas. As marcas são desta sessão (cada
// sessão começa limpa); quem confere as regras (limites, custo sem espaço) é o motor.
import { useState } from 'react'

import { type MarcaDeJogo, useMarcarNaSessao } from '../api/consultas'
import type { Ficha } from '../api/tipos'
import Condicoes from './Condicoes'
import FichaVisao from './Ficha'
import AbaInventario from './inventario/AbaInventario'
import Morte from './Morte'
import { Abas, Aviso, Cartao, Espacos, Esperanca } from './ui'

function Contador({ rotulo, detalhe, menos, mais, ocupado, children }: {
  rotulo: string; detalhe: string; ocupado: boolean
  menos?: { texto: string; acao: () => void; pode: boolean }
  mais?: { texto: string; acao: () => void; pode: boolean }
  children: React.ReactNode
}) {
  const botao = 'h-9 min-w-9 rounded-lg border border-borda px-2 text-sm font-semibold hover:bg-superficie-2 disabled:opacity-40'
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm">{rotulo} <span className="text-texto-suave">({detalhe})</span></p>
        <div className="flex gap-1.5">
          {menos && (
            <button type="button" className={botao} aria-label={menos.texto} title={menos.texto}
              disabled={ocupado || !menos.pode} onClick={menos.acao}>−</button>
          )}
          {mais && (
            <button type="button" className={botao} aria-label={mais.texto} title={mais.texto}
              disabled={ocupado || !mais.pode} onClick={mais.acao}>+</button>
          )}
        </div>
      </div>
      {children}
    </div>
  )
}

/** O cartão "Vida e ânimo" com os controles de jogo. */
export function MarcasDeJogo({ personagemId, ficha: f }: { personagemId: string; ficha: Ficha }) {
  const marcar = useMarcarNaSessao(personagemId)
  const fazer = (m: MarcaDeJogo) => () => marcar.mutate(m)
  const ocupado = marcar.isPending || f.morto
  const livresArmadura = f.pontuacao_armadura - f.armadura_marcada

  return (
    <div className="space-y-4">
      <Contador rotulo="Pontos de Vida" detalhe={`restam ${f.pv_max - f.pv_marcados}/${f.pv_max}`} ocupado={ocupado}
        menos={{ texto: 'Limpar 1 PV', acao: fazer({ tipo: 'pv', acao: 'limpar', quantidade: 1 }), pode: f.pv_marcados > 0 }}
        mais={{ texto: 'Marcar 1 PV', acao: fazer({ tipo: 'pv', acao: 'marcar', quantidade: 1 }), pode: f.pv_marcados < f.pv_max }}>
        <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo="Pontos de Vida" restantes />
      </Contador>
      <Contador rotulo="Fadiga" detalhe={`restam ${f.estresse_max - f.estresse_marcado}/${f.estresse_max}`} ocupado={ocupado}
        menos={{ texto: 'Limpar 1 PF', acao: fazer({ tipo: 'estresse', acao: 'limpar', quantidade: 1 }), pode: f.estresse_marcado > 0 }}
        mais={{ texto: 'Marcar 1 PF', acao: fazer({ tipo: 'estresse', acao: 'marcar', quantidade: 1 }), pode: f.estresse_marcado < f.estresse_max }}>
        <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo="Fadiga" cor="medo" restantes />
      </Contador>
      <Contador rotulo="Esperança" detalhe={`${f.esperanca}/${f.esperanca_max}`} ocupado={ocupado}
        menos={{ texto: 'Gastar 1 de Esperança', acao: fazer({ tipo: 'esperanca', acao: 'gastar', quantidade: 1 }), pode: f.esperanca > 0 }}
        mais={{ texto: 'Ganhar 1 de Esperança', acao: fazer({ tipo: 'esperanca', acao: 'ganhar', quantidade: 1 }), pode: f.esperanca < f.esperanca_max }}>
        <Esperanca atual={f.esperanca} maximo={f.esperanca_max} />
      </Contador>
      {f.pontuacao_armadura > 0 && (
        <Contador rotulo="Armadura" detalhe={`livres ${livresArmadura}/${f.pontuacao_armadura}`} ocupado={ocupado}
          mais={{ texto: 'Marcar 1 espaço de armadura', acao: fazer({ tipo: 'armadura', quantidade: 1 }), pode: livresArmadura > 0 }}>
          <Espacos total={f.pontuacao_armadura} marcados={f.armadura_marcada} rotulo="Armadura" cor="medo" restantes />
          <p className="text-xs text-texto-suave">Para reduzir dano, use "usar armadura" quando o mestre aplicar; espaços voltam no descanso.</p>
        </Contador>
      )}
      <div className="space-y-1.5">
        <p className="text-sm">Condições</p>
        <Condicoes rotulo={f.nome || 'você'} condicoes={f.condicoes} desabilitado={ocupado}
          aoAplicar={(condicao) => marcar.mutate({ tipo: 'condicao', condicao })}
          aoTirar={(condicao) => marcar.mutate({ tipo: 'condicao', condicao, tirar: true })} />
      </div>
      {f.companheiro && (
        <Contador rotulo={`Fadiga de ${f.companheiro.nome}`}
          detalhe={f.companheiro.fora_de_cena ? 'fora de cena' : `${f.companheiro.estresse_marcado}/${f.companheiro.estresse_max}`}
          ocupado={ocupado}
          mais={{ texto: `${f.companheiro.nome} sofre dano (marca 1 PF)`, acao: fazer({ tipo: 'companheiro' }),
            pode: !f.companheiro.fora_de_cena }}>
          <Espacos total={f.companheiro.estresse_max} marcados={f.companheiro.estresse_marcado}
            rotulo={`Fadiga de ${f.companheiro.nome}`} cor="medo" restantes />
        </Contador>
      )}
      <Aviso erro={marcar.error} />
    </div>
  )
}

type Parte = 'ficha' | 'inventario'

/** A ficha completa em jogo: morte, as marcas no topo (é o que mais muda), a ficha, a mão e o inventário. */
export default function FichaDeJogo({ personagemId, ficha }: { personagemId: string; ficha: Ficha }) {
  const [parte, setParte] = useState<Parte>('ficha')
  return (
    <div className="space-y-4">
      <Morte personagemId={personagemId} ficha={ficha} />
      <Cartao titulo={`${ficha.nome || 'Personagem'} nesta sessão`}>
        <MarcasDeJogo personagemId={personagemId} ficha={ficha} />
      </Cartao>
      <Abas<Parte> atual={parte} aoTrocar={setParte} abas={[['ficha', 'Ficha'], ['inventario', 'Inventário']]} />
      {parte === 'ficha' && (
        <FichaVisao ficha={ficha} personagemId={personagemId} semVida />
      )}
      {parte === 'inventario' && <AbaInventario personagemId={personagemId} ficha={ficha} />}
    </div>
  )
}
