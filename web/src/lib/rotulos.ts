// Textos em português para os códigos que vêm da API.
import type {
  AlvoFeroz, Opcao, OpcaoTreino, Permissao, TipoAdversario, TipoDano, TipoHabilidade, Traco,
} from '../api/tipos'

export const TRACOS: Traco[] = ['AGILITY', 'STRENGTH', 'FINESSE', 'INSTINCT', 'PRESENCE', 'KNOWLEDGE']

export const NOME_TRACO: Record<Traco, string> = {
  AGILITY: 'Agilidade',
  STRENGTH: 'Força',
  FINESSE: 'Acuidade',
  INSTINCT: 'Instinto',
  PRESENCE: 'Presença',
  KNOWLEDGE: 'Conhecimento',
}

/** Verbos da ficha oficial, para lembrar para que serve cada atributo. */
export const USO_TRACO: Record<Traco, string> = {
  AGILITY: 'Correr, saltar, manobrar',
  STRENGTH: 'Erguer, golpear, agarrar',
  FINESSE: 'Controlar, esconder, consertar',
  INSTINCT: 'Perceber, sentir, navegar',
  PRESENCE: 'Encantar, atuar, enganar',
  KNOWLEDGE: 'Lembrar, analisar, compreender',
}

export const NOME_OPCAO: Record<Opcao, string> = {
  TRACOS: '+1 em dois atributos não marcados',
  PV: '+1 espaço de Ponto de Vida',
  ESTRESSE: '+1 espaço de Fadiga',
  EXPERIENCIAS: '+1 em duas Experiências',
  CARTA_DOMINIO: 'Carta de domínio adicional',
  EVASAO: '+1 de Evasão',
  SUBCLASSE: 'Carta de subclasse aprimorada',
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

// --- Mesas e área do mestre ---------------------------------------------------------------

export const NOME_PAPEL: Record<string, string> = { jogador: 'Jogador', mestre: 'Mestre' }

export const NOME_PERMISSAO: Record<Permissao, string> = {
  ver_fichas: 'Ver as fichas dos personagens',
  aplicar_dano: 'Aplicar dano',
  aplicar_condicoes: 'Aplicar e remover condições',
  preparar: 'Criar e editar inimigos, NPCs e encontros',
  nivel: 'Definir o nível da mesa',
  dar_itens: 'Dar itens e ouro (e vender nas lojas)',
}

export const TIPOS_ADVERSARIO: TipoAdversario[] = [
  'PADRAO', 'BRUTAMONTES', 'ATIRADOR', 'ESPREITADOR', 'SUPORTE', 'LIDER', 'LACAIO', 'HORDA', 'SOCIAL', 'SOLO',
]

/** Nomes da edição brasileira (os códigos continuam os do projeto). */
export const NOME_TIPO_ADVERSARIO: Record<TipoAdversario, string> = {
  PADRAO: 'Comum',
  BRUTAMONTES: 'Brutamonte',
  ATIRADOR: 'Atirador',
  ESPREITADOR: 'Oportunista',
  SUPORTE: 'Assistente',
  LIDER: 'Líder',
  LACAIO: 'Lacaio',
  HORDA: 'Horda',
  SOCIAL: 'Manipulador',
  SOLO: 'Solo',
}

/** Plural para o Guia de Batalha ("2 Brutamontes"). */
export const PLURAL_TIPO_ADVERSARIO: Record<TipoAdversario, string> = {
  PADRAO: 'Comuns', BRUTAMONTES: 'Brutamontes', ATIRADOR: 'Atiradores', ESPREITADOR: 'Oportunistas',
  SUPORTE: 'Assistentes', LIDER: 'Líderes', LACAIO: 'Lacaios', HORDA: 'Hordas', SOCIAL: 'Manipuladores', SOLO: 'Solos',
}

/** O que os jogadores veem da vida de um inimigo (terços dos PV que restam). */
export const NOME_VITALIDADE: Record<string, string> = {
  vida_cheia: 'Vida cheia', metade_da_vida: 'Metade da vida', vida_baixa: 'Vida baixa', derrotado: 'Derrotado',
}

/** Gravidade do dano (quantos PV marca, pelos limiares). */
export const NOME_GRAVIDADE: Record<number, string> = { 0: 'sem dano', 1: 'Menor', 2: 'Maior', 3: 'Grave', 4: 'Massivo' }

export const NOME_TIPO_HABILIDADE: Record<TipoHabilidade, string> = {
  PASSIVA: 'Passiva', ACAO: 'Ação', REACAO: 'Reação',
}

// --- Repouso e morte (nomes do livro básico brasileiro) --------------------------------------------

/** Nome do movimento de repouso; no descanso longo as recuperações limpam tudo. */
export function nomeDoMovimento(m: string, longo: boolean): string {
  const curto: Record<string, string> = {
    CUIDAR_FERIDAS: 'Tratar Feridas', ALIVIAR_ESTRESSE: 'Reduzir Fadiga', REPARAR_ARMADURA: 'Reparar Armadura',
    PREPARAR: 'Preparar-se', PREPARAR_EM_GRUPO: 'Preparar-se em grupo', PROJETO: 'Trabalhar em um Projeto',
  }
  const dosLongos: Record<string, string> = {
    CUIDAR_FERIDAS: 'Tratar Todas as Feridas', ALIVIAR_ESTRESSE: 'Zerar Fadiga', REPARAR_ARMADURA: 'Reparar Armadura por Completo',
  }
  return (longo && dosLongos[m]) || curto[m] || m
}

export function efeitoDoMovimento(m: string, longo: boolean): string {
  const recupera = longo ? 'tudo' : '1d4 + patamar'
  return ({
    CUIDAR_FERIDAS: `Limpa ${recupera} de PV (seu ou de um aliado).`,
    ALIVIAR_ESTRESSE: `Limpa ${recupera} de PF.`,
    REPARAR_ARMADURA: `Limpa ${recupera} de espaços de armadura (sua ou de um aliado).`,
    PREPARAR: '+1 de Esperança.',
    PREPARAR_EM_GRUPO: '+2 de Esperança para cada um que se preparar junto (sozinho, vale +1).',
    PROJETO: 'Avança um projeto de longo prazo (com o aval do mestre).',
  } as Record<string, string>)[m] ?? ''
}

export const NOME_MOVIMENTO_MORTE: Record<string, string> = {
  SACRIFICIO_GLORIOSO: 'Sacrifício Glorioso', EVITAR_A_MORTE: 'Evitar a Morte', ARRISCAR_TUDO: 'Arriscar Tudo',
}

export const NOME_IMPACTO: Record<string, string> = {
  '': 'A definir', FISICA: 'Cicatriz física', MEMORIA: 'Memória dolorosa', MEDO: 'Medo paralisante', OUTRO: 'Outro',
}
