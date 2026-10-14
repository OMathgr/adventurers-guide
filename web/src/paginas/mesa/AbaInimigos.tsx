// Biblioteca de inimigos da mesa (privada dos mestres) + catálogo do SRD
// para copiar. Cópias e inimigos criados do zero têm o mesmo formato.
import { useMemo, useState } from 'react'

import {
  type ComVersao, useAdversariosSrd, useApagarInimigo, useCopiarDoSrd, useInimigo, useInimigos, useSalvarInimigo,
} from '../../api/consultas'
import type { Adversario, TipoAdversario } from '../../api/tipos'
import { AvisoDeConflito } from '../../componentes/Conflito'
import EditorInimigo from '../../componentes/EditorInimigo'
import FichaInimigo from '../../componentes/FichaInimigo'
import { Aviso, Botao, Campo, Carregando, Escolhivel, Selecao, Selo } from '../../componentes/ui'
import { semConflito } from '../../lib/conflito'
import { INIMIGO_EM_BRANCO } from '../../lib/inimigo'
import { NOME_TIPO_ADVERSARIO, TIPOS_ADVERSARIO } from '../../lib/rotulos'

type Painel =
  | { modo: 'vazio' }
  | { modo: 'mesa'; id: string }
  | { modo: 'srd'; id: string }
  | { modo: 'editar'; inimigo: Adversario }

function Linha({ nome, patamar, tipo, extra }: { nome: string; patamar: number; tipo: string; extra?: React.ReactNode }) {
  return (
    <span className="flex items-center justify-between gap-2">
      <span className="font-medium">{nome}</span>
      <span className="flex shrink-0 items-center gap-1.5 text-xs text-texto-suave">
        {extra}P{patamar} · {NOME_TIPO_ADVERSARIO[tipo as TipoAdversario] ?? tipo}
      </span>
    </span>
  )
}

function CatalogoSrd({ selecionado, aoEscolher }: { selecionado?: string; aoEscolher: (id: string) => void }) {
  const srd = useAdversariosSrd()
  const [busca, setBusca] = useState('')
  const [patamar, setPatamar] = useState('')
  const [tipo, setTipo] = useState('')

  const filtrados = useMemo(() => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    return (srd.data ?? []).filter((a) =>
      (!patamar || a.patamar === Number(patamar)) && (!tipo || a.tipo === tipo)
      && (!termo || a.nome.toLocaleLowerCase('pt-BR').includes(termo) || a.nome_original.toLowerCase().includes(termo)))
  }, [srd.data, busca, patamar, tipo])

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Campo rotulo="Buscar" className="col-span-2" value={busca} onChange={(e) => setBusca(e.target.value)}
          placeholder="Nome em português ou inglês" />
        <Selecao rotulo="Patamar" value={patamar} onChange={(e) => setPatamar(e.target.value)}
          opcoes={[['', 'Todos'], ...[1, 2, 3, 4].map((p): [string, string] => [String(p), `Patamar ${p}`])]} />
        <Selecao rotulo="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}
          opcoes={[['', 'Todos'], ...TIPOS_ADVERSARIO.map((t): [string, string] => [t, NOME_TIPO_ADVERSARIO[t]])]} />
      </div>
      {srd.isPending && <Carregando />}
      <Aviso erro={srd.error} />
      <p className="text-xs text-texto-suave">{filtrados.length} adversários</p>
      <ul className="max-h-[60vh] space-y-1.5 overflow-y-auto pr-1">
        {filtrados.map((a) => (
          <li key={a.id}>
            <Escolhivel selecionado={a.id === selecionado} onClick={() => aoEscolher(a.id)}>
              <Linha nome={a.nome} patamar={a.patamar} tipo={a.tipo} />
            </Escolhivel>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function AbaInimigos({ mesaId, podeEditar }: { mesaId: string; podeEditar: boolean }) {
  const inimigos = useInimigos(mesaId)
  const [lista, setLista] = useState<'mesa' | 'srd'>('mesa')
  const [painel, setPainel] = useState<Painel>({ modo: 'vazio' })

  const doMesa = useInimigo(mesaId, painel.modo === 'mesa' ? painel.id : null)
  const srd = useAdversariosSrd(lista === 'srd')
  const doSrd = painel.modo === 'srd' ? srd.data?.find((a) => a.id === painel.id) : undefined

  const copiar = useCopiarDoSrd(mesaId)
  const salvar = useSalvarInimigo(mesaId)
  const apagar = useApagarInimigo(mesaId)

  function copiarParaMesa(id: string) {
    copiar.mutate(id, { onSuccess: (novo) => { setLista('mesa'); setPainel({ modo: 'mesa', id: novo!.id }) } })
  }

  // o inimigo em edição veio com a `versao` de quando abriu: se outro mestre salvar antes, avisa
  function salvarEdicao(inimigo: ComVersao<Adversario>) {
    salvar.mutate(inimigo, { onSuccess: (salvo) => setPainel({ modo: 'mesa', id: salvo!.id }) })
  }

  function editar(inimigo: Adversario) {
    salvar.reset()
    setPainel({ modo: 'editar', inimigo: structuredClone(inimigo) })
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,20rem)_1fr]">
      <aside className="space-y-3">
        <div className="flex gap-2">
          <Botao variante={lista === 'mesa' ? 'primario' : 'secundario'} className="flex-1" onClick={() => setLista('mesa')}>
            Da mesa
          </Botao>
          <Botao variante={lista === 'srd' ? 'primario' : 'secundario'} className="flex-1" onClick={() => setLista('srd')}>
            Catálogo do SRD
          </Botao>
        </div>

        {lista === 'mesa' ? (
          <div className="space-y-2">
            {podeEditar && (
              <Botao variante="secundario" className="w-full" onClick={() => editar(INIMIGO_EM_BRANCO)}>
                Criar inimigo do zero
              </Botao>
            )}
            {inimigos.isPending && <Carregando />}
            <Aviso erro={inimigos.error} />
            {inimigos.data?.length === 0 && (
              <p className="text-sm text-texto-suave">
                Nenhum inimigo ainda. Copie um do catálogo do SRD ou crie do zero.
              </p>
            )}
            <ul className="space-y-1.5">
              {inimigos.data?.map((i) => (
                <li key={i.id}>
                  <Escolhivel selecionado={painel.modo === 'mesa' && painel.id === i.id}
                    onClick={() => setPainel({ modo: 'mesa', id: i.id })}>
                    <Linha nome={i.nome} patamar={i.patamar} tipo={i.tipo}
                      extra={!i.base_id && <Selo>próprio</Selo>} />
                  </Escolhivel>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <CatalogoSrd selecionado={painel.modo === 'srd' ? painel.id : undefined}
            aoEscolher={(id) => setPainel({ modo: 'srd', id })} />
        )}
      </aside>

      <section aria-live="polite">
        {painel.modo === 'vazio' && (
          <div className="rounded-2xl border border-dashed border-borda p-10 text-center text-texto-suave">
            Escolha um inimigo para ver a ficha. Tudo aqui é visível só para os mestres.
          </div>
        )}

        {painel.modo === 'srd' && doSrd && (
          <FichaInimigo adversario={doSrd} acoes={podeEditar && (
            <Botao disabled={copiar.isPending} onClick={() => copiarParaMesa(doSrd.id)}>Adicionar à mesa</Botao>
          )} />
        )}
        {painel.modo === 'srd' && <Aviso erro={copiar.error} />}

        {painel.modo === 'mesa' && (
          <>
            {doMesa.isPending && <Carregando />}
            <Aviso erro={doMesa.error ?? apagar.error} />
            {doMesa.data && (
              <FichaInimigo adversario={doMesa.data} acoes={podeEditar && <>
                <Botao variante="secundario" onClick={() => editar(doMesa.data)}>Editar</Botao>
                <Botao variante="perigo" disabled={apagar.isPending}
                  onClick={() => confirm(`Apagar ${doMesa.data.nome} da mesa?`)
                    && apagar.mutate(doMesa.data.id, { onSuccess: () => setPainel({ modo: 'vazio' }) })}>
                  Apagar
                </Botao>
              </>} />
            )}
          </>
        )}

        {painel.modo === 'editar' && (
          <form className="space-y-4 rounded-2xl border border-borda bg-superficie p-4 sm:p-5"
            onSubmit={(e) => { e.preventDefault(); salvarEdicao(painel.inimigo) }}>
            <h2 className="text-lg text-esperanca">{painel.inimigo.id ? `Editar ${painel.inimigo.nome}` : 'Novo inimigo'}</h2>
            <EditorInimigo key={painel.inimigo.id || 'novo'} valor={painel.inimigo}
              aoMudar={(inimigo) => setPainel({ modo: 'editar', inimigo })} />
            <AvisoDeConflito erro={salvar.error} ocupado={salvar.isPending}
              aoVerAtual={() => {
                salvar.reset()
                setPainel({ modo: 'mesa', id: painel.inimigo.id })
                void doMesa.refetch()
              }}
              aoSalvarMesmoAssim={() => salvarEdicao({ ...painel.inimigo, versao: null })} />
            <Aviso erro={semConflito(salvar.error)} />
            <div className="flex gap-2">
              <Botao type="submit" disabled={salvar.isPending}>{salvar.isPending ? 'Salvando…' : 'Salvar'}</Botao>
              <Botao type="button" variante="fantasma"
                onClick={() => setPainel(painel.inimigo.id ? { modo: 'mesa', id: painel.inimigo.id } : { modo: 'vazio' })}>
                Cancelar
              </Botao>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
