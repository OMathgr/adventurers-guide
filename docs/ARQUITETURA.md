# Arquitetura do motor de regras

## Histórico em vez de ficha pronta

O personagem é salvo como **criação + lista de subidas de nível**. A ficha
nunca é salva: ela é recalculada aplicando cada nível em ordem.

```
Criacao ──► Ficha nv1 ──(SubidaDeNivel 2)──► Ficha nv2 ──(SubidaDeNivel 3)──► ...
```

Por que isso importa para o produto:

| Necessidade | Como o modelo resolve |
|---|---|
| Visão **linha do tempo** | `linha_do_tempo()` lista o histórico + o que vem nos próximos níveis |
| Visão **ficha** | `ficha()` aplica todo o histórico |
| Ver como estava no nível 3 | `ficha(ate_nivel=3)` |
| Desfazer uma escolha errada | `desfazer_ultimo_nivel()` |
| Impedir build inválida | cada nível é validado contra a ficha anterior |

No banco de dados (fase 2), isso vira duas tabelas: `personagens` (com a
criação) e `subidas_de_nivel` (uma linha por nível, com as escolhas em JSON).
Ver "API e banco" no fim deste documento.

## Regras de level up implementadas

Ordem de cada nível:

1. **Conquista de tier** (níveis 2, 5, 8): nova Experiência +2, +1 Proficiência;
   nos níveis 5 e 8 limpa as marcas dos atributos.
2. **Dois avanços** do tier atual ou anterior. Proficiência e Multiclasse valem por dois.
3. **Limiares de dano** +1 (o bônus é igual ao nível).
4. **Uma carta de domínio** de nível ≤ ao seu. Opcionalmente troca uma carta antiga
   por outra de nível igual ou menor.

Restrições checadas:

- quantidade de usos de cada opção por tier (`data/progressao.json`);
- atributo marcado não sobe até a próxima conquista de tier;
- pegar Subclasse risca a Multiclasse do mesmo tier;
- Multiclasse risca a Subclasse do tier e todas as outras Multiclasses;
- cartas do domínio da multiclasse têm nível ≤ metade do seu nível,
  arredondada para cima (nível 5 → até nível 3);
- PV e Estresse no máximo 12.

## Equipamento (estado atual, fora do histórico)

Arma e armadura mudam durante o jogo, não ao subir de nível. Por isso o
`Personagem` guarda um `Equipamento` (principal, secundária, armadura) à parte
do histórico. `ficha()` refaz o histórico e, no fim, aplica o equipamento
atual (`_vestir`). Consequência: `ficha(ate_nivel=3)` mostra o nível 3 com o
equipamento de hoje.

- `equipar(...)` define o conjunto completo e valida tudo antes de trocar.
- Sem armadura: limiar maior = nível, grave = 2 × nível, pontuação 0.
- Com armadura: limiares base da armadura + nível.
- Dano: número de dados = Proficiência (`2d8+1`).
- Arma de duas mãos impede secundária; arma mágica exige subclasse com
  atributo de conjuração (inclusive a da multiclasse).

No banco, o equipamento vira colunas (ou tabela) do `personagem`, não de
`subida_de_nivel`.

## Inventário (`motor/inventario.py`, estado atual)

Decisões do projeto (2026-10-13): consumíveis de efeito simples já aplicam na
ficha; o mestre com a permissão `dar_itens` dá e tira ouro e itens; entram as
armas de inventário; os itens iniciais são um passo da criação; cada sessão
tem lojas (várias, com nome) que o mestre monta e vende.

- **Catálogo**: `data/srd/loot.json` e `consumables.json` (60 + 60, extraídos
  do texto do SRD, com o número da tabela d60), `data/itens_iniciais.json`
  (tocha, corda, suprimentos, poções do passo 5, 1 punhado) e os itens de
  classe do `classes.json` (`<classe>_item_<n>`). Tudo em `Biblioteca.itens`
  (`TipoDeItem`: SAQUE, CONSUMIVEL, COMUM, CLASSE).
- **Ouro** guardado em punhados (`em_punhados`/`decompor`): 10 punhados = 1
  bolsa, 10 bolsas = 1 baú, no máximo 1 baú (199 punhados). Gastar troca uma
  bolsa por punhados quando precisa (o SRD não diz; é o natural).
- **Moedas** (regra opcional do SRD, 10 moedas = 1 punhado): ligada por mesa
  (`mesas.usar_moedas`, quem tem a permissão `nivel` decide) ou, sem mesa,
  pelo próprio personagem (`Inventario.usar_moedas`). Ficam em
  `Inventario.moedas` (0 a 9); as contas de ouro são feitas em moedas. Sem a
  regra, mandar moedas dá erro; desligar não apaga as moedas, só as esconde.
  Preço de loja pode ter moedas (0 a 9) quando a mesa usa a regra.
- **Consumível**: no máximo 5 de cada; usar gasta 1. `EfeitoConsumivel` é lido
  do texto em inglês (como as características): "Clear 1d4+1 HP", "gain 2
  Hope", "Mark a Stress and clear a HP" (o PF é custo: precisa de espaço),
  "clear 1d4 HP or 1d4 Stress" (escolha), "clear all...". São 11; os outros
  só mostram o texto. A rolagem é a soma dos dados que a pessoa rolou (sem o
  bônus); sem ela, o motor rola.
- **Relíquia**: só uma; +1 no atributo (aplicado em `_vestir`, então vale nos
  ataques e requisitos), ou +1 numa Experiência escolhida (Honing Relic).
  Gemas, pedras e o resto do saque ficam como texto.
- **Armas de inventário**: até 2. `trocar_arma` só troca por arma ativa da
  mesma empunhadura; grátis na calma, 1 PF (custo) em perigo; mão vazia só
  equipa. Armadura não vai para o inventário (SRD).
- **Itens livres** (`ItemLivre`): nome e descrição criados na mesa.
- **Criação**: `Criacao.pocao_inicial` e `item_de_classe` montam o
  inventário inicial; sem eles (personagens antigos) começa vazio.
- **Loja** (`motor/loja.py`): `ItemDaLoja` (ITEM, ARMA, ARMADURA ou LIVRE;
  preço em punhados; estoque opcional). `vender` cobra, entrega (arma vai para
  as armas guardadas; armadura é vestida na hora, sem marcas, e a antiga fica
  para trás) e baixa o estoque. Se algo for recusado, a API não salva nada.
- `Inventario.de_estado` faz cópia profunda: o estado vem do JSON do banco, e
  mexer nele por baixo fazia o SQLAlchemy achar que nada mudou.
- API: `/personagens/{id}/inventario/...` (dono; usar e trocar arma são só
  dele), `/mesas/{m}/personagens/{p}/inventario/...` (mestre: ver com
  `ver_fichas`, dar e tirar com `dar_itens`), `/mesas/{m}/sessoes/{s}/lojas`
  (só o responsável monta; vender exige também `dar_itens`). Lojas à mostra
  de sessões em andamento vão para `/revelado` (com preço e estoque). Coluna
  `personagens.inventario` e tabela `lojas`.

### Características de armas e armaduras

O SRD só traz texto. A `Biblioteca` extrai os **bônus fixos** dele
(`_modificadores` em `srd.py`): cada trecho separado por `;` no formato
`+N to <alvo>`, com `<alvo>` na tabela `ALVOS_SRD` (Evasão, Pontuação de
Armadura, limiar grave, ataque, atributos). Os valores vêm do próprio SRD, então
"Barrier" +2 a +5 funciona sem tabela feita à mão.

- Bônus fixos de todas as peças alteram a ficha (uma arma Heavy também tira
  Evasão). "+N to attack rolls" vale só para a própria arma.
- O resto (condicionais, ativadas) aparece como texto em
  `Ataque.caracteristicas` e `Ficha.caracteristicas_armadura`.
- Level up e validações partem de `_ficha_base()` (sem equipamento) para os
  modificadores não acumularem a cada nível.
- `test_todo_bonus_fixo_do_srd_e_reconhecido` falha se aparecer um
  `+N to <alvo>` desconhecido (ex.: no SRD 2.0), em vez de ignorá-lo.
- Bônus "igual ao seu X" (Bonded = nível, Sharpwing = Agilidade) viram um
  `Modificador` com `igual_a`; o valor é lido da ficha na hora, já com
  penalidades de equipamento. Valem só para o dano da própria arma.
- Requisitos de uso (Pompous: Presença ≤ 0) bloqueiam `equipar()` e também
  `subir_de_nivel()` se o nível quebrar o requisito de uma peça equipada.
  O atributo é checado com todo o equipamento aplicado.
- Versatile fica só como texto: escolher o perfil alternativo é decisão de mesa.

## Cartas de domínio

### O que dá para escolher

Uma única regra de acesso (`_carta_permitida`) serve à validação e às
listagens, então a interface nunca oferece uma carta que o motor recusaria
(há um teste que confere isso carta por carta).

| Método | Para quê | Nível máximo da carta |
|---|---|---|
| `cartas_para_nivel(escolhas)` | carta obrigatória do passo 4 | nível do personagem |
| `cartas_para_avanco(tier)` | avanço CARTA_DOMINIO | nível, limitado a 4/7/10 pelo tier do quadradinho |
| `cartas_para_troca(antiga, ...)` | troca opcional do passo 4 | nível da carta antiga |

Domínio da multiclasse: no máximo metade do nível, arredondada para cima. As listagens recebem os
avanços já marcados no nível (`escolhas`), para que uma multiclasse recém-
escolhida libere o domínio novo e a carta do avanço saia da lista do passo 4.
Marcando CARTA_DOMINIO, o nível rende duas cartas (avanço + passo 4).

### Mão e reserva (estado atual, fora do histórico)

Termos do livro: **mão** (loadout, até 5 cartas ativas) e **reserva** (vault).
No código continuam `cofre`, `cartas_ativas` e `cartas_cofre`. Como o
equipamento, mudar o que está ativo acontece em jogo. O `Personagem` guarda
só `cofre`; toda carta que ele tem e não está no cofre está na mão.

- Limite da mão em `progressao.json` (`limite_loadout`: 5).
- Carta nova entra na mão; se ela estiver cheia, vai para a reserva, a menos
  que `SubidaDeNivel.para_reserva` mande cartas antigas no lugar ("Trocando
  ao Subir de Nível": sem custo). Valida só o que depende do histórico (a
  carta é sua, continua com você, no máximo uma por carta nova), porque ao
  recarregar o histórico é refeito com uma reserva que pode diferir da real.
  Desfazer o nível devolve essas cartas para a mão.
- Troca de uma carta que estava na reserva: a nova fica na reserva.
- `guardar_carta` é grátis. `recuperar_carta` marca o custo de troca em PF
  (0 em descanso) e é recusada sem PF livre suficiente. Com a mão cheia,
  exige `no_lugar_de`.
- Desfazer um nível tira da reserva as cartas que deixaram de existir.
- Interface: `MaoEReserva` na ficha (mandar para a reserva, trazer no
  descanso ou agora) e a seção "Mão cheia" ao subir de nível.

Multiclasse: o domínio escolhido tem de ser novo ("ao qual você ainda não tem
acesso"); a tela desabilita os que você já tem. Se a nova subclasse conjura,
a ficha lista as duas conjurações (`conjuracoes`): o livro deixa escolher
qual usar **a cada teste**, então não há escolha fixa a guardar.

## Estado de sessão (`motor/sessao.py`)

PV, Estresse, Esperança e espaços de armadura marcados: estado atual, fora do
histórico, em `personagem.sessao`. Os máximos vêm sempre da ficha calculada,
então level up e troca de armadura refletem sozinhos. Quando um máximo cai
(trocar para armadura menor, desfazer nível), `Sessao.ajustar()` corta o
excesso. A ficha mostra `pv_marcados`, `estresse_marcado`,
`armadura_marcada` e `esperanca` (atual).

- **Dano:** abaixo do limiar maior = 1 PV, a partir dele = 2, a partir do
  grave = 3. Regra opcional `dano_massivo` (desligada): ≥ 2× grave = 4.
  `usar_armadura` marca um espaço e reduz um nível de gravidade.
  Marcar o último PV deixa `caido` (movimentos de morte ficam para a mesa).
- **Estresse imposto** (`marcar_estresse`) sem espaço vira PV (regra do SRD).
  **Estresse como custo** (`pagar_estresse`) exige espaço livre.
- **Esperança:** limite 6 (`limite_esperanca` em `progressao.json`).
- **Descansos:** dois movimentos (pode repetir). No curto, recuperar rola
  1d4 + tier; no longo, limpa tudo. Preparar = +1 Esperança (+2 em grupo).
  Projeto só no longo. O motor rola o d4, mas aceita o valor informado.
- **Limite:** depois de 3 descansos curtos seguidos, o próximo precisa ser
  longo (`descansos_curtos_seguidos` em `progressao.json`). O SRD fala do
  grupo; o motor controla por personagem.
- **Condições:** `aplicar_condicao` / `remover_condicao`. As padrão do SRD
  (Hidden, Restrained, Vulnerable) viram `Condicao.OCULTO/CONTIDO/VULNERAVEL`
  (aceita o nome em inglês ou português); outros nomes ficam como condição de
  característica, em texto. Duram até serem removidas. Os efeitos (vantagem,
  desvantagem, não se mover) são resolvidos na mesa.

### Características com regra própria (`Efeito`)

Não cabem em "+N to X": mudam como dano, armadura ou descanso funcionam.
São reconhecidas pelo **nome** no SRD (`_EFEITOS_SRD` em `srd.py`) e ficam em
`Caracteristica.efeito`. `test_todo_efeito_existe_no_srd` avisa se um nome
sumir. A sessão consulta `personagem.efeitos_ativos()` (todas as peças
equipadas, porque Healing é de arma).

| SRD | Regra no motor |
|---|---|
| Fortified | espaço de armadura reduz dois níveis |
| Painful (armadura) | todo espaço marcado marca 1 Estresse (imposto) |
| Resilient | antes do último espaço, d6; 6 = reduz sem marcar |
| Reinforced | com todos os espaços marcados, limiares +2 (a partir do dano seguinte) |
| Hopeful | `gastar_esperanca(n, com_armadura=k)` |
| Impenetrable | `receber_dano(..., evitar_queda=True)`: 1x por descanso, Estresse no lugar do último PV |
| Warded | dano mágico reduzido pela Pontuação de Armadura |
| Physical / Magic | armadura não reduz dano mágico / físico |
| Healing (arma) | limpa 1 PV em todo descanso |

Warded, Physical e Magic precisam do `tipo` do dano em `receber_dano`.
Todo espaço marcado passa por `_marcar_espaco`, para o Painful valer também
em `marcar_armadura` (Shifting, Timeslowing, Deflecting: efeito resolvido na
mesa) e no Hopeful.

Ainda não aplicado: Painful de arma e características que dependem de
ataque, aliados ou adversários (Sheltering, Burning, Lifestealing...) e
cuidar de aliados num descanso.

## Ancestralidade

`Ancestralidade.caracteristicas` tem as duas características na ordem do
SRD. Na **ancestralidade mista**, a 1ª vem de `Criacao.ancestralidade` e a 2ª
de `Criacao.segunda_ancestralidade` (o SRD proíbe duas primeiras ou duas
segundas; para a combinação inversa, troca-se as duas de lugar). A ficha
mostra `caracteristicas_ancestralidade`.

Características com efeito no motor (também via `Efeito`):

| SRD | Efeito |
|---|---|
| Endurance (Giant) | +1 PV na criação |
| High Stamina (Human) | +1 Estresse na criação |
| Nimble (Simiah) | +1 Evasão na criação |
| Purposeful Design (Clank) | +1 na Experiência de `experiencia_proposito` |
| Shell (Galapa) | limiares + Proficiência (em `_vestir`) |
| Efficient (Clank) | `descanso_curto(..., movimento_longo=i)` |
| Celestial Trance (Elf) | 3 movimentos de descanso em vez de 2 |

As demais são situacionais (rerrolagens, reações, voo...) e ficam como texto.

## Companheiro do Beastbound (`motor/companheiro.py`)

O companheiro evolui com o personagem, então os treinos fazem parte do
**histórico** (`SubidaDeNivel.treinos`) e a ficha dele (`Ficha.companheiro`)
é recalculada no replay. Os números da ficha "Ranger Companion" ficam em
`data/companheiro.json`: Evasão 10, 3 Estresse, dano d6 corpo a corpo, duas
Experiências +2 e os quadradinhos de cada treino.

- Ganha-se o companheiro na criação (`Criacao.companheiro`) ou ao
  multiclassear para o Beastbound (`Escolha.companheiro`).
- Um treino por nível em que já se tinha o companheiro (o ganho por
  multiclasse só treina a partir do nível seguinte), +1 ao pegar a
  especialização (Expert Training) e +2 na maestria (Advanced Training).
- Nos níveis 2, 5 e 8 o companheiro também ganha uma Experiência
  (`SubidaDeNivel.experiencia_companheiro`).
- Treinos: Intelligent, Vicious, Resilient e Aware mudam a ficha dele;
  Light in the Dark dá +1 de Esperança máxima ao personagem.
- Sessão: qualquer dano marca 1 Estresse dele (Armored: um espaço da sua
  armadura no lugar); no último Estresse ele sai de cena até o próximo
  descanso longo, quando volta com 1 Estresse limpo. Aliviar Estresse num
  descanso alivia o dele também. Creature Comfort 1x por descanso. Bonded:
  ao marcar seu último PV, rola d6 por Estresse livre dele; com um 6, você
  limpa o último PV.

Fora do motor: Battle-Bonded e Loyal Friend (dependem de posição na cena) e
a rolagem de comando (é a Rolagem de Conjuração do personagem).

## Rolagem de conjuração

`Ficha.conjuracoes` traz uma `Conjuracao` por subclasse que conjura: a
principal e, se houver, a da multiclasse (o SRD define o atributo de conjuração
na subclasse, e cada subclasse pode usar um atributo diferente). Subclasse sem
atributo (ex.: Guerreiro) não gera entrada.

Bônus = atributo de conjuração já com modificadores de equipamento (ex.: Gilded
+1 Presença) + bônus "to Spellcast Rolls" (Channeling). É calculado em
`_vestir`, porque depende dos atributos modificados.

## API e banco (fase 2, `api/`)

O motor continua puro; a API só o chama. Camadas:

```
HTTP ─► rotas (api/rotas) ─► repositorio ─► motor.Personagem
                                  │
                                  └─► tabelas (SQLAlchemy) ─► SQLite / PostgreSQL
```

- **Formato:** criação e level up entram como os próprios dataclasses do
  motor (`Criacao`, `SubidaDeNivel`), validados pelo pydantic. O mesmo
  formato vai para o banco (JSON), sem uma segunda cópia dos modelos.
  A ficha sai pelo `FichaSaida`, gerado a partir de `Ficha` sem os campos de
  controle interno.
- **Tabelas:** `personagens` (criação, equipamento, cofre e sessão em JSON) e
  `subidas_de_nivel` (uma linha por nível). A ficha nunca é salva.
- **Carregar** refaz o personagem pelo motor (criação, cada nível em ordem,
  estado atual por cima), revalidando tudo. **Salvar** grava o estado atual e
  sincroniza as linhas de nível com o histórico.
- **Cada requisição** é carregar → ação do motor → salvar. Se o motor
  recusar (`RegraViolada`), nada é salvo e a resposta é 422 com
  `"tipo": "regra"`. JSON mal formado também é 422, mas sem `tipo`.
- **Estado para persistir:** `Personagem.estado()` / `restaurar_estado()` e
  `Sessao.estado()` / `restaurar()`, no próprio motor, ao lado dos campos.
- **Banco:** URL em `DATABASE_URL` (padrão: `sqlite:///./adventurers.db`).
  Migrações com Alembic; `tests/api/test_migracoes.py` falha se
  `api/tabelas.py` mudar sem migração.

Rotas: `/auth/*` (cadastro, login, conta), `/srd/*` (catálogo, público),
`/personagens` (criar, listar, ficha, apagar, linha do tempo, opções,
cartas, níveis, equipamento, cofre) e `/personagens/{id}/sessao/*` (dano,
PV, Estresse, Esperança, armadura, descanso, companheiro, regras).
Documentação interativa em `/docs`.

### Usuários e login

- Tabela `usuarios` (e-mail único, sempre minúsculo; senha só como hash
  Argon2). `personagens.dono_id` aponta para o dono; apagar a conta apaga os
  personagens dela.
- Login (`POST /auth/login`, formulário OAuth2: e-mail em `username`) devolve
  um JWT HS256 com o id do usuário e validade (`JWT_EXPIRA_MINUTOS`, padrão 120).
  A chave vem de `JWT_SECRET`; sem ela, uma chave temporária é gerada.
- **Sessão por uso** (decisão de 2026-10-13): enquanto a pessoa usa o app, o
  login se renova; parada 2 h, cai (para não ficar logado "AFK"). "Uso" é só
  interação (clique, toque, tecla, rolagem): atualizações ao vivo não contam.
  A interface (`web/src/auth/sessao.ts`) guarda a última interação no
  localStorage (vale para todas as abas) e, se houve uso e o token tem mais de
  5 minutos, troca por um novo em `POST /auth/renovar`. Sem uso pela validade
  do token, sai e explica o motivo na tela de entrar. Nos últimos 10 minutos
  aparece um aviso com contagem regressiva (e uma barra que encolhe); qualquer
  interação, ou o botão "Continuar conectado", conta como uso e renova. Se a
  renovação falhar (ex.: sem rede), tenta de novo em 30 s ou na próxima interação. Descartado: refresh token
  separado (mais uma coisa para guardar e revogar, sem ganho aqui: o token é
  curto e a troca de senha já derruba as sessões). A conexão ao vivo lê o token
  na hora de conectar e, se o servidor recusar um antigo, reabre com o atual.
- Rotas de personagem usam a dependência `acesso` (banco + usuário logado).
  O repositório filtra tudo pelo dono: personagem de outro usuário responde
  404, igual a um inexistente, para não revelar que existe.
- Login errado responde a mesma mensagem para e-mail inexistente e senha
  errada.
- `Base.metadata` tem convenção de nomes para índices e restrições (o
  Alembic precisa deles para alterar tabelas no SQLite).
- **Migrações no SQLite**: coluna nova em tabela que outras apontam com
  `ON DELETE CASCADE` (`usuarios`, `mesas`, `personagens`...) entra com
  `op.add_column` direto, nunca com `batch_alter_table`. O "batch" recria a
  tabela e, com `PRAGMA foreign_keys=ON`, apagar a antiga apaga em cascata
  tudo o que depende dela. Padrão de coluna como texto (`server_default='0'`),
  não `sa.text(...)`, senão o Alembic recria. `tests/api/test_migracoes.py`
  migra um banco com dados para frente e para trás e confere que nada some.

### Recuperação de senha e login com o Google (`api/rotas/auth.py`)

Decisões do projeto (2026-10-13): só Google por enquanto; e-mail por SMTP
configurável; mesmo e-mail (verificado pelo Google) junta as contas; quem
entrou só pelo Google cria senha pelo "esqueci minha senha".

- **Esqueci minha senha**: `POST /auth/recuperar` responde sempre a mesma coisa
  (e o e-mail sai depois da resposta, em segundo plano), para ninguém descobrir
  quem tem conta. O token do link é aleatório; o banco guarda só o sha256
  (`recuperacoes_de_senha`), vale 1 hora e uma vez só; pedir de novo invalida o
  anterior e há no máximo um e-mail por minuto por conta. `POST /auth/redefinir`
  troca a senha e já entra.
- **Sessões antigas caem** ao trocar a senha: `usuarios.tokens_validos_desde`, e
  token com `iat` anterior recebe 401 (o `iat` tem fração de segundo, para valer
  até no mesmo segundo). Vale também para o fluxo ao vivo.
- **E-mail** (`api/correio.py`): SMTP de qualquer provedor (`SMTP_HOST`,
  `SMTP_PORTA`, `SMTP_SEGURANCA`, `SMTP_USUARIO`, `SMTP_SENHA`,
  `SMTP_REMETENTE`; links com `APP_URL`). Sem `SMTP_HOST`, o e-mail vai para o
  log (desenvolvimento).
- **Google** (`api/google.py`): OpenID Connect com código + PKCE. `GET
  /auth/google` guarda estado e verificador num cookie assinado de 10 minutos
  (httpOnly, SameSite=Lax) e vai ao Google; `/auth/google/retorno` confere o
  estado, troca o código no servidor e confere emissor, público, validade e
  e-mail verificado do `id_token` (veio direto do Google por HTTPS, então a
  assinatura não precisa ser conferida). Entra na conta ligada (`identidades`:
  provedor + sub); senão na conta do mesmo e-mail verificado (junta); senão cria
  uma conta sem senha (`senha_hash` vazio; a tabela `usuarios` não precisou
  mudar). Volta ao app com o token no fragmento (`/entrar/google#token=...`),
  que não passa por servidor nem log.
- Ligar o Google a uma conta logada: `POST /auth/google/ligar` dá um bilhete de
  5 minutos (o token de acesso não vai na URL). Desligar exige ter senha.
- Tokens internos (`assinar`/`ler_assinado`, com `typ`) nunca servem de acesso.
- `GET /auth/provedores` diz o que está configurado: sem `GOOGLE_CLIENT_ID` e
  `GOOGLE_CLIENT_SECRET`, o botão nem aparece.

### Mesas (`api/mesas.py` e `api/rotas/mesas.py`)

- Tabelas `mesas` (nome, criador, código de convite, permissões dos mestres
  em JSON) e `membros_mesa` (papel `jogador` ou `mestre`).
  `personagens.mesa_id`: **uma mesa por vez**, e o personagem fica preso a
  ela (ver "Nível da mesa, cópia e plano"; apagar a mesa só desvincula).
- **Entrada:** pelo código de 8 caracteres exibido na mesa (sem 0/O/1/I/L);
  o link do convite usa o mesmo código (`POST /mesas/entrar/{codigo}`). Entra
  como jogador. O criador pode gerar um código novo, invalidando o antigo.
- **Papéis:** o criador é mestre e é o único que administra (renomear,
  apagar, mudar papéis, remover membros, novo código, permissões). Ele
  escolhe quem é mestre e liga/desliga cada permissão **para todos os
  mestres de uma vez**: `ver_fichas`, `aplicar_dano`, `aplicar_condicoes`,
  `preparar` (criar e editar inimigos e NPCs). O criador pode tudo, sempre.
  Mesas antigas sem uma chave nova recebem o padrão (`PERMISSOES_PADRAO`).
- **Mestre só lê e age em jogo:** vê a ficha, aplica dano e condições pelas
  rotas `/mesas/{id}/personagens/{pid}/...`. As rotas de edição do
  personagem continuam só do dono (para o mestre, o personagem "não existe"
  ali: 404).
- **Acesso:** quem não é membro recebe 404 na mesa; membro sem permissão,
  403. Sair ou ser removido desvincula os personagens daquele jogador.
- O repositório separa achar a linha (`linha_do_dono`, `linha_na_mesa`) de
  montar/gravar o personagem (`montar`, `gravar`), para dono e mestre usarem
  o mesmo caminho.

### Quadros: mapa mental da sessão e da campanha (`motor/quadro.py`, `api/rotas/quadro.py`)

Decisões do projeto (2026-10-13):
- **Um quadro por sessão** (`sessoes.quadro`, JSON de `motor.quadro.Quadro`):
  cartões `nota` (título, texto com **negrito**/_itálico_, cor), `item` (NPC,
  inimigo, encontro ou personagem da mesa; a API devolve nome e foto em
  `itens`) e `imagem` (id de /imagens, com legenda), ligados por setas com
  texto opcional. Cada cartão tem um ponto de ligação em cada lado e qualquer
  lado liga em qualquer lado (modo "solto" do React Flow; soltar em qualquer
  parte do cartão encaixa no lado mais perto); a ligação guarda o lado de cada
  ponta (`de_ponto`/`para_ponto`: topo, direita, baixo, esquerda). Só o mestre responsável edita (a sessão compartilhada só lê).
  A tela salva o quadro inteiro sozinha, 800 ms depois da última mudança.
- Cada cartão é privado até o mestre marcar **"Mostrar aos jogadores"**
  (`revelado`). `so_revelado` (motor) é o que os jogadores podem ver: os
  cartões revelados e só as ligações **entre dois revelados** (uma seta para um
  cartão escondido entregaria que ele existe).
- **Quadro da campanha** (`GET /mesas/{id}/quadro-da-campanha`, qualquer
  membro): junta o revelado de todas as sessões, uma região por sessão (ids
  prefixados pela sessão; layout em `web/src/lib/quadro.ts`). Não se edita
  direto: enche conforme os mestres revelam. A tela recarrega a cada 10 s.
- Validação no motor: ids únicos, ligações para cartões existentes, até 300
  cartões e 600 ligações, cores conhecidas, item e imagem preenchidos.
- Interface: React Flow (`@xyflow/react`, MIT) para zoom, arrastar e ligar
  (sem minimapa).
  Carregado sob demanda (`lazy`): só baixa quem abre um quadro. A sessão
  aberta ganhou sub-abas (Planejamento, Quadro, Encontros, Personagens) e a
  mesa tem a aba "Quadro da campanha" para todos.

### Revelar aos jogadores (`api/rotas/revelado.py`)

Decisões do projeto (2026-10-13):
- **Encontro à mostra** (`encontros.visivel`, "Mostrar aos jogadores", só o
  responsável liga) aparece para os jogadores **só com a sessão em andamento**.
  O mestre pode esconder um inimigo específico (`Combatente.escondido`, ex.:
  ainda Oculto).
- Dos inimigos à mostra os jogadores veem **nome na luta, foto, vitalidade e
  condições**; nunca PV, dano, habilidades, Dificuldade ou outros números.
- **Vitalidade em terços** dos PV que restam (`motor.encontro.vitalidade`):
  mais de 2/3 é vida cheia, mais de 1/3 metade da vida, menos vida baixa, zero
  derrotado (6 PV: 6-5 cheia, 4-3 metade, 2-1 baixa). Conta em inteiros
  (restam × 3 contra o total × 2), sem arredondamento.
- **NPC conhecido** (`npcs.revelado`, permissão `preparar`): os jogadores veem
  nome, foto e descrição (nunca motivações nem notas). Fica conhecido entre as
  sessões (o que os jogadores aprenderam não some quando a sessão acaba).
- `GET /mesas/{id}/revelado` (qualquer membro) junta os dois; a aba Mesa mostra
  "Em combate: ..." e "NPCs conhecidos". Atualiza ao vivo (ver abaixo).

### Guia de Batalha (`motor/guia_batalha.py`)

Regra do SRD ("Battle Points", p. 71; p. 197 da edição brasileira). Cada
encontro guarda as escolhas do mestre (`encontros.guia`: nº de PJs, patamar do
grupo, luta mais fácil/difícil, +1d4 no dano) e a API devolve o guia calculado
junto com o encontro: PB iniciais (3 × PJs + 2), ajustes (os de composição —
2+ solos, patamar inferior, sem brutamonte/horda/líder/solo — são automáticos),
gastos por tipo e saldo. Lacaios contam por grupo do tamanho do grupo de PJs,
arredondando para cima. É só auxílio: passar do orçamento não é bloqueado.
Sem escolhas salvas, o nº de PJs vem da mesa (nº de personagens, ou 4). O
**patamar do grupo vem sempre do nível da mesa** (não é escolha do mestre).

**Regra da casa** (2026-10-12), no lugar do "+1 se escolher adversário de
patamar inferior" do SRD: cada adversário dá +1 PB por patamar abaixo do grupo
e −1 PB por patamar acima (lacaios contam por grupo). O guia traz `custos` por
tipo e `POST .../guia/simular` devolve o guia como ficaria com uma escolha (nada
é salvo): a tela mostra, ao escolher, quanto ela custa e quanto muda o total. Tipos com os nomes da edição brasileira: comum, oportunista,
manipulador, assistente, brutamonte.

### Nível da mesa, cópia e plano

- **Nível da mesa** (`mesas.nivel_maximo`, 1 a 10): mesa nova começa no 1;
  as que já existiam na migração ficaram no 10. Muda com `PUT /mesas/{id}/nivel`,
  permissão `nivel` (como `preparar`: o criador sempre pode e decide pelos
  outros mestres). Baixar não desfaz níveis: quem já passou só não sobe mais.
- A regra fica no motor: `Personagem.nivel_limite` (estado atual, como a
  reserva) trava `subir_de_nivel`. A API preenche com o nível da mesa ao
  carregar, **depois** de refazer o histórico (senão baixar o nível da mesa
  impediria carregar o personagem). `proximo_nivel()` e a linha do tempo dizem
  `bloqueado_pela_mesa`.
- **Personagem preso à mesa:** um personagem sem mesa entra numa mesa
  (`PUT /personagens/{id}/mesa`) se estiver no nível dela ou abaixo; dali em
  diante não sai nem troca de mesa. Para jogar em outra, **cópia**
  (`POST /personagens/{id}/copia`): mesma criação, histórico até o nível da
  mesa nova, equipamento e reserva quando ainda valem, sessão zerada. O
  original fica onde está. Sair da mesa, ser removido ou a mesa ser apagada
  ainda solta os personagens (ficam sem mesa).
- **Plano** (`Personagem.plano`, coluna `personagens.plano`): os níveis da
  cópia acima do limite viram níveis planejados. `aplicar_plano()` sobe o
  próximo nível com o plano (validado como qualquer subida; se não valer mais,
  o erro aparece e o plano fica); `descartar_plano(nivel)` tira um nível para
  escolher outra coisa; subir de nível na mão supera o plano daquele nível.
  Planejar níveis à mão (sem cópia) ainda não existe.

### Fotos (`api/rotas/imagens.py`)

- `POST /imagens` (com login, multipart) guarda JPG, PNG ou WebP de até 2 MB
  na tabela `imagens` (no banco: funciona igual no SQLite e no PostgreSQL). O
  tipo é conferido pelos primeiros bytes, não pelo nome do arquivo.
- `GET /imagens/{id}` é aberto (a tag `<img>` não manda token); o id é um
  UUID aleatório, então só quem tem o link abre. Cache longo: trocar a foto
  gera outro id.
- Personagem (`personagens.foto`, `PUT /personagens/{id}/foto`), NPC
  (`npcs.foto`) e inimigo (`Adversario.foto`, vai junto na cópia para o
  encontro) guardam só o id. Imagens trocadas ficam no banco (sem limpeza
  automática por enquanto).

### Conteúdo do mestre (`motor/adversarios.py` e `api/rotas/conteudo.py`)

- **Um formato só de adversário** (`Adversario`) para os 129 do SRD, para os
  inimigos criados do zero e para a ficha de combate de NPC. Descartado: um
  formato livre para inimigos próprios, porque a sessão de jogo (PV/PF por
  clique, estados de vitalidade) precisa dos mesmos números em todos.
- `validar()` no motor confere o que a ficha precisa para funcionar: patamar
  1–4, lacaio **sem** limiares e os demais com Maior (Grave opcional e maior
  que o Maior), dano `2d8+3`/`12`, ataque `+3`/`+2d4`, alcance válido,
  `horda_por_pv` só em horda. Erro vira 422 `"tipo": "regra"`, como no resto.
- `de_srd()` lê o JSON do seansbox/daggerheart-srd (`data/srd/adversarios.json`)
  e trata as variações do SRD: "Horde (5/HP)", limiares "None" e "4/None",
  dano "phy/mag", ataque "+2d4", características "Nome - Ação: detalhe"
  (contagens regressivas vão para `detalhe`).
- **Biblioteca da mesa:** tabelas `inimigos` (adversário em JSON) e `npcs`
  (nome, descrição, motivações, notas, `ficha_combate` JSON opcional), com
  `ON DELETE CASCADE` da mesa. Copiar do SRD faz uma cópia profunda com
  `base_id` (a origem; editar não a muda), para o mestre ajustar sem afetar
  o catálogo.
- **Privado:** jogador recebe 404 (não sabe que existe). Ver exige ser
  mestre; criar/editar/apagar exige `preparar`. Revelar informações aos
  jogadores é uma entrega futura.

### Sessões do mestre (`api/sessoes.py`, `api/rotas/sessoes.py` e `api/rotas/encontros.py`)

- **Sessão** (`sessoes`): planejada e conduzida por UM mestre, o
  **responsável** (quem criou; criar exige `preparar`). Tem título, data,
  resumo/objetivos, notas privadas, NPCs e inimigos da biblioteca que devem
  aparecer, situação (planejada, em andamento, encerrada), o próprio **Medo** e
  os encontros. Decisões do projeto (2026-10-12):
  - outros mestres não veem nada, a menos que o responsável compartilhe
    (`PUT .../compartilhar`); quem recebe só lê. Quem não pode ver recebe 404;
    quem vê mas não é o responsável recebe 403 ao mudar algo;
  - o Medo é **por sessão** (0 a 12, `motor.encontro.ajustar_medo`) e sempre
    começa no número de personagens em jogo: os da mesa **sem os do mestre
    responsável** (quem mestra uma sessão pode jogar em outra; com 1
    personagem dele na mesa, N − 1), no máximo 12;
  - o livro pede que o Medo fique visível: `GET /mesas/{id}` traz
    `medo_em_jogo` das sessões **em andamento** para todos os membros, só com o
    nome do mestre (o título pode ter spoiler).
- **Encontros** ficam dentro da sessão (`encontros.sessao_id`, rotas em
  `/mesas/{id}/sessoes/{sid}/encontros/...`) e seguem o acesso dela: só o
  responsável monta e conduz. **Não têm ordem**: um encontro pode nunca
  acontecer, conforme o caminho dos jogadores. Os encontros anteriores (de
  teste) foram apagados na migração. Quando o quadro de mapa mental existir,
  ele entra na sessão.
- **Encontro** = lista de `Combatente`: uma **cópia** da ficha do adversário
  (editar o inimigo na biblioteca não mexe na luta em andamento) + PV, PF e
  condições marcados. A origem pode ser um inimigo da mesa, a ficha de combate
  de um NPC ou o SRD (`origem: "inimigo:<id>"`...). Várias cópias do mesmo
  nome são numeradas ("Lobo 1", "Lobo 2"), continuando a contagem.
- **Dano em adversário** (`receber_dano`): mesmos limiares dos PJs (abaixo do
  Maior 1 PV, Maior 2, Grave 3); resistência divide por 2 (arredonda para
  cima, `motor.numeros.metade`: convenção do projeto para toda metade) antes
  de comparar; lacaio cai com qualquer dano; marcar o último PV
  derrota. Clicar nos quadradinhos usa `definir_marcas` (valores absolutos).
  Na tela, PV e PF (inimigos **e PJs**, armadura e companheiro também)
  **começam cheios** e esvaziam com o dano (quadradinho cheio = o que resta;
  `Espacos restantes` em `ui.tsx`); a API continua guardando os marcados, como
  a ficha do livro.
  O dano massivo (regra opcional) ficou de fora.
- Encontro guardado como JSON (`encontros.combatentes`), com `ON DELETE
  CASCADE` da sessão e da mesa.
- Interface: aba **Sessões** da mesa (mestres): lista das sessões que você
  pode ver e "Planejar sessão"; a sessão aberta tem situação, Medo,
  planejamento (salvo de uma vez), compartilhamento, os encontros (um cartão
  por combatente: PV/PF clicáveis, dano com "resistente", condições, ficha
  completa, Guia de Batalha) e os personagens da mesa (ficha resumida, dano e
  condições pelas permissões `ver_fichas`, `aplicar_dano`,
  `aplicar_condicoes`). Na aba Mesa, todos veem o Medo das sessões em andamento.

Ainda não: jogadores verem as fichas uns dos outros, controle de concorrência entre duas edições
simultâneas do mesmo personagem (ex.: mestre aplica dano enquanto o jogador
descansa).

### Ao vivo (`api/eventos.py` e `api/rotas/eventos.py`)

Decisões do projeto (2026-10-13): ficam ao vivo o combate e o Medo, a ficha
(dano e condições do mestre aparecem para o jogador), os quadros e a mesa com
as sessões compartilhadas; com presença (bolinha verde em quem está online).

- **Server-Sent Events**, não WebSocket: o servidor só precisa avisar; as
  mudanças continuam indo pelas rotas normais (com validação e permissões).
  `GET /eventos?token=...` (o `EventSource` do navegador não manda cabeçalho,
  então o token vem na URL). Comentário `: ping` a cada 15 s; o fluxo se renova
  a cada hora e o navegador reconecta sozinho.
- **Avisos sem dados**: só `{"tipo": "mesa", "id"}` ou
  `{"tipo": "personagem", "id", "mesa_id"}`. A tela invalida o cache (React
  Query) e busca de novo com as próprias permissões, então um aviso nunca vaza
  o que o usuário não pode ler (ex.: biblioteca do mestre). Descartado: mandar
  o dado no aviso, que obrigaria repetir as regras de visibilidade no envio.
- **Gancho no banco**, não em cada rota: `before_flush` anota o que o commit
  toca (mesa, membro, inimigo, NPC, sessão, encontro, personagem, nível),
  `after_commit` avisa os membros da mesa e o dono do personagem, `after_rollback`
  descarta. Rota nova fica coberta sem lembrar de avisar; erro não avisa ninguém.
  Sem ninguém conectado o gancho não faz nada.
- **Presença**: quem tem um fluxo aberto está online (`MembroSaida.online`);
  conectar e desconectar avisa as mesas da pessoa.
- Ao reconectar (queda de rede, servidor reiniciado) a tela recarrega tudo,
  porque pode ter perdido avisos.
- O quadro aberto por quem só lê (jogador, outro mestre) remonta a cada
  mudança; o do responsável não, para não perder o que ele está arrastando.
- Limite: a central vive na memória de **um** processo. Com vários servidores,
  trocar por Redis (pub/sub) mantendo a mesma interface.
- Desenvolvimento no Windows: o `--reload` do Uvicorn reinicia o processo com
  Ctrl+C, e esse sinal se perde enquanto há um fluxo aberto (testado com um app
  mínimo, sem o nosso código; continua travado mesmo depois que o cliente
  desconecta). Com a página aberta, depois de mudar o Python pare a API e rode
  de novo.

## Interface web (fase 3, `web/`)

React 19 + TypeScript + Vite, Tailwind CSS v4, React Router e React Query.

- **Regras ficam no motor.** A tela guia (ex.: só libera "Continuar" quando
  os atributos estão distribuídos) mas quem decide é a API; a mensagem de
  `RegraViolada` aparece para o jogador. O que a escolha do próximo nível
  precisa saber vem de `GET /personagens/{id}/proximo-nivel`
  (`Personagem.proximo_nivel()`): conquista de tier, avanços disponíveis,
  atributos marcados e quantos treinos o companheiro exige.
- **Tipos gerados da API:** `npm run api:tipos` exporta o OpenAPI do FastAPI
  (`api/exportar_openapi.py`) e gera `web/src/api/esquema.d.ts`. Front e back
  não divergem em silêncio: mudou a API, o `tsc` aponta onde.
- **Dados:** React Query com uma chave por recurso; mutações invalidam o
  personagem para ficha e linha do tempo se atualizarem. O catálogo do SRD
  fica em cache longo e serve para trocar ids da ficha por nomes.
- **Login:** token no `localStorage`; 401 com token desloga e volta para
  /entrar.
- **Desenvolvimento:** o Vite encaminha `/api/*` para o FastAPI (sem CORS).
- **Visual:** azul-escuro (Medo) como base e laranja (Esperança) como
  destaque, tema escuro padrão e claro opcional, tudo em variáveis CSS.

Telas: entrar/cadastro, lista de personagens, criação passo a passo (classe,
subclasse + companheiro, herança com ancestralidade mista, atributos,
Experiências, cartas, revisão) e personagem (abas Ficha e Linha do tempo,
excluir, desfazer último nível).

**Linha do tempo e subir de nível:** os níveis 1 a 10 ficam lado a lado com
rolagem horizontal (abre no próximo nível). Embaixo de cada nível aparece a
caixa de avanços do patamar, como a página de Level Up do livro: um
quadradinho por vez que a opção pode ser marcada, duplo nas que valem dois
avanços. Os dados vêm do motor (`Personagem.quadros_de_avanco`, em cada
evento de `linha_do_tempo()` como `quadros`): por opção, `limite`, `antes`
(marcados em níveis anteriores), `neste` (no próprio nível) e `riscados`
(cortados por regra: subclasse risca a multiclasse do patamar e vice-versa;
contados à parte porque o motor risca preenchendo `slots_usados`).
- Nível feito: o patamar dele e os anteriores de onde vieram avanços.
- Próximo nível: a caixa é interativa (checkbox por quadradinho) e todo o
  level up acontece ali (`EscolhaDeNivel`): conquista, avanços (detalhes como
  quais atributos ou qual carta aparecem logo abaixo), treinos do
  companheiro, carta do nível e confirmar. Patamares anteriores com
  quadradinho livre ficam num "Usar um patamar anterior" recolhível.
  Substituiu o assistente em etapas (`/personagens/{id}/subir` saiu).
- Níveis futuros: só consulta, com o que resta no patamar. Planejar
  (marcar e guardar um plano) ficou de fora por ora.

Mesas: lista, criar, entrar por código ou link (`/convite/CODIGO`; sem login,
a tela de entrar volta para o convite depois), página da mesa com convite,
membros (o criador muda papéis e remove), personagens (trazer/tirar os seus)
e permissões dos mestres. Mestres veem também as abas **Inimigos** (catálogo
do SRD com busca e filtros, "Adicionar à mesa", criar do zero, editar) e
**NPCs** (ficha simples + ficha de combate opcional, com o mesmo editor de
inimigo). A ficha do inimigo segue o bloco do SRD; textos com `**negrito**`,
`_itálico_` e listas são lidos por `web/src/lib/texto.ts` (sem HTML cru).

**Equipamento** (aba do personagem): arma principal, secundária e armadura
do catálogo do SRD, com busca e filtro por patamar; arma de duas mãos ocupa a
secundária; salvar manda tudo de uma vez (`PUT /equipamento`) e o motor valida
(arma mágica, requisitos). `GET /equipamento` devolve os ids equipados.

Ainda não na interface: estado de sessão do próprio jogador (marcar
PV/Fadiga, descansos) — a API já tem.

### App no celular (PWA, `web/public/sw.js` e `web/src/lib/pwa.ts`)

Decisões do projeto (2026-10-13): app instalável (PWA) a partir do próprio
site, com todas as telas adaptadas ao celular. Descartados: empacotar a web
num app de loja (Capacitor), que pede contas nas lojas e um Mac para o iOS, e
um app nativo (React Native), que seria uma segunda interface para manter.

- **Instalação**: `manifest.webmanifest` + ícones em `public/icones/`
  (192/512, um "maskable" com o desenho na zona segura para o Android recortar,
  e o `apple-touch-icon` do iPhone). No Chrome/Edge aparece "Instalar app" no
  topo (`beforeinstallprompt`); no iPhone é Compartilhar → "Adicionar à Tela
  de Início". Só instala em HTTPS (ou `localhost`).
- **Service worker escrito à mão** (sem `vite-plugin-pwa`/Workbox: são ~60
  linhas e uma dependência a menos). Guarda só a casca do app: páginas pela
  rede com a casca de reserva sem rede, `/assets/*` (nome com hash) do cache,
  ícones e fontes do cache atualizando por trás. **Nunca intercepta `/api`**:
  dados de jogo vêm sempre do servidor com as permissões de quem pede, e o
  fluxo ao vivo não pode ficar preso em cache. A decisão por pedido está em
  `estrategia()`, testada em `pwa.test.ts`. Mudou a forma de guardar? Troque
  `VERSAO` no `sw.js` (o antigo é apagado ao ativar).
- Registro só no build (`import.meta.env.PROD`): no `npm run dev` o cache
  atrapalharia o recarregamento do Vite. Para testar: `npm run build` e
  `npx vite preview` (usa o mesmo proxy `/api`).
- **Sem conexão**: o app abre e mostra "Sem conexão" no topo; nada é salvo
  offline (sem fila de mudanças: mestre e jogadores mexem nas mesmas fichas e
  uma fila sem rede criaria conflitos). Quando a rede volta, o fluxo ao vivo
  reconecta e a tela recarrega tudo.
- **Telas**: as abas rolam para os lados (a escolhida sempre à vista); colunas
  com campo de texto usam `minmax(0,1fr)` para não estourar a largura; no toque
  (`pointer: coarse`) os pontos de ligação do quadro ficam maiores, e apagar
  no quadro tem botão no painel (celular não tem tecla Delete). Conferido sem
  rolagem lateral em 360 px e 390 px.

## Tradução pt-BR (`data/traducoes/pt-BR/`)

Tradução **não oficial** do SRD, feita pelo projeto. É só de exibição: o
motor interpreta o texto em inglês do SRD (bônus "+1 to Evasion", nomes como
"Fortified") ao carregar, e só depois a `Biblioteca(idioma="pt-BR")` troca
nomes e textos. O inglês fica em `nome_original` (a interface mostra ao lado).
A API usa pt-BR; o motor e os testes dele usam o inglês.

- `herancas.json`: classes, subclasses, comunidades, domínios, ancestralidades
  (com as duas características, na ordem do SRD).
- `caracteristicas.json`: características de armas/armaduras, traduzidas pelo
  **texto** em inglês (o mesmo nome/texto se repete em muitos itens).
- `equipamento.json`: nomes de armas e armaduras com gênero; itens
  `improved_/advanced_/legendary_` são compostos (Espada Larga + Aprimorada).
- `cartas/<DOMINIO>.json`: nome e texto de cada carta (grimórios com o nome
  de cada magia; listas com "•").
- `itens.json`: saque e consumíveis (nomes do livro básico brasileiro,
  descrições traduzidas por nós do SRD), itens iniciais e itens de classe
  (pelo texto em inglês).
- `adversarios/lote*.json`: por id do adversário, nome, arma, descrição,
  motivações, experiências (inglês → português) e características **na mesma
  ordem e quantidade** do SRD (senão o id conta como faltando).
- `tests/test_traducao.py` exige que nada fique sem tradução
  (`Biblioteca.traducoes_faltando`) e que as regras sejam idênticas nos dois
  idiomas.
- `Classe.codigo` ("BARD") liga subclasse à classe; `Classe.nome` é só exibição.

Glossário (alinhado à edição brasileira quando conhecida):

| SRD | pt-BR | | SRD | pt-BR |
|---|---|---|---|---|
| Hope / Fear | Esperança / Medo | | Stress | Fadiga (PF) |
| traits | atributos | | upgraded subclass card | carta de subclasse aprimorada |
| Hit Points | Pontos de Vida (PV) | | Armor Slot / Score | espaço / Pontuação de Armadura |
| Evasion | Evasão | | damage thresholds | limiares de dano |
| Minor / Major / Severe | Menor / Maior / Grave | | Proficiency | Proficiência |
| roll (action, reaction...) | teste (de ação, de reação...) | | damage roll | rolagem de dano |
| Spellcast Roll | teste de Conjuração | | Tier | patamar |
| Melee / Very Close / Close | corpo a corpo / muito próximo / próximo | | Far / Very Far | distante / muito distante |
| Duality Dice / Hope Die | Dados de Dualidade / Dado de Esperança | | GM | mestre |
| loadout / vault | mão / reserva | | Recall Cost | custo de troca |
| Hidden / Restrained / Vulnerable | Oculto / Contido / Vulnerável | | Death Move | Movimento de Morte |
| tokens | marcadores | | Countdown | Contagem Regressiva |
| spotlight | pôr em destaque | | PCs | PJs |
| Spend a Fear | gaste 1 Ponto de Medo | | mark a Stress | marque 1 PF |
| Relentless / Momentum | Implacável / Embalo | | Minion / Horde | Lacaio / Horda |
| Bruiser / Skulk / Ranged | Brutamonte / Oportunista / Atirador | | Leader / Support / Standard | Líder / Assistente / Comum |
| Social (adversary) | Manipulador | | Battle Points | Pontos de Batalha (PB) |
| Loop (countdown) | Ciclo | | Group Attack | Ataque em Grupo |

Nomes de subclasses, ancestralidades e comunidades seguem o livro básico
brasileiro (pp. 14-16; conferido em 2026-10-13, travado em `test_traducao.py`):

| SRD | pt-BR | | SRD | pt-BR |
|---|---|---|---|---|
| Wordsmith / Troubadour | Beletrista / Trovador | | Warden of the Elements / of Renewal | Protetor dos Elementos / da Renovação |
| Elemental / Primal Origin | Elementalista / Primordialista | | Stalwart / Vengeance | Baluarte / Vingador |
| Call of the Brave / Slayer | Escolhido da Bravura / da Matança | | Nightwalker / Syndicate | Gatuno / Mafioso |
| School of Knowledge / War | Discípulo do Conhecimento / da Guerra | | Wayfinder / Beastbound | Rastreador / Treinador |
| Divine Wielder / Winged Sentinel | Portador Divino / Sentinela Alada | | Halfling / Ribbet | Pequenino / Quacho |
| Clank, Drakona, Galapa, Infernis | (mesmos nomes) | | Simiah | Símio |
| Highborne / Loreborne / Orderborne | Aristocrática / Erudita / Disciplinada | | Ridgeborne / Seaborne / Slyborne | Montanhesa / Marítima / Fora da lei |
| Underborne / Wanderborne / Wildborne | Subterrânea / Nômade / Silvestre | | | |

## Pendências conhecidas

- `progressao.json` conferido (2026-10-09) com o SRD e a ficha oficial.
  Duas diferenças de redação entre as fontes; o motor segue o SRD:
  - Multiclasse risca a subclasse **deste tier** (SRD). A ficha diz "an
    unused 'Take an upgraded subclass card'" (qualquer tier).
  - Avanços podem vir de **qualquer tier anterior** (SRD: "your tier or
    below"). A ficha diz "any from the previous tier".
- Existe um SRD 2.0 (agosto/2026) com classes novas. Os JSON atuais são do 1.0.
  Como o motor só fala com a `Biblioteca`, a troca fica isolada em `srd.py`.
- Desfazer o nível da multiclasse não revalida uma arma mágica já equipada.
