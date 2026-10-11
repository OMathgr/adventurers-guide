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
   nos níveis 5 e 8 limpa as marcas dos traços.
2. **Dois avanços** do tier atual ou anterior. Proficiência e Multiclasse valem por dois.
3. **Limiares de dano** +1 (o bônus é igual ao nível).
4. **Uma carta de domínio** de nível ≤ ao seu. Opcionalmente troca uma carta antiga
   por outra de nível igual ou menor.

Restrições checadas:

- quantidade de usos de cada opção por tier (`data/progressao.json`);
- traço marcado não sobe até a próxima conquista de tier;
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
  traço de conjuração (inclusive a da multiclasse).

No banco, o equipamento vira colunas (ou tabela) do `personagem`, não de
`subida_de_nivel`.

### Características de armas e armaduras

O SRD só traz texto. A `Biblioteca` extrai os **bônus fixos** dele
(`_modificadores` em `srd.py`): cada trecho separado por `;` no formato
`+N to <alvo>`, com `<alvo>` na tabela `ALVOS_SRD` (Evasão, Pontuação de
Armadura, limiar grave, ataque, traços). Os valores vêm do próprio SRD, então
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
  O traço é checado com todo o equipamento aplicado.
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

### Loadout e cofre (estado atual, fora do histórico)

Como o equipamento, mudar o que está ativo acontece em jogo. O `Personagem`
guarda só `cofre` (vault); toda carta que ele tem e não está no cofre está no
loadout. A ficha mostra `cartas_ativas` e `cartas_cofre`.

- Limite do loadout em `progressao.json` (`limite_loadout`: 5).
- Carta nova entra no loadout; se ele estiver cheio, vai para o cofre.
- Troca de uma carta que estava no cofre: a nova fica no cofre.
- `guardar_carta` é grátis. `recuperar_carta` marca o Recall Cost em
  Estresse (0 em descanso) e é recusada sem Estresse livre suficiente.
  Com o loadout cheio, exige `no_lugar_de`.
- Desfazer um nível tira do cofre as cartas que deixaram de existir.

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
principal e, se houver, a da multiclasse (o SRD define o traço de conjuração
na subclasse, e cada subclasse pode usar um traço diferente). Subclasse sem
traço (ex.: Guerreiro) não gera entrada.

Bônus = traço de conjuração já com modificadores de equipamento (ex.: Gilded
+1 Presença) + bônus "to Spellcast Rolls" (Channeling). É calculado em
`_vestir`, porque depende dos traços modificados.

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
  um JWT HS256 com o id do usuário e validade (`JWT_EXPIRA_MINUTOS`, padrão 60).
  A chave vem de `JWT_SECRET`; sem ela, uma chave temporária é gerada.
- Rotas de personagem usam a dependência `acesso` (banco + usuário logado).
  O repositório filtra tudo pelo dono: personagem de outro usuário responde
  404, igual a um inexistente, para não revelar que existe.
- Login errado responde a mesma mensagem para e-mail inexistente e senha
  errada.
- `Base.metadata` tem convenção de nomes para índices e restrições (o
  Alembic precisa deles para alterar tabelas no SQLite).

### Mesas (`api/mesas.py` e `api/rotas/mesas.py`)

- Tabelas `mesas` (nome, criador, código de convite, permissões dos mestres
  em JSON) e `membros_mesa` (papel `jogador` ou `mestre`).
  `personagens.mesa_id`: **uma mesa por vez** (apagar a mesa só desvincula).
- **Entrada:** pelo código de 8 caracteres exibido na mesa (sem 0/O/1/I/L);
  o link do convite usa o mesmo código (`POST /mesas/entrar/{codigo}`). Entra
  como jogador. O criador pode gerar um código novo, invalidando o antigo.
- **Papéis:** o criador é mestre e é o único que administra (renomear,
  apagar, mudar papéis, remover membros, novo código, permissões). Ele
  escolhe quem é mestre e liga/desliga cada permissão **para todos os
  mestres de uma vez**: `ver_fichas`, `aplicar_dano`, `aplicar_condicoes`.
  O criador pode tudo, sempre.
- **Mestre só lê e age em jogo:** vê a ficha, aplica dano e condições pelas
  rotas `/mesas/{id}/personagens/{pid}/...`. As rotas de edição do
  personagem continuam só do dono (para o mestre, o personagem "não existe"
  ali: 404).
- **Acesso:** quem não é membro recebe 404 na mesa; membro sem permissão,
  403. Sair ou ser removido desvincula os personagens daquele jogador.
- O repositório separa achar a linha (`linha_do_dono`, `linha_na_mesa`) de
  montar/gravar o personagem (`montar`, `gravar`), para dono e mestre usarem
  o mesmo caminho.

Ainda não: renovação de token (refresh) e "esqueci minha senha", jogadores
verem as fichas uns dos outros, controle de concorrência entre duas edições
simultâneas do mesmo personagem (ex.: mestre aplica dano enquanto o jogador
descansa), atualização em tempo real.

## Interface web (fase 3, `web/`)

React 19 + TypeScript + Vite, Tailwind CSS v4, React Router e React Query.

- **Regras ficam no motor.** A tela guia (ex.: só libera "Continuar" quando
  os traços estão distribuídos) mas quem decide é a API; a mensagem de
  `RegraViolada` aparece para o jogador. O que o assistente de level up
  precisa saber vem de `GET /personagens/{id}/proximo-nivel`
  (`Personagem.proximo_nivel()`): conquista de tier, avanços disponíveis,
  traços marcados e quantos treinos o companheiro exige.
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
subclasse + companheiro, herança com ancestralidade mista, traços,
Experiências, cartas, revisão), personagem (abas Ficha e Linha do tempo,
excluir, desfazer último nível) e subir de nível passo a passo.

Ainda não na interface: estado de sessão (marcar PV/Estresse, descansos),
equipamento, cofre de cartas e mesas (a API já tem tudo isso).

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
- `tests/test_traducao.py` exige que nada fique sem tradução
  (`Biblioteca.traducoes_faltando`) e que as regras sejam idênticas nos dois
  idiomas.
- `Classe.codigo` ("BARD") liga subclasse à classe; `Classe.nome` é só exibição.

Glossário (alinhado à edição brasileira quando conhecida):

| SRD | pt-BR | | SRD | pt-BR |
|---|---|---|---|---|
| Hope / Fear | Esperança / Medo | | Stress | Fadiga (PF) |
| Hit Points | Pontos de Vida (PV) | | Armor Slot / Score | espaço / Pontuação de Armadura |
| Evasion | Evasão | | damage thresholds | limiares de dano |
| Minor / Major / Severe | Menor / Maior / Grave | | Proficiency | Proficiência |
| roll (action, reaction...) | teste (de ação, de reação...) | | damage roll | rolagem de dano |
| Spellcast Roll | teste de Conjuração | | Tier | patamar |
| Melee / Very Close / Close | corpo a corpo / muito próximo / próximo | | Far / Very Far | distante / muito distante |
| Duality Dice / Hope Die | Dados de Dualidade / Dado de Esperança | | GM | mestre |
| loadout / vault | cartas ativas / cofre | | Recall Cost | custo de recuperação |
| Hidden / Restrained / Vulnerable | Oculto / Contido / Vulnerável | | Death Move | Movimento de Morte |
| tokens | marcadores | | Countdown | Contagem Regressiva |

## Pendências conhecidas

- `progressao.json` conferido (2026-10-09) com o SRD e a ficha oficial.
  Duas diferenças de redação entre as fontes; o motor segue o SRD:
  - Multiclasse risca a subclasse **deste tier** (SRD). A ficha diz "an
    unused 'Take an upgraded subclass card'" (qualquer tier).
  - Avanços podem vir de **qualquer tier anterior** (SRD: "your tier or
    below"). A ficha diz "any from the previous tier".
- Existe um SRD 2.0 (agosto/2026) com classes novas. Os JSON atuais são do 1.0.
  Como o motor só fala com a `Biblioteca`, a troca fica isolada em `srd.py`.
- Inventário (itens, ouro, consumíveis) ainda não existe.
- Desfazer o nível da multiclasse não revalida uma arma mágica já equipada.
