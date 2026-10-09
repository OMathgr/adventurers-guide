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

from .srd import Biblioteca, Traco

DISTRIBUICAO_TRACOS = sorted([2, 1, 1, 0, 0, -1])
ESTAGIOS_SUBCLASSE = ["fundacao", "especializacao", "maestria"]


class RegraViolada(Exception):
    """Uma escolha do jogador não é permitida pelas regras."""


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


@dataclass
class SubidaDeNivel:
    nivel: int
    escolhas: list[Escolha]
    carta: str                                   # passo 4: nova carta de domínio
    nova_experiencia: str | None = None          # só nos níveis 2, 5 e 8
    troca_carta: tuple[str, str] | None = None   # (carta antiga, carta nova)


# --- Saída: a ficha calculada ----------------------------------------------

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

    @property
    def bonus_limiares(self) -> int:
        """Somado aos limiares base da armadura (a regra soma o nível)."""
        return self.nivel


class Personagem:
    def __init__(self, biblioteca: Biblioteca, criacao: Criacao):
        self.bib = biblioteca
        self.criacao = criacao
        self.historico: list[SubidaDeNivel] = []
        self._ficha_inicial = self._criar(criacao)

    # --- API pública -------------------------------------------------------

    def ficha(self, ate_nivel: int | None = None) -> Ficha:
        ficha = copy.deepcopy(self._ficha_inicial)
        for subida in self.historico:
            if ate_nivel is not None and subida.nivel > ate_nivel:
                break
            ficha = self._aplicar(ficha, subida)
        return ficha

    def subir_de_nivel(self, subida: SubidaDeNivel) -> Ficha:
        """Valida e registra o nível. Se algo for inválido, nada muda."""
        nova = self._aplicar(self.ficha(), subida)
        self.historico.append(subida)
        return nova

    def desfazer_ultimo_nivel(self) -> None:
        if not self.historico:
            raise RegraViolada("Não há nível para desfazer.")
        self.historico.pop()

    def opcoes_disponiveis(self) -> list[dict]:
        """Avanços que ainda podem ser marcados no PRÓXIMO nível."""
        ficha = self.ficha()
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
        conquistas = self.bib.progressao["conquistas_de_tier"]
        eventos = [{
            "nivel": 1, "tier": 1, "status": "feito", "titulo": "Criação",
            "itens": [f"Classe: {self.criacao.classe}",
                      f"Subclasse: {self.criacao.subclasse}",
                      *(f"Experiência: {e} +2" for e in self.criacao.experiencias),
                      *(f"Carta: {c}" for c in self.criacao.cartas)],
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
                itens.append("Limiares de dano +1")
                itens.append(f"Carta: {subida.carta}")
                if subida.troca_carta:
                    itens.append(f"Troca: {subida.troca_carta[0]} → {subida.troca_carta[1]}")
            else:
                itens += ["Escolher 2 avanços", "Limiares de dano +1", "Escolher 1 carta de domínio"]
            eventos.append({
                "nivel": nivel, "tier": self.bib.tier_do_nivel(nivel),
                "status": "feito" if subida else "futuro",
                "titulo": f"Nível {nivel}", "itens": itens,
            })
        return eventos

    # --- Criação -----------------------------------------------------------

    def _criar(self, c: Criacao) -> Ficha:
        bib = self.bib
        classe = self._exigir(bib.classes, c.classe, "Classe")
        subclasse = self._exigir(bib.subclasses, c.subclasse, "Subclasse")
        if subclasse.classe != classe.nome:
            raise RegraViolada(f"{subclasse.nome} não é subclasse de {classe.nome}.")
        self._exigir(bib.ancestralidades, c.ancestralidade, "Ancestralidade")
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

        return Ficha(
            nome=c.nome, nivel=1, classe=classe.id, subclasse=subclasse.id,
            estagio_subclasse="fundacao", ancestralidade=c.ancestralidade,
            comunidade=c.comunidade, tracos=dict(c.tracos),
            evasao=classe.evasao_inicial, pv_max=classe.pv_iniciais,
            estresse_max=6, esperanca=2, proficiencia=1,
            experiencias={n: 2 for n in nomes}, cartas=list(c.cartas),
        )

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
        elif s.nova_experiencia:
            raise RegraViolada(f"O nível {s.nivel} não dá nova Experiência.")

        # Passo 2: avanços
        custo_total = sum(self._custo(e.opcao) for e in s.escolhas)
        if custo_total != prog["avancos_por_nivel"]:
            raise RegraViolada("Escolha exatamente 2 avanços (Proficiência e Multiclasse valem por 2).")
        for escolha in s.escolhas:
            self._aplicar_escolha(f, escolha, tier, s.nivel)

        # Passo 3: limiares de dano sobem junto com o nível (ver bonus_limiares)
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
            limite = min(nivel, self.bib.progressao["nivel_maximo_carta_extra_por_tier"][str(tier)])
            self._validar_nova_carta(f, e.carta, limite, nivel)
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
        f.multiclasse = {"classe": classe.id, "dominio": e.dominio, "subclasse": sub.id}
        f.multiclasse_bloqueada = True             # risca as outras multiclasses
        f.subclasse_bloqueada_tiers.add(tier)      # risca a subclasse deste tier

    def _validar_nova_carta(self, f: Ficha, carta_id, nivel_maximo: int, nivel: int):
        carta = self._exigir(self.bib.cartas, carta_id, "Carta")
        if carta_id in f.cartas:
            raise RegraViolada(f"Você já tem {carta.nome}.")
        dominios = self.bib.classes[f.classe].dominios
        if carta.dominio in dominios and carta.nivel <= nivel_maximo:
            return
        if (f.multiclasse and carta.dominio == f.multiclasse["dominio"]
                and carta.nivel <= min(nivel_maximo, nivel // 2)):
            return
        raise RegraViolada(f"{carta.nome} (nível {carta.nivel}, {carta.dominio}) não está disponível.")

    def _trocar_carta(self, f: Ficha, antiga: str, nova: str):
        if antiga not in f.cartas:
            raise RegraViolada("Você só pode trocar uma carta que já tem.")
        nivel_antiga = self.bib.cartas[antiga].nivel
        self._validar_nova_carta(f, nova, nivel_antiga, f.nivel)
        f.cartas[f.cartas.index(antiga)] = nova

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

    @staticmethod
    def _descrever(e: Escolha) -> str:
        detalhe = ""
        if e.tracos:
            detalhe = " (" + ", ".join(t.name.title() for t in e.tracos) + ")"
        elif e.experiencias:
            detalhe = " (" + ", ".join(e.experiencias) + ")"
        elif e.carta:
            detalhe = f" ({e.carta})"
        elif e.classe:
            detalhe = f" ({e.classe} / {e.dominio})"
        origem = f" [tier {e.tier}]" if e.tier else ""
        return f"Avanço: {e.opcao.value}{detalhe}{origem}"
