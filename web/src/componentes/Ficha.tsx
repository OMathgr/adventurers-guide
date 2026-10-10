// Visão "ficha": tudo o que o personagem é agora, como na ficha de papel.
import type { Ficha } from '../api/tipos'
import { useNomes } from '../lib/nomes'
import {
  comSinal, dominio, NOME_ALCANCE, NOME_TIPO_DANO, NOME_TRACO, TRACOS, USO_TRACO,
} from '../lib/rotulos'
import { Cartao, Espacos, Esperanca, Selo } from './ui'

function Numero({ rotulo, valor, detalhe }: { rotulo: string; valor: string | number; detalhe?: string }) {
  return (
    <div className="rounded-xl border border-borda bg-fundo/60 p-3 text-center">
      <p className="text-xs uppercase tracking-wider text-texto-suave">{rotulo}</p>
      <p className="font-titulo text-2xl text-texto">{valor}</p>
      {detalhe && <p className="text-xs text-texto-suave">{detalhe}</p>}
    </div>
  )
}

function ListaCaracteristicas({ lista }: { lista: { nome: string; descricao: string }[] }) {
  return (
    <ul className="space-y-1.5 text-sm">
      {lista.map((c) => (
        <li key={c.nome}><span className="font-semibold">{c.nome}:</span>{' '}
          <span className="text-texto-suave">{c.descricao}</span></li>
      ))}
    </ul>
  )
}

export default function FichaVisao({ ficha }: { ficha: Ficha }) {
  const nomes = useNomes(ficha)

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Cartao titulo="Traços" className="lg:col-span-2">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {TRACOS.map((t) => (
            <div key={t} className="rounded-xl border border-borda bg-fundo/60 p-3">
              <div className="flex items-baseline justify-between">
                <span className="font-semibold">{NOME_TRACO[t]}</span>
                <span className="font-titulo text-2xl text-esperanca">{comSinal(ficha.tracos[t] ?? 0)}</span>
              </div>
              <p className="text-xs text-texto-suave">{USO_TRACO[t]}</p>
              {ficha.tracos_marcados.includes(t) && <p className="mt-1 text-xs text-medo">marcado neste tier</p>}
            </div>
          ))}
        </div>
      </Cartao>

      <Cartao titulo="Defesa">
        <div className="grid grid-cols-2 gap-2">
          <Numero rotulo="Evasão" valor={ficha.evasao} />
          <Numero rotulo="Armadura" valor={ficha.pontuacao_armadura} detalhe={ficha.armadura ?? 'sem armadura'} />
        </div>
        <div className="mt-3 flex items-center justify-between gap-1 text-center text-xs">
          <span className="text-texto-suave">Menor</span>
          <span className="rounded bg-superficie-2 px-2 py-1 font-titulo text-base">{ficha.limiar_maior}</span>
          <span className="text-texto-suave">Maior</span>
          <span className="rounded bg-superficie-2 px-2 py-1 font-titulo text-base">{ficha.limiar_grave}</span>
          <span className="text-texto-suave">Grave</span>
        </div>
        {ficha.pontuacao_armadura > 0 && (
          <div className="mt-3"><p className="mb-1 text-xs text-texto-suave">Espaços de armadura</p>
            <Espacos total={ficha.pontuacao_armadura} marcados={ficha.armadura_marcada} rotulo="Armadura" cor="medo" /></div>
        )}
      </Cartao>

      <Cartao titulo="Vida e ânimo" className="lg:col-span-2">
        <div className="space-y-3">
          <div><p className="mb-1 text-sm">Pontos de Vida <span className="text-texto-suave">({ficha.pv_marcados}/{ficha.pv_max})</span></p>
            <Espacos total={ficha.pv_max} marcados={ficha.pv_marcados} rotulo="Pontos de Vida" cor="perigo" /></div>
          <div><p className="mb-1 text-sm">Estresse <span className="text-texto-suave">({ficha.estresse_marcado}/{ficha.estresse_max})</span></p>
            <Espacos total={ficha.estresse_max} marcados={ficha.estresse_marcado} rotulo="Estresse" cor="medo" /></div>
          <div><p className="mb-1.5 text-sm">Esperança <span className="text-texto-suave">({ficha.esperanca}/{ficha.esperanca_max})</span></p>
            <Esperanca atual={ficha.esperanca} maximo={ficha.esperanca_max} /></div>
          {ficha.condicoes.length > 0 && (
            <p className="flex flex-wrap gap-1.5">{ficha.condicoes.map((c) => <Selo key={c} destaque>{c}</Selo>)}</p>
          )}
        </div>
      </Cartao>

      <Cartao titulo="Experiências">
        <ul className="space-y-1">
          {Object.entries(ficha.experiencias).map(([nome, valor]) => (
            <li key={nome} className="flex justify-between text-sm">
              <span>{nome}</span><span className="font-semibold text-esperanca">{comSinal(valor)}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-texto-suave">Proficiência {ficha.proficiencia}</p>
      </Cartao>

      <Cartao titulo="Ataques" className="lg:col-span-2">
        {ficha.ataques.length === 0 && <p className="text-sm text-texto-suave">Nenhuma arma equipada.</p>}
        <ul className="space-y-3">
          {ficha.ataques.map((a) => (
            <li key={a.arma} className="rounded-xl border border-borda bg-fundo/60 p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-titulo text-lg">{a.arma}</span>
                <span className="text-sm"><b className="text-esperanca">{comSinal(a.bonus)}</b> {NOME_TRACO[a.traco]} ·{' '}
                  <b>{a.dano}</b> {NOME_TIPO_DANO[a.tipo_dano]} · {NOME_ALCANCE[a.alcance] ?? a.alcance}</span>
              </div>
              {(a.caracteristicas ?? []).length > 0 && <div className="mt-2"><ListaCaracteristicas lista={a.caracteristicas ?? []} /></div>}
            </li>
          ))}
        </ul>
      </Cartao>

      <Cartao titulo="Conjuração">
        {ficha.conjuracoes.length === 0
          ? <p className="text-sm text-texto-suave">Sua subclasse não conjura.</p>
          : <ul className="space-y-1 text-sm">{ficha.conjuracoes.map((c) => (
            <li key={c.subclasse} className="flex justify-between"><span>{c.subclasse} · {NOME_TRACO[c.traco]}</span>
              <b className="text-esperanca">{comSinal(c.bonus)}</b></li>))}</ul>}
      </Cartao>

      <Cartao titulo={`Cartas de domínio (${ficha.cartas_ativas.length} ativas)`} className="lg:col-span-3">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {[...ficha.cartas_ativas.map((id) => ({ id, cofre: false })), ...ficha.cartas_cofre.map((id) => ({ id, cofre: true }))]
            .map(({ id, cofre }) => {
              const carta = nomes.carta(id)
              return (
                <details key={id} className={`rounded-xl border border-borda bg-fundo/60 p-3 ${cofre ? 'opacity-60' : ''}`}>
                  <summary className="cursor-pointer list-none">
                    <span className="font-titulo">{carta?.nome ?? id}</span>
                    <span className="mt-1 flex flex-wrap gap-1.5">
                      {carta && <Selo>{dominio(carta.dominio)} · nível {carta.nivel}</Selo>}
                      {cofre && <Selo>no cofre</Selo>}
                    </span>
                  </summary>
                  {carta && <p className="mt-2 whitespace-pre-line text-sm text-texto-suave">{carta.texto}</p>}
                </details>
              )
            })}
        </div>
      </Cartao>

      <Cartao titulo="Ancestralidade" className="lg:col-span-2">
        <ListaCaracteristicas lista={ficha.caracteristicas_ancestralidade} />
        {ficha.caracteristicas_armadura.length > 0 && (
          <><h3 className="mb-1 mt-4 text-sm text-esperanca">{ficha.armadura}</h3>
            <ListaCaracteristicas lista={ficha.caracteristicas_armadura} /></>
        )}
      </Cartao>

      {ficha.companheiro && (
        <Cartao titulo={`Companheiro: ${ficha.companheiro.nome}`}>
          <div className="grid grid-cols-2 gap-2">
            <Numero rotulo="Evasão" valor={ficha.companheiro.evasao} />
            <Numero rotulo="Dano" valor={ficha.companheiro.dano}
              detalhe={NOME_ALCANCE[ficha.companheiro.alcance] ?? ficha.companheiro.alcance} />
          </div>
          <p className="mb-1 mt-3 text-sm">Estresse</p>
          <Espacos total={ficha.companheiro.estresse_max} marcados={ficha.companheiro.estresse_marcado}
            rotulo="Estresse do companheiro" cor="medo" />
          <ul className="mt-3 space-y-1 text-sm">
            {Object.entries(ficha.companheiro.experiencias).map(([nome, v]) => (
              <li key={nome} className="flex justify-between"><span>{nome}</span><b className="text-esperanca">{comSinal(v)}</b></li>
            ))}
          </ul>
          {ficha.companheiro.fora_de_cena && <p className="mt-2 text-sm text-perigo">Fora de cena até o próximo descanso longo.</p>}
        </Cartao>
      )}
    </div>
  )
}
