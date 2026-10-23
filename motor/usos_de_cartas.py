"""Usar uma carta de domínio na sessão (data/usos_de_cartas.json).

Cada carta que se ativa tem um "uso": custo (Esperança, PF, armadura,
marcadores da carta), limite (por sessão, descanso ou descanso longo), alvo,
opções (quando a carta tem mais de um efeito, como os grimórios; cada opção
pode ter custo, limite, alvo e quantidade próprios) e efeitos em você ou no
alvo: limpar PV/PF/armadura, ganhar Esperança, marcar PF, condição,
marcadores na carta, bônus até o descanso, ir para a reserva e tirar Medo do
mestre. O teste (Conjuração, Presença...) e o dano contra inimigos continuam
na rolagem e o mestre aplica no inimigo; o que a carta não automatiza fica no
texto e na `nota`.

Alvos: "si", "aliado" (um personagem da sessão), "qualquer" (você ou um
aliado), "aliados" (todos os outros da sessão) e "grupo" (todos, com você).

Quantidades ("q") e custos são expressões: número, dado ("1d4", "{n}d6"),
referência ("conjuracao", "AGILITY", "nivel", "proficiencia", "esperanca",
"marcadores" = os da carta, "pf_alvo", "n" = a quantidade escolhida,
"cartas:SAGE" = cartas do domínio que você tem), "2xn", "a+b", "a-b",
"min1:X" (no mínimo 1), "metade:X" (para cima) e "tudo".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .numeros import metade
from .rolagem import expandir, resolver

LIMITES = ("sessao", "descanso", "descanso_longo")
ALVOS = ("si", "aliado", "qualquer", "aliados", "grupo")
TIPOS_DE_EFEITO = ("limpa_pv", "limpa_pf", "limpa_armadura", "ganha_esperanca", "marca_pf", "condicao",
                   "tira_condicao", "marcadores", "bonus_temporario", "reserva", "tira_medo",
                   # mudam a rolagem que disparou a carta (só com gatilho)
                   "soma_na_rolagem", "vira_esperanca")
RESULTADOS = ("qualquer", "critico", "sucesso", "falha", "com_esperanca", "com_medo")
_DADO = re.compile(r"(\d+)d(\d+)(?:\+(\d+))?")


@dataclass(frozen=True)
class EfeitoDeCarta:
    tipo: str
    q: str | int = 1
    em: str = "alvo"                 # "alvo" (o(s) escolhido(s); você, se não houver) ou "si"
    condicao: str = ""               # condicao / tira_condicao
    modificadores: tuple[dict, ...] = ()   # bonus_temporario: [{"alvo": "AGILITY", "q": 2}]
    duracao: str = "descanso"        # bonus_temporario: até o descanso (ou "descanso_longo")

    @classmethod
    def de_json(cls, d: dict) -> EfeitoDeCarta:
        if d["tipo"] not in TIPOS_DE_EFEITO:
            raise ValueError(f"efeito de carta desconhecido: {d['tipo']}")
        return cls(tipo=d["tipo"], q=d.get("q", 1), em=d.get("em", "alvo"), condicao=d.get("condicao", ""),
                   modificadores=tuple(d.get("modificadores", ())), duracao=d.get("duracao", "descanso"))


@dataclass(frozen=True)
class Custo:
    """Cada valor é uma expressão (Copycat: "metade:n")."""

    esperanca: str | int = 0
    fadiga: str | int = 0
    armadura: str | int = 0
    marcadores: str | int = 0

    @classmethod
    def de_json(cls, d: dict | None) -> Custo:
        d = d or {}
        return cls(d.get("esperanca", 0), d.get("fadiga", 0), d.get("armadura", 0), d.get("marcadores", 0))


@dataclass(frozen=True)
class Gatilho:
    """A rolagem que dispara a carta: o registro oferece a carta nela.

    `se`: critico, sucesso, falha, com_esperanca, com_medo ou qualquer. Sem
    Dificuldade informada, o sucesso não é conhecido: sucesso e falha valem
    (o mestre confere). `de`: rolagem sua ("si"), de um aliado ou "qualquer"."""

    rolagens: tuple[str, ...] = ("teste", "ataque", "conjuracao", "reacao")
    se: str = "qualquer"
    de: str = "si"

    @classmethod
    def de_json(cls, d: dict | None) -> "Gatilho | None":
        if not d:
            return None
        g = cls(tuple(d.get("rolagens", cls.rolagens)), d.get("se", "qualquer"), d.get("de", "si"))
        if g.se not in RESULTADOS or g.de not in ("si", "aliado", "qualquer"):
            raise ValueError(f"gatilho inválido: {d}")
        return g

    def vale(self, r, propria: bool) -> bool:
        """`r`: ResultadoRolagem; `propria`: a rolagem é do personagem da carta."""
        if r.tipo not in self.rolagens or (self.de == "si" and not propria) or (self.de == "aliado" and propria):
            return False
        dual = r.dualidade.value if r.dualidade is not None else None
        return {"qualquer": True, "critico": dual == "critico",
                "sucesso": r.sucesso is not False or dual == "critico",
                "falha": r.sucesso is not True and dual != "critico",
                "com_esperanca": dual == "esperanca", "com_medo": dual == "medo"}[self.se]


@dataclass(frozen=True)
class OpcaoDeUso:
    id: str
    rotulo: str
    custo: Custo = Custo()
    por_unidade: Custo = Custo()
    efeitos: tuple[EfeitoDeCarta, ...] = ()
    alvo: str | None = None          # None: o da carta
    limite: str | None = None        # limite só desta opção (ex.: Arcane Barrage, 1x por descanso)
    quantidade: bool = True          # pede a quantidade da carta (se ela tiver)
    teste: str = ""


@dataclass(frozen=True)
class UsoDeCarta:
    """Como a carta se ativa. `por_unidade`: custo de cada unidade de `quantidade`."""

    custo: Custo = Custo()
    por_unidade: Custo = Custo()
    quantidade_max: str | int | None = None   # escolher n de `quantidade_min` até isto
    quantidade_min: int = 1
    quantidade_rotulo: str = ""
    limite: str | None = None
    alvo: str = "si"
    condicao: str | None = None   # "dominio:CODEX": 4 cartas do domínio na mão
    teste: str = ""               # dica para a tela: "Conjuração (15)"
    opcoes: tuple[OpcaoDeUso, ...] = ()
    efeitos: tuple[EfeitoDeCarta, ...] = ()
    # marcadores na carta: quantos ela tem no começo da sessão e ao voltar do descanso
    recarga: str | int | None = None
    recarga_quando: str = "descanso_longo"   # "descanso_longo", "descanso" ou "sessao" (só no começo)
    nota: str = ""                # o que a carta não automatiza (a tela mostra junto)
    gatilho: Gatilho | None = None   # a rolagem que dispara a carta (etapa 3)

    @classmethod
    def de_json(cls, d: dict) -> UsoDeCarta:
        q = d.get("quantidade") or {}
        recarga = d.get("recarga") or {}
        opcoes = tuple(OpcaoDeUso(
            o["id"], o["rotulo"], Custo.de_json(o.get("custo")), Custo.de_json(o.get("por_unidade")),
            tuple(EfeitoDeCarta.de_json(e) for e in o.get("efeitos", ())), o.get("alvo"), o.get("limite"),
            o.get("quantidade", True), o.get("teste", "")) for o in d.get("opcoes", ()))
        uso = cls(custo=Custo.de_json(d.get("custo")), por_unidade=Custo.de_json(d.get("por_unidade")),
                  quantidade_max=q.get("max"), quantidade_min=q.get("min", 1), quantidade_rotulo=q.get("rotulo", ""),
                  limite=d.get("limite"), alvo=d.get("alvo", "si"), condicao=d.get("condicao"),
                  teste=d.get("teste", ""), opcoes=opcoes,
                  efeitos=tuple(EfeitoDeCarta.de_json(e) for e in d.get("efeitos", ())),
                  recarga=recarga.get("q"), recarga_quando=recarga.get("quando", "descanso_longo"),
                  nota=d.get("nota", ""), gatilho=Gatilho.de_json(d.get("gatilho")))
        validos = all(x in (None, *LIMITES) for x in (uso.limite, *(o.limite for o in opcoes)))
        if not validos or any(x not in ALVOS for x in (uso.alvo, *(o.alvo for o in opcoes if o.alvo))):
            raise ValueError(f"uso de carta inválido: {d}")
        return uso


def quanto(expr: str | int, valores: dict[str, int], rng, maximo: int = 0) -> int:
    """Valor de uma quantidade do catálogo (ver o topo do módulo)."""
    if isinstance(expr, int):
        return expr
    expr = expandir(expr, valores).strip()
    if expr == "tudo":
        return maximo
    if m := _DADO.fullmatch(expr):
        return sum(rng.randint(1, int(m.group(2))) for _ in range(int(m.group(1)))) + int(m.group(3) or 0)
    for prefixo, f in (("min1:", lambda v: max(1, v)), ("metade:", metade)):
        if expr.startswith(prefixo):
            return f(quanto(expr[len(prefixo):], valores, rng, maximo))
    if "+" in expr:
        a, b = expr.rsplit("+", 1)
        return quanto(a, valores, rng, maximo) + quanto(b, valores, rng, maximo)
    if "-" in expr:
        a, b = expr.rsplit("-", 1)
        return quanto(a, valores, rng, maximo) - quanto(b, valores, rng, maximo)
    return resolver(expr, valores)


def ler_catalogo(dados: dict) -> dict[str, UsoDeCarta]:
    return {carta: UsoDeCarta.de_json(d) for carta, d in dados["usos"].items()}


@dataclass
class ResultadoDeUso:
    notas: list[str] = field(default_factory=list)
    teste: str = ""   # o que rolar agora (se a carta pede)
    medo: int = 0     # Medo tirado do mestre (a API aplica na sessão)
    rolagem: object = None   # a versão nova da rolagem, se a carta mudou a que a disparou


__all__ = ["Custo", "EfeitoDeCarta", "Gatilho", "OpcaoDeUso", "ResultadoDeUso", "UsoDeCarta", "ler_catalogo", "quanto"]
