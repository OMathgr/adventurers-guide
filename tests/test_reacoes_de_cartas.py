"""Cartas disparadas por rolagens (etapa 3 das cartas): o registro oferece a
carta na rolagem certa (crítico, sucesso, falha, com Medo, dano), uma vez por
rolagem, e as que mudam a rolagem a refazem (soma, vira com Esperança)."""

import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco
from motor.rolagem import Dualidade

TRACOS = {Traco.FORCA: 2, Traco.AGILIDADE: 1, Traco.INSTINTO: 1, Traco.ACUIDADE: 0, Traco.PRESENCA: 0,
          Traco.CONHECIMENTO: -1}
ESPADA = "core_weapon_broadsword"


def carta(nome: str) -> str:
    return f"core_domain_card_{nome}"


class Dados:
    def __init__(self, *valores):
        self.valores = list(valores)

    def randint(self, a, b):
        return self.valores.pop(0)


def escolhas(nivel: int) -> list[Escolha]:
    posicao = {2: 0, 3: 1, 4: 2, 5: 0, 6: 1, 7: 2, 8: 0, 9: 1, 10: 2}[nivel]
    return [[Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.TRACOS, tracos=(Traco.ACUIDADE, Traco.PRESENCA)), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.EVASAO), Escolha(Opcao.EXPERIENCIAS, experiencias=("A", "B"))]][posicao]


def criar(bib, classe, subclasse, iniciais, nivel=1, cartas: dict[int, str] = {}, nome="T"):
    p = Personagem(bib, Criacao(nome=nome, classe=classe, subclasse=subclasse, ancestralidade="core_ancestry_faun",
                                comunidade="core_community_highborne", tracos=dict(TRACOS),
                                experiencias=["A", "B"], cartas=[carta(c) for c in iniciais]))
    for n in range(2, nivel + 1):
        escolhida = cartas.get(n) or next(c.id for c in p.cartas_para_nivel()
                                          if not (c.passivo or c.escolha or c.fora_do_limite or (c.uso and c.uso.gatilho)))
        p.subir_de_nivel(SubidaDeNivel(n, escolhas(n), escolhida, nova_experiencia=f"E{n}" if n in (2, 5, 8) else None))
    for c in cartas.values():
        if c in p.cofre:
            sai = next(x for x in p.ficha().cartas_ativas if x not in cartas.values())
            p.recuperar_carta(c, no_lugar_de=sai, em_descanso=True)
    return p


def guardiao(bib, **kw):
    p = criar(bib, "core_class_guardian", "core_subclass_vengeance", ["get_back_up", "i_am_your_shield"], **kw)
    p.equipar(principal=ESPADA)
    return p


def ataque(p, esperanca, medo, dificuldade=None):
    p.sessao.rng = Dados(esperanca, medo)
    return p.rolar_teste("ataque", 0, dificuldade=dificuldade)


# --- o gatilho certo -----------------------------------------------------------------------------

def test_glancing_blow_so_na_falha_do_ataque(bib):
    p = guardiao(bib, nivel=7, cartas={7: carta("glancing_blow")})
    acerto = ataque(p, 10, 3, dificuldade=10)
    assert carta("glancing_blow") not in p.cartas_para_rolagem(acerto, propria=True)
    erro = ataque(p, 2, 3, dificuldade=20)
    assert carta("glancing_blow") in p.cartas_para_rolagem(erro, propria=True)
    sem_dificuldade = ataque(p, 2, 3)   # sem Dificuldade, o app não sabe: oferece (o mestre confere)
    assert carta("glancing_blow") in p.cartas_para_rolagem(sem_dificuldade, propria=True)
    with pytest.raises(RegraViolada, match="não vale para esta rolagem"):
        p.usar_carta(carta("glancing_blow"), rolagem=acerto)
    r = p.usar_carta(carta("glancing_blow"), rolagem=erro)
    assert p.sessao.estresse_marcado == 1 and "metade da Proficiência" in r.teste
    assert carta("glancing_blow") not in p.cartas_para_rolagem(erro, propria=True)   # uma vez por rolagem


def test_champions_edge_uma_vez_cada_opcao_no_critico(bib):
    p = guardiao(bib, nivel=5, cartas={5: carta("champions_edge")})
    p.sessao.esperanca, p.sessao.pv_marcados = 4, 2
    comum = ataque(p, 9, 3)
    assert carta("champions_edge") not in p.cartas_para_rolagem(comum, propria=True)
    critico = ataque(p, 7, 7)
    assert critico.dualidade is Dualidade.CRITICO
    p.usar_carta(carta("champions_edge"), opcao="pv", rolagem=critico)
    with pytest.raises(RegraViolada, match="já foi usada nesta rolagem"):
        p.usar_carta(carta("champions_edge"), opcao="pv", rolagem=critico)
    p.usar_carta(carta("champions_edge"), opcao="alvo", rolagem=critico)
    assert p.sessao.pv_marcados == 1 and carta("champions_edge") in p.cartas_para_rolagem(critico, propria=True)


def test_dano_dispara_healing_strike_no_aliado(bib):
    p = criar(bib, "core_class_seraph", "core_subclass_winged_sentinel", ["bolt_beacon", "mending_touch"],
              nivel=7, cartas={7: carta("healing_strike")})
    p.equipar(principal=ESPADA)
    aliado = guardiao(bib, nome="Bram")
    aliado.sessao.pv_marcados = 2
    p.sessao.esperanca, p.sessao.rng = 3, Dados(5, 5, 5)   # Proficiência 3 no nível 7
    dano = p.rolar_dano(ataque=0)
    assert carta("healing_strike") in p.cartas_para_rolagem(dano, propria=True)
    p.usar_carta(carta("healing_strike"), [aliado], rolagem=dano)
    assert aliado.sessao.pv_marcados == 1 and p.sessao.esperanca == 1


# --- cartas que mudam a rolagem ---------------------------------------------------------------------

def test_wild_surge_soma_o_dado_e_sobe(bib):
    p = criar(bib, "core_class_druid", "core_subclass_warden_of_the_elements", ["gifted_tracker", "vicious_entangle"],
              nivel=7, cartas={7: carta("wild_surge")})
    p.usar_carta(carta("wild_surge"), opcao="ativar")
    with pytest.raises(RegraViolada, match="use pela rolagem"):
        p.usar_carta(carta("wild_surge"), opcao="subir")
    p.sessao.rng = Dados(5, 4)
    r = p.rolar_teste("atributo", "STRENGTH", dificuldade=12)
    assert r.total == 5 + 4 + 2 and r.sucesso is False
    uso = p.usar_carta(carta("wild_surge"), opcao="subir", rolagem=r)
    novo = uso.rolagem
    assert novo.total == r.total + 1 and novo.sucesso is True and novo.reacao_de
    assert p.marcadores_da_carta(carta("wild_surge")) == 2
    assert "core_domain_card_wild_surge:subir" in novo.cartas_usadas


def test_stealth_expertise_vira_com_esperanca_na_rolagem_do_aliado(bib):
    p = criar(bib, "core_class_rogue", "core_subclass_nightwalker", ["pick_and_pull", "rain_of_blades"],
              nivel=4, cartas={4: carta("stealth_expertise")})
    aliado = guardiao(bib, nome="Bram")
    aliado.sessao.rng = Dados(3, 9)
    r = aliado.rolar_teste("atributo", "AGILITY")
    assert r.dualidade is Dualidade.MEDO and r.medo_gerado == 1
    esperanca = aliado.sessao.esperanca
    assert carta("stealth_expertise") in p.cartas_para_rolagem(r, propria=False)   # rolagem de aliado também
    uso = p.usar_carta(carta("stealth_expertise"), rolagem=r, dono_da_rolagem=aliado)
    novo = uso.rolagem
    assert novo.dualidade is Dualidade.ESPERANCA and novo.medo_gerado == 0
    assert aliado.sessao.esperanca == esperanca + 1 and p.sessao.estresse_marcado == 1
