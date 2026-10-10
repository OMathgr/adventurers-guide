# Adventurer's Guide — contexto para o Claude Code

Software para ajudar grupos a jogar RPG, começando por Daggerheart.
Módulos planejados: mesas com papéis (jogador/mestre, vários mestres possíveis),
workspace colaborativo estilo mapa mental (mestre vê informações confidenciais)
e construtor de personagem com visão de ficha e visão de linha do tempo.

## Estado atual
Fase 1 (motor de regras em Python puro, `motor/`) concluída. Fase 2 em
andamento: API FastAPI em `api/`, com SQLite local (PostgreSQL depois, só
trocando `DATABASE_URL`). Já salva personagens; usuários, login e mesas vêm
a seguir. Leia `docs/ARQUITETURA.md` antes de mudar a modelagem. O personagem
é guardado como criação + histórico de subidas de nível; a ficha é sempre
recalculada.

## Convenções
- Python 3.10+, nomes do domínio em português (`Personagem`, `SubidaDeNivel`).
- `motor/` não depende de FastAPI nem de banco; a API só chama o motor.
- Toda regra nova vem com teste em `tests/` (API em `tests/api/`). Rode
  `.venv\Scripts\python -m pytest` antes de concluir (as dependências da API
  estão no `.venv`).
- Mudou `api/tabelas.py`? Gere a migração: `alembic revision --autogenerate -m "..."`.
- Conteúdo de jogo só do SRD (licença DPCGL). Nada do livro completo.
- Dados ficam em `data/`; o motor só acessa dados pela `Biblioteca` (`motor/srd.py`).

## Como trabalhar comigo
Este não é um projeto de estudo: implemente as funcionalidades diretamente
(com testes). Ao terminar, descreva:
1. o porquê das escolhas de design (alternativas descartadas, quando relevante);
2. como foi feito (o que mudou e onde).
Decisões de produto ou de regra ambíguas: pergunte antes.
