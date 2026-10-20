"""Inventário: ouro, itens, consumíveis e armas guardadas.

É estado atual (como o equipamento e o cofre), fora do histórico: o que o
personagem carrega muda durante o jogo, não ao subir de nível.

Regras do SRD:
- Ouro em punhados, bolsas e baús: 10 punhados = 1 bolsa, 10 bolsas = 1 baú,
  no máximo 1 baú. Guardamos o total em punhados (até 199 = 1 baú, 9 bolsas e
  9 punhados); gastar "troca" uma bolsa por punhados quando precisa.
- Regra opcional (moedas): 10 moedas = 1 punhado. Ligada pela mesa (ou pelo
  próprio personagem sem mesa); as moedas ficam em `moedas` (0 a 9).
- Consumível: no máximo 5 de cada; some ao usar.
- Relíquia: só uma por vez.
- Até 2 armas de inventário (armadura não vai para o inventário).
"""

from __future__ import annotations

import copy
import dataclasses
import uuid
from dataclasses import dataclass, field

from .erros import RegraViolada
from .srd import Biblioteca, Item, TipoDeItem

PUNHADOS_POR_BOLSA = 10
BOLSAS_POR_BAU = 10
PUNHADOS_POR_BAU = PUNHADOS_POR_BOLSA * BOLSAS_POR_BAU
OURO_MAXIMO = PUNHADOS_POR_BAU + (BOLSAS_POR_BAU - 1) * PUNHADOS_POR_BOLSA + PUNHADOS_POR_BOLSA - 1   # 199
MOEDAS_POR_PUNHADO = 10
LIMITE_CONSUMIVEL = 5
LIMITE_ARMAS = 2


def em_punhados(baus: int = 0, bolsas: int = 0, punhados: int = 0) -> int:
    if min(baus, bolsas, punhados) < 0:
        raise RegraViolada("Ouro não pode ser negativo.")
    return baus * PUNHADOS_POR_BAU + bolsas * PUNHADOS_POR_BOLSA + punhados


def decompor(total: int) -> dict[str, int]:
    """Total em punhados -> {"baus", "bolsas", "punhados"} como na ficha."""
    return {"baus": total // PUNHADOS_POR_BAU,
            "bolsas": total % PUNHADOS_POR_BAU // PUNHADOS_POR_BOLSA,
            "punhados": total % PUNHADOS_POR_BOLSA}


@dataclass
class ItemLivre:
    """Item criado na mesa (aprovado pelo mestre), fora do catálogo do SRD."""

    id: str
    nome: str
    descricao: str = ""
    quantidade: int = 1


@dataclass
class Inventario:
    ouro: int = 0                                          # em punhados
    itens: dict[str, int] = field(default_factory=dict)    # id do catálogo -> quantidade
    livres: list[ItemLivre] = field(default_factory=list)
    armas: list[str] = field(default_factory=list)         # armas de inventário (ids)
    # Honing Relic: +1 numa Experiência à escolha
    experiencia_da_reliquia: str | None = None
    # regra opcional das moedas: 0 a 9 (a 10ª vira 1 punhado)
    moedas: int = 0
    # o próprio personagem liga as moedas quando está sem mesa (na mesa, vale a da mesa)
    usar_moedas: bool = False
    # cópias dos itens criados pelo mestre que o personagem recebeu (id -> definição,
    # motor/itens_proprios.py); os ids aparecem em `itens`, `armas` e no equipamento
    proprios: dict[str, dict] = field(default_factory=dict)

    # --- ouro -----------------------------------------------------------------
    # As contas são feitas em moedas; sem a regra, as moedas ficam em 0.

    def ganhar_ouro(self, punhados: int, moedas: int = 0):
        total = self._em_moedas() + _valor(punhados, moedas)
        if total > OURO_MAXIMO * MOEDAS_POR_PUNHADO + MOEDAS_POR_PUNHADO - 1:
            raise RegraViolada("Não cabe mais ouro: o máximo é 1 baú, 9 bolsas e 9 punhados. "
                               "Gaste ou guarde o ouro em outro lugar.")
        self.ouro, self.moedas = divmod(total, MOEDAS_POR_PUNHADO)

    def gastar_ouro(self, punhados: int, moedas: int = 0):
        custo, tem = _valor(punhados, moedas), self._em_moedas()
        if custo > tem:
            falta, moedas_faltando = divmod(custo - tem, MOEDAS_POR_PUNHADO)
            raise RegraViolada(f"Ouro insuficiente: faltam {descrever_ouro(decompor(falta), moedas_faltando)}.")
        self.ouro, self.moedas = divmod(tem - custo, MOEDAS_POR_PUNHADO)

    def _em_moedas(self) -> int:
        return self.ouro * MOEDAS_POR_PUNHADO + self.moedas

    # --- itens do catálogo -------------------------------------------------------

    def adicionar(self, bib: Biblioteca, item_id: str, quantidade: int = 1):
        item = _item(bib, item_id)
        if quantidade < 1:
            raise RegraViolada("A quantidade precisa ser pelo menos 1.")
        total = self.itens.get(item_id, 0) + quantidade
        if item.tipo is TipoDeItem.CONSUMIVEL and total > LIMITE_CONSUMIVEL:
            raise RegraViolada(f"No máximo {LIMITE_CONSUMIVEL} de cada consumível: "
                               f"já tem {self.itens.get(item_id, 0)} de {item.nome}.")
        if item.reliquia and (outra := self.reliquia(bib)) and outra.id != item_id:
            raise RegraViolada(f"Só dá para carregar uma relíquia; já tem {outra.nome}.")
        if item.reliquia and total > 1:
            raise RegraViolada("Só dá para carregar uma relíquia.")
        self.itens[item_id] = total

    def remover(self, bib: Biblioteca, item_id: str, quantidade: int = 1):
        item = _item(bib, item_id)
        tem = self.itens.get(item_id, 0)
        if quantidade < 1 or quantidade > tem:
            raise RegraViolada(f"Você tem {tem} de {item.nome}.")
        if tem == quantidade:
            del self.itens[item_id]
            if item.reliquia:
                self.experiencia_da_reliquia = None
        else:
            self.itens[item_id] = tem - quantidade

    def reliquia(self, bib: Biblioteca) -> Item | None:
        return next((bib.itens[i] for i in self.itens if i in bib.itens and bib.itens[i].reliquia), None)

    # --- itens livres -----------------------------------------------------------------

    def adicionar_livre(self, nome: str, descricao: str = "", quantidade: int = 1) -> ItemLivre:
        nome = nome.strip()
        if not nome:
            raise RegraViolada("Dê um nome ao item.")
        if quantidade < 1:
            raise RegraViolada("A quantidade precisa ser pelo menos 1.")
        novo = ItemLivre(uuid.uuid4().hex[:12], nome, descricao.strip(), quantidade)
        self.livres.append(novo)
        return novo

    def remover_livre(self, livre_id: str, quantidade: int = 1):
        item = next((x for x in self.livres if x.id == livre_id), None)
        if item is None:
            raise RegraViolada("Item não encontrado no inventário.")
        if quantidade < 1 or quantidade > item.quantidade:
            raise RegraViolada(f"Você tem {item.quantidade} de {item.nome}.")
        item.quantidade -= quantidade
        if item.quantidade == 0:
            self.livres.remove(item)

    # --- armas de inventário ------------------------------------------------------------

    def guardar_arma(self, bib: Biblioteca, arma_id: str):
        if arma_id not in bib.armas:
            raise RegraViolada(f"Arma desconhecida: {arma_id}")
        if len(self.armas) >= LIMITE_ARMAS:
            raise RegraViolada(f"Só cabem {LIMITE_ARMAS} armas no inventário.")
        self.armas.append(arma_id)

    def descartar_arma(self, indice: int):
        if not 0 <= indice < len(self.armas):
            raise RegraViolada("Não há arma nessa posição do inventário.")
        del self.armas[indice]

    # --- salvar --------------------------------------------------------------------------

    def estado(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def de_estado(cls, estado: dict | None) -> Inventario:
        # cópia profunda: o dict pode ser o JSON do banco, que não pode mudar por baixo
        estado = copy.deepcopy(estado or {})
        estado["livres"] = [ItemLivre(**x) for x in estado.get("livres", [])]
        return cls(**estado)


def inventario_inicial(bib: Biblioteca, classe_id: str, pocao: str, item_de_classe: str) -> Inventario:
    """Itens do passo 5 da criação: tocha, corda, suprimentos, 1 punhado de ouro,
    uma poção (Vida ou Vigor Menor) e um dos itens da classe."""
    iniciais = bib.itens_iniciais
    if pocao not in iniciais["pocoes"]:
        raise RegraViolada("Escolha a Poção de Vida Menor ou a Poção de Vigor Menor.")
    classe = bib.classes.get(classe_id)
    if classe is None:
        raise RegraViolada(f"Classe desconhecida: {classe_id}")
    if item_de_classe not in classe.itens:
        raise RegraViolada(f"Escolha um dos itens da classe {classe.nome}.")
    inv = Inventario(ouro=iniciais["punhados_de_ouro"])
    for item in iniciais["itens"]:
        inv.adicionar(bib, item["id"])
    inv.adicionar(bib, pocao)
    inv.adicionar(bib, item_de_classe)
    return inv


def exigir_moedas(usa_moedas: bool, moedas: int):
    """Moedas só valem com a regra opcional ligada."""
    if moedas and not usa_moedas:
        raise RegraViolada("Esta mesa não usa a regra opcional das moedas.")


def _valor(punhados: int, moedas: int) -> int:
    if punhados < 0 or moedas < 0:
        raise RegraViolada("Ouro não pode ser negativo.")
    return punhados * MOEDAS_POR_PUNHADO + moedas


def descrever_ouro(ouro: dict[str, int], moedas: int = 0) -> str:
    partes = [(ouro["baus"], "baú", "baús"), (ouro["bolsas"], "bolsa", "bolsas"),
              (ouro["punhados"], "punhado", "punhados"), (moedas, "moeda", "moedas")]
    texto = [f"{n} {um if n == 1 else varios}" for n, um, varios in partes if n]
    return ", ".join(texto) or "nada"


def _item(bib: Biblioteca, item_id: str) -> Item:
    item = bib.itens.get(item_id)
    if item is None:
        raise RegraViolada(f"Item desconhecido: {item_id}")
    return item
