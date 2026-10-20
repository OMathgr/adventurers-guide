"""Itens criados pelo mestre: comuns, consumíveis, armas e armaduras.

Seguem o formato dos do SRD e viram objetos do mesmo tipo (`Item`, `Arma`,
`Armadura`), então ficha, equipamento, inventário e lojas os tratam como os
do catálogo. As características também: copiadas do SRD (com bônus, requisito
e efeito) ou criadas com texto e bônus fixos.

Quem recebe guarda uma CÓPIA da definição (`Inventario.proprios`): editar o
modelo na mesa só vale para as próximas entregas, e o item continua valendo se
o personagem sair da mesa ou for copiado para outra. O id da cópia sai do
conteúdo (`id_da_copia`): duas entregas iguais se empilham; uma entrega
depois de editar o modelo vira outro item.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum

from .erros import RegraViolada
from .srd import (Alvo, Arma, Armadura, Caracteristica, CategoriaArma, Efeito, EfeitoConsumivel, Item,
                  Modificador, Referencia, Requisito, TipoDano, TipoDeItem, Traco)

PREFIXO = "proprio_"
ALCANCES = ("MELEE", "VERY_CLOSE", "CLOSE", "FAR", "VERY_FAR")
DADOS = ("d4", "d6", "d8", "d10", "d12", "d20")
# regras de armadura que o motor aplica na sessão (Fortified, Painful...)
EFEITOS_DE_ARMADURA = (Efeito.FORTIFICADA, Efeito.DOLOROSA, Efeito.ESPERANCOSA, Efeito.REFORCADA,
                       Efeito.RESILIENTE, Efeito.IMPENETRAVEL, Efeito.SO_FISICO, Efeito.SO_MAGICO,
                       Efeito.PROTEGIDA, Efeito.CURA)
_QUANTIDADE = re.compile(r"\d+d\d+(?:\+\d+)?|\d+|tudo")
LIMITE_BONUS = 10


class TipoProprio(str, Enum):
    COMUM = "COMUM"            # item reutilizável (só texto)
    CONSUMIVEL = "CONSUMIVEL"  # no máximo 5 de cada; some ao usar
    ARMA = "ARMA"
    ARMADURA = "ARMADURA"


@dataclass
class ItemProprio:
    tipo: TipoProprio
    nome: str
    descricao: str = ""
    tier: int = 1
    # arma
    categoria: CategoriaArma = CategoriaArma.PRIMARIA_FISICA
    traco: Traco = Traco.FORCA
    alcance: str = "MELEE"
    dado: str = "d8"
    modificador_dano: int = 0
    tipo_dano: TipoDano = TipoDano.FISICO
    duas_maos: bool = False
    # armadura (limiares base; a ficha soma o nível)
    limiar_maior: int = 5
    limiar_grave: int = 11
    pontuacao: int = 3
    # consumível: quantidades como nos do SRD ("1d4+1", "2" ou "tudo")
    limpa_pv: str | None = None
    limpa_pf: str | None = None
    ganha_esperanca: str | None = None
    marca_pf: int = 0            # custo: marca Fadiga ao usar
    escolha: bool = False        # limpa PV OU PF (quem usa escolhe)
    # arma e armadura
    caracteristicas: list[Caracteristica] = field(default_factory=list)
    id: str = ""                 # na mesa: id do modelo; no personagem: id_da_copia()

    def __post_init__(self):
        self.tipo = TipoProprio(self.tipo)
        self.categoria = CategoriaArma(self.categoria)
        self.traco = Traco(self.traco)
        self.tipo_dano = TipoDano(self.tipo_dano)
        self.caracteristicas = [c if isinstance(c, Caracteristica) else _caracteristica(c)
                                for c in self.caracteristicas]

    @property
    def tipo_no_inventario(self) -> TipoDeItem | None:
        return {TipoProprio.COMUM: TipoDeItem.COMUM,
                TipoProprio.CONSUMIVEL: TipoDeItem.CONSUMIVEL}.get(self.tipo)

    # --- salvar ----------------------------------------------------------------------

    def estado(self) -> dict:
        """Em tipos simples (JSON), com os enums pelo valor."""
        return json.loads(json.dumps(dataclasses.asdict(self), default=_valor_enum))

    @classmethod
    def de_estado(cls, estado: dict) -> ItemProprio:
        nomes = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in estado.items() if k in nomes})


def _valor_enum(x):
    if isinstance(x, Enum):
        return x.value
    raise TypeError(type(x))


def _caracteristica(d: dict) -> Caracteristica:
    return Caracteristica(
        nome=d.get("nome", ""), descricao=d.get("descricao", ""),
        modificadores=tuple(_modificador(m) for m in d.get("modificadores", ())),
        requisitos=tuple(Requisito(Traco(r["traco"]), int(r["maximo"])) for r in d.get("requisitos", ())),
        efeito=Efeito(d["efeito"]) if d.get("efeito") else None,
        nome_original=d.get("nome_original", ""))


def _modificador(m: dict | Modificador) -> Modificador:
    if isinstance(m, Modificador):
        return m
    return Modificador(_alvo(m["alvo"]), int(m.get("valor", 0)),
                       _referencia(m["igual_a"]) if m.get("igual_a") else None)


def _alvo(valor: str) -> Alvo | Traco:
    try:
        return Alvo(valor)
    except ValueError:
        pass
    try:
        return Traco(valor)
    except ValueError:
        raise RegraViolada(f"Bônus em algo desconhecido: {valor}") from None


def _referencia(valor: str) -> Referencia | Traco:
    try:
        return Referencia(valor)
    except ValueError:
        pass
    try:
        return Traco(valor)
    except ValueError:
        raise RegraViolada(f"Bônus igual a algo desconhecido: {valor}") from None


# --- validação ------------------------------------------------------------------------------

def validar(item: ItemProprio):
    """Confere o item inteiro (do mestre ou de uma loja) antes de salvar ou entregar."""
    item.nome = item.nome.strip()
    item.descricao = item.descricao.strip()
    if not item.nome:
        raise RegraViolada("Dê um nome ao item.")
    if len(item.nome) > 120 or len(item.descricao) > 4000:
        raise RegraViolada("Nome até 120 caracteres e descrição até 4000.")
    if not 1 <= item.tier <= 4:
        raise RegraViolada("O patamar vai de 1 a 4.")
    if item.tipo is TipoProprio.ARMA:
        if item.dado not in DADOS:
            raise RegraViolada(f"Dado de dano: um entre {', '.join(DADOS)}.")
        if item.alcance not in ALCANCES:
            raise RegraViolada("Alcance desconhecido.")
        if not -LIMITE_BONUS <= item.modificador_dano <= 2 * LIMITE_BONUS:
            raise RegraViolada("Bônus de dano fora do razoável (de -10 a +20).")
    if item.tipo is TipoProprio.ARMADURA:
        if not 1 <= item.limiar_maior < item.limiar_grave <= 99:
            raise RegraViolada("Os limiares vão de 1 a 99, e o grave é maior que o maior.")
        if not 0 <= item.pontuacao <= 12:
            raise RegraViolada("A Pontuação de Armadura vai de 0 a 12.")
    if item.tipo is TipoProprio.CONSUMIVEL:
        for nome, q in (("PV", item.limpa_pv), ("PF", item.limpa_pf), ("Esperança", item.ganha_esperanca)):
            if q is not None and not _QUANTIDADE.fullmatch(q):
                raise RegraViolada(f'Quantidade de {nome}: um número, um dado ("1d4+1") ou "tudo".')
        if sum(1 for q in (item.limpa_pv, item.limpa_pf, item.ganha_esperanca) if q and "d" in q) > 1:
            raise RegraViolada("No máximo um dado por consumível (como nos do SRD).")
        if not 0 <= item.marca_pf <= 6:
            raise RegraViolada("A Fadiga marcada ao usar vai de 0 a 6.")
        if item.escolha and not (item.limpa_pv and item.limpa_pf):
            raise RegraViolada("Para escolher entre PV e PF, preencha os dois.")
    else:
        item.limpa_pv = item.limpa_pf = item.ganha_esperanca = None
        item.marca_pf, item.escolha = 0, False
    if item.caracteristicas and item.tipo not in (TipoProprio.ARMA, TipoProprio.ARMADURA):
        raise RegraViolada("Características (com bônus) são só de armas e armaduras; use a descrição.")
    for c in item.caracteristicas:
        _validar_caracteristica(item, c)


def _validar_caracteristica(item: ItemProprio, c: Caracteristica):
    if not c.nome.strip():
        raise RegraViolada("Dê um nome a cada característica.")
    for m in c.modificadores:
        if not -LIMITE_BONUS <= m.valor <= LIMITE_BONUS:
            raise RegraViolada(f"{c.nome}: bônus de -10 a +10.")
        if m.alvo in (Alvo.ATAQUE, Alvo.DANO) and item.tipo is not TipoProprio.ARMA:
            raise RegraViolada(f"{c.nome}: bônus de ataque e dano são só de armas.")
    if c.efeito is not None and (item.tipo is not TipoProprio.ARMADURA or c.efeito not in EFEITOS_DE_ARMADURA):
        raise RegraViolada(f"{c.nome}: essa regra especial é só de armaduras.")


# --- cópia e catálogo -------------------------------------------------------------------------

def id_da_copia(item: ItemProprio) -> str:
    """Id da cópia que o personagem guarda: o mesmo para o mesmo conteúdo."""
    conteudo = {k: v for k, v in item.estado().items() if k != "id"}
    resumo = hashlib.sha1(json.dumps(conteudo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return PREFIXO + resumo[:12]


def copia(item: ItemProprio) -> ItemProprio:
    """A cópia para entregar: validada e com o id do conteúdo."""
    novo = ItemProprio.de_estado(item.estado())
    validar(novo)
    novo.id = id_da_copia(novo)
    return novo


def no_catalogo(item: ItemProprio) -> Item | Arma | Armadura:
    """O item como os do SRD (mesmo id da cópia), para a `Biblioteca` do personagem."""
    carac = tuple(item.caracteristicas)
    if item.tipo is TipoProprio.ARMA:
        return Arma(id=item.id, nome=item.nome, nome_original=item.nome, categoria=item.categoria, tier=item.tier,
                    traco=item.traco, alcance=item.alcance, dado=item.dado, modificador_dano=item.modificador_dano,
                    tipo_dano=item.tipo_dano, duas_maos=item.duas_maos, caracteristicas=carac)
    if item.tipo is TipoProprio.ARMADURA:
        return Armadura(id=item.id, nome=item.nome, nome_original=item.nome, tier=item.tier,
                        limiar_maior=item.limiar_maior, limiar_grave=item.limiar_grave, pontuacao=item.pontuacao,
                        caracteristicas=carac)
    efeito = None
    if item.limpa_pv or item.limpa_pf or item.ganha_esperanca or item.marca_pf:
        efeito = EfeitoConsumivel(limpa_pv=item.limpa_pv, limpa_pf=item.limpa_pf,
                                  ganha_esperanca=item.ganha_esperanca, marca_pf=item.marca_pf, escolha=item.escolha)
    return Item(id=item.id, nome=item.nome, tipo=item.tipo_no_inventario, texto=item.descricao,
                nome_original=item.nome, efeito=efeito)


def separar(proprios: dict[str, dict]) -> dict[str, dict]:
    """As cópias guardadas, já no formato do catálogo: {"armas", "armaduras", "itens"}."""
    grupos: dict[str, dict] = {"armas": {}, "armaduras": {}, "itens": {}}
    for id_, estado in proprios.items():
        objeto = no_catalogo(ItemProprio.de_estado({**estado, "id": id_}))
        grupo = "armas" if isinstance(objeto, Arma) else "armaduras" if isinstance(objeto, Armadura) else "itens"
        grupos[grupo][id_] = objeto
    return grupos
