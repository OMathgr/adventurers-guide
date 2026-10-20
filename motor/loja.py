"""Loja de uma sessão: itens à venda com preço (em punhados) e estoque opcional.

O mestre monta a loja; ao vender, o ouro sai do personagem e o item entra
nele: itens do catálogo e livres vão para o inventário, armas para as armas
de inventário e armadura é vestida na hora (o SRD não deixa carregar armadura).
Itens criados pelo mestre (PROPRIO) levam a definição junto: quem compra
recebe uma cópia dela (motor/itens_proprios.py).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from .erros import RegraViolada
from .inventario import MOEDAS_POR_PUNHADO, decompor, descrever_ouro, exigir_moedas
from .itens_proprios import ItemProprio, TipoProprio
from .itens_proprios import validar as validar_proprio
from .srd import Biblioteca


class TipoNaLoja(str, Enum):
    ITEM = "ITEM"            # saque ou consumível do SRD
    ARMA = "ARMA"
    ARMADURA = "ARMADURA"
    LIVRE = "LIVRE"          # criado pelo mestre (nome e descrição)
    PROPRIO = "PROPRIO"      # da biblioteca de itens da mesa (arma, armadura, consumível...)


@dataclass
class ItemDaLoja:
    tipo: TipoNaLoja
    preco: int                     # em punhados
    moedas: int = 0                # regra opcional: moedas além dos punhados (0 a 9)
    ref: str | None = None         # id no catálogo (ITEM, ARMA, ARMADURA)
    nome: str = ""                 # só LIVRE
    descricao: str = ""            # só LIVRE
    estoque: int | None = None     # None: sem limite
    id: str = ""
    proprio: dict | None = None    # só PROPRIO: a definição (ItemProprio); `ref` é o modelo na mesa

    def __post_init__(self):
        self.tipo = TipoNaLoja(self.tipo)
        self.id = self.id or uuid.uuid4().hex[:12]


def validar(bib: Biblioteca, itens: list[ItemDaLoja]):
    """Confere a loja inteira antes de salvar."""
    for item in itens:
        if item.preco < 0 or not 0 <= item.moedas <= 9:
            raise RegraViolada("O preço não pode ser negativo (e as moedas vão de 0 a 9).")
        if item.estoque is not None and item.estoque < 0:
            raise RegraViolada("O estoque não pode ser negativo.")
        catalogo = {TipoNaLoja.ITEM: bib.itens, TipoNaLoja.ARMA: bib.armas,
                    TipoNaLoja.ARMADURA: bib.armaduras}.get(item.tipo)
        if catalogo is not None and item.ref not in catalogo:
            raise RegraViolada(f"Item desconhecido na loja: {item.ref}")
        if item.tipo is TipoNaLoja.LIVRE and not item.nome.strip():
            raise RegraViolada("Dê um nome ao item livre da loja.")
        if item.tipo is TipoNaLoja.PROPRIO:
            if not item.proprio:
                raise RegraViolada("Item da mesa sem definição na loja.")
            definicao = ItemProprio.de_estado(item.proprio)
            validar_proprio(definicao)
            item.proprio = definicao.estado()


def nome(bib: Biblioteca, item: ItemDaLoja) -> str:
    if item.tipo is TipoNaLoja.ITEM:
        return bib.itens[item.ref].nome
    if item.tipo is TipoNaLoja.ARMA:
        return bib.armas[item.ref].nome
    if item.tipo is TipoNaLoja.ARMADURA:
        return bib.armaduras[item.ref].nome
    if item.tipo is TipoNaLoja.PROPRIO:
        return item.proprio["nome"]
    return item.nome


def vender(personagem, item: ItemDaLoja, quantidade: int = 1) -> list[str]:
    """Cobra e entrega. Tudo acontece no personagem em memória: se algo for
    recusado (ouro, espaço, limite de consumível), quem chamou não salva."""
    bib = personagem.bib
    if quantidade < 1:
        raise RegraViolada("A quantidade precisa ser pelo menos 1.")
    if item.estoque is not None and quantidade > item.estoque:
        raise RegraViolada(f"Só há {item.estoque} em estoque.")
    proprio = ItemProprio.de_estado(item.proprio) if item.tipo is TipoNaLoja.PROPRIO else None
    if (item.tipo is TipoNaLoja.ARMADURA or (proprio and proprio.tipo is TipoProprio.ARMADURA)) and quantidade != 1:
        raise RegraViolada("Armadura se compra uma por vez (ela é vestida na hora).")
    inv = personagem.inventario
    exigir_moedas(personagem.usa_moedas, item.moedas)
    total = (item.preco * MOEDAS_POR_PUNHADO + item.moedas) * quantidade   # em moedas
    inv.gastar_ouro(0, total)
    if item.tipo is TipoNaLoja.ITEM:
        inv.adicionar(bib, item.ref, quantidade)
    elif item.tipo is TipoNaLoja.ARMA:
        for _ in range(quantidade):
            inv.guardar_arma(bib, item.ref)
    elif item.tipo is TipoNaLoja.ARMADURA:
        personagem.vestir_armadura_nova(item.ref)
    elif proprio is not None:
        personagem.receber_item_proprio(proprio, quantidade)
    else:
        inv.adicionar_livre(item.nome, item.descricao, quantidade)
    if item.estoque is not None:
        item.estoque -= quantidade
    punhados, moedas = divmod(total, MOEDAS_POR_PUNHADO)
    pago = descrever_ouro(decompor(punhados), moedas) if total else "de graça"
    return [f"Comprou {quantidade}× {nome(bib, item)} ({pago})."]
