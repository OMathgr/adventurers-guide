# Interface web (fase 3)

React 19 + TypeScript + Vite, Tailwind CSS, React Router e React Query.

```bash
npm install
npm run dev        # http://localhost:5173 (precisa da API rodando em :8000)
npm test           # testes (Vitest + Testing Library)
npm run build      # checagem de tipos + build de produção em dist/
npm run api:tipos  # regenera src/api/esquema.d.ts depois de mudar a API
```

Em desenvolvimento, o Vite encaminha `/api/...` para `http://127.0.0.1:8000`
(o FastAPI), então não há CORS a configurar.

## Organização

```
src/
  api/          cliente HTTP, hooks de dados (React Query) e tipos gerados da API
  auth/         login: token, usuário atual, entrar/cadastrar/sair
  componentes/  Layout, ficha, linha do tempo e peças visuais (ui.tsx)
  paginas/      telas: acesso, personagens, novo personagem, personagem, subir de nível
  lib/          rótulos em português, nomes a partir do catálogo e ajudas dos assistentes
  testes/       preparação e testes de telas
```

Os tipos em `src/api/esquema.d.ts` são **gerados** a partir do OpenAPI da API;
não edite à mão. As regras do jogo ficam no motor (Python); a interface só
guia o jogador e mostra a mensagem que a API devolve quando algo não vale.
