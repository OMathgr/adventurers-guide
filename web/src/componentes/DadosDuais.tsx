// Os dois d12 da dualidade: toda rolagem do jogo decide entre a Esperança e o Medo.
const CENTRO = 100

function ponto(raio: number, angulo: number) {
  const a = (angulo * Math.PI) / 180
  return `${(CENTRO + raio * Math.cos(a)).toFixed(2)} ${(CENTRO + raio * Math.sin(a)).toFixed(2)}`
}

const CONTORNO = Array.from({ length: 10 }, (_, i) => ponto(96, -90 + 36 * i))
const FACE = Array.from({ length: 5 }, (_, i) => ponto(50, -90 + 72 * i))
const fechado = (pontos: string[]) => `M${pontos.join('L')}Z`
const ARESTAS = `${fechado(CONTORNO)}${fechado(FACE)}${FACE.map((p, i) => `M${p}L${CONTORNO[i * 2]}`).join('')}`

/** Um d12 no viewBox de 200. `celebrando`: desenha-se na tela (ao subir de nível). */
export function D12({ cor, x = 0, y = 0, numero = 12, celebrando }: {
  cor: string; x?: number; y?: number; numero?: number; celebrando?: boolean
}) {
  return (
    <g transform={`translate(${x} ${y})`} stroke={cor} fill="none">
      <path d={fechado(CONTORNO)} fill={cor} fillOpacity="0.14" stroke="none" className={celebrando ? 'd12-face' : undefined} />
      <path d={ARESTAS} strokeWidth="1.6" strokeLinejoin="round" pathLength={1} className={celebrando ? 'd12-arestas' : undefined} />
      <text x={CENTRO} y={celebrando ? CENTRO + 19 : CENTRO + 10} textAnchor="middle" fill={cor} stroke="none"
        className={`font-titulo font-bold ${celebrando ? 'd12-numero text-[54px]' : 'text-[28px]'}`}>{numero}</text>
    </g>
  )
}

export default function DadosDuais({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 345 215" aria-hidden className={className}>
      <D12 cor="var(--esperanca)" x={0} y={0} />
      <D12 cor="var(--medo)" x={145} y={15} />
    </svg>
  )
}
