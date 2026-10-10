"""Carrega o conteúdo do SRD (arquivos JSON em data/srd) em objetos Python.

O motor de regras nunca lê JSON diretamente: ele pergunta à `Biblioteca`.
Assim, se um dia trocarmos JSON por banco de dados (ou pelo SRD 2.0),
só este arquivo muda.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"


class Traco(str, Enum):
    """Os seis traços de personagem. O valor é a chave usada no SRD."""

    AGILIDADE = "AGILITY"
    FORCA = "STRENGTH"
    ACUIDADE = "FINESSE"
    INSTINTO = "INSTINCT"
    PRESENCA = "PRESENCE"
    CONHECIMENTO = "KNOWLEDGE"


def _texto(valor):
    """O SRD guarda textos como {"en-US": "..."}; pegamos o inglês por enquanto."""
    if isinstance(valor, dict):
        return valor.get("en-US", "")
    return valor


@dataclass(frozen=True)
class Classe:
    id: str
    nome: str
    dominios: tuple[str, str]
    evasao_inicial: int
    pv_iniciais: int


@dataclass(frozen=True)
class Subclasse:
    id: str
    nome: str
    classe: str  # nome da classe em maiúsculas, ex.: "BARD"
    traco_conjuracao: str | None


@dataclass(frozen=True)
class CartaDeDominio:
    id: str
    nome: str
    dominio: str
    nivel: int
    tipo: str
    custo_recall: int


class CategoriaArma(str, Enum):
    PRIMARIA_FISICA = "PRIMARY_PHYSICAL"
    PRIMARIA_MAGICA = "PRIMARY_MAGIC"
    SECUNDARIA = "SECONDARY"


@dataclass(frozen=True)
class Arma:
    id: str
    nome: str
    categoria: CategoriaArma
    tier: int
    traco: Traco
    alcance: str
    dado: str               # ex.: "d8"
    modificador_dano: int
    tipo_dano: str          # PHYSICAL ou MAGICAL
    duas_maos: bool

    @property
    def primaria(self) -> bool:
        return self.categoria is not CategoriaArma.SECUNDARIA

    @property
    def magica(self) -> bool:
        return self.categoria is CategoriaArma.PRIMARIA_MAGICA


@dataclass(frozen=True)
class Armadura:
    id: str
    nome: str
    tier: int
    limiar_maior: int       # valores base; a ficha soma o nível
    limiar_grave: int
    pontuacao: int


@dataclass(frozen=True)
class Ancestralidade:
    id: str
    nome: str


@dataclass(frozen=True)
class Comunidade:
    id: str
    nome: str


class Biblioteca:
    """Todo o conteúdo do SRD, indexado por id."""

    def __init__(self, pasta: Path = PASTA_DADOS):
        srd = pasta / "srd"
        self.classes = {
            c["id"]: Classe(
                id=c["id"],
                nome=c["name"],
                dominios=tuple(c["domains"]),
                evasao_inicial=c["startingEvasion"],
                pv_iniciais=c["startingHitPoints"],
            )
            for c in self._ler(srd / "classes.json")
        }
        self.subclasses = {
            s["id"]: Subclasse(
                id=s["id"],
                nome=_texto(s["name"]),
                classe=s["class"],
                traco_conjuracao=s.get("spellcastTrait"),
            )
            for s in self._ler(srd / "subclasses.json")
        }
        self.cartas = {
            c["id"]: CartaDeDominio(
                id=c["id"],
                nome=_texto(c["name"]),
                dominio=c["domain"],
                nivel=c["level"],
                tipo=c["type"],
                custo_recall=c["recallCost"],
            )
            for c in self._ler(srd / "domain-cards.json")
        }
        self.ancestralidades = {
            a["id"]: Ancestralidade(a["id"], _texto(a["name"]))
            for a in self._ler(srd / "ancestries.json")
        }
        self.comunidades = {
            c["id"]: Comunidade(c["id"], _texto(c["name"]))
            for c in self._ler(srd / "communities.json")
        }
        self.armas = {
            a["id"]: Arma(
                id=a["id"],
                nome=_texto(a["name"]),
                categoria=CategoriaArma(a["type"]),
                tier=a["tier"],
                traco=Traco(a["trait"]),
                alcance=a["range"],
                dado=a["damage"]["dice"].lower(),
                modificador_dano=a["damage"].get("modifier", 0),
                tipo_dano=a["damage"]["type"],
                duas_maos=a["burden"] == "TWO_HANDED",
            )
            for a in self._ler(srd / "weapons.json")
        }
        self.armaduras = {
            a["id"]: Armadura(
                id=a["id"],
                nome=_texto(a["name"]),
                tier=a["tier"],
                limiar_maior=a["baseMajorThreshold"],
                limiar_grave=a["baseSevereThreshold"],
                pontuacao=a["baseScore"],
            )
            for a in self._ler(srd / "armors.json")
        }
        self.progressao = self._ler(pasta / "progressao.json")

    @staticmethod
    def _ler(caminho: Path):
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)

    # --- consultas úteis para o motor e para a interface -------------------

    def subclasses_da_classe(self, classe: Classe) -> list[Subclasse]:
        return [s for s in self.subclasses.values() if s.classe == classe.nome]

    def cartas_disponiveis(self, dominios, nivel_maximo: int) -> list[CartaDeDominio]:
        """Cartas dos domínios informados com nível <= nivel_maximo."""
        return sorted(
            (c for c in self.cartas.values()
             if c.dominio in dominios and c.nivel <= nivel_maximo),
            key=lambda c: (c.nivel, c.dominio, c.nome),
        )

    def tier_do_nivel(self, nivel: int) -> int:
        for tier, info in self.progressao["tiers"].items():
            if nivel in info["niveis"]:
                return int(tier)
        raise ValueError(f"Nível inválido: {nivel}")
