"""Estado de sessão: o que muda durante o jogo (PV, Estresse, Esperança,
espaços de armadura) e as regras de dano e descanso.

Fica fora do histórico, como o equipamento e o cofre: é o estado ATUAL do
personagem. Os máximos (PV, Estresse, limiares, Pontuação de Armadura) vêm
sempre da ficha calculada, então subir de nível ou trocar de armadura já
reflete aqui.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .erros import RegraViolada

if TYPE_CHECKING:
    from .personagem import Personagem


class Gravidade(int, Enum):
    """Quantos PV um dano marca, pela comparação com os limiares."""

    NENHUM = 0
    MENOR = 1      # abaixo do limiar maior
    MAIOR = 2      # a partir do limiar maior
    GRAVE = 3      # a partir do limiar grave
    MASSIVO = 4    # regra opcional: a partir do dobro do limiar grave


class Movimento(str, Enum):
    """Movimentos de descanso (downtime). Cada descanso permite dois."""

    CUIDAR_FERIDAS = "CUIDAR_FERIDAS"        # Tend to Wounds: limpa PV
    ALIVIAR_ESTRESSE = "ALIVIAR_ESTRESSE"    # Clear Stress
    REPARAR_ARMADURA = "REPARAR_ARMADURA"    # Repair Armor
    PREPARAR = "PREPARAR"                    # Prepare: +1 Esperança
    PREPARAR_EM_GRUPO = "PREPARAR_EM_GRUPO"  # Prepare com o grupo: +2 Esperança
    PROJETO = "PROJETO"                      # Work on a Project (só no longo; narrativo)


# No descanso curto estes rolam 1d4 + tier; no longo recuperam tudo.
_RECUPERACAO = {
    Movimento.CUIDAR_FERIDAS: "pv_marcados",
    Movimento.ALIVIAR_ESTRESSE: "estresse_marcado",
    Movimento.REPARAR_ARMADURA: "armadura_marcada",
}


@dataclass
class ResultadoDano:
    dano: int
    gravidade: Gravidade         # antes da armadura
    pv_marcados: int             # depois da armadura
    usou_armadura: bool
    caiu: bool                   # marcou o último PV: hora do movimento de morte


@dataclass
class ResultadoMovimento:
    movimento: Movimento
    rolagem: int | None          # d4 rolado (só no descanso curto)
    recuperado: int              # PV/Estresse/armadura limpos ou Esperança ganha


class Sessao:
    def __init__(self, personagem: Personagem, esperanca: int,
                 rng: random.Random | None = None):
        self.personagem = personagem
        self.pv_marcados = 0
        self.estresse_marcado = 0
        self.esperanca = esperanca
        self.armadura_marcada = 0
        self.rng = rng or random.Random()
        # Regra opcional do SRD; no futuro vem da configuração da mesa.
        self.dano_massivo = False

    # --- Dano e PV --------------------------------------------------------------

    def gravidade(self, dano: int) -> Gravidade:
        f = self.personagem.ficha()
        if dano <= 0:
            return Gravidade.NENHUM
        if self.dano_massivo and dano >= 2 * f.limiar_grave:
            return Gravidade.MASSIVO
        if dano >= f.limiar_grave:
            return Gravidade.GRAVE
        if dano >= f.limiar_maior:
            return Gravidade.MAIOR
        return Gravidade.MENOR

    def receber_dano(self, dano: int, usar_armadura: bool = False) -> ResultadoDano:
        """Marca PV conforme os limiares.

        Com `usar_armadura`, marca um espaço de armadura e reduz a gravidade
        em um nível (um espaço por dano). Sem espaço livre, não reduz.
        """
        gravidade = self.gravidade(dano)
        pv = int(gravidade)
        usou = False
        if usar_armadura and pv > 0 and self.armadura_livre > 0:
            self.armadura_marcada += 1
            pv -= 1
            usou = True
        self.marcar_pv(pv)
        return ResultadoDano(dano, gravidade, pv, usou, self.caido)

    def marcar_pv(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.pv_marcados = min(self.pv_marcados + quantidade, self._ficha().pv_max)

    def limpar_pv(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.pv_marcados = max(self.pv_marcados - quantidade, 0)

    @property
    def caido(self) -> bool:
        return self.pv_marcados >= self._ficha().pv_max

    # --- Estresse ----------------------------------------------------------------

    def marcar_estresse(self, quantidade: int = 1):
        """Estresse imposto (ex.: por um adversário).

        Regra do SRD: se precisar marcar Estresse e não houver espaço, marca PV
        no lugar. Para PAGAR um custo com Estresse, use `pagar_estresse`.
        """
        self._exigir_positivo(quantidade)
        cabe = min(quantidade, self.estresse_livre)
        self.estresse_marcado += cabe
        if quantidade > cabe:
            self.marcar_pv(quantidade - cabe)

    def pagar_estresse(self, quantidade: int):
        """Estresse como custo de uma ação: só se houver espaço livre."""
        if quantidade > self.estresse_livre:
            raise RegraViolada(f"Estresse insuficiente: custa {quantidade}, "
                         f"você tem {self.estresse_livre} livre.")
        self.estresse_marcado += quantidade

    def limpar_estresse(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.estresse_marcado = max(self.estresse_marcado - quantidade, 0)

    @property
    def estresse_livre(self) -> int:
        return self._ficha().estresse_max - self.estresse_marcado

    # --- Esperança ---------------------------------------------------------------

    def ganhar_esperanca(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.esperanca = min(self.esperanca + quantidade, self._limite_esperanca)

    def gastar_esperanca(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        if quantidade > self.esperanca:
            raise RegraViolada(f"Esperança insuficiente: custa {quantidade}, você tem {self.esperanca}.")
        self.esperanca -= quantidade

    # --- Armadura ----------------------------------------------------------------

    @property
    def armadura_livre(self) -> int:
        return self._ficha().pontuacao_armadura - self.armadura_marcada

    # --- Descansos -----------------------------------------------------------------

    def descanso_curto(self, movimentos: list[Movimento],
                       rolagens: list[int | None] | None = None) -> list[ResultadoMovimento]:
        """Dois movimentos (pode repetir). Recuperações rolam 1d4 + tier.

        `rolagens` permite informar o d4 de cada movimento (None = o motor rola).
        """
        if Movimento.PROJETO in movimentos:
            raise RegraViolada("Trabalhar num projeto só no descanso longo.")
        return self._descansar(movimentos, rolagens, longo=False)

    def descanso_longo(self, movimentos: list[Movimento]) -> list[ResultadoMovimento]:
        """Dois movimentos (pode repetir). Recuperações limpam tudo."""
        return self._descansar(movimentos, None, longo=True)

    def _descansar(self, movimentos, rolagens, longo: bool) -> list[ResultadoMovimento]:
        if len(movimentos) != 2:
            raise RegraViolada("Escolha dois movimentos de descanso.")
        rolagens = list(rolagens) if rolagens is not None else [None, None]
        if len(rolagens) != len(movimentos):
            raise RegraViolada("Informe uma rolagem (ou None) para cada movimento.")
        for r in rolagens:
            if r is not None and not 1 <= r <= 4:
                raise RegraViolada(f"Rolagem de d4 inválida: {r}.")

        tier = self.personagem.bib.tier_do_nivel(self._ficha().nivel)
        resultados = []
        for movimento, rolagem in zip(movimentos, rolagens):
            if movimento in _RECUPERACAO:
                campo = _RECUPERACAO[movimento]
                marcados = getattr(self, campo)
                if longo:
                    rolagem, quanto = None, marcados
                else:
                    rolagem = rolagem or self.rng.randint(1, 4)
                    quanto = min(rolagem + tier, marcados)
                setattr(self, campo, marcados - quanto)
            elif movimento in (Movimento.PREPARAR, Movimento.PREPARAR_EM_GRUPO):
                antes = self.esperanca
                self.ganhar_esperanca(2 if movimento is Movimento.PREPARAR_EM_GRUPO else 1)
                rolagem, quanto = None, self.esperanca - antes
            else:   # PROJETO: narrativo
                rolagem, quanto = None, 0
            resultados.append(ResultadoMovimento(movimento, rolagem, quanto))
        return resultados

    # --- Ajuste quando os máximos caem ----------------------------------------------

    def ajustar(self):
        """Chamado quando um máximo pode ter diminuído (trocar armadura,
        desfazer nível): nada fica marcado além do máximo."""
        f = self._ficha()
        self.pv_marcados = min(self.pv_marcados, f.pv_max)
        self.estresse_marcado = min(self.estresse_marcado, f.estresse_max)
        self.armadura_marcada = min(self.armadura_marcada, f.pontuacao_armadura)

    # --- utilitários ----------------------------------------------------------------

    def _ficha(self):
        return self.personagem.ficha()

    @property
    def _limite_esperanca(self) -> int:
        return self.personagem.bib.progressao["limite_esperanca"]

    @staticmethod
    def _exigir_positivo(quantidade: int):
        if quantidade < 0:
            raise RegraViolada("Quantidade não pode ser negativa.")

