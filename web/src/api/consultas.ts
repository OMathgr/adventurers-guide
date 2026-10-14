// Hooks de dados (React Query). Cada recurso da API tem uma chave de cache;
// as mutações invalidam o que mudou para a tela se atualizar sozinha.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { chamar } from './cliente'
import type {
  Adversario, Ancestralidade, Arma, Armadura, Cartao, CartaDeDominio, Equipamento, Ligacao, QuadroDaSessao, QuadroSaida, Classe, Comunidade, Criacao, Encontro, Escolha,
  EventoLinhaDoTempo, Ficha, GuiaDeBatalha, InimigoResumo, Mesa, MesaResumo, Npc, NpcEntrada, OpcoesDoGuia, PermissoesMestres, DadosDaSessao, Sessao, SessaoResumo,
  PersonagemCriado, PersonagemResumo, ProximoNivel, ResultadoDano, ResultadoDanoAdversario, Subclasse, VistaDosJogadores,
  SubidaDeNivel, Item, Inventario, UsoDeConsumivel, Loja, ItemDaLojaEntrada, Venda, FichaResumida,
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

// --- Equipamento ---------------------------------------------------------------------------

export const useArmas = () =>
  useQuery({ queryKey: ['srd', 'armas'], queryFn: () => chamar<Arma[]>('/srd/armas'), staleTime: UMA_HORA })

export const useArmaduras = () =>
  useQuery({ queryKey: ['srd', 'armaduras'], queryFn: () => chamar<Armadura[]>('/srd/armaduras'), staleTime: UMA_HORA })

export const useEquipamento = (id: string) =>
  useQuery({ queryKey: ['personagens', id, 'equipamento'], queryFn: () => chamar<Equipamento>(`/personagens/${id}/equipamento`) })

export function useEquipar(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (eq: Equipamento) => chamar<Ficha>(`/personagens/${id}/equipamento`, { metodo: 'PUT', corpo: eq }),
    onSuccess: () => invalidar(id),
  })
}

// --- Plano, cópia e foto do personagem -----------------------------------------------------

export function useAplicarPlano(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: () => chamar<Ficha>(`/personagens/${id}/plano/aplicar`, { metodo: 'POST' }),
    onSuccess: () => invalidar(id),
  })
}

export function useDescartarPlano(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (nivel: number) => chamar<void>(`/personagens/${id}/plano/${nivel}`, { metodo: 'DELETE' }),
    onSuccess: () => invalidar(id),
  })
}

/** Cópia do personagem para outra mesa (o original fica); devolve o novo. */
export function useCopiarParaMesa() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ personagemId, mesaId }: { personagemId: string; mesaId: string }) =>
      chamar<PersonagemCriado>(`/personagens/${personagemId}/copia`, { corpo: { mesa_id: mesaId } }),
    onSuccess: () => Promise.all([
      cliente.invalidateQueries({ queryKey: chaves.lista }),
      cliente.invalidateQueries({ queryKey: ['mesas'] }),
    ]),
  })
}

/** Envia uma foto e devolve o id para guardar no personagem, NPC ou inimigo. */
export const useEnviarImagem = () =>
  useMutation({
    mutationFn: (arquivo: File) => {
      const dados = new FormData()
      dados.append('arquivo', arquivo)
      return chamar<{ id: string; url: string }>('/imagens', { metodo: 'POST', multipart: dados })
    },
  })

export function useFotoDoPersonagem(id: string) {
  const invalidar = useInvalidarPersonagem()
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (imagemId: string | null) =>
      chamar<PersonagemResumo>(`/personagens/${id}/foto`, { metodo: 'PUT', corpo: { imagem_id: imagemId } }),
    onSuccess: () => Promise.all([invalidar(id), cliente.invalidateQueries({ queryKey: ['mesas'] })]),
  })
}

/** Manda uma carta da mão para a reserva (sem custo). */
export function useGuardarCarta(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: (carta: string) => chamar<Ficha>(`/personagens/${id}/cartas/${carta}/guardar`, { metodo: 'POST' }),
    onSuccess: () => invalidar(id),
  })
}

/** Traz uma carta da reserva para a mão: grátis no descanso, senão marca o custo de troca em PF. */
export function useRecuperarCarta(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: ({ carta, noLugarDe, emDescanso }: { carta: string; noLugarDe?: string; emDescanso: boolean }) =>
      chamar<Ficha>(`/personagens/${id}/cartas/${carta}/recuperar`,
        { corpo: { no_lugar_de: noLugarDe ?? null, em_descanso: emDescanso } }),
    onSuccess: () => invalidar(id),
  })
}

/** Leva o personagem para a mesa (ou tira, com `mesaId: null`). */
export function useVincularMesa() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ personagemId, mesaId }: { personagemId: string; mesaId: string }) =>
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

/** Regra opcional das moedas (10 moedas = 1 punhado). */
export const useMoedasDaMesa = (id: string) =>
  useMutacaoMesa((usar_moedas: boolean) => chamar<Mesa>(`/mesas/${id}/moedas`, { metodo: 'PUT', corpo: { usar_moedas } }))

export const useNivelDaMesa = (id: string) =>
  useMutacaoMesa((nivel_maximo: number) => chamar<Mesa>(`/mesas/${id}/nivel`, { metodo: 'PUT', corpo: { nivel_maximo } }))

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

// --- Sessões do mestre: planejamento, Medo e encontros ------------------------------------

const chaveSessoes = (mesaId: string) => ['mesas', mesaId, 'sessoes'] as const
const chaveSessao = (mesaId: string, sid: string) => ['mesas', mesaId, 'sessoes', sid] as const
const chaveEncontro = (mesaId: string, sid: string, id: string) => ['mesas', mesaId, 'sessoes', sid, 'encontros', id] as const
const urlSessao = (mesaId: string, sid: string) => `/mesas/${mesaId}/sessoes/${sid}`

export const useSessoes = (mesaId: string) =>
  useQuery({ queryKey: chaveSessoes(mesaId), queryFn: () => chamar<SessaoResumo[]>(`/mesas/${mesaId}/sessoes`) })

export const useSessao = (mesaId: string, sid: string | null) =>
  useQuery({
    queryKey: chaveSessao(mesaId, sid ?? ''),
    queryFn: () => chamar<Sessao>(urlSessao(mesaId, sid!)),
    enabled: !!sid,
  })

/** Grava a sessão devolvida no cache e atualiza a lista (e a mesa, por causa do Medo em jogo). */
function useMutacaoSessao<V>(mesaId: string, fn: (v: V) => Promise<Sessao>) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (s) => {
      cliente.setQueryData(chaveSessao(mesaId, s.id), s)
      return Promise.all([
        cliente.invalidateQueries({ queryKey: chaveSessoes(mesaId), exact: true }),
        cliente.invalidateQueries({ queryKey: chavesMesa.mesa(mesaId), exact: true }),
      ])
    },
  })
}

export const useCriarSessao = (mesaId: string) =>
  useMutacaoSessao(mesaId, (dados: { titulo: string; data: string | null }) =>
    chamar<Sessao>(`/mesas/${mesaId}/sessoes`, { corpo: dados }))

export const useEditarSessao = (mesaId: string, sid: string) =>
  useMutacaoSessao(mesaId, (dados: DadosDaSessao) => chamar<Sessao>(urlSessao(mesaId, sid), { metodo: 'PUT', corpo: dados }))

export const useStatusDaSessao = (mesaId: string, sid: string) =>
  useMutacaoSessao(mesaId, (status: string) =>
    chamar<Sessao>(`${urlSessao(mesaId, sid)}/status`, { metodo: 'PUT', corpo: { status } }))

export const useCompartilharSessao = (mesaId: string, sid: string) =>
  useMutacaoSessao(mesaId, (mestres: string[]) =>
    chamar<Sessao>(`${urlSessao(mesaId, sid)}/compartilhar`, { metodo: 'PUT', corpo: { mestres } }))

/** Medo da sessão (delta ou valor). */
export const useMedo = (mesaId: string, sid: string) =>
  useMutacaoSessao(mesaId, (p: { delta: number } | { valor: number }) =>
    chamar<Sessao>(`${urlSessao(mesaId, sid)}/medo`, { metodo: 'delta' in p ? 'POST' : 'PUT', corpo: p }))

export function useApagarSessao(mesaId: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (sid: string) => chamar<void>(urlSessao(mesaId, sid), { metodo: 'DELETE' }),
    onSuccess: (_, sid) => {
      cliente.removeQueries({ queryKey: chaveSessao(mesaId, sid) })
      return Promise.all([
        cliente.invalidateQueries({ queryKey: chaveSessoes(mesaId), exact: true }),
        cliente.invalidateQueries({ queryKey: chavesMesa.mesa(mesaId), exact: true }),
      ])
    },
  })
}

export const useEncontro = (mesaId: string, sid: string, id: string | null) =>
  useQuery({
    queryKey: chaveEncontro(mesaId, sid, id ?? ''),
    queryFn: () => chamar<Encontro>(`${urlSessao(mesaId, sid)}/encontros/${id}`),
    enabled: !!id,
  })

/** Mudou um encontro: troca no cache e recarrega a sessão (a lista de encontros vem com ela). */
function useMutacaoEncontro<V, R>(mesaId: string, sid: string, fn: (v: V) => Promise<R>, encontroDe: (r: R) => Encontro | null) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      const e = encontroDe(r)
      if (e) cliente.setQueryData(chaveEncontro(mesaId, sid, e.id), e)
      return cliente.invalidateQueries({ queryKey: chaveSessao(mesaId, sid), exact: true })
    },
  })
}

export const useCriarEncontro = (mesaId: string, sid: string) =>
  useMutacaoEncontro(mesaId, sid, (nome: string) =>
    chamar<Encontro>(`${urlSessao(mesaId, sid)}/encontros`, { corpo: { nome } }), (e) => e)

export function useApagarEncontro(mesaId: string, sid: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => chamar<void>(`${urlSessao(mesaId, sid)}/encontros/${id}`, { metodo: 'DELETE' }),
    onSuccess: (_, id) => {
      cliente.removeQueries({ queryKey: chaveEncontro(mesaId, sid, id) })
      return cliente.invalidateQueries({ queryKey: chaveSessao(mesaId, sid), exact: true })
    },
  })
}

type AcaoNoEncontro =
  | { tipo: 'adicionar'; origem: 'inimigo' | 'npc' | 'srd'; id: string; quantidade: number }
  | { tipo: 'remover'; combatente: string }
  | { tipo: 'marcas'; combatente: string; pv_marcados: number; pf_marcados: number }
  | { tipo: 'condicao'; combatente: string; condicao: string }
  | { tipo: 'tirar_condicao'; combatente: string; condicao: string }
  | { tipo: 'esconder'; combatente: string; escondido: boolean }
  | { tipo: 'visivel'; visivel: boolean }

/** Ações que devolvem o encontro inteiro: o cache é trocado pela resposta. */
export function useAcaoNoEncontro(mesaId: string, sid: string, encontroId: string) {
  const base = `${urlSessao(mesaId, sid)}/encontros/${encontroId}/combatentes`
  return useMutacaoEncontro(mesaId, sid, (a: AcaoNoEncontro) => {
    switch (a.tipo) {
      case 'adicionar': return chamar<Encontro>(base, { corpo: { origem: a.origem, id: a.id, quantidade: a.quantidade } })
      case 'remover': return chamar<Encontro>(`${base}/${a.combatente}`, { metodo: 'DELETE' })
      case 'marcas': return chamar<Encontro>(`${base}/${a.combatente}/marcas`,
        { metodo: 'PUT', corpo: { pv_marcados: a.pv_marcados, pf_marcados: a.pf_marcados } })
      case 'condicao': return chamar<Encontro>(`${base}/${a.combatente}/condicoes`, { corpo: { condicao: a.condicao } })
      case 'tirar_condicao': return chamar<Encontro>(
        `${base}/${a.combatente}/condicoes/${encodeURIComponent(a.condicao)}`, { metodo: 'DELETE' })
      case 'esconder': return chamar<Encontro>(`${base}/${a.combatente}/escondido`,
        { metodo: 'PUT', corpo: { escondido: a.escondido } })
      case 'visivel': return chamar<Encontro>(`${urlSessao(mesaId, sid)}/encontros/${encontroId}/visivel`,
        { metodo: 'PUT', corpo: { visivel: a.visivel } })
    }
  }, (e) => e)
}

/** O que os jogadores veem (encontros à mostra e NPCs conhecidos). Atualiza ao vivo (api/aoVivo.ts). */
export const useRevelado = (mesaId: string) =>
  useQuery({
    queryKey: ['mesas', mesaId, 'revelado'],
    queryFn: () => chamar<VistaDosJogadores>(`/mesas/${mesaId}/revelado`),
  })

// --- Quadros (mapa mental) -------------------------------------------------------------------

const chaveQuadro = (mesaId: string, sid: string) => ['mesas', mesaId, 'sessoes', sid, 'quadro'] as const

export const useQuadro = (mesaId: string, sid: string) =>
  useQuery({ queryKey: chaveQuadro(mesaId, sid), queryFn: () => chamar<QuadroSaida>(`${urlSessao(mesaId, sid)}/quadro`) })

/** Grava o quadro inteiro. A tela mantém o próprio estado (para não pular
    enquanto se arrasta); da resposta só aproveita os itens resolvidos. */
export function useSalvarQuadro(mesaId: string, sid: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (q: { cartoes: Cartao[]; ligacoes: Ligacao[] }) =>
      chamar<QuadroSaida>(`${urlSessao(mesaId, sid)}/quadro`, { metodo: 'PUT', corpo: q }),
    onSuccess: (q) => {
      cliente.setQueryData(chaveQuadro(mesaId, sid), q)
      return cliente.invalidateQueries({ queryKey: ['mesas', mesaId, 'quadro-da-campanha'] })
    },
  })
}

/** O revelado de todas as sessões (qualquer membro). Atualiza ao vivo (api/aoVivo.ts). */
export const useQuadroDaCampanha = (mesaId: string) =>
  useQuery({
    queryKey: ['mesas', mesaId, 'quadro-da-campanha'],
    queryFn: () => chamar<QuadroDaSessao[]>(`/mesas/${mesaId}/quadro-da-campanha`),
  })

/** Torna um NPC conhecido (ou não) pelos jogadores. */
export function useRevelarNpc(mesaId: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ npcId, revelado }: { npcId: string; revelado: boolean }) =>
      chamar<Npc>(`/mesas/${mesaId}/npcs/${npcId}/revelado`, { metodo: 'PUT', corpo: { revelado } }),
    onSuccess: () => Promise.all([
      cliente.invalidateQueries({ queryKey: chavesMesa.npcs(mesaId) }),
      cliente.invalidateQueries({ queryKey: ['mesas', mesaId, 'revelado'] }),
    ]),
  })
}

/** Como ficaria o guia com estes inimigos (nada é salvo): mostra o custo antes de adicionar. */
export const useSimularGuia = (mesaId: string, sid: string, encontroId: string,
  pedido: { origem: 'inimigo' | 'npc' | 'srd'; id: string; quantidade: number } | null) =>
  useQuery({
    queryKey: [...chaveEncontro(mesaId, sid, encontroId), 'simular', pedido],
    queryFn: () => chamar<GuiaDeBatalha>(`${urlSessao(mesaId, sid)}/encontros/${encontroId}/guia/simular`, { corpo: pedido }),
    enabled: !!pedido,
  })

/** Escolhas do Guia de Batalha; a API devolve o encontro com o guia recalculado. */
export const useGuiaDeBatalha = (mesaId: string, sid: string, encontroId: string) =>
  useMutacaoEncontro(mesaId, sid, (opcoes: OpcoesDoGuia) =>
    chamar<Encontro>(`${urlSessao(mesaId, sid)}/encontros/${encontroId}/guia`, { metodo: 'PUT', corpo: opcoes }), (e) => e)

export const useDanoEmCombatente = (mesaId: string, sid: string, encontroId: string) =>
  useMutacaoEncontro(mesaId, sid, ({ combatente, dano, resistente }: { combatente: string; dano: number; resistente: boolean }) =>
    chamar<{ resultado: ResultadoDanoAdversario; encontro: Encontro }>(
      `${urlSessao(mesaId, sid)}/encontros/${encontroId}/combatentes/${combatente}/dano`, { corpo: { dano, resistente } }),
  (r) => r.encontro)
const chaveFichaNaMesa = (mesaId: string, pid: string) => ['mesas', mesaId, 'personagens', pid] as const

/** Ficha de um personagem da mesa, como o mestre vê (permissão ver_fichas). */
export const useFichaNaMesa = (mesaId: string, pid: string, ativo = true) =>
  useQuery({
    queryKey: chaveFichaNaMesa(mesaId, pid),
    queryFn: () => chamar<Ficha>(`/mesas/${mesaId}/personagens/${pid}`),
    enabled: ativo,
  })

type AcaoNoPersonagem =
  | { tipo: 'dano'; dano: number; usar_armadura: boolean }
  | { tipo: 'condicao'; condicao: string }
  | { tipo: 'tirar_condicao'; condicao: string }

export function useAcaoNoPersonagem(mesaId: string, pid: string) {
  const cliente = useQueryClient()
  const base = `/mesas/${mesaId}/personagens/${pid}`
  return useMutation({
    mutationFn: async (a: AcaoNoPersonagem): Promise<{ ficha: Ficha; resultado?: ResultadoDano }> => {
      if (a.tipo === 'dano') {
        return chamar<{ ficha: Ficha; resultado: ResultadoDano }>(`${base}/dano`,
          { corpo: { dano: a.dano, usar_armadura: a.usar_armadura } })
      }
      const ficha = a.tipo === 'condicao'
        ? await chamar<Ficha>(`${base}/condicoes`, { corpo: { condicao: a.condicao } })
        : await chamar<Ficha>(`${base}/condicoes/${encodeURIComponent(a.condicao)}`, { metodo: 'DELETE' })
      return { ficha }
    },
    onSuccess: ({ ficha }) => cliente.setQueryData(chaveFichaNaMesa(mesaId, pid), ficha),
  })
}

export const useApagarNpc = (mesaId: string) =>
  useMutacaoNpc(mesaId, (npcId: string) => chamar<void>(`/mesas/${mesaId}/npcs/${npcId}`, { metodo: 'DELETE' }))

// --- Inventário --------------------------------------------------------------------------------

export const useItensSrd = () =>
  useQuery({ queryKey: ['srd', 'itens'], queryFn: () => chamar<Item[]>('/srd/itens'), staleTime: UMA_HORA })

const chaveInventario = (id: string) => ['personagens', id, 'inventario'] as const
const chaveInventarioNaMesa = (mesaId: string, pid: string) => ['mesas', mesaId, 'personagens', pid, 'inventario'] as const

export const useInventario = (id: string) =>
  useQuery({ queryKey: chaveInventario(id), queryFn: () => chamar<Inventario>(`/personagens/${id}/inventario`) })

/** Ações que mudam o inventário (do dono ou do mestre com "dar_itens"). */
export type AcaoNoInventario =
  | { tipo: 'ouro'; punhados: number; moedas: number }
  | { tipo: 'usar_moedas'; usar: boolean }
  | { tipo: 'item'; item_id: string; quantidade: number }
  | { tipo: 'tirar_item'; item_id: string; quantidade: number }
  | { tipo: 'livre'; nome: string; descricao: string; quantidade: number }
  | { tipo: 'tirar_livre'; id: string; quantidade: number }
  | { tipo: 'arma'; arma_id: string }
  | { tipo: 'tirar_arma'; indice: number }
  | { tipo: 'reliquia'; experiencia: string | null }

function chamarInventario(base: string, a: AcaoNoInventario) {
  switch (a.tipo) {
    case 'ouro': return chamar<Inventario>(`${base}/ouro`, { corpo: { punhados: a.punhados, moedas: a.moedas } })
    case 'usar_moedas': return chamar<Inventario>(`${base}/moedas`, { metodo: 'PUT', corpo: { usar: a.usar } })
    case 'item': return chamar<Inventario>(`${base}/itens`, { corpo: { item_id: a.item_id, quantidade: a.quantidade } })
    case 'tirar_item': return chamar<Inventario>(`${base}/itens/${a.item_id}?quantidade=${a.quantidade}`, { metodo: 'DELETE' })
    case 'livre': return chamar<Inventario>(`${base}/livres`,
      { corpo: { nome: a.nome, descricao: a.descricao, quantidade: a.quantidade } })
    case 'tirar_livre': return chamar<Inventario>(`${base}/livres/${a.id}?quantidade=${a.quantidade}`, { metodo: 'DELETE' })
    case 'arma': return chamar<Inventario>(`${base}/armas`, { corpo: { arma_id: a.arma_id } })
    case 'tirar_arma': return chamar<Inventario>(`${base}/armas/${a.indice}`, { metodo: 'DELETE' })
    case 'reliquia': return chamar<Inventario>(`${base}/reliquia`, { metodo: 'PUT', corpo: { experiencia: a.experiencia } })
  }
}

export function useAcaoNoInventario(id: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (a: AcaoNoInventario) => chamarInventario(`/personagens/${id}/inventario`, a),
    onSuccess: (inv) => {
      cliente.setQueryData(chaveInventario(id), inv)
      // relíquia muda atributo/Experiência na ficha
      return cliente.invalidateQueries({ queryKey: chaves.ficha(id) })
    },
  })
}

export function useUsarConsumivel(id: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: ({ item_id, rolagem, escolha }: { item_id: string; rolagem: number | null; escolha: 'PV' | 'PF' | null }) =>
      chamar<UsoDeConsumivel>(`/personagens/${id}/inventario/itens/${item_id}/usar`, { corpo: { rolagem, escolha } }),
    onSuccess: (r) => {
      cliente.setQueryData(chaveInventario(id), r.inventario)
      cliente.setQueryData(chaves.ficha(id), r.ficha)
    },
  })
}

export function useTrocarArma(id: string) {
  const invalidar = useInvalidarPersonagem()
  return useMutation({
    mutationFn: ({ indice, em_perigo }: { indice: number; em_perigo: boolean }) =>
      chamar<Ficha>(`/personagens/${id}/inventario/armas/${indice}/trocar`, { corpo: { em_perigo } }),
    onSuccess: () => invalidar(id),
  })
}

export const useInventarioNaMesa = (mesaId: string, pid: string, ativo = true) =>
  useQuery({
    queryKey: chaveInventarioNaMesa(mesaId, pid),
    queryFn: () => chamar<Inventario>(`/mesas/${mesaId}/personagens/${pid}/inventario`),
    enabled: ativo,
  })

/** Mestre com "dar_itens": dá ou tira ouro e itens de um personagem da mesa. */
export function useDarNoInventario(mesaId: string, pid: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (a: AcaoNoInventario) => chamarInventario(`/mesas/${mesaId}/personagens/${pid}/inventario`, a),
    onSuccess: (inv) => cliente.setQueryData(chaveInventarioNaMesa(mesaId, pid), inv),
  })
}

// --- Lojas da sessão -----------------------------------------------------------------------------

const chaveLojas = (mesaId: string, sid: string) => ['mesas', mesaId, 'sessoes', sid, 'lojas'] as const

export const useLojas = (mesaId: string, sid: string) =>
  useQuery({ queryKey: chaveLojas(mesaId, sid), queryFn: () => chamar<Loja[]>(`${urlSessao(mesaId, sid)}/lojas`) })

export type AcaoNaLoja =
  | { tipo: 'criar'; nome: string }
  | { tipo: 'salvar'; id: string; nome: string; visivel: boolean; itens: ItemDaLojaEntrada[] }
  | { tipo: 'apagar'; id: string }

export function useAcaoNaLoja(mesaId: string, sid: string) {
  const cliente = useQueryClient()
  const base = `${urlSessao(mesaId, sid)}/lojas`
  return useMutation({
    mutationFn: (a: AcaoNaLoja): Promise<Loja | void> => {
      if (a.tipo === 'criar') return chamar<Loja>(base, { corpo: { nome: a.nome } })
      if (a.tipo === 'apagar') return chamar<void>(`${base}/${a.id}`, { metodo: 'DELETE' })
      return chamar<Loja>(`${base}/${a.id}`, { metodo: 'PUT', corpo: { nome: a.nome, visivel: a.visivel, itens: a.itens } })
    },
    onSuccess: () => cliente.invalidateQueries({ queryKey: chaveLojas(mesaId, sid) }),
  })
}

export function useVender(mesaId: string, sid: string, lojaId: string) {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: (v: { item_id: string; personagem_id: string; quantidade: number }) =>
      chamar<Venda>(`${urlSessao(mesaId, sid)}/lojas/${lojaId}/vender`, { corpo: v }),
    onSuccess: (r, v) => {
      cliente.setQueryData(chaveInventarioNaMesa(mesaId, v.personagem_id), r.inventario)
      return cliente.invalidateQueries({ queryKey: chaveLojas(mesaId, sid) })
    },
  })
}

/** Ficha simplificada de um personagem da mesa (qualquer membro vê; atualiza ao vivo). */
export const useFichaResumida = (mesaId: string, pid: string, ativo = true) =>
  useQuery({
    queryKey: ['mesas', mesaId, 'personagens', pid, 'resumo'],
    queryFn: () => chamar<FichaResumida>(`/mesas/${mesaId}/personagens/${pid}/resumo`),
    enabled: ativo,
  })
