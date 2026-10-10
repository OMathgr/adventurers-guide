import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router'

import { ErroApi } from './api/cliente'
import { ProvedorAutenticacao, useAutenticacao } from './auth/Autenticacao'
import Layout from './componentes/Layout'
import { Cadastro, Entrar } from './paginas/Acesso'
import NovoPersonagem from './paginas/NovoPersonagem'
import Personagem from './paginas/Personagem'
import Personagens from './paginas/Personagens'
import SubirNivel from './paginas/SubirNivel'

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
  return logado ? <Outlet /> : <Navigate to="/entrar" replace />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={clienteConsultas}>
      <ProvedorAutenticacao>
        <BrowserRouter>
          <Routes>
            <Route path="/entrar" element={<Entrar />} />
            <Route path="/cadastro" element={<Cadastro />} />
            <Route element={<SoLogado />}>
              <Route element={<Layout />}>
                <Route path="/personagens" element={<Personagens />} />
                <Route path="/personagens/novo" element={<NovoPersonagem />} />
                <Route path="/personagens/:id" element={<Personagem />} />
                <Route path="/personagens/:id/subir" element={<SubirNivel />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/personagens" replace />} />
          </Routes>
        </BrowserRouter>
      </ProvedorAutenticacao>
    </QueryClientProvider>
  </StrictMode>,
)
