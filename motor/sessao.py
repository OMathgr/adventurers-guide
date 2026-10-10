"""Estado de sessão: o que muda durante o jogo (PV, Estresse, Esperança,
espaços de armadura) e as regras de dano e descanso.

Fica fora do histórico, como o equipamento e o cofre: é o estado ATUAL do
personagem. Os máximos (PV, Estresse, limiares, Pontuação de Armadura) vêm
sempre da ficha calculada, então subir de nível ou trocar de armadura já
reflete aqui.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .erros import RegraViolada
from .srd import Efeito, TipoDano

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
    dano: int                    # depois de reduções (ex.: Warded)
    gravidade: Gravidade         # antes da armadura
    pv_marcados: int             # o que de fato foi marcado
    usou_armadura: bool          # a armadura reduziu a gravidade
    caiu: bool                   # marcou o último PV: hora do movimento de morte
    espacos_marcados: int = 0    # 0 se Resilient evitou marcar
    estresse_marcado: int = 0    # Painful / Impenetrable
    rolagem_d6: int | None = None   # Resilient
    notas: list[str] = field(default_factory=list)   # características que agiram


@dataclass
class ResultadoMovimento:
    movimento: Movimento
    rolagem: int | None          # d4 rolado (só no descanso curto)
    recuperado: int              # PV/Estresse/armadura limpos ou Esperança ganha
    fonte: str | None = None     # característica que gerou (ex.: "Healing")


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
        # Efeitos de "uma vez por descanso" já usados (ex.: Impenetrable)
        self.usados_no_descanso: set[Efeito] = set()

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

    def receber_dano(self, dano: int, usar_armadura: bool = False,
                     tipo: TipoDano | None = None, evitar_queda: bool = False,
                     rolagem_d6: int | None = None) -> ResultadoDano:
        """Marca PV conforme os limiares, aplicando as características equipadas.

        - `usar_armadura`: marca um espaço e reduz a gravidade em um nível
          (dois com Fortified). Sem espaço livre, não reduz.
        - `tipo`: físico ou mágico. Necessário para Warded, Magic e Physical;
          se omitido, essas regras não se aplicam.
        - `evitar_queda`: com Impenetrable (1x por descanso), marca Estresse no
          lugar do último PV.
        - `rolagem_d6`: o d6 do Resilient, se rolado na mesa (senão o motor rola).

        A gravidade é medida antes de marcar o espaço; por isso o +2 do
        Reinforced vale a partir do dano seguinte.
        """
        efeitos = self.personagem.efeitos_ativos()
        f = self._ficha()
        if rolagem_d6 is not None and not 1 <= rolagem_d6 <= 6:
            raise RegraViolada(f"Rolagem de d6 inválida: {rolagem_d6}.")
        if usar_armadura and tipo is TipoDano.MAGICO and Efeito.SO_FISICO in efeitos:
            raise RegraViolada("Sua armadura (Physical) não reduz dano mágico.")
        if usar_armadura and tipo is TipoDano.FISICO and Efeito.SO_MAGICO in efeitos:
            raise RegraViolada("Sua armadura (Magic) não reduz dano físico.")

        notas: list[str] = []
        estresse_antes = self.estresse_marcado
        if tipo is TipoDano.MAGICO and Efeito.PROTEGIDA in efeitos and f.pontuacao_armadura:
            reduzido = min(dano, f.pontuacao_armadura)
            dano -= reduzido
            notas.append(f"Warded: dano mágico reduzido em {reduzido}")

        gravidade = self.gravidade(dano)
        pv = int(gravidade)
        usou = False
        espacos = 0
        d6 = None
        if usar_armadura and pv > 0 and self.armadura_livre > 0:
            usou = True
            if Efeito.RESILIENTE in efeitos and self.armadura_livre == 1:
                d6 = rolagem_d6 or self.rng.randint(1, 6)
                if d6 == 6:
                    notas.append("Resilient: tirou 6 e reduziu sem marcar o último espaço")
            if d6 != 6:
                self._marcar_espaco(efeitos, notas)
                espacos = 1
            reducao = 2 if Efeito.FORTIFICADA in efeitos else 1
            if reducao == 2:
                notas.append("Fortified: reduziu dois níveis")
            pv = max(pv - reducao, 0)

        if (evitar_queda and pv > 0 and Efeito.IMPENETRAVEL in efeitos
                and Efeito.IMPENETRAVEL not in self.usados_no_descanso
                and self.pv_marcados + pv >= self._ficha().pv_max
                and self.estresse_livre > 0):
            pv -= 1
            self.estresse_marcado += 1
            self.usados_no_descanso.add(Efeito.IMPENETRAVEL)
            notas.append("Impenetrable: marcou Estresse no lugar do último PV")

        self.marcar_pv(pv)
        return ResultadoDano(dano, gravidade, pv, usou, self.caido, espacos,
                             self.estresse_marcado - estresse_antes, d6, notas)

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

    def gastar_esperanca(self, quantidade: int = 1, com_armadura: int = 0):
        """Gasta Esperança. Com Hopeful, `com_armadura` dessas Esperanças são
        pagas marcando espaços de armadura no lugar."""
        self._exigir_positivo(quantidade)
        self._exigir_positivo(com_armadura)
        efeitos = self.personagem.efeitos_ativos()
        if com_armadura:
            if Efeito.ESPERANCOSA not in efeitos:
                raise RegraViolada("Só uma armadura com Hopeful troca Esperança por espaço de armadura.")
            if com_armadura > quantidade:
                raise RegraViolada("Não dá para pagar com armadura mais do que o custo.")
            if com_armadura > self.armadura_livre:
                raise RegraViolada(f"Espaços de armadura insuficientes: {self.armadura_livre} livre(s).")
        if quantidade - com_armadura > self.esperanca:
            raise RegraViolada(f"Esperança insuficiente: custa {quantidade - com_armadura}, "
                               f"você tem {self.esperanca}.")
        self.esperanca -= quantidade - com_armadura
        for _ in range(com_armadura):
            self._marcar_espaco(efeitos, [])

    # --- Armadura ----------------------------------------------------------------

    @property
    def armadura_livre(self) -> int:
        return self._ficha().pontuacao_armadura - self.armadura_marcada

    def marcar_armadura(self, quantidade: int = 1) -> list[str]:
        """Marca espaços de armadura por uma característica ativada na mesa
        (ex.: Shifting, Timeslowing, Deflecting). Devolve as notas (ex.: Painful)."""
        self._exigir_positivo(quantidade)
        if quantidade > self.armadura_livre:
            raise RegraViolada(f"Espaços de armadura insuficientes: {self.armadura_livre} livre(s).")
        efeitos, notas = self.personagem.efeitos_ativos(), []
        for _ in range(quantidade):
            self._marcar_espaco(efeitos, notas)
        return notas

    def _marcar_espaco(self, efeitos: set[Efeito], notas: list[str]):
        """Todo espaço marcado passa por aqui, para o Painful valer sempre."""
        self.armadura_marcada += 1
        if Efeito.DOLOROSA in efeitos:
            self.marcar_estresse(1)   # "must mark": imposto, transborda para PV
            notas.append("Painful: marcou 1 Estresse")

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

        # Healing: "during downtime, automatically clear a Hit Point"
        if Efeito.CURA in self.personagem.efeitos_ativos():
            curado = min(1, self.pv_marcados)
            self.pv_marcados -= curado
            resultados.append(ResultadoMovimento(Movimento.CUIDAR_FERIDAS, None, curado, fonte="Healing"))
        self.usados_no_descanso.clear()   # Impenetrable volta a valer
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

