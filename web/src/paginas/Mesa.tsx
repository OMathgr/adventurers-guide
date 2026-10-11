// Página da mesa. Todos veem a aba Geral (com o Medo do mestre); os mestres
// também veem a Sessão (encontros) e a biblioteca privada (Inimigos e NPCs).
import { useParams, useSearchParams } from 'react-router'

import { useMesa } from '../api/consultas'
import { Abas, Aviso, Carregando, Selo } from '../componentes/ui'
import { NOME_PAPEL } from '../lib/rotulos'
import AbaGeral from './mesa/AbaGeral'
import AbaInimigos from './mesa/AbaInimigos'
import AbaNpcs from './mesa/AbaNpcs'
import AbaSessao from './mesa/AbaSessao'

type Aba = 'geral' | 'sessao' | 'inimigos' | 'npcs'
const SO_MESTRE: Aba[] = ['sessao', 'inimigos', 'npcs']

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
  const aba: Aba = mestre && pedida && SO_MESTRE.includes(pedida) ? pedida : 'geral'

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl">{m.nome}</h1>
        <Selo destaque={mestre}>{NOME_PAPEL[m.meu_papel] ?? m.meu_papel}</Selo>
      </div>

      {mestre && (
        <Abas<Aba> atual={aba}
          abas={[['geral', 'Mesa'], ['sessao', 'Sessão'], ['inimigos', 'Inimigos'], ['npcs', 'NPCs']]}
          aoTrocar={(nova) => setBusca(nova === 'geral' ? {} : { aba: nova }, { replace: true })} />
      )}

      {aba === 'geral' && <AbaGeral mesa={m} />}
      {aba === 'sessao' && <AbaSessao mesa={m} podePreparar={podePreparar} />}
      {aba === 'inimigos' && <AbaInimigos mesaId={m.id} podeEditar={podePreparar} />}
      {aba === 'npcs' && <AbaNpcs mesaId={m.id} podeEditar={podePreparar} />}
    </div>
  )
}
