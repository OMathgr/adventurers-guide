"""Guia de Batalha: os três encontros do exemplo do livro (grupo de 4 PJs)."""

import pytest

from motor import RegraViolada
from motor.adversarios import TipoAdversario as T
from motor.guia_batalha import OpcoesDoGuia, calcular


def inimigos(*pares, patamar=1):
    return [(tipo, patamar) for tipo, n in pares for _ in range(n)]


def test_encontro_mais_facil():
    g = calcular(OpcoesDoGuia(pjs=4, mais_facil=True), inimigos((T.BRUTAMONTES, 2), (T.PADRAO, 2), (T.LACAIO, 4)))
    assert (g.base, g.total) == (14, 13)
    assert {(x.tipo, x.custo) for x in g.gastos} == {(T.BRUTAMONTES, 8), (T.PADRAO, 4), (T.LACAIO, 1)}
    assert (g.gasto, g.saldo) == (13, 0)


def test_sem_pesados_ganha_1_e_lacaios_contam_por_grupo():
    g = calcular(OpcoesDoGuia(pjs=4), inimigos((T.PADRAO, 5), (T.ATIRADOR, 1), (T.LACAIO, 8)))
    assert [(a.valor, a.automatico) for a in g.ajustes] == [(1, True)]     # nenhum brutamonte/horda/líder/solo
    assert g.total == 15 and g.gasto == 10 + 2 + 2                        # 8 lacaios = 2 grupos de 4
    # grupo incompleto conta inteiro (arredonda para cima)
    assert calcular(OpcoesDoGuia(pjs=4), inimigos((T.LACAIO, 5))).gasto == 2


def test_dano_extra_e_composicao_pesada():
    g = calcular(OpcoesDoGuia(pjs=4, dano_extra=True),
                 inimigos((T.LIDER, 1), (T.BRUTAMONTES, 1), (T.HORDA, 2), (T.SUPORTE, 1)))
    assert (g.total, g.gasto, g.saldo) == (12, 12, 0)


def test_ajustes_automaticos_de_solos_e_patamar():
    g = calcular(OpcoesDoGuia(pjs=3, patamar=2, mais_dificil=True), [(T.SOLO, 2), (T.SOLO, 1)])
    valores = {a.descricao: a.valor for a in g.ajustes}
    assert valores == {"2 ou mais solos": -2, "Adversários de patamar inferior (+1 por patamar, cada)": 1,
                       "Luta mais difícil ou longa": 2}
    assert (g.base, g.total, g.gasto, g.saldo) == (11, 12, 10, 2)


def _patamar(g):
    return {a.descricao.split(" (")[0]: a.valor for a in g.ajustes if "patamar" in a.descricao}


def test_regra_da_casa_patamar_por_inimigo_e_por_nivel():
    # mesa no patamar 3: dois de patamar 1 dão +2 cada; um de patamar 4 tira 1
    g = calcular(OpcoesDoGuia(pjs=4, patamar=3), [(T.PADRAO, 1), (T.PADRAO, 1), (T.BRUTAMONTES, 4), (T.LIDER, 3)])
    assert _patamar(g) == {"Adversários de patamar inferior": 4, "Adversários de patamar superior": -1}
    assert g.total == 14 + 4 - 1


def test_lacaios_contam_o_patamar_por_grupo():
    # 8 lacaios de patamar 1 com 4 PJs = 2 grupos; mesa no patamar 3: +2 por grupo
    g = calcular(OpcoesDoGuia(pjs=4, patamar=3), inimigos((T.LACAIO, 8), patamar=1))
    assert _patamar(g) == {"Adversários de patamar inferior": 4}


def test_custos_vem_no_guia_para_a_tela():
    g = calcular(OpcoesDoGuia(), [])
    assert g.custos[T.LACAIO] == 1 and g.custos[T.SOLO] == 5 and g.custos[T.SUPORTE] == 1


def test_passar_do_orcamento_e_permitido_mas_aparece():
    assert calcular(OpcoesDoGuia(pjs=1), inimigos((T.SOLO, 1))).saldo == 0      # 5 PB, 1 solo
    assert calcular(OpcoesDoGuia(pjs=1), inimigos((T.SOLO, 2))).saldo < 0


@pytest.mark.parametrize("opcoes", [OpcoesDoGuia(pjs=0), OpcoesDoGuia(patamar=5),
                                    OpcoesDoGuia(mais_facil=True, mais_dificil=True)])
def test_opcoes_invalidas(opcoes):
    with pytest.raises(RegraViolada):
        calcular(opcoes, [])
