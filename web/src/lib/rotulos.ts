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
  PV: '+1 espaço de Pontos de Vida',
  ESTRESSE: '+1 espaço de Estresse',
  EXPERIENCIAS: '+1 em duas Experiências',
  CARTA_DOMINIO: 'Carta de domínio adicional',
  EVASAO: '+1 de Evasão',
  SUBCLASSE: 'Próxima carta de subclasse',
  PROFICIENCIA: '+1 de Proficiência',
  MULTICLASSE: 'Multiclasse',
}

export const NOME_TREINO: Record<OpcaoTreino, string> = {
  INTELIGENTE: 'Intelligent: +1 numa Experiência do companheiro',
  LUZ_NA_ESCURIDAO: 'Light in the Dark: +1 espaço de Esperança para você',
  CONFORTO: 'Creature Comfort: 1x por descanso, Esperança ou alívio',
  BLINDADO: 'Armored: usa sua armadura no lugar do Estresse dele',
  FEROZ: 'Vicious: dado de dano ou alcance sobe um passo',
  RESILIENTE: 'Resilient: +1 espaço de Estresse',
  VINCULO: 'Bonded: pode te levantar quando você cair',
  ATENTO: 'Aware: +2 de Evasão',
}

export const NOME_ALVO_FEROZ: Record<AlvoFeroz, string> = { DANO: 'Dado de dano', ALCANCE: 'Alcance' }

export const NOME_TIPO_DANO: Record<TipoDano, string> = {
  PHYSICAL: 'físico',
  MAGICAL: 'mágico',
  PHYSICAL_OR_MAGICAL: 'físico ou mágico',
}

export const NOME_ALCANCE: Record<string, string> = {
  MELEE: 'Corpo a corpo',
  VERY_CLOSE: 'Muito perto',
  CLOSE: 'Perto',
  FAR: 'Longe',
  VERY_FAR: 'Muito longe',
}

export const NOME_DOMINIO: Record<string, string> = {
  ARCANA: 'Arcana', BLADE: 'Lâmina', BONE: 'Osso', CODEX: 'Códice', GRACE: 'Graça',
  MIDNIGHT: 'Meia-noite', SAGE: 'Sábio', SPLENDOR: 'Esplendor', VALOR: 'Valor',
}

export const NOME_ESTAGIO: Record<string, string> = {
  fundacao: 'Fundação', especializacao: 'Especialização', maestria: 'Maestria',
}

/** "BARD" -> "Bard" (o SRD guarda o nome da classe em maiúsculas). */
export const nomeClasse = (nome: string) => nome.charAt(0) + nome.slice(1).toLowerCase()

export const dominio = (d: string) => NOME_DOMINIO[d] ?? d

export const comSinal = (n: number) => (n > 0 ? `+${n}` : `${n}`)
