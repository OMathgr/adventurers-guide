"""Guia de Batalha (SRD, "Battle Points"): orçamento de Pontos de Batalha (PB)
para montar um encontro equilibrado.

- PB iniciais: 3 × número de PJs + 2.
- Ajustes: −1 luta mais fácil ou curta; −2 com 2 ou mais solos; −2 somando
  +1d4 (ou +2) ao dano de todos os adversários; +1 sem brutamonte, horda,
  líder ou solo; +2 luta mais difícil ou longa.
- Custos: 1 por grupo de lacaios do tamanho do grupo de PJs; 1 por
  manipulador (social) ou assistente (suporte); 2 por horda, atirador,
  oportunista (skulk) ou comum (standard); 3 por líder; 4 por brutamonte; 5 por solo.

**Regra da casa** (decisão do projeto, 2026-10-12) no lugar do "+1 com
adversário de patamar inferior" do SRD: CADA adversário dá +1 PB por patamar
abaixo do grupo e −1 PB por patamar acima (mesa no patamar 3: um inimigo de
patamar 1 dá +2; um de patamar 4 dá −1). Lacaios contam por grupo, como no custo.

Grupo de lacaios incompleto conta como um grupo (metades e frações arredondam
para cima no projeto). Os ajustes que dependem da composição (solos, patamar,
sem brutamontes...) são calculados a partir dos inimigos.
É só um guia: gastar mais ou menos do que o total não é proibido.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adversarios import TipoAdversario
from .erros import RegraViolada

CUSTO: dict[TipoAdversario, int] = {
    TipoAdversario.SOCIAL: 1, TipoAdversario.SUPORTE: 1,
    TipoAdversario.HORDA: 2, TipoAdversario.ATIRADOR: 2,
    TipoAdversario.ESPREITADOR: 2, TipoAdversario.PADRAO: 2,
    TipoAdversario.LIDER: 3, TipoAdversario.BRUTAMONTES: 4, TipoAdversario.SOLO: 5,
}
PESADOS = {TipoAdversario.BRUTAMONTES, TipoAdversario.HORDA, TipoAdversario.LIDER, TipoAdversario.SOLO}


@dataclass
class OpcoesDoGuia:
    """O que o mestre escolhe; o resto vem dos inimigos do encontro."""

    pjs: int = 4
    patamar: int = 1                 # patamar do grupo (para "adversário de patamar inferior")
    mais_facil: bool = False         # −1: luta mais fácil ou curta
    mais_dificil: bool = False       # +2: luta mais difícil ou longa
    dano_extra: bool = False         # −2: +1d4 (ou +2) no dano de todos os adversários


@dataclass
class Ajuste:
    descricao: str
    valor: int
    automatico: bool                 # veio da composição do encontro, não de uma escolha


@dataclass
class Gasto:
    tipo: TipoAdversario
    quantidade: int                  # adversários desse tipo
    custo: int                       # PB gastos com eles


@dataclass
class GuiaDeBatalha:
    opcoes: OpcoesDoGuia
    base: int
    ajustes: list[Ajuste] = field(default_factory=list)
    total: int = 0
    gastos: list[Gasto] = field(default_factory=list)
    gasto: int = 0
    saldo: int = 0                   # total − gasto (negativo: passou do orçamento)
    # custo de cada tipo, para a tela mostrar ao escolher (lacaio: por grupo de `pjs`)
    custos: dict[TipoAdversario, int] = field(
        default_factory=lambda: {TipoAdversario.LACAIO: 1, **CUSTO})


def validar_opcoes(o: OpcoesDoGuia):
    if not 1 <= o.pjs <= 12:
        raise RegraViolada("O grupo tem de 1 a 12 PJs.")
    if not 1 <= o.patamar <= 4:
        raise RegraViolada("O patamar vai de 1 a 4.")
    if o.mais_facil and o.mais_dificil:
        raise RegraViolada("Escolha luta mais fácil ou mais difícil, não as duas.")


def calcular(opcoes: OpcoesDoGuia, adversarios: list[tuple[TipoAdversario, int]]) -> GuiaDeBatalha:
    """`adversarios`: (tipo, patamar) de cada inimigo do encontro."""
    validar_opcoes(opcoes)
    tipos = [t for t, _ in adversarios]
    ajustes = []
    if opcoes.mais_facil:
        ajustes.append(Ajuste("Luta mais fácil ou curta", -1, False))
    if tipos.count(TipoAdversario.SOLO) >= 2:
        ajustes.append(Ajuste("2 ou mais solos", -2, True))
    if opcoes.dano_extra:
        ajustes.append(Ajuste("+1d4 (ou +2) no dano de todos os adversários", -2, False))
    inferior, superior = _ajuste_de_patamar(opcoes, adversarios)
    if inferior:
        ajustes.append(Ajuste("Adversários de patamar inferior (+1 por patamar, cada)", inferior, True))
    if superior:
        ajustes.append(Ajuste("Adversários de patamar superior (−1 por patamar, cada)", -superior, True))
    if not any(t in PESADOS for t in tipos):
        ajustes.append(Ajuste("Sem brutamonte, horda, líder ou solo", +1, True))
    if opcoes.mais_dificil:
        ajustes.append(Ajuste("Luta mais difícil ou longa", +2, False))

    gastos = []
    lacaios = tipos.count(TipoAdversario.LACAIO)
    if lacaios:
        gastos.append(Gasto(TipoAdversario.LACAIO, lacaios, -(-lacaios // opcoes.pjs)))   # grupos, para cima
    for tipo, custo in CUSTO.items():
        n = tipos.count(tipo)
        if n:
            gastos.append(Gasto(tipo, n, n * custo))

    base = 3 * opcoes.pjs + 2
    total = base + sum(a.valor for a in ajustes)
    gasto = sum(g.custo for g in gastos)
    return GuiaDeBatalha(opcoes=opcoes, base=base, ajustes=ajustes, total=total,
                         gastos=gastos, gasto=gasto, saldo=total - gasto)


def _ajuste_de_patamar(opcoes: OpcoesDoGuia, adversarios: list[tuple[TipoAdversario, int]]) -> tuple[int, int]:
    """(PB a mais pelos de patamar inferior, PB a menos pelos de patamar superior).
    Cada adversário conta a diferença de patamares; lacaios contam por grupo
    (de cada patamar), como no custo."""
    inferior = superior = 0
    lacaios: dict[int, int] = {}
    unidades = []
    for tipo, patamar in adversarios:
        if tipo is TipoAdversario.LACAIO:
            lacaios[patamar] = lacaios.get(patamar, 0) + 1
        else:
            unidades.append((patamar, 1))
    unidades += [(p, -(-n // opcoes.pjs)) for p, n in lacaios.items()]   # grupos, para cima
    for patamar, vezes in unidades:
        diferenca = opcoes.patamar - patamar
        if diferenca > 0:
            inferior += diferenca * vezes
        elif diferenca < 0:
            superior += -diferenca * vezes
    return inferior, superior
