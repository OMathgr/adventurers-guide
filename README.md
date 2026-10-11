# Adventurer's Guide

Software para ajudar grupos a jogar RPG. Começa com as regras de **Daggerheart**.

Hoje tem três camadas:

- **Motor de regras** (`motor/`, Python puro): cria personagens, valida cada
  subida de nível, calcula a ficha, a linha do tempo e o estado de jogo.
- **API** (`api/`, FastAPI + SQLAlchemy): expõe o motor por HTTP e salva os
  personagens no banco (SQLite local; PostgreSQL trocando a `DATABASE_URL`).
- **Interface web** (`web/`, React + TypeScript + Vite): construtor de
  personagem com visão de ficha e visão de linha do tempo.

Tem cadastro e login (e-mail e senha, token JWT) e mesas: entrada por
código de convite, jogadores e mestres, e o mestre vê as fichas e aplica
dano e condições nos personagens da mesa. Cada mesa tem uma biblioteca
privada dos mestres: inimigos (copiados dos 129 adversários do SRD ou criados
do zero) e NPCs (ficha simples, com ficha de combate opcional). A interface
web cobre o construtor (criar, ficha, linha do tempo, subir de nível), as
mesas, a área do mestre e a sessão de jogo (Medo, encontros com várias cópias
de inimigos, PV/PF/condições por clique, dano e condições nos personagens).

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest                 # roda os testes
python exemplo.py                # cria uma personagem e mostra a ficha (só o motor)

alembic upgrade head             # cria/atualiza o banco (adventurers.db)
uvicorn api.main:app --reload    # API em http://127.0.0.1:8000 (docs em /docs)

cd web                           # interface (precisa do Node.js 20+)
npm install
npm run dev                      # http://localhost:5173 (usa a API acima)
npm test
```

Na página `/docs`, cadastre-se em `POST /auth/cadastro` e use o botão
**Authorize** (e-mail no campo `username`) para testar as rotas protegidas.

Em produção, defina `JWT_SECRET` (chave longa e aleatória). Sem ela, a API
gera uma chave temporária e os logins caem a cada reinício.

Para usar PostgreSQL: instale um driver (ex.: `pip install "psycopg[binary]"`),
defina `DATABASE_URL=postgresql+psycopg://usuario:senha@servidor/adventurers`
e rode `alembic upgrade head`.

## Estrutura

```
motor/
  srd.py          # lê o conteúdo do SRD (JSON) e transforma em objetos
  personagem.py   # criação, level up, equipamento, cartas, ficha e linha do tempo
  sessao.py       # estado de jogo: PV, Estresse, Esperança, armadura, dano e descansos
  companheiro.py  # companheiro do Ranger Beastbound: ficha e treinos
  adversarios.py  # adversários (SRD e criados pelo mestre): formato e validação
  encontro.py     # sessão do mestre: encontros (cópias em combate, dano) e Medo
  erros.py        # RegraViolada
api/
  main.py         # aplicação FastAPI e tratamento de erros
  rotas/          # auth, srd (catálogo), personagens (construtor), sessao (jogo), mesas,
                  # conteudo (inimigos e NPCs da mesa), encontros (sessão do mestre)
  mesas.py        # papéis e permissões das mesas
  seguranca.py    # hash de senha (Argon2) e tokens JWT
  autenticacao.py # dependência usuario_atual (quem está logado)
  repositorio.py  # Personagem <-> banco (carregar refaz o personagem pelo motor)
  tabelas.py      # tabelas SQLAlchemy
  esquemas.py     # ficha de saída e corpos das ações
  db.py           # conexão (DATABASE_URL)
migrations/       # migrações do banco (Alembic)
web/              # interface React (ver web/README.md)
data/
  srd/              # classes, subclasses, cartas... (SRD 1.0, JSON da comunidade)
  progressao.json   # tiers, conquistas e opções de avanço (feito por nós)
  companheiro.json  # ficha do Ranger Companion (feito por nós)
tests/            # um teste para cada regra (tests/api: testes da API)
docs/ARQUITETURA.md
```

## Roadmap

1. ~~Motor de regras~~
2. ~~API (FastAPI) + banco: personagens salvos, usuários e login, mesas e papéis~~
3. Interface web: ~~construtor (ficha + linha do tempo)~~, ~~mesas e área do mestre (inimigos e NPCs)~~,
   ~~sessão de jogo (encontros, Medo, PV/PF dos inimigos)~~ e revelar informações aos jogadores (próximo)
4. Workspace da mesa (mapa mental com visibilidade por papel)
5. Colaboração em tempo real
6. App mobile

## Licença do conteúdo

This product includes materials from the Daggerheart System Reference Document 1.0,
© Critical Role, LLC. under the terms of the Darrington Press Community Gaming (DPCGL)
License. More information can be found at https://www.daggerheart.com. There are no
previous modifications by others.

Modifications: the SRD content was translated into Brazilian Portuguese by the
Adventurer's Guide project (`data/traducoes/pt-BR/`). This is an unofficial
translation, not affiliated with or endorsed by Darrington Press or Critical Role.

Tradução não oficial para o português feita pelo projeto Adventurer's Guide.

Dados em JSON: [daggersearch/daggerheart-data](https://github.com/daggersearch/daggerheart-data)
(personagens, cartas, equipamento) e [seansbox/daggerheart-srd](https://github.com/seansbox/daggerheart-srd)
(adversários, `data/srd/adversarios.json`).
