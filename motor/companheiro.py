"""Companheiro animal do Ranger Beastbound.

O companheiro tem ficha própria (Evasão, Estresse, dano, Experiências) e
evolui junto com o personagem: a cada nível o jogador escolhe uma opção de
treino (Training) da ficha do companheiro. Por isso os treinos fazem parte do
histórico (`SubidaDeNivel.treinos`), e a ficha do companheiro é recalculada
no replay, como a do personagem.

Os números da ficha do companheiro ficam em `data/companheiro.json`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .erros import RegraViolada
from .srd import TipoDano


class OpcaoTreino(str, Enum):
    """Opções de Training da ficha do companheiro (nome no SRD ao lado)."""

    INTELIGENTE = "INTELIGENTE"            # Intelligent: +1 numa Experiência do companheiro
    LUZ_NA_ESCURIDAO = "LUZ_NA_ESCURIDAO"  # Light in the Dark: +1 espaço de Esperança (do personagem)
    CONFORTO = "CONFORTO"                  # Creature Comfort: 1x por descanso, Esperança ou limpar Estresse
    BLINDADO = "BLINDADO"                  # Armored: marcar espaço de armadura no lugar do Estresse dele
    FEROZ = "FEROZ"                        # Vicious: dado de dano ou alcance sobe um passo
    RESILIENTE = "RESILIENTE"              # Resilient: +1 espaço de Estresse
    VINCULO = "VINCULO"                    # Bonded: ao marcar seu último PV, ele pode te levantar
    ATENTO = "ATENTO"                      # Aware: +2 Evasão

    @property
    def rotulo(self) -> str:
        return {"INTELIGENTE": "Inteligente", "LUZ_NA_ESCURIDAO": "Luz na Escuridão",
                "CONFORTO": "Conforto Animal", "BLINDADO": "Blindado", "FEROZ": "Feroz",
                "RESILIENTE": "Resiliente", "VINCULO": "Vínculo", "ATENTO": "Atento"}[self.value]


class AlvoFeroz(str, Enum):
    DANO = "DANO"
    ALCANCE = "ALCANCE"

    @property
    def rotulo(self) -> str:
        return "dano" if self is AlvoFeroz.DANO else "alcance"


# --- Entradas -------------------------------------------------------------------

@dataclass
class Companheiro:
    """O que o jogador define ao ganhar o companheiro (criação ou multiclasse)."""

    nome: str
    experiencias: list[str]
    tipo_dano: TipoDano = TipoDano.FISICO   # errata de set/2025: físico ou mágico


@dataclass
class Treino:
    opcao: OpcaoTreino
    experiencia: str | None = None        # INTELIGENTE
    alvo: AlvoFeroz | None = None         # FEROZ


# --- Saída ------------------------------------------------------------------------

@dataclass
class FichaCompanheiro:
    nome: str
    evasao: int
    estresse_max: int
    dado: str
    alcance: str
    tipo_dano: TipoDano
    experiencias: dict[str, int]
    treinos: dict[OpcaoTreino, int] = field(default_factory=dict)   # quadradinhos marcados
    dano: str = ""                   # preenchido na ficha final: Proficiência + dado
    estresse_marcado: int = 0        # estado de sessão
    fora_de_cena: bool = False       # marcou o último Estresse

    def tem(self, opcao: OpcaoTreino) -> bool:
        return self.treinos.get(opcao, 0) > 0


def criar_companheiro(regras: dict, c: Companheiro) -> FichaCompanheiro:
    nomes = [e.strip() for e in c.experiencias]
    if not c.nome.strip():
        raise RegraViolada("Dê um nome ao companheiro.")
    n = regras["experiencias_iniciais"]
    if len(nomes) != n or "" in nomes or len(set(nomes)) != n:
        raise RegraViolada(f"Escolha {n} Experiências diferentes para o companheiro.")
    return FichaCompanheiro(
        nome=c.nome.strip(), evasao=regras["evasao_inicial"],
        estresse_max=regras["estresse_inicial"], dado=regras["dados"][0],
        alcance=regras["alcances"][0], tipo_dano=TipoDano(c.tipo_dano),
        experiencias={e: regras["valor_experiencia"] for e in nomes},
    )


def nova_experiencia(regras: dict, comp: FichaCompanheiro, nome: str | None):
    """Quando o personagem ganha uma Experiência, o companheiro também ganha."""
    nome = (nome or "").strip()
    if not nome:
        raise RegraViolada("Seu companheiro também ganha uma nova Experiência neste nível.")
    if nome in comp.experiencias:
        raise RegraViolada(f"O companheiro já tem a Experiência '{nome}'.")
    comp.experiencias[nome] = regras["valor_experiencia"]


def aplicar_treino(regras: dict, comp: FichaCompanheiro, t: Treino):
    """Valida e aplica um treino. Efeitos no personagem (Luz na Escuridão)
    são lidos da ficha do companheiro por quem precisa deles."""
    limite = regras["treinos"][t.opcao.value]
    if comp.treinos.get(t.opcao, 0) >= limite:
        raise RegraViolada(f"Treino {t.opcao.value} já foi marcado {limite} vez(es).")

    if t.opcao is OpcaoTreino.INTELIGENTE:
        if t.experiencia not in comp.experiencias:
            raise RegraViolada("Escolha uma Experiência que o companheiro tem.")
        comp.experiencias[t.experiencia] += 1
    elif t.opcao is OpcaoTreino.FEROZ:
        if t.alvo is AlvoFeroz.DANO:
            comp.dado = _proximo(regras["dados"], comp.dado, "O dado de dano já é o máximo.")
        elif t.alvo is AlvoFeroz.ALCANCE:
            comp.alcance = _proximo(regras["alcances"], comp.alcance, "O alcance já é o máximo.")
        else:
            raise RegraViolada("Vicious: escolha melhorar o dano ou o alcance.")
    elif t.opcao is OpcaoTreino.RESILIENTE:
        comp.estresse_max += 1
    elif t.opcao is OpcaoTreino.ATENTO:
        comp.evasao += 2
    # LUZ_NA_ESCURIDAO, CONFORTO, BLINDADO e VINCULO só são marcados aqui;
    # o efeito acontece na ficha/sessão do personagem.
    comp.treinos[t.opcao] = comp.treinos.get(t.opcao, 0) + 1


def _proximo(passos: list[str], atual: str, erro: str) -> str:
    i = passos.index(atual)
    if i == len(passos) - 1:
        raise RegraViolada(erro)
    return passos[i + 1]
