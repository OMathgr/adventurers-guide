import dataclasses

import pytest

from motor import Movimento, Personagem, RegraViolada

# Bardo (conftest) é Faun, sem efeito numérico: 5 PV, 6 Estresse, Evasão 10.


def bardo_com(bib, criacao_bardo, **mudancas):
    return Personagem(bib, dataclasses.replace(criacao_bardo, **mudancas))


def nomes(f):
    return [c.nome for c in f.caracteristicas_ancestralidade]


# --- Características que mudam números na criação ---------------------------------

def test_giant_ganha_pv(bib, criacao_bardo):
    assert bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_giant").ficha().pv_max == 6


def test_human_ganha_estresse(bib, criacao_bardo):
    assert bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_human").ficha().estresse_max == 7


def test_simiah_ganha_evasao(bib, criacao_bardo):
    assert bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_simiah").ficha().evasao == 11


def test_clank_escolhe_experiencia_para_o_proposito(bib, criacao_bardo):
    f = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_clank",
                  experiencia_proposito="Diplomata").ficha()
    assert f.experiencias == {"Diplomata": 3, "Cantora de taverna": 2}
    with pytest.raises(RegraViolada, match="Projeto com Propósito"):
        bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_clank")
    with pytest.raises(RegraViolada, match="Projeto com Propósito"):
        bardo_com(bib, criacao_bardo, experiencia_proposito="Diplomata")   # Faun


def test_galapa_soma_proficiencia_aos_limiares(bib, criacao_bardo):
    f = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_galapa").ficha()
    assert (f.limiar_maior, f.limiar_grave) == (1 + 1, 2 + 1)   # sem armadura, Proficiência 1


def test_ficha_lista_as_caracteristicas(bardo):
    assert nomes(bardo.ficha()) == ["Caprine Leap", "Kick"]


# --- Ancestralidade mista ------------------------------------------------------------

def test_mista_pega_primeira_de_uma_e_segunda_de_outra(bib, criacao_bardo):
    f = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_giant",
                  segunda_ancestralidade="core_ancestry_simiah").ficha()
    assert nomes(f) == ["Endurance", "Nimble"]
    assert (f.pv_max, f.evasao) == (6, 11)
    assert f.segunda_ancestralidade == "core_ancestry_simiah"


def test_mista_invertida_troca_as_caracteristicas(bib, criacao_bardo):
    f = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_simiah",
                  segunda_ancestralidade="core_ancestry_giant").ficha()
    assert nomes(f) == ["Natural Climber", "Reach"]
    assert (f.pv_max, f.evasao) == (5, 10)


def test_mista_exige_ancestralidades_diferentes_e_validas(bib, criacao_bardo):
    with pytest.raises(RegraViolada, match="diferentes"):
        bardo_com(bib, criacao_bardo, segunda_ancestralidade="core_ancestry_faun")
    with pytest.raises(RegraViolada, match="Ancestralidade"):
        bardo_com(bib, criacao_bardo, segunda_ancestralidade="core_ancestry_dragao")


# --- Características que mudam o descanso ----------------------------------------------

def test_efficient_faz_um_movimento_longo_no_descanso_curto(bib, criacao_bardo):
    clank = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_clank",
                      experiencia_proposito="Diplomata")
    clank.sessao.marcar_pv(5)
    r = clank.sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.PREPARAR],
                                    movimento_longo=0)
    assert r[0].recuperado == 5 and clank.sessao.pv_marcados == 0


def test_efficient_permite_projeto_no_curto(bib, criacao_bardo):
    clank = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_clank",
                      experiencia_proposito="Diplomata")
    clank.sessao.descanso_curto([Movimento.PROJETO, Movimento.PREPARAR], movimento_longo=0)


def test_sem_efficient_nao_troca(bardo):
    with pytest.raises(RegraViolada, match="Eficiente"):
        bardo.sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.PREPARAR], movimento_longo=0)


def test_celestial_trance_da_um_movimento_a_mais(bib, criacao_bardo):
    elfo = bardo_com(bib, criacao_bardo, ancestralidade="core_ancestry_elf")
    r = elfo.sessao.descanso_longo([Movimento.PREPARAR, Movimento.PREPARAR, Movimento.PREPARAR])
    assert len(r) == 3 and elfo.sessao.esperanca == 5
    with pytest.raises(RegraViolada, match="dois"):
        elfo.sessao.descanso_curto([Movimento.PREPARAR] * 4)


def test_sem_trance_tres_movimentos_e_recusado(bardo):
    with pytest.raises(RegraViolada, match="dois"):
        bardo.sessao.descanso_longo([Movimento.PREPARAR] * 3)
