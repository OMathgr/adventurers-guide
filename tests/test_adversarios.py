import copy

import pytest

from motor import RegraViolada, TipoAdversario, TipoDano, TipoHabilidade
from motor.adversarios import validar


def test_todos_os_adversarios_do_srd_sao_lidos_e_validos(bib):
    assert len(bib.adversarios) == 129
    for a in bib.adversarios.values():
        validar(a)


def test_ficha_completa(bib):
    a = bib.adversarios["srd_acid_burrower"]
    assert (a.nome, a.patamar, a.tipo, a.dificuldade) == ("Acid Burrower", 1, TipoAdversario.SOLO, 14)
    assert (a.limiar_maior, a.limiar_grave, a.pv, a.pf) == (8, 15, 8, 3)
    assert (a.ataque, a.arma, a.alcance, a.dano, a.tipo_dano) == ("+3", "Claws", "VERY_CLOSE", "1d12+2", TipoDano.FISICO)
    assert a.experiencias == {"Tremor Sense": 2}
    assert [(h.nome, h.tipo) for h in a.habilidades][:2] == [
        ("Relentless (3)", TipoHabilidade.PASSIVA), ("Earth Eruption", TipoHabilidade.ACAO)]


def test_casos_especiais_do_srd(bib):
    rato = bib.adversarios["srd_giant_rat"]
    assert rato.tipo is TipoAdversario.LACAIO and rato.limiar_maior is None
    mosquitos = bib.adversarios["srd_giant_mosquitoes"]
    assert (mosquitos.tipo, mosquitos.horda_por_pv) == (TipoAdversario.HORDA, 5)
    assert bib.adversarios["srd_tiny_green_ooze"].limiar_grave is None       # só limiar maior
    assert bib.adversarios["srd_spellblade"].tipo_dano is TipoDano.FISICO_OU_MAGICO
    assert bib.adversarios["srd_outer_realms_abomination"].ataque == "+2d4"
    contagem = [h for a in bib.adversarios.values() for h in a.habilidades if h.detalhe]
    assert any(h.detalhe.startswith("Countdown") for h in contagem)


@pytest.fixture
def base(bib):
    return copy.deepcopy(bib.adversarios["srd_acid_burrower"])


@pytest.mark.parametrize("mudanca, mensagem", [
    ({"nome": " "}, "nome"),
    ({"patamar": 5}, "patamar"),
    ({"pv": 0}, "PV"),
    ({"limiar_grave": 5}, "Grave"),
    ({"limiar_maior": None}, "Maior"),
    ({"dano": "muito"}, "Dano"),
    ({"ataque": "3"}, "Ataque"),
    ({"alcance": "LONGE"}, "Alcance"),
    ({"horda_por_pv": 3}, "hordas"),
])
def test_validacao_de_inimigo_criado(base, mudanca, mensagem):
    for campo, valor in mudanca.items():
        setattr(base, campo, valor)
    with pytest.raises(RegraViolada, match=mensagem):
        validar(base)


def test_lacaio_nao_tem_limiares(base):
    base.tipo = TipoAdversario.LACAIO
    with pytest.raises(RegraViolada, match="Lacaios"):
        validar(base)
    base.limiar_maior = base.limiar_grave = None
    validar(base)
