// Link de convite (/convite/CODIGO): entra na mesa e vai para a página dela.
import { useEffect, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { useEntrarNaMesa } from '../api/consultas'
import { Aviso, Carregando } from '../componentes/ui'

export default function Convite() {
  const { codigo = '' } = useParams()
  const entrar = useEntrarNaMesa()
  const navegar = useNavigate()
  const pedido = useRef(false)   // StrictMode roda o efeito duas vezes em desenvolvimento

  useEffect(() => {
    if (pedido.current) return
    pedido.current = true
    entrar.mutate(codigo, { onSuccess: (mesa) => navegar(`/mesas/${mesa.id}`, { replace: true }) })
  }, [codigo, entrar, navegar])

  if (entrar.isError) {
    return (
      <div className="space-y-3">
        <Aviso erro={entrar.error} />
        <Link to="/mesas" className="text-esperanca hover:underline">Ir para suas mesas</Link>
      </div>
    )
  }
  return <Carregando texto="Entrando na mesa…" />
}
