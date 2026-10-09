import pytest

from motor import Personagem, RegraViolada, Traco


def test_ficha_inicial(bardo):
    f = bardo.ficha()
    assert f.nivel == 1
    assert f.evasao == 10 and f.pv_max == 5      # valores do Bardo no SRD
    assert f.estresse_max == 6 and f.esperanca == 2 and f.proficiencia == 1
    assert f.experiencias == {"Diplomata": 2, "Cantora de taverna": 2}
    assert f.bonus_limiares == 1


def test_distribuicao_de_tracos_invalida(bib, criacao_bardo):
    criacao_bardo.tracos[Traco.FORCA] = 2
    with pytest.raises(RegraViolada, match="Distribua"):
        Personagem(bib, criacao_bardo)


def test_subclasse_de_outra_classe(bib, criacao_bardo):
    criacao_bardo.subclasse = "core_subclass_call_of_the_brave"
    with pytest.raises(RegraViolada, match="não é subclasse"):
        Personagem(bib, criacao_bardo)


def test_carta_fora_dos_dominios(bib, criacao_bardo):
    criacao_bardo.cartas = ["core_domain_card_get_back_up", "core_domain_card_book_of_ava"]
    with pytest.raises(RegraViolada):
        Personagem(bib, criacao_bardo)


def test_carta_de_nivel_alto_na_criacao(bib, criacao_bardo):
    criacao_bardo.cartas = ["core_domain_card_tell_no_lies", "core_domain_card_book_of_ava"]
    with pytest.raises(RegraViolada):
        Personagem(bib, criacao_bardo)


def test_experiencias_repetidas(bib, criacao_bardo):
    criacao_bardo.experiencias = ["Diplomata", "Diplomata"]
    with pytest.raises(RegraViolada):
        Personagem(bib, criacao_bardo)
