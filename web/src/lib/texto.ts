// Leitura do markdown mínimo usado nos textos do SRD: **negrito**, _itálico_,
// parágrafos separados por linha em branco e itens de lista começando com "- ".

export type Trecho = { texto: string; negrito?: boolean; italico?: boolean }
export type Bloco = { tipo: 'paragrafo'; trechos: Trecho[] } | { tipo: 'lista'; itens: Trecho[][] }

/** Quebra uma linha em trechos com negrito/itálico. Marcas sem par ficam como texto. */
export function trechos(linha: string): Trecho[] {
  const saida: Trecho[] = []
  const padrao = /\*\*(.+?)\*\*|(?<![\p{L}\d])_(.+?)_(?![\p{L}\d])/gu
  let inicio = 0
  for (const m of linha.matchAll(padrao)) {
    if (m.index > inicio) saida.push({ texto: linha.slice(inicio, m.index) })
    if (m[1] !== undefined) {
      // itálico dentro de negrito ("**_Oculto_**") vira os dois
      for (const t of trechos(m[1])) saida.push({ ...t, negrito: true })
    } else {
      saida.push({ texto: m[2], italico: true })
    }
    inicio = m.index + m[0].length
  }
  if (inicio < linha.length) saida.push({ texto: linha.slice(inicio) })
  return saida
}

export function blocos(texto: string): Bloco[] {
  const saida: Bloco[] = []
  for (const paragrafo of texto.split(/\n\s*\n/)) {
    const linhas = paragrafo.split('\n').map((l) => l.trim()).filter(Boolean)
    if (linhas.length === 0) continue
    const itens = linhas.filter((l) => /^[-•]\s/.test(l))
    if (itens.length === linhas.length) {
      saida.push({ tipo: 'lista', itens: itens.map((l) => trechos(l.replace(/^[-•]\s+/, ''))) })
    } else {
      saida.push({ tipo: 'paragrafo', trechos: trechos(linhas.join(' ')) })
    }
  }
  return saida
}
