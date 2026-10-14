// Ficha simplificada de um personagem da mesa: quem é, e PV, PF e Esperança.
// Qualquer membro vê (os jogadores acompanham o grupo); o resto da ficha
// continua sendo só do dono (e do mestre com "ver fichas").
import { useFichaResumida } from '../api/consultas'
import { NOME_ESTAGIO } from '../lib/rotulos'
import { Aviso, Carregando, Espacos, Esperanca } from './ui'

export default function FichaResumida({ mesaId, pid }: { mesaId: string; pid: string }) {
  const ficha = useFichaResumida(mesaId, pid)
  if (ficha.isPending) return <Carregando />
  if (ficha.isError) return <Aviso erro={ficha.error} />
  const f = ficha.data
  const nome = f.nome || 'Sem nome'

  return (
    <section aria-label={`Ficha de ${nome}`} className="space-y-2 rounded-xl border border-borda bg-fundo/60 p-3 text-sm">
      <p className="text-texto-suave">
        Nível {f.nivel} · {f.classe} ({f.subclasse}, {NOME_ESTAGIO[f.estagio_subclasse] ?? f.estagio_subclasse})
        {f.multiclasse && <> · Multiclasse {f.multiclasse}</>}
      </p>
      <p className="text-texto-suave">{f.ancestralidade} · {f.comunidade} · jogado por {f.jogador}</p>
      {f.morto && <p className="font-medium text-perigo">Atravessou o véu da morte.</p>}
      {!f.morto && f.inconsciente && <p className="font-medium text-perigo">Inconsciente.</p>}
      <div className="grid gap-2 sm:grid-cols-3">
        <div>
          <p className="text-xs text-texto-suave">Vida: {f.pv_max - f.pv_marcados}/{f.pv_max} PV</p>
          <Espacos total={f.pv_max} marcados={f.pv_marcados} rotulo={`PV de ${nome}`} restantes />
        </div>
        <div>
          <p className="text-xs text-texto-suave">Fadiga: {f.estresse_max - f.estresse_marcado}/{f.estresse_max} PF</p>
          <Espacos total={f.estresse_max} marcados={f.estresse_marcado} rotulo={`PF de ${nome}`} cor="medo" restantes />
        </div>
        <div>
          <p className="text-xs text-texto-suave">Esperança: {f.esperanca}/{f.esperanca_max}</p>
          <Esperanca atual={f.esperanca} maximo={f.esperanca_max} />
        </div>
      </div>
    </section>
  )
}
