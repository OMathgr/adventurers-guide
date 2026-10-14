// Aviso de quando duas pessoas (ou duas abas) editam o mesmo formulário: quem
// salvou por último tinha uma versão velha. Deixa escolher entre ver a versão
// atual (descarta a sua) e salvar a sua por cima. Ver api/concorrencia.py.
import type { ErroApi } from '../api/cliente'
import { ehConflito } from '../lib/conflito'
import { Botao } from './ui'

export function AvisoDeConflito({ erro, aoVerAtual, aoSalvarMesmoAssim, ocupado }: {
  erro: unknown; aoVerAtual: () => void; aoSalvarMesmoAssim: () => void; ocupado?: boolean
}) {
  if (!ehConflito(erro)) return null
  return (
    <div role="alert" className="space-y-2 rounded-xl border border-esperanca/60 bg-esperanca/10 p-3 text-sm">
      <p>{(erro as ErroApi).message} Suas mudanças ainda não foram salvas.</p>
      <div className="flex flex-wrap gap-2">
        <Botao variante="secundario" disabled={ocupado} onClick={aoVerAtual}>Ver a versão atual</Botao>
        <Botao disabled={ocupado} onClick={aoSalvarMesmoAssim}>Salvar a minha por cima</Botao>
      </div>
    </div>
  )
}
