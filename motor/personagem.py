"""Personagem de Daggerheart: criação, level up e linha do tempo.

Ideia central: o personagem NÃO é guardado como uma ficha pronta.
Guardamos a CRIAÇÃO e o HISTÓRICO de cada subida de nível. A ficha é
sempre recalculada a partir disso ("replay").

Isso dá de graça:
  - linha do tempo: é só listar o histórico;
  - ver a ficha em qualquer nível passado: ficha(ate_nivel=3);
  - desfazer um nível: remover o último item do histórico;
  - validação: cada nível é checado contra a ficha do nível anterior.
"""

import copy
import dataclasses
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from .companheiro import (Companheiro, FichaCompanheiro, OpcaoTreino, Treino,
                          aplicar_treino, criar_companheiro, nova_experiencia)
from .erros import RegraViolada
from .inventario import Inventario, inventario_inicial
from .itens_proprios import ItemProprio, TipoProprio
from .itens_proprios import copia as copia_proprio
from .itens_proprios import separar as separar_proprios
from .numeros import metade
from .rolagem import (TIPOS_DE_TESTE, Bonus, DadoRolado, Dualidade, EfeitoDeRolagem, PapelDoDado, PlanoDeDano,
                      ResultadoRolagem, _delta, _ganhar_esperanca, _limpar_fadiga, aplicar_teste, dado, desfazer,
                      expandir, ler_expressao, recalcular_teste, resolver, rolar_dano, rolar_dualidade, rolar_teste)
from .sessao import Cicatriz, Sessao
from .srd import (ALTERNATIVAS_A_MORTE, DEFESAS_DE_CARTAS, LIMIARES_OSSOS_EXPOSTOS, PONTUACAO_OSSOS_EXPOSTOS, Alvo, Arma, Armadura, Biblioteca, Caracteristica,
                  CartaDeDominio, Efeito, EscolhaDeCarta, Modificador, PassivoDeCarta, Referencia, Subclasse, TipoDano,
                  TipoDeItem, Traco)

DISTRIBUICAO_TRACOS = sorted([2, 1, 1, 0, 0, -1])


def _rolar(dado: str, rolagem: int | None, rng) -> int:
    """Resolve "1d4+1". `rolagem` é a soma dos dados que a pessoa rolou na mesa
    (sem o +1); sem ela, o motor rola."""
    m = re.fullmatch(r"(\d+)d(\d+)(?:\+(\d+))?", dado)
    n, faces, bonus = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if rolagem is None:
        rolagem = sum(rng.randint(1, faces) for _ in range(n))
    elif not n <= rolagem <= n * faces:
        raise RegraViolada(f"Resultado impossível para {n}d{faces}: {rolagem}.")
    return rolagem + bonus
ESTAGIOS_SUBCLASSE = ["fundacao", "especializacao", "maestria"]


class Opcao(str, Enum):
    """Opções de avanço da página de Level Up da ficha."""

    TRACOS = "TRACOS"              # +1 em dois atributos não marcados
    PV = "PV"                      # +1 slot de Pontos de Vida
    ESTRESSE = "ESTRESSE"          # +1 slot de Estresse
    EXPERIENCIAS = "EXPERIENCIAS"  # +1 em duas Experiências
    CARTA_DOMINIO = "CARTA_DOMINIO"  # carta de domínio adicional
    EVASAO = "EVASAO"              # +1 Evasão
    SUBCLASSE = "SUBCLASSE"        # próxima carta de subclasse
    PROFICIENCIA = "PROFICIENCIA"  # +1 Proficiência (custa os 2 avanços)
    MULTICLASSE = "MULTICLASSE"    # nova classe (custa os 2 avanços)

    @property
    def rotulo(self) -> str:
        return _ROTULO_OPCAO[self]


_ROTULO_OPCAO = {
    Opcao.TRACOS: "+1 em dois atributos", Opcao.PV: "+1 espaço de Ponto de Vida",
    Opcao.ESTRESSE: "+1 espaço de Fadiga", Opcao.EXPERIENCIAS: "+1 em duas Experiências",
    Opcao.CARTA_DOMINIO: "Carta de domínio adicional", Opcao.EVASAO: "+1 de Evasão",
    Opcao.SUBCLASSE: "Carta de subclasse aprimorada", Opcao.PROFICIENCIA: "+1 de Proficiência",
    Opcao.MULTICLASSE: "Multiclasse",
}


# --- Entradas: o que o jogador escolhe -------------------------------------

@dataclass
class Criacao:
    classe: str
    subclasse: str
    ancestralidade: str
    comunidade: str
    tracos: dict[Traco, int]
    experiencias: list[str]
    cartas: list[str]
    nome: str = ""
    # Ancestralidade mista: a 1ª característica vem de `ancestralidade` e a
    # 2ª de `segunda_ancestralidade` (SRD: nunca duas primeiras ou duas segundas).
    segunda_ancestralidade: str | None = None
    experiencia_proposito: str | None = None   # Purposeful Design (Clank): qual Experiência ganha +1
    companheiro: Companheiro | None = None     # obrigatório para o Beastbound
    # Passo 5 (itens iniciais): a poção escolhida e um dos itens da classe.
    # Sem eles (personagens antigos), o inventário começa vazio.
    pocao_inicial: str | None = None
    item_de_classe: str | None = None


@dataclass
class Escolha:
    """Um avanço escolhido. `tier` permite usar um slot de tier anterior."""

    opcao: Opcao
    tier: int | None = None
    tracos: tuple[Traco, ...] = ()
    experiencias: tuple[str, ...] = ()
    carta: str | None = None
    classe: str | None = None      # usado por MULTICLASSE
    dominio: str | None = None     # usado por MULTICLASSE
    subclasse: str | None = None   # usado por MULTICLASSE
    companheiro: Companheiro | None = None   # MULTICLASSE para o Beastbound


@dataclass
class SubidaDeNivel:
    nivel: int
    escolhas: list[Escolha]
    carta: str                                   # passo 4: nova carta de domínio
    nova_experiencia: str | None = None          # só nos níveis 2, 5 e 8
    troca_carta: tuple[str, str] | None = None   # (carta antiga, carta nova)
    # Beastbound: um treino por nível (+1 na especialização, +2 na maestria)
    treinos: list[Treino] = field(default_factory=list)
    experiencia_companheiro: str | None = None   # nos níveis 2, 5 e 8, se tiver companheiro
    # Mão cheia ao ganhar carta: cartas que já tinha e vão para a reserva sem
    # custo, para as novas entrarem na mão ("Trocando ao Subir de Nível").
    para_reserva: list[str] = field(default_factory=list)
    # Cartas a mais que uma habilidade ganha neste nível dá (Discípulo do
    # Conhecimento: Talentoso/Brilhante, ou Promissor numa multiclasse)
    cartas_extras: list[str] = field(default_factory=list)
    # Cartas que pedem escolha ao serem pegas neste nível (carta id -> escolhas):
    # Vitality: dois entre "PV", "ESTRESSE" e "LIMIARES"; Master of the Craft:
    # duas Experiências (+2 cada) ou uma (+3).
    beneficios_de_carta: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Equipamento:
    """O que o personagem está usando AGORA. Não faz parte do histórico:
    trocar de arma acontece durante o jogo, não ao subir de nível."""

    principal: str | None = None
    secundaria: str | None = None
    armadura: str | None = None
    # Versatile Fighter: atributo do ataque no lugar do da arma (só vale com a carta na mão)
    traco_principal: Traco | None = None
    traco_secundaria: Traco | None = None


# --- Saída: a ficha calculada ----------------------------------------------

@dataclass
class Ataque:
    arma: str        # nome de exibição
    traco: Traco     # atributo usado na rolagem de ataque
    bonus: int       # atributo (já com modificadores) + bônus de ataque da arma
    alcance: str
    dano: str        # ex.: "2d8+1" (número de dados = Proficiência)
    tipo_dano: TipoDano
    caracteristicas: list[Caracteristica] = field(default_factory=list)
    arma_original: str = ""   # nome no SRD (inglês)
    traco_da_arma: Traco | None = None   # Versatilidade: o atributo que a arma pede (quando `traco` é outro)


@dataclass
class ProximoNivel:
    nivel: int
    tier: int
    nova_experiencia: bool             # conquista de tier (níveis 2, 5, 8)
    limpa_marcas_tracos: bool          # níveis 5 e 8
    experiencia_companheiro: bool      # o companheiro também ganha uma
    avancos: int                       # quantos avanços escolher (custo total)
    opcoes: list[dict]                 # avanços disponíveis (ver opcoes_disponiveis)
    tracos_marcados: list[Traco]       # não podem subir de novo neste nível
    treinos: int                       # treinos do companheiro exigidos
    treinos_extra_com_subclasse: int   # a mais se marcar SUBCLASSE (Expert/Advanced Training)
    limite_mesa: int | None = None     # nível máximo da mesa (None: sem limite)
    bloqueado_pela_mesa: bool = False  # o próximo nível passa do limite da mesa
    planejado: bool = False            # há um plano para este nível (aplicar_plano)


@dataclass
class OpcaoDeRolagem:
    """Um efeito do catálogo para a tela: automático, opção antes de rolar ou reação."""

    id: str
    nome: str
    momento: str                 # automatico, antes, depois
    condicao: str = ""
    custo_esperanca: int = 0
    custo_fadiga: int = 0
    por_unidade: bool = False    # o custo vale por unidade da quantidade
    limite: str | None = None
    quantidade_max: int | None = None
    escolha: list[str] = field(default_factory=list)
    alvo: str = "proprio"
    se: str | None = None
    disponivel: bool = True
    motivo: str = ""


@dataclass
class OpcaoEscolhida:
    """Opção pedida numa rolagem."""

    id: str
    quantidade: int | None = None
    escolha: str | None = None


@dataclass
class HabilidadeNaFicha:
    """Habilidade de classe ou de subclasse, como aparece na ficha."""

    nome: str
    descricao: str
    origem: str        # nome de exibição da classe ou subclasse
    tipo: str          # "esperanca", "classe", "fundacao", "especializacao" ou "maestria"
    automatica: bool   # o motor já aplica (números da ficha ou regra); senão é texto para a mesa
    nome_original: str = ""


@dataclass
class DefesaDeCarta:
    """Carta que o jogador pode usar ao receber dano (Get Back Up, Brace...)."""

    carta: str
    nome: str
    custo_esperanca: int = 0
    custo_fadiga: int = 0


@dataclass
class Conjuracao:
    subclasse: str   # nome de exibição da subclasse que dá o atributo
    traco: Traco     # atributo de conjuração da subclasse
    bonus: int       # atributo (já com modificadores) + bônus de equipamento


@dataclass
class Ficha:
    nome: str
    nivel: int
    classe: str
    subclasse: str
    estagio_subclasse: str
    ancestralidade: str
    comunidade: str
    tracos: dict[Traco, int]
    evasao: int
    pv_max: int
    estresse_max: int
    esperanca: int
    proficiencia: int
    experiencias: dict[str, int]
    cartas: list[str]
    tracos_marcados: set[Traco] = field(default_factory=set)
    multiclasse: dict | None = None
    # controle interno dos quadradinhos da página de Level Up
    slots_usados: dict[tuple[int, str], int] = field(default_factory=dict)
    subclasse_bloqueada_tiers: set[int] = field(default_factory=set)
    multiclasse_bloqueada: bool = False
    # preenchidos por _vestir a partir do equipamento atual
    # (evasao e tracos acima também recebem os modificadores do equipamento)
    limiar_maior: int = 0
    limiar_grave: int = 0
    pontuacao_armadura: int = 0
    armadura: str | None = None   # nome de exibição
    armadura_original: str | None = None   # nome no SRD (inglês)
    caracteristicas_armadura: list[Caracteristica] = field(default_factory=list)
    ataques: list[Ataque] = field(default_factory=list)
    # uma por subclasse que conjura (a principal e, se houver, a da multiclasse)
    conjuracoes: list[Conjuracao] = field(default_factory=list)
    # `cartas` (acima) tem todas; aqui elas estão divididas entre ativas e cofre
    cartas_ativas: list[str] = field(default_factory=list)   # loadout
    cartas_cofre: list[str] = field(default_factory=list)    # vault
    # estado de sessão (marcas atuais); `esperanca` acima é a Esperança atual
    pv_marcados: int = 0
    estresse_marcado: int = 0
    armadura_marcada: int = 0
    esperanca_max: int = 6
    segunda_ancestralidade: str | None = None
    caracteristicas_ancestralidade: list[Caracteristica] = field(default_factory=list)
    caracteristicas_comunidade: list[Caracteristica] = field(default_factory=list)
    companheiro: FichaCompanheiro | None = None
    condicoes: list[str] = field(default_factory=list)   # estado de sessão
    # morte (estado de sessão): cada cicatriz risca 1 espaço de Esperança
    inconsciente: bool = False
    morto: bool = False
    precisa_movimento_de_morte: bool = False
    cicatrizes: list[Cicatriz] = field(default_factory=list)
    # de classe (e da multiclasse) e das cartas de subclasse que o personagem tem
    habilidades: list[HabilidadeNaFicha] = field(default_factory=list)
    padroes_estranhos: int | None = None   # Mago: o número escolhido (estado de sessão)
    # permanente, de cartas como Vitality (somado aos dois limiares em _vestir)
    bonus_limiares: int = 0
    # cartas na mão cujo passivo já está aplicado nos números da ficha
    cartas_aplicadas: list[str] = field(default_factory=list)
    # cartas da mão que dá para usar agora ao receber dano / no lugar do movimento de morte
    defesas_de_carta: list[DefesaDeCarta] = field(default_factory=list)
    alternativas_a_morte: list[str] = field(default_factory=list)


class Personagem:
    def __init__(self, biblioteca: Biblioteca, criacao: Criacao):
        self.bib = biblioteca
        self.criacao = criacao
        self.historico: list[SubidaDeNivel] = []
        self.equipamento = Equipamento()
        # Cartas guardadas no cofre (estado atual, como o equipamento).
        # Toda carta que o personagem tem e não está aqui está no loadout.
        self.cofre: list[str] = []
        # Nível máximo permitido pela mesa (None: sem mesa, sem limite). Estado
        # atual: quem carrega o personagem define DEPOIS de refazer o histórico.
        self.nivel_limite: int | None = None
        # Níveis planejados (ainda não aplicados), em ordem a partir do próximo.
        # Vêm de uma cópia para uma mesa de nível menor.
        self.plano: list[SubidaDeNivel] = []
        # Ouro, itens e armas guardadas (estado atual; motor/inventario.py)
        self.inventario = Inventario()
        # Regra opcional das moedas definida pela mesa (None: sem mesa, vale a
        # escolha do próprio inventário). Como o nível limite, quem carrega define.
        self.moedas_da_mesa: bool | None = None
        # recarregando níveis já salvos (refazer_historico): não exige o que uma
        # regra nova passou a pedir depois (ex.: a escolha da Vitality)
        self._refazendo = False
        self._ficha_inicial = self._criar(criacao)
        if criacao.pocao_inicial or criacao.item_de_classe:
            self.inventario = inventario_inicial(biblioteca, criacao.classe, criacao.pocao_inicial or "",
                                                 criacao.item_de_classe or "")
        self.sessao = Sessao(self, esperanca=self._ficha_inicial.esperanca)

    # --- API pública -------------------------------------------------------

    def ficha(self, ate_nivel: int | None = None) -> Ficha:
        """Refaz o histórico e aplica o estado ATUAL (equipamento, cofre e
        sessão) por cima.

        Por isso ficha(ate_nivel=3) mostra o nível 3 com o equipamento de hoje.
        """
        f = self._vestir(self._ficha_base(ate_nivel), self.equipamento)
        f.cartas_cofre = [c for c in f.cartas if c in self.cofre]
        f.cartas_ativas = [c for c in f.cartas if c not in self.cofre]
        s = self.sessao
        # min(): numa ficha de nível passado os máximos podem ser menores
        f.pv_marcados = min(s.pv_marcados, f.pv_max)
        f.estresse_marcado = min(s.estresse_marcado, f.estresse_max)
        f.armadura_marcada = min(s.armadura_marcada, f.pontuacao_armadura)
        f.esperanca = s.esperanca
        f.condicoes = list(s.condicoes)
        # Reinforced: com o último espaço marcado, limiares +2 até limpar um espaço
        if (Efeito.REFORCADA in self.efeitos_ativos()
                and 0 < f.pontuacao_armadura <= f.armadura_marcada):
            f.limiar_maior += 2
            f.limiar_grave += 2
        f.esperanca_max = self.bib.progressao["limite_esperanca"]
        f.inconsciente, f.morto = s.inconsciente, s.morto
        f.cicatrizes = list(s.cicatrizes)
        f.padroes_estranhos = s.padroes_estranhos
        if f.companheiro:
            c = f.companheiro
            if c.tem(OpcaoTreino.LUZ_NA_ESCURIDAO):
                f.esperanca_max += 1   # Light in the Dark: espaço de Esperança extra
            c.dano = f"{f.proficiencia}{c.dado}"   # usa a sua Proficiência
            c.estresse_marcado = min(s.companheiro_estresse, c.estresse_max)
            c.fora_de_cena = s.companheiro_fora
        f.esperanca_max = max(f.esperanca_max - len(s.cicatrizes), 0)   # espaços riscados
        f.precisa_movimento_de_morte = f.pv_marcados >= f.pv_max and not s.inconsciente and not s.morto
        mao = set(f.cartas_ativas)
        f.defesas_de_carta = [DefesaDeCarta(c, self.bib.cartas[c].nome, *custo) for c, custo in DEFESAS_DE_CARTAS.items()
                              if c in mao and f"carta:{c}" not in s.usos_rolagem]
        f.alternativas_a_morte = [c for c in ALTERNATIVAS_A_MORTE if c in mao and f"carta:{c}" not in s.usos_rolagem]
        return f

    def cartas_na_mao(self) -> list[str]:
        return [c for c in self._ficha_base().cartas if c not in self.cofre]

    def subir_de_nivel(self, subida: SubidaDeNivel) -> Ficha:
        """Valida e registra o nível. Se algo for inválido, nada muda.

        Cartas novas vão para a mão; se ela estiver cheia, para a reserva, a
        menos que `para_reserva` mande cartas antigas no lugar delas.
        """
        if self.nivel_limite is not None and subida.nivel > self.nivel_limite:
            raise RegraViolada(f"A mesa está no nível {self.nivel_limite}: o mestre ainda não "
                               f"liberou o nível {subida.nivel}.")
        base = self._ficha_base()
        nova = self._vestir(self._aplicar(base, subida), self.equipamento)
        if not self._refazendo:
            for c in nova.cartas:
                carta = self.bib.cartas[c]
                if c not in base.cartas and carta.escolha and not subida.beneficios_de_carta.get(c):
                    raise RegraViolada(f"{carta.nome}: escolha os benefícios da carta.")
        # ex.: subir a Presença com uma arma Pompous equipada
        self._validar_requisitos(nova, self.equipamento)
        self._validar_para_reserva(subida, cartas_antes=self._ficha_base().cartas, cartas_depois=nova.cartas)
        self.historico.append(subida)
        if subida.troca_carta and subida.troca_carta[0] in self.cofre:
            antiga, nova_carta = subida.troca_carta   # a nova ocupa o lugar da antiga
            self.cofre[self.cofre.index(antiga)] = nova_carta
        # sem custo; já estar na reserva não é erro (ao recarregar, o histórico
        # é refeito com uma reserva que pode diferir da real, restaurada depois)
        self.cofre += [c for c in subida.para_reserva if c not in self.cofre]
        self._ajustar_cofre()
        # o que estava planejado para este nível (ou antes) foi superado
        self.plano = [s for s in self.plano if s.nivel > subida.nivel]
        return self.ficha()

    def refazer_historico(self, subidas: list[SubidaDeNivel]):
        """Recarrega níveis já salvos. Um nível salvo antes de uma carta passar a
        pedir escolha (Vitality, Master of the Craft) entra sem o benefício, em vez
        de deixar o personagem sem abrir; uma subida nova continua exigindo."""
        self._refazendo = True
        try:
            for subida in subidas:
                self.subir_de_nivel(subida)
        finally:
            self._refazendo = False

    # --- Plano e cópia -------------------------------------------------------

    def aplicar_plano(self) -> Ficha:
        """Sobe o próximo nível com o que está planejado para ele (validado como
        qualquer subida; se não valer mais, o plano fica e o erro sobe)."""
        proximo = len(self.historico) + 2
        if not self.plano or self.plano[0].nivel != proximo:
            raise RegraViolada(f"Não há plano para o nível {proximo}.")
        return self.subir_de_nivel(self.plano[0])

    def descartar_plano(self, nivel: int):
        """Tira do plano o nível `nivel` (para escolher outra coisa nele)."""
        if not any(s.nivel == nivel for s in self.plano):
            raise RegraViolada(f"Não há plano para o nível {nivel}.")
        self.plano = [s for s in self.plano if s.nivel != nivel]

    def copia(self, nivel_maximo: int | None = None) -> "Personagem":
        """Cópia para outra mesa: mesma criação e histórico até `nivel_maximo`;
        os níveis acima (e o plano que já existia) viram plano. Equipamento,
        reserva e inventário vão junto quando ainda valem; marcas de sessão começam zeradas."""
        nova = Personagem(self.bib, self.criacao)
        corte = nivel_maximo if nivel_maximo is not None else len(self.historico) + 1
        nova.refazer_historico([copy.deepcopy(s) for s in self.historico if s.nivel <= corte])
        nova.plano = [copy.deepcopy(s) for s in self.historico if s.nivel > corte] + copy.deepcopy(self.plano)
        try:
            nova.equipar(**dataclasses.asdict(self.equipamento))
        except RegraViolada:
            pass   # ex.: arma mágica sem a multiclasse que ficou no plano: vai sem equipamento
        nova.cofre = [c for c in self.cofre if c in nova._ficha_base().cartas]
        nova._ajustar_cofre()
        nova.inventario = copy.deepcopy(self.inventario)
        nova._usar_proprios()
        nova.nivel_limite = nivel_maximo
        return nova

    def _validar_para_reserva(self, subida: SubidaDeNivel, cartas_antes: list[str], cartas_depois: list[str]):
        if not subida.para_reserva:
            return
        if len(set(subida.para_reserva)) != len(subida.para_reserva):
            raise RegraViolada("Escolha cartas diferentes para mandar para a reserva.")
        novas = len(cartas_depois) - len(cartas_antes)
        if len(subida.para_reserva) > novas:
            raise RegraViolada(f"Neste nível você ganha {novas} carta(s): mande no máximo "
                               f"{novas} para a reserva.")
        saindo = subida.troca_carta[0] if subida.troca_carta else None
        for c in subida.para_reserva:
            if c not in cartas_antes or c == saindo:
                raise RegraViolada("Só vão para a reserva cartas que você já tinha e que continuam com você.")

    def equipar(self, principal: str | None = None, secundaria: str | None = None,
                armadura: str | None = None, traco_principal: Traco | str | None = None,
                traco_secundaria: Traco | str | None = None) -> Ficha:
        """Define o equipamento completo; o que não for passado fica vazio.

        `traco_*`: Versatile Fighter (o atributo do ataque com aquela arma; só
        vale com a carta na mão). Igual ao da arma, ou sem arma, fica vazio.
        Tudo é validado antes de trocar, então um erro não muda nada.
        """
        def traco(arma_id, valor):
            if not valor or not arma_id or arma_id not in self.bib.armas:
                return None
            valor = Traco(valor)
            return None if valor is self.bib.armas[arma_id].traco else valor
        novo = Equipamento(principal, secundaria, armadura,
                           traco(principal, traco_principal), traco(secundaria, traco_secundaria))
        base = self._ficha_base()
        self._validar_equipamento(base, novo)
        self._validar_requisitos(self._vestir(base, novo), novo)
        self.equipamento = novo
        self.sessao.ajustar()   # armadura nova pode ter menos espaços
        return self.ficha()

    def estado(self) -> dict:
        """Estado atual (fora do histórico) em tipos simples, para salvar."""
        return {
            "equipamento": {k: v.value if isinstance(v, Traco) else v
                        for k, v in dataclasses.asdict(self.equipamento).items()},
            "cofre": list(self.cofre),
            "sessao": self.sessao.estado(),
            "inventario": self.inventario.estado(),
        }

    def restaurar_estado(self, estado: dict):
        """Inverso de estado(). O equipamento passa por equipar(), então
        continua valendo a validação (ex.: arma mágica, Pompous)."""
        self.inventario = Inventario.de_estado(estado.get("inventario"))
        self._usar_proprios()   # antes do equipamento: ele pode ser um item do mestre
        self.equipar(**estado["equipamento"])
        self.cofre = list(estado["cofre"])
        self._ajustar_cofre()
        self.sessao.restaurar(estado["sessao"])

    # --- inventário ----------------------------------------------------------------

    @property
    def usa_moedas(self) -> bool:
        return self.moedas_da_mesa if self.moedas_da_mesa is not None else self.inventario.usar_moedas

    def usar_consumivel(self, item_id: str, rolagem: int | None = None,
                        escolha: str | None = None) -> list[str]:
        """Usa 1 consumível. Os de efeito simples (PV, PF, Esperança) já mexem
        na ficha: `rolagem` é o resultado do dado (sem ela, o motor rola) e
        `escolha` ("PV" ou "PF") decide quando o item dá uma ou outra.
        Devolve o que aconteceu, para mostrar na tela. Erro não muda nada."""
        item = self.bib.itens.get(item_id)
        if item is None or item.tipo is not TipoDeItem.CONSUMIVEL:
            raise RegraViolada("Isso não é um consumível.")
        if self.inventario.itens.get(item_id, 0) < 1:
            raise RegraViolada(f"Você não tem {item.nome}.")
        ef, s = item.efeito, self.sessao
        notas = [f"Usou {item.nome}."]
        if ef is None:
            self.inventario.remover(self.bib, item_id)
            return notas
        pv, pf = ef.limpa_pv, ef.limpa_pf
        if ef.escolha:
            if escolha not in ("PV", "PF"):
                raise RegraViolada(f"{item.nome}: escolha limpar PV ou PF.")
            pv, pf = (pv, None) if escolha == "PV" else (None, pf)
        dado = dataclasses.replace(ef, limpa_pv=pv, limpa_pf=pf).dado   # só o lado escolhido
        valor_dado = _rolar(dado, rolagem, s.rng) if dado else None
        if ef.marca_pf and s.estresse_livre < ef.marca_pf:
            raise RegraViolada(f"Fadiga insuficiente: {item.nome} custa {ef.marca_pf} PF.")

        def quanto(q: str, maximo: int) -> int:
            if q == "tudo":
                return maximo
            return valor_dado if q == dado else int(q)

        if ef.marca_pf:
            s.pagar_estresse(ef.marca_pf)
            notas.append(f"Marcou {ef.marca_pf} PF.")
        if pv:
            n = min(quanto(pv, s.pv_marcados), s.pv_marcados)
            s.limpar_pv(n)
            notas.append(f"Limpou {n} PV.")
        if pf:
            n = min(quanto(pf, s.estresse_marcado), s.estresse_marcado)
            s.limpar_estresse(n)
            notas.append(f"Limpou {n} PF.")
        if ef.ganha_esperanca:
            antes = s.esperanca
            s.ganhar_esperanca(quanto(ef.ganha_esperanca, 0))
            notas.append(f"Ganhou {s.esperanca - antes} de Esperança.")
        if valor_dado is not None:
            notas.insert(1, f"Rolagem: {dado} = {valor_dado}.")
        self.inventario.remover(self.bib, item_id)
        return notas

    def trocar_arma(self, indice: int, em_perigo: bool) -> Ficha:
        """Troca a arma de inventário `indice` pela arma ativa do mesmo tipo
        (principal ou secundária). SRD: só entre armas da mesma empunhadura;
        grátis num descanso ou momento de calma, senão marca 1 PF."""
        inv = self.inventario
        if not 0 <= indice < len(inv.armas):
            raise RegraViolada("Não há arma nessa posição do inventário.")
        guardada = self.bib.armas[inv.armas[indice]]
        eq = self.equipamento
        lugar = "principal" if guardada.primaria else "secundaria"
        ativa_id = getattr(eq, lugar)
        if ativa_id and self.bib.armas[ativa_id].duas_maos != guardada.duas_maos:
            raise RegraViolada("Só dá para trocar por uma arma ativa da mesma empunhadura "
                               "(uma mão por uma mão, duas mãos por duas mãos).")
        if em_perigo and self.sessao.estresse_livre < 1:
            raise RegraViolada("Fadiga insuficiente: trocar de arma em perigo custa 1 PF.")
        # arma nova: o atributo da Versatilidade volta ao dela
        novo = dataclasses.replace(eq, **{lugar: guardada.id, f"traco_{lugar}": None})
        self.equipar(**dataclasses.asdict(novo))   # valida (arma mágica, duas mãos...)
        if ativa_id:
            inv.armas[indice] = ativa_id
        else:
            del inv.armas[indice]
        if em_perigo:
            self.sessao.pagar_estresse(1)
        return self.ficha()

    def receber_item_proprio(self, item: ItemProprio, quantidade: int = 1) -> str:
        """Entrega um item criado pelo mestre (presente, tesouro ou compra): o
        personagem guarda uma cópia dele, que vai para o inventário como os do
        SRD (arma nas armas guardadas; armadura é vestida na hora). Devolve o id
        da cópia. Erro não muda nada."""
        if quantidade < 1:
            raise RegraViolada("A quantidade precisa ser pelo menos 1.")
        if item.tipo is TipoProprio.ARMADURA and quantidade != 1:
            raise RegraViolada("Armadura se entrega uma por vez (ela é vestida na hora).")
        recebido = copia_proprio(item)
        antes = (copy.deepcopy(self.inventario), self.equipamento, self.sessao.armadura_marcada)
        self.inventario.proprios[recebido.id] = recebido.estado()
        self._usar_proprios()
        try:
            if item.tipo is TipoProprio.ARMA:
                for _ in range(quantidade):
                    self.inventario.guardar_arma(self.bib, recebido.id)
            elif item.tipo is TipoProprio.ARMADURA:
                self.vestir_armadura_nova(recebido.id)
            else:
                self.inventario.adicionar(self.bib, recebido.id, quantidade)
        except RegraViolada:
            self.inventario, self.equipamento, self.sessao.armadura_marcada = antes
            self._usar_proprios()
            raise
        return recebido.id

    def armas_proprias(self) -> list[Arma]:
        """Armas criadas pelo mestre que o personagem já recebeu (para equipar)."""
        return [self.bib.armas[i] for i in self.inventario.proprios if i in self.bib.armas]

    def armaduras_proprias(self) -> list[Armadura]:
        return [self.bib.armaduras[i] for i in self.inventario.proprios if i in self.bib.armaduras]

    def _usar_proprios(self):
        """A Biblioteca deste personagem: o SRD mais as cópias dos itens do mestre."""
        self.bib = self.bib.base.com_itens(**separar_proprios(self.inventario.proprios))

    def vestir_armadura_nova(self, armadura_id: str) -> Ficha:
        """Armadura comprada: vai direto para o corpo (o SRD não deixa carregar
        armadura no inventário) e a antiga fica para trás. Começa sem marcas."""
        eq = dataclasses.replace(self.equipamento, armadura=armadura_id)
        self.equipar(**dataclasses.asdict(eq))
        self.sessao.armadura_marcada = 0
        return self.ficha()

    def desfazer_ultimo_nivel(self) -> None:
        if not self.historico:
            raise RegraViolada("Não há nível para desfazer.")
        desfeita = self.historico.pop()
        # o que foi para a reserva por causa deste nível volta para a mão
        self.cofre = [c for c in self.cofre if c not in desfeita.para_reserva]
        self._ajustar_cofre()
        self.sessao.ajustar()   # PV/Estresse máximos podem ter caído

    # --- Cartas: o que dá para escolher no próximo nível ---------------------

    def cartas_para_nivel(self, escolhas: list[Escolha] = ()) -> list[CartaDeDominio]:
        """Opções para a carta obrigatória do próximo nível (passo 4).

        Passe os avanços já marcados neste nível em `escolhas`: uma multiclasse
        libera o domínio novo e a carta do avanço CARTA_DOMINIO sai da lista.
        """
        f, proximo = self._ficha_com_escolhas(escolhas)
        return self._listar_cartas(f, proximo, proximo)

    def cartas_para_avanco(self, tier: int | None = None) -> list[CartaDeDominio]:
        """Opções para o avanço CARTA_DOMINIO do próximo nível.

        `tier` é o tier do quadradinho usado (padrão: o do próximo nível); ele
        define o nível máximo da carta (4, 7 ou 10).
        """
        f, proximo = self._ficha_com_escolhas(())
        tier = tier or self.bib.tier_do_nivel(proximo)
        return self._listar_cartas(f, self._limite_carta_extra(tier, proximo), proximo)

    def cartas_para_troca(self, antiga: str, escolhas: list[Escolha] = (),
                          carta_do_nivel: str | None = None) -> list[CartaDeDominio]:
        """Opções para trocar `antiga` no próximo nível (nível igual ou menor que ela).

        `carta_do_nivel` é a carta já escolhida no passo 4, que sai da lista.
        """
        f, proximo = self._ficha_com_escolhas(escolhas)
        if antiga not in f.cartas:
            raise RegraViolada("Você só pode trocar uma carta que já tem.")
        if carta_do_nivel:
            f.cartas.append(carta_do_nivel)
        return self._listar_cartas(f, self.bib.cartas[antiga].nivel, proximo)

    # --- Rolagens (motor/rolagem.py e data/efeitos_de_rolagem.json) -----------------

    def _valores(self, f: Ficha, n: int = 0) -> dict[str, int]:
        """O que as referências do catálogo podem usar (nivel, patamar, atributos, n...)."""
        v: dict[str, int] = {t.value: f.tracos[t] for t in Traco}
        v.update(nivel=f.nivel, patamar=self.bib.tier_do_nivel(f.nivel), proficiencia=f.proficiencia, n=n,
                 conjuracao=max((f.tracos[c.traco] for c in f.conjuracoes), default=0))
        if self.equipamento.secundaria:
            v["secundaria"] = int(re.search(r"d(\d+)", self.bib.armas[self.equipamento.secundaria].dado).group(1))
        for nome, q in self.sessao.marcadores_rolagem.items():
            v[f"marcador:{nome}"] = q
        return v

    def _fontes(self, f: Ficha, ataque: int | None) -> dict[tuple[str, str], str]:
        """(tipo, nome em inglês ou id da carta) -> nome exibido, de tudo o que o personagem tem."""
        fontes = {("habilidade", h.nome_original): h.nome for h in f.habilidades}
        fontes |= {("ancestralidade", c.nome_original): c.nome for c in f.caracteristicas_ancestralidade}
        fontes |= {("comunidade", c.nome_original): c.nome for c in f.caracteristicas_comunidade}
        fontes |= {("armadura", c.nome_original): c.nome for c in f.caracteristicas_armadura}
        fontes |= {("carta", c): self.bib.cartas[c].nome for c in f.cartas_ativas}
        if ataque is not None and 0 <= ataque < len(f.ataques):
            fontes |= {("arma", c.nome_original): c.nome for c in f.ataques[ataque].caracteristicas}
        return fontes

    def _condicao(self, chave: str | None, f: Ficha, ataque: int | None, carta: str | None) -> str | None:
        """None se a condição automática vale; senão, o motivo (para a tela)."""
        if not chave:
            return None
        a = f.ataques[ataque] if ataque is not None and 0 <= ataque < len(f.ataques) else None
        ua = self.sessao.ultimo_ataque
        for parte in chave.split("+"):
            if parte == "pv_baixo" and f.pv_max - f.pv_marcados > 2:
                return "só com 2 PV ou menos sem marcar"
            if parte == "vulneravel" and "VULNERAVEL" not in f.condicoes:
                return "só Vulnerável"
            if parte == "fadiga_cheia" and f.estresse_marcado < f.estresse_max:
                return "só com toda a Fadiga marcada"
            if parte == "arma" and a is None:
                return "só no dano de uma arma"
            if parte == "arma_corpo_a_corpo" and (a is None or a.alcance != "MELEE"):
                return "só com arma corpo a corpo"
            if parte == "dano_magico" and not (carta or (a and a.tipo_dano is not TipoDano.FISICO)):
                return "só com dano mágico"
            if parte == "secundaria" and not self.equipamento.secundaria:
                return "precisa de uma arma secundária equipada"
            if parte.startswith("dominio:"):
                dominio = parte.split(":", 1)[1]
                if sum(1 for c in f.cartas_ativas if self.bib.cartas[c].dominio == dominio) < 4:
                    return f"precisa de 4 cartas de {self.bib.nome_dominio(dominio)} na mão"
            if parte == "ultimo_ataque" and ua is None:
                return "depois de um ataque nesta sessão"
            if parte == "ultimo_ataque_com_medo" and (ua or {}).get("dualidade") != "medo":
                return "o último ataque não foi com Medo"
            if parte == "ultimo_ataque_com_esperanca" and (ua or {}).get("dualidade") != "esperanca":
                return "o último ataque não foi com Esperança"
        return None

    def opcoes_de_rolagem(self, tipo: str, traco: str | None = None, ataque: int | None = None,
                          carta: str | None = None) -> list[OpcaoDeRolagem]:
        """Os efeitos do catálogo que valem para esta rolagem (`tipo`: teste, ataque,
        conjuracao, reacao, dano), com nome, custo e se dá para usar agora."""
        f = self.ficha()
        fontes = self._fontes(f, ataque)
        valores = self._valores(f)
        tem = {e.id: e for e in self.bib.efeitos_rolagem.values()
               if tipo in e.rolagens and (e.fonte_tipo, e.fonte) in fontes
               and (not e.atributos or traco in e.atributos)}
        saida = []
        for e in tem.values():
            if any(s in tem for s in e.substituido_por):
                continue   # ex.: Encare o Medo some quando há Movido por Medo
            motivo = self._condicao(e.auto, f, ataque, carta)
            if e.momento == "automatico" and motivo:
                continue
            if motivo is None and e.limite and e.id in self.sessao.usos_rolagem:
                motivo = {"sessao": "já usado nesta sessão", "descanso": "já usado (volta no descanso)",
                          "descanso_longo": "já usado (volta no descanso longo)"}[e.limite]
            maximo = None
            if e.quantidade is not None:
                maximo = resolver(e.quantidade, valores) if not str(e.quantidade).startswith("marcador:") \
                    else self.sessao.marcadores_rolagem.get(str(e.quantidade).split(":", 1)[1], 0)
                if maximo < 1 and motivo is None:
                    motivo = "nada para gastar agora"
            saida.append(OpcaoDeRolagem(
                id=e.id, nome=fontes[(e.fonte_tipo, e.fonte)], momento=e.momento, condicao=e.condicao,
                custo_esperanca=e.custo_esperanca, custo_fadiga=e.custo_fadiga, por_unidade=e.custo_por_unidade,
                limite=e.limite, quantidade_max=maximo, escolha=list(e.escolha), alvo=e.alvo, se=e.se,
                disponivel=motivo is None, motivo=motivo or ""))
        return sorted(saida, key=lambda o: (o.momento != "automatico", o.nome))

    def _escolhidas(self, tipo: str, traco: str | None, ataque: int | None, carta: str | None,
                    opcoes) -> tuple[list[tuple[EfeitoDeRolagem, OpcaoDeRolagem, int, str | None]], list]:
        """(efeito, opção, quantidade, escolha) das opções pedidas + os automáticos. Valida tudo."""
        disponiveis = {o.id: o for o in self.opcoes_de_rolagem(tipo, traco, ataque, carta)}
        usadas = []
        for pedida in opcoes:
            o = disponiveis.get(pedida.id)
            if o is None or o.momento != "antes":
                raise RegraViolada("Essa opção não vale para esta rolagem.")
            if not o.disponivel:
                raise RegraViolada(f"{o.nome}: {o.motivo}.")
            q = pedida.quantidade or 1
            if o.quantidade_max is not None and not 1 <= q <= o.quantidade_max:
                raise RegraViolada(f"{o.nome}: escolha de 1 a {o.quantidade_max}.")
            if o.escolha and pedida.escolha not in o.escolha:
                raise RegraViolada(f"{o.nome}: escolha uma das opções.")
            usadas.append((self.bib.efeitos_rolagem[o.id], o, q, pedida.escolha))
        automaticos = [(self.bib.efeitos_rolagem[o.id], o, 1, None) for o in disponiveis.values()
                       if o.momento == "automatico"]
        return usadas, automaticos

    def _pagar(self, usadas, esperanca_extra: int = 0, fadiga_extra: int = 0):
        """Paga os custos das opções (e das Experiências) de uma vez: sem saldo, nada muda."""
        esperanca = esperanca_extra + sum(e.custo_esperanca * (q if e.custo_por_unidade else 1) for e, _, q, _ in usadas)
        fadiga = fadiga_extra + sum(e.custo_fadiga * (q if e.custo_por_unidade else 1) for e, _, q, _ in usadas)
        s = self.sessao
        if esperanca > s.esperanca:
            raise RegraViolada(f"Esperança insuficiente: precisa de {esperanca}, você tem {s.esperanca}.")
        if fadiga > s.estresse_livre:
            raise RegraViolada(f"Fadiga insuficiente: precisa de {fadiga} PF livres, você tem {s.estresse_livre}.")
        if esperanca:
            s.gastar_esperanca(esperanca)
        if fadiga:
            s.pagar_estresse(fadiga)
        for e, _, _, _ in usadas:
            if e.limite:
                s.usos_rolagem[e.id] = e.limite

    def rolar_teste(self, tipo: str, alvo: str | int | None = None, experiencias: list[str] = (),
                    vantagem: bool = False, desvantagem: bool = False, dificuldade: int | None = None,
                    reacao: bool = False, opcoes=(), somar: str = "") -> ResultadoRolagem:
        """Teste com os Dados de Dualidade. `tipo`: "atributo" (alvo: o atributo),
        "ataque" (alvo: índice em ficha.ataques) ou "conjuracao" (índice em
        ficha.conjuracoes). Custos (Experiências, opções) são pagos antes; o
        resultado (Esperança, Medo, crítico e os efeitos do catálogo) já vai para a sessão.
        `somar`: dados de fora (Dado de Inspiração, de Oração...), ex.: "1d8"."""
        f = self.ficha()
        ataque = None
        if tipo == "atributo":
            t = Traco(alvo)
            titulo, bonus = f"Teste de {t.rotulo}", [Bonus(t.rotulo, f.tracos[t])]
        elif tipo == "ataque":
            a = self._da_lista(f.ataques, alvo, "Arma equipada")
            ataque, t = alvo, a.traco
            titulo, bonus = f"Ataque: {a.arma}", [Bonus(f"{a.arma} ({a.traco.rotulo})", a.bonus)]
        elif tipo == "conjuracao":
            c = self._da_lista(f.conjuracoes, alvo, "Conjuração")
            t = c.traco
            titulo, bonus = "Teste de Conjuração", [Bonus(f"Conjuração ({c.traco.rotulo})", c.bonus)]
        else:
            raise RegraViolada(f"Tipo de teste desconhecido: {tipo}.")
        tipo_rolagem = "reacao" if reacao else ("teste" if tipo == "atributo" else tipo)
        if reacao:
            titulo = titulo.replace("Teste de ", "Reação: ")
        usadas, automaticos = self._escolhidas(tipo_rolagem, t.value, ataque, None, opcoes)
        tipos = {x["tipo"] for e, _, _, _ in usadas + automaticos for x in e.efeitos}
        nomes = [o.nome for _, o, _, _ in usadas + automaticos]

        # Experiências: 1 Esperança cada; Adepto troca por 1 PF e dobra; Bem Vivido: d6 5+ sai de graça
        exps = list(dict.fromkeys(experiencias))
        for nome in exps:
            if nome not in f.experiencias:
                raise RegraViolada(f"Você não tem a Experiência '{nome}'.")
        notas, pagas = [], 0
        for nome in exps:
            if "experiencia_d6_gratis" in tipos:
                d6 = self.sessao.rng.randint(1, 6)
                if d6 >= 5:
                    notas.append(f"Bem Vivido (d6 {d6}): {nome} sem custo.")
                    continue
                notas.append(f"Bem Vivido (d6 {d6}): {nome} paga o custo.")
            pagas += 1
        adepto = "experiencia_com_fadiga" in tipos
        self._pagar(usadas, esperanca_extra=0 if adepto else pagas, fadiga_extra=pagas if adepto else 0)
        if pagas:
            notas.insert(0, f"Experiências: {pagas} {'PF' if adepto else 'de Esperança'}.")
        bonus += [Bonus(f"Experiência: {n}", f.experiencias[n] * (2 if adepto else 1)) for n in exps]

        # efeitos antes de rolar
        valores = self._valores(f)
        extras: list[tuple[str, str]] = [("Somar", somar.strip())] if somar.strip() else []
        soma_no_dado: dict[str, int] = {}
        faces_esperanca, limpa_no_sucesso = 12, False
        for e, o, q, escolha in usadas + automaticos:
            valores["n"] = q
            for x in e.efeitos:
                if x["tipo"] == "bonus":
                    bonus.append(Bonus(o.nome, resolver(x.get("ref", x.get("valor", 0)), valores)))
                elif x["tipo"] == "dados":
                    extras.append((o.nome, expandir(x["expr"], valores)))
                elif x["tipo"] == "vantagem":
                    vantagem = True
                elif x["tipo"] == "desvantagem":
                    desvantagem = True
                elif x["tipo"] == "ignora_desvantagem":
                    desvantagem = False
                elif x["tipo"] == "dado_esperanca":
                    faces_esperanca = max(faces_esperanca, x["faces"])
                elif x["tipo"] == "dobra_atributo":
                    bonus.append(Bonus(f"{o.nome} (dobro)", f.tracos[t]))
                elif x["tipo"] == "soma_no_dado":
                    soma_no_dado[escolha] = soma_no_dado.get(escolha, 0) + x["valor"]
                elif x["tipo"] == "limpa_fadiga_no_sucesso":
                    limpa_no_sucesso = True
                elif x["tipo"] == "gasta_marcador":
                    self.sessao.marcadores_rolagem[x["marcador"]] -= q
        if any(x["tipo"] == "ignora_desvantagem" for e, _, _, _ in automaticos for x in e.efeitos):
            desvantagem = False
        if self.sessao.proxima_vantagem and not reacao and any(
                x["tipo"] == "vantagem_apos_falha" for e, _, _, _ in automaticos for x in e.efeitos):
            vantagem, self.sessao.proxima_vantagem = True, False
            notas.append("Inevitável: vantagem depois da falha.")

        r = rolar_teste(titulo, bonus, self.sessao.rng, vantagem, desvantagem, dificuldade, reacao, faces_esperanca)
        if faces_esperanca == 20:
            notas.append("Dado de Esperança d20.")
        r.soma_no_dado, r.limpa_fadiga_no_sucesso = soma_no_dado, limpa_no_sucesso
        for fonte, expressao in extras:
            for sinal, n, faces in ler_expressao(expressao)[0]:
                for _ in range(n):
                    valor = self.sessao.rng.randint(1, faces)
                    r.dados.append(DadoRolado(faces, valor * sinal, PapelDoDado.EXTRA, fonte=fonte))
            constante = ler_expressao(expressao)[1]
            if constante:
                r.bonus.append(Bonus(fonte, constante))
        recalcular_teste(r)
        r.tipo, r.traco, r.experiencias, r.opcoes, r.ataque = tipo_rolagem, t.value, len(exps), nomes, ataque
        self._pos_teste(r, automaticos)
        r.efeitos = notas + r.efeitos
        if tipo == "ataque":
            self.sessao.ultimo_ataque = {"dualidade": r.dualidade.value, "medo": dado(r, PapelDoDado.MEDO).valor,
                                         "critico": r.dualidade is Dualidade.CRITICO, "sucesso": r.sucesso, "arma": ataque}
            for e, o, _, _ in automaticos:
                for x in e.efeitos:
                    if x["tipo"] == "nota_d6" and self.sessao.rng.randint(1, 6) == x["valor"]:
                        r.efeitos.append(f"{o.nome}: {x['nota']}.")
        return r

    def _pos_teste(self, r: ResultadoRolagem, automaticos):
        """O que o resultado do teste aplica: Esperança/Medo/crítico, Padrões
        Estranhos e os automáticos que dependem do resultado (Coragem, marcadores...)."""
        tipos = {x["tipo"]: (o, x) for e, o, _, _ in automaticos for x in e.efeitos}
        if "rerrola_esperanca_1" in tipos and dado(r, PapelDoDado.ESPERANCA).valor == 1:
            rolar_dualidade(r, self.sessao.rng, ("esperanca",))
            r.efeitos.append(f"{tipos['rerrola_esperanca_1'][0].nome}: rerrolou o 1 no Dado de Esperança.")
        f = self.ficha()
        padroes = self.sessao.padroes_estranhos if self._tem_habilidade(f, "Strange Patterns") else None
        aplicar_teste(r, self.sessao, padroes)
        if "esperanca_falha_com_medo" in tipos and r.sucesso is False and r.dualidade is Dualidade.MEDO \
                and not r.reacao:
            _ganhar_esperanca(r, self.sessao, tipos["esperanca_falha_com_medo"][0].nome)
        if "marcador_no_medo" in tipos and r.dualidade is Dualidade.MEDO:
            o, x = tipos["marcador_no_medo"]
            atual = self.sessao.marcadores_rolagem.get(x["marcador"], 0)
            if atual < resolver(x["max"], self._valores(f)):
                self.sessao.marcadores_rolagem[x["marcador"]] = atual + 1
                _delta(r, f"marcador:{x['marcador']}", 1)
                r.efeitos.append(f"{o.nome}: +1 marcador ({atual + 1}).")
        if "vantagem_apos_falha" in tipos and r.sucesso is False and not r.reacao:
            self.sessao.proxima_vantagem = True
            _delta(r, "proxima_vantagem", 1)
            r.efeitos.append(f"{tipos['vantagem_apos_falha'][0].nome}: o próximo teste de ação tem vantagem.")

    def rolar_dano(self, ataque: int | None = None, carta: str | None = None, formula: int = 0,
                   critico: bool = False, extra: str = "", opcoes=()) -> ResultadoRolagem:
        """Dano da arma (a expressão da ficha) ou de uma fórmula de carta da mão
        (com "using your Proficiency", tantos dados quanto a Proficiência), com
        os efeitos do catálogo (Poderoso, Brutal, Ataque Furtivo...). `extra`
        soma dados ou números; `critico`, o máximo dos dados."""
        f = self.ficha()
        if carta is not None:
            if carta not in f.cartas_ativas:
                raise RegraViolada("Só dá para rolar cartas que estão na sua mão.")
            c = self.bib.cartas[carta]
            fr = self._da_lista(list(c.formulas), formula, "Rolagem da carta")
            plano = PlanoDeDano(f"Dano: {c.nome}", fr.expressao(f.proficiencia), principal=fr.dados == 0)
        else:
            a = self._da_lista(f.ataques, ataque, "Arma equipada")
            plano = PlanoDeDano(f"Dano: {a.arma}", a.dano)
        plano.critico = critico
        if extra.strip():
            ler_expressao(extra)   # valida antes de pagar qualquer custo
            plano.extras.append(("Extra", extra.strip().lstrip("+")))
        usadas, automaticos = self._escolhidas("dano", None, ataque, carta, opcoes)
        self._pagar(usadas)
        valores = self._valores(f)
        notas, pos = [], []
        for e, o, q, _ in usadas + automaticos:
            valores["n"] = q
            for x in e.efeitos:
                t = x["tipo"]
                if t == "bonus":
                    plano.bonus.append(Bonus(o.nome, resolver(x.get("ref", x.get("valor", 0)), valores)))
                elif t == "dados":
                    plano.extras.append((o.nome, expandir(x["expr"], valores)))
                elif t == "proficiencia":
                    if plano.principal:
                        plano.proficiencia_extra += x["valor"]
                    else:
                        notas.append(f"{o.nome}: esta rolagem não usa a Proficiência.")
                elif t == "dado_de_dano":
                    plano.faces_do_dado = x["faces"]
                elif t == "dado_extra_descarta_menor":
                    plano.descarta_menor += 1
                elif t == "explode_maximo":
                    plano.explode = True
                elif t == "troca_valor":
                    plano.troca_valor[x["de"]] = x["para"]
                elif t == "rerrola_valores":
                    plano.rerrola_valores = tuple(x["valores"])
                elif t == "dobra_iguais":
                    plano.dobra_iguais = True
                elif t == "dobra_maior_dado":
                    plano.dobra_maior = True
                elif t == "multiplica_dano":
                    plano.multiplica *= x["fator"]
                elif t == "soma_dado_medo_do_ataque":
                    plano.bonus.append(Bonus(o.nome, (self.sessao.ultimo_ataque or {}).get("medo", 0)))
                elif t == "nota_valor":
                    plano.notas_valor.append((x["valor"], f"{o.nome}: {x['nota']}."))
                elif t == "rolagem_extra":
                    pos.append((o, x))
        r = rolar_dano(plano, self.sessao.rng)
        r.opcoes, r.ataque, r.carta = [o.nome for _, o, _, _ in usadas + automaticos], ataque, carta
        r.efeitos = notas + r.efeitos
        for o, x in pos:   # Revigorante, Rouba-Vida: um dado à parte depois do acerto
            valor = self.sessao.rng.randint(1, x["faces"])
            if valor != x["alvo"]:
                r.efeitos.append(f"{o.nome}: d{x['faces']} {valor}, nada.")
            elif x["limpa"] == "pv_ou_fadiga" and self.sessao.pv_marcados:
                self.sessao.limpar_pv(1)
                _delta(r, "pv", 1)
                r.efeitos.append(f"{o.nome}: d{x['faces']} {valor}, limpou 1 PV.")
            else:
                _limpar_fadiga(r, self.sessao, f"{o.nome} (d{x['faces']} {valor})")
        return r

    def reagir(self, r: ResultadoRolagem, efeito_id: str, escolha: str | None = None,
               dono: "Personagem | None" = None) -> ResultadoRolagem:
        """Reação a uma rolagem já feita (de `dono`, ou sua): este personagem
        paga o custo; a rolagem é desfeita na ficha do dono e refeita. Devolve a
        versão nova (o Medo que muda é com a API: compare `medo_gerado`)."""
        dono = dono or self
        e = self.bib.efeitos_rolagem.get(efeito_id)
        disponiveis = {o.id: o for o in self.opcoes_de_rolagem(r.tipo, r.traco, r.ataque, r.carta)}
        o = disponiveis.get(efeito_id)
        if e is None or o is None or e.momento != "depois":
            raise RegraViolada("Essa reação não vale para esta rolagem.")
        if not o.disponivel:
            raise RegraViolada(f"{o.nome}: {o.motivo}.")
        proprio = dono is self
        if (e.alvo == "proprio" and not proprio) or (e.alvo == "aliado" and proprio):
            raise RegraViolada(f"{o.nome}: {'só na rolagem de um aliado' if e.alvo == 'aliado' else 'só na sua rolagem'}.")
        if e.se == "falhou" and r.sucesso is not False:
            raise RegraViolada(f"{o.nome}: só depois de uma falha (informe a Dificuldade ao rolar).")
        if e.se == "falhou_com_experiencia" and not (r.sucesso is False and r.experiencias):
            raise RegraViolada(f"{o.nome}: só numa falha que usou Experiência.")
        if e.se == "com_medo" and r.dualidade is not Dualidade.MEDO:
            raise RegraViolada(f"{o.nome}: só num resultado com Medo.")
        if e.escolha and escolha not in e.escolha:
            raise RegraViolada(f"{o.nome}: escolha qual dado.")
        self._pagar([(e, o, 1, escolha)])
        novo = copy.deepcopy(r)
        desfazer(novo, dono.sessao)
        efeito = e.efeitos[0]["tipo"]
        if efeito in ("rerrola_dualidade", "rerrola_teste"):
            rolar_dualidade(novo, dono.sessao.rng)
        elif efeito == "rerrola_esperanca":
            rolar_dualidade(novo, dono.sessao.rng, ("esperanca",))
        elif efeito == "rerrola_um_dado":
            rolar_dualidade(novo, dono.sessao.rng, (escolha,))
        elif efeito == "troca_dualidade":
            esp, med = dado(novo, PapelDoDado.ESPERANCA), dado(novo, PapelDoDado.MEDO)
            esp.valor, med.valor = med.valor, esp.valor
            recalcular_teste(novo)
        elif efeito == "medo_vira_esperanca":
            recalcular_teste(novo, forcar=Dualidade.ESPERANCA)
        elif efeito == "rerrola_dano":
            for d in novo.dados:
                if not d.descartado:
                    d.original, d.valor = d.valor, dono.sessao.rng.randint(1, d.faces)
            novo.total = sum(d.valor for d in novo.dados if not d.descartado) + sum(b.valor for b in novo.bonus)
        elif efeito == "maximiza_um_dado":
            # Versatile Fighter: o dado que mais ganha vira o máximo dele
            validos = [d for d in novo.dados if not d.descartado and d.valor < d.faces]
            if not validos:
                raise RegraViolada(f"{o.nome}: todos os dados já estão no máximo.")
            d = max(validos, key=lambda x: x.faces - x.valor)
            d.original, d.valor = d.valor, d.faces
            novo.total = sum(d.valor for d in novo.dados if not d.descartado) + sum(b.valor for b in novo.bonus)
        if novo.tipo in TIPOS_DE_TESTE:
            _, automaticos = dono._escolhidas(novo.tipo, novo.traco, novo.ataque, novo.carta, ())
            dono._pos_teste(novo, automaticos)
        novo.reacao_de = o.nome
        novo.efeitos.insert(0, f"{o.nome}{'' if proprio else f' (de {self.criacao.nome or 'um aliado'})'}.")
        return novo

    def _tem_habilidade(self, f: Ficha, nome_original: str) -> bool:
        return any(h.nome_original == nome_original for h in f.habilidades)

    @staticmethod
    def _da_lista(lista: list, indice, rotulo: str):
        if not isinstance(indice, int) or not 0 <= indice < len(lista):
            raise RegraViolada(f"{rotulo} não encontrada.")
        return lista[indice]

    def definir_padroes_estranhos(self, numero: int | None):
        """Padrões Estranhos (Mago): o número de 1 a 12 (ou None para tirar)."""
        if not self._tem_habilidade(self.ficha(), "Strange Patterns"):
            raise RegraViolada("Só quem tem Padrões Estranhos escolhe um número.")
        if numero is not None and not 1 <= numero <= 12:
            raise RegraViolada("Escolha um número de 1 a 12.")
        self.sessao.padroes_estranhos = numero

    # --- Cartas: loadout e cofre -----------------------------------------------

    def guardar_carta(self, carta: str) -> Ficha:
        """Move uma carta do loadout para o cofre (sem custo)."""
        if carta not in self._ficha_base().cartas:
            raise RegraViolada("Você só pode guardar uma carta que tem.")
        if carta in self.cofre:
            raise RegraViolada(f"{self._nome(self.bib.cartas, carta)} já está na reserva.")
        if self.bib.cartas[carta].fora_do_limite:
            raise RegraViolada(f"{self.bib.cartas[carta].nome} não vai para a reserva.")
        self.cofre.append(carta)
        return self.ficha()

    def recuperar_carta(self, carta: str, no_lugar_de: str | None = None,
                        em_descanso: bool = False) -> int:
        """Traz uma carta do cofre para o loadout, marcando o Estresse do custo.

        Fora de um descanso, custa o Recall Cost da carta; no descanso é grátis.
        Sem Estresse livre suficiente, a troca é recusada (é um custo, não um
        Estresse imposto). Com o loadout cheio, informe em `no_lugar_de` a
        carta que vai para o cofre. Devolve o Estresse marcado.
        """
        if carta not in self.cofre:
            raise RegraViolada(f"{self._nome(self.bib.cartas, carta)} não está na reserva.")
        if self.bib.cartas[carta].reserva_permanente:
            raise RegraViolada(f"{self.bib.cartas[carta].nome} fica na reserva para sempre.")
        ativas = [c for c in self._ficha_base().cartas if c not in self.cofre and not self.bib.cartas[c].fora_do_limite]
        if no_lugar_de is not None and no_lugar_de not in ativas:
            raise RegraViolada("A carta que sai precisa estar na mão.")
        if no_lugar_de is None and len(ativas) >= self._limite_loadout:
            raise RegraViolada(f"Mão cheia ({self._limite_loadout} cartas): escolha uma para ir para a reserva.")
        custo = 0 if em_descanso else self.bib.cartas[carta].custo_recall
        self.sessao.pagar_estresse(custo)   # recusa antes de mexer no cofre
        self.cofre.remove(carta)
        if no_lugar_de is not None:
            self.cofre.append(no_lugar_de)
        return custo

    def proximo_nivel(self) -> ProximoNivel | None:
        """O que o próximo nível pede, para a interface montar o assistente
        sem repetir as regras. None no nível máximo."""
        f = self._ficha_base()
        proximo = f.nivel + 1
        if proximo > self.bib.progressao["nivel_maximo"]:
            return None
        conquista = self.bib.progressao["conquistas_de_tier"].get(str(proximo))
        regras = self.bib.companheiro
        tem_companheiro = f.companheiro is not None
        extra = 0
        indice = ESTAGIOS_SUBCLASSE.index(f.estagio_subclasse)
        if f.subclasse == regras["subclasse"] and indice < len(ESTAGIOS_SUBCLASSE) - 1:
            extra = regras["treinos_extras_por_estagio"][ESTAGIOS_SUBCLASSE[indice + 1]]
        limpa = bool(conquista and conquista["limpar_marcas_tracos"])
        return ProximoNivel(
            nivel=proximo, tier=self.bib.tier_do_nivel(proximo),
            nova_experiencia=bool(conquista),
            limpa_marcas_tracos=limpa,
            experiencia_companheiro=bool(conquista and tem_companheiro),
            avancos=self.bib.progressao["avancos_por_nivel"],
            opcoes=self.opcoes_disponiveis(),
            # a conquista dos níveis 5 e 8 limpa as marcas antes das escolhas
            tracos_marcados=[] if limpa else sorted(f.tracos_marcados, key=list(Traco).index),
            treinos=1 if tem_companheiro else 0,
            treinos_extra_com_subclasse=extra,
            limite_mesa=self.nivel_limite,
            bloqueado_pela_mesa=self.nivel_limite is not None and proximo > self.nivel_limite,
            planejado=any(s.nivel == proximo for s in self.plano),
        )

    def opcoes_disponiveis(self) -> list[dict]:
        """Avanços que ainda podem ser marcados no PRÓXIMO nível."""
        ficha = self._ficha_base()
        proximo = ficha.nivel + 1
        if proximo > self.bib.progressao["nivel_maximo"]:
            return []
        tier_atual = self.bib.tier_do_nivel(proximo)
        disponiveis = []
        for tier_str, opcoes in self.bib.progressao["opcoes"].items():
            tier = int(tier_str)
            if tier > tier_atual:
                continue
            for nome, limite in opcoes.items():
                opcao = Opcao(nome)
                restantes = limite - ficha.slots_usados.get((tier, nome), 0)
                if restantes > 0 and not self._bloqueada(ficha, opcao, tier):
                    disponiveis.append(
                        {"tier": tier, "opcao": opcao, "restantes": restantes,
                         "custo": self._custo(opcao)}
                    )
        return disponiveis

    def linha_do_tempo(self) -> list[dict]:
        """Dados para a visualização em linha do tempo (níveis 1 a 10).

        Níveis já feitos trazem as escolhas; os futuros trazem o que
        vai acontecer automaticamente (conquistas de tier), para o
        jogador planejar.
        """
        bib = self.bib
        conquistas = bib.progressao["conquistas_de_tier"]
        eventos = [{
            "nivel": 1, "tier": 1, "status": "feito", "titulo": "Criação",
            "itens": [f"Classe: {self._nome_classe(self.criacao.classe)}",
                      f"Subclasse: {self._nome(bib.subclasses, self.criacao.subclasse)}",
                      *(f"Experiência: {e} +2" for e in self.criacao.experiencias),
                      *(f"Carta: {self._nome(bib.cartas, c)}" for c in self.criacao.cartas)],
        }]
        feitos = {s.nivel: s for s in self.historico}
        planejados = {s.nivel: s for s in self.plano}
        for nivel in range(2, self.bib.progressao["nivel_maximo"] + 1):
            itens = []
            if str(nivel) in conquistas:
                c = conquistas[str(nivel)]
                itens.append("Conquista de patamar: nova Experiência +2, +1 Proficiência"
                             + (", limpa marcas dos atributos" if c["limpar_marcas_tracos"] else ""))
            subida = feitos.get(nivel)
            plano = planejados.get(nivel)
            if subida:
                itens += self._descrever_subida(subida)
            elif plano:
                itens += [f"Planejado: {i}" for i in self._descrever_subida(plano)]
            else:
                itens += ["Escolher 2 avanços", "Limiares de dano +1", "Escolher 1 carta de domínio"]
            tier = self.bib.tier_do_nivel(nivel)
            if subida:
                # o patamar do nível e os de onde vieram os avanços dele
                quadros = self.quadros_de_avanco(nivel, {tier} | {e.tier or tier for e in subida.escolhas})
            elif nivel == len(self.historico) + 2:
                quadros = self.quadros_de_avanco(None, set(range(2, tier + 1)))   # pode usar anteriores
            else:
                quadros = self.quadros_de_avanco(None, {tier})
            eventos.append({
                "nivel": nivel, "tier": tier,
                "status": "feito" if subida else "futuro",
                "titulo": f"Nível {nivel}", "itens": itens, "quadros": quadros,
                "planejado": plano is not None and not subida,
                "bloqueado_pela_mesa": not subida and self.nivel_limite is not None and nivel > self.nivel_limite,
            })
        return eventos

    def _descrever_subida(self, s: SubidaDeNivel) -> list[str]:
        cartas = self.bib.cartas
        itens = []
        if s.nova_experiencia:
            itens.append(f"Nova Experiência: {s.nova_experiencia} +2")
        itens += [self._descrever(e) for e in s.escolhas]
        if s.experiencia_companheiro:
            itens.append(f"Companheiro: nova Experiência {s.experiencia_companheiro} +2")
        itens += [self._descrever_treino(t) for t in s.treinos]
        itens.append("Limiares de dano +1")
        itens.append(f"Carta: {self._nome(cartas, s.carta)}")
        itens += [f"Carta a mais (subclasse): {self._nome(cartas, c)}" for c in s.cartas_extras]
        if s.troca_carta:
            antiga, nova = s.troca_carta
            itens.append(f"Troca: {self._nome(cartas, antiga)} → {self._nome(cartas, nova)}")
        return itens

    def quadros_de_avanco(self, nivel: int | None, tiers: set[int]) -> list[dict]:
        """Quadradinhos da página de Level Up de cada patamar em `tiers`, do mais
        alto para o mais baixo, como estavam ao fim de `nivel` (None: hoje).

        Por opção: `limite` de quadradinhos, `antes` (marcados em níveis
        anteriores), `neste` (marcados no próprio `nivel`), `riscados` (cortados
        por regra: subclasse risca a multiclasse do patamar e vice-versa) e
        `custo` (2 para as opções de quadradinho duplo).
        """
        f = self._ficha_base(nivel)
        antes: dict[tuple[int, str], int] = {}
        neste: dict[tuple[int, str], int] = {}
        for s in self.historico:
            if nivel is not None and s.nivel > nivel:
                continue
            destino = neste if s.nivel == nivel else antes
            for e in s.escolhas:
                chave = (e.tier or self.bib.tier_do_nivel(s.nivel), e.opcao.value)
                destino[chave] = destino.get(chave, 0) + 1
        quadros = []
        for tier in sorted(tiers, reverse=True):
            opcoes = []
            for nome, limite in self.bib.progressao["opcoes"][str(tier)].items():
                chave, opcao = (tier, nome), Opcao(nome)
                marcados = antes.get(chave, 0) + neste.get(chave, 0)
                livres = limite - marcados
                # riscar preenche os quadradinhos em slots_usados sem ser marca de verdade
                riscados = livres if self._bloqueada(f, opcao, tier) else f.slots_usados.get(chave, 0) - marcados
                opcoes.append({"opcao": nome, "limite": limite, "custo": self._custo(opcao),
                               "antes": antes.get(chave, 0), "neste": neste.get(chave, 0),
                               "riscados": max(0, min(riscados, livres))})
            quadros.append({"tier": tier, "opcoes": opcoes})
        return quadros

    # --- Replay --------------------------------------------------------------

    def _ficha_base(self, ate_nivel: int | None = None) -> Ficha:
        """Só criação + histórico, SEM equipamento.

        O level up e as validações partem daqui: se partissem de ficha(),
        os modificadores do equipamento (ex.: -1 Evasão) seriam somados de
        novo a cada nível.
        """
        ficha = copy.deepcopy(self._ficha_inicial)
        for subida in self.historico:
            if ate_nivel is not None and subida.nivel > ate_nivel:
                break
            ficha = self._aplicar(ficha, subida)
        return ficha

    # --- Criação -----------------------------------------------------------

    def _criar(self, c: Criacao) -> Ficha:
        bib = self.bib
        classe = self._exigir(bib.classes, c.classe, "Classe")
        subclasse = self._exigir(bib.subclasses, c.subclasse, "Subclasse")
        if subclasse.classe != classe.codigo:
            raise RegraViolada(f"{subclasse.nome} não é subclasse de {classe.nome}.")
        caracteristicas_anc = self._caracteristicas_ancestralidade(c)
        comunidade = self._exigir(bib.comunidades, c.comunidade, "Comunidade")

        if set(c.tracos) != set(Traco):
            raise RegraViolada("Todos os seis atributos precisam de um valor.")
        if sorted(c.tracos.values()) != DISTRIBUICAO_TRACOS:
            raise RegraViolada("Distribua exatamente +2, +1, +1, +0, +0 e -1 entre os atributos.")

        nomes = [e.strip() for e in c.experiencias]
        if len(nomes) != 2 or "" in nomes or len(set(nomes)) != 2:
            raise RegraViolada("Escolha duas Experiências diferentes.")

        # a carta a mais da fundamental (Promissor) é direito, não obrigação: personagens
        # criados antes dela existir no motor têm 2 e precisam continuar carregando
        quantas = 2 + self._cartas_extras_da(subclasse.fundacao)
        if not 2 <= len(c.cartas) <= quantas or len(set(c.cartas)) != len(c.cartas):
            extra = f" ({subclasse.nome} dá uma a mais)" if quantas > 2 else ""
            raise RegraViolada(f"Escolha {quantas} cartas de domínio diferentes{extra}.")
        for carta_id in c.cartas:
            carta = self._exigir(bib.cartas, carta_id, "Carta")
            if carta.nivel != 1 or carta.dominio not in classe.dominios:
                raise RegraViolada(f"{carta.nome} precisa ser de nível 1 e dos domínios da classe.")

        f = Ficha(
            nome=c.nome, nivel=1, classe=classe.id, subclasse=subclasse.id,
            estagio_subclasse="fundacao", ancestralidade=c.ancestralidade,
            comunidade=c.comunidade, tracos=dict(c.tracos),
            evasao=classe.evasao_inicial, pv_max=classe.pv_iniciais,
            estresse_max=6, esperanca=2, proficiencia=1,
            experiencias={n: 2 for n in nomes}, cartas=list(c.cartas),
            segunda_ancestralidade=c.segunda_ancestralidade,
            caracteristicas_ancestralidade=caracteristicas_anc,
            caracteristicas_comunidade=list(comunidade.caracteristicas),
        )
        self._aplicar_ancestralidade(f, c)
        f.companheiro = self._ganhar_companheiro(subclasse, c.companheiro)
        return f

    def _caracteristicas_ancestralidade(self, c: Criacao) -> list[Caracteristica]:
        """As duas características de ancestralidade do personagem.

        Mista: a 1ª da `ancestralidade` e a 2ª da `segunda_ancestralidade`.
        Isso já garante a regra do SRD (uma primeira e uma segunda); para
        a combinação inversa, basta trocar as duas de lugar.
        """
        primeira = self._exigir(self.bib.ancestralidades, c.ancestralidade, "Ancestralidade")
        if c.segunda_ancestralidade is None:
            return list(primeira.caracteristicas)
        segunda = self._exigir(self.bib.ancestralidades, c.segunda_ancestralidade, "Ancestralidade")
        if segunda.id == primeira.id:
            raise RegraViolada("Na ancestralidade mista, escolha duas ancestralidades diferentes.")
        return [primeira.caracteristicas[0], segunda.caracteristicas[1]]

    @staticmethod
    def _aplicar_ancestralidade(f: Ficha, c: Criacao):
        """Características de ancestralidade que mudam números na criação."""
        efeitos = {x.efeito for x in f.caracteristicas_ancestralidade}
        if Efeito.VIGOR in efeitos:
            f.pv_max += 1
        if Efeito.FOLEGO in efeitos:
            f.estresse_max += 1
        if Efeito.AGIL in efeitos:
            f.evasao += 1
        if Efeito.PROPOSITO in efeitos:
            if c.experiencia_proposito not in f.experiencias:
                raise RegraViolada("Projeto com Propósito: escolha uma das suas Experiências para ganhar +1.")
            f.experiencias[c.experiencia_proposito] += 1
        elif c.experiencia_proposito is not None:
            raise RegraViolada("Só Projeto com Propósito (Clank) dá +1 numa Experiência na criação.")

    def _ganhar_companheiro(self, sub: Subclasse, dados: Companheiro | None) -> FichaCompanheiro | None:
        """Beastbound exige os dados do companheiro; outras subclasses não aceitam."""
        regras = self.bib.companheiro
        if sub.id == regras["subclasse"]:
            if dados is None:
                raise RegraViolada(f"{sub.nome} vem com um companheiro: informe nome e Experiências.")
            return criar_companheiro(regras, dados)
        if dados is not None:
            raise RegraViolada(f"{sub.nome} não tem companheiro.")
        return None

    # --- Level up ----------------------------------------------------------

    def _aplicar(self, anterior: Ficha, s: SubidaDeNivel) -> Ficha:
        """Retorna uma NOVA ficha com o nível aplicado (não altera a anterior)."""
        f = copy.deepcopy(anterior)
        prog = self.bib.progressao
        if s.nivel != f.nivel + 1:
            raise RegraViolada(f"O próximo nível é {f.nivel + 1}, não {s.nivel}.")
        if s.nivel > prog["nivel_maximo"]:
            raise RegraViolada("Nível máximo atingido.")
        tier = self.bib.tier_do_nivel(s.nivel)
        # companheiro ganho NESTE nível (multiclasse) só evolui a partir do próximo
        tinha_companheiro = f.companheiro is not None
        estagio_antes = f.estagio_subclasse

        # Passo 1: conquistas de tier
        conquista = prog["conquistas_de_tier"].get(str(s.nivel))
        if conquista:
            nome = (s.nova_experiencia or "").strip()
            if not nome:
                raise RegraViolada(f"No nível {s.nivel} você ganha uma nova Experiência.")
            if nome in f.experiencias:
                raise RegraViolada(f"Você já tem a Experiência '{nome}'.")
            f.experiencias[nome] = 2
            f.proficiencia += conquista["proficiencia"]
            if conquista["limpar_marcas_tracos"]:
                f.tracos_marcados.clear()
            if tinha_companheiro:
                nova_experiencia(self.bib.companheiro, f.companheiro, s.experiencia_companheiro)
        elif s.nova_experiencia:
            raise RegraViolada(f"O nível {s.nivel} não dá nova Experiência.")
        if s.experiencia_companheiro and not (conquista and tinha_companheiro):
            raise RegraViolada("O companheiro só ganha Experiência junto com você (níveis 2, 5 e 8).")

        # Passo 2: avanços
        custo_total = sum(self._custo(e.opcao) for e in s.escolhas)
        if custo_total != prog["avancos_por_nivel"]:
            raise RegraViolada("Escolha exatamente 2 avanços (Proficiência e Multiclasse valem por 2).")
        for escolha in s.escolhas:
            self._aplicar_escolha(f, escolha, tier, s.nivel)
        self._treinar_companheiro(f, s, tinha_companheiro, estagio_antes)

        # Passo 3: limiares de dano sobem junto com o nível (ver _vestir)
        f.nivel = s.nivel

        # Passo 4: carta de domínio
        self._validar_nova_carta(f, s.carta, s.nivel, s.nivel)
        f.cartas.append(s.carta)
        self._ganhar_cartas_extras(anterior, f, s)
        if s.troca_carta:
            self._trocar_carta(f, *s.troca_carta)
        self._beneficios_de_cartas(anterior, f, s)
        return f

    def _beneficios_de_cartas(self, anterior: Ficha, f: Ficha, s: SubidaDeNivel):
        """Bônus permanentes de cartas pegas neste nível que pedem escolha."""
        novas = [c for c in f.cartas if c not in anterior.cartas]
        for carta_id in s.beneficios_de_carta:
            if carta_id not in novas or self.bib.cartas[carta_id].escolha is None:
                raise RegraViolada("Só cartas pegas neste nível que pedem escolha recebem benefícios.")
        for carta_id in novas:
            carta = self.bib.cartas[carta_id]
            escolhas = s.beneficios_de_carta.get(carta_id, [])
            if not escolhas:
                continue   # nível salvo antes da regra (subir_de_nivel exige a escolha)
            if carta.escolha is EscolhaDeCarta.VITALIDADE:
                self._vitalidade(f, carta, escolhas)
            elif carta.escolha is EscolhaDeCarta.MESTRE_DO_OFICIO:
                validas = len(escolhas) in (1, 2) and len(set(escolhas)) == len(escolhas)
                if not validas or any(x not in f.experiencias for x in escolhas):
                    raise RegraViolada(f"{carta.nome}: escolha duas Experiências que você tem (+2 cada) ou uma (+3).")
                for x in escolhas:
                    f.experiencias[x] += 3 if len(escolhas) == 1 else 2

    def _vitalidade(self, f: Ficha, carta: CartaDeDominio, escolhas: list[str]):
        if len(set(escolhas)) != 2 or not set(escolhas) <= {"PV", "ESTRESSE", "LIMIARES"}:
            raise RegraViolada(f"{carta.nome}: escolha dois benefícios diferentes (PV, Fadiga ou limiares).")
        prog = self.bib.progressao
        if "PV" in escolhas:
            if f.pv_max >= prog["limite_pv"]:
                raise RegraViolada("Limite de Pontos de Vida atingido: escolha outro benefício.")
            f.pv_max += 1
        if "ESTRESSE" in escolhas:
            if f.estresse_max >= prog["limite_estresse"]:
                raise RegraViolada("Limite de Fadiga atingido: escolha outro benefício.")
            f.estresse_max += 1
        if "LIMIARES" in escolhas:
            f.bonus_limiares += 2

    def _aplicar_escolha(self, f: Ficha, e: Escolha, tier_atual: int, nivel: int):
        tier = e.tier or tier_atual
        tabela = self.bib.progressao["opcoes"].get(str(tier))
        if tabela is None or tier > tier_atual:
            raise RegraViolada(f"Patamar {tier} não está disponível no nível {nivel}.")
        if e.opcao.value not in tabela:
            raise RegraViolada(f"A opção {e.opcao.rotulo} não existe no patamar {tier}.")
        chave = (tier, e.opcao.value)
        if f.slots_usados.get(chave, 0) >= tabela[e.opcao.value]:
            raise RegraViolada(f"Não há mais espaços de {e.opcao.rotulo} no patamar {tier}.")
        if self._bloqueada(f, e.opcao, tier):
            raise RegraViolada(f"{e.opcao.rotulo} foi bloqueada no patamar {tier}.")

        o = e.opcao
        if o is Opcao.TRACOS:
            if len(set(e.tracos)) != 2:
                raise RegraViolada("Escolha dois atributos diferentes.")
            if any(t in f.tracos_marcados for t in e.tracos):
                raise RegraViolada("Atributo marcado só pode subir de novo após a próxima conquista de patamar.")
            for t in e.tracos:
                f.tracos[t] += 1
                f.tracos_marcados.add(t)
        elif o is Opcao.PV:
            if f.pv_max >= self.bib.progressao["limite_pv"]:
                raise RegraViolada("Limite de Pontos de Vida atingido.")
            f.pv_max += 1
        elif o is Opcao.ESTRESSE:
            if f.estresse_max >= self.bib.progressao["limite_estresse"]:
                raise RegraViolada("Limite de Fadiga atingido.")
            f.estresse_max += 1
        elif o is Opcao.EXPERIENCIAS:
            if len(set(e.experiencias)) != 2 or any(x not in f.experiencias for x in e.experiencias):
                raise RegraViolada("Escolha duas Experiências que você já tem.")
            for x in e.experiencias:
                f.experiencias[x] += 1
        elif o is Opcao.CARTA_DOMINIO:
            self._validar_nova_carta(f, e.carta, self._limite_carta_extra(tier, nivel), nivel)
            f.cartas.append(e.carta)
        elif o is Opcao.EVASAO:
            f.evasao += 1
        elif o is Opcao.SUBCLASSE:
            indice = ESTAGIOS_SUBCLASSE.index(f.estagio_subclasse)
            if indice == len(ESTAGIOS_SUBCLASSE) - 1:
                raise RegraViolada("Sua subclasse já está na maestria.")
            f.estagio_subclasse = ESTAGIOS_SUBCLASSE[indice + 1]
            # regra: pegar a subclasse risca a multiclasse deste tier
            f.slots_usados[(tier, Opcao.MULTICLASSE.value)] = tabela[Opcao.MULTICLASSE.value]
        elif o is Opcao.PROFICIENCIA:
            f.proficiencia += 1
        elif o is Opcao.MULTICLASSE:
            self._multiclassear(f, e, tier)

        f.slots_usados[chave] = f.slots_usados.get(chave, 0) + 1

    def _multiclassear(self, f: Ficha, e: Escolha, tier: int):
        classe = self._exigir(self.bib.classes, e.classe, "Classe")
        if classe.id == f.classe:
            raise RegraViolada("Escolha uma classe diferente da sua.")
        if e.dominio not in classe.dominios:
            raise RegraViolada(f"{e.dominio} não é domínio de {classe.nome}.")
        if e.dominio in self.bib.classes[f.classe].dominios:
            # "Escolha um domínio da sua nova classe ao qual você ainda não tem acesso."
            raise RegraViolada(f"Você já tem acesso a {self.bib.nome_dominio(e.dominio)}: "
                               f"escolha um domínio novo de {classe.nome}.")
        sub = self._exigir(self.bib.subclasses, e.subclasse, "Subclasse")
        if sub.classe != classe.codigo:
            raise RegraViolada(f"{sub.nome} não é subclasse de {classe.nome}.")
        companheiro = self._ganhar_companheiro(sub, e.companheiro)
        f.multiclasse = {"classe": classe.id, "dominio": e.dominio, "subclasse": sub.id}
        f.multiclasse_bloqueada = True             # risca as outras multiclasses
        f.subclasse_bloqueada_tiers.add(tier)      # risca a subclasse deste tier
        if companheiro:
            f.companheiro = companheiro

    def _ganhar_cartas_extras(self, anterior: Ficha, f: Ficha, s: SubidaDeNivel):
        """Habilidade ganha neste nível que dá carta a mais ("do seu nível ou
        menor, de um domínio a que você tem acesso"). Como na criação, é um
        direito: níveis salvos antes desta regra vêm sem elas e continuam valendo
        (a tela sempre pede todas)."""
        permitidas = self._n_cartas_extras(f) - self._n_cartas_extras(anterior)
        if len(s.cartas_extras) > permitidas:
            if permitidas == 0:
                raise RegraViolada("Neste nível nenhuma habilidade dá carta a mais.")
            raise RegraViolada(f"Neste nível a subclasse dá {permitidas} carta(s) a mais, não {len(s.cartas_extras)}.")
        if len(set(s.cartas_extras)) != len(s.cartas_extras):
            raise RegraViolada("Escolha cartas a mais diferentes.")
        for carta in s.cartas_extras:
            self._validar_nova_carta(f, carta, s.nivel, s.nivel)
            f.cartas.append(carta)

    def _n_cartas_extras(self, f: Ficha) -> int:
        """Cartas a mais que as habilidades de subclasse que a ficha tem dão no total."""
        return self._cartas_extras_da([h for _, _, h in self._habilidades_da_ficha(f)])

    @staticmethod
    def _cartas_extras_da(habilidades) -> int:
        return sum(1 for h in habilidades if h.efeito is Efeito.CARTA_EXTRA)

    def cartas_extras(self, escolhas: list[Escolha] = ()) -> int:
        """Quantas cartas a mais o próximo nível dá com estes avanços (ex.:
        a especialização do Discípulo do Conhecimento)."""
        f, _ = self._ficha_com_escolhas(escolhas)
        return self._n_cartas_extras(f) - self._n_cartas_extras(self._ficha_base())

    def _treinar_companheiro(self, f: Ficha, s: SubidaDeNivel, tinha_companheiro: bool,
                             estagio_antes: str):
        """Beastbound: um treino por nível em que já se tinha o companheiro,
        mais 1 ao pegar a especialização (Expert Training) e 2 na maestria
        (Advanced Training) da subclasse principal."""
        regras = self.bib.companheiro
        exigidos = 1 if tinha_companheiro else 0
        if f.subclasse == regras["subclasse"] and f.estagio_subclasse != estagio_antes:
            exigidos += regras["treinos_extras_por_estagio"][f.estagio_subclasse]
        if len(s.treinos) != exigidos:
            raise RegraViolada(f"Escolha {exigidos} treino(s) para o companheiro neste nível.")
        for t in s.treinos:
            aplicar_treino(regras, f.companheiro, t)

    @property
    def _limite_loadout(self) -> int:
        return self.bib.progressao["limite_loadout"]

    def _ajustar_cofre(self):
        """Mantém o cofre coerente depois que o histórico muda.

        Tira do cofre cartas que o personagem não tem mais (ex.: nível
        desfeito) e, se o loadout passar do limite, manda para o cofre as
        cartas ativas mais recentes (é assim que uma carta nova "cai" no cofre).
        """
        cartas = self._ficha_base().cartas
        self.cofre = [c for c in self.cofre if c in cartas]
        # Vitality, Master of the Craft: depois de pegas, ficam na reserva para sempre;
        # Notorious nunca vai para a reserva e não conta no limite da mão
        self.cofre = [c for c in self.cofre if not self.bib.cartas[c].fora_do_limite]
        self.cofre += [c for c in cartas if self.bib.cartas[c].reserva_permanente and c not in self.cofre]
        ativas = [c for c in cartas if c not in self.cofre and not self.bib.cartas[c].fora_do_limite]
        while len(ativas) > self._limite_loadout:
            self.cofre.append(ativas.pop())

    def _carta_permitida(self, f: Ficha, carta: CartaDeDominio, nivel_maximo: int,
                         nivel: int) -> bool:
        """Regra única de acesso a cartas, usada na validação E nas listagens."""
        if carta.dominio in self.bib.classes[f.classe].dominios and carta.nivel <= nivel_maximo:
            return True
        # domínio da multiclasse: "half your level or lower (rounded up)"
        return bool(f.multiclasse and carta.dominio == f.multiclasse["dominio"]
                    and carta.nivel <= min(nivel_maximo, metade(nivel)))

    def _validar_nova_carta(self, f: Ficha, carta_id, nivel_maximo: int, nivel: int):
        carta = self._exigir(self.bib.cartas, carta_id, "Carta")
        if carta_id in f.cartas:
            raise RegraViolada(f"Você já tem {carta.nome}.")
        if not self._carta_permitida(f, carta, nivel_maximo, nivel):
            raise RegraViolada(f"{carta.nome} (nível {carta.nivel}, {carta.dominio}) não está disponível.")

    def _listar_cartas(self, f: Ficha, nivel_maximo: int, nivel: int) -> list[CartaDeDominio]:
        return sorted(
            (c for c in self.bib.cartas.values()
             if c.id not in f.cartas and self._carta_permitida(f, c, nivel_maximo, nivel)),
            key=lambda c: (c.nivel, c.dominio, c.nome),
        )

    def _limite_carta_extra(self, tier: int, nivel: int) -> int:
        return min(nivel, self.bib.progressao["nivel_maximo_carta_extra_por_tier"][str(tier)])

    def _ficha_com_escolhas(self, escolhas) -> tuple[Ficha, int]:
        """Ficha base com os avanços do PRÓXIMO nível já aplicados.

        Serve para as listagens enxergarem o que o jogador já marcou neste
        nível: uma multiclasse recém-escolhida libera o domínio novo, e a carta
        pega pelo avanço CARTA_DOMINIO some da lista do passo 4.
        """
        f = self._ficha_base()
        proximo = f.nivel + 1
        if proximo > self.bib.progressao["nivel_maximo"]:
            raise RegraViolada("Nível máximo atingido.")
        tier = self.bib.tier_do_nivel(proximo)
        for e in escolhas:
            self._aplicar_escolha(f, e, tier, proximo)
        return f, proximo

    def _trocar_carta(self, f: Ficha, antiga: str, nova: str):
        if antiga not in f.cartas:
            raise RegraViolada("Você só pode trocar uma carta que já tem.")
        nivel_antiga = self.bib.cartas[antiga].nivel
        self._validar_nova_carta(f, nova, nivel_antiga, f.nivel)
        f.cartas[f.cartas.index(antiga)] = nova

    # --- Equipamento ---------------------------------------------------------

    def _validar_equipamento(self, f: Ficha, eq: Equipamento):
        bib = self.bib
        principal = secundaria = None
        if eq.principal:
            principal = self._exigir(bib.armas, eq.principal, "Arma")
            if not principal.primaria:
                raise RegraViolada(f"{principal.nome} é uma arma secundária.")
            if principal.magica and not self._conjura(f):
                raise RegraViolada(f"{principal.nome} é mágica e exige um atributo de conjuração.")
        if eq.secundaria:
            secundaria = self._exigir(bib.armas, eq.secundaria, "Arma")
            if secundaria.primaria:
                raise RegraViolada(f"{secundaria.nome} é uma arma principal.")
            if principal and principal.duas_maos and not self._tem_efeito(f, Efeito.TREINAMENTO_DE_COMBATE):
                raise RegraViolada(f"{principal.nome} usa as duas mãos; não sobra mão para a secundária.")
        if eq.armadura:
            self._exigir(bib.armaduras, eq.armadura, "Armadura")

    def _subclasses(self, f: Ficha) -> list[Subclasse]:
        """A subclasse principal e, se houver, a da multiclasse."""
        ids = [f.subclasse]
        if f.multiclasse:
            ids.append(f.multiclasse["subclasse"])
        return [self.bib.subclasses[s] for s in ids]

    def _habilidades_da_ficha(self, f: Ficha) -> list[tuple[str, str, Caracteristica]]:
        """(origem, tipo, habilidade): habilidade de Esperança e de classe da
        classe principal; de classe da multiclasse (o SRD não dá a de
        Esperança dela); cartas de subclasse até o estágio atual e a
        fundamental da subclasse da multiclasse."""
        classe = self.bib.classes[f.classe]
        sub = self.bib.subclasses[f.subclasse]
        lista = [(classe.nome, "esperanca", classe.habilidade_esperanca)] if classe.habilidade_esperanca else []
        lista += [(classe.nome, "classe", h) for h in classe.habilidades]
        lista += [(sub.nome, estagio, h) for estagio, h in sub.habilidades_ate(f.estagio_subclasse)]
        if f.multiclasse:
            outra = self.bib.classes[f.multiclasse["classe"]]
            outra_sub = self.bib.subclasses[f.multiclasse["subclasse"]]
            lista += [(outra.nome, "classe", h) for h in outra.habilidades]
            lista += [(outra_sub.nome, "fundacao", h) for h in outra_sub.fundacao]
        return lista

    def _tem_efeito(self, f: Ficha, efeito: Efeito) -> bool:
        return any(h.efeito is efeito for _, _, h in self._habilidades_da_ficha(f))

    def _conjura(self, f: Ficha) -> bool:
        """Alguma subclasse do personagem (inclusive da multiclasse) tem atributo de conjuração."""
        return any(s.traco_conjuracao for s in self._subclasses(f))

    def _vestir(self, f: Ficha, eq: Equipamento) -> Ficha:
        """Aplica o equipamento sobre uma ficha base (que é alterada).

        Ordem: valores base da armadura, depois os modificadores fixos de
        TODAS as peças (uma arma Heavy também tira Evasão), e por último os
        ataques, que já usam os atributos modificados.
        O equipamento já foi validado em equipar().
        """
        armas = [self.bib.armas[a] for a in (eq.principal, eq.secundaria) if a]
        armadura = self.bib.armaduras[eq.armadura] if eq.armadura else None
        self._aplicar_reliquia(f)

        if armadura:
            f.limiar_maior = armadura.limiar_maior + f.nivel
            f.limiar_grave = armadura.limiar_grave + f.nivel
            f.pontuacao_armadura = armadura.pontuacao
            f.armadura = armadura.nome
            f.armadura_original = armadura.nome_original
            f.caracteristicas_armadura = list(armadura.caracteristicas)
        else:
            # regra do SRD para quem está sem armadura
            f.limiar_maior, f.limiar_grave, f.pontuacao_armadura = f.nivel, 2 * f.nivel, 0
        passivos = self._passivos_de_cartas(f, eq)
        efeitos_cartas = {p.efeito for _, p in passivos if p.efeito}
        if Efeito.OSSOS_EXPOSTOS in efeitos_cartas:
            # Bare Bones: limiares base do patamar + nível (a Pontuação vem no fim, com a Força)
            maior, grave = LIMIARES_OSSOS_EXPOSTOS[self.bib.tier_do_nivel(f.nivel)]
            f.limiar_maior, f.limiar_grave = maior + f.nivel, grave + f.nivel
        f.limiar_maior += f.bonus_limiares
        f.limiar_grave += f.bonus_limiares
        if any(c.efeito is Efeito.CASCO for c in f.caracteristicas_ancestralidade):
            # Shell (Galapa): limiares + Proficiência
            f.limiar_maior += f.proficiencia
            f.limiar_grave += f.proficiencia
        # habilidades de classe/subclasse com número fixo (Resoluto, Mago de Batalha...)
        habilidades = self._habilidades_da_ficha(f)
        for _, _, h in habilidades:
            for m in h.modificadores:
                self._modificar(f, m)
        f.habilidades = [HabilidadeNaFicha(h.nome, h.descricao, origem, tipo,
                                    automatica=bool(h.modificadores or h.efeito), nome_original=h.nome_original)
                         for origem, tipo, h in habilidades]

        mods = [m for peca in self._pecas(eq) for c in peca.caracteristicas for m in c.modificadores]
        mods_cartas = [m for _, p in passivos for m in p.modificadores]
        for m in mods + mods_cartas:
            self._modificar(f, m)
        if Efeito.OSSOS_EXPOSTOS in efeitos_cartas:
            f.pontuacao_armadura += PONTUACAO_OSSOS_EXPOSTOS + f.tracos[Traco.FORCA]
        if Efeito.INTOCAVEL in efeitos_cartas:
            f.evasao += max(0, metade(f.tracos[Traco.AGILIDADE]))   # bônus: Agilidade negativa não tira
        if Efeito.LEVANTE in efeitos_cartas:
            f.limiar_grave += f.proficiencia
        f.cartas_aplicadas = [c for c, _ in passivos]

        # Blade-Touched: "+2 to your attack rolls" vale para todas as armas
        ataque_cartas = sum(self._valor(f, m) for m in mods_cartas if m.alvo is Alvo.ATAQUE)
        versatil = Efeito.VERSATIL in efeitos_cartas
        trocas = {eq.principal: eq.traco_principal, eq.secundaria: eq.traco_secundaria} if versatil else {}
        f.ataques = [self._ataque(f, arma, ataque_cartas, trocas.get(arma.id)) for arma in armas]
        bonus_conjuracao = sum(self._valor(f, m) for m in mods + mods_cartas if m.alvo is Alvo.CONJURACAO)
        f.conjuracoes = [Conjuracao(sub.nome, sub.traco_conjuracao,
                                    f.tracos[sub.traco_conjuracao] + bonus_conjuracao)
                         for sub in self._subclasses(f) if sub.traco_conjuracao]
        return f

    def _aplicar_reliquia(self, f: Ficha):
        """Relíquia carregada: +1 num atributo, ou numa Experiência escolhida (Honing Relic)."""
        reliquia = self.inventario.reliquia(self.bib)
        if reliquia is None:
            return
        if isinstance(reliquia.reliquia, Traco):
            f.tracos[reliquia.reliquia] += 1
        elif (exp := self.inventario.experiencia_da_reliquia) in f.experiencias:
            f.experiencias[exp] += 1

    @staticmethod
    def _modificar(f: Ficha, m: Modificador):
        if isinstance(m.alvo, Traco):
            f.tracos[m.alvo] += m.valor
        elif m.alvo is Alvo.EVASAO:
            f.evasao += m.valor
        elif m.alvo is Alvo.PONTUACAO_ARMADURA:
            f.pontuacao_armadura += m.valor
        elif m.alvo is Alvo.LIMIAR_GRAVE:
            f.limiar_grave += m.valor
        elif m.alvo is Alvo.LIMIARES:
            f.limiar_maior += m.valor
            f.limiar_grave += m.valor
        elif m.alvo is Alvo.PV:
            f.pv_max += m.valor
        elif m.alvo is Alvo.ESTRESSE:
            f.estresse_max += m.valor
        # Alvo.ATAQUE e Alvo.DANO valem só para a própria arma (_ataque);
        # Alvo.CONJURACAO é somado nas conjurações, no fim de _vestir

    @staticmethod
    def _valor(f: Ficha, m: Modificador) -> int:
        """Valor do modificador nesta ficha (resolve "igual ao seu nível/atributo")."""
        if m.igual_a is Referencia.NIVEL:
            return f.nivel
        if isinstance(m.igual_a, Traco):
            return f.tracos[m.igual_a]
        return m.valor

    def _passivos_de_cartas(self, f: Ficha, eq: Equipamento) -> list[tuple[str, PassivoDeCarta]]:
        """Cartas NA MÃO com passivo que vale agora (a reserva não conta)."""
        mao = [c for c in f.cartas if c not in self.cofre]
        dominios = Counter(self.bib.cartas[c].dominio for c in mao)
        valem = []
        for c in mao:
            p = self.bib.cartas[c].passivo
            if p is None:
                continue
            cond = p.condicao or ""
            if (cond == "com_armadura" and not eq.armadura) or (cond == "sem_armadura" and eq.armadura):
                continue
            if cond.startswith("dominio:") and dominios[cond.split(":", 1)[1]] < 4:
                continue
            valem.append((c, p))
        return valem

    def _ataque(self, f: Ficha, arma: Arma, bonus_cartas: int = 0, traco: Traco | None = None) -> Ataque:
        mods = [m for c in arma.caracteristicas for m in c.modificadores]
        bonus_ataque = bonus_cartas + sum(self._valor(f, m) for m in mods if m.alvo is Alvo.ATAQUE)
        bonus_dano = arma.modificador_dano + sum(
            self._valor(f, m) for m in mods if m.alvo is Alvo.DANO)
        if arma.tipo_dano is TipoDano.FISICO and self._tem_efeito(f, Efeito.TREINAMENTO_DE_COMBATE):
            bonus_dano += f.nivel   # Treinamento de Combate: +nível no dano físico
        dano = f"{f.proficiencia}{arma.dado}"
        if bonus_dano:
            dano += f"{bonus_dano:+d}"   # "+5" ou "-1"
        usado = traco or arma.traco
        return Ataque(arma=arma.nome, traco=usado,
                      bonus=f.tracos[usado] + bonus_ataque,
                      alcance=arma.alcance, dano=dano, tipo_dano=arma.tipo_dano,
                      caracteristicas=list(arma.caracteristicas), arma_original=arma.nome_original,
                      traco_da_arma=arma.traco if traco else None)

    def _pecas(self, eq: Equipamento) -> list[Arma | Armadura]:
        """Armas e armadura do equipamento, como objetos da Biblioteca."""
        pecas: list[Arma | Armadura] = [self.bib.armas[a] for a in (eq.principal, eq.secundaria) if a]
        if eq.armadura:
            pecas.append(self.bib.armaduras[eq.armadura])
        return pecas

    def efeitos_ativos(self) -> set[Efeito]:
        """Regras especiais em vigor: das peças equipadas agora (Fortified,
        Healing...) e da ancestralidade (Efficient, Celestial Trance...)."""
        caracteristicas = [c for p in self._pecas(self.equipamento) for c in p.caracteristicas]
        caracteristicas += self._ficha_inicial.caracteristicas_ancestralidade
        return {c.efeito for c in caracteristicas if c.efeito}

    def _validar_requisitos(self, f: Ficha, eq: Equipamento):
        """`f` já vestida com `eq`: o requisito vale para o atributo como ele fica
        com todo o equipamento (ex.: uma peça que dá +1 Presença conta)."""
        for peca in self._pecas(eq):
            for c in peca.caracteristicas:
                for r in c.requisitos:
                    if f.tracos[r.traco] > r.maximo:
                        raise RegraViolada(
                            f"{peca.nome} exige {r.traco.rotulo} {r.maximo} ou menos "
                            f"(você tem {f.tracos[r.traco]}).")

    # --- utilitários ---------------------------------------------------------

    def _bloqueada(self, f: Ficha, opcao: Opcao, tier: int) -> bool:
        if opcao is Opcao.MULTICLASSE:
            return f.multiclasse_bloqueada
        if opcao is Opcao.SUBCLASSE:
            return tier in f.subclasse_bloqueada_tiers
        return False

    def _custo(self, opcao: Opcao) -> int:
        return 2 if opcao.value in self.bib.progressao["opcoes_que_custam_dois_avancos"] else 1

    @staticmethod
    def _exigir(colecao: dict, chave, rotulo: str):
        if chave not in colecao:
            raise RegraViolada(f"{rotulo} não encontrada: {chave}")
        return colecao[chave]

    def _nome(self, colecao: dict, chave: str) -> str:
        """Nome de exibição de um conteúdo do SRD a partir do id.

        Os ids do histórico já foram validados por _criar/_aplicar.
        """
        return colecao[chave].nome

    def _nome_classe(self, chave: str) -> str:
        return self._nome(self.bib.classes, chave)

    @staticmethod
    def _descrever_treino(t: Treino) -> str:
        detalhe = f" ({t.experiencia})" if t.experiencia else f" ({t.alvo.rotulo})" if t.alvo else ""
        return f"Treino do companheiro: {t.opcao.rotulo}{detalhe}"

    def _descrever(self, e: Escolha) -> str:
        detalhe = ""
        if e.tracos:
            detalhe = " (" + ", ".join(t.rotulo for t in e.tracos) + ")"
        elif e.experiencias:
            detalhe = " (" + ", ".join(e.experiencias) + ")"
        elif e.carta:
            detalhe = f" ({self._nome(self.bib.cartas, e.carta)})"
        elif e.classe:
            detalhe = (f" ({self._nome_classe(e.classe)} / {self.bib.nome_dominio(e.dominio)}"
                       f" / {self._nome(self.bib.subclasses, e.subclasse)})")
        origem = f" [patamar {e.tier}]" if e.tier else ""
        return f"Avanço: {e.opcao.rotulo}{detalhe}{origem}"
