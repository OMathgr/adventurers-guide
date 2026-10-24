// Conta: jeitos de entrar (senha e Google). Quem entrou só pelo Google cria
// uma senha pelo mesmo link de "esqueci minha senha"; desligar o Google exige
// ter senha (senão não haveria como entrar). Excluir a conta pede o e-mail
// digitado; mesas e sessões ficam com outros mestres (api/conta.py).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { chamar } from '../api/cliente'
import type { Usuario } from '../api/tipos'
import { useAutenticacao } from '../auth/Autenticacao'
import { Aviso, Botao, Cartao, Selo } from '../componentes/ui'
import { abertoComoApp, ehIOS, useInstalar } from '../lib/pwa'

export default function Conta() {
  const { usuario, sair } = useAutenticacao()
  const navegar = useNavigate()
  const [confirmacao, setConfirmacao] = useState('')
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

  const excluir = useMutation({
    mutationFn: () => chamar<void>('/auth/eu', { metodo: 'DELETE', corpo: { email: confirmacao } }),
    onSuccess: () => { cliente.clear(); sair(); navegar('/') },
  })

  const instalar = useInstalar()

  if (!usuario) return null
  const erroDoGoogle = busca.get('erro')

  return (
    <div className="max-w-xl space-y-5">
      <h1 className="text-2xl">Conta</h1>
      <Cartao titulo={usuario.nome}>
        <p className="text-sm text-texto-suave">{usuario.email}</p>
      </Cartao>

      <Cartao titulo="App no celular">
        <div className="space-y-2 text-sm">
          {abertoComoApp() ? (
            <p>Você já está usando o app instalado.</p>
          ) : instalar ? (
            <>
              <p className="text-texto-suave">Instale para abrir direto da tela inicial, em tela cheia.</p>
              <Botao onClick={instalar}>Instalar o app</Botao>
            </>
          ) : ehIOS() ? (
            <p className="text-texto-suave">
              No iPhone, abra no <b>Safari</b>, toque em <b>Compartilhar</b> e depois em <b>Adicionar à Tela de Início</b>.
            </p>
          ) : (
            <p className="text-texto-suave">
              No Chrome do Android, toque no menu <b>⋮</b> e depois em <b>Instalar app</b> (ou <b>Adicionar à tela
              inicial</b>). Se a opção não aparecer, o app pode já estar instalado.
            </p>
          )}
        </div>
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

      <Cartao titulo="Excluir conta">
        <div className="space-y-3 text-sm">
          <p>Excluir é para sempre e não dá para desfazer:</p>
          <ul className="list-inside list-disc space-y-1 text-texto-suave">
            <li>seus personagens são apagados, com as fichas, o inventário e as rolagens;</li>
            <li>as mesas que você criou continuam com os outros membros: passam para o mestre mais antigo
              (sem mestre, para o jogador mais antigo). Mesa sem mais ninguém é apagada;</li>
            <li>as sessões que você mestrou ficam com quem criou a mesa, e seus NPCs também.</li>
          </ul>
          <label className="flex flex-col gap-1">
            <span className="text-texto-suave">Para confirmar, digite o seu e-mail ({usuario.email})</span>
            <input type="email" value={confirmacao} onChange={(e) => setConfirmacao(e.target.value)} autoComplete="off"
              aria-label="E-mail para confirmar a exclusão"
              className="rounded-lg border border-borda bg-fundo px-3 py-2" />
          </label>
          <Botao variante="perigo" disabled={excluir.isPending
            || confirmacao.trim().toLowerCase() !== usuario.email.toLowerCase()} onClick={() => excluir.mutate()}>
            {excluir.isPending ? 'Excluindo…' : 'Excluir minha conta'}
          </Botao>
          <Aviso erro={excluir.error} />
        </div>
      </Cartao>
    </div>
  )
}
