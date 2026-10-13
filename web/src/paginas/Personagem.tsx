// Página do personagem: foto, mesa, e as visões ficha, equipamento, inventário e linha do tempo.
import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

import {
  useApagarPersonagem, useCopiarParaMesa, useDesfazerNivel, useFicha, useFotoDoPersonagem, useLinhaDoTempo,
  useMesas, usePersonagens,
} from '../api/consultas'
import AbaEquipamento from '../componentes/AbaEquipamento'
import FichaVisao from '../componentes/Ficha'
import AbaInventario from '../componentes/inventario/AbaInventario'
import { EnviarFoto, Foto } from '../componentes/Foto'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import { Abas, Aviso, Botao, Carregando, Selecao } from '../componentes/ui'
import { useNomeDominio, useNomes } from '../lib/nomes'
import { NOME_ESTAGIO } from '../lib/rotulos'

type Visao = 'ficha' | 'equipamento' | 'inventario' | 'tempo'

/** Mesa do personagem e a cópia para outra mesa (ele fica preso à mesa em que está). */
function MesaDoPersonagem({ id, mesaId }: { id: string; mesaId: string | null | undefined }) {
  const mesas = useMesas()
  const copiar = useCopiarParaMesa()
  const navegar = useNavigate()
  const [aberto, setAberto] = useState(false)
  const [destino, setDestino] = useState('')
  const atual = mesas.data?.find((m) => m.id === mesaId)
  const outras = mesas.data?.filter((m) => m.id !== mesaId) ?? []

  return (
    <div className="space-y-2 text-sm">
      <p className="text-texto-suave">
        {mesaId
          ? <>Mesa: <Link to={`/mesas/${mesaId}`} className="text-esperanca hover:underline">{atual?.nome ?? '…'}</Link></>
          : 'Sem mesa (sem limite de nível).'}
        {outras.length > 0 && !aberto && (
          <button type="button" className="ml-2 text-esperanca hover:underline" onClick={() => setAberto(true)}>
            Copiar para outra mesa
          </button>
        )}
      </p>
      {aberto && (
        <form className="flex flex-wrap items-end gap-2 rounded-xl border border-borda p-3" onSubmit={(e) => {
          e.preventDefault()
          copiar.mutate({ personagemId: id, mesaId: destino },
            { onSuccess: (novo) => { setAberto(false); navegar(`/personagens/${novo.id}`) } })
        }}>
          <Selecao rotulo="Mesa de destino" value={destino} onChange={(e) => setDestino(e.target.value)}
            opcoes={[['', 'Escolha…'], ...outras.map((m): [string, string] => [m.id, m.nome])]} />
          <Botao type="submit" disabled={!destino || copiar.isPending}>Fazer cópia</Botao>
          <Botao type="button" variante="fantasma" onClick={() => setAberto(false)}>Cancelar</Botao>
          <p className="w-full text-xs text-texto-suave">
            O original continua onde está. A cópia segue o nível da mesa nova; os níveis acima viram plano,
            aplicado quando o mestre liberar.
          </p>
          <div className="w-full"><Aviso erro={copiar.error} /></div>
        </form>
      )}
    </div>
  )
}

export default function Personagem() {
  const { id = '' } = useParams()
  const [busca, setBusca] = useSearchParams()
  const pedida = busca.get('visao')
  const visao: Visao = pedida === 'tempo' || pedida === 'equipamento' || pedida === 'inventario' ? pedida : 'ficha'
  const ficha = useFicha(id)
  const tempo = useLinhaDoTempo(id)
  const lista = usePersonagens()
  const desfazer = useDesfazerNivel(id)
  const apagar = useApagarPersonagem()
  const foto = useFotoDoPersonagem(id)
  const navegar = useNavigate()
  const nomes = useNomes(ficha.data)
  const dominio = useNomeDominio()

  if (ficha.isPending) return <Carregando />
  if (ficha.error) return <Aviso erro={ficha.error} />
  const f = ficha.data
  const resumo = lista.data?.find((p) => p.id === id)

  function excluir() {
    if (window.confirm(`Excluir ${f.nome || 'este personagem'}? Isso não pode ser desfeito.`)) {
      apagar.mutate(id, { onSuccess: () => navegar('/personagens') })
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex gap-4">
          <div className="space-y-1.5">
            <Foto id={resumo?.foto} nome={f.nome || '?'} tamanho="g" />
            <EnviarFoto temFoto={!!resumo?.foto} desabilitado={foto.isPending} aoMudar={(imagem) => foto.mutate(imagem)} />
          </div>
          <div>
            <h1 className="text-3xl">{f.nome || 'Sem nome'}</h1>
            <p className="mt-1 text-texto-suave">
              Nível {f.nivel} · {nomes.classe(f.classe)} ({nomes.subclasse(f.subclasse)}, {NOME_ESTAGIO[f.estagio_subclasse]})
              {nomes.multiclasse && <> · Multiclasse {nomes.classe(nomes.multiclasse.classe)} ({dominio(nomes.multiclasse.dominio)})</>}
            </p>
            <p className="text-sm text-texto-suave">
              {nomes.ancestralidade(f.ancestralidade)}
              {f.segunda_ancestralidade && ` / ${nomes.ancestralidade(f.segunda_ancestralidade)}`} · {nomes.comunidade(f.comunidade)}
            </p>
            {resumo && <MesaDoPersonagem id={id} mesaId={resumo.mesa_id} />}
          </div>
        </div>
        <div className="flex gap-2">
          {f.nivel < 10 && (
            <Link to={`/personagens/${id}?visao=tempo`}
              className="rounded-lg bg-esperanca px-4 py-2 text-sm font-semibold text-sobre-esperanca hover:bg-esperanca-forte">
              Subir de nível
            </Link>
          )}
          <Botao variante="perigo" onClick={excluir} disabled={apagar.isPending}>Excluir</Botao>
        </div>
      </header>

      <Aviso erro={desfazer.error ?? apagar.error ?? foto.error} />

      <Abas<Visao> atual={visao}
        abas={[['ficha', 'Ficha'], ['equipamento', 'Equipamento'], ['inventario', 'Inventário'], ['tempo', 'Linha do tempo']]}
        aoTrocar={(nova) => setBusca(nova === 'ficha' ? {} : { visao: nova })} />

      {visao === 'ficha' && <FichaVisao ficha={f} personagemId={id} />}
      {visao === 'equipamento' && <AbaEquipamento personagemId={id} ficha={f} />}
      {visao === 'inventario' && <AbaInventario personagemId={id} ficha={f} />}
      {visao === 'tempo' && (tempo.isPending ? <Carregando /> : tempo.data && (
        <LinhaDoTempo eventos={tempo.data} personagemId={id} ficha={f}
          aoDesfazer={() => desfazer.mutate()} desfazendo={desfazer.isPending} />
      ))}
    </div>
  )
}
