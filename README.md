# Adventurer's Guide

Software para ajudar grupos a jogar RPG. Começa com as regras de **Daggerheart**.

Hoje tem duas camadas:

- **Motor de regras** (`motor/`, Python puro): cria personagens, valida cada
  subida de nível, calcula a ficha, a linha do tempo e o estado de jogo.
- **API** (`api/`, FastAPI + SQLAlchemy): expõe o motor por HTTP e salva os
  personagens no banco (SQLite local; PostgreSQL trocando a `DATABASE_URL`).

Ainda não tem usuários, mesas nem interface.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest                 # roda os testes
python exemplo.py                # cria uma personagem e mostra a ficha (só o motor)

alembic upgrade head             # cria/atualiza o banco (adventurers.db)
uvicorn api.main:app --reload    # API em http://127.0.0.1:8000 (docs em /docs)
```

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
  erros.py        # RegraViolada
api/
  main.py         # aplicação FastAPI e tratamento de erros
  rotas/          # srd (catálogo), personagens (construtor), sessao (jogo)
  repositorio.py  # Personagem <-> banco (carregar refaz o personagem pelo motor)
  tabelas.py      # tabelas SQLAlchemy
  esquemas.py     # ficha de saída e corpos das ações
  db.py           # conexão (DATABASE_URL)
migrations/       # migrações do banco (Alembic)
data/
  srd/              # classes, subclasses, cartas... (SRD 1.0, JSON da comunidade)
  progressao.json   # tiers, conquistas e opções de avanço (feito por nós)
  companheiro.json  # ficha do Ranger Companion (feito por nós)
tests/            # um teste para cada regra (tests/api: testes da API)
docs/ARQUITETURA.md
```

## Roadmap

1. ~~Motor de regras~~
2. API (FastAPI) + banco: ~~personagens salvos~~ (agora), usuários, mesas, papéis
3. Interface web do construtor: visão ficha + visão linha do tempo
4. Workspace da mesa (mapa mental com visibilidade por papel)
5. Colaboração em tempo real
6. App mobile

## Licença do conteúdo

This product includes materials from the Daggerheart System Reference Document 1.0,
© Critical Role, LLC. under the terms of the Darrington Press Community Gaming (DPCGL)
License. More information can be found at https://www.daggerheart.com. There are no
previous modifications by others.

Dados em JSON: [daggersearch/daggerheart-data](https://github.com/daggersearch/daggerheart-data).
