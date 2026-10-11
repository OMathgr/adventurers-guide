"""Tradução pt-BR: tudo do SRD precisa ter tradução, e traduzir não pode
mudar nenhuma regra (as regras leem o inglês)."""

import pytest

from motor import Biblioteca, Personagem



@pytest.fixture(scope="module")
def pt():
    return Biblioteca(idioma="pt-BR")


def test_nada_ficou_sem_traducao(pt):
    assert pt.traducoes_faltando == []


def test_nomes_traduzidos_e_original_guardado(pt):
    bardo = pt.classes["core_class_bard"]
    assert (bardo.nome, bardo.nome_original, bardo.codigo) == ("Bardo", "Bard", "BARD")
    espada = pt.armas["core_weapon_improved_broadsword"]   # composta: base + qualidade
    assert (espada.nome, espada.nome_original) == ("Espada Larga Aprimorada", "Improved Broadsword")
    assert pt.armas["core_weapon_legendary_battleaxe"].nome == "Machado de Batalha Lendário"
    assert pt.armas["core_weapon_advanced_glowing_rings"].nome == "Anéis Brilhantes Avançados"
    assert pt.nome_dominio("BLADE") == "Lâmina"


def test_texto_das_cartas_inclui_listas_e_magias(pt):
    assert "• +1 nos seus testes de Conjuração" in pt.cartas["core_domain_card_arcana_touched"].texto
    assert pt.cartas["core_domain_card_book_of_ava"].texto.startswith("Empurrão de Poder:")


def test_traduzir_nao_muda_regras(pt):
    en = Biblioteca()
    for i, arma in en.armas.items():
        traduzida = pt.armas[i]
        assert [(c.modificadores, c.requisitos, c.efeito) for c in arma.caracteristicas] == \
               [(c.modificadores, c.requisitos, c.efeito) for c in traduzida.caracteristicas], i
    for i, a in en.ancestralidades.items():
        assert [c.efeito for c in a.caracteristicas] == [c.efeito for c in pt.ancestralidades[i].caracteristicas]


def test_personagem_com_biblioteca_traduzida(pt, criacao_bardo):
    p = Personagem(pt, criacao_bardo)
    p.equipar(principal="core_weapon_broadsword", armadura="core_armor_chainmail_armor")
    f = p.ficha()
    assert f.ataques[0].arma == "Espada Larga"
    assert f.evasao == 9                                   # Heavy (Pesada) continua valendo
    assert f.caracteristicas_armadura[0].nome == "Pesada"
    assert p.linha_do_tempo()[0]["itens"][0] == "Classe: Bardo"
