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

No banco de dados (fase 2), isso vira duas tabelas: `personagem` (com a
criação) e `subida_de_nivel` (uma linha por nível, com as escolhas em JSON).

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
- cartas do domínio da multiclasse têm nível ≤ metade do seu nível;
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

Domínio da multiclasse: no máximo metade do nível. As listagens recebem os
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

Ainda não aplicado: características que dependem de marcar espaços ou
Estresse (Fortified, Painful, Hopeful, Reinforced, Resilient etc.), limite
de descansos curtos seguidos e cuidar de aliados num descanso.

## Rolagem de conjuração

`Ficha.conjuracoes` traz uma `Conjuracao` por subclasse que conjura: a
principal e, se houver, a da multiclasse (o SRD define o traço de conjuração
na subclasse, e cada subclasse pode usar um traço diferente). Subclasse sem
traço (ex.: Guerreiro) não gera entrada.

Bônus = traço de conjuração já com modificadores de equipamento (ex.: Gilded
+1 Presença) + bônus "to Spellcast Rolls" (Channeling). É calculado em
`_vestir`, porque depende dos traços modificados.

## Pendências conhecidas

- **Conferir `progressao.json` com a ficha oficial impressa** (número de
  quadradinhos por opção em cada tier). Os dados vieram da ficha e de um
  compêndio do SRD, mas vale a checagem manual.
- Existe um SRD 2.0 (agosto/2026) com classes novas. Os JSON atuais são do 1.0.
  Como o motor só fala com a `Biblioteca`, a troca fica isolada em `srd.py`.
- Inventário (itens, ouro, consumíveis) ainda não existe.
- Desfazer o nível da multiclasse não revalida uma arma mágica já equipada.
- Ancestralidade mista e regras de companheiro do Ranger Beastbound.
