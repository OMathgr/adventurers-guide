# Adventurer's Guide

Software para ajudar grupos a jogar RPG. Começa com as regras de **Daggerheart**.

Esta é a fase 1: o **motor de regras** em Python puro. Ele cria personagens,
valida cada subida de nível e gera os dados da ficha e da linha do tempo.
Ainda não tem banco, API nem interface.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pytest
python -m pytest                 # roda os testes
python exemplo.py                # cria uma personagem e mostra a ficha
```

## Estrutura

```
motor/
  srd.py          # lê o conteúdo do SRD (JSON) e transforma em objetos
  personagem.py   # criação, level up, validações e linha do tempo
data/
  srd/            # classes, subclasses, cartas... (SRD 1.0, JSON da comunidade)
  progressao.json # tiers, conquistas e opções de avanço (feito por nós)
tests/            # um teste para cada regra
docs/ARQUITETURA.md
```

## Roadmap

1. **Motor de regras** (agora)
2. API (FastAPI) + PostgreSQL: usuários, mesas, papéis, personagens salvos
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
