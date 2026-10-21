"""Cartas de domínio no dano recebido e no movimento de morte (etapa 1 das
cartas): Get Back Up, Shrug It Off, Brace, Rune Ward, Unyielding Armor, On the
Brink, Rise Up, Battle Hardened, Unbreakable, e Notorious fora do limite da mão."""

import pytest

from motor import Criacao, Escolha, Opcao, Personagem, RegraViolada, SubidaDeNivel, Traco
from motor.sessao import Gravidade

COURO = "core_armor_leather_armor"   # limiares 6/13, Pontuação 3
TRACOS = {Traco.PRESENCA: 2, Traco.AGILIDADE: 1, Traco.CONHECIMENTO: 1,
          Traco.ACUIDADE: 0, Traco.INSTINTO: 0, Traco.FORCA: -1}


def carta(nome: str) -> str:
    return f"core_domain_card_{nome}"


class Dados:
    """rng falso: devolve os valores na ordem."""
    def __init__(self, *valores):
        self.valores = list(valores)

    def randint(self, a, b):
        return self.valores.pop(0)


def escolhas(nivel: int) -> list[Escolha]:
    """Avanços que cabem do nível 2 ao 10 (um PV por patamar: não estoura o limite)."""
    posicao = {2: 0, 3: 1, 4: 2, 5: 0, 6: 1, 7: 2, 8: 0, 9: 1, 10: 2}[nivel]
    return [[Escolha(Opcao.PV), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.TRACOS, tracos=(Traco.ACUIDADE, Traco.INSTINTO)), Escolha(Opcao.ESTRESSE)],
            [Escolha(Opcao.EVASAO), Escolha(Opcao.EXPERIENCIAS, experiencias=("A", "B"))]][posicao]


def criar(bib, classe, subclasse, iniciais, nivel=1, cartas: dict[int, str] = {}):
    p = Personagem(bib, Criacao(nome="T", classe=classe, subclasse=subclasse, ancestralidade="core_ancestry_faun",
                                comunidade="core_community_highborne", tracos=dict(TRACOS),
                                experiencias=["A", "B"], cartas=iniciais))
    for n in range(2, nivel + 1):
        escolhida = cartas.get(n) or next(c.id for c in p.cartas_para_nivel()
                                          if not (c.passivo or c.escolha or c.fora_do_limite))
        p.subir_de_nivel(SubidaDeNivel(n, escolhas(n), escolhida, nova_experiencia=f"E{n}" if n in (2, 5, 8) else None))
    return p


def na_mao(p, *ids):
    """Deixa estas cartas na mão (manda outras para a reserva se precisar)."""
    for c in ids:
        if c in p.cofre:
            sai = next(x for x in p.ficha().cartas_ativas if x not in ids)
            p.recuperar_carta(c, no_lugar_de=sai, em_descanso=True)


def guardiao(bib, nivel=1, cartas: dict[int, str] = {}, iniciais=("get_back_up", "i_am_your_shield")):
    return criar(bib, "core_class_guardian", "core_subclass_vengeance", [carta(c) for c in iniciais], nivel, cartas)


# --- Get Back Up, Shrug It Off -------------------------------------------------------------------

def test_get_back_up_so_no_dano_grave(bib):
    p = guardiao(bib)
    p.equipar(armadura=COURO)   # limiares 7/14 no nível 1
    assert [d.carta for d in p.ficha().defesas_de_carta] == [carta("get_back_up")]
    r = p.sessao.receber_dano(1, cartas=[carta("get_back_up")])   # Menor: não precisa, não paga
    assert (r.pv_marcados, p.sessao.estresse_marcado) == (1, 0)
    r = p.sessao.receber_dano(30, cartas=[carta("get_back_up")])   # Grave
    assert r.gravidade is Gravidade.GRAVE and r.pv_marcados == 2 and p.sessao.estresse_marcado == 1
    assert any("reduziu um nível" in n for n in r.notas)


def test_carta_de_defesa_precisa_estar_na_mao_e_do_custo(bib):
    p = guardiao(bib)
    with pytest.raises(RegraViolada, match="não se usa ao receber dano"):
        p.sessao.receber_dano(5, cartas=[carta("i_am_your_shield")])
    p.guardar_carta(carta("get_back_up"))
    with pytest.raises(RegraViolada, match="precisa estar na mão"):
        p.sessao.receber_dano(5, cartas=[carta("get_back_up")])
    p.recuperar_carta(carta("get_back_up"), em_descanso=True)
    p.sessao.estresse_marcado = p.ficha().estresse_max
    with pytest.raises(RegraViolada, match="Fadiga insuficiente"):
        p.sessao.receber_dano(30, cartas=[carta("get_back_up")])
    assert p.sessao.pv_marcados == 0   # recusou antes de marcar


def test_shrug_it_off_vai_para_a_reserva_com_d6_baixo(bib):
    p = guardiao(bib, 7, {7: carta("shrug_it_off")})
    na_mao(p, carta("shrug_it_off"))
    p.sessao.rng = Dados(5)
    r = p.sessao.receber_dano(30, cartas=[carta("shrug_it_off")])
    assert r.pv_marcados == 2 and carta("shrug_it_off") not in p.cofre
    p.sessao.rng = Dados(3)
    p.sessao.receber_dano(30, cartas=[carta("shrug_it_off")])
    assert carta("shrug_it_off") in p.cofre


# --- armadura: Brace e Unyielding Armor ---------------------------------------------------------

def test_brace_marca_mais_um_espaco(bib):
    p = criar(bib, "core_class_warrior", "core_subclass_call_of_the_brave",
              [carta("get_back_up"), carta("whirlwind")], 3, {3: carta("brace")})
    na_mao(p, carta("brace"))
    with pytest.raises(RegraViolada, match="só vale quando você marca armadura"):
        p.sessao.receber_dano(30, cartas=[carta("brace")])
    p.equipar(armadura=COURO)
    r = p.sessao.receber_dano(30, usar_armadura=True, cartas=[carta("brace")])
    assert (r.pv_marcados, r.espacos_marcados, p.sessao.armadura_marcada, p.sessao.estresse_marcado) == (1, 2, 2, 1)


def test_unyielding_armor_reduz_sem_marcar_com_um_6(bib):
    p = guardiao(bib, 10, {10: carta("unyielding_armor")})
    na_mao(p, carta("unyielding_armor"))
    p.equipar(armadura=COURO)
    p.sessao.rng = Dados(2, 6, 1, 4)   # Proficiência 4 no nível 10
    r = p.sessao.receber_dano(100, usar_armadura=True)
    assert r.usou_armadura and r.pv_marcados == 2 and p.sessao.armadura_marcada == 0
    p.sessao.rng = Dados(1, 2, 3, 4)   # sem 6: marca o espaço normalmente
    r = p.sessao.receber_dano(100, usar_armadura=True)
    assert r.pv_marcados == 2 and p.sessao.armadura_marcada == 1


# --- Rune Ward ------------------------------------------------------------------------------------

def test_rune_ward_reduz_1d8_e_apaga_no_8(bib):
    p = criar(bib, "core_class_sorcerer", "core_subclass_elemental_origin",
              [carta("rune_ward"), carta("unleash_chaos")])
    p.equipar(armadura=COURO)   # limiares 7/14
    p.sessao.esperanca = 3
    p.sessao.rng = Dados(5)
    r = p.sessao.receber_dano(6, cartas=[carta("rune_ward")])   # 6 - 5 = 1: Menor
    assert r.dano == 1 and r.pv_marcados == 1 and p.sessao.esperanca == 2
    p.sessao.rng = Dados(8)
    p.sessao.receber_dano(9, cartas=[carta("rune_ward")])
    assert carta("rune_ward") not in [d.carta for d in p.ficha().defesas_de_carta]
    with pytest.raises(RegraViolada, match="próximo descanso"):
        p.sessao.receber_dano(9, cartas=[carta("rune_ward")])
    p.sessao.terminar_repouso(longo=False)
    assert carta("rune_ward") in [d.carta for d in p.ficha().defesas_de_carta]


# --- automáticas: On the Brink e Rise Up -------------------------------------------------------------

def test_on_the_brink_ignora_dano_menor_com_pouco_pv(bib):
    p = criar(bib, "core_class_warrior", "core_subclass_call_of_the_brave",
              [carta("get_back_up"), carta("whirlwind")], 9, {9: carta("on_the_brink")})
    na_mao(p, carta("on_the_brink"))
    p.sessao.pv_marcados = p.ficha().pv_max - 3
    assert p.sessao.receber_dano(1).pv_marcados == 1   # ainda com 3: sofre
    r = p.sessao.receber_dano(1)                       # com 2: não sofre o Menor
    assert r.pv_marcados == 0 and any("não sofre dano Menor" in n for n in r.notas)


def test_rise_up_soma_proficiencia_no_grave_e_limpa_pf(bib):
    p = guardiao(bib, 6, {6: carta("rise_up")})
    sem = p.ficha().limiar_grave
    na_mao(p, carta("rise_up"))
    f = p.ficha()
    assert f.limiar_grave == sem + f.proficiencia and carta("rise_up") in f.cartas_aplicadas
    p.sessao.estresse_marcado = 2
    p.sessao.receber_dano(1)
    assert p.sessao.estresse_marcado == 1


# --- no lugar do movimento de morte -----------------------------------------------------------------

def test_battle_hardened_uma_vez_por_descanso_longo(bib):
    p = guardiao(bib, 6, {6: carta("battle_hardened")})
    na_mao(p, carta("battle_hardened"))
    with pytest.raises(RegraViolada, match="último PV"):
        p.sessao.evitar_morte_com_carta(carta("battle_hardened"))
    p.sessao.pv_marcados = p.ficha().pv_max
    assert p.ficha().alternativas_a_morte == [carta("battle_hardened")]
    esperanca = p.sessao.esperanca
    p.sessao.evitar_morte_com_carta(carta("battle_hardened"))
    assert p.sessao.pv_marcados == p.ficha().pv_max - 1 and p.sessao.esperanca == esperanca - 1
    p.sessao.pv_marcados = p.ficha().pv_max
    with pytest.raises(RegraViolada, match="descanso longo"):
        p.sessao.evitar_morte_com_carta(carta("battle_hardened"))
    p.sessao.terminar_repouso(longo=False)   # curto não devolve
    assert p.ficha().alternativas_a_morte == []


def test_unbreakable_limpa_d6_e_vai_para_a_reserva(bib):
    p = guardiao(bib, 10, {10: carta("unbreakable")})
    na_mao(p, carta("unbreakable"))
    p.sessao.pv_marcados = p.ficha().pv_max
    notas = p.sessao.evitar_morte_com_carta(carta("unbreakable"), rolagem=4)
    assert p.sessao.pv_marcados == p.ficha().pv_max - 4 and carta("unbreakable") in p.cofre
    assert "reserva" in notas[0]


# --- Notorious ------------------------------------------------------------------------------------------

def test_notorious_nao_conta_na_mao_nem_vai_para_a_reserva(bib):
    p = criar(bib, "core_class_bard", "core_subclass_troubadour",
              [carta("inspirational_words"), carta("book_of_ava")], 10, {10: carta("notorious")})
    f = p.ficha()
    assert carta("notorious") in f.cartas_ativas
    assert len([c for c in f.cartas_ativas if c != carta("notorious")]) == 5   # a mão cheia continua 5
    with pytest.raises(RegraViolada, match="não vai para a reserva"):
        p.guardar_carta(carta("notorious"))
    opcoes = {o.id: o for o in p.opcoes_de_rolagem("teste", "PRESENCE")}
    assert opcoes["notorious"].custo_fadiga == 1
