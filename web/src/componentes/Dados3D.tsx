// Dados 3D caindo na mesa (three.js + física), mostrando os resultados que o
// servidor já rolou (a biblioteca aceita o resultado decidido: "1d12+1d12@7,3").
// Cada grupo tem uma cor (Esperança, Medo, outros). A biblioteca é pesada: só
// carrega quando este componente aparece.
//
// Cores por dado: a biblioteca pinta todos de uma rolagem com a mesma cor, e
// `add()` no meio de uma rolagem limpa a mesa. Então todos caem num `roll()` só
// e, logo depois de nascerem (é na hora), cada dado ganha o material da cor dele.
import { useEffect, useId, useRef, useState } from 'react'

import { corDoNumero, type GrupoDeDados, notacao } from '../lib/coresDosDados'

type Caixa = import('@3d-dice/dice-box-threejs').default

/** O que usamos de dentro da biblioteca (não é API pública, mas é estável nesta versão fixa). */
type Interna = {
  diceList: { notation: { type: string }; material: unknown }[]
  colorData: unknown
  DiceColors: { makeColorSet: (c: unknown) => Promise<unknown> }
  DiceFactory: {
    applyColorSet: (c: unknown) => void
    setMaterialInfo: () => void
    get: (tipo: string) => unknown
    createMaterials: (def: unknown, a: number, b: number) => unknown
    baseScale: number
  }
}

function conjunto(cor: string) {
  const numero = corDoNumero(cor)
  return { name: `ag-${cor}`, foreground: numero, background: cor, outline: numero === '#ffffff' ? '#000000' : '#ffffff',
    texture: 'none', material: 'plastic' }
}

/** `chave` muda a cada rolagem nova: aí os `grupos` caem na mesa. */
export default function Dados3D({ grupos, chave, aoTerminar }: {
  grupos: GrupoDeDados[]; chave: string | null; aoTerminar?: () => void
}) {
  const id = `dados3d-${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  const caixa = useRef<Caixa | null>(null)
  const [pronta, setPronta] = useState(false)
  const [falhou, setFalhou] = useState(false)

  useEffect(() => {
    let cancelado = false
    import('@3d-dice/dice-box-threejs').then(async ({ default: DiceBox }) => {
      if (cancelado) return
      const nova = new DiceBox(`#${id}`, { sounds: false, shadows: true, light_intensity: 0.9, gravity_multiplier: 400,
        baseScale: 90, strength: 1.2, theme_customColorset: conjunto('#d8dde8') })
      await nova.initialize()
      if (!cancelado) { caixa.current = nova; setPronta(true) }
    }).catch(() => setFalhou(true))   // sem WebGL (ou sem a biblioteca): o resultado continua no registro
    return () => { cancelado = true }
  }, [id])

  useEffect(() => {
    const c = caixa.current
    if (!pronta || !c || !chave) return
    const interna = c as unknown as Interna
    let cancelado = false
    ;(async () => {
      // uma notação só, na ordem dos grupos; lembra de que grupo é cada dado
      const partes = grupos.map((g) => ({ g, n: notacao(g) })).filter((x) => x.n)
      if (partes.length === 0) return
      const dados = partes.map((x) => x.n.split('@')[0]).join('+')
      const valores = partes.map((x) => x.n.split('@')[1]).join(',')
      const grupoDoDado = partes.flatMap((x, i) => x.n.split('@')[0].split('+').map(() => i))
      const cores = await Promise.all(partes.map((x) => interna.DiceColors.makeColorSet(conjunto(x.g.cor))))
      if (cancelado) return
      const f = interna.DiceFactory
      f.applyColorSet(cores[0])
      interna.colorData = cores[0]
      const fim = c.roll(`${dados}@${valores}`)
      interna.diceList.forEach((d, i) => {   // os dados já nasceram: pinta os dos outros grupos
        const g = grupoDoDado[i] ?? 0
        if (g === 0) return
        f.applyColorSet(cores[g])
        f.setMaterialInfo()
        d.material = f.createMaterials(f.get(d.notation.type), f.baseScale / 2, 1)
      })
      await fim
      if (!cancelado) aoTerminar?.()
    })()
    return () => { cancelado = true }
    // grupos acompanham a chave: só rola de novo quando ela muda
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, pronta])

  if (falhou) return null
  return (
    <div id={id} aria-hidden
      className="pointer-events-none h-56 w-full max-w-full overflow-hidden rounded-2xl border border-borda bg-fundo/60 sm:h-64 [&>canvas]:!h-full [&>canvas]:!w-full" />
  )
}
