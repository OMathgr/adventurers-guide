"""Carrega o conteúdo do SRD (arquivos JSON em data/srd) em objetos Python.

O motor de regras nunca lê JSON diretamente: ele pergunta à `Biblioteca`.
Assim, se um dia trocarmos JSON por banco de dados (ou pelo SRD 2.0),
só este arquivo muda.
"""

from __future__ import annotations

import json
import re
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

    @property
    def rotulo(self) -> str:
        """Nome para exibição, com acentos (o nome do membro não pode ter)."""
        return {"FORCA": "Força", "PRESENCA": "Presença"}.get(self.name, self.name.title())


def _texto(valor):
    """O SRD guarda textos como {"en-US": "..."}; pegamos o inglês por enquanto."""
    if isinstance(valor, dict):
        return valor.get("en-US", "")
    return valor


def _paragrafos(descricao: list) -> str:
    return " ".join(_texto(p["paragraph"]) for p in descricao if "paragraph" in p)


class Alvo(str, Enum):
    """O que um modificador fixo de equipamento altera (além dos traços)."""

    EVASAO = "EVASAO"
    PONTUACAO_ARMADURA = "PONTUACAO_ARMADURA"
    LIMIAR_GRAVE = "LIMIAR_GRAVE"
    ATAQUE = "ATAQUE"   # só nas rolagens de ataque da própria arma
    DANO = "DANO"       # só nas rolagens de dano da própria arma
    CONJURACAO = "CONJURACAO"   # rolagens de conjuração


class Referencia(str, Enum):
    """Valores da ficha que um bônus pode copiar (além dos traços)."""

    NIVEL = "NIVEL"


@dataclass(frozen=True)
class Modificador:
    alvo: Alvo | Traco
    valor: int = 0
    # Se preenchido, o bônus é "igual ao seu X" e o valor sai da ficha na hora
    # (ex.: Bonded = nível, Sharpwing = Agilidade); `valor` é ignorado.
    igual_a: Traco | Referencia | None = None


@dataclass(frozen=True)
class Requisito:
    """Condição para poder usar a peça, ex.: Pompous (Presença <= 0)."""

    traco: Traco
    maximo: int


@dataclass(frozen=True)
class Caracteristica:
    nome: str
    descricao: str
    modificadores: tuple[Modificador, ...] = ()   # vazio = só texto
    requisitos: tuple[Requisito, ...] = ()
    efeito: Efeito | None = None                  # regra especial aplicada na sessão


class TipoDano(str, Enum):
    FISICO = "PHYSICAL"
    MAGICO = "MAGICAL"
    FISICO_OU_MAGICO = "PHYSICAL_OR_MAGICAL"   # só em armas (Otherworldly): quem ataca escolhe


class Efeito(str, Enum):
    """Características com regra própria no estado de sessão (dano/descanso).

    Não cabem em "+N to X": mudam COMO o dano, a armadura ou o descanso
    funcionam. O nome no SRD está no comentário.
    """

    FORTIFICADA = "FORTIFICADA"    # Fortified: espaço de armadura reduz 2 níveis
    DOLOROSA = "DOLOROSA"          # Painful (armadura): marcar espaço marca Estresse
    ESPERANCOSA = "ESPERANCOSA"    # Hopeful: pagar Esperança com espaço de armadura
    REFORCADA = "REFORCADA"        # Reinforced: limiares +2 com todos os espaços marcados
    RESILIENTE = "RESILIENTE"      # Resilient: d6 antes do último espaço; 6 = reduz sem marcar
    IMPENETRAVEL = "IMPENETRAVEL"  # Impenetrable: 1x por descanso, Estresse no lugar do último PV
    SO_FISICO = "SO_FISICO"        # Physical: armadura não reduz dano mágico
    SO_MAGICO = "SO_MAGICO"        # Magic: armadura não reduz dano físico
    PROTEGIDA = "PROTEGIDA"        # Warded: dano mágico reduzido pela Pontuação de Armadura
    CURA = "CURA"                  # Healing: limpa 1 PV em todo descanso
    # ancestralidades
    VIGOR = "VIGOR"                # Endurance (Giant): +1 PV na criação
    FOLEGO = "FOLEGO"              # High Stamina (Human): +1 Estresse na criação
    AGIL = "AGIL"                  # Nimble (Simiah): +1 Evasão na criação
    PROPOSITO = "PROPOSITO"        # Purposeful Design (Clank): +1 numa Experiência na criação
    CASCO = "CASCO"                # Shell (Galapa): limiares + Proficiência
    EFICIENTE = "EFICIENTE"        # Efficient (Clank): no descanso curto, um movimento de longo
    TRANSE = "TRANSE"              # Celestial Trance (Elf): um movimento de descanso a mais


_EFEITOS_SRD = {
    "Fortified": Efeito.FORTIFICADA,
    "Painful": Efeito.DOLOROSA,
    "Hopeful": Efeito.ESPERANCOSA,
    "Reinforced": Efeito.REFORCADA,
    "Resilient": Efeito.RESILIENTE,
    "Impenetrable": Efeito.IMPENETRAVEL,
    "Physical": Efeito.SO_FISICO,
    "Magic": Efeito.SO_MAGICO,
    "Warded": Efeito.PROTEGIDA,
    "Healing": Efeito.CURA,
    "Endurance": Efeito.VIGOR,
    "High Stamina": Efeito.FOLEGO,
    "Nimble": Efeito.AGIL,
    "Purposeful Design": Efeito.PROPOSITO,
    "Shell": Efeito.CASCO,
    "Efficient": Efeito.EFICIENTE,
    "Celestial Trance": Efeito.TRANSE,
}


def _efeito(nome: str, descricao: str) -> Efeito | None:
    efeito = _EFEITOS_SRD.get(nome)
    # Painful tem duas versões: a de arma ("successful attack") depende de
    # ataque, que o motor não modela; só a de armadura vira regra.
    if efeito is Efeito.DOLOROSA and "Armor Slot" not in descricao:
        return None
    return efeito


# Como o SRD escreve cada alvo em "+N to <alvo>". Alvos fora desta tabela
# (ex.: "primary weapon damage within Melee range") são condicionais e ficam
# só como texto na ficha.
TRACOS_SRD = {t.value.title(): t for t in Traco}   # "Agility" -> Traco.AGILIDADE
ALVOS_SRD: dict[str, tuple[Alvo | Traco, ...]] = {
    "Evasion": (Alvo.EVASAO,),
    "Armor Score": (Alvo.PONTUACAO_ARMADURA,),
    "Severe damage threshold": (Alvo.LIMIAR_GRAVE,),
    "attack rolls": (Alvo.ATAQUE,),
    "Spellcast Rolls": (Alvo.CONJURACAO,),
    "all character traits": tuple(Traco),
    "all character traits and Evasion": (*Traco, Alvo.EVASAO),
    **{nome: (t,) for nome, t in TRACOS_SRD.items()},
}
REFERENCIAS_SRD: dict[str, Traco | Referencia] = {"level": Referencia.NIVEL, **TRACOS_SRD}

_BONUS_FIXO = re.compile(r"\s*([+-]\d+) to (.+?)\.?\s*")
_BONUS_DANO_IGUAL = re.compile(r"\s*Gain a bonus to your damage rolls equal to your (\w+)\.?\s*")
_REQUISITO_MAXIMO = re.compile(
    r"\s*You must have an? (\w+) of ([+-]?\d+) or lower to use this weapon\.?\s*")


def _modificadores(texto: str) -> tuple[Modificador, ...]:
    """Extrai os bônus fixos de um texto como "-2 to Evasion; -1 to Agility".

    Cada trecho separado por ";" é analisado sozinho, então em
    "-1 to Agility; on a successful attack..." só a primeira parte vira número.
    """
    mods = []
    for trecho in texto.split(";"):
        if m := _BONUS_FIXO.fullmatch(trecho):
            if m.group(2) in ALVOS_SRD:
                mods += [Modificador(alvo, int(m.group(1))) for alvo in ALVOS_SRD[m.group(2)]]
        elif m := _BONUS_DANO_IGUAL.fullmatch(trecho):
            if m.group(1) in REFERENCIAS_SRD:
                mods.append(Modificador(Alvo.DANO, igual_a=REFERENCIAS_SRD[m.group(1)]))
    return tuple(mods)


def _requisitos(texto: str) -> tuple[Requisito, ...]:
    m = _REQUISITO_MAXIMO.fullmatch(texto)
    if m and m.group(1) in TRACOS_SRD:
        return (Requisito(TRACOS_SRD[m.group(1)], int(m.group(2))),)
    return ()


def _caracteristicas(item: dict) -> tuple[Caracteristica, ...]:
    resultado = []
    for c in item.get("features", []):
        descricao = _paragrafos(c["description"])
        nome = _texto(c["name"])
        resultado.append(Caracteristica(nome, descricao, _modificadores(descricao),
                                        _requisitos(descricao), _efeito(nome, descricao)))
    return tuple(resultado)


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
    traco_conjuracao: Traco | None   # None = subclasse não conjura


@dataclass(frozen=True)
class CartaDeDominio:
    id: str
    nome: str
    dominio: str
    nivel: int
    tipo: str
    custo_recall: int
    texto: str = ""   # o que a carta faz (só para exibição)


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
    tipo_dano: TipoDano
    duas_maos: bool
    caracteristicas: tuple[Caracteristica, ...] = ()

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
    caracteristicas: tuple[Caracteristica, ...] = ()


@dataclass(frozen=True)
class Ancestralidade:
    id: str
    nome: str
    # Sempre duas, na ordem do SRD. A ordem importa na ancestralidade mista:
    # pega-se a primeira de uma e a segunda de outra.
    caracteristicas: tuple[Caracteristica, ...] = ()


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
                traco_conjuracao=Traco(s["spellcastTrait"]) if s.get("spellcastTrait") else None,
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
                texto="\n\n".join(_paragrafos(f["description"]) for f in c.get("features", [])),
            )
            for c in self._ler(srd / "domain-cards.json")
        }
        self.ancestralidades = {
            a["id"]: Ancestralidade(a["id"], _texto(a["name"]), _caracteristicas(a))
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
                tipo_dano=TipoDano(a["damage"]["type"]),
                duas_maos=a["burden"] == "TWO_HANDED",
                caracteristicas=_caracteristicas(a),
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
                caracteristicas=_caracteristicas(a),
            )
            for a in self._ler(srd / "armors.json")
        }
        self.progressao = self._ler(pasta / "progressao.json")
        self.companheiro = self._ler(pasta / "companheiro.json")   # ficha do Ranger Companion

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
