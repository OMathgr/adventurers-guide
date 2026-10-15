// Convite da mesa: código e link para quem vai jogar. Só os mestres veem (a API
// nem manda o código para jogadores); gerar um código novo é de quem criou a mesa.
import { useState } from 'react'

import { useNovoCodigo } from '../../api/consultas'
import type { Mesa } from '../../api/tipos'
import { Aviso, Botao, Cartao } from '../../componentes/ui'

export default function AbaConvite({ mesa }: { mesa: Mesa }) {
  const novoCodigo = useNovoCodigo(mesa.id)
  const [copiado, setCopiado] = useState(false)
  const link = `${window.location.origin}/convite/${mesa.codigo_convite}`

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch { /* sem permissão de área de transferência: o link continua visível */ }
  }

  return (
    <Cartao titulo="Convite">
      <p className="text-sm text-texto-suave">Passe o código ou o link para quem vai jogar. Quem entra começa como jogador.</p>
      <p className="my-3 font-titulo text-3xl tracking-[0.3em] text-esperanca" aria-label="Código de convite">
        {mesa.codigo_convite}
      </p>
      <p className="break-all text-xs text-texto-suave">{link}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Botao variante="secundario" onClick={copiar}>{copiado ? 'Link copiado' : 'Copiar link'}</Botao>
        {mesa.sou_criador && (
          <Botao variante="fantasma" disabled={novoCodigo.isPending}
            onClick={() => confirm('Gerar um código novo? O código e o link atuais param de funcionar.') && novoCodigo.mutate()}>
            Gerar novo código
          </Botao>
        )}
      </div>
      <Aviso erro={novoCodigo.error} />
    </Cartao>
  )
}
