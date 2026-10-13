"""Sessão de jogo do mestre: encontros com adversários em combate e Medo.

Um encontro guarda uma CÓPIA da ficha de cada adversário (editar o inimigo
na biblioteca depois não muda a luta em andamento) e as marcas de cada
cópia: PV, PF e condições. Várias cópias do mesmo inimigo ganham número
("Lobo 1", "Lobo 2").

Regras (livro, "Dano" e "Adversários Derrotados"):
- dano abaixo do limiar Maior marca 1 PV; Maior ou mais, 2; Grave ou mais, 3;
- resistência reduz o dano à metade (arredondada para cima, convenção do
  projeto) ANTES de comparar com os limiares;
- lacaio é derrotado com qualquer dano;
- marcar o último PV derrota o adversário.

Medo: o mestre tem de 0 a 12 Pontos de Medo, que passam de uma sessão
para a outra.
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field

from .adversarios import Adversario, TipoAdversario
from .erros import RegraViolada
from .numeros import metade
from .sessao import Gravidade, normalizar_condicao

MEDO_MAXIMO = 12
MAX_COPIAS = 20

# O que os jogadores veem da vida de um inimigo (nunca os PV exatos)
VIDA_CHEIA, METADE_DA_VIDA, VIDA_BAIXA, DERROTADO = "vida_cheia", "metade_da_vida", "vida_baixa", "derrotado"


def vitalidade(pv_total: int, pv_marcados: int) -> str:
    """Estado de vitalidade em terços dos PV que restam (decisão do projeto):
    mais de 2/3 restando é vida cheia; mais de 1/3, metade da vida; menos,
    vida baixa; nenhum, derrotado. Ex.: 6 PV → 6-5 cheia, 4-3 metade, 2-1 baixa.
    Conta em inteiros (restam × 3 contra o total × 2), sem arredondamento."""
    restam = pv_total - pv_marcados
    if restam <= 0:
        return DERROTADO
    if restam * 3 > pv_total * 2:
        return VIDA_CHEIA
    if restam * 3 > pv_total:
        return METADE_DA_VIDA
    return VIDA_BAIXA


@dataclass
class ResultadoDanoAdversario:
    dano: int               # depois da resistência
    gravidade: Gravidade
    pv_marcados: int        # quantos PV este dano marcou
    derrotado: bool


@dataclass
class Combatente:
    id: str
    rotulo: str                      # nome na luta: "Lobo Sombrio 2"
    adversario: Adversario           # cópia da ficha
    origem: str = ""                 # "inimigo:<id>", "npc:<id>" ou "srd:<id>"
    pv_marcados: int = 0
    pf_marcados: int = 0
    condicoes: list[str] = field(default_factory=list)
    escondido: bool = False          # mesmo com o encontro à mostra, os jogadores não veem este

    @property
    def derrotado(self) -> bool:
        return self.pv_marcados >= self.adversario.pv

    @property
    def vitalidade(self) -> str:
        return vitalidade(self.adversario.pv, self.pv_marcados)

    def gravidade(self, dano: int) -> Gravidade:
        a = self.adversario
        if a.limiar_grave is not None and dano >= a.limiar_grave:
            return Gravidade.GRAVE
        if a.limiar_maior is not None and dano >= a.limiar_maior:
            return Gravidade.MAIOR
        return Gravidade.MENOR

    def receber_dano(self, dano: int, resistente: bool = False) -> ResultadoDanoAdversario:
        if dano < 0:
            raise RegraViolada("O dano não pode ser negativo.")
        if self.derrotado:
            raise RegraViolada(f"{self.rotulo} já foi derrotado.")
        if resistente:
            dano = metade(dano)   # antes de comparar com os limiares; arredonda para cima
        if dano == 0:
            return ResultadoDanoAdversario(0, Gravidade.NENHUM, 0, False)
        if self.adversario.tipo is TipoAdversario.LACAIO:
            marcar = self.adversario.pv - self.pv_marcados          # qualquer dano derrota
            gravidade = Gravidade.MENOR
        else:
            gravidade = self.gravidade(dano)
            marcar = min(int(gravidade), self.adversario.pv - self.pv_marcados)
        self.pv_marcados += marcar
        return ResultadoDanoAdversario(dano, gravidade, marcar, self.derrotado)

    def definir_marcas(self, pv: int, pf: int):
        """Marcas absolutas, como clicar nos quadradinhos da ficha."""
        if not 0 <= pv <= self.adversario.pv:
            raise RegraViolada(f"PV marcados vão de 0 a {self.adversario.pv}.")
        if not 0 <= pf <= self.adversario.pf:
            raise RegraViolada(f"PF marcados vão de 0 a {self.adversario.pf}.")
        self.pv_marcados, self.pf_marcados = pv, pf

    def aplicar_condicao(self, condicao: str) -> str:
        nome = normalizar_condicao(condicao)
        if nome in self.condicoes:
            raise RegraViolada(f"{self.rotulo} já está com a condição {nome}.")
        self.condicoes.append(nome)
        return nome

    def remover_condicao(self, condicao: str):
        nome = normalizar_condicao(condicao)
        if nome not in self.condicoes:
            raise RegraViolada(f"{self.rotulo} não está com a condição {nome}.")
        self.condicoes.remove(nome)


@dataclass
class Encontro:
    nome: str
    combatentes: list[Combatente] = field(default_factory=list)

    def adicionar(self, adversario: Adversario, quantidade: int = 1, origem: str = "") -> list[Combatente]:
        """Põe `quantidade` cópias na luta. Com mais de uma do mesmo nome, numera
        ("Lobo 1", "Lobo 2"), continuando a contagem das que já estão lá."""
        if not 1 <= quantidade <= MAX_COPIAS:
            raise RegraViolada(f"Adicione de 1 a {MAX_COPIAS} cópias por vez.")
        nome = adversario.nome
        mesmos = [c for c in self.combatentes if c.adversario.nome == nome]
        numerar = quantidade > 1 or mesmos
        if numerar and len(mesmos) == 1 and mesmos[0].rotulo == nome:
            mesmos[0].rotulo = f"{nome} 1"   # o primeiro, que estava sozinho, ganha número
        ultimo = max((self._numero(c.rotulo, nome) for c in mesmos), default=0)
        novos = [Combatente(id=str(uuid.uuid4()),
                            rotulo=f"{nome} {ultimo + i + 1}" if numerar else nome,
                            adversario=copy.deepcopy(adversario), origem=origem)
                 for i in range(quantidade)]
        self.combatentes += novos
        return novos

    def combatente(self, combatente_id: str) -> Combatente:
        for c in self.combatentes:
            if c.id == combatente_id:
                return c
        raise RegraViolada("Esse combatente não está no encontro.")

    def remover(self, combatente_id: str):
        self.combatentes.remove(self.combatente(combatente_id))

    @staticmethod
    def _numero(rotulo: str, nome: str) -> int:
        m = re.fullmatch(re.escape(nome) + r" (\d+)", rotulo)
        return int(m.group(1)) if m else 1


def ajustar_medo(atual: int, delta: int) -> int:
    """Ganhar Medo para no máximo (12); gastar mais do que tem é recusado."""
    if atual + delta < 0:
        raise RegraViolada(f"Medo insuficiente: você tem {atual}.")
    return min(MEDO_MAXIMO, atual + delta)


def definir_medo(valor: int) -> int:
    if not 0 <= valor <= MEDO_MAXIMO:
        raise RegraViolada(f"O Medo vai de 0 a {MEDO_MAXIMO}.")
    return valor
