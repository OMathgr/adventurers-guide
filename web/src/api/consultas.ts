// Hooks de dados (React Query). Cada recurso da API tem uma chave de cache;
// as mutações invalidam o que mudou para a tela se atualizar sozinha.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { chamar } from './cliente'
import type {
  Ancestralidade, CartaDeDominio, Classe, Comunidade, Criacao, Escolha, EventoLinhaDoTempo, Ficha,
  PersonagemCriado, PersonagemResumo, ProximoNivel, Subclasse, SubidaDeNivel,
} from './tipos'

const UMA_HORA = 60 * 60 * 1000

// --- Catálogo do SRD (não muda: cache longo) -------------------------------------------

export const useClasses = () =>
  useQuery({ queryKey: ['srd', 'classes'], queryFn: () => chamar<Classe[]>('/srd/classes'), staleTime: UMA_HORA })

export const useSubclasses = (classeId: string | undefined) =>
  useQuery({
    queryKey: ['srd', 'subclasses', classeId],
    queryFn: () => chamar<Subclasse[]>(`/srd/classes/${classeId}/subclasses`),
    enabled: !!classeId,
    staleTime: UMA_HORA,
  })

export const useAncestralidades = () =>
  useQuery({
    queryKey: ['srd', 'ancestralidades'],
    queryFn: () => chamar<Ancestralidade[]>('/srd/ancestralidades'),
    staleTime: UMA_HORA,
  })

export const useComunidades = () =>
  useQuery({ queryKey: ['srd', 'comunidades'], queryFn: () => chamar<Comunidade[]>('/srd/comunidades'), staleTime: UMA_HORA })

export const useCartas = () =>
  useQuery({ queryKey: ['srd', 'cartas'], queryFn: () => chamar<CartaDeDominio[]>('/srd/cartas'), staleTime: UMA_HORA })

// --- Personagens -----------------------------------------------------------------------------

export const chaves = {
  lista: ['personagens'] as const,
  ficha: (id: string) => ['personagens', id, 'ficha'] as const,
  tempo: (id: string) => ['personagens', id, 'tempo'] as const,
  proximo: (id: string) => ['personagens', id, 'proximo'] as const,
}

export const usePersonagens = () =>
  useQuery({ queryKey: chaves.lista, queryFn: () => chamar<PersonagemResumo[]>('/personagens') })

export const useFicha = (id: string) =>
  useQuery({ queryKey: chaves.ficha(id), queryFn: () => chamar<Ficha>(`/personagens/${id}`) })

export const useLinhaDoTempo = (id: string) =>
  useQuery({ queryKey: chaves.tempo(id), queryFn: () => chamar<EventoLinhaDoTempo[]>(`/personagens/${id}/linha-do-tempo`) })

export const useProximoNivel = (id: string) =>
  useQuery({ queryKey: chaves.proximo(id), queryFn: () => chamar<ProximoNivel | null>(`/personagens/${id}/proximo-nivel`) })

type PedidoCartas =
  | { para: 'nivel'; escolhas: Escolha[] }
  | { para: 'avanco'; tier: number }
  | { para: 'troca'; antiga: string; escolhas: Escolha[]; carta_do_nivel: string | null }

/** Cartas que podem ser escolhidas no próximo nível (depende do que já foi marcado). */
export const useOpcoesDeCarta = (id: string, pedido: PedidoCartas | null) =>
  useQuery({
    queryKey: ['personagens', id, 'cartas', pedido],
    queryFn: () => chamar<CartaDeDominio[]>(`/personagens/${id}/cartas/opcoes`, { corpo: pedido }),
    enabled: pedido !== null,
  })

function useInvalidarPersonagem() {
  const cliente = useQueryClient()
  return (id?: string) =>
    cliente.invalidateQueries({ queryKey: id ? ['personagens', id] : chaves.lista }).then(() =>
      id ? cliente.invalidateQueries({ queryKey: chaves.lista }) : undefined)
}

export function useCriarPersonagem() {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (criacao: Criacao) => chamar<PersonagemCriado>('/personagens', { corpo: criacao }),
    onSuccess: () => invalidar(),
  })
}

export function useApagarPersonagem() {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (id: string) => chamar<void>(`/personagens/${id}`, { metodo: 'DELETE' }),
    onSuccess: () => invalidar(),
  })
}

export function useSubirDeNivel(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (subida: SubidaDeNivel) => chamar<Ficha>(`/personagens/${id}/niveis`, { corpo: subida }),
    onSuccess: () => invalidar(id),
  })
}

export function useDesfazerNivel(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: () => chamar<Ficha>(`/personagens/${id}/niveis/ultimo`, { metodo: 'DELETE' }),
    onSuccess: () => invalidar(id),
  })
}
