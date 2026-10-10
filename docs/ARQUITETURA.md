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
