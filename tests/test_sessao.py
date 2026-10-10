import random

import pytest

from motor import Escolha, Gravidade, Movimento, Opcao, RegraViolada, SubidaDeNivel

# Bardo nível 1: 5 PV, 6 Estresse, Esperança 2.
# Com armadura de couro: limiares 7 / 14, Pontuação de Armadura 3.
COURO = "core_armor_leather_armor"
PALAVRAS = "core_domain_card_inspirational_words"


@pytest.fixture
def bardo_de_couro(bardo):
    bardo.equipar(armadura=COURO)
    return bardo


# --- Dano --------------------------------------------------------------------------

@pytest.mark.parametrize("dano, gravidade", [
    (0, Gravidade.NENHUM), (6, Gravidade.MENOR), (7, Gravidade.MAIOR),
    (13, Gravidade.MAIOR), (14, Gravidade.GRAVE), (40, Gravidade.GRAVE),
])
def test_gravidade_pelos_limiares(bardo_de_couro, dano, gravidade):
    assert bardo_de_couro.sessao.gravidade(dano) is gravidade


def test_dano_massivo_e_opcional(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    assert sessao.gravidade(28) is Gravidade.GRAVE
    sessao.dano_massivo = True
    assert sessao.gravidade(28) is Gravidade.MASSIVO   # 2 x 14
    assert sessao.gravidade(27) is Gravidade.GRAVE


def test_receber_dano_marca_pv(bardo_de_couro):
    r = bardo_de_couro.sessao.receber_dano(10)
    assert (r.gravidade, r.pv_marcados, r.usou_armadura, r.caiu) == (Gravidade.MAIOR, 2, False, False)
    assert bardo_de_couro.ficha().pv_marcados == 2


def test_armadura_reduz_um_nivel_e_gasta_espaco(bardo_de_couro):
    r = bardo_de_couro.sessao.receber_dano(14, usar_armadura=True)
    assert (r.gravidade, r.pv_marcados, r.usou_armadura) == (Gravidade.GRAVE, 2, True)
    f = bardo_de_couro.ficha()
    assert (f.pv_marcados, f.armadura_marcada) == (2, 1)


def test_sem_espaco_de_armadura_nao_reduz(bardo):
    r = bardo.sessao.receber_dano(1, usar_armadura=True)   # sem armadura: limiares 1/2, Pontuação 0
    assert (r.gravidade, r.pv_marcados, r.usou_armadura) == (Gravidade.MAIOR, 2, False)


def test_ultimo_pv_derruba(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    sessao.receber_dano(14)
    r = sessao.receber_dano(14)
    assert r.caiu and sessao.caido
    assert bardo_de_couro.ficha().pv_marcados == 5   # não passa do máximo


# --- Estresse e Esperança -------------------------------------------------------------

def test_estresse_imposto_sem_espaco_vira_pv(bardo):
    bardo.sessao.marcar_estresse(8)   # 6 de Estresse + 2 de PV
    f = bardo.ficha()
    assert (f.estresse_marcado, f.pv_marcados) == (6, 2)


def test_pagar_estresse_exige_espaco(bardo):
    bardo.sessao.marcar_estresse(5)
    with pytest.raises(RegraViolada, match="insuficiente"):
        bardo.sessao.pagar_estresse(2)
    assert bardo.sessao.estresse_marcado == 5
    bardo.sessao.pagar_estresse(1)
    assert bardo.sessao.estresse_livre == 0


def test_esperanca(bardo):
    sessao = bardo.sessao
    assert bardo.ficha().esperanca == 2
    sessao.ganhar_esperanca(10)
    assert sessao.esperanca == 6                      # limite
    sessao.gastar_esperanca(4)
    with pytest.raises(RegraViolada, match="insuficiente"):
        sessao.gastar_esperanca(3)
    assert bardo.ficha().esperanca == 2


def test_quantidade_negativa(bardo):
    with pytest.raises(RegraViolada):
        bardo.sessao.marcar_pv(-1)


# --- Descansos ---------------------------------------------------------------------

def test_descanso_curto_com_rolagem_informada(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    sessao.receber_dano(14)                              # 3 PV
    sessao.marcar_estresse(5)
    r = sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.ALIVIAR_ESTRESSE], [1, 3])
    # tier 1: 1d4 + 1
    assert [(x.rolagem, x.recuperado) for x in r] == [(1, 2), (3, 4)]
    assert (sessao.pv_marcados, sessao.estresse_marcado) == (1, 1)


def test_descanso_curto_rolado_pelo_motor(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    sessao.rng = random.Random(42)
    sessao.marcar_estresse(6)
    r = sessao.descanso_curto([Movimento.ALIVIAR_ESTRESSE, Movimento.ALIVIAR_ESTRESSE])
    assert all(1 <= x.rolagem <= 4 for x in r)
    assert sessao.estresse_marcado == max(0, 6 - sum(x.rolagem + 1 for x in r))


def test_recuperacao_nao_passa_do_que_esta_marcado(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    sessao.receber_dano(1)                               # 1 PV
    r = sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.PREPARAR], [4, None])
    assert r[0].recuperado == 1 and sessao.pv_marcados == 0
    assert r[1].recuperado == 1 and sessao.esperanca == 3


def test_descanso_longo_limpa_tudo(bardo_de_couro):
    sessao = bardo_de_couro.sessao
    sessao.receber_dano(14, usar_armadura=True)
    sessao.marcar_estresse(4)
    sessao.descanso_longo([Movimento.CUIDAR_FERIDAS, Movimento.ALIVIAR_ESTRESSE])
    assert (sessao.pv_marcados, sessao.estresse_marcado, sessao.armadura_marcada) == (0, 0, 1)
    sessao.descanso_longo([Movimento.REPARAR_ARMADURA, Movimento.PREPARAR_EM_GRUPO])
    assert (sessao.armadura_marcada, sessao.esperanca) == (0, 4)


def test_tres_descansos_curtos_seguidos_exigem_um_longo(bardo):
    sessao = bardo.sessao
    for _ in range(3):
        sessao.descanso_curto([Movimento.PREPARAR, Movimento.PREPARAR])
    with pytest.raises(RegraViolada, match="longo"):
        sessao.descanso_curto([Movimento.PREPARAR, Movimento.PREPARAR])
    sessao.descanso_longo([Movimento.PREPARAR, Movimento.PREPARAR])
    sessao.descanso_curto([Movimento.PREPARAR, Movimento.PREPARAR])


def test_regras_do_descanso(bardo):
    sessao = bardo.sessao
    with pytest.raises(RegraViolada, match="dois"):
        sessao.descanso_curto([Movimento.PREPARAR])
    with pytest.raises(RegraViolada, match="longo"):
        sessao.descanso_curto([Movimento.PROJETO, Movimento.PREPARAR])
    with pytest.raises(RegraViolada, match="d4"):
        sessao.descanso_curto([Movimento.CUIDAR_FERIDAS, Movimento.PREPARAR], [5, None])
    sessao.descanso_longo([Movimento.PROJETO, Movimento.PREPARAR])


# --- Integração com o resto do personagem ----------------------------------------------

def test_recuperar_carta_marca_estresse(bib, bardo):
    custo = bib.cartas[PALAVRAS].custo_recall
    assert custo > 0
    bardo.guardar_carta(PALAVRAS)
    bardo.recuperar_carta(PALAVRAS)
    assert bardo.sessao.estresse_marcado == custo


def test_recuperar_carta_sem_estresse_livre_e_recusado(bib, bardo):
    custo = bib.cartas[PALAVRAS].custo_recall
    bardo.guardar_carta(PALAVRAS)
    bardo.sessao.marcar_estresse(6 - custo + 1)
    with pytest.raises(RegraViolada, match="Estresse insuficiente"):
        bardo.recuperar_carta(PALAVRAS)
    assert bardo.ficha().cartas_cofre == [PALAVRAS]
    bardo.recuperar_carta(PALAVRAS, em_descanso=True)   # no descanso é grátis
    assert bardo.ficha().cartas_cofre == []


def test_trocar_para_armadura_menor_ajusta_espacos(bardo):
    bardo.equipar(armadura="core_armor_chainmail_armor")   # Pontuação 4
    bardo.sessao.armadura_marcada = 4
    bardo.equipar(armadura=COURO)                          # Pontuação 3
    assert bardo.sessao.armadura_marcada == 3


def test_desfazer_nivel_ajusta_pv(bardo):
    bardo.subir_de_nivel(SubidaDeNivel(2, [Escolha(Opcao.PV), Escolha(Opcao.EVASAO)],
                                       "core_domain_card_tell_no_lies", nova_experiencia="X"))
    bardo.sessao.marcar_pv(6)
    bardo.desfazer_ultimo_nivel()
    assert bardo.sessao.pv_marcados == 5


def test_subir_de_nivel_mantem_marcas(bardo):
    bardo.sessao.marcar_pv(2)
    f = bardo.subir_de_nivel(SubidaDeNivel(2, [Escolha(Opcao.PV), Escolha(Opcao.EVASAO)],
                                           "core_domain_card_tell_no_lies", nova_experiencia="X"))
    assert (f.pv_max, f.pv_marcados) == (6, 2)
