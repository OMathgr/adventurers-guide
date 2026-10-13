// Service worker do app instalável (PWA). Guarda só a "casca" do app (HTML, JS,
// CSS, ícones e fontes) para abrir rápido e abrir mesmo sem rede. A API (/api)
// nunca passa por aqui: dados de jogo sempre vêm do servidor, com as permissões
// de quem pede, e o fluxo ao vivo (/api/eventos) não pode ficar preso em cache.
const VERSAO = 'ag-v1'
const CASCA = '/index.html'

/** Como tratar cada pedido: null = deixa com o navegador (não intercepta). */
function estrategia(url, modo, origem) {
  const u = new URL(url)
  const fonte = u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com'
  if (u.origin !== origem) return fonte ? 'cache-e-atualiza' : null
  if (u.pathname === '/api' || u.pathname.startsWith('/api/')) return null
  if (modo === 'navigate') return 'navegacao'
  // arquivos do build têm hash no nome: o mesmo nome é sempre o mesmo conteúdo
  if (u.pathname.startsWith('/assets/')) return 'cache-primeiro'
  return 'cache-e-atualiza'
}
self.estrategia = estrategia   // para os testes

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(VERSAO).then((c) => c.add(CASCA)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  )
})

async function guardar(pedido, resposta) {
  // opaca (fonte de outra origem) tem status 0 mas serve; erro não se guarda
  if (resposta.ok || resposta.type === 'opaque') {
    const cache = await caches.open(VERSAO)
    await cache.put(pedido, resposta.clone())
  }
  return resposta
}

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request
  if (pedido.method !== 'GET') return
  const tipo = estrategia(pedido.url, pedido.mode, self.location.origin)
  if (!tipo) return

  if (tipo === 'navegacao') {
    // rede primeiro (versão nova do app); sem rede, a casca guardada
    evento.respondWith(
      fetch(pedido)
        .then((r) => (r.ok ? guardar(CASCA, r) : r))
        .catch(() => caches.match(CASCA).then((r) => r ?? Response.error())),
    )
  } else if (tipo === 'cache-primeiro') {
    evento.respondWith(caches.match(pedido).then((r) => r ?? fetch(pedido).then((nova) => guardar(pedido, nova))))
  } else {
    // devolve o guardado na hora e atualiza por trás
    evento.respondWith(
      caches.match(pedido).then((guardada) => {
        const rede = fetch(pedido).then((nova) => guardar(pedido, nova)).catch(() => guardada ?? Response.error())
        if (guardada) evento.waitUntil(rede.then(() => undefined))
        return guardada ?? rede
      }),
    )
  }
})
