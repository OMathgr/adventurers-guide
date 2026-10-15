# Adventurer's Guide — contexto para o Claude Code

Software para ajudar grupos a jogar RPG, começando por Daggerheart.
Módulos planejados: mesas com papéis (jogador/mestre, vários mestres possíveis),
workspace colaborativo estilo mapa mental (mestre vê informações confidenciais)
e construtor de personagem com visão de ficha e visão de linha do tempo.

## Estado atual
Fase 1 (motor de regras em Python puro, `motor/`) e fase 2 (API FastAPI em
`api/`) concluídas. A API usa SQLite local (PostgreSQL depois, só trocando
`DATABASE_URL`) e tem personagens salvos, cadastro e login (JWT) e mesas
(convite por código, jogador/mestre, permissões dos mestres definidas pelo
criador; o mestre só lê fichas e aplica dano e condições) e biblioteca
privada dos mestres por mesa (inimigos do SRD ou do zero, NPCs). Fase 3 em
andamento: interface React em `web/` (construtor com equipamento, mesas com
nível máximo, personagem preso à mesa com cópia + plano de níveis, fotos,
área do mestre e sessões de jogo (de um mestre responsável, com Medo próprio,
planejamento e encontros com Guia de Batalha), revelar aos jogadores
(vitalidade e condições dos inimigos, NPCs conhecidos) e quadros de mapa
mental (um por sessão; o revelado vai para o quadro da campanha) e ao vivo
(avisos por SSE sem dados, presença online) prontos). App mobile como PWA
(instalável, todas as telas em 360 px) pronto. Inventário (ouro, saque e
consumíveis do SRD, relíquias, armas guardadas, itens iniciais) e lojas da
sessão (o mestre vende, cobrando o ouro), com a regra opcional das moedas
por mesa, prontos. Conta: esqueci minha senha (link por e-mail via SMTP) e login
com o Google (contas com o mesmo e-mail se juntam) e sessão por uso (renova
enquanto se usa; cai depois de 2 h parado) prontos. Jogadores veem a ficha
simplificada (quem é, PV, PF e Esperança) dos outros personagens da mesa.
Edição simultânea protegida: ações se refazem sozinhas; formulários avisam do
conflito (api/concorrencia.py). Repouso do grupo (o mestre abre, cada jogador
escolhe os movimentos, inclusive em aliados) e movimentos de morte com
cicatrizes prontos. Habilidades de classe e de subclasse na ficha (as de número
fixo já aplicadas; cartas a mais do Discípulo do Conhecimento) prontas. Produção: `api/servidor.py` (API em /api + interface em /),
Dockerfile e `deploy/` (Oracle + DuckDNS + Caddy, backup diário; guia em
deploy/README.md). Leia `docs/ARQUITETURA.md` antes de mudar a modelagem. O
personagem é guardado como criação + histórico de subidas de nível; a ficha
é sempre recalculada.

## Convenções
- Python 3.10+, nomes do domínio em português (`Personagem`, `SubidaDeNivel`).
- `motor/` não depende de FastAPI nem de banco; a API só chama o motor.
- Toda regra nova vem com teste em `tests/` (API em `tests/api/`). Rode
  `.venv\Scripts\python -m pytest` antes de concluir (as dependências da API
  estão no `.venv`).
- Mudou `api/tabelas.py`? Gere a migração: `alembic revision --autogenerate -m "..."`.
- Front (`web/`): textos em português, regras só no motor (a tela guia e
  mostra o erro da API). Mudou a API? `npm run api:tipos` regenera
  `web/src/api/esquema.d.ts`. Antes de concluir: `npm test` e `npm run build`
  dentro de `web/`. Cores: azul-escuro (Medo) e laranja (Esperança), via
  variáveis em `web/src/index.css`.
- Conteúdo de jogo só do SRD (licença DPCGL). Nada do livro completo.
- Tradução pt-BR em `data/traducoes/pt-BR/` (não oficial, só exibição; as
  regras leem o inglês). Siga o glossário do `docs/ARQUITETURA.md` (Fadiga/PF,
  teste, patamar, alcance próximo/distante). Da edição brasileira usamos só
  termos e nomes, nunca o texto.
- Arredondamento: toda metade arredonda **para cima**, em todo o projeto
  (resistência, metade do nível etc.). Use `motor.numeros.metade`, nunca `// 2`.
- Dados ficam em `data/`; o motor só acessa dados pela `Biblioteca` (`motor/srd.py`).

## Como trabalhar comigo
Este não é um projeto de estudo: implemente as funcionalidades diretamente
(com testes). Ao terminar, descreva:
1. o porquê das escolhas de design (alternativas descartadas, quando relevante);
2. como foi feito (o que mudou e onde).
Decisões de produto ou de regra ambíguas: pergunte antes.
