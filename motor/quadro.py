"""Quadro (mapa mental) de uma sessão: cartões ligados por setas.

Cartões:
- `nota`: título e texto livre (com **negrito**/_itálico_), com cor;
- `item`: aponta para algo da mesa (NPC, inimigo, encontro, personagem);
- `imagem`: uma imagem enviada (id em /imagens), com legenda opcional.

Tudo é privado do mestre até ele marcar o cartão como `revelado`. O que os
jogadores veem (`so_revelado`) são os cartões revelados e as ligações entre
dois cartões revelados (uma seta que leva a um cartão escondido entregaria
que ele existe). O quadro da campanha junta o revelado de todas as sessões.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .erros import RegraViolada

MAX_CARTOES = 300
MAX_LIGACOES = 600
CORES = ("padrao", "esperanca", "medo", "perigo", "sucesso")


class TipoCartao(str, Enum):
    NOTA = "nota"
    ITEM = "item"
    IMAGEM = "imagem"


class TipoItem(str, Enum):
    NPC = "npc"
    INIMIGO = "inimigo"
    ENCONTRO = "encontro"
    PERSONAGEM = "personagem"


@dataclass
class Cartao:
    id: str
    tipo: TipoCartao
    x: float = 0
    y: float = 0
    titulo: str = ""
    texto: str = ""
    cor: str = "padrao"
    item_tipo: TipoItem | None = None     # só em `item`
    item_id: str | None = None
    imagem: str | None = None             # só em `imagem`
    revelado: bool = False


PONTOS = ("topo", "direita", "baixo", "esquerda")


@dataclass
class Ligacao:
    id: str
    de: str
    para: str
    rotulo: str = ""
    # lado de cada cartão onde a seta encosta (qualquer lado com qualquer lado);
    # None: a tela escolhe
    de_ponto: str | None = None
    para_ponto: str | None = None


@dataclass
class Quadro:
    cartoes: list[Cartao] = field(default_factory=list)
    ligacoes: list[Ligacao] = field(default_factory=list)


def validar(q: Quadro):
    if len(q.cartoes) > MAX_CARTOES:
        raise RegraViolada(f"O quadro comporta até {MAX_CARTOES} cartões.")
    if len(q.ligacoes) > MAX_LIGACOES:
        raise RegraViolada(f"O quadro comporta até {MAX_LIGACOES} ligações.")
    ids = [c.id for c in q.cartoes]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        raise RegraViolada("Cada cartão precisa de um id único.")
    for c in q.cartoes:
        if len(c.titulo) > 120 or len(c.texto) > 4000:
            raise RegraViolada("Título até 120 caracteres e texto até 4000.")
        if c.cor not in CORES:
            raise RegraViolada(f"Cor inválida: {c.cor}.")
        if c.tipo is TipoCartao.ITEM and (c.item_tipo is None or not c.item_id):
            raise RegraViolada("Cartão de item precisa dizer qual item da mesa.")
        if c.tipo is TipoCartao.IMAGEM and not c.imagem:
            raise RegraViolada("Cartão de imagem precisa de uma imagem.")
    existentes = set(ids)
    vistos = set()
    for l in q.ligacoes:
        if not l.id or l.id in vistos:
            raise RegraViolada("Cada ligação precisa de um id único.")
        vistos.add(l.id)
        if l.de not in existentes or l.para not in existentes:
            raise RegraViolada("A ligação aponta para um cartão que não está no quadro.")
        if l.de == l.para:
            raise RegraViolada("Uma ligação liga dois cartões diferentes.")
        if len(l.rotulo) > 120:
            raise RegraViolada("O texto da ligação vai até 120 caracteres.")
        if any(p is not None and p not in PONTOS for p in (l.de_ponto, l.para_ponto)):
            raise RegraViolada("A seta encosta no topo, na direita, embaixo ou na esquerda do cartão.")


def so_revelado(q: Quadro) -> Quadro:
    """O que os jogadores podem ver: cartões revelados e as ligações entre eles."""
    revelados = [c for c in q.cartoes if c.revelado]
    ids = {c.id for c in revelados}
    return Quadro(cartoes=revelados, ligacoes=[l for l in q.ligacoes if l.de in ids and l.para in ids])
