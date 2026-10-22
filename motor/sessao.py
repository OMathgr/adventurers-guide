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

from .companheiro import OpcaoTreino
from .erros import RegraViolada
from .srd import ALTERNATIVAS_A_MORTE, DEFESAS_DE_CARTAS, Efeito, TipoDano

# cartas de domínio que mexem no dano recebido e no movimento de morte
GET_BACK_UP = "core_domain_card_get_back_up"
SHRUG_IT_OFF = "core_domain_card_shrug_it_off"
BRACE = "core_domain_card_brace"
RUNE_WARD = "core_domain_card_rune_ward"
UNYIELDING_ARMOR = "core_domain_card_unyielding_armor"
ON_THE_BRINK = "core_domain_card_on_the_brink"
RISE_UP = "core_domain_card_rise_up"
BATTLE_HARDENED = "core_domain_card_battle_hardened"
LIFE_WARD = "core_domain_card_life_ward"
SELO_DA_VIDA = "Selo da Vida"   # condição que o Life Ward de um aliado deixa

if TYPE_CHECKING:
    from .personagem import Personagem


class Gravidade(int, Enum):
    """Quantos PV um dano marca, pela comparação com os limiares."""

    NENHUM = 0
    MENOR = 1      # abaixo do limiar maior
    MAIOR = 2      # a partir do limiar maior
    GRAVE = 3      # a partir do limiar grave
    MASSIVO = 4    # regra opcional: a partir do dobro do limiar grave


class Condicao(str, Enum):
    """Condições padrão do SRD. Características podem criar outras
    ("temporary conditions"); essas entram como texto livre."""

    OCULTO = "OCULTO"          # Hidden (Escondido): rolagens contra você têm desvantagem
    CONTIDO = "CONTIDO"        # Restrained (Imobilizado): não pode se mover
    VULNERAVEL = "VULNERAVEL"  # Vulnerable: rolagens contra você têm vantagem


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


class MovimentoDeMorte(str, Enum):
    """Death moves: ao marcar o último PV, o jogador escolhe um."""

    SACRIFICIO_GLORIOSO = "SACRIFICIO_GLORIOSO"   # Blaze of Glory: ação final crítica, depois morre
    EVITAR_A_MORTE = "EVITAR_A_MORTE"             # Avoid Death: inconsciente; pode ganhar cicatriz
    ARRISCAR_TUDO = "ARRISCAR_TUDO"               # Risk It All: Dados de Dualidade decidem


class ImpactoDaCicatriz(str, Enum):
    """O impacto narrativo da cicatriz (o livro dá esses exemplos; o jogador escolhe)."""

    A_DEFINIR = ""
    FISICA = "FISICA"              # uma cicatriz física
    MEMORIA = "MEMORIA"            # uma memória dolorosa
    MEDO = "MEDO"                  # um medo paralisante
    OUTRO = "OUTRO"                # descrito no texto


@dataclass
class Cicatriz:
    """Risca um espaço de Esperança para sempre (até o mestre deixar curar)."""

    impacto: ImpactoDaCicatriz = ImpactoDaCicatriz.A_DEFINIR
    descricao: str = ""


@dataclass
class ResultadoMorte:
    movimento: MovimentoDeMorte
    morreu: bool
    inconsciente: bool = False
    cicatriz: bool = False
    rolagem_esperanca: int | None = None
    rolagem_medo: int | None = None
    pv_limpos: int = 0
    pf_limpos: int = 0
    notas: list[str] = field(default_factory=list)


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
    alvo: str | None = None      # nome do aliado, se o movimento foi nele


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
        # Efeitos de "uma vez por descanso" já usados (Impenetrable, Creature Comfort)
        self.usados_no_descanso: set[Enum] = set()
        self.descansos_curtos_seguidos = 0
        # companheiro do Beastbound
        self.companheiro_estresse = 0
        self.companheiro_fora = False
        # Condições atuais: as padrão (Condicao.value) e as de características (texto)
        self.condicoes: list[str] = []
        # Morte: Evitar a Morte deixa inconsciente (até limparem 1 PV ou um descanso
        # longo); atravessar o véu é para sempre; cada cicatriz risca 1 de Esperança
        self.inconsciente = False
        self.morto = False
        self.cicatrizes: list[Cicatriz] = []
        # Padrões Estranhos (Mago): o número escolhido (muda no descanso longo)
        self.padroes_estranhos: int | None = None
        # Rolagens (motor/rolagem.py): efeitos com limite já usados (id -> limite),
        # marcadores de cartas/habilidades, o último ataque (para o dano depois dele)
        # e a vantagem guardada pelo Inevitável
        self.usos_rolagem: dict[str, str] = {}
        self.marcadores_rolagem: dict[str, int] = {}
        self.ultimo_ataque: dict | None = None
        self.proxima_vantagem = False
        # Cartas usadas (motor/usos_de_cartas.py): marcadores em cada carta e bônus
        # que valem até o descanso ({carta: {"modificadores": [...], "ate": "descanso"}})
        self.marcadores_cartas: dict[str, int] = {}
        self.bonus_temporarios: dict[str, dict] = {}

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
                     rolagem_d6: int | None = None,
                     rolagens_vinculo: list[int] | None = None,
                     cartas: list[str] | None = None) -> ResultadoDano:
        """Marca PV conforme os limiares, aplicando as características equipadas.

        - `usar_armadura`: marca um espaço e reduz a gravidade em um nível
          (dois com Fortified). Sem espaço livre, não reduz.
        - `tipo`: físico ou mágico. Necessário para Warded, Magic e Physical;
          se omitido, essas regras não se aplicam.
        - `evitar_queda`: com Impenetrable (1x por descanso), marca Estresse no
          lugar do último PV.
        - `rolagem_d6`: o d6 do Resilient, se rolado na mesa (senão o motor rola).
        - `rolagens_vinculo`: os d6 do Bonded (companheiro), se rolados na mesa.
        - `cartas`: cartas da mão que o jogador usa (`DEFESAS_DE_CARTAS`: Get Back
          Up, Shrug It Off, Brace, Rune Ward), pagando o custo só se precisar.
          Unyielding Armor, On the Brink e Rise Up valem sozinhas (na mão).

        A gravidade é medida antes de marcar o espaço; por isso o +2 do
        Reinforced vale a partir do dano seguinte.
        """
        efeitos = self.personagem.efeitos_ativos()
        f = self._ficha()
        if rolagem_d6 is not None and not 1 <= rolagem_d6 <= 6:
            raise RegraViolada(f"Rolagem de d6 inválida: {rolagem_d6}.")
        if usar_armadura and tipo is TipoDano.MAGICO and Efeito.SO_FISICO in efeitos:
            raise RegraViolada("Sua armadura (Física) não reduz dano mágico.")
        if usar_armadura and tipo is TipoDano.FISICO and Efeito.SO_MAGICO in efeitos:
            raise RegraViolada("Sua armadura (Mágica) não reduz dano físico.")

        mao = set(self.personagem.cartas_na_mao())
        escolhidas = self._validar_defesas(cartas or [], mao, usar_armadura)
        bib = self.personagem.bib

        notas: list[str] = []
        estresse_antes = self.estresse_marcado
        if tipo is TipoDano.MAGICO and Efeito.PROTEGIDA in efeitos and f.pontuacao_armadura:
            reduzido = min(dano, f.pontuacao_armadura)
            dano -= reduzido
            notas.append(f"Égide: dano mágico reduzido em {reduzido}")
        if RUNE_WARD in escolhidas and dano > 0:
            self.gastar_esperanca(1)
            d8 = self.rng.randint(1, 8)
            dano = max(dano - d8, 0)
            notas.append(f"{bib.cartas[RUNE_WARD].nome}: d8 = {d8}, dano reduzido para {dano}")
            if d8 == 8:
                self.usos_rolagem[f"carta:{RUNE_WARD}"] = "descanso"
                notas.append(f"{bib.cartas[RUNE_WARD].nome}: tirou 8, o amuleto se apaga até o próximo descanso")

        gravidade = self.gravidade(dano)
        pv = int(gravidade)
        if (pv == int(Gravidade.MENOR) and ON_THE_BRINK in mao
                and self._ficha().pv_max - self.pv_marcados <= 2):
            pv = 0
            notas.append(f"{bib.cartas[ON_THE_BRINK].nome}: com 2 PV ou menos, não sofre dano Menor")
        usou = False
        espacos = 0
        d6 = None
        inabalavel = []
        if usar_armadura and pv > 0 and self.armadura_livre > 0 and UNYIELDING_ARMOR in mao:
            # Unyielding Armor: Proficiência d6; algum 6 reduz sem marcar espaço
            inabalavel = [self.rng.randint(1, 6) for _ in range(self._ficha().proficiencia)]
        if 6 in inabalavel:
            usou = True
            pv = max(pv - 1, 0)
            notas.append(f"{bib.cartas[UNYIELDING_ARMOR].nome}: {inabalavel}, reduziu sem marcar espaço")
        elif usar_armadura and pv > 0 and self.armadura_livre > 0:
            usou = True
            if inabalavel:
                notas.append(f"{bib.cartas[UNYIELDING_ARMOR].nome}: {inabalavel}, sem 6")
            if Efeito.RESILIENTE in efeitos and self.armadura_livre == 1:
                d6 = rolagem_d6 or self.rng.randint(1, 6)
                if d6 == 6:
                    notas.append("Resiliente: tirou 6 e reduziu sem marcar o último espaço")
            if d6 != 6:
                self._marcar_espaco(efeitos, notas)
                espacos = 1
            reducao = 2 if Efeito.FORTIFICADA in efeitos else 1
            if reducao == 2:
                notas.append("Fortificação: reduziu dois níveis")
            pv = max(pv - reducao, 0)
            if BRACE in escolhidas and pv > 0 and self.armadura_livre > 0:
                self.pagar_estresse(1)
                self._marcar_espaco(efeitos, notas)
                espacos += 1
                pv -= 1
                notas.append(f"{bib.cartas[BRACE].nome}: marcou 1 PF e mais um espaço de armadura")

        if GET_BACK_UP in escolhidas and gravidade >= Gravidade.GRAVE and pv > 0:
            self.pagar_estresse(1)
            pv -= 1
            notas.append(f"{bib.cartas[GET_BACK_UP].nome}: marcou 1 PF e reduziu um nível")
        if SHRUG_IT_OFF in escolhidas and pv > 0:
            self.pagar_estresse(1)
            pv -= 1
            d6 = self.rng.randint(1, 6)
            notas.append(f"{bib.cartas[SHRUG_IT_OFF].nome}: marcou 1 PF e reduziu um nível (d6 = {d6})")
            if d6 <= 3:
                self.personagem.guardar_carta(SHRUG_IT_OFF)
                notas.append(f"{bib.cartas[SHRUG_IT_OFF].nome} foi para a reserva")

        if (evitar_queda and pv > 0 and Efeito.IMPENETRAVEL in efeitos
                and Efeito.IMPENETRAVEL not in self.usados_no_descanso
                and self.pv_marcados + pv >= self._ficha().pv_max
                and self.estresse_livre > 0):
            pv -= 1
            self.estresse_marcado += 1
            self.usados_no_descanso.add(Efeito.IMPENETRAVEL)
            notas.append("Impenetrável: marcou 1 PF no lugar do último PV")

        self._exigir_vivo()
        self.marcar_pv(pv)
        if pv > 0 and RISE_UP in mao and self.estresse_marcado > 0:
            self.limpar_estresse(1)
            notas.append(f"{bib.cartas[RISE_UP].nome}: limpou 1 PF")
        if pv > 0 and self.caido:
            self._vinculo(notas, rolagens_vinculo)
        return ResultadoDano(dano, gravidade, pv, usou, self.caido, espacos,
                             self.estresse_marcado - estresse_antes, d6, notas)

    def _validar_defesas(self, cartas: list[str], mao: set[str], usar_armadura: bool) -> set[str]:
        """Confere as cartas de defesa escolhidas antes de mexer em qualquer coisa."""
        escolhidas = set(cartas)
        nomes = self.personagem.bib.cartas
        for c in escolhidas:
            if c not in DEFESAS_DE_CARTAS:
                raise RegraViolada("Essa carta não se usa ao receber dano.")
            if c not in mao:
                raise RegraViolada(f"{nomes[c].nome} precisa estar na mão.")
            if f"carta:{c}" in self.usos_rolagem:
                raise RegraViolada(f"{nomes[c].nome} só volta no próximo descanso.")
        if BRACE in escolhidas and not usar_armadura:
            raise RegraViolada(f"{nomes[BRACE].nome} só vale quando você marca armadura.")
        esperanca = sum(DEFESAS_DE_CARTAS[c][0] for c in escolhidas)
        fadiga = sum(DEFESAS_DE_CARTAS[c][1] for c in escolhidas)
        if esperanca > self.esperanca:
            raise RegraViolada(f"Esperança insuficiente: as cartas pedem {esperanca}.")
        if fadiga > self.estresse_livre:
            raise RegraViolada(f"Fadiga insuficiente: as cartas pedem {fadiga} PF livres.")
        return escolhidas

    def evitar_morte_com_carta(self, carta: str, rolagem: int | None = None) -> list[str]:
        """No lugar do movimento de morte: Battle Hardened (1x por descanso longo,
        gasta 1 Esperança e limpa 1 PV) ou Unbreakable (limpa 1d6 PV e vai para a reserva)."""
        self._exigir_vivo()
        if not self.precisa_movimento_de_morte:
            raise RegraViolada("Só quem marcou o último PV pode usar isso.")
        nome = self.personagem.bib.cartas[carta].nome if carta in self.personagem.bib.cartas else carta
        if carta == LIFE_WARD:   # o selo de um aliado: não precisa ter a carta
            if SELO_DA_VIDA not in self.condicoes:
                raise RegraViolada(f"Só com o {SELO_DA_VIDA} que um aliado pôs em você.")
            self.remover_condicao(SELO_DA_VIDA)
            self.limpar_pv(1)
            return [f"{SELO_DA_VIDA}: limpou 1 PV no lugar do movimento de morte, e o selo se apagou."]
        if carta not in ALTERNATIVAS_A_MORTE:
            raise RegraViolada(f"{nome} não substitui o movimento de morte.")
        if carta not in self.personagem.cartas_na_mao():
            raise RegraViolada(f"{nome} precisa estar na mão.")
        if f"carta:{carta}" in self.usos_rolagem:
            raise RegraViolada(f"{nome} só volta no próximo descanso longo.")
        if carta == BATTLE_HARDENED:
            if self.esperanca < 1:
                raise RegraViolada(f"{nome} custa 1 de Esperança.")
            self.gastar_esperanca(1)
            self.limpar_pv(1)
            self.usos_rolagem[f"carta:{carta}"] = "descanso_longo"
            return [f"{nome}: gastou 1 de Esperança e limpou 1 PV no lugar do movimento de morte."]
        if rolagem is not None and not 1 <= rolagem <= 6:
            raise RegraViolada(f"Rolagem de d6 inválida: {rolagem}.")
        d6 = rolagem or self.rng.randint(1, 6)
        self.limpar_pv(d6)
        self.personagem.guardar_carta(carta)
        return [f"{nome}: d6 = {d6}, limpou {d6} PV no lugar do movimento de morte. A carta foi para a reserva."]

    def marcar_pv(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.pv_marcados = min(self.pv_marcados + quantidade, self._ficha().pv_max)

    def limpar_pv(self, quantidade: int = 1):
        self._exigir_positivo(quantidade)
        self.pv_marcados = max(self.pv_marcados - quantidade, 0)
        if quantidade > 0:
            self.inconsciente = False   # um aliado limpou PV: volta a si

    @property
    def caido(self) -> bool:
        return self.pv_marcados >= self._ficha().pv_max

    @property
    def precisa_movimento_de_morte(self) -> bool:
        """Marcou o último PV e ainda não escolheu o movimento de morte."""
        return self.caido and not self.inconsciente and not self.morto

    # --- Morte -------------------------------------------------------------------------

    def movimento_de_morte(self, movimento: MovimentoDeMorte | str, rolagem_esperanca: int | None = None,
                           rolagem_medo: int | None = None, pv: int | None = None) -> ResultadoMorte:
        """Death move. As rolagens (d12) vêm da mesa ou o motor rola. `pv`: no
        Arriscar Tudo que dá certo, quanto do Dado de Esperança vai para PV (o
        resto vai para PF); sem ele, PV primeiro."""
        self._exigir_vivo()
        if not self.precisa_movimento_de_morte:
            raise RegraViolada("Só quem marcou o último PV faz um movimento de morte.")
        movimento = MovimentoDeMorte(movimento)
        for r in (rolagem_esperanca, rolagem_medo):
            if r is not None and not 1 <= r <= 12:
                raise RegraViolada(f"Rolagem de d12 inválida: {r}.")
        esperanca = rolagem_esperanca or self.rng.randint(1, 12)

        if movimento is MovimentoDeMorte.SACRIFICIO_GLORIOSO:
            self.morto = True
            return ResultadoMorte(movimento, morreu=True, notas=[
                "Faça uma ação final: com o aval do mestre, ela é um sucesso crítico. "
                "Depois, o personagem atravessa o véu da morte."])

        if movimento is MovimentoDeMorte.EVITAR_A_MORTE:
            self.inconsciente = True
            r = ResultadoMorte(movimento, morreu=False, inconsciente=True, rolagem_esperanca=esperanca, notas=[
                "Inconsciente: não se move nem age e não pode ser alvo de ataques. Volta a si quando um "
                "aliado limpar 1 PV ou mais, ou no fim de um descanso longo. Combine com o mestre como a cena piora."])
            if esperanca <= self._ficha().nivel:
                self.cicatrizes.append(Cicatriz())
                r.cicatriz = True
                r.notas.append("Ganhou uma cicatriz: um espaço de Esperança foi riscado. Escolha o impacto dela na ficha.")
                if self._limite_esperanca <= 0:
                    self.morto, r.morreu = True, True
                    r.notas.append("Era o último espaço de Esperança: a jornada do personagem termina.")
                self.ajustar()
            return r

        medo = rolagem_medo or self.rng.randint(1, 12)
        r = ResultadoMorte(movimento, morreu=False, rolagem_esperanca=esperanca, rolagem_medo=medo)
        if esperanca == medo:
            r.pv_limpos, r.pf_limpos = self.pv_marcados, self.estresse_marcado
            self.pv_marcados = self.estresse_marcado = 0
            r.notas.append("Crítico: continua de pé e limpa todos os PV e PF.")
        elif esperanca > medo:
            para_pv = min(esperanca, self.pv_marcados) if pv is None else pv
            if not 0 <= para_pv <= esperanca:
                raise RegraViolada(f"Divida os {esperanca} do Dado de Esperança entre PV e PF.")
            r.pv_limpos = min(para_pv, self.pv_marcados)
            r.pf_limpos = min(esperanca - para_pv, self.estresse_marcado)
            self.pv_marcados -= r.pv_limpos
            self.estresse_marcado -= r.pf_limpos
            r.notas.append(f"A Esperança venceu: continua de pé e limpa {r.pv_limpos} PV e {r.pf_limpos} PF.")
        else:
            self.morto, r.morreu = True, True
            r.notas.append("O Medo venceu: o personagem atravessa o véu da morte.")
        return r

    def definir_cicatriz(self, indice: int, impacto: ImpactoDaCicatriz | str, descricao: str = ""):
        """O jogador escolhe o impacto narrativo (física, memória, medo ou outro)."""
        if not 0 <= indice < len(self.cicatrizes):
            raise RegraViolada("Cicatriz não encontrada.")
        self.cicatrizes[indice] = Cicatriz(ImpactoDaCicatriz(impacto), descricao.strip()[:500])

    def curar_cicatriz(self, indice: int):
        """A critério do mestre (projeto no repouso, missão...): o espaço de Esperança volta."""
        if not 0 <= indice < len(self.cicatrizes):
            raise RegraViolada("Cicatriz não encontrada.")
        del self.cicatrizes[indice]

    def _exigir_vivo(self):
        if self.morto:
            raise RegraViolada("Este personagem atravessou o véu da morte.")

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
            raise RegraViolada(f"Fadiga insuficiente: custa {quantidade} PF, "
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
                raise RegraViolada("Só uma armadura com Esperança troca Esperança por espaço de armadura.")
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
            notas.append("Excruciante: marcou 1 PF")

    # --- Descansos -----------------------------------------------------------------

    def descanso_curto(self, movimentos: list[Movimento],
                       rolagens: list[int | None] | None = None,
                       movimento_longo: int | None = None) -> list[ResultadoMovimento]:
        """Dois movimentos (pode repetir; três com Celestial Trance).
        Recuperações rolam 1d4 + tier.

        - `rolagens`: o d4 de cada movimento, se rolado na mesa (None = o motor rola).
        - `movimento_longo`: com Efficient (Clank), o índice do movimento que
          vale como movimento de descanso longo.

        Regra do SRD: depois de três descansos curtos seguidos, o próximo
        precisa ser longo.
        """
        limite = self.personagem.bib.progressao["descansos_curtos_seguidos"]
        if self.descansos_curtos_seguidos >= limite:
            raise RegraViolada(f"Depois de {limite} descansos curtos seguidos, o próximo precisa ser longo.")
        longos = set()
        if movimento_longo is not None:
            if Efeito.EFICIENTE not in self.personagem.efeitos_ativos():
                raise RegraViolada("Só Eficiente (Clank) troca um movimento curto por um longo.")
            if not 0 <= movimento_longo < len(movimentos):
                raise RegraViolada("Índice de movimento inválido.")
            longos.add(movimento_longo)
        if any(m is Movimento.PROJETO and i not in longos for i, m in enumerate(movimentos)):
            raise RegraViolada("Trabalhar num projeto só no descanso longo.")
        resultados = self._descansar(movimentos, rolagens, longos)
        self.descansos_curtos_seguidos += 1
        return resultados

    def descanso_longo(self, movimentos: list[Movimento]) -> list[ResultadoMovimento]:
        """Dois movimentos (pode repetir; três com Celestial Trance).
        Recuperações limpam tudo. O companheiro fora de cena volta."""
        self._validar_movimentos(movimentos, None)
        if self.companheiro_fora:
            # volta no início do descanso longo, com 1 Estresse limpo
            self.companheiro_fora = False
            self.companheiro_estresse = max(self.companheiro_estresse - 1, 0)
        resultados = self._descansar(movimentos, None, set(range(len(movimentos))))
        self.inconsciente = False   # fim de um descanso longo: volta a si
        self.descansos_curtos_seguidos = 0
        return resultados

    def _validar_movimentos(self, movimentos, rolagens) -> list[int | None]:
        maximo = 3 if Efeito.TRANSE in self.personagem.efeitos_ativos() else 2
        if not 2 <= len(movimentos) <= maximo:
            raise RegraViolada("Escolha dois movimentos de descanso"
                               + (" (ou três, com Transe Celestial)." if maximo == 3 else "."))
        rolagens = list(rolagens) if rolagens is not None else [None] * len(movimentos)
        if len(rolagens) != len(movimentos):
            raise RegraViolada("Informe uma rolagem (ou None) para cada movimento.")
        for r in rolagens:
            if r is not None and not 1 <= r <= 4:
                raise RegraViolada(f"Rolagem de d4 inválida: {r}.")
        return rolagens

    def _descansar(self, movimentos, rolagens, longos: set[int]) -> list[ResultadoMovimento]:
        """`longos`: índices dos movimentos feitos na versão de descanso longo."""
        self._exigir_vivo()
        rolagens = self._validar_movimentos(movimentos, rolagens)
        resultados = [self.aplicar_movimento(m, i in longos, r) for i, (m, r) in enumerate(zip(movimentos, rolagens))]
        return resultados + self.terminar_repouso(longo=False)

    def aplicar_movimento(self, movimento: Movimento, longo: bool, rolagem: int | None = None,
                          alvo: Sessao | None = None) -> ResultadoMovimento:
        """Um movimento de descanso. Tratar Feridas e Reparar Armadura podem ser
        num aliado (`alvo`); o tier (no curto) é sempre o de quem faz."""
        self._exigir_vivo()
        alvo = alvo or self
        if alvo is not self and movimento not in (Movimento.CUIDAR_FERIDAS, Movimento.REPARAR_ARMADURA):
            raise RegraViolada("Só Tratar Feridas e Reparar Armadura podem ser feitos num aliado.")
        if alvo is not self and alvo.morto:
            raise RegraViolada("Esse aliado atravessou o véu da morte.")
        tier = self.personagem.bib.tier_do_nivel(self._ficha().nivel)
        nome_alvo = (alvo.personagem.criacao.nome or "aliado") if alvo is not self else None
        if movimento in _RECUPERACAO:
            campo = _RECUPERACAO[movimento]
            marcados = getattr(alvo, campo)
            if longo:
                rolagem, potencial = None, None   # limpa tudo
            else:
                rolagem = rolagem or self.rng.randint(1, 4)
                potencial = rolagem + tier
            quanto = marcados if potencial is None else min(potencial, marcados)
            setattr(alvo, campo, marcados - quanto)
            if movimento is Movimento.CUIDAR_FERIDAS and quanto > 0:
                alvo.inconsciente = False   # limparam PV: volta a si
            if movimento is Movimento.ALIVIAR_ESTRESSE:
                # o companheiro limpa o mesmo número de Estresse
                self._companheiro_limpa(self.companheiro_estresse if potencial is None else potencial)
        elif movimento in (Movimento.PREPARAR, Movimento.PREPARAR_EM_GRUPO):
            antes = self.esperanca
            self.ganhar_esperanca(2 if movimento is Movimento.PREPARAR_EM_GRUPO else 1)
            rolagem, quanto = None, self.esperanca - antes
        else:   # PROJETO: narrativo
            rolagem, quanto = None, 0
        return ResultadoMovimento(movimento, rolagem, quanto, alvo=nome_alvo)

    def terminar_repouso(self, longo: bool) -> list[ResultadoMovimento]:
        """O que acontece no fim de qualquer descanso (e, no longo, acordar)."""
        resultados = []
        # Healing: "during downtime, automatically clear a Hit Point"
        if Efeito.CURA in self.personagem.efeitos_ativos():
            curado = min(1, self.pv_marcados)
            self.pv_marcados -= curado
            resultados.append(ResultadoMovimento(Movimento.CUIDAR_FERIDAS, None, curado, fonte="Healing"))
        self.usados_no_descanso.clear()   # Impenetrable, Creature Comfort voltam a valer
        # efeitos de rolagem "uma vez por descanso" (e, no longo, os de descanso longo)
        voltam = ("descanso", "descanso_longo") if longo else ("descanso",)
        self.usos_rolagem = {k: v for k, v in self.usos_rolagem.items() if v not in voltam}
        # cartas: bônus "até o descanso" acabam; marcadores voltam ao que a carta dá
        self.bonus_temporarios = {k: v for k, v in self.bonus_temporarios.items() if v.get("ate") not in voltam}
        self.personagem.recarregar_cartas(voltam)
        if longo:
            self.inconsciente = False   # o grupo terminou um descanso longo: volta a si
        return resultados

    # --- Companheiro (Beastbound) ------------------------------------------------------

    def companheiro_recebe_dano(self, usar_armadura: bool = False) -> bool:
        """Qualquer dano no companheiro marca 1 Estresse dele. Com Armored,
        você pode marcar um espaço da SUA armadura no lugar.
        No último Estresse ele sai de cena até o próximo descanso longo.
        Devolve se ele saiu de cena."""
        comp = self._companheiro_presente()
        if usar_armadura:
            if not comp.tem(OpcaoTreino.BLINDADO):
                raise RegraViolada("Só com o treino Blindado o companheiro usa sua armadura.")
            if self.armadura_livre <= 0:
                raise RegraViolada("Sem espaço de armadura livre.")
            self._marcar_espaco(self.personagem.efeitos_ativos(), [])
            return False
        self.companheiro_estresse = min(self.companheiro_estresse + 1, comp.estresse_max)
        if self.companheiro_estresse >= comp.estresse_max:
            self.companheiro_fora = True
        return self.companheiro_fora

    def conforto_do_companheiro(self, ganhar_esperanca: bool):
        """Creature Comfort: 1x por descanso, num momento tranquilo, você ganha
        uma Esperança OU vocês dois limpam um Estresse."""
        comp = self._companheiro_presente()
        if not comp.tem(OpcaoTreino.CONFORTO):
            raise RegraViolada("Seu companheiro não tem o treino Conforto Animal.")
        if OpcaoTreino.CONFORTO in self.usados_no_descanso:
            raise RegraViolada("Conforto Animal já foi usado neste descanso.")
        if ganhar_esperanca:
            self.ganhar_esperanca(1)
        else:
            self.limpar_estresse(1)
            self._companheiro_limpa(1)
        self.usados_no_descanso.add(OpcaoTreino.CONFORTO)

    def _companheiro_limpa(self, quantidade: int):
        if self._ficha().companheiro and not self.companheiro_fora:
            self.companheiro_estresse = max(self.companheiro_estresse - quantidade, 0)

    def _companheiro_presente(self):
        comp = self._ficha().companheiro
        if comp is None:
            raise RegraViolada("Você não tem companheiro.")
        if self.companheiro_fora:
            raise RegraViolada(f"{comp.nome} está fora de cena até o próximo descanso longo.")
        return comp

    def _vinculo(self, notas: list[str], rolagens: list[int] | None):
        """Bonded: ao marcar seu último PV, o companheiro corre até você. Rola
        um d6 por Estresse livre dele e marca todos; com algum 6, você limpa
        o último PV e volta à cena."""
        comp = self._ficha().companheiro
        if not (comp and comp.tem(OpcaoTreino.VINCULO) and not self.companheiro_fora):
            return
        livres = comp.estresse_max - self.companheiro_estresse
        if livres <= 0:
            return
        dados = list(rolagens) if rolagens is not None else [self.rng.randint(1, 6) for _ in range(livres)]
        if len(dados) != livres or any(not 1 <= d <= 6 for d in dados):
            raise RegraViolada(f"Vínculo: informe {livres} rolagens de d6.")
        self.companheiro_estresse = comp.estresse_max
        self.companheiro_fora = True
        if 6 in dados:
            self.pv_marcados -= 1
            notas.append(f"Vínculo: {comp.nome} rolou {dados} e te levantou")
        else:
            notas.append(f"Vínculo: {comp.nome} rolou {dados}, sem 6")

    # --- Condições -------------------------------------------------------------------

    def aplicar_condicao(self, condicao: Condicao | str) -> str:
        """Aplica uma condição. Nomes das padrão (Hidden/OCULTO...) viram o
        valor do enum; outros nomes ficam como condição de característica.
        Condições duram até serem removidas (o SRD não dá prazo fixo)."""
        nome = normalizar_condicao(condicao)
        if nome in self.condicoes:
            raise RegraViolada(f"O personagem já está com a condição {nome}.")
        self.condicoes.append(nome)
        return nome

    def remover_condicao(self, condicao: Condicao | str):
        nome = normalizar_condicao(condicao)
        if nome not in self.condicoes:
            raise RegraViolada(f"O personagem não está com a condição {nome}.")
        self.condicoes.remove(nome)

    # --- Persistência -------------------------------------------------------------------

    # O que segue o personagem de uma sessão de jogo para a outra; o resto do
    # estado é de cada sessão (começa limpo, com a Esperança inicial).
    CAMPOS_PERMANENTES = ("morto", "cicatrizes")

    def estado_permanente(self) -> dict:
        return {k: v for k, v in self.estado().items() if k in self.CAMPOS_PERMANENTES}

    def estado_da_sessao(self) -> dict:
        return {k: v for k, v in self.estado().items() if k not in self.CAMPOS_PERMANENTES}

    def estado(self) -> dict:
        """Tudo o que precisa ser salvo, só com tipos simples (vira JSON)."""
        return {
            "pv_marcados": self.pv_marcados,
            "estresse_marcado": self.estresse_marcado,
            "esperanca": self.esperanca,
            "armadura_marcada": self.armadura_marcada,
            "dano_massivo": self.dano_massivo,
            "descansos_curtos_seguidos": self.descansos_curtos_seguidos,
            "companheiro_estresse": self.companheiro_estresse,
            "companheiro_fora": self.companheiro_fora,
            "condicoes": list(self.condicoes),
            "inconsciente": self.inconsciente,
            "morto": self.morto,
            "cicatrizes": [{"impacto": c.impacto.value, "descricao": c.descricao} for c in self.cicatrizes],
            "padroes_estranhos": self.padroes_estranhos,
            "usos_rolagem": dict(self.usos_rolagem),
            "marcadores_rolagem": dict(self.marcadores_rolagem),
            "ultimo_ataque": self.ultimo_ataque,
            "proxima_vantagem": self.proxima_vantagem,
            "marcadores_cartas": dict(self.marcadores_cartas),
            "bonus_temporarios": dict(self.bonus_temporarios),
            "usados_no_descanso": sorted(f"{type(e).__name__}:{e.value}"
                                         for e in self.usados_no_descanso),
        }

    def restaurar(self, estado: dict):
        """Inverso de estado(). Campo que falta fica como numa sessão nova
        (ex.: só o permanente, quando o personagem não está em jogo)."""
        tipos = {"Efeito": Efeito, "OpcaoTreino": OpcaoTreino}
        for campo in ("pv_marcados", "estresse_marcado", "esperanca", "armadura_marcada",
                      "dano_massivo", "descansos_curtos_seguidos", "companheiro_estresse",
                      "companheiro_fora"):
            if campo in estado:
                setattr(self, campo, estado[campo])
        self.condicoes = list(estado.get("condicoes", []))
        self.inconsciente = bool(estado.get("inconsciente", False))
        self.padroes_estranhos = estado.get("padroes_estranhos")
        self.usos_rolagem = dict(estado.get("usos_rolagem", {}))
        self.marcadores_rolagem = dict(estado.get("marcadores_rolagem", {}))
        self.ultimo_ataque = estado.get("ultimo_ataque")
        self.proxima_vantagem = bool(estado.get("proxima_vantagem", False))
        self.marcadores_cartas = dict(estado.get("marcadores_cartas", {}))
        self.bonus_temporarios = dict(estado.get("bonus_temporarios", {}))
        self.morto = bool(estado.get("morto", False))
        self.cicatrizes = [Cicatriz(ImpactoDaCicatriz(c.get("impacto", "")), c.get("descricao", ""))
                           for c in estado.get("cicatrizes", [])]
        self.usados_no_descanso = set()
        for item in estado.get("usados_no_descanso", []):
            tipo, valor = item.split(":", 1)
            self.usados_no_descanso.add(tipos[tipo](valor))
        self.ajustar()

    # --- Ajuste quando os máximos caem ----------------------------------------------

    def ajustar(self):
        """Chamado quando um máximo pode ter diminuído (trocar armadura,
        desfazer nível): nada fica marcado além do máximo."""
        f = self._ficha()
        self.pv_marcados = min(self.pv_marcados, f.pv_max)
        self.estresse_marcado = min(self.estresse_marcado, f.estresse_max)
        self.armadura_marcada = min(self.armadura_marcada, f.pontuacao_armadura)
        self.esperanca = min(self.esperanca, f.esperanca_max)
        if f.companheiro is None:
            self.companheiro_estresse, self.companheiro_fora = 0, False
        else:
            self.companheiro_estresse = min(self.companheiro_estresse, f.companheiro.estresse_max)

    # --- utilitários ----------------------------------------------------------------

    def _ficha(self):
        return self.personagem.ficha()

    @property
    def _limite_esperanca(self) -> int:
        return self._ficha().esperanca_max   # 6, ou 7 com Light in the Dark

    @staticmethod
    def _exigir_positivo(quantidade: int):
        if quantidade < 0:
            raise RegraViolada("Quantidade não pode ser negativa.")


_NOMES_SRD = {"HIDDEN": Condicao.OCULTO, "RESTRAINED": Condicao.CONTIDO,
              "ESCONDIDO": Condicao.OCULTO, "IMOBILIZADO": Condicao.CONTIDO,   # nomes do livro
              "VULNERABLE": Condicao.VULNERAVEL}


def normalizar_condicao(condicao: Condicao | str) -> str:
    if isinstance(condicao, Condicao):
        return condicao.value
    nome = condicao.strip()
    if not nome:
        raise RegraViolada("Informe o nome da condição.")
    chave = nome.upper()
    if chave in Condicao.__members__:
        return Condicao[chave].value
    if chave in _NOMES_SRD:
        return _NOMES_SRD[chave].value
    return nome   # condição de característica: mantém como escrita
