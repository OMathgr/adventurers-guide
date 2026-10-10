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

## Pendências conhecidas

- **Conferir `progressao.json` com a ficha oficial impressa** (número de
  quadradinhos por opção em cada tier). Os dados vieram da ficha e de um
  compêndio do SRD, mas vale a checagem manual.
- Existe um SRD 2.0 (agosto/2026) com classes novas. Os JSON atuais são do 1.0.
  Como o motor só fala com a `Biblioteca`, a troca fica isolada em `srd.py`.
- Características de armas e armaduras (ex.: Flexible +1 Evasão, Heavy −1
  Evasão, Reliable +1 no ataque) só existem como texto no SRD e ainda não têm
  efeito. Ideia: um mapa nosso em `data/` de nome da característica → efeito.
- Inventário (itens, ouro, consumíveis) ainda não existe.
- Desfazer o nível da multiclasse não revalida uma arma mágica já equipada.
- Ancestralidade mista e regras de companheiro do Ranger Beastbound.
