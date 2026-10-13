"""Carrega o conteúdo do SRD (arquivos JSON em data/srd) em objetos Python.

O motor de regras nunca lê JSON diretamente: ele pergunta à `Biblioteca`.
Assim, se um dia trocarmos JSON por banco de dados (ou pelo SRD 2.0),
só este arquivo muda.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"


class Traco(str, Enum):
    """Os seis atributos de personagem. O valor é a chave usada no SRD."""

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
    """Texto corrido (para ler regras como "+1 to Evasion")."""
    return " ".join(_texto(p["paragraph"]) for p in descricao if "paragraph" in p)


def _texto_completo(descricao: list) -> str:
    """Texto para exibição: parágrafos em linhas e listas com marcador
    (algumas cartas têm listas, ex.: os benefícios da Arcana-Touched)."""
    linhas = []
    for bloco in descricao:
        if "paragraph" in bloco:
            linhas.append(_texto(bloco["paragraph"]))
        for item in bloco.get("list", []):
            linhas.append(f"• {_texto(item)}")
    return "\n".join(linhas)


class Alvo(str, Enum):
    """O que um modificador fixo de equipamento altera (além dos atributos)."""

    EVASAO = "EVASAO"
    PONTUACAO_ARMADURA = "PONTUACAO_ARMADURA"
    LIMIAR_GRAVE = "LIMIAR_GRAVE"
    ATAQUE = "ATAQUE"   # só nas rolagens de ataque da própria arma
    DANO = "DANO"       # só nas rolagens de dano da própria arma
    CONJURACAO = "CONJURACAO"   # rolagens de conjuração


class Referencia(str, Enum):
    """Valores da ficha que um bônus pode copiar (além dos atributos)."""

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
    nome_original: str = ""                       # nome no SRD (inglês)


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
                                        _requisitos(descricao), _efeito(nome, descricao), nome))
    return tuple(resultado)


@dataclass(frozen=True)
class Classe:
    id: str
    codigo: str     # "BARD": é por ele que as subclasses apontam para a classe
    nome: str       # nome de exibição ("Bard", ou traduzido)
    dominios: tuple[str, str]
    evasao_inicial: int
    pv_iniciais: int
    nome_original: str = ""
    itens: tuple[str, ...] = ()   # ids dos itens de classe ("escolha um" na criação)


@dataclass(frozen=True)
class Subclasse:
    id: str
    nome: str
    classe: str  # código da classe, ex.: "BARD" (Classe.codigo)
    traco_conjuracao: Traco | None   # None = subclasse não conjura
    nome_original: str = ""


@dataclass(frozen=True)
class CartaDeDominio:
    id: str
    nome: str
    dominio: str
    nivel: int
    tipo: str
    custo_recall: int
    texto: str = ""   # o que a carta faz (só para exibição)
    nome_original: str = ""


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
    nome_original: str = ""

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
    nome_original: str = ""


@dataclass(frozen=True)
class Ancestralidade:
    id: str
    nome: str
    # Sempre duas, na ordem do SRD. A ordem importa na ancestralidade mista:
    # pega-se a primeira de uma e a segunda de outra.
    caracteristicas: tuple[Caracteristica, ...] = ()
    nome_original: str = ""


@dataclass(frozen=True)
class Comunidade:
    id: str
    nome: str
    nome_original: str = ""


class TipoDeItem(str, Enum):
    SAQUE = "SAQUE"            # Loot: reutilizável
    CONSUMIVEL = "CONSUMIVEL"  # Consumable: some ao usar; no máximo 5 de cada
    COMUM = "COMUM"            # itens iniciais (tocha, corda, suprimentos)
    CLASSE = "CLASSE"          # item de classe ("escolha um" do guia)


@dataclass(frozen=True)
class EfeitoConsumivel:
    """O que um consumível faz na ficha, lido do texto do SRD.

    Cada quantidade é um dado ("1d4+1"), um número ou "tudo". Com `escolha`,
    só um entre PV e PF é limpo (Sweet Moss: "1d4 HP or 1d4 Stress").
    """

    limpa_pv: str | None = None
    limpa_pf: str | None = None
    ganha_esperanca: str | None = None
    marca_pf: int = 0
    escolha: bool = False

    @property
    def dado(self) -> str | None:
        """O dado a rolar ao usar (no SRD, nunca mais de um por consumível)."""
        return next((q for q in (self.limpa_pv, self.limpa_pf, self.ganha_esperanca)
                     if q and re.fullmatch(r"\d+d\d+(?:\+\d+)?", q)), None)


@dataclass(frozen=True)
class Item:
    id: str
    nome: str
    tipo: TipoDeItem
    texto: str = ""
    nome_original: str = ""
    rolagem: int | None = None                 # número na tabela do SRD (d60)
    efeito: EfeitoConsumivel | None = None     # só consumíveis com efeito simples
    reliquia: Traco | str | None = None        # relíquia: atributo +1, ou "EXPERIENCIA"


_QUANTIDADE = r"(\d+d\d+(?:\+\d+)?|\d+|a|all)"


def _quantidade(texto: str) -> str:
    return {"a": "1", "all": "tudo"}.get(texto.lower(), texto.lower())


def _efeito_consumivel(texto: str) -> EfeitoConsumivel | None:
    """Efeitos simples de PV, PF e Esperança. O resto é só texto (o jogador narra)."""
    t = texto.strip()
    if m := re.fullmatch(rf"Clear {_QUANTIDADE} (HP|Stress)\.", t):
        q = _quantidade(m.group(1))
        return EfeitoConsumivel(limpa_pv=q) if m.group(2) == "HP" else EfeitoConsumivel(limpa_pf=q)
    if m := re.search(rf"immediately gain {_QUANTIDADE} Hope", t):
        return EfeitoConsumivel(ganha_esperanca=_quantidade(m.group(1)))
    if re.fullmatch(r"Mark a Stress and clear a HP\.", t):
        return EfeitoConsumivel(marca_pf=1, limpa_pv="1")
    if m := re.search(rf"clear {_QUANTIDADE} HP or {_QUANTIDADE} Stress", t):
        return EfeitoConsumivel(limpa_pv=_quantidade(m.group(1)), limpa_pf=_quantidade(m.group(2)), escolha=True)
    if m := re.search(rf"clear all HP and Stress and gain {_QUANTIDADE} Hope", t):
        return EfeitoConsumivel(limpa_pv="tudo", limpa_pf="tudo", ganha_esperanca=_quantidade(m.group(1)))
    if re.search(r"You clear all Stress upon waking", t):
        return EfeitoConsumivel(limpa_pf="tudo")
    return None


def _reliquia(texto: str) -> Traco | str | None:
    if "You can only carry one relic" not in texto:
        return None
    if m := re.search(r"\+1 bonus to your (\w+)\.", texto):
        return Traco(m.group(1).upper())
    return "EXPERIENCIA" if "an Experience of your choice" in texto else None


class Biblioteca:
    """Todo o conteúdo do SRD, indexado por id.

    `idioma` (ex.: "pt-BR") troca nomes e textos de EXIBIÇÃO pela tradução em
    data/traducoes/<idioma>/. As regras continuam lendo o inglês do SRD
    ("+1 to Evasion", "Fortified"...), que é interpretado antes da tradução;
    o nome em inglês fica em `nome_original`.
    """

    def __init__(self, pasta: Path = PASTA_DADOS, idioma: str | None = None):
        srd = pasta / "srd"
        self.idioma = idioma
        self.classes = {
            c["id"]: Classe(
                id=c["id"],
                codigo=c["name"],
                nome=c["name"].title(),
                nome_original=c["name"].title(),
                dominios=tuple(c["domains"]),
                evasao_inicial=c["startingEvasion"],
                pv_iniciais=c["startingHitPoints"],
                itens=tuple(f"{c['id']}_item_{n}" for n in range(1, len(c.get("classItems", [])) + 1)),
            )
            for c in self._ler(srd / "classes.json")
        }
        self.itens: dict[str, Item] = {}
        for c in self._ler(srd / "classes.json"):
            for n, item in enumerate(c.get("classItems", []), 1):
                nome = _texto(item)
                self.itens[f"{c['id']}_item_{n}"] = Item(f"{c['id']}_item_{n}", nome, TipoDeItem.CLASSE,
                                                         nome_original=nome)
        self.itens_iniciais = self._ler(pasta / "itens_iniciais.json")
        for item in self.itens_iniciais["itens"]:
            self.itens[item["id"]] = Item(item["id"], item["name"], TipoDeItem.COMUM, nome_original=item["name"])
        for arquivo, tipo in (("loot.json", TipoDeItem.SAQUE), ("consumables.json", TipoDeItem.CONSUMIVEL)):
            for item in self._ler(srd / arquivo):
                self.itens[item["id"]] = Item(
                    id=item["id"], nome=item["name"], tipo=tipo, texto=item["description"],
                    nome_original=item["name"], rolagem=item["roll"],
                    efeito=_efeito_consumivel(item["description"]) if tipo is TipoDeItem.CONSUMIVEL else None,
                    reliquia=_reliquia(item["description"]))
        self.subclasses = {
            s["id"]: Subclasse(
                id=s["id"],
                nome=_texto(s["name"]),
                nome_original=_texto(s["name"]),
                classe=s["class"],
                traco_conjuracao=Traco(s["spellcastTrait"]) if s.get("spellcastTrait") else None,
            )
            for s in self._ler(srd / "subclasses.json")
        }
        self.cartas = {
            c["id"]: CartaDeDominio(
                id=c["id"],
                nome=_texto(c["name"]),
                nome_original=_texto(c["name"]),
                dominio=c["domain"],
                nivel=c["level"],
                tipo=c["type"],
                custo_recall=c["recallCost"],
                # grimórios têm várias magias, cada uma com nome: "Power Push: ..."
                texto="\n\n".join((f"{_texto(f['name'])}: " if "name" in f else "")
                                  + _texto_completo(f["description"]) for f in c.get("features", [])),
            )
            for c in self._ler(srd / "domain-cards.json")
        }
        self.ancestralidades = {
            a["id"]: Ancestralidade(a["id"], _texto(a["name"]), _caracteristicas(a), _texto(a["name"]))
            for a in self._ler(srd / "ancestries.json")
        }
        self.comunidades = {
            c["id"]: Comunidade(c["id"], _texto(c["name"]), _texto(c["name"]))
            for c in self._ler(srd / "communities.json")
        }
        self.armas = {
            a["id"]: Arma(
                id=a["id"],
                nome=_texto(a["name"]),
                nome_original=_texto(a["name"]),
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
                nome_original=_texto(a["name"]),
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
        from .adversarios import de_srd   # aqui para evitar import circular (adversarios usa TipoDano)
        self.adversarios = {a.id: a for a in map(de_srd, self._ler(srd / "adversarios.json"))}
        self._dominios: dict[str, str] = {}
        # o que não achou tradução (o teste de traduções exige que fique vazio)
        self.traducoes_faltando: list[str] = []
        if idioma:
            self._traduzir(pasta / "traducoes" / idioma)

    # --- tradução (só exibição) ----------------------------------------------

    def _traduzir(self, pasta: Path):
        herancas = self._ler(pasta / "herancas.json")
        itens = self._ler(pasta / "itens.json")
        carac = self._ler(pasta / "caracteristicas.json")
        equip = self._ler(pasta / "equipamento.json")
        cartas: dict = {}
        for arquivo in sorted((pasta / "cartas").glob("*.json")):
            cartas.update(self._ler(arquivo))
        self._dominios = herancas["dominios"]
        faltando = self.traducoes_faltando

        def nome_de(tabela: dict, id_: str, atual: str) -> str:
            if id_ not in tabela:
                faltando.append(id_)
                return atual
            return tabela[id_]

        def traduzir_carac(c: Caracteristica, nova: dict | None = None) -> Caracteristica:
            nome = nova["nome"] if nova else carac["nomes"].get(c.nome_original)
            descricao = nova["descricao"] if nova else carac["descricoes"].get(c.descricao)
            if nome is None or descricao is None:
                faltando.append(f"característica: {c.nome_original}")
                return c
            return dataclasses.replace(c, nome=nome, descricao=descricao)

        def nome_equipamento(tabela: dict, prefixo: str, id_: str, atual: str) -> str:
            if id_ in tabela:
                return tabela[id_]["nome"]
            # "core_weapon_improved_broadsword" = base "core_weapon_broadsword" + qualidade
            for qualidade, formas in equip["qualidades"].items():
                base = id_.replace(f"{prefixo}{qualidade}_", prefixo, 1)
                if base != id_ and base in tabela:
                    return f"{tabela[base]['nome']} {formas[tabela[base]['genero']]}"
            faltando.append(id_)
            return atual

        def ancestralidade(i: str, a: Ancestralidade) -> Ancestralidade:
            nova = herancas["ancestralidades"].get(i)
            if nova is None:
                faltando.append(i)
                return a
            return dataclasses.replace(a, nome=nova["nome"], caracteristicas=tuple(
                traduzir_carac(c, n) for c, n in zip(a.caracteristicas, nova["caracteristicas"])))

        def carta(i: str, c: CartaDeDominio) -> CartaDeDominio:
            if i not in cartas:
                faltando.append(i)
                return c
            return dataclasses.replace(c, nome=cartas[i]["nome"], texto=cartas[i]["texto"])

        self.classes = {i: dataclasses.replace(c, nome=nome_de(herancas["classes"], i, c.nome))
                        for i, c in self.classes.items()}
        self.subclasses = {i: dataclasses.replace(s, nome=nome_de(herancas["subclasses"], i, s.nome))
                           for i, s in self.subclasses.items()}
        self.comunidades = {i: dataclasses.replace(c, nome=nome_de(herancas["comunidades"], i, c.nome))
                            for i, c in self.comunidades.items()}
        self.ancestralidades = {i: ancestralidade(i, a) for i, a in self.ancestralidades.items()}
        self.cartas = {i: carta(i, c) for i, c in self.cartas.items()}
        self.armas = {
            i: dataclasses.replace(a, nome=nome_equipamento(equip["armas"], "core_weapon_", i, a.nome),
                                   caracteristicas=tuple(traduzir_carac(c) for c in a.caracteristicas))
            for i, a in self.armas.items()}
        self.armaduras = {
            i: dataclasses.replace(a, nome=nome_equipamento(equip["armaduras"], "core_armor_", i, a.nome),
                                   caracteristicas=tuple(traduzir_carac(c) for c in a.caracteristicas))
            for i, a in self.armaduras.items()}

        def item(i: str, it: Item) -> Item:
            if it.tipo is TipoDeItem.CLASSE:   # traduzidos pelo texto (o id é nosso, não do SRD)
                return dataclasses.replace(it, nome=nome_de(itens["itens_de_classe"], it.nome_original, it.nome))
            if it.tipo is TipoDeItem.COMUM:
                return dataclasses.replace(it, nome=nome_de(itens["iniciais"], i, it.nome))
            novo = itens["saque" if it.tipo is TipoDeItem.SAQUE else "consumiveis"].get(i)
            if novo is None:
                faltando.append(i)
                return it
            return dataclasses.replace(it, nome=novo["nome"], texto=novo["texto"])

        self.itens = {i: item(i, it) for i, it in self.itens.items()}

        adversarios: dict = {}
        for arquivo in sorted((pasta / "adversarios").glob("*.json")):
            adversarios.update(self._ler(arquivo))

        def adversario(i, a):
            t = adversarios.get(i)
            if t is None or len(t["habilidades"]) != len(a.habilidades):
                faltando.append(i)
                return a
            return dataclasses.replace(
                a, nome=t["nome"], descricao=t["descricao"], motivacoes=t["motivacoes"], arma=t["arma"],
                experiencias={t["experiencias"].get(n, n): v for n, v in a.experiencias.items()},
                habilidades=[dataclasses.replace(h, nome=n["nome"], texto=n["texto"],
                                                 detalhe=n.get("detalhe", h.detalhe))
                             for h, n in zip(a.habilidades, t["habilidades"])])

        self.adversarios = {i: adversario(i, a) for i, a in self.adversarios.items()}

    def nome_dominio(self, codigo: str) -> str:
        """Nome de exibição de um domínio ("BLADE" -> "Lâmina" ou "Blade")."""
        return self._dominios.get(codigo, codigo.title())

    @staticmethod
    def _ler(caminho: Path):
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)

    # --- consultas úteis para o motor e para a interface -------------------

    def subclasses_da_classe(self, classe: Classe) -> list[Subclasse]:
        return [s for s in self.subclasses.values() if s.classe == classe.codigo]

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
