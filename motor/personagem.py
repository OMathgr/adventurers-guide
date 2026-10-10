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
from dataclasses import dataclass, field
from enum import Enum

from .companheiro import (Companheiro, FichaCompanheiro, OpcaoTreino, Treino,
                          aplicar_treino, criar_companheiro, nova_experiencia)
from .erros import RegraViolada
from .sessao import Sessao
from .srd import (Alvo, Arma, Armadura, Biblioteca, Caracteristica, CartaDeDominio, Efeito,
                  Modificador, Referencia, Subclasse, TipoDano, Traco)

DISTRIBUICAO_TRACOS = sorted([2, 1, 1, 0, 0, -1])
ESTAGIOS_SUBCLASSE = ["fundacao", "especializacao", "maestria"]


class Opcao(str, Enum):
    """Opções de avanço da página de Level Up da ficha."""

    TRACOS = "TRACOS"              # +1 em dois traços não marcados
    PV = "PV"                      # +1 slot de Pontos de Vida
    ESTRESSE = "ESTRESSE"          # +1 slot de Estresse
    EXPERIENCIAS = "EXPERIENCIAS"  # +1 em duas Experiências
    CARTA_DOMINIO = "CARTA_DOMINIO"  # carta de domínio adicional
    EVASAO = "EVASAO"              # +1 Evasão
    SUBCLASSE = "SUBCLASSE"        # próxima carta de subclasse
    PROFICIENCIA = "PROFICIENCIA"  # +1 Proficiência (custa os 2 avanços)
    MULTICLASSE = "MULTICLASSE"    # nova classe (custa os 2 avanços)


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


@dataclass(frozen=True)
class Equipamento:
    """O que o personagem está usando AGORA. Não faz parte do histórico:
    trocar de arma acontece durante o jogo, não ao subir de nível."""

    principal: str | None = None
    secundaria: str | None = None
    armadura: str | None = None


# --- Saída: a ficha calculada ----------------------------------------------

@dataclass
class Ataque:
    arma: str        # nome de exibição
    traco: Traco     # traço usado na rolagem de ataque
    bonus: int       # traço (já com modificadores) + bônus de ataque da arma
    alcance: str
    dano: str        # ex.: "2d8+1" (número de dados = Proficiência)
    tipo_dano: TipoDano
    caracteristicas: list[Caracteristica] = field(default_factory=list)


@dataclass
class Conjuracao:
    subclasse: str   # nome de exibição da subclasse que dá o traço
    traco: Traco     # traço de conjuração da subclasse
    bonus: int       # traço (já com modificadores) + bônus de equipamento


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
    companheiro: FichaCompanheiro | None = None


class Personagem:
    def __init__(self, biblioteca: Biblioteca, criacao: Criacao):
        self.bib = biblioteca
        self.criacao = criacao
        self.historico: list[SubidaDeNivel] = []
        self.equipamento = Equipamento()
        # Cartas guardadas no cofre (estado atual, como o equipamento).
        # Toda carta que o personagem tem e não está aqui está no loadout.
        self.cofre: list[str] = []
        self._ficha_inicial = self._criar(criacao)
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
        # Reinforced: com o último espaço marcado, limiares +2 até limpar um espaço
        if (Efeito.REFORCADA in self.efeitos_ativos()
                and 0 < f.pontuacao_armadura <= f.armadura_marcada):
            f.limiar_maior += 2
            f.limiar_grave += 2
        f.esperanca_max = self.bib.progressao["limite_esperanca"]
        if f.companheiro:
            c = f.companheiro
            if c.tem(OpcaoTreino.LUZ_NA_ESCURIDAO):
                f.esperanca_max += 1   # Light in the Dark: espaço de Esperança extra
            c.dano = f"{f.proficiencia}{c.dado}"   # usa a sua Proficiência
            c.estresse_marcado = min(s.companheiro_estresse, c.estresse_max)
            c.fora_de_cena = s.companheiro_fora
        return f

    def subir_de_nivel(self, subida: SubidaDeNivel) -> Ficha:
        """Valida e registra o nível. Se algo for inválido, nada muda.

        Cartas novas vão para o loadout; se ele estiver cheio, para o cofre.
        """
        nova = self._vestir(self._aplicar(self._ficha_base(), subida), self.equipamento)
        # ex.: subir a Presença com uma arma Pompous equipada
        self._validar_requisitos(nova, self.equipamento)
        self.historico.append(subida)
        if subida.troca_carta and subida.troca_carta[0] in self.cofre:
            antiga, nova_carta = subida.troca_carta   # a nova ocupa o lugar da antiga
            self.cofre[self.cofre.index(antiga)] = nova_carta
        self._ajustar_cofre()
        return self.ficha()

    def equipar(self, principal: str | None = None, secundaria: str | None = None,
                armadura: str | None = None) -> Ficha:
        """Define o equipamento completo; o que não for passado fica vazio.

        Tudo é validado antes de trocar, então um erro não muda nada.
        """
        novo = Equipamento(principal, secundaria, armadura)
        base = self._ficha_base()
        self._validar_equipamento(base, novo)
        self._validar_requisitos(self._vestir(base, novo), novo)
        self.equipamento = novo
        self.sessao.ajustar()   # armadura nova pode ter menos espaços
        return self.ficha()

    def desfazer_ultimo_nivel(self) -> None:
        if not self.historico:
            raise RegraViolada("Não há nível para desfazer.")
        self.historico.pop()
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

    # --- Cartas: loadout e cofre -----------------------------------------------

    def guardar_carta(self, carta: str) -> Ficha:
        """Move uma carta do loadout para o cofre (sem custo)."""
        if carta not in self._ficha_base().cartas:
            raise RegraViolada("Você só pode guardar uma carta que tem.")
        if carta in self.cofre:
            raise RegraViolada(f"{self._nome(self.bib.cartas, carta)} já está no cofre.")
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
            raise RegraViolada(f"{self._nome(self.bib.cartas, carta)} não está no cofre.")
        ativas = [c for c in self._ficha_base().cartas if c not in self.cofre]
        if no_lugar_de is not None and no_lugar_de not in ativas:
            raise RegraViolada("A carta que sai precisa estar no loadout.")
        if no_lugar_de is None and len(ativas) >= self._limite_loadout:
            raise RegraViolada(f"Loadout cheio ({self._limite_loadout}): escolha uma carta para guardar.")
        custo = 0 if em_descanso else self.bib.cartas[carta].custo_recall
        self.sessao.pagar_estresse(custo)   # recusa antes de mexer no cofre
        self.cofre.remove(carta)
        if no_lugar_de is not None:
            self.cofre.append(no_lugar_de)
        return custo

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
        for nivel in range(2, self.bib.progressao["nivel_maximo"] + 1):
            itens = []
            if str(nivel) in conquistas:
                c = conquistas[str(nivel)]
                itens.append("Conquista de tier: nova Experiência +2, +1 Proficiência"
                             + (", limpa marcas dos traços" if c["limpar_marcas_tracos"] else ""))
            subida = feitos.get(nivel)
            if subida:
                if subida.nova_experiencia:
                    itens.append(f"Nova Experiência: {subida.nova_experiencia} +2")
                itens += [self._descrever(e) for e in subida.escolhas]
                if subida.experiencia_companheiro:
                    itens.append(f"Companheiro: nova Experiência {subida.experiencia_companheiro} +2")
                itens += [self._descrever_treino(t) for t in subida.treinos]
                itens.append("Limiares de dano +1")
                itens.append(f"Carta: {self._nome(bib.cartas, subida.carta)}")
                if subida.troca_carta:
                    antiga, nova = subida.troca_carta
                    itens.append(f"Troca: {self._nome(bib.cartas, antiga)}"
                                 f" → {self._nome(bib.cartas, nova)}")
            else:
                itens += ["Escolher 2 avanços", "Limiares de dano +1", "Escolher 1 carta de domínio"]
            eventos.append({
                "nivel": nivel, "tier": self.bib.tier_do_nivel(nivel),
                "status": "feito" if subida else "futuro",
                "titulo": f"Nível {nivel}", "itens": itens,
            })
        return eventos

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
        if subclasse.classe != classe.nome:
            raise RegraViolada(f"{subclasse.nome} não é subclasse de {classe.nome}.")
        caracteristicas_anc = self._caracteristicas_ancestralidade(c)
        self._exigir(bib.comunidades, c.comunidade, "Comunidade")

        if set(c.tracos) != set(Traco):
            raise RegraViolada("Todos os seis traços precisam de um valor.")
        if sorted(c.tracos.values()) != DISTRIBUICAO_TRACOS:
            raise RegraViolada("Distribua exatamente +2, +1, +1, +0, +0 e -1 entre os traços.")

        nomes = [e.strip() for e in c.experiencias]
        if len(nomes) != 2 or "" in nomes or len(set(nomes)) != 2:
            raise RegraViolada("Escolha duas Experiências diferentes.")

        if len(c.cartas) != 2 or len(set(c.cartas)) != 2:
            raise RegraViolada("Escolha duas cartas de domínio diferentes.")
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
                raise RegraViolada("Purposeful Design: escolha uma das suas Experiências para ganhar +1.")
            f.experiencias[c.experiencia_proposito] += 1
        elif c.experiencia_proposito is not None:
            raise RegraViolada("Só Purposeful Design (Clank) dá +1 numa Experiência na criação.")

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
        if s.troca_carta:
            self._trocar_carta(f, *s.troca_carta)
        return f

    def _aplicar_escolha(self, f: Ficha, e: Escolha, tier_atual: int, nivel: int):
        tier = e.tier or tier_atual
        tabela = self.bib.progressao["opcoes"].get(str(tier))
        if tabela is None or tier > tier_atual:
            raise RegraViolada(f"Tier {tier} não está disponível no nível {nivel}.")
        if e.opcao.value not in tabela:
            raise RegraViolada(f"A opção {e.opcao.value} não existe no tier {tier}.")
        chave = (tier, e.opcao.value)
        if f.slots_usados.get(chave, 0) >= tabela[e.opcao.value]:
            raise RegraViolada(f"Não há mais espaços de {e.opcao.value} no tier {tier}.")
        if self._bloqueada(f, e.opcao, tier):
            raise RegraViolada(f"{e.opcao.value} foi bloqueada no tier {tier}.")

        o = e.opcao
        if o is Opcao.TRACOS:
            if len(set(e.tracos)) != 2:
                raise RegraViolada("Escolha dois traços diferentes.")
            if any(t in f.tracos_marcados for t in e.tracos):
                raise RegraViolada("Traço marcado só pode subir de novo após a próxima conquista de tier.")
            for t in e.tracos:
                f.tracos[t] += 1
                f.tracos_marcados.add(t)
        elif o is Opcao.PV:
            if f.pv_max >= self.bib.progressao["limite_pv"]:
                raise RegraViolada("Limite de Pontos de Vida atingido.")
            f.pv_max += 1
        elif o is Opcao.ESTRESSE:
            if f.estresse_max >= self.bib.progressao["limite_estresse"]:
                raise RegraViolada("Limite de Estresse atingido.")
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
        sub = self._exigir(self.bib.subclasses, e.subclasse, "Subclasse")
        if sub.classe != classe.nome:
            raise RegraViolada(f"{sub.nome} não é subclasse de {classe.nome}.")
        companheiro = self._ganhar_companheiro(sub, e.companheiro)
        f.multiclasse = {"classe": classe.id, "dominio": e.dominio, "subclasse": sub.id}
        f.multiclasse_bloqueada = True             # risca as outras multiclasses
        f.subclasse_bloqueada_tiers.add(tier)      # risca a subclasse deste tier
        if companheiro:
            f.companheiro = companheiro

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
        ativas = [c for c in cartas if c not in self.cofre]
        while len(ativas) > self._limite_loadout:
            self.cofre.append(ativas.pop())

    def _carta_permitida(self, f: Ficha, carta: CartaDeDominio, nivel_maximo: int,
                         nivel: int) -> bool:
        """Regra única de acesso a cartas, usada na validação E nas listagens."""
        if carta.dominio in self.bib.classes[f.classe].dominios and carta.nivel <= nivel_maximo:
            return True
        # domínio da multiclasse: "half your level or lower (rounded up)"
        metade = (nivel + 1) // 2
        return bool(f.multiclasse and carta.dominio == f.multiclasse["dominio"]
                    and carta.nivel <= min(nivel_maximo, metade))

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
                raise RegraViolada(f"{principal.nome} é mágica e exige um traço de conjuração.")
        if eq.secundaria:
            secundaria = self._exigir(bib.armas, eq.secundaria, "Arma")
            if secundaria.primaria:
                raise RegraViolada(f"{secundaria.nome} é uma arma principal.")
            if principal and principal.duas_maos:
                raise RegraViolada(f"{principal.nome} usa as duas mãos; não sobra mão para a secundária.")
        if eq.armadura:
            self._exigir(bib.armaduras, eq.armadura, "Armadura")

    def _subclasses(self, f: Ficha) -> list[Subclasse]:
        """A subclasse principal e, se houver, a da multiclasse."""
        ids = [f.subclasse]
        if f.multiclasse:
            ids.append(f.multiclasse["subclasse"])
        return [self.bib.subclasses[s] for s in ids]

    def _conjura(self, f: Ficha) -> bool:
        """Alguma subclasse do personagem (inclusive da multiclasse) tem traço de conjuração."""
        return any(s.traco_conjuracao for s in self._subclasses(f))

    def _vestir(self, f: Ficha, eq: Equipamento) -> Ficha:
        """Aplica o equipamento sobre uma ficha base (que é alterada).

        Ordem: valores base da armadura, depois os modificadores fixos de
        TODAS as peças (uma arma Heavy também tira Evasão), e por último os
        ataques, que já usam os traços modificados.
        O equipamento já foi validado em equipar().
        """
        armas = [self.bib.armas[a] for a in (eq.principal, eq.secundaria) if a]
        armadura = self.bib.armaduras[eq.armadura] if eq.armadura else None

        if armadura:
            f.limiar_maior = armadura.limiar_maior + f.nivel
            f.limiar_grave = armadura.limiar_grave + f.nivel
            f.pontuacao_armadura = armadura.pontuacao
            f.armadura = armadura.nome
            f.caracteristicas_armadura = list(armadura.caracteristicas)
        else:
            # regra do SRD para quem está sem armadura
            f.limiar_maior, f.limiar_grave, f.pontuacao_armadura = f.nivel, 2 * f.nivel, 0
        if any(c.efeito is Efeito.CASCO for c in f.caracteristicas_ancestralidade):
            # Shell (Galapa): limiares + Proficiência
            f.limiar_maior += f.proficiencia
            f.limiar_grave += f.proficiencia

        mods = [m for peca in self._pecas(eq) for c in peca.caracteristicas for m in c.modificadores]
        for m in mods:
            self._modificar(f, m)

        f.ataques = [self._ataque(f, arma) for arma in armas]
        bonus_conjuracao = sum(self._valor(f, m) for m in mods if m.alvo is Alvo.CONJURACAO)
        f.conjuracoes = [Conjuracao(sub.nome, sub.traco_conjuracao,
                                    f.tracos[sub.traco_conjuracao] + bonus_conjuracao)
                         for sub in self._subclasses(f) if sub.traco_conjuracao]
        return f

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
        # Alvo.ATAQUE e Alvo.DANO valem só para a própria arma (_ataque);
        # Alvo.CONJURACAO é somado nas conjurações, no fim de _vestir

    @staticmethod
    def _valor(f: Ficha, m: Modificador) -> int:
        """Valor do modificador nesta ficha (resolve "igual ao seu nível/traço")."""
        if m.igual_a is Referencia.NIVEL:
            return f.nivel
        if isinstance(m.igual_a, Traco):
            return f.tracos[m.igual_a]
        return m.valor

    def _ataque(self, f: Ficha, arma: Arma) -> Ataque:
        mods = [m for c in arma.caracteristicas for m in c.modificadores]
        bonus_ataque = sum(self._valor(f, m) for m in mods if m.alvo is Alvo.ATAQUE)
        bonus_dano = arma.modificador_dano + sum(
            self._valor(f, m) for m in mods if m.alvo is Alvo.DANO)
        dano = f"{f.proficiencia}{arma.dado}"
        if bonus_dano:
            dano += f"{bonus_dano:+d}"   # "+5" ou "-1"
        return Ataque(arma=arma.nome, traco=arma.traco,
                      bonus=f.tracos[arma.traco] + bonus_ataque,
                      alcance=arma.alcance, dano=dano, tipo_dano=arma.tipo_dano,
                      caracteristicas=list(arma.caracteristicas))

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
        """`f` já vestida com `eq`: o requisito vale para o traço como ele fica
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
        # O SRD guarda "BARD" e as subclasses comparam por esse valor,
        # então só formatamos na exibição.
        return self._nome(self.bib.classes, chave).title()

    @staticmethod
    def _descrever_treino(t: Treino) -> str:
        detalhe = f" ({t.experiencia})" if t.experiencia else f" ({t.alvo.value})" if t.alvo else ""
        return f"Treino do companheiro: {t.opcao.value}{detalhe}"

    def _descrever(self, e: Escolha) -> str:
        detalhe = ""
        if e.tracos:
            detalhe = " (" + ", ".join(t.rotulo for t in e.tracos) + ")"
        elif e.experiencias:
            detalhe = " (" + ", ".join(e.experiencias) + ")"
        elif e.carta:
            detalhe = f" ({self._nome(self.bib.cartas, e.carta)})"
        elif e.classe:
            detalhe = (f" ({self._nome_classe(e.classe)} / {e.dominio.title()}"
                       f" / {self._nome(self.bib.subclasses, e.subclasse)})")
        origem = f" [tier {e.tier}]" if e.tier else ""
        return f"Avanço: {e.opcao.value}{detalhe}{origem}"
