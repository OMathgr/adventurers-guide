// Mapa tipo de cartão → componente, para o React Flow (fora de Cartoes.tsx por causa do fast refresh).
import { CartaoImagem, CartaoItem, CartaoNota, TituloDeRegiao } from './Cartoes'

export const TIPOS_DE_CARTAO = { nota: CartaoNota, item: CartaoItem, imagem: CartaoImagem, titulo: TituloDeRegiao }
