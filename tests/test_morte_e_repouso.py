"""Movimentos de morte, cicatrizes e o repouso do grupo (com movimentos em aliados)."""

import pytest

from motor import Cicatriz, Personagem, RegraViolada
from motor.repouso import EscolhaDeRepouso, MovimentoEscolhido, TipoDeRepouso, concluir
from motor.sessao import ImpactoDaCicatriz, Movimento, MovimentoDeMorte


def cair(p: Personagem):
    p.sessao.marcar_pv(p.ficha().pv_max)
    assert p.sessao.precisa_movimento_de_morte and p.ficha().precisa_movimento_de_morte


# --- Morte --------------------------------------------------------------------------------------

def test_so_quem_caiu_faz_movimento_de_morte(bardo):
    with pytest.raises(RegraViolada, match="último PV"):
        bardo.sessao.movimento_de_morte(MovimentoDeMorte.SACRIFICIO_GLORIOSO)


def test_sacrificio_glorioso(bardo):
    cair(bardo)
    r = bardo.sessao.movimento_de_morte("SACRIFICIO_GLORIOSO")
    assert r.morreu and bardo.ficha().morto
    with pytest.raises(RegraViolada, match="véu da morte"):
        bardo.sessao.receber_dano(3)


def test_evitar_a_morte_sem_cicatriz_e_acordar(bardo):
    cair(bardo)
    r = bardo.sessao.movimento_de_morte("EVITAR_A_MORTE", rolagem_esperanca=12)   # 12 > nível 1
    assert (r.inconsciente, r.cicatriz, r.morreu) == (True, False, False)
    assert not bardo.sessao.precisa_movimento_de_morte   # já escolheu
    bardo.sessao.limpar_pv(1)                             # um aliado limpa 1 PV
    assert not bardo.sessao.inconsciente


def test_evitar_a_morte_com_cicatriz(bardo):
    cair(bardo)
    bardo.sessao.esperanca = 6
    r = bardo.sessao.movimento_de_morte("EVITAR_A_MORTE", rolagem_esperanca=1)   # 1 <= nível 1
    assert r.cicatriz and not r.morreu
    f = bardo.ficha()
    assert (f.esperanca_max, f.esperanca, len(f.cicatrizes)) == (5, 5, 1)   # um espaço riscado
    bardo.sessao.definir_cicatriz(0, "MEMORIA", "O incêndio da vila")
    assert bardo.ficha().cicatrizes[0].impacto is ImpactoDaCicatriz.MEMORIA
    bardo.sessao.curar_cicatriz(0)   # a critério do mestre
    assert bardo.ficha().esperanca_max == 6


def test_ultimo_espaco_de_esperanca_encerra_a_jornada(bardo):
    for _ in range(5):
        bardo.sessao.cicatrizes.append(Cicatriz())   # 5 dos 6 espaços já riscados
    cair(bardo)
    r = bardo.sessao.movimento_de_morte("EVITAR_A_MORTE", rolagem_esperanca=1)
    assert r.morreu and bardo.ficha().esperanca_max == 0


def test_arriscar_tudo(bardo, bib, criacao_bardo):
    cair(bardo)
    bardo.sessao.marcar_estresse(2)
    r = bardo.sessao.movimento_de_morte("ARRISCAR_TUDO", rolagem_esperanca=8, rolagem_medo=3, pv=5)
    assert (r.morreu, r.pv_limpos, r.pf_limpos) == (False, 5, 2)   # 8 = 5 PV + 3 PF (só 2 marcados)
    with pytest.raises(RegraViolada, match="Divida"):
        outro = Personagem(bib, criacao_bardo)
        cair(outro)
        outro.sessao.movimento_de_morte("ARRISCAR_TUDO", rolagem_esperanca=4, rolagem_medo=2, pv=5)


def test_arriscar_tudo_critico_e_medo(bib, criacao_bardo):
    a = Personagem(bib, criacao_bardo)
    cair(a)
    a.sessao.marcar_estresse(3)
    r = a.sessao.movimento_de_morte("ARRISCAR_TUDO", rolagem_esperanca=7, rolagem_medo=7)
    assert (a.sessao.pv_marcados, a.sessao.estresse_marcado, r.morreu) == (0, 0, False)
    b = Personagem(bib, criacao_bardo)
    cair(b)
    assert b.sessao.movimento_de_morte("ARRISCAR_TUDO", rolagem_esperanca=2, rolagem_medo=9).morreu


def test_morte_e_cicatrizes_sao_salvas(bardo, bib):
    cair(bardo)
    bardo.sessao.movimento_de_morte("EVITAR_A_MORTE", rolagem_esperanca=1)
    bardo.sessao.definir_cicatriz(0, "MEDO", "Água funda")
    outro = Personagem(bib, bardo.criacao)
    outro.restaurar_estado(bardo.estado())
    assert outro.sessao.inconsciente and outro.sessao.cicatrizes == bardo.sessao.cicatrizes


# --- Repouso do grupo --------------------------------------------------------------------------

def mov(m, alvo=None, rolagem=None):
    return MovimentoEscolhido(Movimento(m), alvo, rolagem)


def test_tratar_feridas_de_um_aliado_e_preparar_em_grupo(bardo, guerreiro):
    guerreiro.sessao.marcar_pv(4)
    bardo.sessao.esperanca = guerreiro.sessao.esperanca = 2
    r = concluir("curto", {"b": bardo, "g": guerreiro}, {
        "b": EscolhaDeRepouso([mov("CUIDAR_FERIDAS", alvo="g", rolagem=2), mov("PREPARAR_EM_GRUPO")]),
        "g": EscolhaDeRepouso([mov("PREPARAR_EM_GRUPO"), mov("ALIVIAR_ESTRESSE", rolagem=1)]),
    })
    assert guerreiro.sessao.pv_marcados == 1             # 2 + patamar 1 = 3 PV limpos pelo bardo
    assert (bardo.sessao.esperanca, guerreiro.sessao.esperanca) == (4, 4)   # +2 cada
    assert r.por_personagem["b"][0].alvo == "Bruna"
    assert bardo.sessao.descansos_curtos_seguidos == 1


def test_preparar_em_grupo_sozinho_vale_um(bardo, guerreiro):
    bardo.sessao.esperanca = 2
    r = concluir("curto", {"b": bardo, "g": guerreiro}, {
        "b": EscolhaDeRepouso([mov("PREPARAR_EM_GRUPO"), mov("ALIVIAR_ESTRESSE", rolagem=1)]),
        "g": EscolhaDeRepouso([mov("ALIVIAR_ESTRESSE", rolagem=1), mov("ALIVIAR_ESTRESSE", rolagem=1)]),
    })
    assert bardo.sessao.esperanca == 3 and "sozinho" in r.notas[0]


def test_descanso_longo_acorda_e_limpa_tudo(bardo, guerreiro):
    cair(bardo)
    bardo.sessao.movimento_de_morte("EVITAR_A_MORTE", rolagem_esperanca=12)
    concluir("longo", {"b": bardo, "g": guerreiro}, {
        "b": EscolhaDeRepouso([mov("ALIVIAR_ESTRESSE"), mov("PREPARAR")]),
        "g": EscolhaDeRepouso([mov("CUIDAR_FERIDAS", alvo="b"), mov("PREPARAR")]),
    })
    assert (bardo.sessao.pv_marcados, bardo.sessao.inconsciente) == (0, False)


def test_longo_interrompido_vale_curto(bardo, guerreiro):
    bardo.sessao.marcar_pv(5)
    bardo.sessao.descansos_curtos_seguidos = 3   # mesmo depois de três curtos (o livro diz)
    r = concluir("longo", {"b": bardo}, {
        "b": EscolhaDeRepouso([mov("CUIDAR_FERIDAS", rolagem=1), mov("PROJETO")]),
    }, interrompido=True)
    assert r.tipo is TipoDeRepouso.CURTO
    assert bardo.sessao.pv_marcados == 3     # 1 + patamar 1, não "tudo"; o projeto ficou para depois
    assert bardo.sessao.descansos_curtos_seguidos == 3
    with pytest.raises(RegraViolada, match="cancele"):
        concluir("curto", {"b": bardo}, {"b": EscolhaDeRepouso([mov("PREPARAR"), mov("PREPARAR")])}, interrompido=True)


def test_validacoes_do_repouso(bardo, guerreiro):
    com_os_dois = {"b": bardo, "g": guerreiro}
    so_bardo = {"b": EscolhaDeRepouso([mov("PREPARAR"), mov("PREPARAR")])}
    with pytest.raises(RegraViolada, match="falta escolher"):
        concluir("curto", com_os_dois, so_bardo)
    with pytest.raises(RegraViolada, match="não está neste repouso"):
        concluir("curto", {"b": bardo}, {"b": EscolhaDeRepouso([mov("CUIDAR_FERIDAS", alvo="x"), mov("PREPARAR")])})
    with pytest.raises(RegraViolada, match="num aliado"):
        concluir("curto", com_os_dois, {**so_bardo, "g": EscolhaDeRepouso([mov("PREPARAR", alvo="b"), mov("PREPARAR")])})
    with pytest.raises(RegraViolada, match="projeto"):
        concluir("curto", {"b": bardo}, {"b": EscolhaDeRepouso([mov("PROJETO"), mov("PREPARAR")])})
    # nada mudou com as recusas
    assert bardo.sessao.descansos_curtos_seguidos == 0


def test_quem_morreu_nao_descansa(bardo, guerreiro):
    cair(guerreiro)
    guerreiro.sessao.movimento_de_morte("SACRIFICIO_GLORIOSO")
    r = concluir("curto", {"b": bardo, "g": guerreiro}, {"b": EscolhaDeRepouso([mov("PREPARAR"), mov("PREPARAR")])})
    assert list(r.por_personagem) == ["b"]
