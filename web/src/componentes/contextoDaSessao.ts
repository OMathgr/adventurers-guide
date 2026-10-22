// A sessão de jogo em andamento (só existe na tela de jogo): mesa, sessão e
// os aliados que estão jogando. As cartas da mão usam para o botão "Usar".
import { createContext, useContext } from 'react'

export type SessaoEmJogo = { mesaId: string; sessaoId: string; aliados: { id: string; nome: string }[] }
export const ContextoDaSessao = createContext<SessaoEmJogo | null>(null)
export const useSessaoEmJogo = () => useContext(ContextoDaSessao)
