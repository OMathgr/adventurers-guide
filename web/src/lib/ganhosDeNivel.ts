// O que mudou na ficha entre um nível e o seguinte, em frases para mostrar ao
// jogador. Só compara as duas fichas que o motor calculou; nenhuma regra aqui.
import type { Ficha } from '../api/tipos'
import { comSinal, NOME_TRACO, TRACOS } from './rotulos'

const aumento = (d: number, singular: string, plural: string) => `+${d} ${d === 1 ? singular : plural}`

export function ganhosDeNivel(antes: Ficha, depois: Ficha, nomeDaCarta: (id: string) => string | undefined): string[] {
  const ganhos: string[] = []

  const tinha = new Set([...antes.cartas_ativas, ...antes.cartas_cofre])
  for (const id of [...depois.cartas_ativas, ...depois.cartas_cofre]) {
    if (!tinha.has(id)) ganhos.push(`Nova carta: ${nomeDaCarta(id) ?? id}`)
  }

  for (const [nome, valor] of Object.entries(depois.experiencias)) {
    const era = antes.experiencias[nome]
    if (era === undefined) ganhos.push(`Nova Experiência: ${nome} (${comSinal(valor)})`)
    else if (valor !== era) ganhos.push(`${nome}: ${comSinal(era)} → ${comSinal(valor)}`)
  }

  for (const t of TRACOS) {
    const d = (depois.tracos[t] ?? 0) - (antes.tracos[t] ?? 0)
    if (d > 0) ganhos.push(`+${d} em ${NOME_TRACO[t]}`)
  }

  const espacos = [
    [depois.pv_max - antes.pv_max, 'espaço de Ponto de Vida', 'espaços de Ponto de Vida'],
    [depois.estresse_max - antes.estresse_max, 'espaço de Fadiga', 'espaços de Fadiga'],
    [depois.esperanca_max - antes.esperanca_max, 'espaço de Esperança', 'espaços de Esperança'],
    [depois.evasao - antes.evasao, 'de Evasão', 'de Evasão'],
    [depois.proficiencia - antes.proficiencia, 'de Proficiência', 'de Proficiência'],
  ] as const
  for (const [d, singular, plural] of espacos) {
    if (d > 0) ganhos.push(aumento(d, singular, plural))
  }

  if (depois.limiar_maior !== antes.limiar_maior || depois.limiar_grave !== antes.limiar_grave) {
    ganhos.push(`Limiares de dano: ${antes.limiar_maior}/${antes.limiar_grave} → ${depois.limiar_maior}/${depois.limiar_grave}`)
  }
  return ganhos
}
