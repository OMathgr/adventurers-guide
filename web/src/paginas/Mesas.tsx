import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { useCriarMesa, useEntrarNaMesa, useMesas } from '../api/consultas'
import { Aviso, Botao, Campo, Cartao, Carregando, Selo } from '../componentes/ui'
import { NOME_PAPEL } from '../lib/rotulos'

export default function Mesas() {
  const mesas = useMesas()
  const criar = useCriarMesa()
  const entrar = useEntrarNaMesa()
  const navegar = useNavigate()
  const [nome, setNome] = useState('')
  const [codigo, setCodigo] = useState('')

  function enviarCriar(e: FormEvent) {
    e.preventDefault()
    criar.mutate(nome.trim(), { onSuccess: (mesa) => navegar(`/mesas/${mesa.id}`) })
  }

  function enviarCodigo(e: FormEvent) {
    e.preventDefault()
    entrar.mutate(codigo.trim(), { onSuccess: (mesa) => navegar(`/mesas/${mesa.id}`) })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl">Suas mesas</h1>

      {mesas.isPending && <Carregando />}
      <Aviso erro={mesas.error} />

      {mesas.data?.length === 0 && (
        <div className="rounded-2xl border border-dashed border-borda p-8 text-center">
          <p className="font-titulo text-lg">Nenhuma mesa ainda.</p>
          <p className="mt-1 text-sm text-texto-suave">Crie uma para mestrar ou entre com o código que o mestre passou.</p>
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {mesas.data?.map((m) => (
          <li key={m.id}>
            <Link to={`/mesas/${m.id}`}
              className="flex items-center justify-between gap-2 rounded-2xl border border-borda bg-superficie p-4 transition hover:border-esperanca">
              <span className="font-titulo text-lg">{m.nome}</span>
              <Selo destaque={m.meu_papel === 'mestre'}>{NOME_PAPEL[m.meu_papel] ?? m.meu_papel}</Selo>
            </Link>
          </li>
        ))}
      </ul>

      <div className="grid gap-4 sm:grid-cols-2">
        <Cartao titulo="Criar mesa">
          <form onSubmit={enviarCriar} className="space-y-3">
            <Campo rotulo="Nome da mesa" value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={120} />
            <Aviso erro={criar.error} />
            <Botao type="submit" disabled={criar.isPending || !nome.trim()}>Criar e ser o mestre</Botao>
          </form>
        </Cartao>
        <Cartao titulo="Entrar com código">
          <form onSubmit={enviarCodigo} className="space-y-3">
            <Campo rotulo="Código de convite" value={codigo} onChange={(e) => setCodigo(e.target.value.toUpperCase())}
              required autoComplete="off" />
            <Aviso erro={entrar.error} />
            <Botao type="submit" variante="secundario" disabled={entrar.isPending || !codigo.trim()}>Entrar</Botao>
          </form>
        </Cartao>
      </div>
    </div>
  )
}
