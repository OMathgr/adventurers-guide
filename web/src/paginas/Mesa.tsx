// Página da mesa. Todos veem a aba Geral (com o Medo e o que foi revelado) e o\n// Quadro da campanha; os mestres
// também veem as Sessões (planejamento, Medo e encontros) e a biblioteca privada (Inimigos e NPCs).
import { lazy, Suspense } from 'react'
import { useParams, useSearchParams } from 'react-router'

import { useMesa } from '../api/consultas'
import { Abas, Aviso, Carregando, Selo } from '../componentes/ui'
import { NOME_PAPEL } from '../lib/rotulos'
import AbaGeral from './mesa/AbaGeral'
import AbaInimigos from './mesa/AbaInimigos'
import AbaNpcs from './mesa/AbaNpcs'
import AbaSessoes from './mesa/AbaSessoes'

type Aba = 'geral' | 'campanha' | 'sessao' | 'inimigos' | 'npcs'
const SO_MESTRE: Aba[] = ['sessao', 'inimigos', 'npcs']

// o quadro usa o React Flow (pesado): só carrega quando alguém abre a aba
const QuadroDaCampanha = lazy(() => import('../componentes/QuadroDaCampanha'))

export default function Mesa() {
  const { id = '' } = useParams()
  const mesa = useMesa(id)
  const [busca, setBusca] = useSearchParams()

  if (mesa.isPending) return <Carregando />
  if (mesa.isError) return <Aviso erro={mesa.error} />

  const m = mesa.data
  const mestre = m.meu_papel === 'mestre'
  const podePreparar = m.minhas_permissoes.includes('preparar')
  const pedida = busca.get('aba') as Aba | null
  const aba: Aba = pedida === 'campanha' ? 'campanha' : mestre && pedida && SO_MESTRE.includes(pedida) ? pedida : 'geral'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl">{m.nome}</h1>
        <Selo destaque={mestre}>{NOME_PAPEL[m.meu_papel] ?? m.meu_papel}</Selo>
      </div>

      <Abas<Aba> atual={aba}
        abas={[['geral', 'Mesa'], ['campanha', 'Quadro da campanha'],
          ...(mestre ? [['sessao', 'Sessões'], ['inimigos', 'Inimigos'], ['npcs', 'NPCs']] as [Aba, string][] : [])]}
        aoTrocar={(nova) => setBusca(nova === 'geral' ? {} : { aba: nova }, { replace: true })} />

      {aba === 'geral' && <AbaGeral mesa={m} />}
      {aba === 'campanha' && <Suspense fallback={<Carregando />}><QuadroDaCampanha mesaId={m.id} /></Suspense>}
      {aba === 'sessao' && <AbaSessoes mesa={m} podePreparar={podePreparar} />}
      {aba === 'inimigos' && <AbaInimigos mesaId={m.id} podeEditar={podePreparar} />}
      {aba === 'npcs' && <AbaNpcs mesaId={m.id} podeEditar={podePreparar} />}
    </div>
  )
}
