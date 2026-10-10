// A ficha guarda ids (classe, cartas, ancestralidade...). Este hook troca
// pelos nomes de exibição usando o catálogo do SRD (em cache).
import { useAncestralidades, useCartas, useClasses, useComunidades, useSubclasses } from '../api/consultas'
import type { CartaDeDominio, Ficha } from '../api/tipos'
import { nomeClasse } from './rotulos'

export function useNomes(ficha: Ficha | undefined) {
  const classes = useClasses()
  const subclasses = useSubclasses(ficha?.classe)
  const multiclasse = (ficha?.multiclasse ?? null) as { classe: string; subclasse: string; dominio: string } | null
  const subclassesMulti = useSubclasses(multiclasse?.classe)
  const ancestralidades = useAncestralidades()
  const comunidades = useComunidades()
  const cartas = useCartas()

  const porId = <T extends { id: string; nome: string }>(lista: T[] | undefined, id: string | null | undefined) =>
    lista?.find((x) => x.id === id)

  return {
    classe: (id: string) => nomeClasse(porId(classes.data, id)?.nome ?? ''),
    subclasse: (id: string) => porId(subclasses.data, id)?.nome ?? porId(subclassesMulti.data, id)?.nome ?? '',
    ancestralidade: (id: string | null | undefined) => porId(ancestralidades.data, id)?.nome ?? '',
    comunidade: (id: string) => porId(comunidades.data, id)?.nome ?? '',
    carta: (id: string): CartaDeDominio | undefined => porId(cartas.data, id),
    multiclasse,
  }
}
