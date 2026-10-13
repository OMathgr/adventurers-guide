// Conta: jeitos de entrar (senha e Google). Quem entrou só pelo Google cria
// uma senha pelo mesmo link de "esqueci minha senha"; desligar o Google exige
// ter senha (senão não haveria como entrar).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'

import { chamar } from '../api/cliente'
import type { Usuario } from '../api/tipos'
import { useAutenticacao } from '../auth/Autenticacao'
import { Aviso, Botao, Cartao, Selo } from '../componentes/ui'

export default function Conta() {
  const { usuario } = useAutenticacao()
  const cliente = useQueryClient()
  const [busca] = useSearchParams()
  const provedores = useQuery({
    queryKey: ['auth', 'provedores'],
    queryFn: () => chamar<{ google: boolean }>('/auth/provedores'),
    staleTime: Infinity,
  })
  const pedirSenha = useMutation({
    mutationFn: () => chamar('/auth/recuperar', { corpo: { email: usuario?.email } }),
  })
  const ligar = useMutation({
    mutationFn: () => chamar<{ url: string }>('/auth/google/ligar', { corpo: {} }),
    onSuccess: ({ url }) => { window.location.assign(`/api${url}`) },
  })
  const desligar = useMutation({
    mutationFn: () => chamar<Usuario>('/auth/google', { metodo: 'DELETE' }),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ['eu'] }),
  })

  if (!usuario) return null
  const erroDoGoogle = busca.get('erro')

  return (
    <div className="max-w-xl space-y-5">
      <h1 className="text-2xl">Conta</h1>
      <Cartao titulo={usuario.nome}>
        <p className="text-sm text-texto-suave">{usuario.email}</p>
      </Cartao>

      <Cartao titulo="Jeitos de entrar">
        <div className="space-y-4 text-sm">
          {busca.get('ligado') === 'google' && (
            <p role="status" className="rounded-lg border border-sucesso/50 bg-sucesso/10 px-3 py-2">
              Conta Google ligada. Agora dá para entrar por ela também.
            </p>
          )}
          {erroDoGoogle && <Aviso>{erroDoGoogle}</Aviso>}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              Senha {usuario.tem_senha ? <Selo destaque>definida</Selo> : <Selo>ainda não tem</Selo>}
            </span>
            <Botao variante="secundario" disabled={pedirSenha.isPending || pedirSenha.isSuccess}
              onClick={() => pedirSenha.mutate()}>
              {usuario.tem_senha ? 'Trocar senha' : 'Criar senha'}
            </Botao>
          </div>
          {pedirSenha.isSuccess && (
            <p role="status" className="text-xs text-texto-suave">
              Enviamos um link para {usuario.email}. Ele vale por 1 hora.
            </p>
          )}
          <Aviso erro={pedirSenha.error} />

          {(provedores.data?.google || usuario.google) && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-borda pt-4">
              <span className="flex items-center gap-2">
                Google {usuario.google ? <Selo destaque>ligado</Selo> : <Selo>não ligado</Selo>}
              </span>
              {usuario.google ? (
                <Botao variante="fantasma" disabled={desligar.isPending || !usuario.tem_senha}
                  onClick={() => desligar.mutate()}>Desligar</Botao>
              ) : (
                <Botao variante="secundario" disabled={ligar.isPending} onClick={() => ligar.mutate()}>
                  Ligar conta Google
                </Botao>
              )}
            </div>
          )}
          {usuario.google && !usuario.tem_senha && (
            <p className="text-xs text-texto-suave">Para desligar o Google, crie uma senha antes.</p>
          )}
          <Aviso erro={ligar.error ?? desligar.error} />
        </div>
      </Cartao>
    </div>
  )
}
