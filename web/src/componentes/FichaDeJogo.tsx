// Os contadores mostram o que RESTA (como os espaços na ficha): "−" marca (perde)
// e "+" limpa (recupera); na Esperança, que mostra o que se tem, "+" ganha.
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
import { Abas, Aviso, Cartao, Espacos, Esperanca, useMudanca } from './ui'

/** Com `curto`, é um dos três fixos no celular: mostra só a sigla, o número e os botões. */
function Contador({ rotulo, detalhe, menos, mais, ocupado, children, curto, contagem, corDaContagem }: {
  rotulo: string; detalhe: string; ocupado: boolean
  curto?: string; contagem?: string; corDaContagem?: string
  menos?: { texto: string; acao: () => void; pode: boolean }
  mais?: { texto: string; acao: () => void; pode: boolean }
  children: React.ReactNode
}) {
  const mudanca = useMudanca(contagem)
  const botao = 'h-11 w-11 rounded-lg border border-borda-campo text-lg font-semibold hover:bg-superficie-2 disabled:border-borda disabled:text-texto-suave'
  // rótulo e espaços num bloco; os botões ao lado, no meio da altura dele (no
  // celular não ficam "soltos" acima da barra). Sem um dos botões, o lugar fica
  // reservado para os de todas as linhas ficarem na mesma coluna.
  return (
    <div className={`flex items-center gap-3 ${curto ? 'max-sm:flex-col max-sm:items-stretch max-sm:gap-1' : ''}`}>
      <div className="min-w-0 flex-1 space-y-1.5 max-sm:space-y-0">
        <p className={`text-sm ${curto ? 'max-sm:hidden' : ''}`}>{rotulo} <span className="text-texto-suave">({detalhe})</span></p>
        {curto && (
          <p aria-hidden className="flex items-baseline justify-between px-0.5 text-sm font-semibold sm:hidden">
            {curto} <span className={`font-titulo text-lg font-bold ${corDaContagem ?? ''} ${mudanca ? 'numero-muda' : ''}`}>{contagem}</span>
          </p>
        )}
        <div className={curto ? 'max-sm:hidden' : ''}>{children}</div>
      </div>
      <div className={`flex shrink-0 gap-1.5 ${curto ? 'max-sm:justify-between' : ''}`}>
        {menos ? (
          <button type="button" className={botao} aria-label={menos.texto} title={menos.texto}
            disabled={ocupado || !menos.pode} onClick={menos.acao}>−</button>
        ) : <span aria-hidden className="w-11" />}
        {mais ? (
          <button type="button" className={botao} aria-label={mais.texto} title={mais.texto}
            disabled={ocupado || !mais.pode} onClick={mais.acao}>+</button>
        ) : <span aria-hidden className="w-11" />}
      </div>
    </div>
  )
}

/** PV, Fadiga e Esperança, o que mais muda em jogo: no celular ficam sempre à mão,
    logo acima do menu. Com `soCelular`, não aparecem no computador (na rolagem, onde
    a ficha não está na tela). O erro fica junto, senão não seria visto ao rolar a página. */
export function MarcasPrincipais({ personagemId, ficha: f, soCelular }: { personagemId: string; ficha: Ficha; soCelular?: boolean }) {
  const marcar = useMarcarNaSessao(personagemId)
  const fazer = (m: MarcaDeJogo) => () => marcar.mutate(m)
  const ocupado = marcar.isPending || f.morto
  return (
    <div aria-label="Marcas da sessão" role="group" data-marcas-fixas
      className={`space-y-4 max-sm:!mb-0 max-sm:fixed max-sm:inset-x-0 max-sm:bottom-14 max-sm:z-20 max-sm:grid max-sm:grid-cols-3 max-sm:gap-2 max-sm:space-y-0 max-sm:border-t max-sm:border-borda max-sm:bg-superficie max-sm:p-2 ${soCelular ? 'sm:hidden' : ''}`}>
      <Contador rotulo="Pontos de Vida" detalhe={`restam ${f.pv_max - f.pv_marcados}/${f.pv_max}`} ocupado={ocupado}
        curto="PV" contagem={`${f.pv_max - f.pv_marcados}/${f.pv_max}`} corDaContagem="text-pv"
        menos={{ texto: 'Marcar 1 PV', acao: fazer({ tipo: 'pv', acao: 'marcar', quantidade: 1 }), pode: f.pv_marcados < f.pv_max }}
        mais={{ texto: 'Limpar 1 PV', acao: fazer({ tipo: 'pv', acao: 'limpar', quantidade: 1 }), pode: f.pv_marcados > 0 }}>
        <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo="Pontos de Vida" restantes />
      </Contador>
      <Contador rotulo="Fadiga" detalhe={`restam ${f.estresse_max - f.estresse_marcado}/${f.estresse_max}`} ocupado={ocupado}
        curto="PF" contagem={`${f.estresse_max - f.estresse_marcado}/${f.estresse_max}`} corDaContagem="text-fadiga"
        menos={{ texto: 'Marcar 1 PF', acao: fazer({ tipo: 'estresse', acao: 'marcar', quantidade: 1 }), pode: f.estresse_marcado < f.estresse_max }}
        mais={{ texto: 'Limpar 1 PF', acao: fazer({ tipo: 'estresse', acao: 'limpar', quantidade: 1 }), pode: f.estresse_marcado > 0 }}>
        <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo="Fadiga" cor="fadiga" restantes />
      </Contador>
      <Contador rotulo="Esperança" detalhe={`${f.esperanca}/${f.esperanca_max}`} ocupado={ocupado}
        curto="Esperança" contagem={`${f.esperanca}/${f.esperanca_max}`} corDaContagem="text-esperanca"
        menos={{ texto: 'Gastar 1 de Esperança', acao: fazer({ tipo: 'esperanca', acao: 'gastar', quantidade: 1 }), pode: f.esperanca > 0 }}
        mais={{ texto: 'Ganhar 1 de Esperança', acao: fazer({ tipo: 'esperanca', acao: 'ganhar', quantidade: 1 }), pode: f.esperanca < f.esperanca_max }}>
        <Esperanca atual={f.esperanca} maximo={f.esperanca_max} />
      </Contador>
      <div className="max-sm:col-span-3"><Aviso erro={marcar.error} /></div>
    </div>
  )
}

/** O cartão "Vida e Fadiga" com os controles de jogo. */
export function MarcasDeJogo({ personagemId, ficha: f }: { personagemId: string; ficha: Ficha }) {
  const marcar = useMarcarNaSessao(personagemId)
  const fazer = (m: MarcaDeJogo) => () => marcar.mutate(m)
  const ocupado = marcar.isPending || f.morto
  const livresArmadura = f.pontuacao_armadura - f.armadura_marcada

  return (
    <div className="space-y-4">
      <MarcasPrincipais personagemId={personagemId} ficha={f} />
      {f.pontuacao_armadura > 0 && (
        <Contador rotulo="Armadura" detalhe={`livres ${livresArmadura}/${f.pontuacao_armadura}`} ocupado={ocupado}
          menos={{ texto: 'Marcar 1 espaço de armadura', acao: fazer({ tipo: 'armadura', quantidade: 1 }), pode: livresArmadura > 0 }}>
          <Espacos total={f.pontuacao_armadura} marcados={f.armadura_marcada} rotulo="Armadura" cor="armadura" restantes />
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
          detalhe={f.companheiro.fora_de_cena ? 'fora de cena'
            : `restam ${f.companheiro.estresse_max - f.companheiro.estresse_marcado}/${f.companheiro.estresse_max}`}
          ocupado={ocupado}
          menos={{ texto: `${f.companheiro.nome} sofre dano (marca 1 PF)`, acao: fazer({ tipo: 'companheiro' }),
            pode: !f.companheiro.fora_de_cena }}>
          <Espacos total={f.companheiro.estresse_max} marcados={f.companheiro.estresse_marcado}
            rotulo={`Fadiga de ${f.companheiro.nome}`} cor="fadiga" restantes />
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
