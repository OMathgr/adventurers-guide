// Quadro da campanha: tudo o que os mestres revelaram nos quadros das sessões,
// uma região por sessão. Só leitura, para jogadores e mestres. Enche sozinho
// conforme os cartões são revelados (a tela recarrega a cada 10 s).
import '@xyflow/react/dist/style.css'

import { Background, ConnectionMode, Controls, ReactFlow } from '@xyflow/react'
import { useMemo } from 'react'

import { useQuadroDaCampanha } from '../api/consultas'
import { layoutDaCampanha } from '../lib/quadro'
import { TIPOS_DE_CARTAO } from './quadro/tipos'
import { Aviso, Carregando } from './ui'

export default function QuadroDaCampanha({ mesaId }: { mesaId: string }) {
  const quadro = useQuadroDaCampanha(mesaId)
  const { nos, arestas } = useMemo(() => layoutDaCampanha(quadro.data ?? []), [quadro.data])

  if (quadro.isPending) return <Carregando />
  if (quadro.isError) return <Aviso erro={quadro.error} />
  if (quadro.data.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-borda p-10 text-center text-texto-suave">
        Nada revelado ainda. Quando os mestres mostrarem cartões dos quadros das sessões, eles aparecem aqui.
      </div>
    )
  }
  return (
    <div className="h-[70vh] overflow-hidden rounded-2xl border border-borda" aria-label="Quadro da campanha">
      <ReactFlow nodes={nos} edges={arestas} nodeTypes={TIPOS_DE_CARTAO}
        colorMode={document.documentElement.dataset.tema === 'claro' ? 'light' : 'dark'}
        nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} fitView minZoom={0.1}
        connectionMode={ConnectionMode.Loose}>
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
