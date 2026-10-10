# Adventurer's Guide — contexto para o Claude Code

Software para ajudar grupos a jogar RPG, começando por Daggerheart.
Módulos planejados: mesas com papéis (jogador/mestre, vários mestres possíveis),
workspace colaborativo estilo mapa mental (mestre vê informações confidenciais)
e construtor de personagem com visão de ficha e visão de linha do tempo.

## Estado atual
Fase 1: motor de regras em Python puro (`motor/`). Leia `docs/ARQUITETURA.md`
antes de mudar a modelagem. O personagem é guardado como criação + histórico
de subidas de nível; a ficha é sempre recalculada.

## Convenções
- Python 3.10+, nomes do domínio em português (`Personagem`, `SubidaDeNivel`).
- Toda regra nova vem com teste em `tests/`. Rode `python -m pytest` antes de concluir.
- Conteúdo de jogo só do SRD (licença DPCGL). Nada do livro completo.
- Dados ficam em `data/`; o motor só acessa dados pela `Biblioteca` (`motor/srd.py`).

## Como trabalhar comigo
Este não é um projeto de estudo: implemente as funcionalidades diretamente
(com testes). Ao terminar, descreva:
1. o porquê das escolhas de design (alternativas descartadas, quando relevante);
2. como foi feito (o que mudou e onde).
Decisões de produto ou de regra ambíguas: pergunte antes.
