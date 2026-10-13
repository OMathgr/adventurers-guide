"""Encontros: cópias de adversários em combate, dano pelos limiares e Medo."""

import pytest

from motor import Biblioteca, RegraViolada
from motor.encontro import Encontro, ajustar_medo, definir_medo
from motor.numeros import metade
from motor.sessao import Gravidade


@pytest.fixture(scope="module")
def adversarios():
    return Biblioteca().adversarios


def test_copias_ganham_numero_e_continuam_a_contagem(adversarios):
    lobo = adversarios["srd_dire_wolf"]
    e = Encontro("Emboscada")
    sozinho, = e.adicionar(lobo)
    assert sozinho.rotulo == lobo.nome
    e.adicionar(lobo, quantidade=2)
    assert [c.rotulo for c in e.combatentes] == [f"{lobo.nome} {i}" for i in (1, 2, 3)]
    assert len({c.id for c in e.combatentes}) == 3


def test_copia_nao_muda_com_o_original(adversarios):
    original = adversarios["srd_dire_wolf"]
    c, = Encontro("x").adicionar(original)
    c.adversario.pv = 99
    assert original.pv != 99


def test_dano_pelos_limiares(adversarios):
    # Acid Burrower: limiares 8/15, 8 PV
    e = Encontro("x")
    c, = e.adicionar(adversarios["srd_acid_burrower"])
    assert (c.adversario.limiar_maior, c.adversario.limiar_grave) == (8, 15)
    assert c.receber_dano(7).gravidade is Gravidade.MENOR and c.pv_marcados == 1
    assert c.receber_dano(8).gravidade is Gravidade.MAIOR and c.pv_marcados == 3
    assert c.receber_dano(15).gravidade is Gravidade.GRAVE and c.pv_marcados == 6
    r = c.receber_dano(20)
    assert r.pv_marcados == 2 and r.derrotado and c.derrotado   # não passa do total
    with pytest.raises(RegraViolada, match="derrotado"):
        c.receber_dano(5)


def test_resistencia_reduz_antes_dos_limiares(adversarios):
    c, = Encontro("x").adicionar(adversarios["srd_acid_burrower"])
    r = c.receber_dano(16, resistente=True)    # 8: Maior, não Grave
    assert (r.dano, r.gravidade, c.pv_marcados) == (8, Gravidade.MAIOR, 2)
    # metade arredonda para cima (convenção do projeto): 15 -> 8 é Maior, 1 -> 1
    r = c.receber_dano(15, resistente=True)
    assert (r.dano, r.gravidade) == (8, Gravidade.MAIOR)
    assert c.receber_dano(1, resistente=True).dano == 1


def test_metade_arredonda_para_cima():
    assert [metade(n) for n in (0, 1, 2, 5, 15, 16)] == [0, 1, 1, 3, 8, 8]


def test_lacaio_cai_com_qualquer_dano(adversarios):
    rato, = Encontro("x").adicionar(adversarios["srd_giant_rat"])
    assert rato.receber_dano(1).derrotado


def test_marcas_por_clique_e_condicoes(adversarios):
    c, = Encontro("x").adicionar(adversarios["srd_acid_burrower"])
    c.definir_marcas(pv=2, pf=1)
    assert (c.pv_marcados, c.pf_marcados) == (2, 1)
    with pytest.raises(RegraViolada, match="PF marcados"):
        c.definir_marcas(pv=0, pf=c.adversario.pf + 1)
    assert c.aplicar_condicao("vulnerable") == "VULNERAVEL"
    c.aplicar_condicao("Envolvido")
    with pytest.raises(RegraViolada, match="já está"):
        c.aplicar_condicao("VULNERAVEL")
    c.remover_condicao("VULNERAVEL")
    assert c.condicoes == ["Envolvido"]


def test_remover_e_limite_de_copias(adversarios):
    e = Encontro("x")
    c, = e.adicionar(adversarios["srd_giant_rat"])
    e.remover(c.id)
    assert e.combatentes == []
    with pytest.raises(RegraViolada):
        e.adicionar(adversarios["srd_giant_rat"], quantidade=21)
    with pytest.raises(RegraViolada, match="não está"):
        e.remover("nao-existe")


def test_medo():
    assert ajustar_medo(11, 3) == 12          # para no máximo
    assert ajustar_medo(5, -2) == 3
    with pytest.raises(RegraViolada, match="insuficiente"):
        ajustar_medo(1, -2)
    assert definir_medo(4) == 4
    with pytest.raises(RegraViolada):
        definir_medo(13)


def test_vitalidade_em_tercos():
    from motor.encontro import vitalidade
    assert [vitalidade(6, m) for m in range(7)] == [
        "vida_cheia", "vida_cheia", "metade_da_vida", "metade_da_vida", "vida_baixa", "vida_baixa", "derrotado"]
    assert vitalidade(1, 0) == "vida_cheia" and vitalidade(1, 1) == "derrotado"        # lacaio
    assert [vitalidade(3, m) for m in range(4)] == ["vida_cheia", "metade_da_vida", "vida_baixa", "derrotado"]


def test_combatente_comeca_visivel_e_tem_vitalidade(adversarios):
    c, = Encontro("x").adicionar(adversarios["srd_acid_burrower"])
    assert c.escondido is False and c.vitalidade == "vida_cheia"
    c.definir_marcas(pv=c.adversario.pv, pf=0)
    assert c.vitalidade == "derrotado"
