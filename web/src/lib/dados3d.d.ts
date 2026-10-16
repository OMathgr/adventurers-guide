// A biblioteca de dados 3D não traz tipos: só o que o app usa.
declare module '@3d-dice/dice-box-threejs' {
  export interface ConjuntoDeCores {
    name: string
    foreground: string
    background: string
    outline: string
    texture: string
    material: string
  }

  export default class DiceBox {
    constructor(seletor: string, config?: Record<string, unknown>)
    initialize(): Promise<void>
    updateConfig(config: { theme_customColorset?: ConjuntoDeCores } & Record<string, unknown>): Promise<void>
    roll(notacao: string): Promise<unknown>
    add(notacao: string): Promise<unknown>
    clearDice(): void
  }
}
