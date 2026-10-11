// Ajudas para os assistentes. As REGRAS de verdade ficam no motor (a API
// valida tudo); aqui só o que a tela precisa para guiar o jogador antes de
// enviar, sem duplicar validação que importa.
import type { OpcaoAvanco, ProximoNivel, Traco } from '../api/tipos'
import { TRACOS } from './rotulos'

/** Os valores que a criação distribui entre os seis atributos. */
export const VALORES_TRACOS = [2, 1, 1, 0, 0, -1] as const

export type Distribuicao = Partial<Record<Traco, number>>

/** Valores ainda livres, dado o que já foi atribuído. */
export function valoresRestantes(dist: Distribuicao): number[] {
  const restantes: number[] = [...VALORES_TRACOS]
  for (const valor of Object.values(dist)) {
    const i = restantes.indexOf(valor as number)
    if (i >= 0) restantes.splice(i, 1)
  }
  return restantes
}

export function distribuicaoCompleta(dist: Distribuicao): boolean {
  return TRACOS.every((t) => dist[t] !== undefined) && valoresRestantes(dist).length === 0
}

/** Cartas de domínio ativas ao mesmo tempo ("Mão e Reserva"); o motor tem o mesmo número em progressao.json. */
export const LIMITE_MAO = 5

/** Avanço escolhido na tela: a opção da API + uma chave para a lista. */
export type AvancoMarcado = OpcaoAvanco & { chave: string }

export function custoTotal(marcados: AvancoMarcado[]): number {
  return marcados.reduce((soma, a) => soma + a.custo, 0)
}

/** Pode marcar mais uma vez esta opção? (custo cabe e ainda há quadradinho) */
export function podeMarcar(opcao: OpcaoAvanco, marcados: AvancoMarcado[], limite: number): boolean {
  const vezes = marcados.filter((m) => m.opcao === opcao.opcao && m.tier === opcao.tier).length
  return vezes < opcao.restantes && custoTotal(marcados) + opcao.custo <= limite
}

/** Quantos treinos o companheiro exige, conforme o que foi marcado. */
export function treinosExigidos(proximo: ProximoNivel, marcados: AvancoMarcado[]): number {
  const pegouSubclasse = marcados.some((m) => m.opcao === 'SUBCLASSE')
  return proximo.treinos + (pegouSubclasse ? proximo.treinos_extra_com_subclasse : 0)
}
