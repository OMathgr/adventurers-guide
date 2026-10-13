"""Quadro da sessão: validação e o que os jogadores veem."""

import pytest

from motor import RegraViolada
from motor.quadro import Cartao, Ligacao, Quadro, TipoCartao, TipoItem, so_revelado, validar


def nota(i, revelado=False):
    return Cartao(id=i, tipo=TipoCartao.NOTA, titulo=f"Nota {i}", revelado=revelado)


def test_quadro_valido():
    q = Quadro(cartoes=[nota("a"), Cartao(id="b", tipo=TipoCartao.ITEM, item_tipo=TipoItem.NPC, item_id="n1"),
                        Cartao(id="c", tipo=TipoCartao.IMAGEM, imagem="img1")],
               ligacoes=[Ligacao("l1", "a", "b", "trai"),
                         Ligacao("l2", "b", "c", de_ponto="baixo", para_ponto="topo")])   # de baixo para cima
    validar(q)


@pytest.mark.parametrize("q, mensagem", [
    (Quadro(cartoes=[nota("a"), nota("a")]), "id único"),
    (Quadro(cartoes=[nota("a")], ligacoes=[Ligacao("l1", "a", "x")]), "não está no quadro"),
    (Quadro(cartoes=[nota("a")], ligacoes=[Ligacao("l1", "a", "a")]), "diferentes"),
    (Quadro(cartoes=[Cartao(id="a", tipo=TipoCartao.ITEM)]), "qual item"),
    (Quadro(cartoes=[Cartao(id="a", tipo=TipoCartao.IMAGEM)]), "imagem"),
    (Quadro(cartoes=[Cartao(id="a", tipo=TipoCartao.NOTA, cor="roxo")]), "Cor"),
    (Quadro(cartoes=[nota(str(i)) for i in range(301)]), "300"),
    (Quadro(cartoes=[nota("a"), nota("b")], ligacoes=[Ligacao("l", "a", "b", de_ponto="meio")]), "topo"),
])
def test_quadro_invalido(q, mensagem):
    with pytest.raises(RegraViolada, match=mensagem):
        validar(q)


def test_jogadores_veem_so_o_revelado_e_ligacoes_entre_revelados():
    q = Quadro(cartoes=[nota("a", True), nota("b", True), nota("c")],
               ligacoes=[Ligacao("l1", "a", "b", "leva a"), Ligacao("l2", "b", "c", "esconde")])
    v = so_revelado(q)
    assert [c.id for c in v.cartoes] == ["a", "b"]
    # a seta para o cartão escondido entregaria que ele existe
    assert [l.id for l in v.ligacoes] == ["l1"]
