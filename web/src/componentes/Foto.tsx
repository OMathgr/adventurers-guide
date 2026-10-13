// Foto de personagem, NPC ou inimigo: mostra a imagem enviada ou as iniciais
// do nome; e o botão para enviar/trocar/tirar a foto.
import { useRef, useState } from 'react'

import { urlDaImagem } from '../api/cliente'
import { useEnviarImagem } from '../api/consultas'
import { Aviso, Botao } from './ui'

const TAMANHOS = { p: 'h-10 w-10 text-sm', m: 'h-16 w-16 text-lg', g: 'h-24 w-24 text-2xl' }

function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean)
  return ((partes[0]?.[0] ?? '?') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase()
}

export function Foto({ id, nome, tamanho = 'm' }: { id?: string | null; nome: string; tamanho?: keyof typeof TAMANHOS }) {
  const classe = `${TAMANHOS[tamanho]} shrink-0 rounded-xl border border-borda object-cover`
  if (id) return <img src={urlDaImagem(id)} alt={`Foto de ${nome}`} className={classe} />
  return (
    <span aria-hidden className={`${classe} flex items-center justify-center bg-superficie-2 font-titulo text-texto-suave`}>
      {iniciais(nome)}
    </span>
  )
}

const TIPOS = ['image/jpeg', 'image/png', 'image/webp']
const MAXIMO = 2 * 1024 * 1024

/** Escolher arquivo, enviar e devolver o id. O servidor confere tipo e tamanho
    de novo; aqui só evita a viagem com um aviso imediato. */
export function EnviarFoto({ temFoto, aoMudar, desabilitado }:
  { temFoto: boolean; aoMudar: (imagemId: string | null) => void; desabilitado?: boolean }) {
  const entrada = useRef<HTMLInputElement>(null)
  const enviar = useEnviarImagem()
  const [aviso, setAviso] = useState<string | null>(null)

  function escolher(arquivo: File | undefined) {
    if (!arquivo) return
    enviar.reset()
    setAviso(null)
    if (!TIPOS.includes(arquivo.type)) return setAviso('Escolha uma imagem JPG, PNG ou WebP.')
    if (arquivo.size > MAXIMO) return setAviso('A imagem passa de 2 MB. Reduza o tamanho e tente de novo.')
    enviar.mutate(arquivo, { onSuccess: ({ id }) => aoMudar(id) })
  }

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap gap-1">
        <input ref={entrada} type="file" accept={TIPOS.join(',')} className="sr-only" aria-label="Arquivo da foto"
          onChange={(e) => { escolher(e.target.files?.[0]); e.target.value = '' }} />
        <Botao type="button" variante="secundario" className="!px-2 !py-1 text-xs"
          disabled={desabilitado || enviar.isPending} onClick={() => entrada.current?.click()}>
          {enviar.isPending ? 'Enviando…' : temFoto ? 'Trocar foto' : 'Enviar foto'}
        </Botao>
        {temFoto && (
          <Botao type="button" variante="fantasma" className="!px-2 !py-1 text-xs" disabled={desabilitado}
            onClick={() => aoMudar(null)}>Tirar foto</Botao>
        )}
      </div>
      <Aviso erro={enviar.error}>{aviso}</Aviso>
    </div>
  )
}
