"""Itens criados pelo mestre: armas, armaduras, consumíveis e comuns que viram
itens como os do SRD na ficha, no equipamento, no inventário e nas lojas."""

import dataclasses

import pytest

from motor import Alvo, Caracteristica, Efeito, Modificador, Personagem, RegraViolada, Traco
from motor.itens_proprios import ItemProprio, TipoProprio, copia, id_da_copia, validar
from motor.loja import ItemDaLoja, TipoNaLoja, vender
from motor.srd import CategoriaArma, TipoDano


def lamina(**extra) -> ItemProprio:
    campos = dict(
        tipo=TipoProprio.ARMA, nome="Lâmina do Eclipse", descricao="Forjada na última noite.",
        tier=1, categoria=CategoriaArma.PRIMARIA_FISICA, traco=Traco.PRESENCA, alcance="MELEE",
        dado="d10", modificador_dano=2, tipo_dano=TipoDano.FISICO,
        caracteristicas=[Caracteristica("Sombria", "+1 em Evasão e +1 nos ataques.",
                                        (Modificador(Alvo.EVASAO, 1), Modificador(Alvo.ATAQUE, 1)))])
    return ItemProprio(**{**campos, **extra})


def couraca() -> ItemProprio:
    return ItemProprio(tipo=TipoProprio.ARMADURA, nome="Couraça de Escamas", limiar_maior=7, limiar_grave=15,
                       pontuacao=4, caracteristicas=[Caracteristica("Fortificada", "Reduz mais.",
                                                                    efeito=Efeito.FORTIFICADA)])


def tonico(**extra) -> ItemProprio:
    return ItemProprio(**{**dict(tipo=TipoProprio.CONSUMIVEL, nome="Tônico da Bruxa", descricao="Amargo.",
                                 limpa_pv="1d6"), **extra})


# --- arma ---------------------------------------------------------------------------------------

def test_arma_vai_para_as_guardadas_e_equipada_entra_na_ficha(bardo, bib):
    evasao = bardo.ficha().evasao
    id_ = bardo.receber_item_proprio(lamina())
    assert bardo.inventario.armas == [id_] and id_.startswith("proprio_")
    assert id_ not in bib.armas   # o catálogo do SRD (compartilhado) não muda
    f = bardo.trocar_arma(0, em_perigo=False)
    ataque = f.ataques[0]
    assert (ataque.arma, ataque.traco, ataque.dano) == ("Lâmina do Eclipse", Traco.PRESENCA, "1d10+2")
    assert ataque.bonus == 2 + 1   # Presença 2 + o bônus de ataque da característica
    assert f.evasao == evasao + 1
    assert [a.id for a in bardo.armas_proprias()] == [id_]


def test_caracteristica_copiada_do_srd_vale_igual(bardo, bib):
    pesada = next(c for a in bib.armas.values() for c in a.caracteristicas if c.nome_original == "Heavy")
    id_ = bardo.receber_item_proprio(lamina(caracteristicas=[pesada]))
    evasao = bardo.ficha().evasao
    assert bardo.equipar(principal=id_).evasao == evasao - 1   # Heavy: -1 to Evasion


# --- armadura -----------------------------------------------------------------------------------

def test_armadura_e_vestida_na_hora_com_a_regra_especial(bardo):
    id_ = bardo.receber_item_proprio(couraca())
    f = bardo.ficha()
    assert bardo.equipamento.armadura == id_
    assert (f.armadura, f.pontuacao_armadura, f.limiar_maior, f.limiar_grave) == ("Couraça de Escamas", 4, 8, 16)
    assert Efeito.FORTIFICADA in bardo.efeitos_ativos()
    with pytest.raises(RegraViolada, match="uma por vez"):
        bardo.receber_item_proprio(couraca(), quantidade=2)


# --- consumível e comum -------------------------------------------------------------------------

def test_consumivel_usa_o_efeito_e_respeita_o_limite(bardo):
    id_ = bardo.receber_item_proprio(tonico(), quantidade=2)
    bardo.sessao.pv_marcados = 5
    notas = bardo.usar_consumivel(id_, rolagem=4)
    assert bardo.sessao.pv_marcados == 1 and "Limpou 4 PV." in notas
    assert bardo.inventario.itens[id_] == 1
    assert bardo.receber_item_proprio(tonico(), quantidade=4) == id_   # mesmo conteúdo: empilha
    with pytest.raises(RegraViolada, match="No máximo 5"):
        bardo.receber_item_proprio(tonico())


def test_editar_o_modelo_vira_outro_item(bardo):
    antigo = bardo.receber_item_proprio(tonico())
    novo = bardo.receber_item_proprio(tonico(descricao="Mais amargo."))
    assert antigo != novo and (bardo.inventario.itens[antigo], bardo.inventario.itens[novo]) == (1, 1)
    assert bardo.bib.itens[antigo].texto == "Amargo."   # o que já tinha não muda


def test_item_comum_so_tem_texto(bardo):
    id_ = bardo.receber_item_proprio(ItemProprio(tipo=TipoProprio.COMUM, nome="Chave da Torre", descricao="Fria."))
    item = bardo.bib.itens[id_]
    assert (item.nome, item.texto, item.efeito) == ("Chave da Torre", "Fria.", None)
    with pytest.raises(RegraViolada, match="Isso não é um consumível"):
        bardo.usar_consumivel(id_)


# --- salvar, copiar, falhar -------------------------------------------------------------------------

def test_copia_guardada_volta_ao_carregar_e_vai_na_copia_do_personagem(bardo, bib, criacao_bardo):
    id_ = bardo.receber_item_proprio(lamina())
    bardo.trocar_arma(0, em_perigo=False)
    estado = bardo.estado()
    outro = Personagem(bib, criacao_bardo)
    outro.restaurar_estado(estado)
    assert outro.equipamento.principal == id_ and outro.ficha().ataques[0].dano == "1d10+2"
    assert bardo.copia().ficha().ataques[0].arma == "Lâmina do Eclipse"


def test_recusa_nao_muda_nada(bardo):
    bardo.receber_item_proprio(lamina(), quantidade=2)   # cabem 2 armas guardadas
    antes = dataclasses.asdict(bardo.inventario)
    with pytest.raises(RegraViolada, match="Só cabem 2"):
        bardo.receber_item_proprio(lamina(descricao="Outra."))
    assert dataclasses.asdict(bardo.inventario) == antes
    assert len(bardo.armas_proprias()) == 1


def test_loja_vende_item_da_mesa(bardo):
    bardo.inventario.ouro = 5
    item = ItemDaLoja(TipoNaLoja.PROPRIO, preco=3, ref="modelo-1", proprio=tonico().estado(), estoque=2)
    notas = vender(bardo, item)
    assert notas == ["Comprou 1× Tônico da Bruxa (3 punhados)."]
    assert bardo.inventario.ouro == 2 and item.estoque == 1
    assert bardo.inventario.itens[id_da_copia(copia(tonico()))] == 1


# --- validação ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("item, erro", [
    (lamina(dado="d7"), "Dado de dano"),
    (lamina(alcance="LONGE"), "Alcance"),
    (ItemProprio(tipo=TipoProprio.ARMADURA, nome="X", limiar_maior=10, limiar_grave=8), "limiares"),
    (ItemProprio(tipo=TipoProprio.COMUM, nome="  "), "Dê um nome"),
    (tonico(limpa_pf="1d4"), "um dado"),
    (tonico(limpa_pv="muito"), "Quantidade de PV"),
    (tonico(escolha=True), "preencha os dois"),
    (ItemProprio(tipo=TipoProprio.COMUM, nome="X", caracteristicas=[Caracteristica("Y", "")]), "só de armas"),
    (lamina(caracteristicas=[Caracteristica("Z", "", efeito=Efeito.FORTIFICADA)]), "só de armaduras"),
    (ItemProprio(tipo=TipoProprio.ARMADURA, nome="X",
                 caracteristicas=[Caracteristica("Z", "", (Modificador(Alvo.ATAQUE, 1),))]), "só de armas"),
    (lamina(caracteristicas=[Caracteristica("Z", "", (Modificador(Alvo.EVASAO, 50),))]), "-10 a \\+10"),
])
def test_validacao(item, erro):
    with pytest.raises(RegraViolada, match=erro):
        validar(item)


def test_estado_vai_e_volta():
    item = couraca()
    assert ItemProprio.de_estado(item.estado()) == item
    assert item.estado()["caracteristicas"][0]["efeito"] == "FORTIFICADA"
