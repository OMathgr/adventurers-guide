// Hooks de dados (React Query). Cada recurso da API tem uma chave de cache;
// as mutações invalidam o que mudou para a tela se atualizar sozinha.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { chamar } from './cliente'
import type {
  Adversario, Ancestralidade, CartaDeDominio, Classe, Comunidade, Criacao, Escolha, EventoLinhaDoTempo,
  Ficha, InimigoResumo, Mesa, MesaResumo, Npc, NpcEntrada, PermissoesMestres, PersonagemCriado,
  PersonagemResumo, ProximoNivel, Subclasse, SubidaDeNivel,
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

export const useDominios = () =>
  useQuery({ queryKey: ['srd', 'dominios'], queryFn: () => chamar<Record<string, string>>('/srd/dominios'), staleTime: UMA_HORA })

export const useCartas = () =>
  useQuery({ queryKey: ['srd', 'cartas'], queryFn: () => chamar<CartaDeDominio[]>('/srd/cartas'), staleTime: UMA_HORA })

/** Todos os adversários do SRD (são poucos; o filtro é feito na tela). */
export const useAdversariosSrd = (ativo = true) =>
  useQuery({
    queryKey: ['srd', 'adversarios'],
    queryFn: () => chamar<Adversario[]>('/srd/adversarios'),
    staleTime: UMA_HORA,
    enabled: ativo,
  })

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

/** Leva o personagem para a mesa (ou tira, com `mesaId: null`). */
export function useVincularMesa() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ personagemId, mesaId }: { personagemId: string; mesaId: string | null }) =>
      chamar<PersonagemResumo>(`/personagens/${personagemId}/mesa`, { metodo: 'PUT', corpo: { mesa_id: mesaId } }),
    onSuccess: () => Promise.all([
      cliente.invalidateQueries({ queryKey: chaves.lista }),
      cliente.invalidateQueries({ queryKey: ['mesas'] }),
    ]),
  })
}

// --- Mesas -----------------------------------------------------------------------------------

export const chavesMesa = {
  lista: ['mesas'] as const,
  mesa: (id: string) => ['mesas', id] as const,
  inimigos: (id: string) => ['mesas', id, 'inimigos'] as const,
  inimigo: (id: string, inimigoId: string) => ['mesas', id, 'inimigos', inimigoId] as const,
  npcs: (id: string) => ['mesas', id, 'npcs'] as const,
}

export const useMesas = () =>
  useQuery({ queryKey: chavesMesa.lista, queryFn: () => chamar<MesaResumo[]>('/mesas') })

export const useMesa = (id: string) =>
  useQuery({ queryKey: chavesMesa.mesa(id), queryFn: () => chamar<Mesa>(`/mesas/${id}`) })

/** Mutação que devolve a mesa atualizada: grava direto no cache. */
function useMutacaoMesa<V>(fn: (v: V) => Promise<Mesa>) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (mesa) => {
      cliente.setQueryData(chavesMesa.mesa(mesa.id), mesa)
      return cliente.invalidateQueries({ queryKey: chavesMesa.lista, exact: true })
    },
  })
}

export const useCriarMesa = () =>
  useMutacaoMesa((nome: string) => chamar<Mesa>('/mesas', { corpo: { nome } }))

export const useEntrarNaMesa = () =>
  useMutacaoMesa((codigo: string) => chamar<Mesa>(`/mesas/entrar/${encodeURIComponent(codigo)}`, { metodo: 'POST' }))

export const useNovoCodigo = (id: string) =>
  useMutacaoMesa(() => chamar<Mesa>(`/mesas/${id}/convite`, { metodo: 'POST' }))

export const useMudarPapel = (id: string) =>
  useMutacaoMesa(({ usuarioId, papel }: { usuarioId: string; papel: string }) =>
    chamar<Mesa>(`/mesas/${id}/membros/${usuarioId}`, { metodo: 'PUT', corpo: { papel } }))

export const useRemoverMembro = (id: string) =>
  useMutacaoMesa((usuarioId: string) => chamar<Mesa>(`/mesas/${id}/membros/${usuarioId}`, { metodo: 'DELETE' }))

export const usePermissoesMestres = (id: string) =>
  useMutacaoMesa((p: PermissoesMestres) => chamar<Mesa>(`/mesas/${id}/permissoes`, { metodo: 'PUT', corpo: p }))

/** Sair ou apagar: a mesa some da lista e os personagens ficam sem mesa. */
function useDeixarMesa(caminho: (id: string) => string, metodo: 'POST' | 'DELETE') {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => chamar<void>(caminho(id), { metodo }),
    onSuccess: (_, id) => {
      cliente.removeQueries({ queryKey: chavesMesa.mesa(id) })
      return Promise.all([
        cliente.invalidateQueries({ queryKey: chavesMesa.lista, exact: true }),
        cliente.invalidateQueries({ queryKey: chaves.lista }),
      ])
    },
  })
}

export const useSairDaMesa = () => useDeixarMesa((id) => `/mesas/${id}/sair`, 'POST')
export const useApagarMesa = () => useDeixarMesa((id) => `/mesas/${id}`, 'DELETE')

// --- Conteúdo do mestre (inimigos e NPCs da mesa) ----------------------------------------------

export const useInimigos = (mesaId: string) =>
  useQuery({ queryKey: chavesMesa.inimigos(mesaId), queryFn: () => chamar<InimigoResumo[]>(`/mesas/${mesaId}/inimigos`) })

export const useInimigo = (mesaId: string, inimigoId: string | null) =>
  useQuery({
    queryKey: chavesMesa.inimigo(mesaId, inimigoId ?? ''),
    queryFn: () => chamar<Adversario>(`/mesas/${mesaId}/inimigos/${inimigoId}`),
    enabled: !!inimigoId,
  })

function useMutacaoInimigo<V>(mesaId: string, fn: (v: V) => Promise<Adversario | void>) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => cliente.invalidateQueries({ queryKey: chavesMesa.inimigos(mesaId) }),
  })
}

export const useCopiarDoSrd = (mesaId: string) =>
  useMutacaoInimigo(mesaId, (adversarioId: string) =>
    chamar<Adversario>(`/mesas/${mesaId}/inimigos/do-srd/${adversarioId}`, { metodo: 'POST' }))

export const useSalvarInimigo = (mesaId: string) =>
  useMutacaoInimigo(mesaId, (inimigo: Adversario) =>
    inimigo.id
      ? chamar<Adversario>(`/mesas/${mesaId}/inimigos/${inimigo.id}`, { metodo: 'PUT', corpo: inimigo })
      : chamar<Adversario>(`/mesas/${mesaId}/inimigos`, { corpo: inimigo }))

export const useApagarInimigo = (mesaId: string) =>
  useMutacaoInimigo(mesaId, (inimigoId: string) =>
    chamar<void>(`/mesas/${mesaId}/inimigos/${inimigoId}`, { metodo: 'DELETE' }))

export const useNpcs = (mesaId: string) =>
  useQuery({ queryKey: chavesMesa.npcs(mesaId), queryFn: () => chamar<Npc[]>(`/mesas/${mesaId}/npcs`) })

function useMutacaoNpc<V>(mesaId: string, fn: (v: V) => Promise<Npc | void>) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => cliente.invalidateQueries({ queryKey: chavesMesa.npcs(mesaId) }),
  })
}

export const useSalvarNpc = (mesaId: string) =>
  useMutacaoNpc(mesaId, ({ id, ...npc }: NpcEntrada & { id?: string }) =>
    id
      ? chamar<Npc>(`/mesas/${mesaId}/npcs/${id}`, { metodo: 'PUT', corpo: npc })
      : chamar<Npc>(`/mesas/${mesaId}/npcs`, { corpo: npc }))

export const useApagarNpc = (mesaId: string) =>
  useMutacaoNpc(mesaId, (npcId: string) => chamar<void>(`/mesas/${mesaId}/npcs/${npcId}`, { metodo: 'DELETE' }))
