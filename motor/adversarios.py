"""Adversários (inimigos) e o formato da ficha deles.

O mesmo formato serve para os adversários do SRD, para os inimigos que o
mestre cria do zero (ou a partir de um do SRD) e para a ficha de combate de
um NPC. É a ficha de bloco do livro: patamar e tipo, Dificuldade, limiares,
PV, Fadiga (PF), ataque, Experiências e habilidades (passiva, ação, reação).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from .erros import RegraViolada
from .srd import TipoDano


class TipoAdversario(str, Enum):
    """Papel do adversário no combate (nome no SRD ao lado)."""

    SOLO = "SOLO"                    # Solo
    BRUTAMONTES = "BRUTAMONTES"      # Bruiser
    LACAIO = "LACAIO"                # Minion: cai com qualquer dano
    LIDER = "LIDER"                  # Leader
    ESPREITADOR = "ESPREITADOR"      # Skulk
    PADRAO = "PADRAO"                # Standard
    ATIRADOR = "ATIRADOR"            # Ranged
    SOCIAL = "SOCIAL"                # Social
    SUPORTE = "SUPORTE"              # Support
    HORDA = "HORDA"                  # Horde: várias criaturas por PV


class TipoHabilidade(str, Enum):
    PASSIVA = "PASSIVA"
    ACAO = "ACAO"
    REACAO = "REACAO"


ALCANCES = ("MELEE", "VERY_CLOSE", "CLOSE", "FAR", "VERY_FAR")


@dataclass
class Habilidade:
    nome: str                        # ex.: "Relentless (3)"
    tipo: TipoHabilidade
    texto: str                       # pode ter **negrito** e _itálico_
    detalhe: str = ""                # ex.: "Countdown (Loop 1d6)"
    nome_original: str = ""


@dataclass
class Adversario:
    nome: str
    patamar: int                     # 1 a 4 (Tier)
    tipo: TipoAdversario
    dificuldade: int
    pv: int
    pf: int                          # espaços de Fadiga (Stress)
    ataque: str                      # bônus de ataque: "+3", "-1" ou até "+2d4"
    arma: str                        # nome do ataque padrão, ex.: "Garras"
    alcance: str                     # MELEE, VERY_CLOSE, CLOSE, FAR, VERY_FAR
    dano: str                        # "1d12+2" ou fixo, "3"
    tipo_dano: TipoDano
    limiar_maior: int | None = None  # lacaios não têm limiares
    limiar_grave: int | None = None  # alguns só têm o maior
    descricao: str = ""
    motivacoes: str = ""             # motivações e táticas
    experiencias: dict[str, int] = field(default_factory=dict)
    habilidades: list[Habilidade] = field(default_factory=list)
    horda_por_pv: int | None = None  # Horde (3/HP): 3 criaturas por PV
    id: str = ""                     # "srd_acid_burrower" (SRD) ou vazio (criado na mesa)
    base_id: str | None = None       # adversário do SRD em que foi baseado
    nome_original: str = ""
    arma_original: str = ""
    foto: str | None = None          # id da imagem enviada (só exibição; o motor não usa)


_DANO = re.compile(r"(\d+|\d*d\d+([+-]\d+)?)")
_ATAQUE = re.compile(r"[+-](\d+|\d*d\d+)")


def validar(a: Adversario):
    """Regras do formato, para inimigos criados ou editados pelo mestre."""
    if not a.nome.strip():
        raise RegraViolada("Dê um nome ao inimigo.")
    if not 1 <= a.patamar <= 4:
        raise RegraViolada("O patamar vai de 1 a 4.")
    if a.dificuldade < 1 or a.pv < 1 or a.pf < 0:
        raise RegraViolada("Dificuldade e PV precisam ser pelo menos 1, e PF não pode ser negativo.")
    if a.tipo is TipoAdversario.LACAIO:
        if a.limiar_maior is not None or a.limiar_grave is not None:
            raise RegraViolada("Lacaios não têm limiares de dano (caem com qualquer dano).")
    else:
        if a.limiar_maior is None or a.limiar_maior < 1:
            raise RegraViolada("Informe o limiar Maior.")
        if a.limiar_grave is not None and a.limiar_grave <= a.limiar_maior:
            raise RegraViolada("O limiar Grave precisa ser maior que o Maior.")
    if a.alcance not in ALCANCES:
        raise RegraViolada(f"Alcance inválido: {a.alcance}.")
    if not _DANO.fullmatch(a.dano.strip()):
        raise RegraViolada("Dano no formato 1d8+2, 2d6 ou um número fixo.")
    if not _ATAQUE.fullmatch(a.ataque.strip()):
        raise RegraViolada("Ataque no formato +3, -1 (ou +2d4).")
    if a.horda_por_pv is not None and a.tipo is not TipoAdversario.HORDA:
        raise RegraViolada("Só hordas têm criaturas por PV.")
    for h in a.habilidades:
        if not h.nome.strip() or not h.texto.strip():
            raise RegraViolada("Toda habilidade precisa de nome e texto.")


# --- Leitura do SRD (formato do projeto seansbox/daggerheart-srd) ------------------

_TIPOS_SRD = {
    "Solo": TipoAdversario.SOLO, "Bruiser": TipoAdversario.BRUTAMONTES,
    "Minion": TipoAdversario.LACAIO, "Leader": TipoAdversario.LIDER,
    "Skulk": TipoAdversario.ESPREITADOR, "Standard": TipoAdversario.PADRAO,
    "Ranged": TipoAdversario.ATIRADOR, "Social": TipoAdversario.SOCIAL,
    "Support": TipoAdversario.SUPORTE, "Horde": TipoAdversario.HORDA,
}
_HABILIDADE_SRD = re.compile(r"(.*?)\s*-\s*(Passive|Action|Reaction)(?::\s*(.*))?")
_TIPO_HABILIDADE = {"Passive": TipoHabilidade.PASSIVA, "Action": TipoHabilidade.ACAO,
                    "Reaction": TipoHabilidade.REACAO}
_TIPO_DANO_SRD = {"phy": TipoDano.FISICO, "mag": TipoDano.MAGICO, "phy/mag": TipoDano.FISICO_OU_MAGICO}


def id_srd(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return "srd_" + re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def _int_ou_none(texto: str) -> int | None:
    return None if texto in ("None", "", None) else int(texto)


def de_srd(d: dict) -> Adversario:
    tipo_srd = d["type"]
    horda = re.fullmatch(r"Horde \((\d*)/HP\)", tipo_srd)
    tipo = TipoAdversario.HORDA if horda else _TIPOS_SRD[tipo_srd]

    maior = grave = None
    if d["thresholds"] != "None":
        a, b = d["thresholds"].split("/")
        maior, grave = _int_ou_none(a), _int_ou_none(b)

    dano, tipo_dano = d["damage"].rsplit(" ", 1)

    experiencias = {}
    if d.get("experience", "None") not in ("None", ""):
        for parte in d["experience"].split(", "):
            nome, valor = parte.rsplit(" ", 1)
            experiencias[nome] = int(valor)

    habilidades = []
    for f in d["feature"]:
        m = _HABILIDADE_SRD.fullmatch(f["name"])
        habilidades.append(Habilidade(nome=m.group(1), tipo=_TIPO_HABILIDADE[m.group(2)],
                                      texto=f["text"], detalhe=m.group(3) or "",
                                      nome_original=m.group(1)))

    return Adversario(
        id=id_srd(d["name"]), nome=d["name"], nome_original=d["name"], patamar=int(d["tier"]),
        tipo=tipo, horda_por_pv=int(horda.group(1)) if horda and horda.group(1) else None,
        dificuldade=int(d["difficulty"]), limiar_maior=maior, limiar_grave=grave,
        pv=int(d["hp"]), pf=int(d["stress"]), ataque=d["atk"], arma=d["attack"],
        arma_original=d["attack"], alcance=d["range"].upper().replace(" ", "_"),
        dano=dano, tipo_dano=_TIPO_DANO_SRD[tipo_dano], descricao=d.get("description", ""),
        motivacoes=d.get("motives_and_tactics", ""), experiencias=experiencias, habilidades=habilidades,
    )
