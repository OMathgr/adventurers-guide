// Página do personagem: visão ficha e visão linha do tempo.
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

import { useApagarPersonagem, useDesfazerNivel, useFicha, useLinhaDoTempo } from '../api/consultas'
import FichaVisao from '../componentes/Ficha'
import LinhaDoTempo from '../componentes/LinhaDoTempo'
import { Aviso, Botao, Carregando } from '../componentes/ui'
import { useNomes } from '../lib/nomes'
import { NOME_ESTAGIO, dominio } from '../lib/rotulos'

export default function Personagem() {
  const { id = '' } = useParams()
  const [busca, setBusca] = useSearchParams()
  const visao = busca.get('visao') === 'tempo' ? 'tempo' : 'ficha'
  const ficha = useFicha(id)
  const tempo = useLinhaDoTempo(id)
  const desfazer = useDesfazerNivel(id)
  const apagar = useApagarPersonagem()
  const navegar = useNavigate()
  const nomes = useNomes(ficha.data)

  if (ficha.isPending) return <Carregando />
  if (ficha.error) return <Aviso erro={ficha.error} />
  const f = ficha.data

  function excluir() {
    if (window.confirm(`Excluir ${f.nome || 'este personagem'}? Isso não pode ser desfeito.`)) {
      apagar.mutate(id, { onSuccess: () => navegar('/personagens') })
    }
  }

  const aba = (valor: 'ficha' | 'tempo', rotulo: string) => (
    <button role="tab" aria-selected={visao === valor}
      onClick={() => setBusca(valor === 'tempo' ? { visao: 'tempo' } : {})}
      className={`border-b-2 px-3 py-2 text-sm ${visao === valor ? 'border-esperanca text-esperanca' : 'border-transparent text-texto-suave hover:text-texto'}`}>
      {rotulo}
    </button>
  )

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4">
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
        </div>
        <div className="flex gap-2">
          {f.nivel < 10 && (
            <Link to={`/personagens/${id}/subir`}
              className="rounded-lg bg-esperanca px-4 py-2 text-sm font-semibold text-sobre-esperanca hover:bg-esperanca-forte">
              Subir de nível
            </Link>
          )}
          <Botao variante="perigo" onClick={excluir} disabled={apagar.isPending}>Excluir</Botao>
        </div>
      </header>

      <Aviso erro={desfazer.error ?? apagar.error} />

      <div role="tablist" className="flex gap-2 border-b border-borda">
        {aba('ficha', 'Ficha')}
        {aba('tempo', 'Linha do tempo')}
      </div>

      {visao === 'ficha' && <FichaVisao ficha={f} />}
      {visao === 'tempo' && (tempo.isPending ? <Carregando /> : tempo.data && (
        <LinhaDoTempo eventos={tempo.data} personagemId={id}
          aoDesfazer={() => desfazer.mutate()} desfazendo={desfazer.isPending} />
      ))}
    </div>
  )
}
