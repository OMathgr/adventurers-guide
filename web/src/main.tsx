import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router'

import { ErroApi } from './api/cliente'
import { ProvedorAutenticacao, useAutenticacao } from './auth/Autenticacao'
import Layout from './componentes/Layout'
import { capturarConviteDeInstalacao, registrarServiceWorker } from './lib/pwa'
import { Cadastro, Entrar, EntrarComGoogle, RecuperarSenha, RedefinirSenha } from './paginas/Acesso'
import Conta from './paginas/Conta'
import Convite from './paginas/Convite'
import Mesa from './paginas/Mesa'
import Mesas from './paginas/Mesas'
import NovoPersonagem from './paginas/NovoPersonagem'
import Personagem from './paginas/Personagem'
import Personagens from './paginas/Personagens'

const clienteConsultas = new QueryClient({
  defaultOptions: {
    queries: {
      // erro de regra/permissão não melhora tentando de novo
      retry: (tentativas, erro) => !(erro instanceof ErroApi && erro.status < 500) && tentativas < 2,
      refetchOnWindowFocus: false,
    },
  },
})

function SoLogado() {
  const { logado } = useAutenticacao()
  const local = useLocation()
  // guarda para onde ia (ex.: link de convite) para voltar depois de entrar
  return logado ? <Outlet /> : <Navigate to="/entrar" replace state={{ de: local.pathname }} />
}

capturarConviteDeInstalacao()   // antes das telas: o convite do Chrome vem uma vez só
registrarServiceWorker()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={clienteConsultas}>
      <ProvedorAutenticacao>
        <BrowserRouter>
          <Routes>
            <Route path="/entrar" element={<Entrar />} />
            <Route path="/cadastro" element={<Cadastro />} />
            <Route path="/entrar/google" element={<EntrarComGoogle />} />
            <Route path="/recuperar-senha" element={<RecuperarSenha />} />
            <Route path="/redefinir-senha" element={<RedefinirSenha />} />
            <Route element={<SoLogado />}>
              <Route element={<Layout />}>
                <Route path="/personagens" element={<Personagens />} />
                <Route path="/personagens/novo" element={<NovoPersonagem />} />
                <Route path="/personagens/:id" element={<Personagem />} />
                <Route path="/mesas" element={<Mesas />} />
                <Route path="/mesas/:id" element={<Mesa />} />
                <Route path="/convite/:codigo" element={<Convite />} />
                <Route path="/conta" element={<Conta />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/personagens" replace />} />
          </Routes>
        </BrowserRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>
  </StrictMode>,
)
