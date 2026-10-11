// Textos em português para os códigos que vêm da API.
import type { AlvoFeroz, Opcao, OpcaoTreino, TipoDano, Traco } from '../api/tipos'

export const TRACOS: Traco[] = ['AGILITY', 'STRENGTH', 'FINESSE', 'INSTINCT', 'PRESENCE', 'KNOWLEDGE']

export const NOME_TRACO: Record<Traco, string> = {
  AGILITY: 'Agilidade',
  STRENGTH: 'Força',
  FINESSE: 'Acuidade',
  INSTINCT: 'Instinto',
  PRESENCE: 'Presença',
  KNOWLEDGE: 'Conhecimento',
}

/** Verbos da ficha oficial, para lembrar para que serve cada traço. */
export const USO_TRACO: Record<Traco, string> = {
  AGILITY: 'Correr, saltar, manobrar',
  STRENGTH: 'Erguer, golpear, agarrar',
  FINESSE: 'Controlar, esconder, consertar',
  INSTINCT: 'Perceber, sentir, navegar',
  PRESENCE: 'Encantar, atuar, enganar',
  KNOWLEDGE: 'Lembrar, analisar, compreender',
}

export const NOME_OPCAO: Record<Opcao, string> = {
  TRACOS: '+1 em dois traços não marcados',
  PV: '+1 espaço de Ponto de Vida',
  ESTRESSE: '+1 espaço de Fadiga',
  EXPERIENCIAS: '+1 em duas Experiências',
  CARTA_DOMINIO: 'Carta de domínio adicional',
  EVASAO: '+1 de Evasão',
  SUBCLASSE: 'Próxima carta de subclasse',
  PROFICIENCIA: '+1 de Proficiência',
  MULTICLASSE: 'Multiclasse',
}

export const NOME_TREINO: Record<OpcaoTreino, string> = {
  INTELIGENTE: 'Inteligente: +1 numa Experiência do companheiro',
  LUZ_NA_ESCURIDAO: 'Luz na Escuridão: +1 espaço de Esperança para você',
  CONFORTO: 'Conforto Animal: 1x por descanso, Esperança ou alívio',
  BLINDADO: 'Blindado: usa sua armadura no lugar da Fadiga dele',
  FEROZ: 'Feroz: dado de dano ou alcance sobe um passo',
  RESILIENTE: 'Resiliente: +1 espaço de Fadiga',
  VINCULO: 'Vínculo: pode te levantar quando você cair',
  ATENTO: 'Atento: +2 de Evasão',
}

export const NOME_ALVO_FEROZ: Record<AlvoFeroz, string> = { DANO: 'Dado de dano', ALCANCE: 'Alcance' }

export const NOME_TIPO_DANO: Record<TipoDano, string> = {
  PHYSICAL: 'físico',
  MAGICAL: 'mágico',
  PHYSICAL_OR_MAGICAL: 'físico ou mágico',
}

export const NOME_ALCANCE: Record<string, string> = {
  MELEE: 'Corpo a corpo',
  VERY_CLOSE: 'Muito próximo',
  CLOSE: 'Próximo',
  FAR: 'Distante',
  VERY_FAR: 'Muito distante',
}

/** Condições padrão (o resto são condições de características, já em texto). */
export const NOME_CONDICAO: Record<string, string> = {
  OCULTO: 'Oculto', CONTIDO: 'Contido', VULNERAVEL: 'Vulnerável',
}

export const condicao = (c: string) => NOME_CONDICAO[c] ?? c

export const NOME_ESTAGIO: Record<string, string> = {
  fundacao: 'Fundação', especializacao: 'Especialização', maestria: 'Maestria',
}

export const comSinal = (n: number) => (n > 0 ? `+${n}` : `${n}`)
