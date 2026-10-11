// Valores iniciais de um adversário criado do zero (números típicos de patamar 1).
import type { Adversario } from '../api/tipos'

export const INIMIGO_EM_BRANCO: Adversario = {
  nome: '', patamar: 1, tipo: 'PADRAO', dificuldade: 11, pv: 4, pf: 3,
  ataque: '+1', arma: '', alcance: 'MELEE', dano: '1d8+2', tipo_dano: 'PHYSICAL',
  limiar_maior: 6, limiar_grave: 11, descricao: '', motivacoes: '', experiencias: {}, habilidades: [],
  horda_por_pv: null, id: '', base_id: null, nome_original: '', arma_original: '',
}
